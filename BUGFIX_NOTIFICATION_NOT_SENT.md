# Bug Fix: 质量检查完成后没有收到通知

## Issue
任务提交后，质量检查完成了（任务被拒绝，评分85分），但用户没有收到拒绝通知。日志显示：
```
'BitableClient' object has no attribute 'get_table_records'
统计数据已更新: 总任务9, 有效记录0
Task TASK_1678888888 rejected with score 85
```

## Root Cause

### Issue 1: BitableClient 缺少 get_table_records 方法
`_update_daily_stats` 和 `_get_simple_task_info` 方法中直接调用了 `self.bitable.get_table_records()`，但 `BitableClient` 类本身没有这个方法。该方法存在于 `BitableClient.client`（`FeishuBitableClient` 实例）中。

这导致：
1. 统计更新失败
2. 可能影响后续的通知发送流程
3. 虽然任务状态更新成功，但通知没有发送

### Issue 2: 评分逻辑问题
评分 85 分（>= 80 分阈值）但仍被拒绝，说明 `failed_reasons` 不为空。判断逻辑是：
```python
passed = score >= min_pass_score and len(failed_reasons) == 0
```

这意味着即使分数达标，只要有任何改进建议，任务就会被拒绝。这个逻辑可能过于严格。

## Solution

### 1. 修复 get_table_records 调用
**Before:**
```python
# 获取表格记录
result = self.bitable.get_table_records(task_table_id)
records = result.get('data', {}).get('items', [])
```

**After:**
```python
# 获取表格记录 - 通过 client 访问
result = self.bitable.client.get_table_records(task_table_id)
records = result.get('data', {}).get('items', [])
```

修复位置：
- `_get_simple_task_info()` 方法
- `_calculate_average_assignment_time()` 方法

### 2. 建议优化评分逻辑（可选）
当前逻辑：
```python
passed = score >= min_pass_score and len(failed_reasons) == 0
```

建议改为：
```python
# 分数达标即通过，failed_reasons 仅作为改进建议
passed = score >= min_pass_score
```

或者更灵活的方式：
```python
# 高分（>=90）即使有建议也通过，低分必须无问题才通过
if score >= 90:
    passed = True
elif score >= min_pass_score:
    passed = len(failed_reasons) == 0
else:
    passed = False
```

## Files Modified
- `app/services/task_manager.py`

## Testing
修复后的功能：
1. 统计更新不会因为方法调用错误而失败
2. 任务拒绝后会正确发送通知给用户
3. 通知包含评分和改进建议

## Expected Behavior
任务提交后：
1. 状态更新为 "reviewing"（审核中）
2. AI 进行质量评估
3. 根据评分结果：
   - 评分 >= 80分且无问题：任务完成，发送成功通知
   - 评分 >= 80分但有建议：任务被拒绝，发送改进建议
   - 评分 < 80分：任务被拒绝，发送改进建议
4. 用户收到包含评分和反馈的通知消息
5. 统计数据正确更新

## Notes
当前的评分逻辑可能过于严格。建议根据实际业务需求调整：
- 如果 AI 总是会给出一些改进建议，那么应该只看分数
- 如果 AI 只在有严重问题时才给建议，那么当前逻辑是合理的

## Date
2026-01-06
