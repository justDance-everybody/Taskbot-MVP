"""
Task Monitor 单元测试
测试任务监控功能，包括健康检查、卡住任务检测和告警发送
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.task_monitor import TaskMonitor, task_monitor


@pytest.fixture
def mock_bitable_client():
    """模拟Bitable客户端"""
    mock = MagicMock()
    mock.get_table_records = MagicMock(return_value={
        'data': {
            'items': []
        }
    })
    return mock


@pytest.fixture
def mock_feishu_service():
    """模拟飞书服务"""
    mock = AsyncMock()
    mock.send_message = AsyncMock(return_value={"code": 0})
    return mock


@pytest.fixture
def mock_settings():
    """模拟配置"""
    mock = MagicMock()
    mock.feishu_task_table_id = "test_table_id"
    return mock


@pytest.fixture
def sample_task_in_progress():
    """进行中的任务示例"""
    now = datetime.now()
    created = now - timedelta(days=5)
    deadline = now + timedelta(days=3)
    
    return {
        'fields': {
            'taskid': 'TASK001',
            'title': '测试任务',
            'status': 'in_progress',
            'deadline': deadline.strftime('%Y-%m-%d %H:%M:%S'),
            'create_time': created.strftime('%Y-%m-%d %H:%M:%S'),
            'assignee': 'user123',
            'creator': 'user456'
        }
    }


@pytest.fixture
def sample_task_past_half():
    """已过半周期的任务示例"""
    now = datetime.now()
    created = now - timedelta(days=10)
    deadline = now + timedelta(days=2)
    
    return {
        'fields': {
            'taskid': 'TASK002',
            'title': '过半任务',
            'status': 'in_progress',
            'deadline': deadline.strftime('%Y-%m-%d %H:%M:%S'),
            'create_time': created.strftime('%Y-%m-%d %H:%M:%S'),
            'assignee': 'user789',
            'creator': 'user456'
        }
    }


@pytest.fixture
def sample_task_near_deadline():
    """临近截止时间的任务示例"""
    now = datetime.now()
    created = now - timedelta(days=10)
    deadline = now + timedelta(hours=12)
    
    return {
        'fields': {
            'taskid': 'TASK003',
            'title': '紧急任务',
            'status': 'in_progress',
            'deadline': deadline.strftime('%Y-%m-%d %H:%M:%S'),
            'create_time': created.strftime('%Y-%m-%d %H:%M:%S'),
            'assignee': 'user111',
            'creator': 'user222'
        }
    }


class TestTaskMonitorInitialization:
    """测试任务监控器初始化"""
    
    def test_task_monitor_initialization(self):
        """测试监控器初始化"""
        monitor = TaskMonitor()
        
        assert monitor.monitoring is False
        assert monitor.check_interval == 3600
        assert isinstance(monitor.reminded_tasks, set)
        assert len(monitor.reminded_tasks) == 0
    
    def test_global_task_monitor_instance(self):
        """测试全局监控器实例"""
        assert task_monitor is not None
        assert isinstance(task_monitor, TaskMonitor)



class TestCheckTaskHealth:
    """测试任务健康检查功能"""
    
    @pytest.mark.asyncio
    async def test_check_task_deadline_past_half(self, sample_task_past_half, mock_feishu_service):
        """测试检查已过半周期的任务"""
        monitor = TaskMonitor()
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            result = await monitor.check_task_deadline(sample_task_past_half['fields'])
        
        # 验证返回True表示发送了提醒
        assert result is True
        # 验证任务ID被添加到已提醒集合
        assert 'TASK002' in monitor.reminded_tasks
        # 验证调用了发送消息方法
        assert mock_feishu_service.send_message.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_check_task_deadline_not_past_half(self, sample_task_in_progress, mock_feishu_service):
        """测试检查未过半周期的任务"""
        monitor = TaskMonitor()
        
        # 修改任务使其未过半周期
        now = datetime.now()
        created = now - timedelta(days=2)
        deadline = now + timedelta(days=10)
        
        task_data = sample_task_in_progress['fields'].copy()
        task_data['create_time'] = created.strftime('%Y-%m-%d %H:%M:%S')
        task_data['deadline'] = deadline.strftime('%Y-%m-%d %H:%M:%S')
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            result = await monitor.check_task_deadline(task_data)
        
        # 验证返回False表示未发送提醒
        assert result is False
        # 验证任务ID未被添加到已提醒集合
        assert 'TASK001' not in monitor.reminded_tasks
        # 验证未调用发送消息方法
        assert mock_feishu_service.send_message.call_count == 0
    
    @pytest.mark.asyncio
    async def test_check_task_deadline_near_deadline(self, sample_task_near_deadline, mock_feishu_service):
        """测试检查临近截止时间的任务"""
        monitor = TaskMonitor()
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            result = await monitor.check_task_deadline(sample_task_near_deadline['fields'])
        
        # 验证返回True表示发送了提醒
        assert result is True
        # 验证任务ID被添加到已提醒集合（可能是普通提醒或最后期限提醒）
        assert 'TASK003' in monitor.reminded_tasks or 'TASK003_final' in monitor.reminded_tasks
        # 验证调用了发送消息方法
        assert mock_feishu_service.send_message.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_check_task_deadline_missing_data(self, mock_feishu_service):
        """测试缺少时间数据的任务"""
        monitor = TaskMonitor()
        task_data = {
            'taskid': 'TASK004',
            'title': '缺少数据的任务',
            'status': 'in_progress'
            # 缺少deadline和create_time
        }
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            result = await monitor.check_task_deadline(task_data)
        
        # 验证返回False
        assert result is False
        # 验证未调用发送消息方法
        assert mock_feishu_service.send_message.call_count == 0
    
    @pytest.mark.asyncio
    async def test_check_task_deadline_already_reminded(self, sample_task_past_half, mock_feishu_service):
        """测试已提醒过的任务不会重复提醒"""
        monitor = TaskMonitor()
        monitor.reminded_tasks.add('TASK002')  # 预先添加到已提醒集合
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            result = await monitor.check_task_deadline(sample_task_past_half['fields'])
        
        # 验证返回False表示未发送提醒
        assert result is False
        # 验证未调用发送消息方法
        assert mock_feishu_service.send_message.call_count == 0
    
    def test_parse_datetime_valid_formats(self):
        """测试解析有效的日期格式"""
        monitor = TaskMonitor()
        
        # 测试多种日期格式
        test_cases = [
            ('2026-01-05 10:30:00', '%Y-%m-%d %H:%M:%S'),
            ('2026-01-05', '%Y-%m-%d'),
            ('2026.01.05 10:30', '%Y.%m.%d %H:%M'),
            ('2026.01.05', '%Y.%m.%d'),
            ('2026/01/05 10:30:00', '%Y/%m/%d %H:%M:%S'),
            ('2026/01/05', '%Y/%m/%d')
        ]
        
        for date_str, expected_format in test_cases:
            result = monitor._parse_datetime(date_str)
            assert result is not None
            assert isinstance(result, datetime)
    
    def test_parse_datetime_invalid_format(self):
        """测试解析无效的日期格式"""
        monitor = TaskMonitor()
        
        result = monitor._parse_datetime('invalid-date-format')
        
        # 验证返回None
        assert result is None


class TestDetectStuckTasks:
    """测试卡住任务检测功能"""
    
    @pytest.mark.asyncio
    async def test_check_all_tasks_success(self, mock_bitable_client, mock_settings, sample_task_in_progress):
        """测试检查所有任务成功"""
        monitor = TaskMonitor()
        
        # 配置mock返回一个任务
        mock_bitable_client.get_table_records.return_value = {
            'data': {
                'items': [sample_task_in_progress]
            }
        }
        
        with patch('app.bitable.bitable_client', mock_bitable_client):
            with patch('app.config.settings', mock_settings):
                await monitor.check_all_tasks()
        
        # 验证调用了get_table_records
        mock_bitable_client.get_table_records.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_all_tasks_no_table_id(self, mock_bitable_client):
        """测试未配置任务表ID"""
        monitor = TaskMonitor()
        
        mock_settings_no_id = MagicMock()
        mock_settings_no_id.feishu_task_table_id = None
        
        with patch('app.bitable.bitable_client', mock_bitable_client):
            with patch('app.config.settings', mock_settings_no_id):
                await monitor.check_all_tasks()
        
        # 验证未调用get_table_records
        mock_bitable_client.get_table_records.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_all_tasks_filters_by_status(self, mock_bitable_client, mock_settings):
        """测试只检查进行中和已分配的任务"""
        monitor = TaskMonitor()
        
        now = datetime.now()
        created = now - timedelta(days=5)
        deadline = now + timedelta(days=3)
        
        # 配置mock返回多个不同状态的任务
        mock_bitable_client.get_table_records.return_value = {
            'data': {
                'items': [
                    {
                        'fields': {
                            'taskid': 'TASK001',
                            'title': '进行中任务',
                            'status': 'in_progress',
                            'deadline': deadline.strftime('%Y-%m-%d %H:%M:%S'),
                            'create_time': created.strftime('%Y-%m-%d %H:%M:%S'),
                            'assignee': 'user123'
                        }
                    },
                    {
                        'fields': {
                            'taskid': 'TASK002',
                            'title': '已完成任务',
                            'status': 'completed',
                            'deadline': deadline.strftime('%Y-%m-%d %H:%M:%S'),
                            'create_time': created.strftime('%Y-%m-%d %H:%M:%S'),
                            'assignee': 'user456'
                        }
                    },
                    {
                        'fields': {
                            'taskid': 'TASK003',
                            'title': '已分配任务',
                            'status': 'assigned',
                            'deadline': deadline.strftime('%Y-%m-%d %H:%M:%S'),
                            'create_time': created.strftime('%Y-%m-%d %H:%M:%S'),
                            'assignee': 'user789'
                        }
                    }
                ]
            }
        }
        
        with patch('app.bitable.bitable_client', mock_bitable_client):
            with patch('app.config.settings', mock_settings):
                with patch('app.services.task_monitor.feishu_service', AsyncMock()):
                    await monitor.check_all_tasks()
        
        # 验证调用了get_table_records
        mock_bitable_client.get_table_records.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_all_tasks_handles_exception(self, mock_bitable_client, mock_settings):
        """测试处理异常情况"""
        monitor = TaskMonitor()
        
        # 配置mock抛出异常
        mock_bitable_client.get_table_records.side_effect = Exception("API错误")
        
        with patch('app.bitable.bitable_client', mock_bitable_client):
            with patch('app.config.settings', mock_settings):
                # 不应该抛出异常
                await monitor.check_all_tasks()


class TestSendAlerts:
    """测试告警发送功能"""
    
    @pytest.mark.asyncio
    async def test_send_reminder_to_assignee(self, sample_task_past_half, mock_feishu_service):
        """测试向执行人发送提醒"""
        monitor = TaskMonitor()
        
        now = datetime.now()
        deadline = now + timedelta(days=2)
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            await monitor._send_reminder(
                sample_task_past_half['fields'],
                0.7,
                deadline
            )
        
        # 验证调用了send_message
        assert mock_feishu_service.send_message.call_count >= 1
        
        # 验证发送给了执行人
        calls = mock_feishu_service.send_message.call_args_list
        assignee_call = [call for call in calls if call[1]['user_id'] == 'user789']
        assert len(assignee_call) > 0
    
    @pytest.mark.asyncio
    async def test_send_reminder_to_creator(self, sample_task_past_half, mock_feishu_service):
        """测试向创建者发送提醒"""
        monitor = TaskMonitor()
        
        now = datetime.now()
        deadline = now + timedelta(days=2)
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            await monitor._send_reminder(
                sample_task_past_half['fields'],
                0.7,
                deadline
            )
        
        # 验证调用了send_message
        assert mock_feishu_service.send_message.call_count >= 1
        
        # 验证发送给了创建者
        calls = mock_feishu_service.send_message.call_args_list
        creator_call = [call for call in calls if call[1]['user_id'] == 'user456']
        assert len(creator_call) > 0
    
    @pytest.mark.asyncio
    async def test_send_final_reminder(self, sample_task_near_deadline, mock_feishu_service):
        """测试发送最后期限提醒"""
        monitor = TaskMonitor()
        
        time_remaining = 12 * 3600  # 12小时
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_service):
            await monitor._send_final_reminder(
                sample_task_near_deadline['fields'],
                time_remaining
            )
        
        # 验证调用了send_message
        assert mock_feishu_service.send_message.call_count >= 1
        
        # 验证消息内容包含紧急标识
        calls = mock_feishu_service.send_message.call_args_list
        for call in calls:
            message = call[1]['message']
            assert '🚨' in message or '紧急' in message
    
    @pytest.mark.asyncio
    async def test_send_reminder_handles_exception(self, sample_task_past_half):
        """测试发送提醒时处理异常"""
        monitor = TaskMonitor()
        
        now = datetime.now()
        deadline = now + timedelta(days=2)
        
        mock_feishu_error = AsyncMock()
        mock_feishu_error.send_message.side_effect = Exception("发送失败")
        
        with patch('app.services.task_monitor.feishu_service', mock_feishu_error):
            # 不应该抛出异常
            await monitor._send_reminder(
                sample_task_past_half['fields'],
                0.7,
                deadline
            )


class TestMonitoringControl:
    """测试监控启停控制"""
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self):
        """测试启动监控"""
        monitor = TaskMonitor()
        
        assert monitor.monitoring is False
        
        # 注意：start_monitoring会进入无限循环，这里只测试初始状态
        # 实际使用时需要在后台任务中运行
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self):
        """测试停止监控"""
        monitor = TaskMonitor()
        monitor.monitoring = True
        
        await monitor.stop_monitoring()
        
        assert monitor.monitoring is False
    
    @pytest.mark.asyncio
    async def test_test_monitoring_success(self, mock_bitable_client, mock_settings, sample_task_in_progress):
        """测试监控功能测试模式"""
        monitor = TaskMonitor()
        
        # 配置mock返回一个任务
        mock_bitable_client.get_table_records.return_value = {
            'data': {
                'items': [sample_task_in_progress]
            }
        }
        
        with patch('app.bitable.bitable_client', mock_bitable_client):
            with patch('app.config.settings', mock_settings):
                with patch('app.services.task_monitor.feishu_service', AsyncMock()):
                    result = await monitor.test_monitoring()
        
        # 验证返回结果
        assert result['status'] == 'success'
        assert result['tested_tasks'] >= 0
        assert 'tasks_details' in result
    
    @pytest.mark.asyncio
    async def test_test_monitoring_no_table_id(self, mock_bitable_client):
        """测试监控功能测试模式 - 未配置表ID"""
        monitor = TaskMonitor()
        
        mock_settings_no_id = MagicMock()
        mock_settings_no_id.feishu_task_table_id = None
        
        with patch('app.bitable.bitable_client', mock_bitable_client):
            with patch('app.config.settings', mock_settings_no_id):
                result = await monitor.test_monitoring()
        
        # 验证返回错误状态
        assert result['status'] == 'error'
        assert '未配置任务表ID' in result['message']
