# Testing Standards

本文档定义了项目测试代码的标准模式和最佳实践。

## 1. 异步测试装饰器

### 标准模式

所有异步测试必须使用 `@pytest.mark.asyncio` 装饰器：

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await some_async_function()
    assert result is not None
```

### 规则

- ✅ 使用 `@pytest.mark.asyncio` 装饰所有 `async def` 测试函数
- ✅ 测试函数名以 `test_` 开头
- ✅ 包含清晰的文档字符串
- ❌ 不要忘记 `await` 关键字
- ❌ 不要在同步测试中使用 `async def`

## 2. Mock配置模式

### 标准模式：使用Fixtures

优先使用 `conftest.py` 中定义的共享fixtures：

```python
@pytest.mark.asyncio
async def test_with_mock_service(mock_feishu_service):
    """使用共享fixture的测试"""
    # 配置mock行为
    mock_feishu_service.send_message.return_value = {"code": 0}
    
    # 执行测试
    result = await some_function(mock_feishu_service)
    
    # 验证
    assert result is not None
    mock_feishu_service.send_message.assert_called_once()
```

### 标准模式：使用Patch

当需要替换模块级对象时使用 `patch`：

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_patch():
    """使用patch的测试"""
    with patch('app.services.match.bitable_client') as mock_bitable:
        # 配置mock
        mock_bitable.get_task = AsyncMock(return_value={"task_id": "123"})
        
        # 执行测试
        result = await some_function()
        
        # 验证
        assert result is not None
```

### Mock配置规则

- ✅ 使用 `AsyncMock` 模拟异步函数
- ✅ 使用 `MagicMock` 模拟同步函数
- ✅ 配置 `return_value` 或 `side_effect`
- ✅ 使用 `assert_called_once()` 或 `assert_called_with()` 验证调用
- ❌ 不要使用真实的外部API调用
- ❌ 不要在测试间共享可变的mock状态

## 3. 测试结构模式 (AAA Pattern)

### 标准模式

所有测试应遵循 Arrange-Act-Assert 模式：

```python
@pytest.mark.asyncio
async def test_create_task(mock_bitable):
    """测试创建任务"""
    # Arrange - 准备测试数据和mock
    task_data = {
        "title": "测试任务",
        "description": "测试描述",
        "status": "pending"
    }
    mock_bitable.create_task.return_value = {"record_id": "rec_123"}
    
    # Act - 执行被测试的功能
    result = await create_task(task_data, mock_bitable)
    
    # Assert - 验证结果
    assert result is not None
    assert result["record_id"] == "rec_123"
    mock_bitable.create_task.assert_called_once_with(task_data)
```

### 规则

- ✅ 使用注释标记三个阶段（可选但推荐）
- ✅ Arrange: 准备测试数据、配置mocks
- ✅ Act: 调用被测试的函数
- ✅ Assert: 验证结果和mock调用
- ✅ 每个阶段之间用空行分隔

## 4. 断言模式

### 标准断言

```python
# 基本断言
assert result is not None
assert result == expected_value
assert len(result) == 2
assert "key" in result

# 类型断言
assert isinstance(result, dict)
assert isinstance(result, list)

# 布尔断言
assert result is True
assert result is False

# 异常断言
with pytest.raises(ValueError):
    some_function()

# 异步异常断言
with pytest.raises(ValueError):
    await some_async_function()
```

### Mock调用断言

```python
# 验证调用次数
mock.assert_called_once()
mock.assert_called()
mock.assert_not_called()

# 验证调用参数
mock.assert_called_with(arg1, arg2, key=value)
mock.assert_called_once_with(arg1, arg2)

# 验证任意调用
mock.assert_any_call(arg1, arg2)

# 获取调用参数
call_args = mock.call_args
call_kwargs = mock.call_args[1]
```

### 规则

- ✅ 使用清晰、具体的断言
- ✅ 每个测试验证一个主要行为
- ✅ 使用 `assert_called_once()` 而不是 `assert mock.called`
- ❌ 不要在一个测试中验证太多不相关的内容
- ❌ 不要使用模糊的断言如 `assert result`

