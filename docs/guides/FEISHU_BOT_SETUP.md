# 飞书机器人完整配置指南

## 概述

本指南将帮助你完成飞书机器人的完整配置，让机器人能够：
- 接收和回复消息
- 创建任务子群
- 发送提醒和通知
- 处理文件上传（PDF简历）
- 自动管理群聊

---

## 第一步：创建飞书应用

### 1.1 进入飞书开放平台
访问：https://open.feishu.cn/app

### 1.2 创建企业自建应用
1. 点击「创建企业自建应用」
2. 填写应用信息：
   - **应用名称**：任务管理Bot
   - **应用描述**：智能任务管理助手
   - **应用图标**：上传一个机器人图标

3. 创建完成后，记录：
   - **App ID**：`cli_xxxxx`
   - **App Secret**：点击「查看」获取

### 1.3 配置应用凭证
将获取的凭证填入 `.env` 文件：
```bash
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=your_app_secret
```

---

## 第二步：配置应用权限

### 2.1 进入权限管理
在应用管理页面，点击「权限管理」

### 2.2 添加必需权限

#### 消息与群组权限
```
✅ im:message (获取与发送单聊、群组消息)
✅ im:message:send_as_bot (以应用身份发消息)
✅ im:chat (获取群组信息)
✅ im:chat:write (创建群组、更新群组信息)
✅ im:chat.member (获取群成员信息)
✅ im:chat.member:write (管理群成员)
```

#### 多维表格权限
```
✅ bitable:app (访问多维表格)
✅ bitable:app:readonly (读取多维表格)
✅ bitable:app:write (编辑多维表格)
```

#### 文件权限
```
✅ drive:drive (访问云文档)
✅ drive:drive:readonly (读取云文档)
```

#### 通讯录权限（可选）
```
✅ contact:user.base (获取用户基本信息)
✅ contact:user.email (获取用户邮箱)
```

### 2.3 申请权限
1. 勾选所有需要的权限
2. 点击「申请权限」
3. 等待管理员审批（如果你是管理员，直接通过）

---

## 第三步：配置事件订阅

### 3.1 获取公网地址

#### 方案A：使用ngrok（开发测试）
```bash
# 安装ngrok
brew install ngrok  # macOS
# 或从 https://ngrok.com/ 下载

# 启动ngrok
ngrok http 8000

# 获取公网地址，例如：
# https://abc123.ngrok.io
```

#### 方案B：使用服务器（生产环境）
```bash
# 确保服务器有公网IP和域名
# 例如：https://taskbot.yourdomain.com
```

### 3.2 配置Webhook URL
1. 在应用管理页面，点击「事件订阅」
2. 点击「添加事件订阅」
3. 填写配置：
   - **请求地址**：`https://your-domain.com/webhooks/feishu`
   - **加密策略**：选择「不加密」（开发测试）或「加密」（生产环境）

4. 点击「保存」，飞书会发送验证请求

### 3.3 订阅事件

#### 必需事件
```
✅ im.message.receive_v1 (接收消息)
   - 用于接收用户发送的指令和消息

✅ im.message.message_read_v1 (消息已读)
   - 用于跟踪消息状态

✅ im.chat.updated_v1 (群配置修改)
   - 用于监控群组变化
```

#### 可选事件
```
□ im.chat.member.user.added_v1 (用户进群)
□ im.chat.member.user.withdrawn_v1 (用户退群)
□ im.chat.disbanded_v1 (群解散)
```

### 3.4 验证配置
飞书会向你的Webhook URL发送验证请求，确保：
1. 你的服务已启动：`python3 main.py`
2. Webhook端点可访问：`/webhooks/feishu`
3. 返回正确的challenge值

---

## 第四步：配置机器人

### 4.1 启用机器人功能
1. 在应用管理页面，点击「机器人」
2. 点击「启用机器人」
3. 配置机器人信息：
   - **机器人名称**：任务管理Bot
   - **描述**：智能任务管理助手
   - **头像**：上传机器人头像

### 4.2 配置消息卡片
1. 点击「消息卡片」
2. 启用「消息卡片」功能
3. 配置卡片请求地址（如果需要交互式卡片）

### 4.3 配置指令（可选）
**注意**：这一步是可选的，主要用于在飞书中显示指令提示。如果你的应用管理页面没有这个选项，可以跳过。

机器人会自动识别以下指令：
```
/newtask - 创建新任务
/task list - 查看任务列表
/task <id> - 查看任务详情
/done <url> - 提交任务完成
/help - 查看帮助
ping - 测试连接
```

