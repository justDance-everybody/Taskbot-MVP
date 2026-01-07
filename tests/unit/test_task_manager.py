"""
Task Manager 单元测试
测试状态转换和日报生成
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
import json
from app.services.task_manager import TaskManager, TaskStatus, TaskUrgency


class TestTaskStateTransitions:
    """测试任务状态转换"""
    
    @pytest.mark.asyncio
    async def test_create_task_sets_pending_status(self):
        """测试创建任务设置为pending状态"""
        task_data = {
            "title": "开发API",
            "description": "开发用户登录API",
            "skill_tags": ["Python", "FastAPI"],
            "deadline": "2024-01-15",
            "urgency": "normal"
        }
        
        # Mock the bitable_client at module level
        mock_bitable = MagicMock()
        mock_bitable.create_task = AsyncMock(return_value="rec123")
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            record_id = await manager.create_task(task_data)
        
        # 验证返回记录ID
        assert record_id == "rec123"
        
        # 验证调用create_task时状态为pending
        call_args = mock_bitable.create_task.call_args[0][0]
        assert call_args["status"] == TaskStatus.PENDING.value
    
    @pytest.mark.asyncio
    async def test_accept_task_transitions_to_in_progress(self):
        """测试接受任务转换为in_progress状态"""
        task_id = "TASK001"
        user_id = "user123"
        
        mock_task = {
            "taskid": task_id,
            "status": TaskStatus.ASSIGNED.value,
            "candidates": ["user123", "user456"],
            "title": "测试任务",
            "created_by": "hr001"
        }
        
        # Mock the bitable_client and feishu service
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        mock_bitable.update_task = AsyncMock(return_value=True)
        
        mock_feishu = MagicMock()
        mock_feishu.send_message = AsyncMock()
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            manager.feishu = mock_feishu
            result = await manager.accept_task(task_id, user_id)
        
        # 验证返回成功
        assert result is True
        
        # 验证更新任务状态为in_progress
        update_call = mock_bitable.update_task.call_args[0]
        assert update_call[0] == task_id
        assert update_call[1]["status"] == TaskStatus.IN_PROGRESS.value
        assert update_call[1]["assignee"] == user_id
    
    @pytest.mark.asyncio
    async def test_accept_task_wrong_status_fails(self):
        """测试错误状态下接受任务失败"""
        task_id = "TASK002"
        user_id = "user123"
        
        # 任务状态不是assigned
        mock_task = {
            "taskid": task_id,
            "status": TaskStatus.COMPLETED.value,
            "title": "测试任务"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            result = await manager.accept_task(task_id, user_id)
        
        # 验证返回失败
        assert result is False
    
    @pytest.mark.asyncio
    async def test_submit_task_transitions_to_submitted(self):
        """测试提交任务转换为submitted状态"""
        task_id = "TASK003"
        user_id = "user123"
        submission_url = "https://github.com/repo/pull/123"
        
        mock_task = {
            "taskid": task_id,
            "status": TaskStatus.IN_PROGRESS.value,
            "assignee": user_id,
            "title": "测试任务",
            "description": "任务描述"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        mock_bitable.update_task = AsyncMock(return_value=True)
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            with patch.object(manager, '_update_daily_stats', AsyncMock()):
                with patch.object(manager, '_auto_quality_check', AsyncMock()):
                    result = await manager.submit_task(
                        task_id, user_id, submission_url, "提交说明"
                    )
        
        # 验证返回成功
        assert result is True
        
        # 验证更新任务状态为submitted
        update_call = mock_bitable.update_task.call_args[0]
        assert update_call[0] == task_id
        assert update_call[1]["status"] == TaskStatus.SUBMITTED.value
        assert update_call[1]["submission_url"] == submission_url
    
    @pytest.mark.asyncio
    async def test_submit_task_wrong_assignee_fails(self):
        """测试非指派人提交任务失败"""
        task_id = "TASK004"
        user_id = "user123"
        wrong_user = "user456"
        
        mock_task = {
            "taskid": task_id,
            "status": TaskStatus.IN_PROGRESS.value,
            "assignee": user_id,  # 指派给user123
            "title": "测试任务"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            result = await manager.submit_task(
                task_id, wrong_user, "https://github.com/repo/pull/123"
            )
        
        # 验证返回失败
        assert result is False
    
    @pytest.mark.asyncio
    async def test_complete_task_transitions_to_completed(self):
        """测试完成任务转换为completed状态"""
        task_id = "TASK005"
        
        mock_task = {
            "taskid": task_id,
            "status": TaskStatus.REVIEWING.value,
            "assignee": "user123",
            "title": "测试任务",
            "reward_points": 100,
            "created_by": "hr001"
        }
        
        review_data = {
            "final_score": 95
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        mock_bitable.update_task = AsyncMock(return_value=True)
        mock_bitable.update_candidate_performance = AsyncMock()
        
        mock_feishu = MagicMock()
        mock_feishu.send_message = AsyncMock()
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            manager.feishu = mock_feishu
            with patch.object(manager, '_update_daily_stats', AsyncMock()):
                result = await manager.complete_task(task_id, review_data)
        
        # 验证返回成功
        assert result is True
        
        # 验证更新任务状态为completed
        update_call = mock_bitable.update_task.call_args[0]
        assert update_call[0] == task_id
        assert update_call[1]["status"] == TaskStatus.COMPLETED.value
        assert update_call[1]["final_score"] == 95
    
    @pytest.mark.asyncio
    async def test_reject_task_transitions_to_rejected(self):
        """测试拒绝任务转换为rejected状态"""
        task_id = "TASK006"
        
        mock_task = {
            "taskid": task_id,
            "status": TaskStatus.REVIEWING.value,
            "assignee": "user123",
            "title": "测试任务"
        }
        
        review_data = {
            "final_score": 60,
            "failed_reasons": ["代码质量不达标", "测试覆盖率不足"]
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        mock_bitable.update_task = AsyncMock(return_value=True)
        
        mock_feishu = MagicMock()
        mock_feishu.send_message = AsyncMock()
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            manager.feishu = mock_feishu
            with patch.object(manager, '_update_daily_stats', AsyncMock()):
                result = await manager.reject_task(task_id, review_data)
        
        # 验证返回成功
        assert result is True
        
        # 验证更新任务状态为rejected
        update_call = mock_bitable.update_task.call_args[0]
        assert update_call[0] == task_id
        assert update_call[1]["status"] == TaskStatus.REJECTED.value
        assert update_call[1]["final_score"] == 60


class TestDailyReportGeneration:
    """测试日报生成"""
    
    @pytest.mark.asyncio
    async def test_generate_daily_report_structure(self):
        """测试日报生成包含所有必需字段"""
        manager = TaskManager()
        
        # 模拟JSON文件数据
        mock_stats = {
            "date": "2024-01-10",
            "total_tasks": 50,
            "completed_tasks": 30,
            "pending_tasks": 10,
            "in_progress_tasks": 8,
            "submitted_tasks": 2,
            "reviewing_tasks": 0,
            "rejected_tasks": 0,
            "assigned_tasks": 0,
            "cancelled_tasks": 0,
            "average_score": 85.5,
            "completion_rate": 60.0,
            "tasks_by_urgency": {
                "urgent": 5,
                "high": 10,
                "normal": 30,
                "low": 5
            },
            "today_created": 5,
            "today_completed": 3,
            "top_performers": []
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))):
            with patch('os.path.exists', return_value=True):
                with patch.object(manager, '_get_simple_task_info', 
                                new_callable=AsyncMock, 
                                return_value={"total_records": 50, "valid_records": 50, "empty_records": 0}):
                    with patch.object(manager, '_calculate_average_assignment_time', 
                                    new_callable=AsyncMock, return_value="2.5小时"):
                        report = await manager.generate_daily_report()
        
        # 验证报告包含所有必需字段
        assert "date" in report
        assert "total_tasks" in report
        assert "completed_tasks" in report
        assert "pending_tasks" in report
        assert "in_progress_tasks" in report
        assert "average_assignment_time" in report
        assert "completion_rate" in report
        assert "tasks_by_urgency" in report
        assert "today_created" in report
        assert "today_completed" in report
        
        # 验证数据正确
        assert report["total_tasks"] == 50
        assert report["completed_tasks"] == 30
        assert report["average_assignment_time"] == "2.5小时"
    
    @pytest.mark.asyncio
    async def test_generate_daily_report_no_json_file(self):
        """测试没有JSON文件时生成日报"""
        manager = TaskManager()
        
        with patch('os.path.exists', return_value=False):
            with patch.object(manager, '_get_simple_task_info', 
                            new_callable=AsyncMock, 
                            return_value={"total_records": 10, "valid_records": 10, "empty_records": 0}):
                with patch.object(manager, '_calculate_average_assignment_time', 
                                new_callable=AsyncMock, return_value="N/A"):
                    report = await manager.generate_daily_report()
        
        # 验证报告仍然包含基本结构
        assert "date" in report
        assert "total_tasks" in report
        assert "database_operations" in report
    
    @pytest.mark.asyncio
    async def test_calculate_average_assignment_time_with_tasks(self):
        """测试计算平均指派耗时"""
        manager = TaskManager()
        
        now = datetime.now()
        mock_records = [
            {
                "fields": {
                    "status": "in_progress",
                    "create_time": (now - timedelta(hours=5)).isoformat(),
                    "assigned_at": (now - timedelta(hours=3)).isoformat()
                }
            },
            {
                "fields": {
                    "status": "completed",
                    "create_time": (now - timedelta(hours=10)).isoformat(),
                    "assigned_at": (now - timedelta(hours=7)).isoformat()
                }
            }
        ]
        
        with patch.object(manager.bitable, 'get_table_records', 
                         return_value={"data": {"items": mock_records}}):
            with patch('app.services.task_manager.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await manager._calculate_average_assignment_time()
        
        # 验证返回格式化的时间
        # 平均耗时：(2小时 + 3小时) / 2 = 2.5小时
        assert "小时" in result or "分钟" in result or "天" in result
    
    @pytest.mark.asyncio
    async def test_calculate_average_assignment_time_no_tasks(self):
        """测试没有任务时计算平均指派耗时"""
        manager = TaskManager()
        
        with patch.object(manager.bitable, 'get_table_records', 
                         return_value={"data": {"items": []}}):
            with patch('app.services.task_manager.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await manager._calculate_average_assignment_time()
        
        # 验证返回N/A
        assert result == "N/A"
    
    @pytest.mark.asyncio
    async def test_calculate_average_assignment_time_formats(self):
        """测试不同时间跨度的格式化"""
        manager = TaskManager()
        
        now = datetime.now()
        
        # 测试分钟格式（小于1小时）
        mock_records_minutes = [
            {
                "fields": {
                    "status": "assigned",
                    "create_time": (now - timedelta(minutes=30)).isoformat(),
                    "assigned_at": now.isoformat()
                }
            }
        ]
        
        with patch.object(manager.bitable, 'get_table_records', 
                         return_value={"data": {"items": mock_records_minutes}}):
            with patch('app.services.task_manager.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await manager._calculate_average_assignment_time()
        
        # 验证返回分钟格式
        assert "分钟" in result
        
        # 测试天格式（大于24小时）
        mock_records_days = [
            {
                "fields": {
                    "status": "assigned",
                    "create_time": (now - timedelta(days=3)).isoformat(),
                    "assigned_at": (now - timedelta(days=1)).isoformat()
                }
            }
        ]
        
        with patch.object(manager.bitable, 'get_table_records', 
                         return_value={"data": {"items": mock_records_days}}):
            with patch('app.services.task_manager.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await manager._calculate_average_assignment_time()
        
        # 验证返回天格式
        assert "天" in result


class TestDailyStatsUpdate:
    """测试每日统计更新"""
    
    @pytest.mark.asyncio
    async def test_update_daily_stats_creates_file(self):
        """测试更新统计创建文件"""
        manager = TaskManager()
        
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open()) as mock_file:
                with patch.object(manager, '_get_simple_task_info', 
                                new_callable=AsyncMock, 
                                return_value={"total_records": 10, "valid_records": 10, "empty_records": 0}):
                    await manager._update_daily_stats()
        
        # 验证文件被写入
        mock_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_increment_task_created_updates_stats(self):
        """测试增量更新任务创建统计"""
        manager = TaskManager()
        
        mock_stats = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total_tasks": 10,
            "pending_tasks": 5,
            "today_created": 2,
            "tasks_by_urgency": {
                "normal": 8,
                "high": 2
            }
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))) as mock_file:
                await manager.increment_task_created(urgency="high")
        
        # 验证文件被写入
        assert mock_file.call_count >= 2  # 至少读和写各一次
    
    @pytest.mark.asyncio
    async def test_increment_task_created_new_day(self):
        """测试新的一天重置today_created"""
        manager = TaskManager()
        
        # 模拟昨天的统计
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        mock_stats = {
            "date": yesterday,
            "total_tasks": 10,
            "today_created": 5
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))) as mock_file:
                await manager.increment_task_created()
        
        # 验证文件被写入（新的一天会重置统计）
        assert mock_file.call_count >= 2


class TestTaskCreation:
    """测试任务创建"""
    
    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self):
        """测试创建包含所有字段的任务"""
        task_data = {
            "title": "开发API",
            "description": "开发用户登录API",
            "skill_tags": ["Python", "FastAPI"],
            "deadline": "2024-01-15",
            "urgency": "high",
            "created_by": "hr001"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.create_task = AsyncMock(return_value="rec123")
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            record_id = await manager.create_task(task_data)
        
        # 验证返回记录ID
        assert record_id == "rec123"
        
        # 验证调用参数
        call_args = mock_bitable.create_task.call_args[0][0]
        assert call_args["title"] == "开发API"
        assert call_args["description"] == "开发用户登录API"
        assert call_args["skilltags"] == ["Python", "FastAPI"]
        assert call_args["urgency"] == "high"
        assert call_args["creator"] == "hr001"
    
    @pytest.mark.asyncio
    async def test_create_task_missing_required_field(self):
        """测试缺少必需字段时创建任务失败"""
        task_data = {
            "title": "开发API"
            # 缺少description, skill_tags, deadline
        }
        
        manager = TaskManager()
        
        with pytest.raises(ValueError):
            await manager.create_task(task_data)
    
    @pytest.mark.asyncio
    async def test_create_task_generates_task_id(self):
        """测试创建任务生成任务ID"""
        task_data = {
            "title": "开发API",
            "description": "描述",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.create_task = AsyncMock(return_value="rec123")
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            await manager.create_task(task_data)
        
        # 验证生成了taskid
        call_args = mock_bitable.create_task.call_args[0][0]
        assert "taskid" in call_args
        assert call_args["taskid"].startswith("TASK")


class TestTaskAssignment:
    """测试任务分配"""
    
    @pytest.mark.asyncio
    async def test_assign_task_to_candidate(self):
        """测试将任务分配给候选人"""
        task_id = "TASK001"
        candidate_id = "user123"
        
        mock_bitable = MagicMock()
        mock_bitable.update_task = AsyncMock(return_value=True)
        
        mock_feishu = MagicMock()
        mock_feishu.send_message = AsyncMock()
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            manager.feishu = mock_feishu
            result = await manager.assign_task_to_candidate(task_id, candidate_id)
        
        # 验证返回成功
        assert result is True
        
        # 验证更新任务状态
        update_call = mock_bitable.update_task.call_args[0]
        assert update_call[0] == task_id
        assert update_call[1]["status"] == TaskStatus.ASSIGNED.value
        assert update_call[1]["assigned_candidate"] == candidate_id
        
        # 验证发送通知
        mock_feishu.send_message.assert_called_once()


class TestGetTaskStatus:
    """测试获取任务状态"""
    
    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        """测试成功获取任务状态"""
        task_id = "TASK001"
        mock_task = {
            "taskid": task_id,
            "status": "in_progress",
            "title": "测试任务"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=mock_task)
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            result = await manager.get_task_status(task_id)
        
        # 验证返回任务数据
        assert result is not None
        assert result["taskid"] == task_id
        assert result["status"] == "in_progress"
    
    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """测试任务不存在时返回None"""
        task_id = "NONEXISTENT"
        
        mock_bitable = MagicMock()
        mock_bitable.get_task = AsyncMock(return_value=None)
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            result = await manager.get_task_status(task_id)
        
        # 验证返回None
        assert result is None


class TestTaskStatistics:
    """测试任务统计功能"""
    
    @pytest.mark.asyncio
    async def test_increment_task_created_updates_counts(self):
        """测试增量更新任务创建统计"""
        manager = TaskManager()
        
        mock_stats = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total_tasks": 10,
            "pending_tasks": 5,
            "completed_tasks": 3,
            "today_created": 2,
            "tasks_by_urgency": {
                "normal": 8,
                "high": 2,
                "urgent": 0,
                "low": 0
            }
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))) as mock_file:
                await manager.increment_task_created(urgency="high")
        
        # 验证文件被写入
        assert mock_file.call_count >= 2  # 读和写
        
        # 获取写入的数据
        write_calls = [call for call in mock_file().write.call_args_list]
        if write_calls:
            written_data = ''.join([call[0][0] for call in write_calls])
            updated_stats = json.loads(written_data)
            
            # 验证统计数据更新
            assert updated_stats["total_tasks"] == 11  # 增加1
            assert updated_stats["pending_tasks"] == 6  # 增加1
            assert updated_stats["today_created"] == 3  # 增加1
            assert updated_stats["tasks_by_urgency"]["high"] == 3  # 增加1
    
    @pytest.mark.asyncio
    async def test_increment_task_created_creates_new_file(self):
        """测试首次创建统计文件"""
        manager = TaskManager()
        
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open()) as mock_file:
                await manager.increment_task_created(urgency="normal")
        
        # 验证文件被创建和写入
        mock_file.assert_called()
        
        # 获取写入的数据
        write_calls = [call for call in mock_file().write.call_args_list]
        if write_calls:
            written_data = ''.join([call[0][0] for call in write_calls])
            new_stats = json.loads(written_data)
            
            # 验证初始统计数据
            assert new_stats["total_tasks"] == 1
            assert new_stats["pending_tasks"] == 1
            assert new_stats["today_created"] == 1
            assert new_stats["tasks_by_urgency"]["normal"] == 1
    
    @pytest.mark.asyncio
    async def test_increment_task_created_different_urgencies(self):
        """测试不同紧急程度的统计"""
        manager = TaskManager()
        
        mock_stats = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total_tasks": 0,
            "pending_tasks": 0,
            "completed_tasks": 0,
            "today_created": 0,
            "tasks_by_urgency": {
                "urgent": 0,
                "high": 0,
                "normal": 0,
                "low": 0
            }
        }
        
        # 测试urgent
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))):
                await manager.increment_task_created(urgency="urgent")
        
        # 测试low
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))):
                await manager.increment_task_created(urgency="low")
    
    @pytest.mark.asyncio
    async def test_update_daily_stats_merges_with_bitable(self):
        """测试统计更新合并多维表格数据"""
        manager = TaskManager()
        
        mock_stats = {
            "date": datetime.now().strftime('%Y-%m-%d'),
            "total_tasks": 10,
            "completed_tasks": 5
        }
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(mock_stats))):
                with patch.object(manager, '_get_simple_task_info', 
                                new_callable=AsyncMock, 
                                return_value={"total_records": 15, "valid_records": 12, "empty_records": 3}):
                    await manager._update_daily_stats()
        
        # 验证统计被更新（通过日志或其他方式）
        # 这里主要验证方法执行不报错
    
    @pytest.mark.asyncio
    async def test_get_simple_task_info_counts_records(self):
        """测试获取任务表基本信息"""
        manager = TaskManager()
        
        mock_records = [
            {"record_id": "rec1", "fields": {"taskid": "TASK001", "title": "任务1"}},
            {"record_id": "rec2", "fields": {"taskid": "TASK002", "title": "任务2"}},
            {"record_id": "rec3", "fields": {}},  # 空记录
            {"record_id": "rec4", "fields": {"taskid": "TASK004"}},
        ]
        
        with patch.object(manager.bitable, 'get_table_records', 
                         return_value={"data": {"items": mock_records}}):
            with patch('app.services.task_manager.settings') as mock_settings:
                mock_settings.feishu_task_table_id = "tbl123"
                
                result = await manager._get_simple_task_info()
        
        # 验证统计结果
        assert result["total_records"] == 4
        assert result["valid_records"] == 3  # 有非空字段的记录
        assert result["empty_records"] == 1  # 空记录


class TestBatchOperations:
    """测试批量操作"""
    
    @pytest.mark.asyncio
    async def test_auto_assign_task_to_multiple_candidates(self):
        """测试自动分配任务给多个候选人"""
        task_id = "TASK001"
        task_data = {
            "taskid": task_id,
            "title": "开发API",
            "description": "开发用户登录API",
            "skill_tags": ["Python", "FastAPI"],
            "deadline": "2024-01-15"
        }
        
        mock_candidates = [
            {"user_id": "user1", "name": "候选人1", "skills": ["Python", "FastAPI"]},
            {"user_id": "user2", "name": "候选人2", "skills": ["Python", "Django"]},
            {"user_id": "user3", "name": "候选人3", "skills": ["Python", "FastAPI", "React"]},
        ]
        
        mock_matches = [
            {"user_id": "user3", "score": 95, "reason": "技能完全匹配"},
            {"user_id": "user1", "score": 90, "reason": "技能匹配度高"},
            {"user_id": "user2", "score": 75, "reason": "部分技能匹配"},
        ]
        
        mock_bitable = MagicMock()
        mock_bitable.get_available_candidates = AsyncMock(return_value=mock_candidates)
        mock_bitable.update_task = AsyncMock(return_value=True)
        
        mock_feishu = MagicMock()
        mock_feishu.send_message = AsyncMock()
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            with patch('app.services.task_manager.MatchService') as MockMatchService:
                mock_match_service = MockMatchService.return_value
                mock_match_service.find_top_candidates = AsyncMock(return_value=mock_matches)
                
                manager = TaskManager()
                manager.feishu = mock_feishu
                await manager._auto_assign_task(task_id, task_data)
        
        # 验证发送了3条消息（给Top-3候选人）
        assert mock_feishu.send_message.call_count == 3
        
        # 验证更新了任务状态
        mock_bitable.update_task.assert_called_once()
        update_call = mock_bitable.update_task.call_args[0]
        assert update_call[0] == task_id
        assert update_call[1]["status"] == TaskStatus.ASSIGNED.value
        assert len(update_call[1]["candidates"]) == 3
    
    @pytest.mark.asyncio
    async def test_auto_assign_task_no_candidates(self):
        """测试没有候选人时的自动分配"""
        task_id = "TASK002"
        task_data = {
            "taskid": task_id,
            "title": "开发API",
            "description": "描述",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        mock_bitable = MagicMock()
        mock_bitable.get_available_candidates = AsyncMock(return_value=[])
        
        mock_feishu = MagicMock()
        mock_feishu.send_message = AsyncMock()
        
        with patch('app.services.task_manager.bitable_client', mock_bitable):
            manager = TaskManager()
            manager.feishu = mock_feishu
            await manager._auto_assign_task(task_id, task_data)
        
        # 验证没有发送消息
        mock_feishu.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_user_tasks_returns_empty_list(self):
        """测试获取用户任务列表（当前返回空列表）"""
        manager = TaskManager()
        
        result = await manager.get_user_tasks("user123")
        
        # 验证返回空列表（当前实现）
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_user_tasks_with_status_filter(self):
        """测试按状态筛选用户任务"""
        manager = TaskManager()
        
        result = await manager.get_user_tasks("user123", status="in_progress")
        
        # 验证返回空列表（当前实现）
        assert result == []
    
    @pytest.mark.asyncio
    async def test_send_daily_reminders_executes(self):
        """测试发送每日提醒执行"""
        manager = TaskManager()
        
        # 测试方法执行不报错
        await manager.send_daily_reminders()
        
        # 当前实现只记录日志，验证执行成功即可
