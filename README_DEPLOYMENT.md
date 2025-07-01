# 飞书机器人部署指南

本文档提供完整的飞书智能任务管理机器人部署指南，从0到1快速部署一个可用的系统。

## 📋 目录

- [环境要求](#环境要求)
- [必需的秘钥和配置](#必需的秘钥和配置)
- [飞书应用配置](#飞书应用配置)
- [多维表格设置](#多维表格设置)
- [本地部署](#本地部署)
- [Docker部署](#docker部署)
- [生产环境部署](#生产环境部署)
- [配置验证](#配置验证)
- [故障排除](#故障排除)

## 🔧 环境要求

- **Python**: 3.9+
- **系统**: Linux/macOS/Windows
- **内存**: 最小512MB，推荐1GB+
- **飞书企业账号**: 具备应用开发权限
- **外网访问**: 用于接收飞书Webhook

## 🔑 必需的秘钥和配置

### 核心配置文件：`.env`

在项目根目录创建 `.env` 文件，配置以下必需参数：

```env
# ===== 飞书机器人配置 (必需) =====
FEISHU_APP_ID=cli_xxxxxxxxxx              # 飞书应用ID
FEISHU_APP_SECRET=xxxxxxxxxx               # 飞书应用密钥
FEISHU_VERIFY_TOKEN=xxxxxxxxxx             # 事件订阅验证Token（可选）
FEISHU_ENCRYPT_KEY=                        # 事件订阅加密Key (可选)

# ===== 多维表格配置 (必需) =====
FEISHU_BITABLE_APP_TOKEN=xxxxxxxxxx        # 多维表格App Token
FEISHU_TASK_TABLE_ID=xxxxxxxxxx            # 任务表ID
FEISHU_PERSON_TABLE_ID=xxxxxxxxxx          # 候选人表ID

# ===== LLM配置 (至少选一个) =====
DEEPSEEK_KEY=sk-xxxxxxxxxx                 # DeepSeek API密钥 (推荐)
OPENAI_KEY=                                # OpenAI API密钥 (可选)
GEMINI_KEY=                                # Google Gemini密钥 (可选)
DEFAULT_LLM_MODEL=deepseek                 # 默认使用的模型

# ===== GitHub集成 (可选) =====
GITHUB_WEBHOOK_SECRET=xxxxxxxxxx           # GitHub Webhook密钥

# ===== 服务器配置 =====
SERVER_HOST=0.0.0.0                       # 服务监听地址
SERVER_PORT=8000                          # 服务端口
DEBUG=false                               # 调试模式
```

## 🚀 飞书应用配置

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 进入「开发者后台」→「应用管理」
3. 点击「创建企业自建应用」
4. 填写应用名称
5. 获取 `App ID` 和 `App Secret`

### 2. 配置机器人权限

在应用管理页面，进入「功能配置」→「机器人」：

**必需权限：**
```
建议相关分类全部勾选
📨 消息与群组
├── im:message                    # 获取与发送单聊、群聊消息
├── im:message:send_as_bot        # 以应用的身份发送消息
├── im:chat                       # 获取群组信息，发送消息到群组
└── im:chat:readonly              # 获取群组信息

📊 多维表格
├── bitable:app                   # 获取多维表格信息
├── bitable:app:readonly          # 获取多维表格基础信息
├── bitable:table                 # 获取多维表格数据表信息
├── bitable:table:readonly        # 获取多维表格数据表基础信息
├── bitable:record                # 新增、删除、修改多维表格记录
└── bitable:record:readonly       # 查看多维表格记录

👤 通讯录 (可选)
├── contact:user.id:readonly      # 获取用户 user ID
└── contact:user.base:readonly    # 获取用户基础信息
```

### 3. 配置事件订阅 （可选）

在「事件订阅」页面：

1. **Request URL**: `https://your-domain.com/webhooks/feishu`
2. **Verification Token**: 生成并复制到 `.env` 文件的 `FEISHU_VERIFY_TOKEN`
3. **Encrypt Key**: (可选) 如需加密则生成，复制到 `FEISHU_ENCRYPT_KEY`

**订阅事件：**
```
✅ im.message.receive_v1          # 接收消息
✅ im.message.message_read_v1     # 消息已读  
✅ im.chat.updated_v1             # 群配置修改
```




## 📊 多维表格设置

### 1. 创建多维表格

1. 在飞书中创建新的多维表格应用
2. 获取表格的 `App Token`（URL中的标识符）
3. 将 `App Token` 配置到 `.env` 的 `FEISHU_BITABLE_APP_TOKEN`

### 2. 创建任务表

**表格名称**: `tasks` 或 `任务表`

**必需字段**:
| 字段名 | 字段类型 | 描述 | 必需 |
|--------|----------|------|------|
| taskid | 单行文本 | 任务ID | ✅ |
| title | 单行文本 | 任务标题 | ✅ |
| description | 多行文本 | 任务描述 | ✅ |
| status | 单选 | 任务状态 | ✅ |
| creator | 单行文本 | 创建者 | ✅ |
| assignee | 单行文本 | 负责人 | ❌ |
| deadline | 日期时间 | 截止时间 | ✅ |
| urgency | 单选 | 紧急程度 | ❌ |
| skilltags | 多选 | 技能标签 | ❌ |
| final_score | 数字 | 最终得分 | ❌ |
| create_time | 日期时间 | 创建时间 | ❌ |
| completed_at | 日期时间 | 完成时间 | ❌ |

**状态字段选项**:
```
pending     # 待处理
assigned    # 已分配  
in_progress # 进行中
submitted   # 已提交
reviewing   # 审核中
completed   # 已完成
rejected    # 已拒绝
cancelled   # 已取消
```

**紧急程度选项**:
```
low      # 低优先级
normal   # 普通
high     # 高优先级  
urgent   # 紧急
```

### 3. 创建候选人表

**表格名称**: `candidates` 或 `候选人表`

**必需字段**:
| 字段名 | 字段类型 | 描述 | 必需 |
|--------|----------|------|------|
| user_id | 单行文本 | 用户ID | ✅ |
| name | 单行文本 | 姓名 | ✅ |
| skill_tags | 多选 | 技能标签 | ✅ |
| job_level | 单选 | 职级 | ❌ |
| experience | 数字 | 工作经验(年) | ❌ |
| total_tasks | 数字 | 总任务数 | ❌ |
| average_score | 数字 | 平均评分 | ❌ |
| available_hours | 数字 | 可用工时 | ❌ |

### 4. 获取表格ID

1. 打开对应的表格
2. 点击右上角「...」→「复制链接」
3. 从URL中提取表格ID：
   ```
   https://example.feishu.cn/base/APP_TOKEN/objects/TABLE_ID
   ```
4. 将 `TABLE_ID` 分别配置到 `.env` 对应字段

## 💻 本地部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd Bot
```

### 2. 安装依赖

```bash
# 创建虚拟环境 (推荐)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

### 4. 启动服务

```bash
# 开发模式
python main.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 设置公网访问 (开发环境)

如需本地测试，可使用 ngrok 提供公网访问：

```bash
# 安装ngrok
brew install ngrok  # macOS
# 或下载: https://ngrok.com/download

# 启动隧道
ngrok http 8000

# 复制生成的HTTPS地址到飞书事件订阅配置
```

## 🐳 Docker部署

### 1. 使用Docker Compose (推荐)

```bash
# 确保.env文件已配置
cp .env.example .env
vim .env

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 2. 使用Docker

```bash
# 构建镜像
docker build -t feishu-chatops .

# 运行容器
docker run -d \
  --name feishu-chatops \
  -p 8000:8000 \
  --env-file .env \
  feishu-chatops

# 查看日志
docker logs -f feishu-chatops
```



## ✅ 配置验证

### 1. 基础连通性测试

```bash
# 测试服务是否启动
curl http://localhost:8000/health

# 预期响应
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00"
}
```

### 2. 飞书连接测试

在飞书中向机器人发送消息：
```
ping
```

预期机器人回复：`pong`

### 3. 功能测试

```bash
# 测试任务监测功能
/monitor test

# 测试群聊创建功能  
/testgroup create

# 查看帮助
/help
```




## 🔧 故障排除

### 常见问题

#### 1. 机器人无响应

**症状**: 发送消息给机器人无回复

**可能原因**:
- 事件订阅URL配置错误
- Verification Token不匹配
- 服务未启动或端口不通

**解决方案**:
```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查日志
tail -f app.log

# 验证配置
grep FEISHU_VERIFY_TOKEN .env
```

#### 2. 多维表格访问失败

**症状**: 日志显示表格API调用失败

**可能原因**:
- App Token或Table ID错误
- 应用权限不足
- 表格字段名称不匹配

**解决方案**:
```bash
# 验证配置
python -c "
from app.config import settings
print('App Token:', settings.feishu_bitable_app_token)
print('Task Table:', settings.feishu_task_table_id)
"

# 测试表格连接
python -c "
from app.bitable import create_bitable_client
client = create_bitable_client()
print(client.get_tables())
"
```

#### 3. LLM服务调用失败

**症状**: 智能功能无法使用

**可能原因**:
- API密钥无效或过期
- 网络连接问题
- API配额不足

**解决方案**:
```bash
# 检查API密钥
grep -E "(DEEPSEEK|OPENAI|GEMINI)_KEY" .env

# 测试API连接
python -c "
from app.services.llm import llm_service
result = llm_service.simple_chat('Hello')
print(result)
"
```

#### 4. 权限错误

**症状**: 403 Forbidden 错误

**检查清单**:
- ✅ 飞书应用权限是否完整
- ✅ 多维表格是否设置了应用访问权限
- ✅ 机器人是否被拉入相关群聊
- ✅ Verification Token是否正确

### 日志分析

```bash
# 查看实时日志
tail -f app.log

# 搜索错误信息
grep -i error app.log

# 查看最近的API调用
grep "API" app.log | tail -20
```

### 性能监控

```bash
# 检查内存使用
ps aux | grep python

# 检查端口占用
netstat -tlnp | grep 8000

# 检查磁盘空间
df -h
```

## 📞 技术支持

### 日志收集

遇到问题时，请提供以下信息：

1. **错误描述**: 具体的错误现象
2. **复现步骤**: 如何触发问题
3. **环境信息**: Python版本、系统信息
4. **配置文件**: `.env` 文件 (隐去敏感信息)
5. **日志片段**: 相关的错误日志

### 有用链接

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [多维表格API文档](https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview)
- [项目GitHub仓库](https://github.com/your-org/repo)

---

**🎉 部署完成！** 

你的飞书智能任务管理机器人现在应该可以正常工作了。在飞书中发送 `/help` 查看所有可用功能。