"""
任务监测模块

功能：
1. 监测当前任务进度
2. 检查任务周期是否过半
3. 发送提醒消息
4. 定时检查任务状态
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.services.feishu import feishu_service

logger = logging.getLogger(__name__)

class TaskMonitor:
    """任务监测器"""
    
    def __init__(self):
        """初始化任务监测器"""
        self.monitoring = False
        self.check_interval = 3600  # 每小时检查一次（秒）
        self.reminded_tasks = set()  # 已提醒的任务ID
    
    async def start_monitoring(self):
        """开始监测任务"""
        if self.monitoring:
            logger.info("任务监测已在运行中")
            return
        
        self.monitoring = True
        logger.info("开始任务监测服务")
        
        while self.monitoring:
            try:
                await self.check_all_tasks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"任务监测出错: {str(e)}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试
    
    async def stop_monitoring(self):
        """停止监测任务"""
        self.monitoring = False
        logger.info("任务监测服务已停止")
    
    async def check_all_tasks(self):
        """检查所有需要监测的任务"""
        try:
            from app.bitable import bitable_client
            from app.config import settings
            
            # 获取任务表ID
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.warning("未配置任务表ID，跳过任务监测")
                return
            
            # 获取所有进行中和已分配的任务
            result = bitable_client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            monitored_count = 0
            reminded_count = 0
            
            for record in records:
                fields = record.get('fields', {})
                if not fields:
                    continue
                
                status = fields.get('status', '').lower()
                # 只监测进行中和已分配的任务
                if status in ['in_progress', 'assigned', 'in progress']:
                    monitored_count += 1
                    reminded = await self.check_task_deadline(fields)
                    if reminded:
                        reminded_count += 1
            
            if monitored_count > 0:
                logger.info(f"监测了 {monitored_count} 个任务，发送了 {reminded_count} 个提醒")
            
        except Exception as e:
            logger.error(f"检查任务时出错: {str(e)}")
    
    async def check_task_deadline(self, task_data: Dict[str, Any]) -> bool:
        """检查单个任务的截止时间"""
        try:
            task_id = task_data.get('taskid', '')
            title = task_data.get('title', '未知任务')
            deadline_str = task_data.get('deadline', '')
            create_time_str = task_data.get('create_time', '')
            assignee = task_data.get('assignee', task_data.get('assigned_candidate', ''))
            creator = task_data.get('creator', '')
            
            if not deadline_str or not create_time_str:
                return False
            
            # 解析时间
            deadline = self._parse_datetime(deadline_str)
            create_time = self._parse_datetime(create_time_str)
            
            if not deadline or not create_time:
                return False
            
            # 计算任务周期和当前进度
            now = datetime.now()
            total_duration = (deadline - create_time).total_seconds()
            elapsed_duration = (now - create_time).total_seconds()
            
            if total_duration <= 0:
                return False
            
            progress_ratio = elapsed_duration / total_duration
            
            # 检查是否超过一半周期且未提醒过
            if progress_ratio >= 0.5 and task_id not in self.reminded_tasks:
                await self._send_reminder(task_data, progress_ratio, deadline)
                self.reminded_tasks.add(task_id)
                return True
            
            # 检查是否临近截止时间（最后24小时）
            time_remaining = (deadline - now).total_seconds()
            if time_remaining <= 86400 and time_remaining > 0:  # 24小时 = 86400秒
                reminder_key = f"{task_id}_final"
                if reminder_key not in self.reminded_tasks:
                    await self._send_final_reminder(task_data, time_remaining)
                    self.reminded_tasks.add(reminder_key)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查任务截止时间出错: {str(e)}")
            return False
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        try:
            # 支持多种日期格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y.%m.%d %H:%M',
                '%Y.%m.%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            logger.warning(f"无法解析日期格式: {date_str}")
            return None
            
        except Exception as e:
            logger.error(f"解析日期时出错: {str(e)}")
            return None
    
    async def _send_reminder(self, task_data: Dict[str, Any], progress_ratio: float, deadline: datetime):
        """发送周期过半提醒"""
        try:
            task_id = task_data.get('taskid', '')
            title = task_data.get('title', '未知任务')
            assignee = task_data.get('assignee', task_data.get('assigned_candidate', ''))
            creator = task_data.get('creator', '')
            
            # 计算剩余时间
            now = datetime.now()
            time_remaining = (deadline - now).total_seconds()
            days_remaining = int(time_remaining // 86400)
            hours_remaining = int((time_remaining % 86400) // 3600)
            
            # 构建提醒消息
            progress_percent = round(progress_ratio * 100, 1)
            
            reminder_message = f"""⏰ **任务进度提醒**

