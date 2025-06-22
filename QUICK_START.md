# 🚀 飞书任务机器人快速启动指南

## 📋 当前状态

✅ **代码已完成** - 所有功能模块已实现并修正  
✅ **SDK已修正** - 使用正确的飞书官方API调用方式  
✅ **环境已准备** - conda环境feishu已配置完成  
⏳ **等待配置** - 需要您提供飞书应用信息  

## 🔧 下一步操作

### 1. 配置飞书应用信息

请在 `.env.production` 文件中填入您的飞书应用配置：

```bash
# 飞书应用配置 - 请替换为真实值
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx     # 您的应用ID
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx      # 您的应用密钥
FEISHU_VERIFY_TOKEN=xxxxxxxxxxxxxxxx    # 验证令牌
FEISHU_ENCRYPT_KEY=xxxxxxxxxxxxxxxx     # 加密密钥（可选）

# LLM服务配置 - 至少配置一个
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxx   # DeepSeek API密钥（推荐）
# 或者
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxx     # OpenAI API密钥
# 或者  
GOOGLE_API_KEY=xxxxxxxxxxxxxxxxx        # Google Gemini API密钥

# 可选配置
GITHUB_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxx # GitHub集成（可选）
```

### 2. 获取飞书应用配置

如果您还没有飞书应用，请按以下步骤创建：

1. **访问飞书开放平台**
   ```
   https://open.feishu.cn/app
   ```

2. **创建企业自建应用**
   - 点击"创建企业自建应用"
   - 填写应用名称：`任务管理机器人`
   - 选择应用类型：`机器人`

3. **获取应用凭证**
   - 在应用详情页面找到：
     - `App ID` (cli_开头)
     - `App Secret`
     - `Verify Token`
     - `Encrypt Key`（可选）

4. **配置应用权限**
   - 添加机器人权限：
     - `im:message` - 发送消息
     - `im:message.group_at_msg` - 接收@消息
     - `im:chat` - 群组管理
   - 添加多维表格权限：
     - `bitable:app` - 多维表格操作

### 3. 创建多维表格

配置完成后，运行以下命令创建多维表格：

```bash
# 激活环境
conda activate feishu

# 测试配置（推荐先运行）
python test_bitable_simple.py

# 创建完整的多维表格
python create_bitable_correct.py
```

### 4. 启动应用

```bash
# 启动生产环境
conda activate feishu
python start_production.py
```

应用将在 `http://localhost:8000` 启动。

### 5. 配置飞书应用回调

在飞书开放平台配置事件订阅：

1. **事件订阅URL**
   ```
   https://your-domain.com/webhook/feishu
   ```

2. **订阅事件**
   - `im.message.receive_v1` - 接收消息

## 🛠️ 可用的工具脚本

| 脚本 | 用途 | 命令 |
|------|------|------|
| `test_bitable_simple.py` | 测试基本API连接 | `python test_bitable_simple.py` |
| `create_bitable_correct.py` | 创建完整多维表格 | `python create_bitable_correct.py` |
| `start_production.py` | 启动生产环境 | `python start_production.py` |
| `setup_wizard.py` | 交互式配置向导 | `python setup_wizard.py` |
| `setup_complete.sh` | 完整配置脚本 | `./setup_complete.sh` |

## 📊 功能特性

### ✅ 已实现功能

1. **智能任务分派**
   - HR发布任务：`@bot 新任务`
   - AI智能匹配候选人
   - 一键分配任务

2. **自动验收系统**
   - 代码任务：GitHub CI检查
   - 非代码任务：LLM评分
   - 自动状态更新

3. **数据管理**
   - 飞书多维表格存储
   - 实时数据同步
   - 完整的CRUD操作

4. **多LLM支持**
   - DeepSeek（推荐）
   - OpenAI GPT
   - Google Gemini

### 🎯 核心流程

```
HR发布任务 → AI匹配候选人 → 推荐Top3 → 一键分配 → 自动验收 → 状态更新
```

## 🔍 故障排除

### 常见问题

1. **导入错误**
   ```bash
   conda activate feishu
   pip list | grep lark-oapi
   ```

2. **API调用失败**
   - 检查飞书应用权限
   - 验证App ID和App Secret
   - 确认网络连接

3. **多维表格创建失败**
   - 确认应用有bitable权限
   - 检查API调用参数

### 获取帮助

如果遇到问题：

1. 查看日志文件：`logs/app.log`
2. 运行测试脚本：`python test_bitable_simple.py`
3. 检查配置文件：`.env.production`

## 📞 准备就绪

当您准备好飞书应用配置后，请：

1. 填写 `.env.production` 文件
2. 运行 `python test_bitable_simple.py` 测试
3. 运行 `python create_bitable_correct.py` 创建表格
4. 运行 `python start_production.py` 启动应用

我随时准备帮助您完成配置和部署！
