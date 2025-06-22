# 远程任务 Bot MVP — 全套项目文档

> **目的**  在完全远程、无法面对面沟通的情况下，让一名拥有 2 年开发经验、会使用 AI 编程助手的实习生，按照文档即可独立完成飞书 Chat‑Ops MVP 的开发、测试与交付。

---

## 0  阅读顺序

1. **PRD – 产品需求文档**
2. **TECH\_SPEC – 技术设计说明**
3. **ENV\_SETUP – 环境与凭据指南**
4. **PROMPT\_LIBRARY – LLM 提示词与评分模板**
5. **TEST\_PLAN – 功能与验收用例**

*(每个章节自成一体，可被 AI 单独检索；章节之间已加内部跳转链接。)*

---

## 1  PRD – 产品需求文档

### 1.1  背景与目标

- **问题**：任务分派与进度跟进全靠人工聊天，HR/业务主管耗时高、信息散。
- **目标**：交付一款 MVP 飞书机器人，使 “任务创建 → 指派” 时间以及 HR 手工触点数 **降低 ≥ 50 %**。

### 1.2  核心用户

| 角色                | 需求动机               |
| ----------------- | ------------------ |
| **HR / 协调者**      | 减少催促与统计，快速掌握全局     |
| **任务发布者**（工程师/PM） | 一条命令即可派活，不再手动匹配    |
| **远程兼职人员**        | 获取清晰需求、单一沟通入口、即时反馈 |

### 1.3  用户故事（MoSCoW）

- **必须实现**

  1. HR 在控制室群 `@bot 新任务 …`，≤ 10 秒收到候选人 Top‑3 卡片。
  2. HR 点击 **✅ 选 TA** 按钮后，Bot 自动创建私有子群并邀请承接人。
  3. 承接人在子群 `/done 链接` 提交结果后，Bot 根据 **“任务说明 + 验收标准”** 自动执行首轮验收：
     - **代码任务**：拉取 GitHub CI / Lint 结果；
     - **非代码任务**：调用 LLM 评分（得分 ≥ 80 视为通过）。
  4. **未通过**：Bot 立即回 "❌ 未通过" 并列出 `failedReasons[]`，状态 = *Returned*；承接人可在 **2 次内** 修订并重新 `/done`，无需 HR 介入。
  5. **通过**：Bot 回 "🎉 通过"，状态 = *Done*，触发归档计时。

- **应该实现**\
  6\. 子群 48 小时无动静 → Bot 自动提醒承接人并抄送 HR。\
  7\. HR 在群里输入 `#report` 查看当日任务统计。

- **可选 / 不做**\
  – 多人拆分同一任务、复杂 KPI 预测（留到后续迭代）。

### 1.4  功能流程（高层）

```  功能流程（高层）
```

HR → 控制室群 → Bot → GPT 匹配 → HR 点按钮 → Bot 建子群 → 承接人 ↔ Bot（进度沟通） → Bot 更新任务表 & KPI → 日终 #report

````

### 1.5  非功能需求

- 除 LLM 调用外，Bot 响应延时 < 1 秒
- 办公时间在线率 ≥ 99 %
- 单元测试覆盖率 ≥ 60 %

---

## 2  TECH\_SPEC – 技术设计说明

### 2.1  技术栈 & 版本

| 组件     | 选型                                    | 版本                  |
| ------ | ------------------------------------- | ------------------- |
| 运行时    | Python                                | 3.11                |
| Web 框架 | FastAPI                               | ^0.111              |
| 数据库    | **飞书多维表格（内置托管）**                      | —                   |
| 飞书 SDK | lark‑oapi                        | 最新                  |
| LLM 后端 | **可插拔** deepseek‑r1 / gemini / openai | `model_backends` 路由 |
| CI 示例  | GitHub Actions                        | ubuntu‑latest       |

### 2.2  高层架构图

```mermaid
graph TD
  HR-->|@bot|Bot
  Bot-->|LLM 匹配|LLM
  Bot-->|写入|TaskTable
  Bot-->|创建|ChildGroup
  ChildGroup-->|/done|Bot
  Bot-->|CI Webhook|GitHub
  Bot-->|更新|TaskTable
````

### 2.3  数据模型（ERD）

- **Task**(`id`, title, desc, skill\_tags, deadline, `assignee_id`, child\_chat\_id, status, ci\_state, ai\_score, created\_at, assigned\_at, done\_at)
- **Person**(`user_id`, name, skill\_tags, hours\_available, performance, last\_done\_at)

### 2.4  主要接口

| 路径                | 方法   | 鉴权        | 作用          |
| ----------------- | ---- | --------- | ----------- |
| `/webhook/feishu` | POST | Feishu 签名 | 接收群/子群/私聊事件 |
| `/webhook/github` | POST | HMAC      | 接收 CI 状态变更  |

### 2.5  模块拆分 & 目录

```
app/
  main.py         # FastAPI 入口
  services/
    feishu.py     # 发送/接收封装
    llm.py        # 模型路由与 Prompt 加载
    match.py      # Top‑3 算法
    ci.py         # GitHub 状态解析
  bitable.py     # 飞书多维表 API 封装
  config.py       # pydantic Settings -> config.yaml
