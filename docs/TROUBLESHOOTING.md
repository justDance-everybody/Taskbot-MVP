# 飞书机器人故障排查指南

## 问题：机器人不回复消息

当你在飞书中发送消息但机器人没有回复时，按照以下步骤排查：

---

## 第一步：检查服务是否运行

```bash
# 检查服务进程
ps aux | grep "python.*main.py" | grep -v grep

# 如果没有输出，说明服务未运行，需要启动：
source venv/bin/activate
python3 main.py
```

**预期结果**：应该看到一个 Python 进程正在运行

---

## 第二步：检查服务日志

```bash
# 查看最近的日志
tail -50 app.log

# 实时监控日志
tail -f app.log
```

**关键日志信息**：
- ✅ `Application startup complete` - 服务启动成功
- ✅ `connected to wss://msg-frontier.feishu.cn` - WebSocket连接成功
- ✅ `收到长连接消息: {"text":"ping"}` - 收到消息
- ✅ `消息发送成功` - 回复成功

**常见错误**：
- ❌ `connect failed, err: python-socks is required` - WebSocket代理错误
  - **解决方案**：在 `.env` 中添加 `ENABLE_WEBSOCKET=false`，使用Webhook模式
  
- ❌ `ModuleNotFoundError` - 缺少依赖
  - **解决方案**：`pip install -r requirements.txt`

- ❌ `401 Unauthorized` - 认证失败
  - **解决方案**：检查 `.env` 中的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`

---

## 第三步：检查飞书配置

### 3.1 检查事件订阅

1. 访问：https://open.feishu.cn/app
2. 进入你的应用 → 事件订阅
3. 确认已订阅：
   - ✅ `im.message.receive_v1` (接收消息)
   - ✅ `im.message.message_read_v1` (消息已读)

### 3.2 检查权限

进入应用 → 权限管理，确认已申请并通过：
- ✅ `im:message` (获取与发送消息)
- ✅ `im:message:send_as_bot` (以应用身份发消息)
- ✅ `im:chat` (获取群组信息)

### 3.3 检查机器人是否在群里

- 私聊：直接发送消息即可
- 群聊：
  1. 确认机器人已添加到群聊
  2. 群聊中需要 `@机器人` 或使用特定命令（如 `/help`、`新任务`）

---

## 第四步：测试连接

### 4.1 测试Webhook端点

```bash
# 测试本地服务
curl -X POST http://localhost:8000/webhooks/feishu \
  -H "Content-Type: application/json" \
  -d '{"challenge":"test123"}'

# 预期输出：{"challenge":"test123"}
```

### 4.2 测试API访问

```bash
# 运行简单测试
python3 test_simple.py

# 预期输出：所有测试通过
```

---

## 第五步：检查环境变量

确保 `.env` 文件包含所有必需配置：

```bash
# 飞书配置（必需）
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=your_secret
FEISHU_BITABLE_APP_TOKEN=your_token
FEISHU_TASK_TABLE_ID=tblXXXXXX
FEISHU_PERSON_TABLE_ID=tblXXXXXX

# LLM配置（至少一个）
DEEPSEEK_KEY=sk-xxxxx
# 或
GEMINI_KEY=xxxxx
# 或
OPENAI_KEY=xxxxx

# WebSocket配置（可选，建议禁用）
ENABLE_WEBSOCKET=false
```

---

## 常见问题和解决方案

### Q1: 发送 `ping` 没有回复

**可能原因**：
1. 服务未运行
2. WebSocket连接断开
3. 命令处理逻辑有问题

**解决步骤**：
```bash
# 1. 检查服务状态
ps aux | grep "python.*main.py"

# 2. 查看日志
tail -50 app.log | grep -i "ping"

