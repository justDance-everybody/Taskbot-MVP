"""
pytest配置文件
定义测试fixtures和全局配置
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
from datetime import datetime, timedelta

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


@pytest_asyncio.fixture
async def async_client():
    """异步测试客户端fixture"""
    from main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
def mock_bitable():
    """模拟Bitable客户端用于match服务测试"""
    mock = AsyncMock()
    mock.get_available_candidates = AsyncMock(return_value=[])
    mock.get_task = AsyncMock(return_value=None)
    mock.create_task = AsyncMock(return_value={"record_id": "rec123"})
    mock.update_task = AsyncMock(return_value=True)
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
    # 清空delivery缓存，避免测试间干扰
    from app.router.github_hook import clear_delivery_cache
    clear_delivery_cache()
    
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


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_service():
    """模拟LLM服务"""
    mock = AsyncMock()
    mock.call_with_retry = AsyncMock(return_value='{"result": "success"}')
    mock.analyze_resume = AsyncMock(return_value={
        "name": "测试用户",
        "skills": ["Python", "FastAPI"],
        "job_level": 3,
        "experience_years": 5
    })
    mock.match_candidates = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_cv_parser():
    """模拟CV解析器"""
    mock = AsyncMock()
    mock.parse_resume = AsyncMock(return_value={
        "name": "测试用户",
        "skills": ["Python", "FastAPI"],
        "job_level": 3,
        "experience_years": 5,
        "education": "本科",
        "work_experience": "5年开发经验",
        "projects": "多个项目",
        "needs_review": False
    })
    return mock


@pytest.fixture
def mock_match_service():
    """模拟匹配服务"""
    mock = AsyncMock()
    mock.find_top_candidates = AsyncMock(return_value=[
        {
            "user_id": "user_1",
            "name": "候选人1",
            "match_score": 95,
            "match_reason": "技能完全匹配"
        },
        {
            "user_id": "user_2",
            "name": "候选人2",
            "match_score": 85,
            "match_reason": "经验丰富"
        }
    ])
    mock.calculate_match_score = AsyncMock(return_value=(90, "技能匹配"))
    return mock


@pytest.fixture
def mock_scheduler():
    """模拟调度器"""
    mock = AsyncMock()
    mock.get_in_progress_tasks = AsyncMock(return_value=[])
    mock.get_completed_tasks = AsyncMock(return_value=[])
    mock.mark_reminded = AsyncMock(return_value=True)
    mock.send_reminder = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_ci_service():
    """模拟CI服务"""
    mock = AsyncMock()
    mock.process_ci_result = AsyncMock(return_value=True)
    mock.update_task_status = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_db_audit():
    """模拟数据库审计服务"""
    mock = AsyncMock()
    mock.log_operation = AsyncMock(return_value=True)
    mock.query_audit_logs = AsyncMock(return_value=[])
    mock.export_audit_report = AsyncMock(return_value="report.json")
    return mock


@pytest.fixture
def mock_task_monitor():
    """模拟任务监控服务"""
    mock = AsyncMock()
    mock.check_task_health = AsyncMock(return_value={"status": "healthy"})
    mock.detect_stuck_tasks = AsyncMock(return_value=[])
    mock.send_alerts = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_httpx_client():
    """模拟httpx.AsyncClient"""
    mock = AsyncMock()
    mock.post = AsyncMock()
    mock.get = AsyncMock()
    mock.put = AsyncMock()
    mock.delete = AsyncMock()
    
    # 配置默认响应
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 0, "msg": "success"}
    mock.post.return_value = mock_response
    mock.get.return_value = mock_response
    mock.put.return_value = mock_response
    mock.delete.return_value = mock_response
    
    return mock


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_resume_data():
    """简历数据示例"""
    return {
        "name": "张三",
        "skills": ["Python", "FastAPI", "Docker", "React"],
        "job_level": 3,
        "experience_years": 5,
        "education": "本科",
        "work_experience": "5年Python开发经验，熟悉微服务架构",
        "projects": "开发过多个Web项目和API服务",
        "needs_review": False
    }


@pytest.fixture
def sample_candidate_list():
    """候选人列表示例"""
    return [
        {
            "user_id": "user_1",
            "name": "候选人1",
            "skill_tags": ["Python", "FastAPI", "Docker"],
            "job_level": 3,
            "experience": 5,
            "years_experience": 5,
            "average_score": 90,
            "total_tasks": 20,
            "hours_available": 20
        },
        {
            "user_id": "user_2",
            "name": "候选人2",
            "skill_tags": ["Python", "React", "TypeScript"],
            "job_level": 2,
            "experience": 3,
            "years_experience": 3,
            "average_score": 85,
            "total_tasks": 15,
            "hours_available": 15
        },
        {
            "user_id": "user_3",
            "name": "候选人3",
            "skill_tags": ["Java", "Spring", "MySQL"],
            "job_level": 4,
            "experience": 7,
            "years_experience": 7,
            "average_score": 95,
            "total_tasks": 30,
            "hours_available": 10
        }
    ]


@pytest.fixture
def sample_feishu_message():
    """飞书消息示例"""
    return {
        "schema": "2.0",
        "header": {
            "event_id": "event_123",
            "event_type": "im.message.receive_v1",
            "create_time": "1609459200000",
            "token": "test_token",
            "app_id": "test_app_id"
        },
        "event": {
            "sender": {
                "sender_id": {
                    "user_id": "user_123",
                    "open_id": "open_123"
                },
                "sender_type": "user"
            },
            "message": {
                "message_id": "msg_123",
                "message_type": "text",
                "content": '{"text": "help"}',
                "create_time": "1609459200000"
            }
        }
    }


@pytest.fixture
def sample_card_action():
    """飞书卡片动作示例"""
    return {
        "open_id": "open_123",
        "user_id": "user_123",
        "action": {
            "value": {
                "action": "accept_task",
                "task_id": "task_123"
            },
            "tag": "button"
        }
    }


@pytest.fixture
def sample_ci_result():
    """CI结果示例"""
    return {
        "task_id": "task_123",
        "ci_passed": True,
        "quality_passed": True,
        "tests_passed": True,
        "integration_passed": True,
        "build_passed": True,
        "branch": "main",
        "commit_sha": "abc123",
        "commit_message": "TASK123: 完成功能开发"
    }


@pytest.fixture
def sample_audit_log():
    """审计日志示例"""
    return {
        "operation": "create_task",
        "user_id": "user_123",
        "task_id": "task_123",
        "timestamp": datetime.now().isoformat(),
        "details": {"title": "测试任务", "status": "pending"}
    }


@pytest.fixture
def sample_task_list():
    """任务列表示例"""
    return [
        {
            "task_id": "task_1",
            "title": "开发登录API",
            "description": "实现用户登录功能",
            "status": "pending",
            "skill_tags": ["Python", "FastAPI"],
            "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            "urgency": "high",
            "created_at": datetime.now().isoformat()
        },
        {
            "task_id": "task_2",
            "title": "优化数据库查询",
            "description": "提升查询性能",
            "status": "in_progress",
            "skill_tags": ["SQL", "PostgreSQL"],
            "deadline": (datetime.now() + timedelta(days=5)).isoformat(),
            "urgency": "normal",
            "created_at": (datetime.now() - timedelta(days=2)).isoformat()
        },
        {
            "task_id": "task_3",
            "title": "编写单元测试",
            "description": "为核心模块编写测试",
            "status": "completed",
            "skill_tags": ["Python", "pytest"],
            "deadline": (datetime.now() - timedelta(days=1)).isoformat(),
            "urgency": "normal",
            "created_at": (datetime.now() - timedelta(days=5)).isoformat()
        }
    ]


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_response(status_code=200, json_data=None, text_data=None):
    """创建模拟HTTP响应
    
    Args:
        status_code: HTTP状态码
        json_data: JSON响应数据
        text_data: 文本响应数据
    
    Returns:
        MagicMock: 模拟的响应对象
    """
    mock_response = MagicMock()
    mock_response.status_code = status_code
    
    if json_data is not None:
        mock_response.json.return_value = json_data
    
    if text_data is not None:
        mock_response.text = text_data
    
    return mock_response


def create_async_mock_with_return(return_value):
    """创建带返回值的AsyncMock
    
    Args:
        return_value: 要返回的值
    
    Returns:
        AsyncMock: 配置好的异步mock对象
    """
    mock = AsyncMock()
    mock.return_value = return_value
    return mock


def assert_called_with_partial(mock_obj, **expected_kwargs):
    """断言mock被调用时包含指定的关键字参数
    
    Args:
        mock_obj: Mock对象
        **expected_kwargs: 期望的关键字参数
    """
    assert mock_obj.called, "Mock对象未被调用"
    
    call_kwargs = mock_obj.call_args[1] if mock_obj.call_args else {}
    
    for key, expected_value in expected_kwargs.items():
        assert key in call_kwargs, f"参数 '{key}' 未在调用中找到"
        assert call_kwargs[key] == expected_value, \
            f"参数 '{key}' 的值不匹配: 期望 {expected_value}, 实际 {call_kwargs[key]}"


def create_task_with_status(status, **overrides):
    """创建指定状态的任务数据
    
    Args:
        status: 任务状态
        **overrides: 要覆盖的字段
    
    Returns:
        dict: 任务数据
    """
    task = {
        "task_id": f"task_{status}",
        "title": f"测试任务 - {status}",
        "description": "测试描述",
        "status": status,
        "skill_tags": ["Python"],
        "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
        "urgency": "normal",
        "created_at": datetime.now().isoformat()
    }
    task.update(overrides)
    return task


def create_candidate_with_skills(skills, **overrides):
    """创建具有指定技能的候选人数据
    
    Args:
        skills: 技能列表
        **overrides: 要覆盖的字段
    
    Returns:
        dict: 候选人数据
    """
    candidate = {
        "user_id": f"user_{len(skills)}",
        "name": f"候选人_{len(skills)}",
        "skill_tags": skills,
        "job_level": 3,
        "experience": 5,
        "years_experience": 5,
        "average_score": 85,
        "total_tasks": 10,
        "hours_available": 20
    }
    candidate.update(overrides)
    return candidate


async def wait_for_async_mock(mock_obj, timeout=1.0):
    """等待异步mock被调用
    
    Args:
        mock_obj: AsyncMock对象
        timeout: 超时时间（秒）
    """
    start_time = asyncio.get_event_loop().time()
    
    while not mock_obj.called:
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Mock对象在{timeout}秒内未被调用")
        await asyncio.sleep(0.01)


def reset_all_mocks(*mocks):
    """重置所有mock对象
    
    Args:
        *mocks: 要重置的mock对象
    """
    for mock in mocks:
        if hasattr(mock, 'reset_mock'):
            mock.reset_mock()


# ============================================================================
# Legacy Fixtures (保持向后兼容)
# ============================================================================


# ============================================================================
# Legacy Fixtures (保持向后兼容)
# ============================================================================

@pytest.fixture
def test_client():
    """测试客户端fixture"""
    from main import app
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """异步测试客户端fixture"""
    from main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
def mock_bitable():
    """模拟Bitable客户端用于match服务测试"""
    mock = AsyncMock()
    mock.get_available_candidates = AsyncMock(return_value=[])
    mock.get_task = AsyncMock(return_value=None)
    mock.create_task = AsyncMock(return_value={"record_id": "rec123"})
    mock.update_task = AsyncMock(return_value=True)
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
    # 清空delivery缓存，避免测试间干扰
    from app.router.github_hook import clear_delivery_cache
    clear_delivery_cache()
    
    return {
        "X-GitHub-Event": "workflow_run",
        "X-GitHub-Delivery": "12345678-1234-1234-1234-123456789012",
        "X-Hub-Signature-256": "sha256=test_signature",
        "Content-Type": "application/json"
    }


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