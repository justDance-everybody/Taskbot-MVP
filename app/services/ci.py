import logging
from typing import Dict, Any, Optional, Tuple
import json
from datetime import datetime
from app.services.llm import llm_service
from app.bitable import bitable_client
from app.field_mapping import get_field_value

logger = logging.getLogger(__name__)

class CIService:
    """CI状态处理服务"""
    
    def __init__(self):
        self.llm = llm_service
        self.bitable = bitable_client
    
    async def process_github_webhook(self, payload: Dict[str, Any]) -> bool:
        """处理GitHub webhook事件"""
        try:
            event_type = payload.get("action", "")
            
            if event_type in ["completed", "requested"]:
                return await self._process_ci_status(payload)
            
            logger.info(f"忽略GitHub事件类型: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"处理GitHub webhook时出错: {str(e)}")
            return False
    
    async def _process_ci_status(self, payload: Dict[str, Any]) -> bool:
        """处理CI状态变更"""
        try:
            # 提取关键信息
            repo_name = payload.get("repository", {}).get("name", "")
            commit_sha = payload.get("check_run", {}).get("head_sha", "")
            status = payload.get("check_run", {}).get("conclusion", "")
            check_name = payload.get("check_run", {}).get("name", "")
            
            logger.info(f"处理CI状态: {repo_name}/{commit_sha[:8]} - {check_name}: {status}")
            
            # 查找相关任务
            task_record = await self._find_task_by_submission(repo_name, commit_sha)
            if not task_record:
                logger.warning(f"未找到相关任务: {repo_name}/{commit_sha[:8]}")
                return True
            
            # 更新任务CI状态
            ci_state = self._map_ci_status(status)
            await self.bitable.update_task(task_record["record_id"], {
                "ci_state": ci_state,
                "ci_details": json.dumps({
                    "check_name": check_name,
                    "status": status,
                    "commit_sha": commit_sha,
                    "updated_at": datetime.now().isoformat()
                })
            })
            
            # 如果CI失败，自动标记任务为返工
            if ci_state == "failed":
                await self._handle_ci_failure(task_record, payload)
            elif ci_state == "passed":
                await self._handle_ci_success(task_record, payload)
            
            return True
            
        except Exception as e:
            logger.error(f"处理CI状态时出错: {str(e)}")
            return False
    
    async def _find_task_by_submission(self, repo_name: str, commit_sha: str) -> Optional[Dict[str, Any]]:
        """通过提交信息查找相关任务"""
        try:
            # 搜索包含该仓库链接的任务
            tasks = await self.bitable.search_tasks({"status": "submitted"})
            
            for task in tasks:
                submission_url = task.get("submission_url", "")
                if repo_name in submission_url or commit_sha in submission_url:
                    return task
            
            return None
            
        except Exception as e:
            logger.error(f"查找任务时出错: {str(e)}")
            return None
    
    def _map_ci_status(self, github_status: str) -> str:
        """映射GitHub CI状态到内部状态"""
        status_map = {
            "success": "passed",
            "failure": "failed",
            "neutral": "skipped",
            "cancelled": "cancelled",
            "timed_out": "failed",
            "action_required": "pending"
        }
        return status_map.get(github_status, "unknown")
    
    async def _handle_ci_failure(self, task_record: Dict[str, Any], payload: Dict[str, Any]) -> None:
        """处理CI失败"""
        try:
            # 提取失败原因
            check_run = payload.get("check_run", {})
            failure_reason = check_run.get("output", {}).get("summary", "CI检查失败")
            
            # 更新任务状态为返工
            await self.bitable.update_task(task_record["record_id"], {
                "status": "returned",
                "failure_reasons": json.dumps([failure_reason]),
                "returned_at": datetime.now().isoformat()
            })
            
            logger.info(f"任务 {task_record['record_id']} CI失败，已标记为返工")
            
        except Exception as e:
            logger.error(f"处理CI失败时出错: {str(e)}")
    
    async def _handle_ci_success(self, task_record: Dict[str, Any], payload: Dict[str, Any]) -> None:
        """处理CI成功"""
        try:
            # 检查是否还有其他验收步骤
            task_type = self._determine_task_type(task_record)
            
            if task_type == "code":
                # 代码任务，CI通过即可完成
                await self.bitable.update_task(task_record["record_id"], {
                    "status": "completed",
                    "done_at": datetime.now().isoformat(),
                    "ai_score": 100  # CI通过给满分
                })
                logger.info(f"代码任务 {task_record['record_id']} CI通过，已完成")
            else:
                # 非代码任务，需要LLM评分
                await self._trigger_llm_review(task_record)
            
        except Exception as e:
            logger.error(f"处理CI成功时出错: {str(e)}")
    
    def _determine_task_type(self, task_record: Dict[str, Any]) -> str:
        """判断任务类型"""
        try:
            description = task_record.get("description", "").lower()
            skill_tags = [tag.lower() for tag in task_record.get("skill_tags", [])]
            
            # 代码相关关键词
            code_keywords = ["代码", "编程", "开发", "code", "programming", "development", 
                           "python", "javascript", "java", "go", "rust", "c++", "api"]
            
            # 检查描述和技能标签
            for keyword in code_keywords:
                if keyword in description or keyword in skill_tags:
                    return "code"
            
            return "non_code"
            
        except Exception as e:
            logger.error(f"判断任务类型时出错: {str(e)}")
            return "non_code"
    
    async def _trigger_llm_review(self, task_record: Dict[str, Any]) -> None:
        """触发LLM评审"""
        try:
            # 获取任务详情
            task_data = await self.bitable.get_task(task_record["record_id"])
            if not task_data:
                logger.error(f"无法获取任务详情: {task_record['record_id']}")
                return
            
            fields = task_data.get("fields", {})
            submission_url = get_field_value(fields, "submission_url", "task", "")
            
            # 调用LLM进行评分
            score, reasons = await self.evaluate_submission(
                description=get_field_value(fields, "description", "task", ""),
                acceptance_criteria=get_field_value(fields, "acceptance_criteria", "task", ""),
                submission_url=submission_url
            )
            
            # 更新任务状态
            if score >= 80:  # 通过阈值
                await self.bitable.update_task(task_record["record_id"], {
                    "status": "completed",
                    "ai_score": score,
                    "done_at": datetime.now().isoformat()
                })
                logger.info(f"任务 {task_record['record_id']} LLM评分通过: {score}")
            else:
                await self.bitable.update_task(task_record["record_id"], {
                    "status": "returned",
                    "ai_score": score,
                    "failure_reasons": json.dumps(reasons),
                    "returned_at": datetime.now().isoformat()
                })
                logger.info(f"任务 {task_record['record_id']} LLM评分未通过: {score}")
            
        except Exception as e:
            logger.error(f"LLM评审时出错: {str(e)}")
    
    async def evaluate_submission(self, description: str, acceptance_criteria: str, submission_url: str) -> Tuple[int, List[str]]:
        """使用LLM评估提交内容"""
        try:
            system_prompt = self._build_evaluation_system_prompt()
            user_prompt = self._build_evaluation_user_prompt(description, acceptance_criteria, submission_url)
            
            # 调用LLM
            response = await self.llm.call(user_prompt, system_prompt)
            
            # 解析评分结果
            score, reasons = self._parse_evaluation_response(response)
            
            return score, reasons
            
        except Exception as e:
            logger.error(f"LLM评估时出错: {str(e)}")
            return 50, ["评估过程出错，请人工审核"]
    
    def _build_evaluation_system_prompt(self) -> str:
        """构建评估系统提示词"""
        return """
你是质量评审助手，负责评估任务提交的质量。

评估标准：
1. 完整性：提交内容是否完整满足任务要求
2. 质量：工作质量是否达到标准
3. 规范性：是否遵循相关规范和最佳实践
4. 创新性：是否有创新点或优化改进

评分范围：0-100分
- 90-100分：优秀，超出预期
- 80-89分：良好，满足要求
- 70-79分：一般，基本满足
- 60-69分：较差，需要改进
- 0-59分：不合格，需要重做

请客观公正地评估，并提供具体的改进建议。
"""
    
    def _build_evaluation_user_prompt(self, description: str, acceptance_criteria: str, submission_url: str) -> str:
        """构建评估用户提示词"""
        return f"""
任务说明：
{description}

验收标准：
{acceptance_criteria}

提交链接：
{submission_url}

请评估此提交内容，返回JSON格式结果：
{{
  "score": 85,
  "failed_reasons": ["具体的问题或改进建议"]
}}

如果评分>=80，failed_reasons可以为空数组。
如果评分<80，请在failed_reasons中详细说明问题和改进建议。
"""
    
    def _parse_evaluation_response(self, response: str) -> Tuple[int, List[str]]:
        """解析LLM评估响应"""
        try:
            # 尝试解析JSON响应
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            eval_data = json.loads(json_str)
            score = eval_data.get("score", 50)
            reasons = eval_data.get("failed_reasons", [])
            
            # 确保分数在有效范围内
            score = max(0, min(100, int(score)))
            
            return score, reasons
            
        except Exception as e:
            logger.error(f"解析评估响应时出错: {str(e)}")
            # 尝试从文本中提取分数
            try:
                import re
                score_match = re.search(r'(\d+)分', response)
                if score_match:
                    score = int(score_match.group(1))
                    return score, ["自动解析的评分，请人工确认"]
            except:
                pass
            
            return 50, ["评估响应解析失败，请人工审核"]
    
    async def manual_review_task(self, task_id: str, score: int, comments: str) -> bool:
        """人工审核任务"""
        try:
            status = "completed" if score >= 80 else "returned"
            update_data = {
                "status": status,
                "ai_score": score,
                "manual_review_comments": comments
            }
            
            if status == "completed":
                update_data["done_at"] = datetime.now().isoformat()
            else:
                update_data["returned_at"] = datetime.now().isoformat()
                update_data["failure_reasons"] = json.dumps([comments])
            
            success = await self.bitable.update_task(task_id, update_data)
            
            if success:
                logger.info(f"人工审核完成: {task_id}, 分数: {score}, 状态: {status}")
            
            return success
            
        except Exception as e:
            logger.error(f"人工审核时出错: {str(e)}")
            return False

# 创建全局实例
ci_service = CIService()