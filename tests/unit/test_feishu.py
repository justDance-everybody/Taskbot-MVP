"""
Feishu服务测试
测试飞书API客户端的消息发送、重试逻辑等功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import json
from datetime import datetime


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_lark_client():
    """模拟Lark SDK客户端"""
    mock = MagicMock()
    
    # 模拟消息发送响应
    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.code = 0
    mock_response.msg = "success"
    
    # 配置消息API
    mock.im.v1.message.create.return_value = mock_response
    
    return mock


@pytest.fixture
def mock_httpx_client():
    """模拟httpx.AsyncClient用于HTTP请求"""
    mock = AsyncMock()
    
    # 模拟成功响应
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'code': 0,
        'msg': 'success',
        'tenant_access_token': 'test_access_token',
        'data': {
            'chat_id': 'oc_test_chat_123'
        }
    }
    mock_response.text = json.dumps(mock_response.json.return_value)
    
    mock.post = AsyncMock(return_value=mock_response)
    mock.get = AsyncMock(return_value=mock_response)
    
    return mock


@pytest.fixture
def sample_card_data():
    """卡片消息数据示例"""
    return {
        "config": {
            "wide_screen_mode": True
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": "**测试卡片**\n这是一条测试消息",
                    "tag": "lark_md"
                }
            }
        ]
    }


@pytest.fixture
def sample_task_data():
    """任务数据示例"""
    return {
        'task_id': 'task_123',
        'title': '开发用户登录API',
        'description': '实现用户登录功能',
        'deadline': '2026-01-15 18:00:00',
        'priority': 'high'
    }


@pytest.fixture
def sample_candidates():
    """候选人数据示例"""
    return [
        {
            'user_id': 'user_1',
            'name': 'Alice',
            'skills': ['Python', 'FastAPI']
        },
        {
            'user_id': 'user_2',
            'name': 'Bob',
            'skills': ['JavaScript', 'React']
        }
    ]


# ============================================================================
# Test Classes
# ============================================================================

class TestFeishuAPIClient:
    """测试飞书API客户端"""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_lark_client):
        """测试send_message成功场景"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_message('user_123', 'Test message')
            
            # Assert
            assert result is True
            mock_lark_client.im.v1.message.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_timeout(self, mock_lark_client):
        """测试send_message超时"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟超时异常
            mock_lark_client.im.v1.message.create.side_effect = TimeoutError("Request timeout")
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_message('user_123', 'Test message')
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self, mock_lark_client):
        """测试send_message API错误"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟API错误响应
            mock_response = MagicMock()
            mock_response.success.return_value = False
            mock_response.code = 99991663
            mock_response.msg = "user not found"
            mock_lark_client.im.v1.message.create.return_value = mock_response
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_message('invalid_user', 'Test message')
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_to_chat_success(self, mock_lark_client):
        """测试send_message_to_chat成功场景"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_message_to_chat('chat_123', 'Test message')
            
            # Assert
            assert result is True
            mock_lark_client.im.v1.message.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_text_message_with_user_id(self, mock_lark_client):
        """测试send_text_message使用user_id"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_text_message(user_id='user_123', text='Test message')
            
            # Assert
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_text_message_with_chat_id(self, mock_lark_client):
        """测试send_text_message使用chat_id"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_text_message(chat_id='chat_123', text='Test message')
            
            # Assert
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_text_message_without_recipient(self, mock_lark_client):
        """测试send_text_message缺少接收者"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_text_message(text='Test message')
            
            # Assert
            assert result is False


