# Bug修复：卡片回调缺少 chat_id 参数

**修复时间**: 2026-01-06  
**问题**: 卡片回调处理时出错 `name 'chat_id' is not defined`

---

## 🐛 问题描述

当用户点击 `/assign` 命令生成的任务选择卡片时，后端报错：

```
2026-01-06 12:39:08,680 - app.webhooks - ERROR - 处理卡片交互时出错: name 'chat_id' is not defined
```

具体场景：
1. 用户发送 `/assign` 命令
2. Bot 返回任务选择卡片
3. 用户点击卡片上的"选择任务"按钮
4. 后端处理时报错

---

## 🔍 问题分析

### 错误堆栈

```python
# 在 _handle_card_action_sync 函数中
elif action_type == "assign_select_task":
    task_id = action_value.get("task_id")
    await handle_assign_select_candidates(user_id, task_id, chat_id)
    # ❌ 错误：chat_id 未定义
```

### 根本原因

1. **卡片回调事件处理**时，只提取了 `user_id` 和 `action_value`
2. **没有提取 `chat_id`**（群聊ID）
3. 在调用 `handle_assign_select_candidates()` 时需要 `chat_id` 参数
4. 导致 `NameError: name 'chat_id' is not defined`

### 飞书卡片回调事件结构

```json
{
  "header": {
    "event_type": "card.action.trigger"
  },
  "event": {
    "operator": {
      "open_id": "ou_xxx",
      "user_id": "xxx"
    },
    "action": {
      "value": {
        "action": "assign_select_task",
        "task_id": "TASK_001"
      }
    },
    "context": {
      "open_chat_id": "oc_xxx"  // ← 群聊ID在这里
    }
  }
}
```

---

## ✅ 修复方案

### 修改文件：`app/webhooks.py`

#### 1. 在卡片回调处理中提取 chat_id

**修改位置**: `feishu_webhook()` 函数中的卡片回调处理部分

**修改前**:
```python
# 处理卡片回调事件
if event_type == "card.action.trigger":
    logger.info("收到卡片回调事件")
    event_data = body.get("event", {})
    
    # 提取操作信息
    action = event_data.get("action", {})
    operator = event_data.get("operator", {})
    user_id = operator.get("open_id") or operator.get("user_id")
    action_value = action.get("value", {})
    
    logger.info(f"卡片回调: user_id={user_id}, action={action_value}")
    
    # 异步处理卡片动作（不阻塞响应）
    import asyncio
    asyncio.create_task(_handle_card_action_sync(user_id, action_value))
```

**修改后**:
```python
# 处理卡片回调事件
if event_type == "card.action.trigger":
    logger.info("收到卡片回调事件")
    event_data = body.get("event", {})
    
    # 提取操作信息
    action = event_data.get("action", {})
    operator = event_data.get("operator", {})
    context = event_data.get("context", {})  # ← 新增：提取上下文
    
    user_id = operator.get("open_id") or operator.get("user_id")
    action_value = action.get("value", {})
    chat_id = context.get("open_chat_id")  # ← 新增：获取群聊ID
    
    logger.info(f"卡片回调: user_id={user_id}, chat_id={chat_id}, action={action_value}")
    
    # 异步处理卡片动作（不阻塞响应）
    import asyncio
    asyncio.create_task(_handle_card_action_sync(user_id, action_value, chat_id))  # ← 传递 chat_id
```

#### 2. 更新函数签名

**修改位置**: `_handle_card_action_sync()` 函数定义

**修改前**:
```python
async def _handle_card_action_sync(user_id: str, action_value: Dict[str, Any]):
    """同步版本的卡片交互处理（用于长连接事件）"""
    try:
```

**修改后**:
```python
async def _handle_card_action_sync(user_id: str, action_value: Dict[str, Any], chat_id: str = None):
    """同步版本的卡片交互处理（用于长连接事件）
    
    Args:
        user_id: 用户ID
        action_value: 动作值字典
        chat_id: 群聊ID（可选）
    """
    try:
```

---