## 5. 测试命名规范

### 标准命名模式

```python
# 模式: test_<function_name>_<scenario>_<expected_result>

# 好的命名
def test_create_task_with_valid_data_returns_task_id():
    """测试使用有效数据创建任务返回任务ID"""
    pass

def test_find_candidates_with_empty_pool_returns_empty_list():
    """测试空候选人池返回空列表"""
    pass

def test_parse_resume_when_pdf_fails_returns_default_data():
    """测试PDF解析失败时返回默认数据"""
    pass

# 避免的命名
def test_task():  # 太模糊
    pass

def test_1():  # 无意义
    pass

def test_create_task_works():  # 不够具体
    pass
```

### 规则

- ✅ 使用描述性的测试名称
- ✅ 说明测试场景和期望结果
- ✅ 使用下划线分隔单词
- ✅ 包含文档字符串进一步说明
- ❌ 不要使用数字或缩写
- ❌ 不要使用模糊的名称

## 6. 测试类组织

### 标准模式

使用测试类组织相关测试：

```python
class TestTaskCreation:
    """测试任务创建功能"""
    
    @pytest.mark.asyncio
    async def test_create_task_with_valid_data(self):
        """测试使用有效数据创建任务"""
        pass
    
    @pytest.mark.asyncio
    async def test_create_task_with_missing_fields(self):
        """测试缺少字段时的处理"""
        pass
    
    @pytest.mark.asyncio
    async def test_create_task_with_invalid_status(self):
        """测试无效状态的处理"""
        pass


class TestTaskRetrieval:
    """测试任务查询功能"""
    
    @pytest.mark.asyncio
    async def test_get_task_by_id_success(self):
        """测试成功获取任务"""
        pass
    
    @pytest.mark.asyncio
    async def test_get_task_by_id_not_found(self):
        """测试任务不存在的情况"""
        pass
```

### 规则

- ✅ 使用类名描述测试的功能模块
- ✅ 类名以 `Test` 开头
- ✅ 将相关测试组织在同一个类中
- ✅ 类包含清晰的文档字符串
- ❌ 不要在类中定义 `__init__` 方法
- ❌ 不要在测试类间共享状态

## 7. Fixture使用规范

### 使用共享Fixtures

```python
# 使用conftest.py中的fixtures
@pytest.mark.asyncio
async def test_with_shared_fixtures(
    mock_bitable,
    sample_task_data,
    sample_candidate_list
):
    """使用共享fixtures的测试"""
    # 使用fixtures
    mock_bitable.get_task.return_value = sample_task_data
    mock_bitable.get_available_candidates.return_value = sample_candidate_list
    
    # 执行测试
    result = await some_function(mock_bitable)
    
    # 验证
    assert result is not None
```

### 创建本地Fixtures

```python
@pytest.fixture
def local_test_data():
    """本地测试数据fixture"""
    return {
        "specific_field": "specific_value"
    }

@pytest.mark.asyncio
async def test_with_local_fixture(local_test_data):
    """使用本地fixture的测试"""
    result = await some_function(local_test_data)
    assert result is not None
```

### 规则

- ✅ 优先使用 `conftest.py` 中的共享fixtures
- ✅ 为特定测试文件创建本地fixtures
- ✅ 使用 `@pytest.fixture` 装饰器
- ✅ Fixture名称应该描述其提供的内容
- ❌ 不要在fixtures中包含断言
- ❌ 不要创建过于复杂的fixtures

## 8. 错误处理测试

### 标准模式

```python
@pytest.mark.asyncio
async def test_function_handles_exception():
    """测试异常处理"""
    # Arrange
    mock_service = AsyncMock()
    mock_service.call.side_effect = Exception("API错误")
    
    # Act & Assert
    with pytest.raises(Exception) as exc_info:
        await some_function(mock_service)
    
    # 验证异常信息
    assert "API错误" in str(exc_info.value)


@pytest.mark.asyncio
async def test_function_returns_default_on_error():
    """测试错误时返回默认值"""
    # Arrange
    mock_service = AsyncMock()
    mock_service.call.side_effect = Exception("API错误")
    
    # Act
    result = await some_function_with_fallback(mock_service)
    
    # Assert
    assert result == default_value
```