class TestFeishuCardMessages:
    """测试飞书卡片消息"""
    
    @pytest.mark.asyncio
    async def test_send_card_message_to_user(self, mock_lark_client, sample_card_data):
        """测试发送卡片消息给用户"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_card_message(user_id='user_123', card=sample_card_data)
            
            # Assert
            assert result is True
            mock_lark_client.im.v1.message.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_card_message_to_chat(self, mock_lark_client, sample_card_data):
        """测试发送卡片消息到群聊"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_card_message(chat_id='chat_123', card=sample_card_data)
            
            # Assert
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_card_message_without_card(self, mock_lark_client):
        """测试发送空卡片消息"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_card_message(user_id='user_123', card=None)
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_candidate_cards(self, mock_lark_client, sample_candidates):
        """测试发送候选人卡片"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_candidate_cards('chat_123', sample_candidates, 'task_123')
            
            # Assert
            assert result is True
            mock_lark_client.im.v1.message.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_task_notification(self, mock_lark_client, sample_task_data):
        """测试发送任务通知"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_task_notification('user_123', sample_task_data)
            
            # Assert
            assert result is True
            mock_lark_client.im.v1.message.create.assert_called_once()


class TestFeishuChatOperations:
    """测试飞书群聊操作"""
    
    @pytest.mark.asyncio
    async def test_create_chat_success(self, mock_lark_client, mock_httpx_client):
        """测试创建群聊成功"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟AsyncClient上下文管理器
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_httpx_client
            mock_context.__aexit__.return_value = None
            
            with patch('httpx.AsyncClient', return_value=mock_context):
                from app.services.feishu import FeishuService
                service = FeishuService()
                
                # Act
                result = await service.create_chat('Test Chat', ['user_1', 'user_2'])
                
                # Assert
                assert result == 'oc_test_chat_123'
                mock_httpx_client.post.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_chat_api_error(self, mock_lark_client, mock_httpx_client):
        """测试创建群聊API错误"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟API错误响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 99991663,
                'msg': 'user not found'
            }
            mock_response.text = json.dumps(mock_response.json.return_value)
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            
            # 模拟AsyncClient上下文管理器
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_httpx_client
            mock_context.__aexit__.return_value = None
            
            with patch('httpx.AsyncClient', return_value=mock_context):
                from app.services.feishu import FeishuService
                service = FeishuService()
                
                # Act
                result = await service.create_chat('Test Chat', ['invalid_user'])
                
                # Assert
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_access_token_success(self, mock_lark_client, mock_httpx_client):
        """测试获取访问令牌成功"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟AsyncClient上下文管理器
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_httpx_client
            mock_context.__aexit__.return_value = None
            
            with patch('httpx.AsyncClient', return_value=mock_context):
                from app.services.feishu import FeishuService
                service = FeishuService()
                
                # Act
                result = await service._get_access_token()
                
                # Assert
                assert result == 'test_access_token'
    
    @pytest.mark.asyncio
    async def test_get_access_token_failure(self, mock_lark_client, mock_httpx_client):
        """测试获取访问令牌失败"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟失败响应
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'code': 99991663,
                'msg': 'invalid app_id or app_secret'
            }
            mock_response.text = json.dumps(mock_response.json.return_value)
            mock_httpx_client.post = AsyncMock(return_value=mock_response)
            
            # 模拟AsyncClient上下文管理器
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_httpx_client
            mock_context.__aexit__.return_value = None
            
            with patch('httpx.AsyncClient', return_value=mock_context):
                from app.services.feishu import FeishuService
                service = FeishuService()
                
                # Act
                result = await service._get_access_token()
                
                # Assert
                assert result is None


class TestFeishuRetryLogic:
    """测试重试逻辑"""
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, mock_lark_client):
        """测试超时重试"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟第一次超时，第二次成功
            mock_lark_client.im.v1.message.create.side_effect = [
                TimeoutError("Request timeout"),
                MagicMock(success=lambda: True, code=0, msg="success")
            ]
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act - 第一次调用会超时
            result1 = await service.send_message('user_123', 'Test message')
            # 第二次调用应该成功
            result2 = await service.send_message('user_123', 'Test message')
            
            # Assert
            assert result1 is False  # 第一次超时失败
            assert result2 is True   # 第二次成功
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, mock_lark_client):
        """测试速率限制重试"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟速率限制错误
            mock_response = MagicMock()
            mock_response.success.return_value = False
            mock_response.code = 99991400
            mock_response.msg = "rate limit exceeded"
            mock_lark_client.im.v1.message.create.return_value = mock_response
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_message('user_123', 'Test message')
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_lark_client):
        """测试最大重试次数"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟持续超时
            mock_lark_client.im.v1.message.create.side_effect = TimeoutError("Request timeout")
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act - 多次调用都会失败
            results = []
            for _ in range(3):
                result = await service.send_message('user_123', 'Test message')
                results.append(result)
            
            # Assert - 所有调用都应该失败
            assert all(r is False for r in results)


class TestFeishuErrorHandling:
    """测试错误处理"""
    
    @pytest.mark.asyncio
    async def test_send_message_with_exception(self, mock_lark_client):
        """测试发送消息时的异常处理"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟异常
            mock_lark_client.im.v1.message.create.side_effect = Exception("Unexpected error")
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_message('user_123', 'Test message')
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_create_chat_with_exception(self, mock_lark_client, mock_httpx_client):
        """测试创建群聊时的异常处理"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟异常
            mock_httpx_client.post.side_effect = Exception("Network error")
            
            # 模拟AsyncClient上下文管理器
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_httpx_client
            mock_context.__aexit__.return_value = None
            
            with patch('httpx.AsyncClient', return_value=mock_context):
                from app.services.feishu import FeishuService
                service = FeishuService()
                
                # Act
                result = await service.create_chat('Test Chat', ['user_1'])
                
                # Assert
                assert result is None
    
    @pytest.mark.asyncio
    async def test_send_candidate_cards_with_exception(self, mock_lark_client, sample_candidates):
        """测试发送候选人卡片时的异常处理"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟异常
            mock_lark_client.im.v1.message.create.side_effect = Exception("Card creation error")
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_candidate_cards('chat_123', sample_candidates, 'task_123')
            
            # Assert
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_task_notification_with_exception(self, mock_lark_client, sample_task_data):
        """测试发送任务通知时的异常处理"""
        # Arrange
        with patch('app.services.feishu.lark.Client.builder') as mock_builder:
            mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_lark_client
            
            # 模拟异常
            mock_lark_client.im.v1.message.create.side_effect = Exception("Notification error")
            
            from app.services.feishu import FeishuService
            service = FeishuService()
            
            # Act
            result = await service.send_task_notification('user_123', sample_task_data)
            
            # Assert
            assert result is False
