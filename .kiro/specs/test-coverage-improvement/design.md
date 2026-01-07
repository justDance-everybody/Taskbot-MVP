# Design Document

## Overview

本设计文档描述测试覆盖率提升项目的技术方案。当前状态：24%行覆盖率，33个失败测试。目标：修复所有测试，达到60%行覆盖率和75%函数覆盖率。

## Architecture

### 当前测试结构

```
tests/
├── unit/
│   ├── test_cv_parser.py          (9 tests, 9 failing)
│   ├── test_match.py              (7 tests, 7 failing)
│   ├── test_scheduler.py          (4 tests, 4 failing)
│   ├── test_task_manager.py       (13 tests, 13 failing)
│   ├── test_github_webhook.py     (passing)
│   └── test_*_properties.py       (passing)
├── integration/
│   ├── test_api.py                (passing)
│   └── test_feishu_hook.py        (passing)
└── conftest.py
```

### 覆盖率现状

| 模块 | 当前覆盖率 | 目标覆盖率 | 优先级 |
|-----|----------|----------|--------|
| webhooks.py | 11% | 40% | 高 (可提升15%) |
| bitable.py | 16% | 60% | 高 (可提升8%) |
| feishu.py | 17% | 50% | 中 |
| llm.py | 17% | 50% | 中 |
| task_manager.py | 48% | 60% | 中 |
| scheduler.py | 41% | 60% | 中 |
| match.py | 57% | 70% | 低 |
| cv_parser.py | 59% | 70% | 低 |
| ci.py | 0% | 30% | 低 |
| db_audit.py | 0% | 30% | 低 |
| task_monitor.py | 0% | 30% | 低 |

## Components and Interfaces

### 1. 测试修复策略

**阶段1：修复Mock问题**

失败测试的主要原因是mock配置不正确。需要：

```python
# 正确的mock模式
@pytest.fixture
def mock_bitable():
    with patch('app.services.match.Bitable') as mock:
        instance = mock.return_value
        instance.get_available_candidates = AsyncMock(return_value=[...])
        yield instance

# 使用fixture
@pytest.mark.asyncio
async def test_find_top_candidates(mock_bitable):
    service = MatchService(mock_bitable)
    result = await service.find_top_candidates(task_data)
    assert len(result) == 2
```

**阶段2：添加缺失的Mock**

需要为以下服务添加mock：
- `app.bitable.Bitable` → 数据库操作
- `app.services.feishu.FeishuService` → 飞书API
- `app.services.llm.LLMService` → LLM调用
- `httpx.AsyncClient` → HTTP请求

### 2. Bitable测试设计

**文件**: `tests/unit/test_bitable.py` (新增)

**测试范围**:
```python
class TestBitableTaskOperations:
    """测试任务CRUD操作"""
    async def test_create_task_record()
    async def test_get_task_by_id()
    async def test_update_task_status()
    async def test_delete_task_record()
    async def test_list_tasks_with_filters()

class TestBitableCandidateOperations:
    """测试候选人CRUD操作"""
    async def test_create_candidate_record()
    async def test_get_candidate_by_id()
    async def test_get_available_candidates()
    async def test_update_candidate_status()

class TestBitableErrorHandling:
    """测试错误处理"""
    async def test_api_timeout_handling()
    async def test_api_error_response()
    async def test_invalid_record_id()
```

### 3. Webhook测试设计

**文件**: `tests/unit/test_webhooks.py` (新增)

**测试范围**:
```python
class TestMessageRouting:
    """测试消息路由"""
    async def test_route_text_message()
    async def test_route_card_action()
    async def test_route_unknown_event()

class TestCommandParsing:
    """测试命令解析"""
    async def test_parse_help_command()
    async def test_parse_status_command()
    async def test_parse_report_command()
    async def test_parse_invalid_command()

class TestWebhookErrorHandling:
    """测试错误处理"""
    async def test_handle_invalid_signature()
    async def test_handle_malformed_payload()
    async def test_handle_service_exception()
```

### 4. 外部服务测试设计

**文件**: `tests/unit/test_feishu.py` (新增)

```python
class TestFeishuAPIClient:
    """测试飞书API客户端"""
    async def test_send_message_success()
    async def test_send_message_timeout()
    async def test_send_message_api_error()
    async def test_get_user_info()
    async def test_create_group_chat()

class TestFeishuRetryLogic:
    """测试重试逻辑"""
    async def test_retry_on_timeout()
    async def test_retry_on_rate_limit()
    async def test_max_retries_exceeded()
```

**文件**: `tests/unit/test_llm.py` (新增)

```python
class TestLLMService:
    """测试LLM服务"""
    async def test_analyze_resume_success()
    async def test_analyze_resume_timeout()
    async def test_model_fallback()
    async def test_match_candidates()

class TestLLMErrorHandling:
    """测试错误处理"""
    async def test_handle_api_timeout()
    async def test_handle_invalid_response()
    async def test_handle_rate_limit()
```