这些指令已经在代码中实现，不需要在飞书后台配置也能正常使用。

---

## 第五步：创建多维表格

### 5.1 创建多维表格应用
1. 在飞书中打开「多维表格」
2. 点击「创建」→「空白多维表格」
3. 命名：「任务管理系统」

### 5.2 创建任务表
表名：**任务表**

字段配置：
| 字段名 | 字段类型 | 说明 |
|--------|----------|------|
| 任务ID | 单行文本 | 唯一标识 |
| 任务标题 | 单行文本 | 任务名称 |
| 任务描述 | 多行文本 | 详细描述 |
| 任务状态 | 单选 | pending/assigned/in_progress/completed等 |
| 创建人 | 单行文本 | 创建者ID |
| 承接人 | 单行文本 | 承接者ID（可选） |
| 截止时间 | 日期 | 任务截止日期 |
| 技能标签 | 多选 | 所需技能 |
| 紧急程度 | 单选 | low/normal/high/urgent |

### 5.3 创建候选人表
表名：**候选人表**

字段配置：
| 字段名 | 字段类型 | 说明 |
|--------|----------|------|
| user_id | 单行文本 | 用户唯一ID |
| name | 单行文本 | 姓名 |
| skill_tags | 多选 | 技能标签 |
| job_level | 单选 | 职级：初级/中级/高级/专家/架构师 |
| experience | 数字 | 工作年限 |
| total_tasks | 数字 | 完成任务数 |
| average_score | 数字 | 平均评分 |

### 5.4 获取表格配置
1. 打开多维表格
2. 点击右上角「...」→「高级设置」
3. 记录：
   - **App Token**：`ZpUKbCD9WabCcosbqFAcl4ponuh`
   - **任务表ID**：点击任务表，从URL获取 `tblXXXXXX`
   - **候选人表ID**：点击候选人表，从URL获取 `tblXXXXXX`

### 5.5 配置表格权限
1. 点击多维表格右上角「分享」
2. 添加你的应用为协作者
3. 权限设置为「可编辑」

### 5.6 更新配置文件
将表格信息填入 `.env`：
```bash
FEISHU_BITABLE_APP_TOKEN=ZpUKbCD9WabCcosbqFAcl4ponuh
FEISHU_TASK_TABLE_ID=tblHL3XIUZBbCFJE
FEISHU_PERSON_TABLE_ID=tblDtuakdqIGvL7c
```

---

## 第六步：启动服务

### 6.1 安装依赖
```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装PDF解析库
pip install pdfplumber PyPDF2
```

### 6.2 配置环境变量
确保 `.env` 文件包含所有必需配置：
```bash
# 飞书配置
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=your_secret
FEISHU_BITABLE_APP_TOKEN=ZpUKbCD9WabCcosbqFAcl4ponuh
FEISHU_TASK_TABLE_ID=tblHL3XIUZBbCFJE
FEISHU_PERSON_TABLE_ID=tblDtuakdqIGvL7c

# LLM配置（至少配置一个）
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
```

### 6.3 启动服务
```bash
python3 main.py
```

服务启动后，你应该看到：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 第七步：测试机器人

### 7.1 添加机器人到群聊
1. 在飞书中创建一个测试群
2. 点击群设置 → 群机器人
3. 添加你的「任务管理Bot」

### 7.2 测试基本功能

#### 测试1：Ping测试
```
你: ping
Bot: pong! 🏓 Bot is alive!
```

#### 测试2：帮助命令
```
你: /help
Bot: 📋 任务管理Bot使用指南
     /newtask - 创建新任务
     /task list - 查看任务列表
     ...
```

#### 测试3：创建任务
```
你: /newtask
Bot: 请提供任务标题：
你: 开发登录功能
Bot: 请提供任务描述：
你: 实现用户登录功能，支持邮箱和手机号登录
Bot: 请提供所需技能（用逗号分隔）：
你: Python, FastAPI, JWT
Bot: 请提供截止时间（格式：YYYY-MM-DD）：
你: 2026-01-15
Bot: ✅ 任务已创建！
     正在匹配候选人...
     
     推荐候选人：
     1. 张三 (90分) - 技能匹配度高，具备Python和FastAPI经验
     2. 李四 (85分) - 经验丰富，熟悉相关技术栈
     
     请回复数字选择候选人，或回复"取消"
```