# 3. 重启服务
pkill -f "python.*main.py"
source venv/bin/activate
python3 main.py
```

### Q2: 群聊中机器人不回复

**原因**：群聊中需要 `@机器人` 或使用特定命令

**解决方案**：
- 方式1：`@任务管理Bot ping`
- 方式2：直接发送 `/help` 或 `新任务 xxx`
- 方式3：在私聊中测试

### Q3: WebSocket连接失败

**错误信息**：`connect failed, err: python-socks is required`

**解决方案**：
1. 在 `.env` 中添加：
   ```bash
   ENABLE_WEBSOCKET=false
   ```

2. 重启服务：
   ```bash
   pkill -f "python.*main.py"
   python3 main.py
   ```

3. Webhook模式更稳定，推荐使用

### Q4: 权限不足

**错误信息**：`403 Forbidden` 或 `权限不足`

**解决方案**：
1. 进入飞书开放平台 → 应用管理 → 权限管理
2. 申请所有必需权限（参考 `FEISHU_BOT_SETUP.md` 第二步）
3. 等待管理员审批
4. 重启服务

### Q5: 多维表格访问失败

**错误信息**：`获取表格信息失败`

**解决方案**：
1. 检查 `.env` 中的表格配置：
   - `FEISHU_BITABLE_APP_TOKEN`
   - `FEISHU_TASK_TABLE_ID`
   - `FEISHU_PERSON_TABLE_ID`

2. 确认应用已添加为表格协作者：
   - 打开多维表格
   - 点击右上角「分享」
   - 添加你的应用
   - 权限设置为「可编辑」

3. 运行测试：
   ```bash
   python3 test_simple.py
   ```

---

## 调试技巧

### 1. 实时监控日志

```bash
# 在一个终端窗口中运行
tail -f app.log

# 在另一个终端窗口中发送测试消息
```

### 2. 查看详细错误

```bash
# 查看最近的错误日志
tail -100 app.log | grep -i "error"

# 查看特定时间的日志
tail -100 app.log | grep "2026-01-06 00:"
```

### 3. 测试特定功能

```bash
# 测试多维表格
python3 test_bitable.py

# 测试E2E流程
python3 test_e2e_workflow.py

# 测试Webhook
bash test_webhook.sh
```

---

## 快速诊断命令

```bash
# 一键检查所有关键点
echo "=== 服务状态 ==="
ps aux | grep "python.*main.py" | grep -v grep

echo -e "\n=== 最近日志 ==="
tail -20 app.log

echo -e "\n=== 环境变量 ==="
grep -E "^FEISHU_|^DEEPSEEK_|^GEMINI_|^OPENAI_|^ENABLE_" .env

echo -e "\n=== Webhook测试 ==="
curl -s -X POST http://localhost:8000/webhooks/feishu \
  -H "Content-Type: application/json" \
  -d '{"challenge":"test"}' | jq .
```

---

## 获取帮助

如果以上步骤都无法解决问题：

1. **收集信息**：
   ```bash
   # 导出诊断信息
   echo "=== 系统信息 ===" > debug.log
   uname -a >> debug.log
   echo -e "\n=== Python版本 ===" >> debug.log
   python3 --version >> debug.log
   echo -e "\n=== 服务状态 ===" >> debug.log
   ps aux | grep python >> debug.log
   echo -e "\n=== 最近日志 ===" >> debug.log
   tail -100 app.log >> debug.log
   ```

2. **查看文档**：
   - `FEISHU_BOT_SETUP.md` - 完整配置指南
   - `WEBHOOK_VERIFICATION_GUIDE.md` - Webhook配置
   - `WEBSOCKET_PROXY_FIX.md` - WebSocket问题

3. **联系支持**：
   - 提供 `debug.log` 文件
   - 说明具体的错误信息
   - 描述已尝试的解决步骤

---

## 预防措施

### 1. 定期检查

```bash
# 添加到 crontab，每小时检查一次
0 * * * * ps aux | grep "python.*main.py" || cd /path/to/Taskbot-MVP && source venv/bin/activate && python3 main.py
```

### 2. 日志轮转

```bash
# 防止日志文件过大
# 在 /etc/logrotate.d/taskbot 中配置
/path/to/Taskbot-MVP/app.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
}
```

### 3. 监控告警

- 使用 Prometheus + Grafana 监控服务状态
- 配置告警规则，服务异常时发送通知
- 定期查看 `/health` 端点

---

**记住**：大部分问题都可以通过查看日志找到原因！

```bash
tail -f app.log
```
