"""
Unit tests for feishu service module
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.feishu import FeishuService, MessageType


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Mock()
    settings.feishu.app_id = "test_app_id"
    settings.feishu.app_secret = "test_app_secret"
    settings.app.debug = False
    return settings


@pytest.fixture
def mock_client():
    """Mock lark client"""
    client = Mock()
    client.im.v1.message.create = AsyncMock()
    client.im.v1.chat.create = AsyncMock()
    client.im.v1.chat_member.create = AsyncMock()
    client.contact.v3.user.get = AsyncMock()
    return client


@pytest.fixture
def feishu_service(mock_settings, mock_client):
    """Create FeishuService instance with mocked dependencies"""
    with patch('app.services.feishu.get_settings', return_value=mock_settings), \
         patch('app.services.feishu.lark.Client.builder') as mock_builder:
        
        mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_client
        
        service = FeishuService()
        return service


class TestFeishuService:
    """Test FeishuService class"""
    
    @pytest.mark.asyncio
    async def test_send_text_message(self, feishu_service, mock_client):
        """Test sending text message"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.message_id = "test_message_id"
        mock_client.im.v1.message.create.return_value = mock_response
        
        # Test sending text message
        result = await feishu_service.send_text_message("test_chat_id", "Hello, World!")
        
        assert result == "test_message_id"
        mock_client.im.v1.message.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self, feishu_service, mock_client):
        """Test message sending failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.success.return_value = False
        mock_response.msg = "Send failed"
        mock_client.im.v1.message.create.return_value = mock_response
        
        # Test message sending failure
        with pytest.raises(Exception, match="Failed to send message"):
            await feishu_service.send_text_message("test_chat_id", "Hello, World!")
    
    @pytest.mark.asyncio
    async def test_send_interactive_card(self, feishu_service, mock_client):
        """Test sending interactive card"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.message_id = "test_card_message_id"
        mock_client.im.v1.message.create.return_value = mock_response
        
        # Test card
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "**Test Card**"}
                }
            ]
        }
        
        # Test sending interactive card
        result = await feishu_service.send_interactive_card("test_chat_id", card)
        
        assert result == "test_card_message_id"
        mock_client.im.v1.message.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_group_chat(self, feishu_service, mock_client):
        """Test creating group chat"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.chat_id = "test_chat_id"
        mock_client.im.v1.chat.create.return_value = mock_response
        
        # Test creating group chat
        result = await feishu_service.create_group_chat(
            name="Test Group",
            description="Test Description",
            user_ids=["user1", "user2"]
        )
        
        assert result == "test_chat_id"
        mock_client.im.v1.chat.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_chat_members(self, feishu_service, mock_client):
        """Test adding chat members"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_client.im.v1.chat_member.create.return_value = mock_response
        
        # Test adding chat members
        result = await feishu_service.add_chat_members("test_chat_id", ["user3", "user4"])
        
        assert result is True
        mock_client.im.v1.chat_member.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, feishu_service, mock_client):
        """Test getting user info"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_user = Mock()
        mock_user.user_id = "test_user_id"
        mock_user.name = "Test User"
        mock_user.en_name = "Test User EN"
        mock_user.email = "test@example.com"
        mock_user.mobile = "+1234567890"
        mock_user.status = "active"
        mock_response.data.user = mock_user
        mock_client.contact.v3.user.get.return_value = mock_response
        
        # Test getting user info
        result = await feishu_service.get_user_info("test_user_id")
        
        assert result["user_id"] == "test_user_id"
        assert result["name"] == "Test User"
        assert result["email"] == "test@example.com"
        mock_client.contact.v3.user.get.assert_called_once()
    
    def test_create_task_selection_card(self, feishu_service):
        """Test creating task selection card"""
        candidates = [
            {
                "user_id": "user1",
                "name": "Alice",
                "match_score": 95,
                "skill_tags": ["Python", "FastAPI"]
            },
            {
                "user_id": "user2", 
                "name": "Bob",
                "match_score": 85,
                "skill_tags": ["JavaScript", "React"]
            },
            {
                "user_id": "user3",
                "name": "Charlie",
                "match_score": 75,
                "skill_tags": ["Python", "Django"]
            }
        ]
        
        card = feishu_service.create_task_selection_card(
            "Test Task",
            "Test task description",
            candidates
        )
        
        assert "config" in card
        assert "elements" in card
        assert card["config"]["wide_screen_mode"] is True
        
        # Check that candidates are included
        elements = card["elements"]
        action_elements = [e for e in elements if e.get("tag") == "action"]
        assert len(action_elements) == 3  # One for each candidate
    
    def test_create_task_result_card(self, feishu_service):
        """Test creating task result card"""
        # Test success card
        success_card = feishu_service.create_task_result_card(
            "Test Task",
            "success",
            "Task completed successfully",
            "Additional details here"
        )
        
        assert "config" in success_card
        assert "elements" in success_card
        assert success_card["config"]["wide_screen_mode"] is True
        
        # Test failure card
        failure_card = feishu_service.create_task_result_card(
            "Test Task",
            "failure",
            "Task failed",
            "Error details here"
        )
        
        assert "config" in failure_card
        assert "elements" in failure_card
    
    def test_parse_message_event(self, feishu_service):
        """Test parsing message event"""
        event_data = {
            "event": {
                "message": {
                    "message_id": "test_message_id",
                    "chat_id": "test_chat_id",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": '{"text": "Hello, World!"}',
                    "create_time": "1640995200000"
                },
                "sender": {
                    "sender_id": {"user_id": "test_user_id"},
                    "sender_type": "user"
                }
            }
        }
        
        result = feishu_service.parse_message_event(event_data)
        
        assert result is not None
        assert result["message_id"] == "test_message_id"
        assert result["chat_id"] == "test_chat_id"
        assert result["sender_id"] == "test_user_id"
        assert result["message_type"] == "text"
    
    def test_parse_message_event_invalid(self, feishu_service):
        """Test parsing invalid message event"""
        event_data = {}
        
        result = feishu_service.parse_message_event(event_data)
        
        assert result is None
    
    def test_parse_card_action_event(self, feishu_service):
        """Test parsing card action event"""
        event_data = {
            "event": {
                "message_id": "test_message_id",
                "chat_id": "test_chat_id",
                "action": {
                    "value": {"action": "select_candidate", "user_id": "test_user_id"},
                    "tag": "button"
                },
                "user": {"user_id": "test_user_id"},
                "timestamp": "1640995200"
            }
        }
        
        result = feishu_service.parse_card_action_event(event_data)
        
        assert result is not None
        assert result["message_id"] == "test_message_id"
        assert result["chat_id"] == "test_chat_id"
        assert result["action_value"]["action"] == "select_candidate"
        assert result["user_id"] == "test_user_id"
    
    def test_is_bot_mentioned(self, feishu_service):
        """Test bot mention detection"""
        assert feishu_service.is_bot_mentioned("@bot 新任务") is True
        assert feishu_service.is_bot_mentioned("新任务：创建API") is True
        assert feishu_service.is_bot_mentioned("Hello world") is False
        assert feishu_service.is_bot_mentioned("@BOT help") is True  # Case insensitive
    
    def test_extract_task_from_message(self, feishu_service):
        """Test extracting task from message"""
        # Test structured format
        structured_message = """@bot 新任务
