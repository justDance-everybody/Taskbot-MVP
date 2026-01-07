# Bug Fix: 质量检查没有结果

## Issue
任务提交后，质量检查过程失败，用户没有收到任何审核结果。日志显示多个错误：

1. `Error in quality check for task TASK_1698374400: No module named 'app.field_mapping'`
2. `Error in quality check for task TASK_006: 'Settings' object has no attribute 'min_pass_score'`
3. `LLM评估时出错: 'LLMService' object has no attribute 'call'`

## Root Cause

### Issue 1: 导入错误
`CIService` 类导入了一个不存在的模块 `app.field_mapping`，导致质量检查过程在初始化时就失败了。

### Issue 2: 配置项名称错误
代码中使用了 `settings.min_pass_score`，但配置文件中实际的配置项名称是 `ai_score_threshold`。

### Issue 3: LLM 方法名错误
`CIService` 调用了 `self.llm.call()`，但 `LLMService` 类的实际方法名是 `call_with_retry()`。

## Solution

### 1. 修复 CI 服务的导入
**Before:**
```python
from app.bitable import bitable_client
from app.field_mapping import get_field_value

class CIService:
    def __init__(self):
        self.llm = llm_service
        self.bitable = bitable_client
```

**After:**
```python
from app.bitable import BitableClient

class CIService:
    def __init__(self):
        self.llm = llm_service
        self.bitable = BitableClient()
```

### 2. 修复字段访问方式
移除了对不存在的 `get_field_value` 函数的调用，改为直接从任务数据中获取字段值，并支持中英文字段名：

**Before:**
```python
fields = task_data.get("fields", {})
submission_url = get_field_value(fields, "submission_url", "task", "")
description=get_field_value(fields, "description", "task", "")
```

**After:**
```python
description = task_data.get("description") or task_data.get("任务描述", "")
acceptance_criteria = task_data.get("acceptance_criteria", "")
submission_url = task_data.get("submission_url", "")
```

### 3. 修复配置项名称
**Before:**
```python
passed = score >= settings.min_pass_score and len(failed_reasons) == 0
```

**After:**
```python
# 判断是否通过 - 使用配置的分数阈值
min_pass_score = getattr(settings, 'min_pass_score', settings.ai_score_threshold)
passed = score >= min_pass_score and len(failed_reasons) == 0
```

### 4. 修复 LLM 方法调用
**Before:**
```python
# 调用LLM
response = await self.llm.call(user_prompt, system_prompt)
```

**After:**
```python
# 调用LLM - 使用 call_with_retry 方法
response = await self.llm.call_with_retry(user_prompt, system_prompt)
```

`call_with_retry` 方法的优势：
- 自动重试机制，提高成功率
- 支持多个 LLM 后端（DeepSeek、Gemini、OpenAI）
- 自动降级到备用模型
- 更好的错误处理和超时处理

### 5. 修复任务管理器中的字段访问
在 `_auto_quality_check`、`_complete_task` 和 `_reject_task` 方法中，添加了对中英文字段名的支持，并处理了字段可能为空的情况：

**Before:**
```python
score, failed_reasons = await ci_service.evaluate_submission(
    task_description=task_data['description'],  # 参数名不匹配
    acceptance_criteria=task_data.get('acceptance_criteria', ''),
    submission_url=submission_url
)

await self.feishu.send_message(
    user_id=assignee,  # 可能为 None
    message=f"恭喜！您的任务《{task_data['title']}》已通过验收。"  # 可能不存在
)
```

**After:**
```python
# 获取任务描述（支持中英文字段名）
description = task_data.get('description') or task_data.get('任务描述', '')
acceptance_criteria = task_data.get('acceptance_criteria', '')

score, failed_reasons = await ci_service.evaluate_submission(
    description=description,  # 参数名匹配
    acceptance_criteria=acceptance_criteria,
    submission_url=submission_url
)

# 获取字段值（支持中英文字段名）
assignee = task_data.get('assignee') or task_data.get('分配给')
title = task_data.get('title') or task_data.get('任务标题', '未知任务')

# 只在有 assignee 时发送通知
if assignee:
    await self.feishu.send_message(
        user_id=assignee,
        message=f"恭喜！您的任务《{title}》已通过验收。"
    )
```

## Files Modified
- `app/services/ci.py`
- `app/services/task_manager.py`

## Configuration
配置文件中的相关设置（`app/config.py`）：
```python
# 任务配置
ai_score_threshold: int = 80  # AI评分阈值，低于此分数任务将被拒绝
```

## Testing
修复后的功能：
1. 质量检查可以正常执行，不会因为导入错误而失败
2. 使用正确的配置项名称获取分数阈值
3. 使用正确的 LLM 方法名调用 AI 评估
4. 支持中英文字段名访问
5. 正确处理字段为空的情况
6. 只在有 assignee 时发送通知，避免发送给 None
7. 评估完成后会发送审核结果通知给用户

## Expected Behavior
任务提交后：
1. 状态更新为 "reviewing"（审核中）
2. AI 进行质量评估（使用 DeepSeek/Gemini/OpenAI）
3. 根据评分结果：
   - 评分 >= 80分（ai_score_threshold）：任务完成，发送成功通知
   - 评分 < 80分：任务被拒绝，发送改进建议
4. 用户收到包含评分和反馈的通知消息

## Date
2026-01-06
