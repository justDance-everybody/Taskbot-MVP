import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import json
from app.services.llm import llm_service
from app.bitable import bitable_client

logger = logging.getLogger(__name__)

class MatchService:
    """人员匹配服务"""
    
    def __init__(self):
        self.llm = llm_service
        self.bitable = bitable_client
    
    async def find_top_candidates(self, task_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """为任务找到Top-N候选人"""
        try:
            # 获取所有可用候选人
            skill_requirements = task_data.get("skill_tags", [])
            candidates = await self.bitable.get_available_candidates(skill_requirements)
            
            if not candidates:
                logger.warning("没有找到可用的候选人")
                return []
            
            # 使用LLM进行智能匹配
            matched_candidates = await self._llm_match_candidates(task_data, candidates)
            
            # 按匹配分数排序并返回Top-N
            sorted_candidates = sorted(matched_candidates, key=lambda x: x.get("match_score", 0), reverse=True)
            return sorted_candidates[:limit]
            
        except Exception as e:
            logger.error(f"匹配候选人时出错: {str(e)}")
            return []
    
    async def _llm_match_candidates(self, task_data: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用LLM进行候选人匹配"""
        try:
            # 构建匹配提示词
            system_prompt = self._build_match_system_prompt()
            user_prompt = self._build_match_user_prompt(task_data, candidates)
            
            # 调用LLM
            response = await self.llm.call(user_prompt, system_prompt)
            
            # 解析LLM响应
            match_results = self._parse_match_response(response, candidates)
            
            return match_results
            
        except Exception as e:
            logger.error(f"LLM匹配时出错: {str(e)}")
            # 降级到基础匹配算法
            return self._basic_match_candidates(task_data, candidates)
    
    def _build_match_system_prompt(self) -> str:
        """构建匹配系统提示词"""
        return """
你是智能人才匹配助手，负责为任务匹配最合适的候选人。

匹配原则：
1. 技能匹配度：候选人的技能标签与任务需求的匹配程度
2. 可用性：候选人的可用工时是否满足任务需求
3. 历史表现：候选人的绩效评分和完成任务的历史记录
4. 工作负载：候选人当前的工作负载情况
5. 紧急程度：任务的紧急程度与候选人的响应能力

请为每个候选人计算匹配分数（0-100），并提供匹配理由。
"""
    
    def _build_match_user_prompt(self, task_data: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
        """构建匹配用户提示词"""
        task_info = f"""
任务信息：
- 标题：{task_data.get('title', '')}
- 描述：{task_data.get('description', '')}
- 技能要求：{', '.join(task_data.get('skill_tags', []))}
- 截止时间：{task_data.get('deadline', '')}
- 紧急程度：{task_data.get('urgency', 'normal')}
"""
        
        candidates_info = "候选人列表：\n"
        for i, candidate in enumerate(candidates, 1):
            candidates_info += f"""
{i}. 候选人ID: {candidate.get('user_id', '')}
   姓名: {candidate.get('name', '')}
   技能标签: {', '.join(candidate.get('skill_tags', []))}
   职级: {candidate.get('job_level', '')}
   经验年数: {candidate.get('experience', 0)}
   总任务数: {candidate.get('total_tasks', 0)}
   平均评分: {candidate.get('average_score', 0)}
"""
        
        return f"""
{task_info}

{candidates_info}

请返回JSON格式的匹配结果，包含每个候选人的user_id、match_score(0-100)和match_reason：
{{
  "matches": [
    {{
      "user_id": "候选人ID",
      "match_score": 85,
      "match_reason": "匹配理由"
    }}
  ]
}}
"""
    
    def _parse_match_response(self, response: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析LLM匹配响应"""
        try:
            # 尝试解析JSON响应
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            match_data = json.loads(json_str)
            matches = match_data.get("matches", [])
            
            # 将匹配结果与候选人信息合并
            result = []
            for match in matches:
                user_id = match.get("user_id")
                candidate = next((c for c in candidates if c.get("user_id") == user_id), None)
                if candidate:
                    candidate_copy = candidate.copy()
                    candidate_copy["match_score"] = match.get("match_score", 0)
                    candidate_copy["match_reason"] = match.get("match_reason", "")
                    result.append(candidate_copy)
            
            return result
            
        except Exception as e:
            logger.error(f"解析LLM匹配响应时出错: {str(e)}")
            # 降级到基础匹配
            return self._basic_match_candidates({}, candidates)
    
    def _basic_match_candidates(self, task_data: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基础匹配算法（降级方案）"""
        try:
            skill_requirements = set(task_data.get("skill_tags", []))
            
            for candidate in candidates:
                candidate_skills = set(candidate.get("skill_tags", []))
                
                # 计算技能匹配度
                if skill_requirements:
                    skill_match = len(skill_requirements & candidate_skills) / len(skill_requirements)
                else:
                    skill_match = 1.0
                
                # 计算平均评分分数 (0-100 -> 0-1)
                avg_score = candidate.get("average_score", 0) / 100.0
                
                # 计算经验分数 (年数转换为评分)
                experience_years = candidate.get("experience", 0)
                experience_score = min(experience_years / 5.0, 1.0)  # 5年经验为满分
                
                # 综合评分
                match_score = int((skill_match * 0.4 + avg_score * 0.4 + experience_score * 0.2) * 100)
                
                candidate["match_score"] = match_score
                candidate["match_reason"] = f"技能匹配度: {skill_match:.1%}, 平均评分: {avg_score:.1%}, 经验: {experience_score:.1%}"
            
            return candidates
            
        except Exception as e:
            logger.error(f"基础匹配算法出错: {str(e)}")
            return candidates
    
    async def calculate_match_score(self, task_data: Dict[str, Any], candidate: Dict[str, Any]) -> Tuple[int, str]:
        """计算单个候选人的匹配分数"""
        try:
            skill_requirements = set(task_data.get("skill_tags", []))
            candidate_skills = set(candidate.get("skill_tags", []))
            
            # 技能匹配度 (40%)
            if skill_requirements:
                skill_match = len(skill_requirements & candidate_skills) / len(skill_requirements)
            else:
                skill_match = 1.0
            
            # 平均评分 (40%)
            avg_score = candidate.get("average_score", 0) / 100.0
            
            # 经验匹配度 (20%)
            experience_years = candidate.get("experience", 0)
            experience_score = min(experience_years / 5.0, 1.0)  # 5年经验为满分
            
            # 综合评分
            total_score = int((skill_match * 0.4 + avg_score * 0.4 + experience_score * 0.2) * 100)
            
            # 生成匹配理由
            reason = f"技能匹配: {skill_match:.1%}, 平均评分: {avg_score:.1%}, 经验: {experience_score:.1%}"
            
            return total_score, reason
            
        except Exception as e:
            logger.error(f"计算匹配分数时出错: {str(e)}")
            return 50, "计算出错，使用默认分数"

# 创建全局实例
match_service = MatchService()