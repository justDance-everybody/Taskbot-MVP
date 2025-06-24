"""
Unit tests for bitable module
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.bitable import BitableClient, TaskStatus, CIState, FieldType


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Mock()
    settings.feishu.app_id = "test_app_id"
    settings.feishu.app_secret = "test_app_secret"
    settings.feishu.bitable_app_token = "test_app_token"
    settings.feishu.task_table_id = "test_task_table"
    settings.feishu.person_table_id = "test_person_table"
    settings.app.debug = False
    return settings


@pytest.fixture
def mock_client():
    """Mock lark client"""
    client = Mock()
    client.bitable.v1.app_table.create = AsyncMock()
    client.bitable.v1.app_table_record.create = AsyncMock()
    client.bitable.v1.app_table_record.update = AsyncMock()
    client.bitable.v1.app_table_record.get = AsyncMock()
    client.bitable.v1.app_table_record.list = AsyncMock()
    client.bitable.v1.app_table_record.delete = AsyncMock()
    return client


@pytest.fixture
def bitable_client(mock_settings, mock_client):
    """Create BitableClient instance with mocked dependencies"""
    with patch('app.bitable.get_settings', return_value=mock_settings), \
         patch('app.bitable.lark.Client.builder') as mock_builder:
        
        mock_builder.return_value.app_id.return_value.app_secret.return_value.log_level.return_value.build.return_value = mock_client
        
        client = BitableClient()
        return client


class TestBitableClient:
    """Test BitableClient class"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, bitable_client, mock_client):
        """Test task creation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.record_id = "test_record_id"
        mock_client.bitable.v1.app_table_record.create.return_value = mock_response
        
        # Test task creation
        result = await bitable_client.create_task(
            title="Test Task",
            description="Test Description",
            skill_tags=["Python", "FastAPI"]
        )
        
        assert result == "test_record_id"
        mock_client.bitable.v1.app_table_record.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_failure(self, bitable_client, mock_client):
        """Test task creation failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.success.return_value = False
        mock_response.msg = "Creation failed"
        mock_client.bitable.v1.app_table_record.create.return_value = mock_response
        
        # Test task creation failure
        with pytest.raises(Exception, match="Failed to add record"):
            await bitable_client.create_task(
                title="Test Task",
                description="Test Description",
                skill_tags=["Python"]
            )
    
    @pytest.mark.asyncio
    async def test_assign_task(self, bitable_client, mock_client):
        """Test task assignment"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_client.bitable.v1.app_table_record.update.return_value = mock_response
        
        # Test task assignment
        result = await bitable_client.assign_task(
            task_record_id="test_task_id",
            assignee_id="test_user_id",
            child_chat_id="test_chat_id"
        )
        
        assert result is True
        mock_client.bitable.v1.app_table_record.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, bitable_client, mock_client):
        """Test task status update"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_client.bitable.v1.app_table_record.update.return_value = mock_response
        
        # Test status update
        result = await bitable_client.update_task_status(
            task_record_id="test_task_id",
            status=TaskStatus.DONE,
            ci_state=CIState.SUCCESS,
            ai_score=85
        )
        
        assert result is True
        mock_client.bitable.v1.app_table_record.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task(self, bitable_client, mock_client):
        """Test getting task"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.record.fields = {"title": "Test Task", "status": "Draft"}
        mock_client.bitable.v1.app_table_record.get.return_value = mock_response
        
        # Test getting task
        result = await bitable_client.get_task("test_task_id")
        
        assert result == {"title": "Test Task", "status": "Draft"}
        mock_client.bitable.v1.app_table_record.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, bitable_client, mock_client):
        """Test listing tasks"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_item = Mock()
        mock_item.record_id = "test_record_id"
        mock_item.fields = {"title": "Test Task"}
        mock_item.created_time = "2024-01-01T00:00:00Z"
        mock_item.last_modified_time = "2024-01-01T00:00:00Z"
        mock_response.data.items = [mock_item]
        mock_client.bitable.v1.app_table_record.list.return_value = mock_response
        
        # Test listing tasks
        result = await bitable_client.list_tasks()
        
        assert len(result) == 1
        assert result[0]["record_id"] == "test_record_id"
        assert result[0]["fields"]["title"] == "Test Task"
    
    @pytest.mark.asyncio
    async def test_create_person(self, bitable_client, mock_client):
        """Test person creation"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.record_id = "test_person_id"
        mock_client.bitable.v1.app_table_record.create.return_value = mock_response
        
        # Test person creation
        result = await bitable_client.create_person(
            user_id="test_user_id",
            name="Test User",
            skill_tags=["Python", "JavaScript"],
            hours_available=40,
            performance=85.0
        )
        
        assert result == "test_person_id"
        mock_client.bitable.v1.app_table_record.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_person_by_user_id(self, bitable_client, mock_client):
        """Test getting person by user ID"""
        # Mock successful response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_item = Mock()
        mock_item.record_id = "test_record_id"
        mock_item.fields = {"user_id": "test_user_id", "name": "Test User"}
        mock_item.created_time = "2024-01-01T00:00:00Z"
        mock_item.last_modified_time = "2024-01-01T00:00:00Z"
        mock_response.data.items = [mock_item]
        mock_client.bitable.v1.app_table_record.list.return_value = mock_response
        
        # Test getting person by user ID
        result = await bitable_client.get_person_by_user_id("test_user_id")
        
        assert result is not None
        assert result["fields"]["user_id"] == "test_user_id"
        assert result["fields"]["name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_person_by_user_id_not_found(self, bitable_client, mock_client):
        """Test getting person by user ID when not found"""
        # Mock empty response
        mock_response = Mock()
        mock_response.success.return_value = True
        mock_response.data.items = []
        mock_client.bitable.v1.app_table_record.list.return_value = mock_response
        
        # Test getting person by user ID
        result = await bitable_client.get_person_by_user_id("nonexistent_user_id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_daily_task_stats(self, bitable_client, mock_client):
        """Test getting daily task statistics"""
        # Mock successful response with various task statuses
        mock_response = Mock()
        mock_response.success.return_value = True
        
        # Create mock tasks with different statuses
        mock_tasks = []
        statuses = ["Draft", "Assigned", "InProgress", "Done", "Returned"]
        for i, status in enumerate(statuses):
            mock_item = Mock()
            mock_item.record_id = f"task_{i}"
            mock_item.fields = {"status": status, "title": f"Task {i}"}
            mock_item.created_time = "2024-01-01T00:00:00Z"
            mock_item.last_modified_time = "2024-01-01T00:00:00Z"
            mock_tasks.append(mock_item)
        
        mock_response.data.items = mock_tasks
        mock_client.bitable.v1.app_table_record.list.return_value = mock_response
        
        # Test getting daily stats
        result = await bitable_client.get_daily_task_stats()
        
        assert result["total"] == 5
        assert result["draft"] == 1
        assert result["assigned"] == 1
        assert result["in_progress"] == 1
        assert result["done"] == 1
        assert result["returned"] == 1


class TestEnums:
    """Test enum classes"""
    
    def test_task_status_enum(self):
        """Test TaskStatus enum"""
        assert TaskStatus.DRAFT.value == "Draft"
        assert TaskStatus.ASSIGNED.value == "Assigned"
        assert TaskStatus.IN_PROGRESS.value == "InProgress"
        assert TaskStatus.RETURNED.value == "Returned"
        assert TaskStatus.DONE.value == "Done"
        assert TaskStatus.ARCHIVED.value == "Archived"
    
    def test_ci_state_enum(self):
        """Test CIState enum"""
        assert CIState.PENDING.value == "Pending"
        assert CIState.SUCCESS.value == "Success"
        assert CIState.FAILURE.value == "Failure"
        assert CIState.ERROR.value == "Error"
    
    def test_field_type_enum(self):
        """Test FieldType enum"""
        assert FieldType.TEXT.value == 1
        assert FieldType.NUMBER.value == 2
        assert FieldType.SINGLE_SELECT.value == 3
        assert FieldType.MULTI_SELECT.value == 4
