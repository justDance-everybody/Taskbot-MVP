# 飞书任务机器人部署指南

## 🚀 快速开始

### 方式一：使用配置向导（推荐）

1. **激活conda环境**
   ```bash
   conda activate feishu
   ```

2. **运行配置向导**
   ```bash
   python setup_wizard.py
   ```
   
   向导会引导您完成：
   - 飞书应用配置
   - LLM服务配置
   - GitHub集成配置（可选）
   - 自动创建多维表格
   - 生成配置文件

3. **启动应用**
   ```bash
   python start_production.py
   ```

### 方式二：手动配置

1. **准备飞书应用**
   - 访问 [飞书开放平台](https://open.feishu.cn/app)
   - 创建企业自建应用
   - 获取 App ID、App Secret、Verify Token

2. **创建多维表格**
   ```bash
   # 设置飞书应用信息
   export FEISHU_APP_ID="your_app_id"
   export FEISHU_APP_SECRET="your_app_secret"
   
   # 创建多维表格
   conda activate feishu
   python setup_bitable.py
   ```

3. **配置环境变量**
   ```bash
   cp .env.production .env.production.backup
   # 编辑 .env.production 文件，填入真实配置
   ```

4. **启动应用**
   ```bash
   conda activate feishu
   python start_production.py
   ```

## 📋 配置说明

### 必需配置

#### 飞书应用配置
```bash
FEISHU_APP_ID=cli_xxxxxxxxxx          # 应用ID
FEISHU_APP_SECRET=xxxxxxxxxx          # 应用密钥
FEISHU_VERIFY_TOKEN=xxxxxxxxxx        # 验证令牌
FEISHU_BITABLE_APP_TOKEN=xxxxxxxxxx   # 多维表格令牌
```

#### LLM服务配置（至少选择一个）
```bash
# DeepSeek（推荐）
DEEPSEEK_API_KEY=sk-xxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1

# Google Gemini
GOOGLE_API_KEY=xxxxxxxxxx
```

### 可选配置

#### GitHub集成
```bash
GITHUB_WEBHOOK_SECRET=xxxxxxxxxx      # GitHub Webhook密钥
```

#### 应用配置
```bash
APP_DEBUG=false                       # 调试模式
APP_LOG_LEVEL=INFO                    # 日志级别
APP_HOST=0.0.0.0                      # 监听地址
APP_PORT=8000                         # 监听端口
```

## 🔧 飞书应用配置

### 1. 创建应用
1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击"创建企业自建应用"
3. 填写应用信息

### 2. 配置权限
在应用管理页面，添加以下权限：

#### 机器人权限
- `im:message` - 获取与发送单聊、群组消息
- `im:message.group_at_msg` - 接收群聊中@机器人消息事件
- `im:message.group_at_msg:readonly` - 获取群组中所有消息
- `im:chat` - 获取与更新群组信息

#### 多维表格权限
- `bitable:app` - 查看、编辑多维表格
- `bitable:app:readonly` - 查看多维表格

#### 通讯录权限
- `contact:user.id:readonly` - 获取用户 user ID

### 3. 配置事件订阅
1. 在"事件订阅"页面，配置请求地址：
   ```
   https://your-domain.com/webhook/feishu
   ```

2. 订阅以下事件：
   - `im.message.receive_v1` - 接收消息
   - `im.message.message_read_v1` - 消息已读

### 4. 配置机器人
1. 在"机器人"页面，启用机器人功能
2. 设置机器人名称和描述
3. 上传机器人头像

## 🌐 部署到服务器

### 使用Docker部署

1. **构建镜像**
   ```bash
   docker build -t feishu-task-bot .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name feishu-bot \
     -p 8000:8000 \
     --env-file .env.production \
     feishu-task-bot
   ```

### 使用Docker Compose

1. **启动服务**
   ```bash
   # 加载环境变量
   export $(cat .env.production | grep -v '^#' | xargs)
   
   # 启动服务
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **查看日志**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

### 使用systemd服务

1. **创建服务文件**
   ```bash
   sudo nano /etc/systemd/system/feishu-bot.service
   ```

2. **服务配置**
   ```ini
   [Unit]
   Description=Feishu Task Bot
   After=network.target

   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/path/to/feishu_test
   Environment=PATH=/home/your-user/anaconda3/envs/feishu/bin
   EnvironmentFile=/path/to/feishu_test/.env.production
   ExecStart=/home/your-user/anaconda3/envs/feishu/bin/python start_production.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable feishu-bot
   sudo systemctl start feishu-bot
   ```

## 🔍 故障排除

### 常见问题

1. **导入错误**
   ```bash
   # 确保在正确的conda环境中
   conda activate feishu
   pip list | grep lark-oapi
   ```

2. **权限错误**
   ```bash
   # 检查飞书应用权限配置
   # 确保已添加所需的API权限
   ```

3. **网络连接问题**
   ```bash
   # 测试网络连接
   curl -I https://open.feishu.cn
   ```

4. **多维表格访问失败**
   ```bash
   # 检查App Token是否正确
   # 确保应用有多维表格权限
   ```

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log

# 实时查看所有日志
tail -f logs/*.log
```

## 📞 获取帮助

如果遇到问题，请检查：

1. **配置文件** - 确保所有必需配置都已填写
2. **网络连接** - 确保服务器可以访问飞书API
3. **权限设置** - 确保飞书应用有足够的权限
4. **日志文件** - 查看详细的错误信息

## 🎯 下一步

部署完成后，您可以：

1. **测试机器人** - 在飞书群中@机器人测试功能
2. **配置Webhook** - 设置GitHub等外部服务的回调
3. **监控运行** - 设置日志监控和告警
4. **扩展功能** - 根据需要添加新的功能模块
