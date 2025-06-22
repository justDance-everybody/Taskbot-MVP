# 飞书任务机器人 API 文档

本文档描述了飞书任务机器人的 API 接口，包括 Webhook 端点、数据模型和集成指南。

## 📋 目录

- [基础信息](#基础信息)
- [认证和安全](#认证和安全)
- [API 端点](#api-端点)
- [数据模型](#数据模型)
- [Webhook 事件](#webhook-事件)
- [错误处理](#错误处理)
- [SDK 和示例](#sdk-和示例)

## 🔧 基础信息

### 服务地址
- **开发环境**：`http://localhost:8000`
- **生产环境**：`https://your-domain.com`

### API 版本
- **当前版本**：v1.0.0
- **协议**：HTTP/HTTPS
- **数据格式**：JSON

### 响应格式
所有 API 响应都遵循统一格式：

```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 🔐 认证和安全

### Webhook 签名验证

#### 飞书 Webhook 签名
```python
import hmac
import hashlib

def verify_feishu_signature(body: bytes, signature: str, token: str) -> bool:
    expected = hmac.new(
        token.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

#### GitHub Webhook 签名
```python
def verify_github_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### 请求头
```http
Content-Type: application/json
X-Lark-Signature: <飞书签名>
X-Hub-Signature-256: <GitHub签名>
```

## 🌐 API 端点

### 健康检查

#### GET /
基础健康检查端点

**响应示例**：
```json
{
  "message": "Feishu Task Bot is running",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### GET /health
详细健康检查端点

**响应示例**：
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "bitable": "ok",
    "feishu": "ok",
    "llm": "ok",
    "matching": "ok",
    "ci": "ok"
  }
}
```

### Webhook 端点

#### POST /webhook/feishu
接收飞书事件的 Webhook 端点

**请求头**：
```http
Content-Type: application/json
X-Lark-Signature: <签名>
```

**请求体示例**：
```json
{
  "schema": "2.0",
  "header": {
    "event_id": "event_id_12345",
    "event_type": "im.message.receive_v1",
    "create_time": "1640995200000",
    "token": "verification_token",
    "app_id": "cli_app_id",
    "tenant_key": "tenant_key"
  },
  "event": {
    "sender": {
      "sender_id": {
        "user_id": "user_id_12345"
      },
      "sender_type": "user"
    },
    "message": {
      "message_id": "message_id_12345",
      "chat_id": "chat_id_12345",
      "chat_type": "group",
      "message_type": "text",
      "content": "{\"text\":\"@bot 新任务 创建API\"}"
    }
  }
}
```

**响应示例**：
```json
{
  "message": "Event received"
}
```

#### POST /webhook/github
接收 GitHub 事件的 Webhook 端点

**请求头**：
```http
Content-Type: application/json
X-Hub-Signature-256: <签名>
```

**请求体示例**：
```json
{
  "action": "completed",
  "workflow_run": {
    "id": 123456789,
    "name": "CI",
    "status": "completed",
    "conclusion": "success",
    "html_url": "https://github.com/user/repo/actions/runs/123456789"
  },
  "repository": {
    "name": "test-repo",
    "full_name": "user/test-repo",
    "html_url": "https://github.com/user/test-repo"
  }
}
```

## 📊 数据模型

### Task（任务）
```json
{
  "id": "task_record_id",
  "title": "任务标题",
  "description": "任务描述",
  "skill_tags": ["Python", "FastAPI"],
  "deadline": "2024-01-15T00:00:00Z",
  "assignee_id": "user_id_12345",
  "child_chat_id": "chat_id_12345",
  "status": "Draft|Assigned|InProgress|Returned|Done|Archived",
  "ci_state": "Pending|Success|Failure|Error",
  "ai_score": 85,
  "created_at": "2024-01-01T00:00:00Z",
  "assigned_at": "2024-01-01T01:00:00Z",
  "done_at": "2024-01-01T10:00:00Z"
}
```

### Person（人员）
```json
{
  "id": "person_record_id",
  "user_id": "user_id_12345",
  "name": "张三",
  "skill_tags": ["Python", "JavaScript", "React"],
  "hours_available": 40,
  "performance": 85.5,
  "last_done_at": "2024-01-01T00:00:00Z"
}
```

### MatchResult（匹配结果）
```json
{
  "user_id": "user_id_12345",
  "name": "张三",
  "match_score": 85,
  "match_reasons": [
    "技能完全匹配：Python, FastAPI",
    "时间充足：40小时/周",
    "历史表现优秀：平均90分"
  ],
  "score_breakdown": {
    "skill": 90.0,
    "availability": 85.0,
    "performance": 90.0,
    "recency": 75.0
  }
}
```

### CIResult（CI结果）
```json
{
  "state": "Success|Failure|Error|Pending",
  "message": "✅ CI 执行成功",
  "details": "分支: main\n提交: abc123d\n触发者: developer",
  "url": "https://github.com/user/repo/actions/runs/123456789",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## 📨 Webhook 事件

### 飞书事件类型

#### 1. 消息接收事件
**事件类型**：`im.message.receive_v1`

**触发条件**：
- 用户在群组中 @机器人
- 用户发送包含关键词的消息
- 用户在私聊中发送消息

**处理逻辑**：
- 解析消息内容
- 识别命令类型（新任务、提交结果、查看报告）
- 执行相应的业务逻辑

#### 2. 卡片交互事件
**事件类型**：`card.action.trigger`

**触发条件**：
- 用户点击交互式卡片中的按钮
- 用户提交表单

**处理逻辑**：
- 解析用户操作
- 执行对应的业务操作（如分配任务）

### GitHub 事件类型

#### 1. 工作流完成事件
**事件类型**：`workflow_run`

**触发条件**：
- GitHub Actions 工作流执行完成
- 工作流状态变更

**处理逻辑**：
- 解析 CI 执行结果
- 更新任务状态
- 通知相关人员

## ⚠️ 错误处理

### HTTP 状态码
- `200 OK`：请求成功
- `400 Bad Request`：请求参数错误
- `401 Unauthorized`：签名验证失败
- `404 Not Found`：资源不存在
- `500 Internal Server Error`：服务器内部错误

### 错误响应格式
```json
{
  "success": false,
  "error": {
    "code": "INVALID_SIGNATURE",
    "message": "签名验证失败",
    "details": "请检查 Webhook 签名配置"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 常见错误码
| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| `INVALID_SIGNATURE` | 签名验证失败 | 检查 Webhook 签名配置 |
| `INVALID_JSON` | JSON 格式错误 | 检查请求体格式 |
| `MISSING_REQUIRED_FIELD` | 缺少必需字段 | 补充必需的请求参数 |
| `FEISHU_API_ERROR` | 飞书 API 调用失败 | 检查飞书应用配置和权限 |
| `LLM_API_ERROR` | LLM API 调用失败 | 检查 LLM API 密钥和网络连接 |
| `BITABLE_ERROR` | 多维表格操作失败 | 检查表格权限和配置 |

## 🛠️ SDK 和示例

### Python SDK 示例

```python
import requests
import hmac
import hashlib
import json

class FeishuBotClient:
    def __init__(self, base_url: str, verify_token: str):
        self.base_url = base_url
        self.verify_token = verify_token
    
    def verify_signature(self, body: bytes, signature: str) -> bool:
        expected = hmac.new(
            self.verify_token.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    
    def send_webhook(self, event_data: dict) -> dict:
        url = f"{self.base_url}/webhook/feishu"
        body = json.dumps(event_data).encode('utf-8')
        
        signature = hmac.new(
            self.verify_token.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'X-Lark-Signature': signature
        }
        
        response = requests.post(url, data=body, headers=headers)
        return response.json()

# 使用示例
client = FeishuBotClient("http://localhost:8000", "your_verify_token")

# 发送消息事件
event = {
    "header": {
        "event_type": "im.message.receive_v1"
    },
    "event": {
        "message": {
            "content": '{"text":"@bot 新任务 测试API"}'
        }
    }
}

result = client.send_webhook(event)
print(result)
```

### JavaScript SDK 示例

```javascript
const crypto = require('crypto');
const axios = require('axios');

class FeishuBotClient {
    constructor(baseUrl, verifyToken) {
        this.baseUrl = baseUrl;
        this.verifyToken = verifyToken;
    }
    
    verifySignature(body, signature) {
        const expected = crypto
            .createHmac('sha256', this.verifyToken)
            .update(body)
            .digest('hex');
        return crypto.timingSafeEqual(
            Buffer.from(signature),
            Buffer.from(expected)
        );
    }
    
    async sendWebhook(eventData) {
        const url = `${this.baseUrl}/webhook/feishu`;
        const body = JSON.stringify(eventData);
        
        const signature = crypto
            .createHmac('sha256', this.verifyToken)
            .update(body)
            .digest('hex');
        
        const headers = {
            'Content-Type': 'application/json',
            'X-Lark-Signature': signature
        };
        
        const response = await axios.post(url, body, { headers });
        return response.data;
    }
}

// 使用示例
const client = new FeishuBotClient('http://localhost:8000', 'your_verify_token');

const event = {
    header: {
        event_type: 'im.message.receive_v1'
    },
    event: {
        message: {
            content: '{"text":"@bot 新任务 测试API"}'
        }
    }
};

client.sendWebhook(event).then(result => {
    console.log(result);
});
```

## 📝 集成指南

### 1. 飞书应用集成

1. **创建应用**：在飞书开放平台创建内部应用
2. **配置权限**：添加必要的 API 权限
3. **设置 Webhook**：配置事件订阅地址
4. **测试连接**：发送测试事件验证集成

### 2. GitHub 集成

1. **配置 Webhook**：在仓库设置中添加 Webhook
2. **选择事件**：选择 `workflow_run` 事件
3. **设置密钥**：配置 Webhook 密钥
4. **测试触发**：推送代码触发 CI 验证集成

### 3. LLM 集成

1. **获取 API 密钥**：从 LLM 提供商获取 API 密钥
2. **配置环境变量**：设置相应的环境变量
3. **测试调用**：发送测试请求验证 API 连接

## 🔄 版本更新

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持基础任务管理功能
- 集成飞书、GitHub、LLM

### 后续版本计划
- v1.1.0：增加批量任务处理
- v1.2.0：支持更多 LLM 后端
- v1.3.0：增加高级报表功能

---

**注意**：本 API 文档会随着版本更新而变化，请关注最新版本的文档。