📋 **任务信息**:
• 任务ID: {task_id}
• 任务标题: {title}
• 当前进度: {progress_percent}% (已过半)

⏳ **时间提醒**:
• 剩余时间: {days_remaining}天 {hours_remaining}小时
• 截止时间: {deadline.strftime('%Y-%m-%d %H:%M')}

💡 **温馨提示**:
任务周期已过半，请注意把控进度，确保按时完成！

如有问题请及时沟通协调。"""
            
            # 发送给执行人
            if assignee:
                await feishu_service.send_message(
                    user_id=assignee,
                    message=reminder_message
                )
                logger.info(f"已向执行人 {assignee} 发送任务提醒: {task_id}")
            
            # 发送给创建者
            if creator and creator != assignee:
                creator_message = f"""📊 **任务进度通知**

您创建的任务进度已过半：

📋 **任务**: {title} ({task_id})
⏳ **剩余时间**: {days_remaining}天 {hours_remaining}小时
👤 **执行人**: {assignee if assignee else '未分配'}

已向执行人发送提醒消息。"""
                
                await feishu_service.send_message(
                    user_id=creator,
                    message=creator_message
                )
                logger.info(f"已向创建者 {creator} 发送任务通知: {task_id}")
            
        except Exception as e:
            logger.error(f"发送提醒消息失败: {str(e)}")
    
    async def _send_final_reminder(self, task_data: Dict[str, Any], time_remaining: float):
        """发送最后期限提醒"""
        try:
            task_id = task_data.get('taskid', '')
            title = task_data.get('title', '未知任务')
            assignee = task_data.get('assignee', task_data.get('assigned_candidate', ''))
            creator = task_data.get('creator', '')
            
            hours_remaining = int(time_remaining // 3600)
            
            urgent_message = f"""🚨 **紧急任务提醒**

📋 **任务信息**:
• 任务ID: {task_id}
• 任务标题: {title}

⚠️ **紧急提醒**:
• 剩余时间: 仅剩 {hours_remaining} 小时！
• 即将到达截止时间