```

---

## 3  ENV\_SETUP – 环境与凭据指南

### 3.1  前置条件

- 已开通飞书企业，拥有开发者权限
- 可用公网 HTTPS（开发阶段可用 Ngrok）
- GitHub 仓库 + Actions 样例

### 3.2  六步配置

1. **创建机器人**：飞书管理后台 → 开发者中心 → 新建内部应用。
2. 打开 **事件订阅**，回调 URL 填 `https://<domain>/webhook/feishu`。
3. 在「应用权限」增加：
   - `im:message`（发/收消息）
   - `chat:write`, `chat:update`（创建群、拉人）
   - `bitable:*`（读写多维表）
4. 复制 `App ID / App Secret / Verify Token` 到 `.env`。
5. 设置模型密钥：`DEEPSEEK_KEY` / `GEMINI_KEY` （可留备 `OPENAI_KEY`）。
6. `make dev` 一键启动 Uvicorn + Ngrok，将返回的公网地址回填飞书回调。

---

## 4  PROMPT\_LIBRARY – LLM 提示词模板

### 4.1  匹配 Prompt

```text
System: 你是智能人才匹配助手…
User: 任务需求: {skill_tags}, 截止: {deadline}, …
      候选人列表:
      1) {{json person1}}
      …
Assistant: 请返回 JSON 数组，包含 top‑3 的 user_id 与 matchScore(0‑100)。
```

### 4.2  验收评分 Prompt（非代码提交）

```text
System: 你是质量评审助手…
User: 任务说明 = «{description}»
      验收标准 = «{acceptance}»
      提交链接 = {url}
Assistant: 请输出 JSON：{ score: 0‑100, failedReasons: [] }
```

*(评分阈值、回退次数配置在 ****\`\`****)*

---

## 5  TEST_PLAN – 功能、边界与自动化测试方案

> 目标：既支持**手工验收**，又能在 CI 中被 AI‑Copilot / 开发者一键运行，及时暴露回gress。

### 5.1  测试结构总览
| 层级 | 工具 | 覆盖范围 | 触发命令 |
|------|------|----------|----------|
| **单元测试** | `pytest` + `pytest‑mock` | `services/*.py` 纯函数<br>Prompt 解析、CI 结果解析、表写入 | `make test-unit` |
| **集成测试** | `FastAPI TestClient` + 固定 Fixture JSON | `/webhook/feishu` & `/webhook/github` 路由<br>幂等/签名校验 | `make test-int` |
| **端到端测试** | Playwright（对接飞书沙箱组织） | 真群聊流：新任务→卡片→选人→子群→/done<br>断言最终状态写入多维表 | `make test-e2e` *(workflow_dispatch)* |

> **覆盖率门槛**：单元 + 集成整体 ≥ 60 %（`pytest --cov` 自动检测）。

### 5.2  核心用例示例
| 层级 | Case ID | 步骤 | 断言 |
|------|---------|------|------|
| 单元 | U‑CI‑01 | 读取 GitHub `success` payload | 返回 `Green` 状态 |
| 单元 | U‑LLM‑01 | 输入固定人员列表 → 匹配 Prompt | Top‑3 user_id 顺序一致 |
| 集成 | I‑FEI‑01 | `POST /webhook/feishu` 新任务事件 | 多维表新增一行，状态 = Draft |
| 集成 | I‑GIT‑01 | `POST /webhook/github` 红灯 | 对应任务 status = Returned |
| E2E | E‑FLOW‑01 | 全流程 Happy Path | 控制群/子群消息符合 Snapshot；任务 status = Done |

### 5.3  性能与稳定性
- **响应时间**：单位测试中模拟 100 并发事件，平均处理 < 1 s，P95 < 2 s。
- **幂等性**：重复推送同一 `event_id` 时，应被去重，任务状态不变。

### 5.4  CI 工作流模板（GitHub Actions）
```yaml
name: Bot CI
on:
  push:
    branches: [ main ]
  workflow_dispatch:
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: {python-version: '3.11'}
    - run: pip install -r requirements-dev.txt
    - run: make test-unit
  integration:
    needs: unit
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: {python-version: '3.11'}
    - run: pip install -r requirements-dev.txt
    - run: make test-int
  e2e:
    if: github.event_name == 'workflow_dispatch'
    needs: integration
    runs-on: ubuntu-latest
    env:
      FEISHU_BOT_TOKEN: ${{ secrets.FEISHU_BOT_TOKEN }}
      FEISHU_TEST_CHAT_ID: ${{ secrets.FEISHU_TEST_CHAT_ID }}
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: {python-version: '3.11'}
    - run: pip install -r requirements-dev.txt
    - run: make test-e2e
```

### 5.5  附：本地测试命令清单
```
make test           # 运行全部 (unit + int)
make test-unit      # 仅 services 层
make test-int       # FastAPI 集成
make test-e2e       # Playwright，对接飞书沙箱
```

---

> **说明** 端到端脚本所用的飞书沙箱组织及机器人凭证需放置于项目 Secrets；如暂无法跑 E2E，可将该 Job 标记为 `workflow_dispatch` 手动触发。

