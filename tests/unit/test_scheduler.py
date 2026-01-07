"""
Scheduler 单元测试
测试周期计算逻辑、提醒状态持久化和归档条件判断
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.scheduler import TaskScheduler, task_scheduler


class TestDeadlineCalculation:
    """测试周期计算逻辑"""
    
    def test_is_past_half_deadline_true(self):
        """测试已过半周期的任务"""
        # 创建时间：10天前，截止时间：今天，已过半周期
        now = datetime.now()
        created = now - timedelta(days=10)
        deadline = now
        
        task = {
            "taskid": "TASK001",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 验证已过半周期
        assert result is True
    
    def test_is_past_half_deadline_false(self):
        """测试未过半周期的任务"""
        # 创建时间：1天前，截止时间：10天后，未过半周期
        now = datetime.now()
        created = now - timedelta(days=1)
        deadline = now + timedelta(days=10)
        
        task = {
            "taskid": "TASK002",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 验证未过半周期
        assert result is False
    
    def test_is_past_half_deadline_exactly_half(self):
        """测试恰好在半周期的任务"""
        # 创建时间：5天前，截止时间：5天后，恰好半周期
        now = datetime.now()
        created = now - timedelta(days=5)
        deadline = now + timedelta(days=5)
        
        task = {
            "taskid": "TASK003",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 验证恰好在半周期时返回True（>=判断）
        assert result is True
    
    def test_is_past_half_deadline_missing_dates(self):
        """测试缺少日期字段的任务"""
        task = {
            "taskid": "TASK004"
            # 缺少create_time和deadline
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 验证缺少日期时返回False
        assert result is False
    
    def test_is_past_half_deadline_invalid_date_format(self):
        """测试无效日期格式"""
        task = {
            "taskid": "TASK005",
            "create_time": "invalid-date",
            "deadline": "invalid-date"
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 验证无效日期格式时返回False
        assert result is False
    
    def test_is_past_half_deadline_different_formats(self):
        """测试支持多种日期格式"""
        now = datetime.now()
        created = now - timedelta(days=10)
        deadline = now
        
        # 测试ISO格式
        task_iso = {
            "taskid": "TASK006",
            "create_time": created.isoformat(),
            "deadline": deadline.isoformat()
        }
        
        scheduler = TaskScheduler()
        result_iso = scheduler._is_past_half_deadline(task_iso)
        assert result_iso is True
        
        # 测试日期格式（无时间）
        task_date = {
            "taskid": "TASK007",
            "create_time": created.strftime('%Y-%m-%d'),
            "deadline": deadline.strftime('%Y-%m-%d')
        }
        
        result_date = scheduler._is_past_half_deadline(task_date)
        assert result_date is True


class TestReminderPersistence:
    """测试提醒状态持久化"""
    
    @pytest.mark.asyncio
    async def test_mark_reminded_updates_database(self):
        """测试标记提醒更新数据库"""
        task = {
            "taskid": "TASK001",
            "record_id": "rec123",
            "title": "测试任务"
        }
        
        scheduler = TaskScheduler()
        
        with patch('app.services.scheduler.bitable_client') as mock_bitable:
            with patch('app.services.scheduler.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                await scheduler._mark_reminded(task)
        
        # 验证调用了update_record
        mock_bitable.update_record.assert_called_once()
        call_args = mock_bitable.update_record.call_args[0]
        assert call_args[0] == "tbl123"  # table_id
        assert call_args[1] == "rec123"  # record_id
        
        # 验证更新数据包含reminded标记
        update_data = call_args[2]
        assert update_data["fields"]["reminded"] is True
        assert "reminded_at" in update_data["fields"]
    
    @pytest.mark.asyncio
    async def test_mark_reminded_without_record_id(self):
        """测试没有record_id时的处理"""
        task = {
            "taskid": "TASK002",
            "title": "测试任务"
            # 缺少record_id
        }
        
        scheduler = TaskScheduler()
        
        with patch('app.services.scheduler.bitable_client') as mock_bitable:
            with patch('app.services.scheduler.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                await scheduler._mark_reminded(task)
        
        # 验证没有调用update_record
        mock_bitable.update_record.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_deadline_reminders_skips_reminded_tasks(self):
        """测试跳过已提醒的任务"""
        # 模拟已提醒的任务
        mock_tasks = [
            {
                "taskid": "TASK001",
                "record_id": "rec123",
                "reminded": True,  # 已提醒
                "create_time": (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
                "deadline": datetime.now().strftime('%Y-%m-%d')
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_in_progress_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_send_reminder', 
                            new_callable=AsyncMock) as mock_send:
                await scheduler.check_deadline_reminders()
        
        # 验证没有发送提醒
        mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_deadline_reminders_sends_for_unreminded_tasks(self):
        """测试为未提醒的任务发送提醒"""
        # 模拟未提醒且已过半周期的任务
        now = datetime.now()
        mock_tasks = [
            {
                "taskid": "TASK002",
                "record_id": "rec456",
                "reminded": False,  # 未提醒
                "create_time": (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": now.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "测试任务",
                "assignee": "user123",
                "creator": "user456"
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_in_progress_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_send_reminder', 
                            new_callable=AsyncMock) as mock_send:
                with patch.object(scheduler, '_mark_reminded', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler.check_deadline_reminders()
        
        # 验证发送了提醒
        mock_send.assert_called_once()
        # 验证标记为已提醒
        mock_mark.assert_called_once()


class TestArchiveConditions:
    """测试归档条件判断"""
    
    @pytest.mark.asyncio
    async def test_archive_completed_tasks_after_7_days(self):
        """测试完成7天后归档"""
        # 模拟完成8天的任务
        completed_at = datetime.now() - timedelta(days=8)
        mock_tasks = [
            {
                "taskid": "TASK001",
                "record_id": "rec123",
                "status": "completed",
                "completed_at": completed_at.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "测试任务",
                "chat_id": "chat123"
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_archive_task', 
                            new_callable=AsyncMock) as mock_archive:
                await scheduler.archive_completed_tasks()
        
        # 验证调用了归档
        mock_archive.assert_called_once()
        assert mock_archive.call_args[0][0]["taskid"] == "TASK001"
    
    @pytest.mark.asyncio
    async def test_archive_not_before_7_days(self):
        """测试完成不足7天不归档"""
        # 模拟完成5天的任务
        completed_at = datetime.now() - timedelta(days=5)
        mock_tasks = [
            {
                "taskid": "TASK002",
                "record_id": "rec456",
                "status": "completed",
                "completed_at": completed_at.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "测试任务",
                "chat_id": "chat456"
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_archive_task', 
                            new_callable=AsyncMock) as mock_archive:
                await scheduler.archive_completed_tasks()
        
        # 验证没有调用归档
        mock_archive.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_archive_exactly_7_days(self):
        """测试完成恰好7天时归档"""
        # 模拟完成恰好7天的任务
        completed_at = datetime.now() - timedelta(days=7)
        mock_tasks = [
            {
                "taskid": "TASK003",
                "record_id": "rec789",
                "status": "completed",
                "completed_at": completed_at.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "测试任务",
                "chat_id": "chat789"
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_archive_task', 
                            new_callable=AsyncMock) as mock_archive:
                await scheduler.archive_completed_tasks()
        
        # 验证调用了归档（>=7天）
        mock_archive.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_archive_task_renames_chat(self):
        """测试归档任务重命名群聊"""
        task = {
            "taskid": "TASK004",
            "record_id": "rec111",
            "title": "测试任务",
            "chat_id": "chat111"
        }
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_rename_chat_to_archived', 
                         new_callable=AsyncMock) as mock_rename:
            with patch.object(scheduler, '_remove_bot_from_chat', 
                            new_callable=AsyncMock):
                with patch.object(scheduler, '_mark_task_archived', 
                                new_callable=AsyncMock):
                    await scheduler._archive_task(task)
        
        # 验证调用了重命名
        mock_rename.assert_called_once()
        assert mock_rename.call_args[0][0] == "chat111"
    
    @pytest.mark.asyncio
    async def test_archive_task_removes_bot(self):
        """测试归档任务移除机器人"""
        task = {
            "taskid": "TASK005",
            "record_id": "rec222",
            "title": "测试任务",
            "chat_id": "chat222"
        }
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_rename_chat_to_archived', 
                         new_callable=AsyncMock):
            with patch.object(scheduler, '_remove_bot_from_chat', 
                            new_callable=AsyncMock) as mock_remove:
                with patch.object(scheduler, '_mark_task_archived', 
                                new_callable=AsyncMock):
                    await scheduler._archive_task(task)
        
        # 验证调用了移除机器人
        mock_remove.assert_called_once()
        assert mock_remove.call_args[0][0] == "chat222"
    
    @pytest.mark.asyncio
    async def test_archive_task_marks_archived(self):
        """测试归档任务标记为已归档"""
        task = {
            "taskid": "TASK006",
            "record_id": "rec333",
            "title": "测试任务",
            "chat_id": "chat333"
        }
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_rename_chat_to_archived', 
                         new_callable=AsyncMock):
            with patch.object(scheduler, '_remove_bot_from_chat', 
                            new_callable=AsyncMock):
                with patch.object(scheduler, '_mark_task_archived', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler._archive_task(task)
        
        # 验证调用了标记归档
        mock_mark.assert_called_once()
        assert mock_mark.call_args[0][0]["taskid"] == "TASK006"
    
    @pytest.mark.asyncio
    async def test_archive_without_chat_id(self):
        """测试没有chat_id时的归档处理"""
        task = {
            "taskid": "TASK007",
            "record_id": "rec444",
            "title": "测试任务"
            # 缺少chat_id
        }
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_rename_chat_to_archived', 
                         new_callable=AsyncMock) as mock_rename:
            with patch.object(scheduler, '_remove_bot_from_chat', 
                            new_callable=AsyncMock) as mock_remove:
                with patch.object(scheduler, '_mark_task_archived', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler._archive_task(task)
        
        # 验证没有调用群聊相关操作
        mock_rename.assert_not_called()
        mock_remove.assert_not_called()
        # 但仍然标记为归档
        mock_mark.assert_called_once()


class TestSchedulerLifecycle:
    """测试调度器生命周期"""
    
    @pytest.mark.asyncio
    async def test_scheduler_start(self):
        """测试调度器启动"""
        scheduler = TaskScheduler()
        
        # 确保初始状态
        assert scheduler.running is False
        
        # 启动调度器（不等待任务完成）
        with patch.object(scheduler, '_run_deadline_reminders', 
                         new_callable=AsyncMock):
            with patch.object(scheduler, '_run_archiving', 
                            new_callable=AsyncMock):
                await scheduler.start()
        
        # 验证状态
        assert scheduler.running is True
        assert len(scheduler._tasks) == 2
        
        # 清理
        await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_scheduler_stop(self):
        """测试调度器停止"""
        scheduler = TaskScheduler()
        
        # 启动调度器
        with patch.object(scheduler, '_run_deadline_reminders', 
                         new_callable=AsyncMock):
            with patch.object(scheduler, '_run_archiving', 
                            new_callable=AsyncMock):
                await scheduler.start()
        
        # 停止调度器
        await scheduler.stop()
        
        # 验证状态
        assert scheduler.running is False
        assert len(scheduler._tasks) == 0
    
    @pytest.mark.asyncio
    async def test_scheduler_double_start(self):
        """测试重复启动调度器"""
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_run_deadline_reminders', 
                         new_callable=AsyncMock):
            with patch.object(scheduler, '_run_archiving', 
                            new_callable=AsyncMock):
                await scheduler.start()
                
                # 尝试再次启动
                await scheduler.start()
        
        # 验证只有一组任务
        assert len(scheduler._tasks) == 2
        
        # 清理
        await scheduler.stop()


class TestGetInProgressTasks:
    """测试获取进行中的任务"""
    
    @pytest.mark.asyncio
    async def test_get_in_progress_tasks_filters_correctly(self):
        """测试正确筛选进行中的任务"""
        mock_records = [
            {
                "record_id": "rec1",
                "fields": {
                    "taskid": "TASK001",
                    "status": "in_progress",
                    "title": "任务1"
                }
            },
            {
                "record_id": "rec2",
                "fields": {
                    "taskid": "TASK002",
                    "status": "completed",
                    "title": "任务2"
                }
            },
            {
                "record_id": "rec3",
                "fields": {
                    "taskid": "TASK003",
                    "status": "in_progress",
                    "title": "任务3"
                }
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch('app.services.scheduler.bitable_client') as mock_bitable:
            mock_bitable.get_table_records.return_value = {"data": {"items": mock_records}}
            with patch('app.services.scheduler.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await scheduler._get_in_progress_tasks()
        
        # 验证只返回in_progress状态的任务
        assert len(result) == 2
        assert result[0]["taskid"] == "TASK001"
        assert result[1]["taskid"] == "TASK003"


class TestGetCompletedTasks:
    """测试获取已完成的任务"""
    
    @pytest.mark.asyncio
    async def test_get_completed_tasks_filters_correctly(self):
        """测试正确筛选已完成的任务"""
        mock_records = [
            {
                "record_id": "rec1",
                "fields": {
                    "taskid": "TASK001",
                    "status": "completed",
                    "title": "任务1"
                }
            },
            {
                "record_id": "rec2",
                "fields": {
                    "taskid": "TASK002",
                    "status": "in_progress",
                    "title": "任务2"
                }
            },
            {
                "record_id": "rec3",
                "fields": {
                    "taskid": "TASK003",
                    "status": "completed",
                    "title": "任务3"
                }
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch('app.services.scheduler.bitable_client') as mock_bitable:
            mock_bitable.get_table_records.return_value = {"data": {"items": mock_records}}
            with patch('app.services.scheduler.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await scheduler._get_completed_tasks()
        
        # 验证只返回completed状态的任务
        assert len(result) == 2
        assert result[0]["taskid"] == "TASK001"
        assert result[1]["taskid"] == "TASK003"


class TestDeadlineBoundaryConditions:
    """测试周期计算边界条件"""
    
    def test_is_past_half_deadline_zero_duration(self):
        """测试零时长任务（创建时间等于截止时间）"""
        now = datetime.now()
        
        task = {
            "taskid": "TASK001",
            "create_time": now.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": now.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 零时长任务应该被认为已过半周期
        assert result is True
    
    def test_is_past_half_deadline_very_short_duration(self):
        """测试极短时长任务（1分钟）"""
        now = datetime.now()
        created = now - timedelta(seconds=40)
        deadline = now + timedelta(seconds=20)
        
        task = {
            "taskid": "TASK002",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 已过40秒，总共60秒，已过半周期
        assert result is True
    
    def test_is_past_half_deadline_very_long_duration(self):
        """测试极长时长任务（1年）"""
        now = datetime.now()
        created = now - timedelta(days=200)
        deadline = now + timedelta(days=165)
        
        task = {
            "taskid": "TASK003",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 已过200天，总共365天，已过半周期
        assert result is True
    
    def test_is_past_half_deadline_negative_duration(self):
        """测试负时长任务（截止时间早于创建时间）"""
        now = datetime.now()
        created = now
        deadline = now - timedelta(days=1)  # 截止时间在创建时间之前
        
        task = {
            "taskid": "TASK004",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 负时长任务应该被认为已过半周期（已过期）
        assert result is True
    
    def test_is_past_half_deadline_future_task(self):
        """测试未来任务（创建时间在未来）"""
        now = datetime.now()
        created = now + timedelta(days=1)
        deadline = now + timedelta(days=10)
        
        task = {
            "taskid": "TASK005",
            "create_time": created.strftime('%Y-%m-%d %H:%M:%S'),
            "deadline": deadline.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 未来任务未过半周期
        assert result is False
    
    def test_is_past_half_deadline_microsecond_precision(self):
        """测试微秒精度的时间计算"""
        now = datetime.now()
        created = now - timedelta(microseconds=500000)  # 0.5秒前
        deadline = now + timedelta(microseconds=500000)  # 0.5秒后
        
        task = {
            "taskid": "TASK006",
            "create_time": created.isoformat(),
            "deadline": deadline.isoformat()
        }
        
        scheduler = TaskScheduler()
        result = scheduler._is_past_half_deadline(task)
        
        # 恰好在半周期
        assert result is True


class TestConcurrentReminders:
    """测试并发提醒处理"""
    
    @pytest.mark.asyncio
    async def test_check_deadline_reminders_multiple_tasks(self):
        """测试同时处理多个需要提醒的任务"""
        now = datetime.now()
        
        # 创建多个需要提醒的任务
        mock_tasks = [
            {
                "taskid": f"TASK{i:03d}",
                "record_id": f"rec{i:03d}",
                "reminded": False,
                "create_time": (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": now.strftime('%Y-%m-%d %H:%M:%S'),
                "title": f"任务{i}",
                "assignee": f"user{i}",
                "creator": f"hr{i}"
            }
            for i in range(1, 6)  # 5个任务
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_in_progress_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_send_reminder', 
                            new_callable=AsyncMock) as mock_send:
                with patch.object(scheduler, '_mark_reminded', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler.check_deadline_reminders()
        
        # 验证所有任务都发送了提醒
        assert mock_send.call_count == 5
        assert mock_mark.call_count == 5
    
    @pytest.mark.asyncio
    async def test_check_deadline_reminders_mixed_tasks(self):
        """测试混合状态任务（部分需要提醒，部分不需要）"""
        now = datetime.now()
        
        mock_tasks = [
            # 需要提醒：已过半周期，未提醒
            {
                "taskid": "TASK001",
                "record_id": "rec001",
                "reminded": False,
                "create_time": (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": now.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务1",
                "assignee": "user1",
                "creator": "hr1"
            },
            # 不需要提醒：已提醒
            {
                "taskid": "TASK002",
                "record_id": "rec002",
                "reminded": True,
                "create_time": (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": now.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务2",
                "assignee": "user2",
                "creator": "hr2"
            },
            # 不需要提醒：未过半周期
            {
                "taskid": "TASK003",
                "record_id": "rec003",
                "reminded": False,
                "create_time": (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": (now + timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务3",
                "assignee": "user3",
                "creator": "hr3"
            },
            # 需要提醒：已过半周期，未提醒
            {
                "taskid": "TASK004",
                "record_id": "rec004",
                "reminded": False,
                "create_time": (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": (now + timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务4",
                "assignee": "user4",
                "creator": "hr4"
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_in_progress_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_send_reminder', 
                            new_callable=AsyncMock) as mock_send:
                with patch.object(scheduler, '_mark_reminded', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler.check_deadline_reminders()
        
        # 验证只有2个任务发送了提醒
        assert mock_send.call_count == 2
        assert mock_mark.call_count == 2
    
    @pytest.mark.asyncio
    async def test_check_deadline_reminders_error_handling(self):
        """测试提醒过程中的错误处理"""
        now = datetime.now()
        
        mock_tasks = [
            {
                "taskid": "TASK001",
                "record_id": "rec001",
                "reminded": False,
                "create_time": (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": now.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务1",
                "assignee": "user1",
                "creator": "hr1"
            },
            {
                "taskid": "TASK002",
                "record_id": "rec002",
                "reminded": False,
                "create_time": (now - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
                "deadline": now.strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务2",
                "assignee": "user2",
                "creator": "hr2"
            }
        ]
        
        scheduler = TaskScheduler()
        
        # 模拟第一个任务发送失败，第二个成功
        call_count = [0]
        async def mock_send_with_error(task):
            call_count[0] += 1
            if call_count[0] == 1:  # 第一次调用失败
                raise Exception("发送失败")
            # 第二次调用成功（不抛出异常）
        
        with patch.object(scheduler, '_get_in_progress_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_send_reminder', 
                            new_callable=AsyncMock, side_effect=mock_send_with_error):
                with patch.object(scheduler, '_mark_reminded', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler.check_deadline_reminders()
        
        # 验证即使第一个失败，第二个仍然被处理（错误被捕获）
        # 第一个任务发送失败，不会标记为已提醒
        # 第二个任务发送成功，会标记为已提醒
        assert mock_mark.call_count == 1


class TestBatchArchiving:
    """测试批量归档处理"""
    
    @pytest.mark.asyncio
    async def test_archive_completed_tasks_batch_processing(self):
        """测试批量归档多个任务"""
        now = datetime.now()
        
        # 创建多个需要归档的任务
        mock_tasks = [
            {
                "taskid": f"TASK{i:03d}",
                "record_id": f"rec{i:03d}",
                "status": "completed",
                "completed_at": (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": f"任务{i}",
                "chat_id": f"chat{i:03d}"
            }
            for i in range(1, 6)  # 5个任务
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_archive_task', 
                            new_callable=AsyncMock) as mock_archive:
                await scheduler.archive_completed_tasks()
        
        # 验证所有任务都被归档
        assert mock_archive.call_count == 5
    
    @pytest.mark.asyncio
    async def test_archive_completed_tasks_mixed_ages(self):
        """测试混合年龄的已完成任务"""
        now = datetime.now()
        
        mock_tasks = [
            # 需要归档：完成8天
            {
                "taskid": "TASK001",
                "record_id": "rec001",
                "status": "completed",
                "completed_at": (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务1",
                "chat_id": "chat001"
            },
            # 不需要归档：完成5天
            {
                "taskid": "TASK002",
                "record_id": "rec002",
                "status": "completed",
                "completed_at": (now - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务2",
                "chat_id": "chat002"
            },
            # 需要归档：完成恰好7天
            {
                "taskid": "TASK003",
                "record_id": "rec003",
                "status": "completed",
                "completed_at": (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务3",
                "chat_id": "chat003"
            },
            # 需要归档：完成30天
            {
                "taskid": "TASK004",
                "record_id": "rec004",
                "status": "completed",
                "completed_at": (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务4",
                "chat_id": "chat004"
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_archive_task', 
                            new_callable=AsyncMock) as mock_archive:
                await scheduler.archive_completed_tasks()
        
        # 验证只有3个任务被归档（>=7天）
        assert mock_archive.call_count == 3
    
    @pytest.mark.asyncio
    async def test_archive_task_complete_workflow(self):
        """测试归档任务的完整工作流"""
        task = {
            "taskid": "TASK001",
            "record_id": "rec001",
            "title": "测试任务",
            "chat_id": "chat001"
        }
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_rename_chat_to_archived', 
                         new_callable=AsyncMock) as mock_rename:
            with patch.object(scheduler, '_remove_bot_from_chat', 
                            new_callable=AsyncMock) as mock_remove:
                with patch.object(scheduler, '_mark_task_archived', 
                                new_callable=AsyncMock) as mock_mark:
                    await scheduler._archive_task(task)
        
        # 验证所有步骤都被执行
        mock_rename.assert_called_once_with("chat001", task)
        mock_remove.assert_called_once_with("chat001")
        mock_mark.assert_called_once_with(task)
    
    @pytest.mark.asyncio
    async def test_archive_completed_tasks_error_handling(self):
        """测试归档过程中的错误处理"""
        now = datetime.now()
        
        mock_tasks = [
            {
                "taskid": "TASK001",
                "record_id": "rec001",
                "status": "completed",
                "completed_at": (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务1",
                "chat_id": "chat001"
            },
            {
                "taskid": "TASK002",
                "record_id": "rec002",
                "status": "completed",
                "completed_at": (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务2",
                "chat_id": "chat002"
            }
        ]
        
        scheduler = TaskScheduler()
        
        # 模拟第一个任务归档失败
        async def mock_archive_with_error(task):
            if task["taskid"] == "TASK001":
                raise Exception("归档失败")
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_archive_task', 
                            new_callable=AsyncMock, side_effect=mock_archive_with_error):
                await scheduler.archive_completed_tasks()
        
        # 验证即使第一个失败，方法仍然完成（错误被捕获）
        # 由于side_effect应用到所有调用，两个都会失败，但不会抛出异常
    
    @pytest.mark.asyncio
    async def test_archive_tasks_without_chat_id(self):
        """测试归档没有chat_id的任务"""
        now = datetime.now()
        
        mock_tasks = [
            {
                "taskid": "TASK001",
                "record_id": "rec001",
                "status": "completed",
                "completed_at": (now - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
                "title": "任务1"
                # 没有chat_id
            }
        ]
        
        scheduler = TaskScheduler()
        
        with patch.object(scheduler, '_get_completed_tasks', 
                         new_callable=AsyncMock, return_value=mock_tasks):
            with patch.object(scheduler, '_rename_chat_to_archived', 
                            new_callable=AsyncMock) as mock_rename:
                with patch.object(scheduler, '_remove_bot_from_chat', 
                                new_callable=AsyncMock) as mock_remove:
                    with patch.object(scheduler, '_mark_task_archived', 
                                    new_callable=AsyncMock) as mock_mark:
                        await scheduler.archive_completed_tasks()
        
        # 验证没有调用群聊相关操作
        mock_rename.assert_not_called()
        mock_remove.assert_not_called()
        # 但仍然标记为归档
        mock_mark.assert_called_once()
