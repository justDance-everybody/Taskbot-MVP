# Taskbot-MVP 🤖

**一个智能的飞书任务分配机器人** —— 让远程兼职任务管理从"手工分派"变为"10秒自动匹配"。

[![Tests](https://github.com/justDance-everybody/Taskbot-MVP/actions/workflows/tests.yml/badge.svg)](https://github.com/justDance-everybody/Taskbot-MVP/actions)

---

## ✨ 它能做什么？

想象一下，你不再需要在聊天记录里翻找候选人简历、手动催进度、重复验收作业——Taskbot 帮你：

- **10 秒创建任务**：在飞书群里 `@bot 新任务: 开发登录页暗黑模式`，Bot 自动追问需求细节
- **AI 智能匹配**：上传简历 PDF 自动解析入库，LLM 从候选人中推荐最合适的 Top-2，附带匹配理由
- **一键指派**：点击按钮即可创建专属任务子群，邀请承接人开始工作
- **自动验收**：代码任务检查 GitHub CI 状态，文档任务由 LLM 评分，通过即自动标记完成
- **智能提醒**：任务进度过半自动 @承接人和 HR，减少 50% 手动催促
- **数据可视化**：`#report` 指令查看今日任务统计、平均指派耗时等 KPI

**核心价值**：让 HR 和任务协调者把时间花在战略性工作上，而不是重复劳动。

---

## 🚀 快速开始

### 前置要求

- 飞书企业账号（需开发者权限）
- Docker & Docker Compose
- 至少一个 LLM API Key（DeepSeek / Gemini / OpenAI）

### 5 分钟本地运行

```bash
# 1. 克隆项目
git clone https://github.com/justDance-everybody/Taskbot-MVP.git
cd Taskbot-MVP

# 2. 配置环境变量（参考 docs/task_bot_mvp_运行与环境配置.md）
cp .env.example .env
# 填入飞书 APP_ID、APP_SECRET、VERIFY_TOKEN 和至少一个模型密钥

# 3. 启动服务
docker-compose up -d

# 4. 使用 Ngrok 暴露公网地址
ngrok http 8000
# 将生成的 https://xxx.ngrok.io/webhook/feishu 填入飞书事件订阅 URL

# 5. 验证：在飞书群里 @机器人 ping
```

看到 `pong` 回复？恭喜，你已经跑通了！🎉

---

## 📖 核心功能演示

### 1️⃣ 智能候选人匹配

```
HR: @bot 新任务: 开发 React 登录页
Bot: 请描述任务内容...
HR: 需要暗黑模式适配
Bot: 验收标准是...
HR: 通过 UI 测试
Bot: 推荐以下候选人：
     ✅ 张三 - React 经验 3 年，可用时间充足
     ✅ 李四 - 熟悉 Tailwind，最近表现优秀
     [选择] [取消]
```

### 2️⃣ 简历自动解析

```
HR: [上传 resume.pdf]
Bot: ✅ 已解析候选人信息：
     姓名：王五
     技能：Python, Django, PostgreSQL
     可用时长：15 小时/周
     已添加到候选人库
```

### 3️⃣ 自动验收 & 提醒

- 代码任务：检测 GitHub PR 的 CI 状态 ✅
- 文档任务：LLM 根据验收标准评分（≥80 分通过）
- 进度过半自动 @承接人：避免 DDL 前夕手忙脚乱

---

## 🏗️ 技术架构

```
FastAPI (Bot 服务)
    ├── 飞书 Webhook (消息、卡片、群管理)
    ├── 多维表格 API (任务表、候选人表)
    ├── LLM Router (DeepSeek/Gemini/OpenAI)
    └── GitHub Webhook (CI 状态监听)
```

**核心技术栈**：Python 3.11+, FastAPI, Larksuite SDK, Docker

---

## 📚 完整文档

项目包含详尽的文档，帮助你快速上手或深度定制：

- **[产品需求文档 (PRD)](docs/task_bot_mvp_产品PRD需求文档.md)** - 了解功能设计与业务逻辑
- **[开发文档 (DEV_SPEC)](docs/task_bot_mvp_产品开发文档.md)** - 代码结构、API 设计、实现细节
- **[环境配置指南](docs/task_bot_mvp_运行与环境配置.md)** - 飞书应用创建、本地/云端部署
- **[Prompt 模板库](docs/task_bot_mvp_prompt设定说明.md)** - LLM 提示词配置与调优
- **[测试与验收](docs/task_bot_mvp_测试用例及验收文档.md)** - 单元测试、集成测试、E2E 测试

---

## 🤝 参与贡献

我们欢迎所有形式的贡献！无论你是：

- 🐛 **发现 Bug**：提交 [Issue](https://github.com/justDance-everybody/Taskbot-MVP/issues/new) 描述问题
- 💡 **功能建议**：在 Discussions 分享你的想法
- 🔧 **代码贡献**：Fork 项目 → 修改 → 提交 Pull Request
- 📖 **文档改进**：帮助完善中英文档、增加示例

### 贡献流程

```bash
# 1. Fork 并克隆项目
git clone https://github.com/YOUR_USERNAME/Taskbot-MVP.git

# 2. 创建功能分支
git checkout -b feature/your-feature

# 3. 开发与测试
make test  # 确保测试通过

# 4. 提交 PR
# 请在 PR 描述中说明改动目的和测试结果
```

**开发指南**：
- 代码风格：使用 `black` 和 `isort` 格式化
- 测试覆盖率：新功能需包含单元测试（≥60% 覆盖）
- Commit 规范：`feat:` / `fix:` / `docs:` 前缀

---

## 🛣️ Roadmap

- [x] 任务创建与 LLM Top-2 智能匹配
- [x] 简历 PDF 自动解析入库
- [x] 周期过半自动提醒
- [x] 代码/文档自动验收
- [ ] 多人协作子任务拆分
- [ ] 历史数据分析与绩效预测
- [ ] 跨租户支持（SaaS 化）

查看 [Issues](https://github.com/justDance-everybody/Taskbot-MVP/issues) 了解正在开发的功能。

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 💬 联系我们

- **问题反馈**：[GitHub Issues](https://github.com/justDance-everybody/Taskbot-MVP/issues)
- **功能讨论**：[GitHub Discussions](https://github.com/justDance-everybody/Taskbot-MVP/discussions)
- **项目维护者**：[@justDance-everybody](https://github.com/justDance-everybody)

---

**如果这个项目对你有帮助，别忘了给个 ⭐️ Star！**