🔥 **请立即行动**:
请尽快完成任务或联系相关人员协调延期！"""
            
            # 发送给执行人
            if assignee:
                await feishu_service.send_message(
                    user_id=assignee,
                    message=urgent_message
                )
            
            # 发送给创建者
            if creator and creator != assignee:
                await feishu_service.send_message(
                    user_id=creator,
                    message=urgent_message.replace("请立即行动", "请关注任务进度")
                )
            
            logger.info(f"已发送最后期限提醒: {task_id}")
            
        except Exception as e:
            logger.error(f"发送最后期限提醒失败: {str(e)}")
    
    async def test_monitoring(self, task_id: str = None) -> Dict[str, Any]:
        """测试监测功能"""
        try:
            from app.bitable import bitable_client
            from app.config import settings
            
            result = {
                'tested_tasks': 0,
                'reminder_sent': 0,
                'tasks_details': [],
                'status': 'success'
            }
            
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                result['status'] = 'error'
                result['message'] = '未配置任务表ID'
                return result
            
            # 获取任务记录
            table_result = bitable_client.get_table_records(task_table_id)
            records = table_result.get('data', {}).get('items', [])
            
            for record in records:
                fields = record.get('fields', {})
                if not fields:
                    continue
                
                current_task_id = fields.get('taskid', '')
                status = fields.get('status', '').lower()
                
                # 如果指定了task_id，只测试该任务
                if task_id and current_task_id != task_id:
                    continue
                
                # 只测试进行中和已分配的任务
                if status in ['in_progress', 'assigned', 'in progress']:
                    result['tested_tasks'] += 1
                    
                    # 强制检查并发送提醒（测试模式）
                    task_details = await self._test_single_task(fields)
                    result['tasks_details'].append(task_details)
                    
                    if task_details.get('reminder_sent'):
                        result['reminder_sent'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"测试监测功能失败: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'tested_tasks': 0,
                'reminder_sent': 0
            }
    
    async def _test_single_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """测试单个任务"""
        try:
            task_id = task_data.get('taskid', '')
            title = task_data.get('title', '未知任务')
            deadline_str = task_data.get('deadline', '')
            create_time_str = task_data.get('create_time', '')
            
            result = {
                'task_id': task_id,
                'title': title,
                'reminder_sent': False,
                'progress_ratio': 0,
                'time_remaining': 0,
                'status': 'checked'
            }
            
            if not deadline_str or not create_time_str:
                result['status'] = 'missing_time_data'
                return result
            
            deadline = self._parse_datetime(deadline_str)
            create_time = self._parse_datetime(create_time_str)
            
            if not deadline or not create_time:
                result['status'] = 'invalid_time_format'
                return result
            
            # 计算进度
            now = datetime.now()
            total_duration = (deadline - create_time).total_seconds()
            elapsed_duration = (now - create_time).total_seconds()
            
            if total_duration > 0:
                result['progress_ratio'] = round(elapsed_duration / total_duration, 3)
                result['time_remaining'] = int((deadline - now).total_seconds())
                
                # 在测试模式下，如果进度超过30%就发送提醒
                if result['progress_ratio'] >= 0.3:
                    await self._send_test_reminder(task_data, result['progress_ratio'], deadline)
                    result['reminder_sent'] = True
                    result['status'] = 'reminder_sent'
            
            return result
            
        except Exception as e:
            logger.error(f"测试单个任务失败: {str(e)}")
            return {
                'task_id': task_data.get('taskid', ''),
                'title': task_data.get('title', ''),
                'status': 'error',
                'error': str(e)
            }
    
    async def _send_test_reminder(self, task_data: Dict[str, Any], progress_ratio: float, deadline: datetime):
        """发送测试提醒消息"""
        try:
            task_id = task_data.get('taskid', '')
            title = task_data.get('title', '未知任务')
            assignee = task_data.get('assignee', task_data.get('assigned_candidate', ''))
            creator = task_data.get('creator', '')
            
            now = datetime.now()
            time_remaining = (deadline - now).total_seconds()
            days_remaining = int(time_remaining // 86400)
            hours_remaining = int((time_remaining % 86400) // 3600)
            
            progress_percent = round(progress_ratio * 100, 1)
            
            test_message = f"""🧪 **任务监测测试**

📋 **任务信息**:
• 任务ID: {task_id}
• 任务标题: {title}
• 当前进度: {progress_percent}%

⏳ **时间信息**:
• 剩余时间: {days_remaining}天 {hours_remaining}小时
• 截止时间: {deadline.strftime('%Y-%m-%d %H:%M')}

💡 **这是一条测试消息**:
任务监测功能正常工作！实际提醒将在任务周期过半时发送。

---
🔬 测试时间: {now.strftime('%Y-%m-%d %H:%M:%S')}"""
            
            # 发送给执行人
            if assignee:
                await feishu_service.send_message(
                    user_id=assignee,
                    message=test_message
                )
            
            # 发送给创建者
            if creator and creator != assignee:
                await feishu_service.send_message(
                    user_id=creator,
                    message=test_message
                )
            
            logger.info(f"已发送测试提醒: {task_id}")
            
        except Exception as e:
            logger.error(f"发送测试提醒失败: {str(e)}")

# 全局任务监测器实例
task_monitor = TaskMonitor() 