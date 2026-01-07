# 📚 项目文档

飞书任务管理机器人完整文档索引

---

## 🚀 快速开始

### 新用户必读
- **[README.md](../README.md)** - 项目概述和部署指南
- **[QUICK_START.md](QUICK_START.md)** - 快速开始指南
- **[USER_GUIDE.md](USER_GUIDE.md)** - 用户使用手册

---

## 📖 配置指南

### 部署配置
- **[guides/FEISHU_BOT_SETUP.md](guides/FEISHU_BOT_SETUP.md)** - 飞书机器人完整配置（必读）
- **[guides/WEBHOOK_VERIFICATION_GUIDE.md](guides/WEBHOOK_VERIFICATION_GUIDE.md)** - Webhook验证指南
- **[guides/PERMISSION_SETUP.md](guides/PERMISSION_SETUP.md)** - 权限配置说明
- **[guides/LLM_API_SETUP.md](guides/LLM_API_SETUP.md)** - LLM API配置

---

## 🎯 功能指南

### 核心功能
- **[guides/CV_PARSER_GUIDE.md](guides/CV_PARSER_GUIDE.md)** - PDF简历解析功能
- **[guides/SUBGROUP_CREATION_GUIDE.md](guides/SUBGROUP_CREATION_GUIDE.md)** - 任务子群创建
- **[guides/MANUAL_ASSIGN_GUIDE.md](guides/MANUAL_ASSIGN_GUIDE.md)** - 任务分配指南

---

## 🔧 开发文档

### 产品文档
- **[task_bot_mvp_产品PRD需求文档.md](task_bot_mvp_产品PRD需求文档.md)** - 产品需求文档
- **[task_bot_mvp_产品开发文档.md](task_bot_mvp_产品开发文档.md)** - 开发文档
- **[task_bot_mvp_测试用例及验收文档.md](task_bot_mvp_测试用例及验收文档.md)** - 测试用例

### 技术文档
- **[task_bot_mvp_运行与环境配置.md](task_bot_mvp_运行与环境配置.md)** - 运行环境配置
- **[task_bot_mvp_prompt设定说明.md](task_bot_mvp_prompt设定说明.md)** - Prompt设定说明

---

## 🛠️ 故障排查

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 常见问题和解决方案
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 命令速查表

---

## 📂 项目结构

```
Taskbot-MVP/
├── app/                    # 应用代码
│   ├── services/          # 核心服务
│   │   ├── feishu.py     # 飞书API
│   │   ├── llm.py        # LLM服务
│   │   ├── cv_parser.py  # 简历解析
│   │   └── ...
│   ├── api.py            # API路由
│   ├── bitable.py        # 多维表格
│   ├── config.py         # 配置管理
│   └── webhooks.py       # Webhook处理
├── tests/                 # 测试代码
├── docs/                  # 文档目录
│   ├── guides/           # 功能指南
│   └── archive/          # 归档文档
├── main.py               # 应用入口
├── requirements.txt      # 依赖列表
└── README.md            # 项目说明
```

---

## 📝 使用场景

### 按角色查找

#### 👨‍💼 HR/管理员
1. [guides/FEISHU_BOT_SETUP.md](guides/FEISHU_BOT_SETUP.md) - 配置Bot
2. [USER_GUIDE.md](USER_GUIDE.md) - 创建和管理任务
3. [guides/CV_PARSER_GUIDE.md](guides/CV_PARSER_GUIDE.md) - 上传简历
4. [guides/MANUAL_ASSIGN_GUIDE.md](guides/MANUAL_ASSIGN_GUIDE.md) - 分配任务

#### 👨‍💻 开发者/承接人
1. [USER_GUIDE.md](USER_GUIDE.md) - 接收和完成任务
2. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 命令速查

#### 🔧 系统管理员
1. [../README.md](../README.md) - 部署指南
2. [guides/FEISHU_BOT_SETUP.md](guides/FEISHU_BOT_SETUP.md) - 完整配置
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - 故障排查

---

## 🔍 快速查找

### 我想...

- **开始使用Bot** → [USER_GUIDE.md](USER_GUIDE.md)
- **配置Bot** → [guides/FEISHU_BOT_SETUP.md](guides/FEISHU_BOT_SETUP.md)
- **解决Webhook问题** → [guides/WEBHOOK_VERIFICATION_GUIDE.md](guides/WEBHOOK_VERIFICATION_GUIDE.md)
- **了解简历解析** → [guides/CV_PARSER_GUIDE.md](guides/CV_PARSER_GUIDE.md)
- **查看命令列表** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **排查问题** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📞 获取帮助

### 查看日志
```bash
tail -f app.log
```

### 检查配置
```bash
cat .env
```

### 测试连接
```bash
curl http://localhost:8000/health
```

---

最后更新：2026-01-06