标题: 创建用户API
描述: 实现用户注册和登录API
技能: Python, FastAPI, PostgreSQL
截止: 2024-01-15"""
        
        result = feishu_service.extract_task_from_message(structured_message)
        
        assert result is not None
        assert result["title"] == "创建用户API"
        assert result["description"] == "实现用户注册和登录API"
        assert "Python" in result["skill_tags"]
        assert "FastAPI" in result["skill_tags"]
        assert result["deadline"] == "2024-01-15"
        
        # Test unstructured format
        unstructured_message = "@bot 新任务 帮我写一个简单的计算器程序"
        
        result = feishu_service.extract_task_from_message(unstructured_message)
        
        assert result is not None
        assert "计算器程序" in result["title"]
        assert "计算器程序" in result["description"]
        
        # Test invalid message
        invalid_message = "Hello world"
        
        result = feishu_service.extract_task_from_message(invalid_message)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_send_daily_report(self, feishu_service, mock_client):
        """Test sending daily report"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.message_id = "test_report_message_id"
        mock_client.im.v1.message.create.return_value = mock_response
        
        stats = {
            "total": 10,
            "done": 6,
            "in_progress": 2,
            "returned": 1,
            "draft": 1,
            "assigned": 0,
            "archived": 0
        }
        
        result = await feishu_service.send_daily_report("test_chat_id", stats)
        
        assert result == "test_report_message_id"
        mock_client.im.v1.message.create.assert_called_once()


class TestMessageType:
    """Test MessageType constants"""
    
    def test_message_types(self):
        """Test message type constants"""
        assert MessageType.TEXT == "text"
        assert MessageType.POST == "post"
        assert MessageType.IMAGE == "image"
        assert MessageType.INTERACTIVE == "interactive"
