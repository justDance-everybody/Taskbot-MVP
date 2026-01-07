# 📚 文档索引

欢迎使用飞书任务管理Bot！这里是所有文档的索引。

---

## 🚀 快速开始

### 新用户必读
1. **`USER_GUIDE.md`** - 📱 用户使用指南
   - 如何使用Bot
   - 常用命令
   - 使用技巧

2. **`QUICK_REFERENCE.md`** - ⚡ 快速参考卡片
   - 5分钟上手
   - 命令速查表
   - 常见场景

3. **`QUICK_START.md`** - 🎯 快速开始
   - 项目概述
   - 快速部署

---

## ⚙️ 配置指南

### 管理员必读
1. **`FEISHU_BOT_SETUP.md`** - 🔧 完整配置指南
   - 飞书应用配置（8个步骤）
   - 权限设置
   - 事件订阅
   - 多维表格配置

2. **`CONFIG_CHECKLIST.md`** - ✅ 配置检查清单
   - 逐项检查配置
   - 确保不遗漏

3. **`WEBHOOK_VERIFICATION_GUIDE.md`** - 🔗 Webhook验证指南
   - Challenge验证
   - 事件订阅配置
   - 调试方法

4. **`WEBSOCKET_PROXY_FIX.md`** - 🔌 WebSocket代理修复
   - 解决代理错误
   - WebSocket vs Webhook
   - 配置选项

5. **`PERMISSION_SETUP.md`** - 🔐 权限配置
   - 飞书权限说明
   - 权限申请流程

---

## 📖 功能文档

### 核心功能
1. **`CV_PARSER_GUIDE.md`** - 📄 PDF简历解析指南
   - 简历解析功能
   - 技术实现
   - 使用方法
   - 最佳实践

2. **`SUBGROUP_CREATION_GUIDE.md`** - 👥 子群创建功能
   - 子群创建流程
   - 子群功能说明
   - 技术实现

3. **`demo_cv_parser.py`** - 🎬 简历解析演示
   - 运行演示脚本
   - 查看解析效果

---

## 📊 项目文档

### 项目总结
1. **`FINAL_SUMMARY.md`** - 📋 项目最终总结
   - 项目状态
   - 功能完整度
   - 测试结果
   - 性能指标

2. **`SUCCESS_SUMMARY.md`** - 🎉 成功总结
   - 项目成果
   - 关键里程碑

3. **`REQUIREMENTS_CHECK.md`** - ✔️ 需求验证报告
   - 需求完成情况
   - 功能验证

4. **`TEST_RESULTS.md`** - 🧪 测试结果报告
   - E2E测试结果
   - 功能测试
   - 问题修复记录

---

## 🧪 测试文档

### 测试脚本
1. **`test_e2e_workflow.py`** - 🔄 端到端测试
   - 完整流程测试
   - 8个测试步骤

2. **`test_simple.py`** - 🔍 简单数据测试
   - 多维表格读取测试

3. **`test_webhook.sh`** - 🌐 Webhook测试脚本
   - 自动化测试
   - Challenge验证

4. **`add_test_data.py`** - 📝 添加测试数据
   - 初始化测试数据
   - 候选人和任务数据

---

## 📚 参考文档

### 需求文档
1. **`docs/task_bot_mvp_产品PRD需求文档.md`** - 产品需求
2. **`docs/task_bot_mvp_产品开发文档.md`** - 开发文档
3. **`docs/task_bot_mvp_测试用例及验收文档.md`** - 测试用例

### 模板文档
1. **`TEST_DATA_TEMPLATE.md`** - 测试数据模板
2. **`.env.example`** - 环境变量示例

---

## 🔧 技术文档

### 代码结构
```
app/
├── api.py              # API路由
├── bitable.py          # 多维表格客户端
├── config.py           # 配置管理
├── webhooks.py         # Webhook处理
└── services/
    ├── cv_parser.py    # PDF简历解析
    ├── feishu.py       # 飞书服务
    ├── llm.py          # LLM服务
    ├── match.py        # 候选人匹配
    ├── task_manager.py # 任务管理
    └── scheduler.py    # 任务调度
```

### 测试代码
```
tests/
├── unit/               # 单元测试
├── integration/        # 集成测试
└── conftest.py         # 测试配置
```

