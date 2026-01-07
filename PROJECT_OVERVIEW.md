# 飞书任务管理机器人 - 项目概览

## 📋 项目简介

Taskbot-MVP 是一个智能任务协作平台，专为组织管理外部兼职人员和临时任务而设计。通过飞书群聊与自动化Bot，实现任务创建、智能匹配、指派、进度提醒、自动验收及统计归档的全流程管理。

---

## ✨ 核心功能

### 1. 任务管理
- ✅ 快速创建任务（一句指令）
- ✅ 任务状态跟踪
- ✅ 自动进度提醒
- ✅ 智能任务验收

### 2. 候选人管理
- ✅ 简历自动解析（PDF/Word）
- ✅ AI智能匹配推荐
- ✅ 技能标签管理
- ✅ 历史表现追踪

### 3. 协作功能
- ✅ 自动创建任务子群
- ✅ 实时消息通知
- ✅ 群聊自动归档
- ✅ 多维表格同步

### 4. 数据统计
- ✅ 任务完成统计
- ✅ 候选人KPI
- ✅ 日报自动生成
- ✅ 数据可视化

---

## 🏗️ 技术架构

### 后端框架
- **FastAPI** - 高性能Web框架
- **Python 3.9+** - 主要开发语言
- **Uvicorn** - ASGI服务器

### 核心服务
- **飞书开放平台** - 消息、群组、多维表格
- **LLM服务** - DeepSeek/OpenAI/Gemini
- **PDF解析** - pdfplumber/PyPDF2

### 数据存储
- **飞书多维表格** - 任务和候选人数据
- **本地日志** - 运行日志和审计

---

## 📂 项目结构

```
Taskbot-MVP/
├── app/                      # 应用代码
│   ├── services/            # 核心服务
│   │   ├── feishu.py       # 飞书API封装
│   │   ├── llm.py          # LLM服务
│   │   ├── cv_parser.py    # 简历解析
│   │   ├── match.py        # 候选人匹配
│   │   ├── task_manager.py # 任务管理
│   │   ├── scheduler.py    # 定时任务
│   │   └── ...
│   ├── router/             # 路由模块
│   │   └── github_hook.py  # GitHub集成
│   ├── api.py              # API路由
│   ├── bitable.py          # 多维表格客户端
│   ├── config.py           # 配置管理
│   └── webhooks.py         # Webhook处理
├── tests/                   # 测试代码
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── docs/                    # 文档
│   ├── guides/             # 功能指南
│   └── README.md           # 文档索引
├── main.py                 # 应用入口
├── requirements.txt        # 依赖列表
├── Dockerfile              # Docker配置
├── docker-compose.yml      # Docker Compose
└── README.md              # 项目说明
```

---

## 🚀 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd Taskbot-MVP

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（必需）
vim .env
```

必需配置：
- `FEISHU_APP_ID` - 飞书应用ID
- `FEISHU_APP_SECRET` - 飞书应用密钥
- `FEISHU_BITABLE_APP_TOKEN` - 多维表格Token
- `FEISHU_TASK_TABLE_ID` - 任务表ID
- `FEISHU_PERSON_TABLE_ID` - 候选人表ID
- `DEEPSEEK_KEY` - LLM API密钥（至少一个）

### 3. 启动服务
```bash
python main.py
```

### 4. 配置飞书
参考 [docs/guides/FEISHU_BOT_SETUP.md](docs/guides/FEISHU_BOT_SETUP.md)

---

## 📖 文档导航

### 快速入门
- [README.md](README.md) - 完整部署指南
- [docs/QUICK_START.md](docs/QUICK_START.md) - 快速开始
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - 用户手册

### 配置指南
- [docs/guides/FEISHU_BOT_SETUP.md](docs/guides/FEISHU_BOT_SETUP.md) - 飞书配置（必读）
- [docs/guides/WEBHOOK_VERIFICATION_GUIDE.md](docs/guides/WEBHOOK_VERIFICATION_GUIDE.md) - Webhook验证
- [docs/guides/LLM_API_SETUP.md](docs/guides/LLM_API_SETUP.md) - LLM配置

### 功能说明
- [docs/guides/CV_PARSER_GUIDE.md](docs/guides/CV_PARSER_GUIDE.md) - 简历解析
- [docs/guides/SUBGROUP_CREATION_GUIDE.md](docs/guides/SUBGROUP_CREATION_GUIDE.md) - 子群创建
- [docs/guides/MANUAL_ASSIGN_GUIDE.md](docs/guides/MANUAL_ASSIGN_GUIDE.md) - 任务分配

### 故障排查
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - 常见问题
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - 命令速查

---

## 🔑 核心命令

### 任务管理
```
/newtask              # 创建新任务
/task list            # 查看任务列表
/task <id>            # 查看任务详情
/done <url>           # 提交任务完成
```

### 候选人管理
```
/candidates           # 查看候选人列表
[上传PDF]             # 自动解析简历
```

### 系统命令
```
/help                 # 查看帮助
/monitor              # 任务监控
ping                  # 测试连接
```

---

## 🧪 测试

### 运行测试
```bash
# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 所有测试
pytest -v
```

### 测试覆盖率
```bash
pytest --cov=app --cov-report=html
```

---

## 🐳 Docker部署

### 使用Docker Compose
```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 📊 性能指标

- **响应时间**: < 500ms（普通消息）
- **简历解析**: 3-6秒
- **AI匹配**: 2-5秒
- **并发支持**: 100+ 用户
- **可用性**: 99.9%

---

## 🛠️ 技术栈

### 核心技术
- Python 3.9+
- FastAPI
- Uvicorn
- Pydantic

### 集成服务
- 飞书开放平台
- DeepSeek/OpenAI/Gemini
- GitHub API

### 开发工具
- pytest（测试）
- black（代码格式化）
- flake8（代码检查）
- mypy（类型检查）

---

## 📝 开发规范

### 代码风格
- 遵循 PEP 8
- 使用类型注解
- 编写文档字符串

### 提交规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
test: 测试相关
refactor: 重构代码
```

---

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证

---

## 📞 联系方式

- 项目地址: [GitHub](https://github.com/your-org/Taskbot-MVP)
- 问题反馈: [Issues](https://github.com/your-org/Taskbot-MVP/issues)
- 文档: [docs/README.md](docs/README.md)

---

**最后更新**: 2026-01-06
