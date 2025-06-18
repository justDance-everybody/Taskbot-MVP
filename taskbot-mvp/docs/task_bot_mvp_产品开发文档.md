# 技术开发说明（DEV\_SPEC）——飞书远程任务 Bot MVP

> **对应 PRD 版本**：TaskBot\_MVP\_PRD v1.0\
> **目标读者**：具备 2 年开发经验、熟悉 Python & Webhook 的远程实习生；主要依赖 AI 编程助手完成编码。

---

## 1. 总览

- **核心交付**：一个可部署的 FastAPI 服务，集成飞书机器人、多维表、GitHub Webhook 与可插拔 LLM。
- **最小部署方式**：`docker-compose up` 本地跑通；Ngrok 或 Cloudflare Tunnel 暴露公网回调。

```
┌─────────┐   HTTP   ┌────────────────┐
│  飞书群  │◀────────▶│  FastAPI (Bot) │
└─────────┘           └────────────────┘
      ▲  ▲                  ▲  ▲
  事件│  │消息卡片        写│  │读
      │  └─┐    SQL+REST   │  │  LLM
┌─────────────┐           ┌────────────┐
│  多维表格 API │           │  LLM Router│
└─────────────┘           └────────────┘
```

---

## 2. 代码结构

```
app/
  main.py          # FastAPI 入口 & 路由注册
  config.py        # pydantic Settings -> config.yaml
  services/
    feishu.py      # 发送/接收/卡片封装
    bitable.py     # 多维表读写封装
    llm.py         # 模型路由 (deepseek / gemini / openai)
    match.py       # Top‑3 算法 & Prompt
    ci.py          # GitHub 状态解析
  models.py        # dataclass Task, Person (内存缓存)
  router/
    feishu_hook.py # /webhook/feishu
    github_hook.py # /webhook/github
tests/
  unit/
  integration/
  e2e/
Dockerfile
docker-compose.yml
config.yaml          # 模型密钥、阈值、枚举
Makefile             # dev/test 命令
README.md
```

### 2.1  关键依赖

```toml
fastapi~=0.111
uvicorn[standard]
httpx
larksuite-oapi>=2.0.6
pydantic
pytest pytest-mock
playwright
```

---

## 3. 核心流程实现细节

### 3.1  任务创建 & 追问

1. 监听 `im.message.receive_v1` 事件；正则匹配 `@bot 新任务:`。
2. 将 **任务草稿** 存入多维表 `tasks`：status = Draft。
3. Bot 用 **消息卡片** 逐字段询问（描述 / 验收 / 技能标签 / DDL）。
4. 字段收齐后调用 `services.match.top3()`。

### 3.2  匹配算法

```python
def score(person, task):
    s = len(set(task.skill_tags) & set(person.skill_tags)) / len(task.skill_tags)
    a = min(person.hours_available / 10, 1)
    p = person.performance / 100
    return 0.5*s + 0.3*a + 0.2*p
```

- 返回 JSON `[ {user_id, score}, ... ]` 按分数排序。

### 3.3  指派 & 子群

- 使用 `chat.create` 创建名为 `T-{id}-{title[:15]}` 的私有群。
- `chat.add_user` 邀 HR 与承接人。
- 首条消息附任务卡片 + `/done 用法`。

### 3.4  进度提醒

- 在 `scheduler.py` 每小时扫描子群最后消息时间；若 `> reminder_hours` 且 status = In‑Progress → Bot `@`。

### 3.5  自动验收

```python
if task.is_code:
    ci_state = ci.fetch(pr_url)
    pass_ = ci_state == settings.ci_green_label
else:
    score, reasons = llm.score(doc_url, task.acceptance)
    pass_ = score >= settings.llm_threshold
```

- 未通过 → 状态 Returned + `retry_count+=1`（上限 2）。
- 通过 → 状态 Done + 记录 done\_at。

### 3.6  KPI 报告

- 查询多维表：`avg(assigned_at-created_at)` / `status counts`。
- 用文本卡片回复。

---

## 4. 配置文件（config.yaml 示例）

