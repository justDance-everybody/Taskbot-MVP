import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
from app.config import settings
from app.bitable import FeishuBitableClient, bitable_client
from app.services.feishu import FeishuService
from app.services.llm import llm_service
from app.services.match import MatchService

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 待分配
    ASSIGNED = "assigned"  # 已分配
    IN_PROGRESS = "in_progress"  # 进行中
    SUBMITTED = "submitted"  # 已提交
    REVIEWING = "reviewing"  # 审核中
    COMPLETED = "completed"  # 已完成
    REJECTED = "rejected"  # 已拒绝
    CANCELLED = "cancelled"  # 已取消

class TaskUrgency(Enum):
    """任务紧急程度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.bitable = bitable_client
        self.feishu = FeishuService()
    
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """创建新任务"""
        try:
            # 验证必要字段
            required_fields = ['title', 'description', 'skill_tags', 'deadline']
            for field in required_fields:
                if field not in task_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # 根据新的字段结构设置任务记录
            task_record = {
                'taskid': f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}",  # 生成任务ID
                'title': task_data['title'],
                'description': task_data['description'],
                'skilltags': task_data['skill_tags'],  # 更新字段名
                'deadline': task_data['deadline'],
                'status': TaskStatus.PENDING.value,
                'urgency': task_data.get('urgency', TaskUrgency.NORMAL.value),
                'creator': task_data.get('created_by', task_data.get('creator', '')),
                'create_time': datetime.now().isoformat()  # 更新字段名
            }
            
            # 创建任务记录
            record_id = await self.bitable.create_task(task_record)
            
            logger.info(f"任务创建成功: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            raise
    
    async def _auto_assign_task(self, task_id: str, task_data: Dict[str, Any]):
        """自动分配任务"""
        try:
            # 获取可用候选人
            candidates = await self.bitable.get_available_candidates()
            
            if not candidates:
                logger.warning(f"No candidates available for task {task_id}")
                return
            
            # 使用LLM进行候选人匹配
            match_service = MatchService()
            matches = await match_service.find_top_candidates(task_data, candidates)
            
            if not matches:
                logger.warning(f"No suitable candidates found for task {task_id}")
                return
            
            # 发送任务邀请给Top-3候选人
            for i, match in enumerate(matches[:3]):
                user_id = match['user_id']
                match_score = match['match_score']
                reason = match.get('reason', '')
                
                # 发送任务邀请
                await self.feishu.send_message(
                    user_id=user_id,
                    message=f"您好！有一个新任务邀请：\n\n任务：{task_data['title']}\n描述：{task_data['description']}\n截止时间：{task_data['deadline']}\n匹配度：{match_score}%\n推荐理由：{reason}\n\n您在候选人中排名第{i + 1}位，是否接受此任务？"
                )
                
                logger.info(f"Task invitation sent to {user_id} for task {task_id}")
            
            # 更新任务状态
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.ASSIGNED.value,
                'candidates': [m['user_id'] for m in matches],
                'assigned_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error auto-assigning task {task_id}: {str(e)}")
    
    async def accept_task(self, task_id: str, user_id: str) -> bool:
        """接受任务"""
        try:
            # 获取任务信息
            task = await self.bitable.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # 检查任务状态
            if task['status'] != TaskStatus.ASSIGNED.value:
                raise ValueError(f"Task {task_id} is not available for acceptance")
            
            # 检查用户是否在候选人列表中
            candidates = task.get('candidates', [])
            if user_id not in candidates:
                raise ValueError(f"User {user_id} is not a candidate for task {task_id}")
            
            # 更新任务状态
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.IN_PROGRESS.value,
                'assignee': user_id,
                'accepted_at': datetime.now().isoformat()
            })
            
            # 通知其他候选人任务已被接受
            for candidate_id in candidates:
                if candidate_id != user_id:
                    await self.feishu.send_message(
                        user_id=candidate_id,
                        message=f"任务《{task['title']}》已被其他人接受，感谢您的关注！"
                    )
            
            # 通知任务创建者
            if task.get('created_by'):
                await self.feishu.send_message(
                    user_id=task['created_by'],
                    message=f"您发布的任务《{task['title']}》已被 {user_id} 接受，开始执行！"
                )
            
            logger.info(f"Task {task_id} accepted by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error accepting task {task_id}: {str(e)}")
            return False
    
    async def submit_task(self, task_id: str, user_id: str, submission_url: str, 
                         submission_note: str = "") -> bool:
        """提交任务"""
        try:
            # 获取任务信息
            task = await self.bitable.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            # 检查任务状态和权限
            if task['status'] != TaskStatus.IN_PROGRESS.value:
                raise ValueError(f"Task {task_id} is not in progress")
            
            if task.get('assignee') != user_id:
                raise ValueError(f"User {user_id} is not assigned to task {task_id}")
            
            # 更新任务状态
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.SUBMITTED.value,
                'submission_url': submission_url,
                'submission_note': submission_note,
                'submitted_at': datetime.now().isoformat()
            })
            
            # 更新本地统计
            await self._update_daily_stats()
            
            # 自动质量检查
            await self._auto_quality_check(task_id, task, submission_url)
            
            logger.info(f"Task {task_id} submitted by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting task {task_id}: {str(e)}")
            return False
    
    async def _auto_quality_check(self, task_id: str, task_data: Dict[str, Any], 
                                 submission_url: str):
        """自动质量检查"""
        try:
            # 更新状态为审核中
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.REVIEWING.value,
                'review_started_at': datetime.now().isoformat()
            })
            
            # 使用LLM评估提交内容
            from app.services.ci import CIService
            ci_service = CIService()
            score, failed_reasons = await ci_service.evaluate_submission(
                task_description=task_data['description'],
                acceptance_criteria=task_data.get('acceptance_criteria', ''),
                submission_url=submission_url
            )
            
            # 判断是否通过
            passed = score >= settings.min_pass_score and len(failed_reasons) == 0
            
            if passed:
                # 任务通过
                await self._complete_task(task_id, task_data, score)
            else:
                # 任务需要修改
                await self._reject_task(task_id, task_data, score, failed_reasons)
            
        except Exception as e:
            logger.error(f"Error in quality check for task {task_id}: {str(e)}")
            # 降级到人工审核
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.REVIEWING.value,
                'review_note': f"AI审核失败，需要人工审核: {str(e)}"
            })
    
    async def _complete_task(self, task_id: str, task_data: Dict[str, Any], score: int):
        """完成任务"""
        try:
            assignee = task_data.get('assignee')
            reward_points = task_data.get('reward_points', 100)
            
            # 更新任务状态
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.COMPLETED.value,
                'completed_at': datetime.now().isoformat(),
                'final_score': score,
                'review_result': 'passed'
            })
            
            # 更新本地统计
            await self._update_daily_stats()
            
            # 更新候选人表现
            if assignee:
                await self.bitable.update_candidate_performance(
                    user_id=assignee,
                    completed_tasks=1,
                    total_score=score,
                    reward_points=reward_points
                )
            
            # 发送完成通知
            await self.feishu.send_message(
                user_id=assignee,
                message=f"恭喜！您的任务《{task_data['title']}》已通过验收。\n\n评分：{score}分\n奖励积分：{reward_points}分\n反馈：恭喜！您的任务已通过验收。"
            )
            
            # 通知任务创建者
            if task_data.get('created_by'):
                await self.feishu.send_message(
                    user_id=task_data['created_by'],
                    message=f"您发布的任务《{task_data['title']}》已完成！评分：{score}分"
                )
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {str(e)}")
    
    async def _reject_task(self, task_id: str, task_data: Dict[str, Any], 
                          score: int, failed_reasons: List[str]):
        """拒绝任务"""
        try:
            assignee = task_data.get('assignee')
            
            # 更新任务状态
            await self.bitable.update_task(task_id, {
                'status': TaskStatus.REJECTED.value,
                'rejected_at': datetime.now().isoformat(),
                'final_score': score,
                'review_result': 'failed',
                'failed_reasons': failed_reasons
            })
            
            # 更新本地统计
            await self._update_daily_stats()
            
            # 发送拒绝通知
            feedback = "任务需要修改，请根据以下建议进行调整：\n" + "\n".join(failed_reasons)
            
            await self.feishu.send_message(
                user_id=assignee,
                message=f"您的任务《{task_data['title']}》需要修改。\n\n评分：{score}分\n反馈：{feedback}"
            )
            
            logger.info(f"Task {task_id} rejected with score {score}")
            
        except Exception as e:
            logger.error(f"Error rejecting task {task_id}: {str(e)}")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            return await self.bitable.get_task(task_id)
        except Exception as e:
            logger.error(f"Error getting task status {task_id}: {str(e)}")
            return None
    
    async def get_user_tasks(self, user_id: str, status: str = None) -> List[Dict[str, Any]]:
        """获取用户任务列表"""
        try:
            # 这里需要根据实际的Bitable API实现
            # 暂时返回空列表
            return []
        except Exception as e:
            logger.error(f"Error getting user tasks for {user_id}: {str(e)}")
            return []
    
    async def send_daily_reminders(self):
        """发送每日提醒"""
        try:
            # 获取需要提醒的任务
            # 1. 即将到期的任务
            # 2. 长时间未响应的任务
            # 这里需要根据实际的Bitable API实现查询逻辑
            
            logger.info("Daily reminders sent")
            
        except Exception as e:
            logger.error(f"Error sending daily reminders: {str(e)}")
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """生成每日报告 - 统计数据从JSON文件读取，任务信息从多维表格获取"""
        try:
            import json
            import os
            from datetime import datetime
            
            # 1. 首先从JSON文件读取统计数据
            stats_file = "daily_stats.json"
            base_stats = {}
            
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        base_stats = json.load(f)
                    logger.info(f"从JSON文件读取统计数据: {stats_file}")
                except Exception as e:
                    logger.error(f"读取统计JSON文件失败: {str(e)}")
            
            # 2. 从多维表格获取任务基本信息（用于验证和补充）
            task_info = {}
            try:
                # 只获取任务表的基本信息，不进行复杂统计
                task_stats = await self._get_simple_task_info()
                task_info.update(task_stats)
                logger.info(f"从多维表格获取任务信息: 共{task_info.get('total_records', 0)}条记录")
            except Exception as e:
                logger.error(f"从多维表格获取任务信息失败: {str(e)}")
            
            # 3. 合并统计数据，优先使用JSON文件数据
            report = {
                'date': base_stats.get('date', datetime.now().strftime('%Y-%m-%d')),
                'total_tasks': base_stats.get('total_tasks', task_info.get('valid_records', 0)),
                'completed_tasks': base_stats.get('completed_tasks', 0),
                'pending_tasks': base_stats.get('pending_tasks', 0),
                'in_progress_tasks': base_stats.get('in_progress_tasks', 0),
                'submitted_tasks': base_stats.get('submitted_tasks', 0),
                'reviewing_tasks': base_stats.get('reviewing_tasks', 0),
                'rejected_tasks': base_stats.get('rejected_tasks', 0),
                'assigned_tasks': base_stats.get('assigned_tasks', 0),
                'cancelled_tasks': base_stats.get('cancelled_tasks', 0),
                'average_score': base_stats.get('average_score', 0),
                'completion_rate': base_stats.get('completion_rate', 0),
                'tasks_by_urgency': base_stats.get('tasks_by_urgency', {
                    'urgent': 0, 'high': 0, 'normal': 0, 'low': 0
                }),
                'today_created': base_stats.get('today_created', 0),
                'today_completed': base_stats.get('today_completed', 0),
                'top_performers': base_stats.get('top_performers', []),
                'database_operations': {
                    'total_records': task_info.get('total_records', 0),
                    'valid_records': task_info.get('valid_records', 0),
                    'empty_records': task_info.get('empty_records', 0),
                    'last_updated': datetime.now().isoformat(),
                    'data_source': 'JSON文件 + 多维表格验证'
                }
            }
            
            logger.info(f"日报生成成功: 总任务{report['total_tasks']}, 完成{report['completed_tasks']}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            return {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_tasks': 0, 'completed_tasks': 0, 'pending_tasks': 0,
                'in_progress_tasks': 0, 'submitted_tasks': 0, 'reviewing_tasks': 0,
                'rejected_tasks': 0, 'assigned_tasks': 0, 'cancelled_tasks': 0,
                'average_score': 0, 'completion_rate': 0,
                'tasks_by_urgency': {'urgent': 0, 'high': 0, 'normal': 0, 'low': 0},
                'today_created': 0, 'today_completed': 0, 'top_performers': [],
                'database_operations': {
                    'total_records': 0, 'valid_records': 0, 'empty_records': 0,
                    'last_updated': datetime.now().isoformat(),
                    'error': str(e)
                }
            }
    
    async def _get_simple_task_info(self) -> Dict[str, Any]:
        """从多维表格获取简单的任务信息"""
        try:
            from app.config import settings
            
            # 获取任务表ID
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.warning("未配置任务表ID，无法获取任务信息")
                return {'total_records': 0, 'valid_records': 0, 'empty_records': 0}
            
            # 获取表格记录
            result = self.bitable.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            # 统计基本信息
            total_records = len(records)
            valid_records = 0  # 有有效字段的记录
            empty_records = 0  # 空记录
            
            for record in records:
                fields = record.get('fields', {})
                if fields and any(fields.values()):  # 有非空字段
                    valid_records += 1
                else:
                    empty_records += 1
            
            return {
                'total_records': total_records,
                'valid_records': valid_records,
                'empty_records': empty_records
            }
            
        except Exception as e:
            logger.error(f"获取任务表信息失败: {str(e)}")
            return {'total_records': 0, 'valid_records': 0, 'empty_records': 0}
    
    async def _update_daily_stats(self):
        """更新本地每日统计 - 基于实际操作增量更新"""
        try:
            import json
            import os
            from datetime import datetime
            
            stats_file = "daily_stats.json"
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 读取现有统计数据
            if os.path.exists(stats_file):
                try:
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                except Exception:
                    stats = {}
            else:
                stats = {}
            
            # 确保日期正确
            if stats.get('date') != today:
                # 新的一天，重置部分统计
                stats.update({
                    "date": today,
                    "today_created": 0,
                    "today_completed": 0,
                    "last_updated": datetime.now().isoformat()
                })
            
            # 从多维表格获取最新的有效记录数（用于验证）
            task_info = await self._get_simple_task_info()
            
            # 更新基本统计结构
            default_stats = {
                "date": today,
                "total_tasks": max(stats.get('total_tasks', 0), task_info.get('valid_records', 0)),
                "completed_tasks": stats.get('completed_tasks', 0),
                "pending_tasks": stats.get('pending_tasks', 0),
                "in_progress_tasks": stats.get('in_progress_tasks', 0),
                "submitted_tasks": stats.get('submitted_tasks', 0),
                "reviewing_tasks": stats.get('reviewing_tasks', 0),
                "rejected_tasks": stats.get('rejected_tasks', 0),
                "assigned_tasks": stats.get('assigned_tasks', 0),
                "cancelled_tasks": stats.get('cancelled_tasks', 0),
                "average_score": stats.get('average_score', 0.0),
                "completion_rate": stats.get('completion_rate', 0.0),
                "tasks_by_urgency": stats.get('tasks_by_urgency', {
                    "urgent": 0, "high": 0, "normal": 0, "low": 0
                }),
                "today_created": stats.get('today_created', 0),
                "today_completed": stats.get('today_completed', 0),
                "top_performers": stats.get('top_performers', []),
                "last_updated": datetime.now().isoformat(),
                "database_info": {
                    "total_records": task_info.get('total_records', 0),
                    "valid_records": task_info.get('valid_records', 0),
                    "empty_records": task_info.get('empty_records', 0)
                }
            }
            
            # 合并更新
            stats.update(default_stats)
            
            # 重新计算完成率
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = round(
                    (stats['completed_tasks'] / stats['total_tasks']) * 100, 2
                )
            
            # 写入文件
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"统计数据已更新: 总任务{stats['total_tasks']}, 有效记录{task_info.get('valid_records', 0)}")
            
        except Exception as e:
            logger.error(f"Error updating daily stats: {str(e)}")
    
    async def increment_task_created(self, urgency: str = 'normal'):
        """增量更新：新任务创建"""
        try:
            import json
            import os
            from datetime import datetime
            
            stats_file = "daily_stats.json"
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 读取现有统计
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            else:
                stats = {}
            
            # 更新统计
            stats['total_tasks'] = stats.get('total_tasks', 0) + 1
            stats['pending_tasks'] = stats.get('pending_tasks', 0) + 1
            stats['today_created'] = stats.get('today_created', 0) + 1
            stats['last_updated'] = datetime.now().isoformat()
            stats['date'] = today
            
            # 更新紧急程度统计
            urgency_stats = stats.get('tasks_by_urgency', {})
            urgency_stats[urgency.lower()] = urgency_stats.get(urgency.lower(), 0) + 1
            stats['tasks_by_urgency'] = urgency_stats
            
            # 重新计算完成率
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = round(
                    (stats.get('completed_tasks', 0) / stats['total_tasks']) * 100, 2
                )
            
            # 写入文件
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"新任务统计已更新: 总任务{stats['total_tasks']}, 今日新增{stats['today_created']}")
            
        except Exception as e:
            logger.error(f"增量更新任务统计失败: {str(e)}")
    
    async def complete_task(self, task_id: str, review_data: Dict[str, Any]) -> bool:
        """完成任务（公共接口）"""
        try:
            task = await self.bitable.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            score = review_data.get('final_score', 100)
            await self._complete_task(task_id, task, score)
            return True
            
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {str(e)}")
            return False
    
    async def reject_task(self, task_id: str, review_data: Dict[str, Any]) -> bool:
        """拒绝任务（公共接口）"""
        try:
            task = await self.bitable.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            score = review_data.get('final_score', 0)
            failed_reasons = review_data.get('failed_reasons', ['需要修改'])
            await self._reject_task(task_id, task, score, failed_reasons)
            return True
            
        except Exception as e:
            logger.error(f"Error rejecting task {task_id}: {str(e)}")
            return False

    async def assign_task_to_candidate(self, task_id: str, candidate_id: str) -> bool:
        """将任务分配给指定候选人"""
        try:
            # 更新任务状态为已分配，并设置分配的候选人
            update_data = {
                'status': TaskStatus.ASSIGNED.value,
                'assigned_candidate': candidate_id,
                'assigned_at': datetime.now().isoformat()
            }
            
            success = await self.bitable.update_task(task_id, update_data)
            
            if success:
                # 通知被选中的候选人
                await self.feishu.send_message(
                    user_id=candidate_id,
                    message=f"恭喜！您已被选中执行任务 {task_id}，请及时查看任务详情并开始工作。"
                )
                
                logger.info(f"Task {task_id} assigned to candidate {candidate_id}")
                return True
            else:
                logger.error(f"Failed to assign task {task_id} to candidate {candidate_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error assigning task {task_id} to candidate {candidate_id}: {str(e)}")
            return False

# 全局实例
task_manager = TaskManager()