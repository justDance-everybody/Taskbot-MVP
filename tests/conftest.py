"""
pytest配置文件
定义测试fixtures和全局配置
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 设置asyncio测试模式
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client():
    """测试客户端fixture"""
    from main import app
    return TestClient(app)


@pytest.fixture
async def async_client():
    """异步测试客户端fixture"""
    from main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_feishu_service():
    """模拟飞书服务"""
    mock = AsyncMock()
    mock.send_message = AsyncMock(return_value={"code": 0})
    mock.send_message_to_chat = AsyncMock(return_value={"code": 0})
    mock.send_card = AsyncMock(return_value={"code": 0})
    return mock


@pytest.fixture
def mock_task_manager():
    """模拟任务管理器"""
    mock = AsyncMock()
    mock.get_task = AsyncMock(return_value={
        "id": "TASK001",
        "title": "测试任务",
        "assignee_id": "user123",
        "chat_id": "chat456",
        "task_type": "code",
        "status": "in_progress"
    })
    mock.update_task_ci_status = AsyncMock(return_value=True)
    mock.complete_task = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_bitable_client():
    """模拟多维表格客户端"""
    mock = AsyncMock()
    mock.get_candidate_details = AsyncMock(return_value={
        "user_id": "user123",
        "name": "测试用户",
        "skills": ["Python", "FastAPI"],
        "experience_years": 3
    })
    return mock


@pytest.fixture
def sample_github_webhook_payload():
    """GitHub webhook载荷示例"""
    return {
        "action": "completed",
        "workflow_run": {
            "id": 123456789,
            "name": "CI Pipeline",
            "status": "completed",
            "conclusion": "success",
            "head_sha": "abc123def456",
            "html_url": "https://github.com/owner/repo/actions/runs/123456789",
            "updated_at": "2023-12-01T10:00:00Z"
        },
        "repository": {
            "name": "test-repo",
            "full_name": "owner/test-repo"
        },
        "task_metadata": {
            "task_id": "TASK001",
            "ci_passed": True,
            "quality_passed": True,
            "tests_passed": True,
            "integration_passed": True,
            "build_passed": True,
            "branch": "main",
            "commit_message": "TASK001: 完成用户登录功能"
        }
    }


@pytest.fixture
def sample_task_data():
    """任务数据示例"""
    return {
        "id": "TASK001",
        "title": "开发用户登录API",
        "description": "实现用户登录功能，包括密码验证和JWT token生成",
        "assignee_id": "user123",
        "chat_id": "chat456",
        "task_type": "code",
        "status": "in_progress",
        "created_at": "2023-12-01T09:00:00Z",
        "deadline": "2023-12-03T18:00:00Z",
        "skills_required": ["Python", "FastAPI", "JWT"],
        "acceptance_criteria": "API能正确验证用户凭据并返回有效token"
    }


@pytest.fixture
def github_headers():
    """GitHub webhook请求头"""
    return {
        "X-GitHub-Event": "workflow_run",
        "X-GitHub-Delivery": "12345678-1234-1234-1234-123456789012",
        "X-Hub-Signature-256": "sha256=test_signature",
        "Content-Type": "application/json"
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """设置测试环境变量"""
    # 设置测试环境变量
    monkeypatch.setenv("FEISHU_APP_ID", "test_app_id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "test_app_secret")
    monkeypatch.setenv("DEEPSEEK_KEY", "test_deepseek_key")
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test_webhook_secret")


# 测试数据库配置
@pytest.fixture(scope="session")
def test_db():
    """测试数据库配置"""
    # 这里可以配置测试数据库
    # 例如使用SQLite内存数据库
    pass


# 清理测试数据
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """每个测试后清理数据"""
    yield
    # 清理逻辑
    pass 