### 5. 未覆盖模块测试设计

**文件**: `tests/unit/test_ci.py` (新增)

```python
class TestCIService:
    """测试CI服务"""
    async def test_process_ci_result_success()
    async def test_process_ci_result_failure()
    async def test_update_task_status()
```

**文件**: `tests/unit/test_db_audit.py` (新增)

```python
class TestDBAudit:
    """测试数据库审计"""
    async def test_log_operation()
    async def test_query_audit_logs()
    async def test_export_audit_report()
```

**文件**: `tests/unit/test_task_monitor.py` (新增)

```python
class TestTaskMonitor:
    """测试任务监控"""
    async def test_check_task_health()
    async def test_detect_stuck_tasks()
    async def test_send_alerts()
```

## Data Models

### Mock数据模板

```python
# conftest.py中的共享fixtures

@pytest.fixture
def sample_task_data():
    return {
        'task_id': 'task_123',
        'title': 'Test Task',
        'description': 'Test Description',
        'status': 'Pending',
        'skill_tags': ['Python', 'FastAPI'],
        'deadline': '2026-01-15T00:00:00',
        'created_at': '2026-01-05T00:00:00'
    }

@pytest.fixture
def sample_candidate_data():
    return {
        'user_id': 'user_123',
        'name': 'Test User',
        'skills': ['Python', 'FastAPI', 'React'],
        'years_experience': 3,
        'hours_available': 20,
        'updated_at': '2026-01-05T00:00:00'
    }

@pytest.fixture
def mock_bitable_client():
    with patch('app.bitable.Bitable') as mock:
        instance = mock.return_value
        # 配置所有常用方法
        instance.get_task = AsyncMock()
        instance.create_task = AsyncMock()
        instance.update_task = AsyncMock()
        instance.get_available_candidates = AsyncMock()
        yield instance
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Test Isolation

*For any* test in the test suite, running it independently SHALL produce the same result as running it with other tests.

**Validates: Requirements 7.5**

### Property 2: Mock Consistency

*For any* mocked service, the mock behavior SHALL match the actual service interface and return types.

**Validates: Requirements 1.5, 7.2**

### Property 3: Coverage Monotonicity

*For any* new test added, the overall coverage SHALL not decrease.

**Validates: Requirements 6.1, 6.2**

### Property 4: Test Execution Time

*For any* complete test suite run, execution time SHALL not exceed 30 seconds.

**Validates: Requirements 6.4**

## Error Handling

| 场景 | 处理方式 |
|-----|---------|
| Mock未正确配置 | 使用conftest.py中的共享fixtures |
| 异步测试失败 | 确保使用@pytest.mark.asyncio装饰器 |
| 外部API调用 | 使用patch和AsyncMock替换 |
| 测试数据冲突 | 每个测试使用独立的fixture实例 |
| 覆盖率计算错误 | 使用--cov-report=term-missing查看详情 |

## Testing Strategy

### 修复优先级

**P0 - 立即修复 (第1周)**:
1. 修复33个失败的单元测试
2. 添加bitable.py测试 (可提升8%覆盖率)
3. 添加webhooks.py测试 (可提升15%覆盖率)

**P1 - 高优先级 (第2周)**:
4. 添加feishu.py测试
5. 添加llm.py测试
6. 完善task_manager.py和scheduler.py测试

**P2 - 中优先级 (第3周)**:
7. 添加ci.py基础测试
8. 添加db_audit.py基础测试
9. 添加task_monitor.py基础测试

### 测试执行策略

```bash
# 阶段1：修复失败测试
pytest tests/unit/test_cv_parser.py -v
pytest tests/unit/test_match.py -v
pytest tests/unit/test_scheduler.py -v
pytest tests/unit/test_task_manager.py -v

# 阶段2：验证覆盖率提升
pytest --cov=app.bitable --cov-report=term-missing
pytest --cov=app.webhooks --cov-report=term-missing

# 阶段3：整体验证
pytest --cov=app --cov-report=term-missing --cov-report=html
```

### Mock模式标准化

所有测试应遵循统一的mock模式：

```python
# 1. 使用conftest.py中的共享fixtures
# 2. 使用AsyncMock for async functions
# 3. 使用patch装饰器或上下文管理器
# 4. 配置return_value或side_effect
# 5. 验证mock调用：assert_called_once_with()
```

### 覆盖率验证

每次提交前运行：
```bash
pytest --cov=app --cov-report=term --cov-fail-under=60
```

目标：
- 行覆盖率 ≥ 60%
- 函数覆盖率 ≥ 75%
- 0个失败测试
- 执行时间 < 30秒
