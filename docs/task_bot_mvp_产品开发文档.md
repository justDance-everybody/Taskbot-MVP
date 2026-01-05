# 技术设计说明（DEV\_SPEC）——飞书远程任务 Bot MVP

> **对应 PRD 版本**：TaskBot\_MVP\_PRD v1.1
> **目标读者**：具备 2 年开发经验、懂 Python & Webhook，主要借助 AI 编程助手完成编码。

---

## 1  总览

* **核心交付**：一个 FastAPI 服务，整合飞书机器人、多维表格、GitHub Webhook、LLM；实现 *任务创建→LLM Top‑2 匹配→一键指派→周期过半提醒→自动验收* 闭环。
* **最小部署**：`docker‑compose up` 本地跑通；Ngrok 暴露公网 URL。

```
┌─────────┐  HTTPS  ┌────────────────┐
│  飞书群  │◀────────▶│ FastAPI (Bot) │
└─────────┘           └────────────────┘
      ▲   ▲                ▲     ▲
      │   │卡片            写│     │读
      │   └────────┐        │     │
┌─────────────┐   REST   ┌────────────┐
│ 多维表格 API │◀────────▶│  LLM Router│
└─────────────┘           └────────────┘
```

---

## 2  代码结构

```
app/
  main.py           # FastAPI 入口 & 路由
  config.py         # 设置读取 config.yaml
  services/
    feishu.py       # 群/卡片封装
    bitable.py      # 多维表读写
    llm.py          # 模型路由 (deepseek / gemini / openai)
    match.py        # LLM Top‑2 匹配调用
    cv_parser.py    # 简历 PDF→结构化 JSON
    ci.py           # GitHub CI 结果解析
  router/
    feishu_hook.py  # /webhook/feishu
    github_hook.py  # /webhook/github
  scheduler.py      # 周期过半提醒 & 归档
  models.py         # Task / Person dataclass 缓存

Dockerfile
docker-compose.yml
config.yaml          # 密钥与阈值
Makefile             # dev / test 命令
README.md
```

### 2.1  关键依赖

```toml
fastapi~=0.111
uvicorn[standard]
httpx
larksuite-oapi>=2.0.6
pydantic
pdfplumber   # 提取 PDF 文本
pytest pytest-mock
playwright
```

---

## 3  核心流程实现细节

### 3.1  任务创建 & 追问

1. 监听 `im.message.receive_v1`；匹配 `@bot 新任务:` 开头。
2. 把任务草稿写入表 `tasks`（status=Draft）。
3. Bot 逐字段追问：描述 / 验收 / 技能 / **DDL 必填**。
4. 字段齐全后调用 `services.match.top2()`。

### 3.2  LLM Top‑2 匹配

```python
async def top2(task_json):
    people = bitable.fetch_people(limit=15)  # 最新 15 人
    prompt = build_top2_prompt(task_json, people)
    res = await llm.chat(prompt)
    return json.loads(res)  # [{user_id, reason}, {user_id, reason}]
```

* 无本地评分算法；只生成两人 + 理由。
* 卡片展示 “张三 – 技能完全匹配” / “李四 – 可用时间充足”。

### 3.3  指派 & 子群

* `chat.create` → `T-{task.id}-{title[:15]}` 私有群。
* `chat.add_user` 邀 HR + 承接人；子群首条贴任务卡片 `/done 用法`。

### 3.4  简历 PDF 自动解析

```python
text = extract_text(pdf_file)
json_str = llm.chat(build_cv_prompt(text))
data = json.loads(json_str)
bitable.insert_person(**data)  # 写候选人表
```

* **字段**：name, email, phone, skills\[], years\_experience, hours\_available, raw\_text。
* 若缺 `name` 或 `skills` → Bot 提醒 HR 手动补列。

### 3.5  进度提醒（周期过半）

```python
for task in tasks_in_progress():
    span = task.deadline - task.created_at
    if now >= task.created_at + span/2 and not task.reminded:
        feishu.remind(task.assignee, task.id)
        task.reminded = True
```

### 3.6  自动验收

```python
if task.is_code:
    pass_ = (ci.state(pr_url) == "green")
else:
    score = llm.score(doc_url, task.acceptance)
    pass_ = score >= settings.llm_threshold
```

* 未通过：状态 Returned + `retry_count += 1`（≤2）。
* 通过：状态 Done + 归档计时器启动。

### 3.7  KPI 报告

* 查询多维表：平均 `assigned_at-created_at`、各状态计数。
* 用 Markdown 卡片回复。

---

## 4  配置文件（config.yaml 示例）

```yaml
bot_prefix: "@bot"
skills_enum: ["React", "Python", "SEO", "写作"]
model_backends:
  deepseek: {url: "https://...", key_env: DEEPSEEK_KEY}
llm_threshold: 80
candidate_limit: 15          # 匹配时最多取 15 条候选
max_auto_returns: 2
archive_after_days: 7
```

---

## 5  开发任务清单（Issue 列表）

| #  | 分类      | 标题                             | 验收标准            |
| -- | ------- | ------------------------------ | --------------- |
| 1  | infra   | FastAPI 骨架 + `/webhook/feishu` | Ngrok 回调 200 OK |
| 2  | infra   | 多维表封装 `bitable.py`             | CRUD 正常         |
| 3  | feature | 任务创建 + 字段追问                    | 卡片互动写表 OK       |
| 4  | feature | **LLM Top‑2 匹配**               | 返回 2 人 + reason |
| 5  | feature | 子群创建 & 邀请                      | 子群成功            |
| 6  | feature | `/done` + CI 判定                | 绿灯通过            |
| 7  | feature | **简历 PDF 自动解析**                | 上传后表行出现完整字段     |
| 8  | cron    | **周期过半提醒**                     | 模拟时间跳转触发提醒      |
| 9  | cron    | 7 天归档                          | 改名 `[ARCHIVED]` |
| 10 | report  | `#report` KPI                  | 数字正确            |

---

## 6  运行与调试

*(与 v1.0 相同，此处省略，详见画布文档)*

---

## 7  CI / CD

* tests Job 只跑 `make test`（无自动补丁循环）。
* build-image Job 生成镜像，部署步骤留注释，后期开启。

---

> **版本** DEV\_SPEC v1.2 – 2025‑06‑18
> 变更：
> • 匹配改为 LLM Top‑2（候选≤15）
> • 新增简历 PDF 解析模块；删除本地评分算法
> • 提醒逻辑改为“周期过半”
> • 移除 CI 自动补丁循环描述
