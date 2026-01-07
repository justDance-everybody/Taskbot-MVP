"""定时任务调度模块"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.config import settings
from app.bitable import bitable_client, BitableClient
from app.services.feishu import FeishuService

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 负责周期性任务执行"""
    
    def __init__(self):
        """初始化调度器"""
        self.bitable = BitableClient()
        self.feishu = FeishuService()
        self.running = False
        self._tasks = []
        logger.info("TaskScheduler initialized")
    
    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("TaskScheduler started")
        
        # 启动周期性任务
        self._tasks = [
            asyncio.create_task(self._run_deadline_reminders()),
            asyncio.create_task(self._run_archiving())
        ]
    
    async def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping TaskScheduler...")
        
        # 取消所有任务
        for task in self._tasks:
            task.cancel()
        
        # 等待任务取消完成
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("TaskScheduler stopped")
    
    async def _run_deadline_reminders(self):
        """运行周期过半提醒检查（每小时）"""
        while self.running:
            try:
                await self.check_deadline_reminders()
                # 等待1小时
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in deadline reminders task: {str(e)}")
                await asyncio.sleep(300)  # 出错时等待5分钟后重试
    
    async def _run_archiving(self):
        """运行归档检查（每天）"""
        while self.running:
            try:
                await self.archive_completed_tasks()
                # 等待24小时
                await asyncio.sleep(86400)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in archiving task: {str(e)}")
                await asyncio.sleep(3600)  # 出错时等待1小时后重试
    
    def _is_past_half_deadline(self, task: Dict[str, Any]) -> bool:
        """判断任务是否已过半周期
        
        Args:
            task: 任务数据字典
            
        Returns:
            是否已过半周期
        """
        try:
            # 获取任务创建时间和截止时间
            create_time_str = task.get('create_time', '')
            deadline_str = task.get('deadline', '')
            
            if not create_time_str or not deadline_str:
                logger.warning(f"Task {task.get('taskid', 'Unknown')} missing create_time or deadline")
                return False
            
            # 解析时间字符串
            # 支持多种时间格式
            time_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f'
            ]
            
            created = None
            deadline = None
            
            for fmt in time_formats:
                try:
                    created = datetime.strptime(create_time_str, fmt)
                    break
                except ValueError:
                    continue
            
            for fmt in time_formats:
                try:
                    deadline = datetime.strptime(deadline_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not created or not deadline:
                logger.warning(f"Failed to parse dates for task {task.get('taskid', 'Unknown')}")
                return False
            
            # 计算总时间跨度和半程时间点
            total_span = deadline - created
            half_point = created + total_span / 2
            
            # 判断当前时间是否已过半程
            now = datetime.now()
            is_past_half = now >= half_point
            
            if is_past_half:
                logger.info(f"Task {task.get('taskid', 'Unknown')} is past half deadline")
            
            return is_past_half
            
        except Exception as e:
            logger.error(f"Error checking half deadline for task {task.get('taskid', 'Unknown')}: {str(e)}")
            return False
    
    async def check_deadline_reminders(self):
        """检查需要提醒的任务
        
        遍历所有进行中的任务，对于已过半周期且未提醒的任务发送提醒
        """
        try:
            logger.info("Checking deadline reminders...")
            
            # 获取所有进行中的任务
            tasks = await self._get_in_progress_tasks()
            
            if not tasks:
                logger.info("No in-progress tasks found")
                return
            
            reminder_count = 0
            
            for task in tasks:
                try:
                    # 检查是否已提醒过
                    if task.get('reminded'):
                        continue
                    
                    # 检查是否已过半周期
                    if not self._is_past_half_deadline(task):
                        continue
                    
                    # 发送提醒
                    await self._send_reminder(task)
                    
                    # 标记为已提醒
                    await self._mark_reminded(task)
                    
                    reminder_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing reminder for task {task.get('taskid', 'Unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Sent {reminder_count} deadline reminders")
            
        except Exception as e:
            logger.error(f"Error in check_deadline_reminders: {str(e)}")
    
    async def _get_in_progress_tasks(self) -> List[Dict[str, Any]]:
        """获取所有进行中的任务
        
        Returns:
            进行中的任务列表
        """
        try:
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("Task table ID not configured")
                return []
            
            # 获取所有任务记录
            result = bitable_client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            # 筛选进行中的任务
            in_progress_tasks = []
            for record in records:
                fields = record.get('fields', {})
                if not fields:
                    continue
                
                status = fields.get('status', '').lower()
                if status == 'in_progress':
                    # 添加记录ID以便后续更新
                    task_data = {
                        'record_id': record.get('record_id'),
                        **fields
                    }
                    in_progress_tasks.append(task_data)
            
            logger.info(f"Found {len(in_progress_tasks)} in-progress tasks")
            return in_progress_tasks
            
        except Exception as e:
            logger.error(f"Error getting in-progress tasks: {str(e)}")
            return []
    
    async def _send_reminder(self, task: Dict[str, Any]):
        """发送提醒消息
        
        Args:
            task: 任务数据
        """
        try:
            task_id = task.get('taskid', 'Unknown')
            title = task.get('title', '未知任务')
            deadline = task.get('deadline', '未知')
            assignee = task.get('assignee', '')
            creator = task.get('creator', '')
            
            # 构建提醒消息
            reminder_message = (
                f"⏰ 任务进度提醒\n\n"
                f"任务: {title}\n"
                f"任务ID: {task_id}\n"
                f"截止时间: {deadline}\n\n"
                f"该任务已过半周期，请注意按时完成！"
            )
            
            # 发送给任务执行者
            if assignee:
                await self.feishu.send_message(user_id=assignee, message=reminder_message)
                logger.info(f"Reminder sent to assignee {assignee} for task {task_id}")
            
            # 发送给任务创建者（HR）
            if creator and creator != assignee:
                hr_message = (
                    f"📊 任务进度通知\n\n"
                    f"任务: {title}\n"
                    f"任务ID: {task_id}\n"
                    f"执行者: {assignee}\n"
                    f"截止时间: {deadline}\n\n"
                    f"该任务已过半周期，请关注进度。"
                )
                await self.feishu.send_message(user_id=creator, message=hr_message)
                logger.info(f"Reminder sent to creator {creator} for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error sending reminder for task {task.get('taskid', 'Unknown')}: {str(e)}")
    
    async def _mark_reminded(self, task: Dict[str, Any]):
        """标记任务为已提醒
        
        Args:
            task: 任务数据
        """
        try:
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("Task table ID not configured")
                return
            
            record_id = task.get('record_id')
            if not record_id:
                logger.error(f"No record_id for task {task.get('taskid', 'Unknown')}")
                return
            
            # 更新任务记录，添加reminded标记
            update_data = {
                "fields": {
                    "reminded": True,
                    "reminded_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            bitable_client.update_record(task_table_id, record_id, update_data)
            logger.info(f"Task {task.get('taskid', 'Unknown')} marked as reminded")
            
        except Exception as e:
            logger.error(f"Error marking task as reminded: {str(e)}")
    
    async def archive_completed_tasks(self):
        """归档完成超过7天的任务
        
        遍历所有已完成的任务，对于完成超过7天的任务进行归档处理
        """
        try:
            logger.info("Checking tasks for archiving...")
            
            # 获取所有已完成的任务
            completed_tasks = await self._get_completed_tasks()
            
            if not completed_tasks:
                logger.info("No completed tasks found")
                return
            
            archive_count = 0
            now = datetime.now()
            
            for task in completed_tasks:
                try:
                    # 检查完成时间
                    completed_at_str = task.get('completed_at', '')
                    if not completed_at_str:
                        continue
                    
                    # 解析完成时间
                    completed_at = None
                    time_formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d',
                        '%Y-%m-%dT%H:%M:%S',
                        '%Y-%m-%dT%H:%M:%S.%f'
                    ]
                    
                    for fmt in time_formats:
                        try:
                            completed_at = datetime.strptime(completed_at_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not completed_at:
                        logger.warning(f"Failed to parse completed_at for task {task.get('taskid', 'Unknown')}")
                        continue
                    
                    # 计算完成后的天数
                    days_since_completion = (now - completed_at).days
                    
                    # 如果完成超过7天，进行归档
                    if days_since_completion >= 7:
                        await self._archive_task(task)
                        archive_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing archive for task {task.get('taskid', 'Unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Archived {archive_count} completed tasks")
            
        except Exception as e:
            logger.error(f"Error in archive_completed_tasks: {str(e)}")
    
    async def _get_completed_tasks(self) -> List[Dict[str, Any]]:
        """获取所有已完成的任务
        
        Returns:
            已完成的任务列表
        """
        try:
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("Task table ID not configured")
                return []
            
            # 获取所有任务记录
            result = bitable_client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            # 筛选已完成的任务
            completed_tasks = []
            for record in records:
                fields = record.get('fields', {})
                if not fields:
                    continue
                
                status = fields.get('status', '').lower()
                if status == 'completed':
                    # 添加记录ID以便后续更新
                    task_data = {
                        'record_id': record.get('record_id'),
                        **fields
                    }
                    completed_tasks.append(task_data)
            
            logger.info(f"Found {len(completed_tasks)} completed tasks")
            return completed_tasks
            
        except Exception as e:
            logger.error(f"Error getting completed tasks: {str(e)}")
            return []
    
    async def _archive_task(self, task: Dict[str, Any]):
        """归档任务
        
        Args:
            task: 任务数据
        """
        try:
            task_id = task.get('taskid', 'Unknown')
            chat_id = task.get('chat_id', '')
            
            # 1. 重命名群聊为 [ARCHIVED] 前缀
            if chat_id:
                await self._rename_chat_to_archived(chat_id, task)
            
            # 2. 移除机器人从群聊
            if chat_id:
                await self._remove_bot_from_chat(chat_id)
            
            # 3. 更新任务状态为已归档
            await self._mark_task_archived(task)
            
            logger.info(f"Task {task_id} archived successfully")
            
        except Exception as e:
            logger.error(f"Error archiving task {task.get('taskid', 'Unknown')}: {str(e)}")
    
    async def _rename_chat_to_archived(self, chat_id: str, task: Dict[str, Any]):
        """重命名群聊为 [ARCHIVED] 前缀
        
        Args:
            chat_id: 群聊ID
            task: 任务数据
        """
        try:
            import httpx
            
            # 获取访问令牌
            access_token = await self.feishu._get_access_token()
            if not access_token:
                logger.error("Failed to get access token for renaming chat")
                return
            
            # 获取当前群聊名称
            title = task.get('title', '未知任务')
            
            # 如果已经有 [ARCHIVED] 前缀，不重复添加
            if title.startswith('[ARCHIVED]'):
                logger.info(f"Chat {chat_id} already has [ARCHIVED] prefix")
                return
            
            # 构建新的群聊名称
            new_name = f"[ARCHIVED] {title}"
            
            # 构建请求
            url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            payload = {
                "name": new_name
            }
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        logger.info(f"Chat {chat_id} renamed to: {new_name}")
                    else:
                        logger.error(f"Failed to rename chat: {result.get('msg')}")
                else:
                    logger.error(f"HTTP error renaming chat: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error renaming chat {chat_id}: {str(e)}")
    
    async def _remove_bot_from_chat(self, chat_id: str):
        """移除机器人从群聊
        
        Args:
            chat_id: 群聊ID
        """
        try:
            import httpx
            
            # 获取访问令牌
            access_token = await self.feishu._get_access_token()
            if not access_token:
                logger.error("Failed to get access token for removing bot")
                return
            
            # 获取机器人的 open_id
            # 注意：这里需要先获取机器人自己的 open_id
            # 简化实现：直接调用删除成员API，飞书会自动处理
            
            url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members/me_delete"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        logger.info(f"Bot removed from chat {chat_id}")
                    else:
                        logger.error(f"Failed to remove bot from chat: {result.get('msg')}")
                else:
                    logger.error(f"HTTP error removing bot: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Error removing bot from chat {chat_id}: {str(e)}")
    
    async def _mark_task_archived(self, task: Dict[str, Any]):
        """标记任务为已归档
        
        Args:
            task: 任务数据
        """
        try:
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("Task table ID not configured")
                return
            
            record_id = task.get('record_id')
            if not record_id:
                logger.error(f"No record_id for task {task.get('taskid', 'Unknown')}")
                return
            
            # 更新任务记录，标记为已归档
            update_data = {
                "fields": {
                    "archived": True,
                    "archived_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            bitable_client.update_record(task_table_id, record_id, update_data)
            logger.info(f"Task {task.get('taskid', 'Unknown')} marked as archived")
            
        except Exception as e:
            logger.error(f"Error marking task as archived: {str(e)}")


# 全局调度器实例
task_scheduler = TaskScheduler()