---

## 📖 使用场景文档

### 按角色分类

#### 👨‍💼 HR/管理员
1. `FEISHU_BOT_SETUP.md` - 配置Bot
2. `USER_GUIDE.md` - 创建任务
3. `CV_PARSER_GUIDE.md` - 上传简历
4. `SUBGROUP_CREATION_GUIDE.md` - 管理子群

#### 👨‍💻 开发者/承接人
1. `USER_GUIDE.md` - 接收任务
2. `QUICK_REFERENCE.md` - 命令速查
3. 在子群中工作

#### 🔧 系统管理员
1. `FEISHU_BOT_SETUP.md` - 部署配置
2. `CONFIG_CHECKLIST.md` - 检查配置
3. `WEBHOOK_VERIFICATION_GUIDE.md` - 调试问题
4. `WEBSOCKET_PROXY_FIX.md` - 解决错误

---

## 🎯 按任务分类

### 初次部署
1. `README.md` - 项目概述
2. `FEISHU_BOT_SETUP.md` - 配置指南
3. `CONFIG_CHECKLIST.md` - 检查清单
4. `test_webhook.sh` - 验证配置

### 日常使用
1. `USER_GUIDE.md` - 使用指南
2. `QUICK_REFERENCE.md` - 快速参考
3. 在飞书中使用Bot

### 问题排查
1. `WEBHOOK_VERIFICATION_GUIDE.md` - Webhook问题
2. `WEBSOCKET_PROXY_FIX.md` - WebSocket问题
3. `app.log` - 查看日志
4. `test_simple.py` - 测试数据读取

### 功能了解
1. `FINAL_SUMMARY.md` - 功能总览
2. `CV_PARSER_GUIDE.md` - 简历解析
3. `SUBGROUP_CREATION_GUIDE.md` - 子群管理
4. `REQUIREMENTS_CHECK.md` - 需求验证

---

## 🔍 快速查找

### 我想...

#### 开始使用Bot
→ `USER_GUIDE.md`

#### 配置Bot
→ `FEISHU_BOT_SETUP.md`

#### 解决Challenge验证问题
→ `WEBHOOK_VERIFICATION_GUIDE.md`

#### 解决WebSocket错误
→ `WEBSOCKET_PROXY_FIX.md`

#### 了解简历解析功能
→ `CV_PARSER_GUIDE.md`

#### 了解子群创建
→ `SUBGROUP_CREATION_GUIDE.md`

#### 查看命令列表
→ `QUICK_REFERENCE.md`

#### 查看测试结果
→ `TEST_RESULTS.md`

#### 查看项目总结
→ `FINAL_SUMMARY.md`

#### 运行测试
→ `test_e2e_workflow.py` 或 `test_webhook.sh`

---

## 📞 获取帮助

### 文档没有解决问题？

1. **查看日志**
   ```bash
   tail -f app.log
   ```

2. **运行测试**
   ```bash
   ./test_webhook.sh
   python3 test_simple.py
   ```

3. **检查配置**
   ```bash
   # 查看环境变量
   cat .env
   
   # 检查服务状态
   ps aux | grep python3
   ```

4. **查看API文档**
   访问：http://localhost:8000/docs

---

## 🎉 开始使用

### 新用户推荐阅读顺序

1. **`USER_GUIDE.md`** - 了解如何使用
2. **`QUICK_REFERENCE.md`** - 记住常用命令
3. 在飞书中实际使用

### 管理员推荐阅读顺序

1. **`README.md`** - 项目概述
2. **`FEISHU_BOT_SETUP.md`** - 完整配置
3. **`CONFIG_CHECKLIST.md`** - 检查配置
4. **`WEBHOOK_VERIFICATION_GUIDE.md`** - 验证配置
5. **`USER_GUIDE.md`** - 学习使用

### 开发者推荐阅读顺序

1. **`FINAL_SUMMARY.md`** - 项目总结
2. **`REQUIREMENTS_CHECK.md`** - 需求验证
3. **`TEST_RESULTS.md`** - 测试结果
4. 代码文件（`app/` 目录）

---

## 📝 文档更新

最后更新：2026-01-06

如有文档问题或建议，请联系项目维护者。

---

**祝你使用愉快！** 🎉