```yaml
bot_prefix: "@bot"
skills_enum: ["React", "Python", "SEO", "写作"]
matching_weights: {skill: 0.5, availability: 0.3, performance: 0.2}
model_backends:
  deepseek: {url: "https://...", key_env: DEEPSEEK_KEY}
llm_threshold: 80
reminder_hours: 48
max_auto_returns: 2
archive_after_days: 7
```

---

## 5. 开发任务清单（Issue 列）

| #  | 分类      | 标题                                   | 验收标准                               |
| -- | ------- | ------------------------------------ | ---------------------------------- |
| 1  | infra   | 搭建 FastAPI 骨架 + `/webhook/feishu` 路由 | Ngrok 回调 200 OK                    |
| 2  | infra   | Bitable API 封装                       | 能增删改查任务行                           |
| 3  | feature | 新任务正则 + 追问字段                         | 群聊交互回卡片 JSON OK                    |
| 4  | feature | LLM 匹配 & Top‑3 卡片                    | 模拟 3 人返回正确排序                       |
| 5  | feature | 子群创建 & 邀请                            | 控制室点击后群列表出现子群                      |
| 6  | feature | `/done` 解析 + CI Green 判定             | 本地跑绿灯 Fixture 通过                   |
| 7  | feature | 非代码 LLM 评分                           | 低分返回 failedReasons[]               |
| 8  | cron    | 48h 静默提醒                             | 模拟 lastActivity‑49h 发送提醒           |
| 9  | cron    | 7 天归档                                | 修改 done\_at ‑7d → 群改名 `[ARCHIVED]` |
| 10 | report  | `#report` 指令统计                       | 报表字段正确                             |

---

## 6. 运行与调试

```bash
# 克隆仓库
git clone …
cd taskbot
cp .env.example .env       # 填入 AppID/Secret/Keys
make dev                   # Uvicorn + Ngrok 本地启动

# 另一终端
make test                  # 跑全部单/集成测试
```

### 6.1 开发阶段推荐环境

| 场景                | 方案                                                   | 成本        | 步骤                                                 |
| ----------------- | ---------------------------------------------------- | --------- | -------------------------------------------------- |
| **快速迭代**          | 本地 + **Ngrok**                                       | 免费        | `make dev` 后复制公网 URL 填入飞书回调                        |
| **MVP 试用 / Demo** | **Render.com Free Web Service** 或 Railway/Fly.io 免费层 | 0 USD/月   | 1. 连接 GitHub 仓库2. 选择 Docker 部署3. 设置环境变量，点击 Deploy  |
| **长期稳定**          | Oracle Cloud Free VM / 最低配轻量云服务器                     | 0–3 USD/月 | 装 Docker + 自托管 Runner，使用 `docker-compose up -d` 部署 |

> 🚀 **推荐节奏**：先本地+Ngrok 打通 → Demo 用 Render 免费实例 → 生产再迁云服务器。

---

## 7. 持续集成 & 自动部署（可选）

> MVP 阶段 **CI 只跑自动化测试和构建镜像**。部署步骤先注释，待选定正式服务器再开启。

### 7.1 GitHub Actions 工作流片段

```yaml
name: Bot CI
on:
  push:
    branches: [ main ]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r requirements-dev.txt
      - run: make test           # 单元 + 集成测试
  build-image:
    needs: tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t taskbot:${{ github.sha }} .
      - run: echo "镜像已构建，可推送至 Registry (步骤已注释)"
  # deploy:
  #   needs: build-image
  #   runs-on: ubuntu-latest
  #   if: github.event_name == 'workflow_dispatch'
  #   steps:
  #     - name: SSH 部署到云服务器
  #       run: |
  #         echo "解开注释并配置 SSH 密钥后自动部署"
```

### 7.2 自托管 Runner 部署（折中方案）

1. 在云服务器拉取仓库、安装 `actions-runner`。
2. 设置 `RUNNER_ALLOW_RUNASROOT=1` 环境变量。
3. 开启 `persist bot service` 脚本；Runner 更新代码后自动重启容器。

---

> **版本** DEV\_SPEC v1.1 – 2025‑06‑18\
> 修订：添加“6 开发阶段推荐环境”与“7 CI/CD”两节，说明 Ngrok/Render 免费部署方案及可选自动化部署脚手架。