### 规则

- ✅ 测试异常情况
- ✅ 验证错误消息
- ✅ 测试降级和默认值
- ✅ 使用 `pytest.raises` 捕获异常
- ❌ 不要让异常未被捕获

## 9. 测试数据管理

### 使用Helper函数

```python
# 使用conftest.py中的helper函数
def test_with_helper_functions():
    """使用helper函数创建测试数据"""
    # 创建特定状态的任务
    pending_task = create_task_with_status("pending")
    completed_task = create_task_with_status("completed", title="自定义标题")
    
    # 创建特定技能的候选人
    python_dev = create_candidate_with_skills(["Python", "FastAPI"])
    
    assert pending_task["status"] == "pending"
    assert "Python" in python_dev["skill_tags"]
```

### 规则

- ✅ 使用helper函数创建测试数据
- ✅ 使用fixtures提供常用数据
- ✅ 保持测试数据简单和相关
- ❌ 不要在测试中硬编码大量数据
- ❌ 不要在测试间共享可变数据

## 10. 测试文件组织

### 标准结构

```python
"""
模块测试
简要描述测试的内容
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# 导入被测试的模块
from app.services.example import ExampleService


# ============================================================================
# Fixtures (如果有本地fixtures)
# ============================================================================

@pytest.fixture
def local_fixture():
    """本地fixture"""
    return {"data": "value"}


# ============================================================================
# Test Classes
# ============================================================================

class TestExampleFeature:
    """测试示例功能"""
    
    @pytest.mark.asyncio
    async def test_case_1(self):
        """测试用例1"""
        pass
    
    @pytest.mark.asyncio
    async def test_case_2(self):
        """测试用例2"""
        pass


class TestExampleErrorHandling:
    """测试错误处理"""
    
    @pytest.mark.asyncio
    async def test_error_case_1(self):
        """测试错误情况1"""
        pass
```

### 规则

- ✅ 文件以模块文档字符串开始
- ✅ 按逻辑分组导入语句
- ✅ 使用分隔注释组织代码段
- ✅ 测试类按功能分组
- ❌ 不要在一个文件中测试多个不相关的模块

## 快速检查清单

在提交测试代码前，检查以下项目：

- [ ] 所有异步测试使用 `@pytest.mark.asyncio`
- [ ] 使用 `AsyncMock` 模拟异步函数
- [ ] 遵循 AAA (Arrange-Act-Assert) 模式
- [ ] 测试名称清晰描述测试场景
- [ ] 使用共享fixtures而不是重复代码
- [ ] 包含文档字符串
- [ ] 验证mock调用
- [ ] 测试错误情况
- [ ] 没有外部API调用
- [ ] 测试可以独立运行

## 示例：完整的标准测试

```python
"""
任务管理服务测试
测试任务创建、更新和查询功能
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestTaskCreation:
    """测试任务创建功能"""
    
    @pytest.mark.asyncio
    async def test_create_task_with_valid_data_returns_task_id(
        self,
        mock_bitable,
        sample_task_data
    ):
        """测试使用有效数据创建任务返回任务ID"""
        # Arrange
        expected_record_id = "rec_123"
        mock_bitable.create_task.return_value = {"record_id": expected_record_id}
        
        # Act
        result = await create_task(sample_task_data, mock_bitable)
        
        # Assert
        assert result is not None
        assert result["record_id"] == expected_record_id
        mock_bitable.create_task.assert_called_once_with(sample_task_data)
    
    @pytest.mark.asyncio
    async def test_create_task_with_missing_title_raises_error(self, mock_bitable):
        """测试缺少标题时抛出错误"""
        # Arrange
        invalid_data = {"description": "描述"}  # 缺少title
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await create_task(invalid_data, mock_bitable)
        
        assert "title" in str(exc_info.value).lower()
```
