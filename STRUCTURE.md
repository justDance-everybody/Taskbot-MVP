# 项目结构说明

## 📂 目录结构

```
Taskbot-MVP/
│
├── 📄 核心文件
│   ├── main.py                    # 应用入口
│   ├── requirements.txt           # Python依赖
│   ├── .env                       # 环境变量（需配置）
│   ├── .env.example              # 环境变量模板
│   └── config.yaml.example       # 配置文件模板
│
├── 📄 部署文件
│   ├── Dockerfile                # Docker镜像配置
│   ├── docker-compose.yml        # Docker Compose配置
│   ├── Makefile                  # 构建脚本
│   └── start_server.sh           # 启动脚本
│
├── 📄 文档
│   ├── README.md                 # 项目说明（主文档）
│   ├── PROJECT_OVERVIEW.md       # 项目概览
│   └── STRUCTURE.md              # 本文件
│
├── 📁 app/                       # 应用代码
│   ├── __init__.py
│   ├── api.py                    # API路由
│   ├── bitable.py                # 多维表格客户端
│   ├── config.py                 # 配置管理
│   ├── webhooks.py               # Webhook处理
│   │
│   ├── 📁 services/              # 核心服务
│   │   ├── __init__.py
│   │   ├── feishu.py            # 飞书API封装
│   │   ├── llm.py               # LLM服务
│   │   ├── cv_parser.py         # 简历解析
│   │   ├── match.py             # 候选人匹配
│   │   ├── task_manager.py      # 任务管理
│   │   ├── task_monitor.py      # 任务监控
│   │   ├── scheduler.py         # 定时任务
│   │   ├── db_audit.py          # 数据审计
│   │   └── ci.py                # CI集成
│   │
│   └── 📁 router/                # 路由模块
│       ├── __init__.py
│       └── github_hook.py       # GitHub Webhook
│
├── 📁 tests/                     # 测试代码
│   ├── conftest.py              # 测试配置
│   ├── 📁 unit/                 # 单元测试
│   └── 📁 integration/          # 集成测试
│
└── 📁 docs/                      # 文档目录
    ├── README.md                # 文档索引
    ├── DOCUMENTATION_INDEX.md   # 详细文档索引
    │
    ├── 📄 用户文档
    │   ├── QUICK_START.md       # 快速开始
    │   ├── USER_GUIDE.md        # 用户手册
    │   ├── QUICK_REFERENCE.md   # 命令速查
    │   └── TROUBLESHOOTING.md   # 故障排查
    │
    ├── 📁 guides/               # 功能指南
    │   ├── FEISHU_BOT_SETUP.md          # 飞书配置（必读）
    │   ├── WEBHOOK_VERIFICATION_GUIDE.md # Webhook验证
    │   ├── PERMISSION_SETUP.md          # 权限配置
    │   ├── LLM_API_SETUP.md            # LLM配置
    │   ├── CV_PARSER_GUIDE.md          # 简历解析
    │   ├── SUBGROUP_CREATION_GUIDE.md  # 子群创建
    │   └── MANUAL_ASSIGN_GUIDE.md      # 任务分配
    │
    ├── 📁 archive/              # 归档文档
    │   └── CHANGELOG.md         # 更新日志
    │
    └── 📄 产品文档
        ├── task_bot_mvp_产品PRD需求文档.md
        ├── task_bot_mvp_产品开发文档.md
        ├── task_bot_mvp_测试用例及验收文档.md
        ├── task_bot_mvp_运行与环境配置.md
        └── task_bot_mvp_prompt设定说明.md
```

---

## 📖 文档导航

### 🚀 新用户入门
1. **[README.md](README.md)** - 从这里开始
2. **[docs/QUICK_START.md](docs/QUICK_START.md)** - 快速部署
3. **[docs/guides/FEISHU_BOT_SETUP.md](docs/guides/FEISHU_BOT_SETUP.md)** - 飞书配置

### 📚 完整文档
- **[docs/README.md](docs/README.md)** - 文档索引
- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - 项目概览

---

## 🔑 核心模块说明

### app/api.py
- FastAPI路由定义
- 健康检查端点
- API版本管理

### app/webhooks.py
- 飞书事件处理
- 消息路由
- 命令解析
- 卡片交互

### app/bitable.py
- 多维表格CRUD操作
- 任务数据管理
- 候选人数据管理

### app/config.py
- 环境变量加载
- 配置验证
- 默认值设置

### app/services/feishu.py
- 飞书API封装
- 消息发送
- 群组管理
- 文件操作

### app/services/llm.py
- LLM服务抽象
- 多模型支持
- 智能匹配
- 文本分析

### app/services/cv_parser.py
- PDF文本提取
- 简历信息解析
- 结构化数据生成

### app/services/match.py
- 候选人匹配算法
- 技能评分
- 推荐排序

### app/services/task_manager.py
- 任务生命周期管理
- 状态流转
- 通知触发

### app/services/scheduler.py
- 定时任务调度
- 进度提醒
- 自动归档

---

## 🛠️ 开发指南

### 添加新功能
1. 在 `app/services/` 创建服务模块
2. 在 `app/webhooks.py` 添加命令处理
3. 在 `tests/` 添加测试
4. 更新文档

### 修改配置
1. 编辑 `.env` 文件
2. 更新 `app/config.py`（如需新配置项）
3. 重启服务

### 运行测试
```bash
# 所有测试
pytest

# 单个模块
pytest tests/unit/test_cv_parser.py

# 覆盖率
pytest --cov=app
```

---

## 📝 代码规范

### 文件命名
- 模块: `snake_case.py`
- 类: `PascalCase`
- 函数: `snake_case()`
- 常量: `UPPER_CASE`

### 导入顺序
1. 标准库
2. 第三方库
3. 本地模块

### 文档字符串
```python
def function_name(param: str) -> bool:
    """
    简短描述
    
    Args:
        param: 参数说明
        
    Returns:
        返回值说明
    """
    pass
```

---

## 🔍 快速查找

### 我想修改...

- **消息处理逻辑** → `app/webhooks.py`
- **飞书API调用** → `app/services/feishu.py`
- **任务匹配算法** → `app/services/match.py`
- **简历解析** → `app/services/cv_parser.py`
- **配置项** → `app/config.py` 和 `.env`
- **API路由** → `app/api.py`

### 我想了解...

- **如何部署** → `README.md`
- **如何配置** → `docs/guides/FEISHU_BOT_SETUP.md`
- **如何使用** → `docs/USER_GUIDE.md`
- **如何排查问题** → `docs/TROUBLESHOOTING.md`

---

**最后更新**: 2026-01-06
