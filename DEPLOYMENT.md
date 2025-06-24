# 飞书任务机器人部署指南

本文档提供了飞书任务机器人的完整部署指南，包括本地开发、测试环境和生产环境的部署方法。

## 📋 目录

- [环境要求](#环境要求)
- [本地开发部署](#本地开发部署)
- [生产环境部署](#生产环境部署)
- [Docker部署](#docker部署)
- [云平台部署](#云平台部署)
- [监控和维护](#监控和维护)
- [故障排除](#故障排除)

## 🔧 环境要求

### 系统要求
- **操作系统**：Linux (推荐 Ubuntu 20.04+) / macOS / Windows
- **Python**：3.11+
- **内存**：最小 512MB，推荐 2GB+
- **存储**：最小 1GB 可用空间
- **网络**：需要访问外网（飞书API、LLM API）

### 外部依赖
- **飞书企业账号**：具有开发者权限
- **公网HTTPS地址**：用于接收Webhook（生产环境必需）
- **LLM API密钥**：DeepSeek/Gemini/OpenAI 至少一个
- **GitHub仓库**：用于CI集成（可选）

## 🏠 本地开发部署

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd feishu_test

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
make install-dev
```

### 2. 配置文件设置

```bash
# 创建环境配置文件
make setup-env

# 编辑 .env 文件
vim .env
```

**必需配置项**：
```bash
# 飞书基础配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_VERIFY_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 飞书多维表格配置
FEISHU_BITABLE_APP_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# LLM配置（至少配置一个）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 应用配置
DEBUG=true
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=8000
```

### 3. 飞书应用配置

#### 3.1 创建飞书应用
1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 点击"创建应用" → "内部应用"
3. 填写应用信息并创建

#### 3.2 配置应用权限
在应用管理页面添加以下权限：
- `im:message` - 接收和发送消息
- `im:message.group_at_msg` - 接收群组@消息
- `im:message.group_at_msg:readonly` - 读取群组@消息
- `im:chat` - 获取群组信息
- `im:chat:readonly` - 读取群组信息
- `contact:user.id:readonly` - 读取用户ID
- `bitable:app` - 多维表格应用权限
- `bitable:app:readonly` - 读取多维表格

#### 3.3 配置事件订阅
1. 开启"事件订阅"
2. 设置请求地址：`https://your-domain.com/webhook/feishu`
3. 添加事件：
   - `im.message.receive_v1` - 接收消息
   - `im.message.message_read_v1` - 消息已读
   - `application.bot.menu_v6` - 机器人菜单

#### 3.4 创建多维表格
1. 在飞书中创建新的多维表格
2. 记录多维表格的 App Token
3. 表格结构会在首次运行时自动创建

### 4. 启动开发服务

```bash
# 方式1：使用 Makefile
make dev

# 方式2：直接使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式3：使用 Docker
make docker-dev
```

### 5. 配置内网穿透（开发环境）

使用 Ngrok 将本地服务暴露到公网：

```bash
# 安装 ngrok
# 访问 https://ngrok.com/ 注册并下载

# 启动内网穿透
ngrok http 8000

# 复制 HTTPS 地址到飞书应用的事件订阅配置中
```

### 6. 测试部署

```bash
# 健康检查
curl http://localhost:8000/health

# 运行测试
make test

# 在飞书群组中测试
# @bot 新任务 测试任务
```

## 🚀 生产环境部署

### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要软件
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot

# 创建应用用户
sudo useradd -m -s /bin/bash feishu-bot
sudo usermod -aG sudo feishu-bot
```

### 2. 应用部署

```bash
# 切换到应用用户
sudo su - feishu-bot

# 克隆代码
git clone <repository-url> /home/feishu-bot/app
cd /home/feishu-bot/app

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置生产环境配置
```

### 3. 系统服务配置

创建 systemd 服务文件：

```bash
sudo vim /etc/systemd/system/feishu-bot.service
```

```ini
[Unit]
Description=Feishu Task Bot
After=network.target

[Service]
Type=exec
User=feishu-bot
Group=feishu-bot
WorkingDirectory=/home/feishu-bot/app
Environment=PATH=/home/feishu-bot/app/venv/bin
ExecStart=/home/feishu-bot/app/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start feishu-bot

# 设置开机自启
sudo systemctl enable feishu-bot

# 检查状态
sudo systemctl status feishu-bot
```

### 4. Nginx 反向代理配置

```bash
sudo vim /etc/nginx/sites-available/feishu-bot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/feishu-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. SSL 证书配置

```bash
# 使用 Let's Encrypt 获取免费 SSL 证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

## 🐳 Docker部署

### 1. 单容器部署

```bash
# 构建镜像
docker build -t feishu-bot:latest .

# 运行容器
docker run -d \
  --name feishu-bot \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  feishu-bot:latest
```

### 2. Docker Compose 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 生产环境 Docker Compose

创建 `docker-compose.prod.yml`：

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      target: production
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
```

## ☁️ 云平台部署

### 1. 阿里云 ECS 部署

```bash
# 1. 创建 ECS 实例
# 2. 配置安全组（开放 80, 443 端口）
# 3. 按照生产环境部署步骤操作
```

### 2. 腾讯云 CVM 部署

```bash
# 1. 创建 CVM 实例
# 2. 配置防火墙规则
# 3. 按照生产环境部署步骤操作
```

### 3. AWS EC2 部署

```bash
# 1. 创建 EC2 实例
# 2. 配置 Security Groups
# 3. 使用 Application Load Balancer
# 4. 配置 Route 53 域名解析
```

### 4. Kubernetes 部署

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: feishu-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: feishu-bot
  template:
    metadata:
      labels:
        app: feishu-bot
    spec:
      containers:
      - name: feishu-bot
        image: feishu-bot:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: feishu-bot-secrets
---
apiVersion: v1
kind: Service
metadata:
  name: feishu-bot-service
spec:
  selector:
    app: feishu-bot
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 📊 监控和维护

### 1. 日志管理

```bash
# 查看应用日志
sudo journalctl -u feishu-bot -f

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Docker 日志
docker logs -f feishu-bot
```

### 2. 性能监控

```bash
# 系统资源监控
htop
iostat -x 1
free -h

# 应用健康检查
curl http://localhost:8000/health

# 数据库连接检查（如果使用）
```

### 3. 备份策略

```bash
# 配置文件备份
tar -czf backup-$(date +%Y%m%d).tar.gz .env config.yaml

# 代码备份
git archive --format=tar.gz --output=code-backup-$(date +%Y%m%d).tar.gz HEAD
```

### 4. 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重启服务
sudo systemctl restart feishu-bot

# Docker 更新
docker-compose pull
docker-compose up -d
```

## 🔧 故障排除

### 常见问题

1. **服务无法启动**
   ```bash
   # 检查日志
   sudo journalctl -u feishu-bot -n 50
   
   # 检查端口占用
   sudo netstat -tlnp | grep 8000
   ```

2. **Webhook 接收失败**
   ```bash
   # 检查防火墙
   sudo ufw status
   
   # 检查 Nginx 配置
   sudo nginx -t
   ```

3. **LLM 调用失败**
   ```bash
   # 检查网络连接
   curl -I https://api.deepseek.com
   
   # 检查 API 密钥
   grep DEEPSEEK_API_KEY .env
   ```

### 性能优化

1. **增加工作进程**
   ```bash
   # 修改启动命令
   uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

2. **启用缓存**
   ```bash
   # 添加 Redis 缓存
   docker run -d --name redis -p 6379:6379 redis:alpine
   ```

3. **数据库优化**
   ```bash
   # 优化飞书 API 调用频率
   # 实现本地缓存机制
   ```

## 📞 技术支持

如果在部署过程中遇到问题，请：

1. 查看 [故障排除文档](TROUBLESHOOTING.md)
2. 检查 [GitHub Issues](https://github.com/example/feishu-task-bot/issues)
3. 联系技术支持团队

---

**注意**：请确保在生产环境中使用强密码和安全配置，定期更新系统和依赖包。