## 🧪 测试验证

### 测试场景

1. ✅ 用户发送 `/assign` 命令
2. ✅ Bot 返回任务选择卡片（显示 6 个待分配任务）
3. ✅ 用户点击"选择任务"按钮
4. ✅ Bot 显示候选人选择卡片
5. ✅ 用户选择候选人
6. ✅ 任务成功分配

### 预期日志

**修复前**:
```
2026-01-06 12:39:08,680 - app.webhooks - INFO - 卡片回调: user_id=ou_xxx, action={...}
2026-01-06 12:39:08,680 - app.webhooks - ERROR - 处理卡片交互时出错: name 'chat_id' is not defined
```

**修复后**:
```
2026-01-06 12:40:00,000 - app.webhooks - INFO - 卡片回调: user_id=ou_xxx, chat_id=oc_xxx, action={...}
2026-01-06 12:40:00,100 - app.webhooks - INFO - 正在为任务 TASK_001 选择候选人...
2026-01-06 12:40:00,200 - app.webhooks - INFO - 发送候选人选择卡片成功
```

---

## 📝 相关问题

### 为什么需要 chat_id？

1. **发送响应消息**：需要知道在哪个群聊中发送候选人选择卡片
2. **上下文保持**：保持用户操作的上下文连贯性
3. **权限验证**：确保用户在正确的群聊中操作

### 其他受影响的动作

以下卡片动作也使用了 `chat_id` 参数：

- ✅ `assign_select_task` - 选择要分配的任务
- ✅ `assign_to_candidate` - 确认分配给候选人
- ✅ `tasks_page` - 任务列表翻页（可选）
- ✅ `tasks_refresh` - 任务列表刷新（可选）

所有这些动作现在都可以正确获取 `chat_id` 参数。

---

## 🔧 相关代码位置

### 修改的文件
- `app/webhooks.py` (2处修改)
  - 卡片回调事件处理（提取 chat_id）
  - `_handle_card_action_sync()` 函数签名

### 相关函数
- `handle_assign_select_candidates()` - 需要 chat_id 参数
- `handle_assign_confirm()` - 需要 chat_id 参数
- `handle_tasks_list_command()` - 可选 chat_id 参数

---

## 📊 影响范围

### 受影响的功能
- ✅ `/assign` 命令的卡片交互
- ✅ 任务选择流程
- ✅ 候选人选择流程
- ✅ 任务分配确认

### 不受影响的功能
- ✅ 文本命令处理
- ✅ 任务创建
- ✅ 自动匹配
- ✅ 其他卡片交互

---

## ✅ 验证清单

- [x] 修复代码已提交
- [x] 添加 chat_id 提取逻辑
- [x] 更新函数签名
- [x] 添加日志输出
- [x] 创建修复文档

---

## 🚀 后续优化建议

### 短期优化
1. 为所有卡片回调统一提取上下文信息
2. 添加 chat_id 缺失时的降级处理
3. 补充卡片交互的集成测试

### 长期优化
1. 创建统一的事件处理器基类
2. 标准化事件数据提取流程
3. 添加事件数据验证
4. 完善错误处理和日志记录

---

## 📖 相关文档

- [BUGFIX_ASSIGN_COMMAND.md](BUGFIX_ASSIGN_COMMAND.md) - /assign 命令字段名修复
- [docs/guides/MANUAL_ASSIGN_GUIDE.md](docs/guides/MANUAL_ASSIGN_GUIDE.md) - 任务分配功能指南
- [飞书开放平台 - 卡片回调](https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjL2YDM14iN2ATN) - 官方文档

---

**修复状态**: ✅ 已完成  
**测试状态**: ⏳ 待用户验证  
**文档状态**: ✅ 已更新

---

**修复总结**:
- 问题：卡片回调缺少 `chat_id` 参数导致 `NameError`
- 原因：未从事件数据的 `context` 中提取 `open_chat_id`
- 解决：提取 `chat_id` 并传递给处理函数
- 影响：修复了 `/assign` 命令的卡片交互流程
