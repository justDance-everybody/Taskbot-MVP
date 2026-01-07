# 飞书Webhook验证指南

## 问题：Challenge code没有返回

### 原因
之前的代码中缺少处理飞书事件订阅验证的POST端点。

### 解决方案
已在 `app/webhooks.py` 中添加 `/webhooks/feishu` POST端点，用于处理：
1. URL验证（challenge验证）
2. 事件回调

---

## 验证测试

### 1. 本地测试
```bash
# 启动服务
source venv/bin/activate
python3 main.py

# 测试challenge验证
curl -X POST http://localhost:8000/webhooks/feishu \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test_challenge_123"}'

# 应该返回：
# {"challenge":"test_challenge_123"}
```

### 2. 飞书配置

#### 步骤1：确保服务可从外网访问
```bash
# 使用ngrok（开发测试）
ngrok http 8000

# 获取公网地址，例如：
# https://abc123.ngrok.io
```

#### 步骤2：配置事件订阅
1. 进入飞书开放平台
2. 选择你的应用
3. 点击「事件订阅」
4. 点击「添加事件订阅」
5. 填写配置：
   - **请求地址**：`https://abc123.ngrok.io/webhooks/feishu`
   - **加密策略**：选择「不加密」（开发测试）

#### 步骤3：验证URL
1. 点击「保存」
2. 飞书会发送验证请求到你的Webhook URL
3. 你的服务会自动返回challenge值
4. 验证成功后，状态显示为「已验证」

---

## Webhook端点说明

### 端点信息
- **URL**: `/webhooks/feishu`
- **方法**: POST
- **Content-Type**: application/json

### 请求类型

#### 1. URL验证请求
飞书在配置事件订阅时发送：
```json
{
  "type": "url_verification",
  "challenge": "random_challenge_string",
  "token": "your_verification_token"
}
```

**响应**：
```json
{
  "challenge": "random_challenge_string"
}
```

#### 2. 事件回调请求
飞书在事件发生时发送：
```json
{
  "schema": "2.0",
  "header": {
    "event_id": "xxx",
    "event_type": "im.message.receive_v1",
    "create_time": "1234567890",
    "token": "xxx",
    "app_id": "cli_xxx",
    "tenant_key": "xxx"
  },
  "event": {
    // 事件具体内容
  }
}
```

**响应**：
```json
{
  "code": 0,
  "msg": "success"
}
```

---

## 代码实现

### app/webhooks.py
```python
@router.post("/feishu")
async def feishu_webhook(request: Request):
    """
    飞书Webhook端点
    处理飞书事件订阅的验证和事件推送
    """
    try:
        # 获取请求体
        body = await request.json()
        
        # 处理URL验证（challenge）
        if body.get("type") == "url_verification":
            challenge = body.get("challenge", "")
            logger.info(f"收到飞书URL验证请求，challenge: {challenge}")
            return {"challenge": challenge}
        
        # 处理事件回调
        event_type = body.get("header", {}).get("event_type")
        logger.info(f"收到飞书事件: {event_type}")
        
        # 返回成功响应
        return {"code": 0, "msg": "success"}
        
    except Exception as e:
        logger.error(f"处理飞书Webhook失败: {str(e)}")
        return {"code": -1, "msg": str(e)}
```

---

## 常见问题

### Q1: 验证失败，显示"请求超时"
**原因**：
- 服务未启动
- 端口未开放
- 公网地址不可访问

**解决方法**：
```bash
# 1. 确认服务运行
ps aux | grep python3

# 2. 测试本地访问
curl http://localhost:8000/health

# 3. 测试公网访问（使用ngrok地址）
curl https://abc123.ngrok.io/health

# 4. 查看日志
tail -f app.log
```

### Q2: 验证失败，显示"返回格式错误"
**原因**：
- 返回的JSON格式不正确
- 没有返回challenge字段

**解决方法**：
确保返回格式为：
```json
{"challenge": "原样返回的challenge值"}
```

### Q3: 验证成功但收不到事件
**原因**：
- 未订阅相关事件
- 权限不足

**解决方法**：
1. 在「事件订阅」页面添加事件：
   - `im.message.receive_v1` - 接收消息
   - `im.message.message_read_v1` - 消息已读
   - `im.chat.updated_v1` - 群配置修改

2. 在「权限管理」页面确认权限已通过

---

## 调试技巧

### 1. 查看实时日志
```bash
tail -f app.log | grep "飞书"
```

### 2. 使用ngrok查看请求
ngrok提供了Web界面查看所有HTTP请求：
```
访问：http://127.0.0.1:4040
```

### 3. 测试Webhook
```bash
# 模拟飞书验证请求
curl -X POST http://localhost:8000/webhooks/feishu \
  -H "Content-Type: application/json" \
  -d '{
    "type": "url_verification",
    "challenge": "test123",
    "token": "your_token"
  }'

# 模拟飞书事件请求
curl -X POST http://localhost:8000/webhooks/feishu \
  -H "Content-Type: application/json" \
  -d '{
    "schema": "2.0",
    "header": {
      "event_type": "im.message.receive_v1",
      "event_id": "test_event_123"
    },
    "event": {}
  }'
```

---

## 生产环境建议

### 1. 使用HTTPS
```bash
# 配置Nginx反向代理
server {
    listen 443 ssl;
    server_name taskbot.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /webhooks/feishu {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 启用加密验证
在飞书开放平台配置事件订阅时：
- 选择「加密」策略
- 获取Encrypt Key
- 在代码中添加解密逻辑

### 3. 添加签名验证
验证请求确实来自飞书：
```python
import hashlib
import hmac

def verify_signature(timestamp, nonce, encrypt, signature, token):
    """验证飞书请求签名"""
    str_to_sign = f"{timestamp}{nonce}{encrypt}{token}"
    sign = hashlib.sha256(str_to_sign.encode()).hexdigest()
    return sign == signature
```

---

## 总结

✅ **问题已解决**：添加了 `/webhooks/feishu` POST端点  
✅ **Challenge验证**：正常返回challenge值  
✅ **事件接收**：可以接收飞书事件回调  

**下一步**：
1. 配置飞书事件订阅
2. 订阅所需事件
3. 测试完整流程

参考文档：
- `FEISHU_BOT_SETUP.md` - 完整配置指南
- `CONFIG_CHECKLIST.md` - 配置检查清单
