# 🚀 从这里开始

欢迎使用飞书任务管理机器人！

---

## ⚡ 快速导航

### 🆕 第一次使用？

1. **[README.md](README.md)** ← 从这里开始
   - 项目介绍
   - 完整部署指南
   - 环境配置

2. **[IMPLEMENTATION_COMPARISON.md](IMPLEMENTATION_COMPARISON.md)** ⭐ 新增
   - 项目实现对比
   - 功能完成度分析
   - 超出预期的亮点

3. **[docs/guides/FEISHU_BOT_SETUP.md](docs/guides/FEISHU_BOT_SETUP.md)**
   - 飞书应用配置（必读）
   - 权限设置
   - 多维表格配置

4. **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**
   - 如何使用Bot
   - 常用命令
   - 使用技巧

---

## 📚 文档结构

```
📄 README.md                    # 主文档 - 部署指南
📄 PROJECT_OVERVIEW.md          # 项目概览
📄 STRUCTURE.md                 # 项目结构说明

📁 docs/                        # 所有文档
   ├── README.md                # 文档索引
   ├── QUICK_START.md           # 快速开始
   ├── USER_GUIDE.md            # 用户手册
   ├── QUICK_REFERENCE.md       # 命令速查
   ├── TROUBLESHOOTING.md       # 故障排查
   │
   └── guides/                  # 详细指南
       ├── FEISHU_BOT_SETUP.md          # 飞书配置 ⭐
       ├── CV_PARSER_GUIDE.md           # 简历解析
       ├── SUBGROUP_CREATION_GUIDE.md   # 子群创建
       └── ...
```

---

## 🎯 按需求查找

### 我想部署Bot
→ **[README.md](README.md)** → **[docs/guides/FEISHU_BOT_SETUP.md](docs/guides/FEISHU_BOT_SETUP.md)**

### 我想学习使用
→ **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** → **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)**

### 我想了解功能
→ **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** → **[docs/guides/](docs/guides/)**

### 我遇到问题
→ **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**

### 我想看代码结构
→ **[STRUCTURE.md](STRUCTURE.md)**

### 我想看所有文档
→ **[docs/README.md](docs/README.md)**

---

## ⚙️ 快速部署（3步）

### 1️⃣ 安装依赖
```bash
pip install -r requirements.txt
```

### 2️⃣ 配置环境
```bash
cp .env.example .env
vim .env  # 填写必需配置
```

### 3️⃣ 启动服务
```bash
python main.py
```

详细步骤请看 **[README.md](README.md)**

---

## 🔑 核心命令

```bash
# 任务管理
/newtask              # 创建新任务
/task list            # 查看任务列表
/done <url>           # 提交任务

# 候选人管理
/candidates           # 查看候选人
[上传PDF]             # 解析简历

# 系统
/help                 # 查看帮助
ping                  # 测试连接
```

---

## 📞 需要帮助？

1. **查看文档**: [docs/README.md](docs/README.md)
2. **故障排查**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
3. **查看日志**: `tail -f app.log`

---

**开始使用**: [README.md](README.md) 👈
