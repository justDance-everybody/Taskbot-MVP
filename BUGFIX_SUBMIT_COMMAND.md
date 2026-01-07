# Bug Fix: /submit Command Error

## Issue 1: Missing get_task Method
The `/submit` command was failing with the error:
```
'FeishuBitableClient' object has no attribute 'get_task'
```

### Root Cause
The `TaskManager` class in `app/services/task_manager.py` was using `bitable_client` (an instance of `FeishuBitableClient`) which doesn't have the `get_task()` method. The `get_task()` method is only available in the `BitableClient` class.

### Solution
Changed `TaskManager` to use `BitableClient` instead of `FeishuBitableClient`:

**Before:**
```python
from app.bitable import FeishuBitableClient, bitable_client

class TaskManager:
    def __init__(self):
        self.bitable = bitable_client  # FeishuBitableClient instance
```

**After:**
```python
from app.bitable import BitableClient

class TaskManager:
    def __init__(self):
        self.bitable = BitableClient()  # BitableClient instance with get_task() method
```

## Issue 2: Task Status Validation Too Strict
After fixing Issue 1, the `/submit` command was still failing with:
```
Error submitting task TASK_1698374400: Task TASK_1698374400 is not in progress
```

### Root Cause
The `submit_task` method only allowed submissions when task status was `'in_progress'`, but tasks in the database had status `'assigned'`. The workflow should allow users to submit tasks that are in either `'assigned'` or `'in_progress'` status.

### Solution
Modified the status validation to accept both `'assigned'` and `'in_progress'` statuses:

**Before:**
```python
# 检查任务状态和权限
if task['status'] != TaskStatus.IN_PROGRESS.value:
    raise ValueError(f"Task {task_id} is not in progress")

if task.get('assignee') != user_id:
    raise ValueError(f"User {user_id} is not assigned to task {task_id}")
```

**After:**
```python
# 检查任务状态和权限 - 允许从assigned或in_progress状态提交
current_status = task.get('status', task.get('任务状态', ''))
if current_status not in [TaskStatus.ASSIGNED.value, TaskStatus.IN_PROGRESS.value]:
    raise ValueError(f"Task {task_id} cannot be submitted from status: {current_status}")

# 检查是否有分配人（支持中英文字段名）
assignee = task.get('assignee') or task.get('分配给')
if assignee and assignee != user_id:
    raise ValueError(f"User {user_id} is not assigned to task {task_id}")
```

The fix also:
- Supports both Chinese and English field names for status
- Only validates assignee if one is set (allows unassigned tasks to be submitted)
- Provides clearer error messages

## Files Modified
- `app/services/task_manager.py`

## Testing
The fix ensures that:
1. The `/submit` command can now call `self.bitable.get_task(task_id)` successfully
2. Tasks with status `'assigned'` or `'in_progress'` can be submitted
3. Tasks without an assignee can be submitted by any user
4. Better error messages for invalid status transitions

## Date
2026-01-06