#### 测试4：上传简历
```
你: [上传PDF文件: 张三_简历.pdf]
Bot: 📄 正在解析简历...
Bot: ✅ 简历已解析：张三
     - 职级: 高级 (3)
     - 经验: 5年
     - 技能: Python, Django, PostgreSQL, FastAPI, Docker
     候选人信息已自动录入系统
```

---

## 第八步：验证子群创建

### 8.1 完整流程测试
1. 在测试群中创建任务：`/newtask`
2. 填写任务信息
3. Bot推荐候选人
4. 选择候选人（回复数字，如：`1`）
5. **Bot会自动创建子群**：
   - 群名称：`T-TASK001-开发登录功能`
   - 成员：HR（你）+ 承接人（张三）+ Bot
   - 你会收到群邀请通知

### 8.2 检查子群
1. 在飞书左侧群聊列表中查找新创建的子群
2. 子群名称格式：`T-{任务ID}-{任务标题}`
3. 确认成员包括：你、承接人、Bot

### 8.3 子群功能测试
在子群中测试：
```
承接人: 我开始工作了
Bot: 👍 收到！有问题随时联系

[几天后]
承接人: /done https://github.com/test/pr/123
Bot: 🔍 正在检查GitHub CI状态...
Bot: ✅ CI全部通过
     ✅ 代码审查通过
     ✅ 任务验收通过！
     任务状态已更新为Done
     7天后将自动归档本群
```

---

## 常见问题排查

### Q1: Bot收不到消息
**检查清单**：
- ✅ 事件订阅配置正确
- ✅ Webhook URL可访问
- ✅ 服务正在运行
- ✅ Bot已添加到群聊
- ✅ 权限已申请并通过

**调试方法**：
```bash
# 查看服务日志
tail -f app.log

# 测试Webhook端点
curl -X POST http://localhost:8000/webhooks/feishu \
  -H "Content-Type: application/json" \
  -d '{"challenge":"test"}'
```

### Q2: Bot无法创建子群
**可能原因**：
1. 缺少群组创建权限：`im:chat:write`
2. 缺少成员管理权限：`im:chat.member:write`
3. 承接人不在通讯录中

**解决方法**：
1. 检查权限配置
2. 重新申请权限
3. 确保承接人user_id正确

### Q3: 多维表格读写失败
**检查清单**：
- ✅ App Token正确
- ✅ Table ID正确
- ✅ 应用已添加为表格协作者
- ✅ 权限设置为「可编辑」

**测试方法**：
```bash
python3 test_simple.py
```

### Q4: PDF简历解析失败
**可能原因**：
1. PDF是扫描件（需要OCR）
2. PDF格式不支持
3. LLM服务未配置

**解决方法**：
```bash
# 安装PDF解析库
pip install pdfplumber PyPDF2

# 配置LLM服务
# 在.env中添加至少一个LLM API Key
```

---

## 生产环境部署建议

### 1. 使用HTTPS
```bash
# 使用Nginx反向代理
server {
    listen 443 ssl;
    server_name taskbot.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 使用进程管理
```bash
# 使用systemd
sudo nano /etc/systemd/system/taskbot.service

[Unit]
Description=Feishu Taskbot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Taskbot-MVP
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl start taskbot
sudo systemctl enable taskbot
```

### 3. 配置日志轮转
```bash
# /etc/logrotate.d/taskbot
/path/to/Taskbot-MVP/app.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 your_user your_user
}
```

### 4. 监控和告警
- 使用Prometheus监控服务状态
- 配置告警规则
- 定期检查日志

---

## 下一步

配置完成后，你可以：

1. **添加测试数据**
   ```bash
   python3 add_test_data.py
   ```

2. **运行完整测试**
   ```bash
   python3 test_e2e_workflow.py
   ```

3. **查看API文档**
   访问：http://localhost:8000/docs

4. **阅读更多文档**
   - `CV_PARSER_GUIDE.md` - PDF简历解析指南
   - `FINAL_SUMMARY.md` - 项目总结
   - `README.md` - 项目概述

---

## 技术支持

如遇到问题：
1. 查看日志：`tail -f app.log`
2. 运行测试：`python3 test_simple.py`
3. 检查配置：确保所有环境变量正确
4. 查看文档：阅读相关配置文档

---

**配置完成后，你的机器人就可以正常工作了！** 🎉

记得在生产环境中：
- 使用HTTPS
- 配置防火墙
- 定期备份数据
- 监控服务状态
