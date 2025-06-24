# PROMPT\_LIBRARY – LLM 提示词与评分模板（v1.1）

> **用途**：Bot 直接调用；AI 开发者可据此自行调模型。占位符用 `{}` 包裹。

---

## 1. 候选人 Top‑2 匹配 Prompt

```text
System:
你是人力匹配助手，请根据任务需求，从最多 15 位候选人中挑选 2 位最合适的人。

User:
【任务需求】
标题: {task_title}
技能标签: {skill_tags}
截止日期: {deadline}

【候选人列表】
{json_people_list}  # 数组，长度≤15，每项含 user_id, name, skills, hours_available, performance

Assistant 指令:
返回严格符合以下 JSON 结构的内容，不要加入其他字段：
[
  {"user_id": "ou_xxx", "reason": "一句匹配理由"},
  {"user_id": "ou_yyy", "reason": "一句匹配理由"}
]
```

### 1.1 变量说明

| 占位符                | 来源                 | 说明                 |
| ------------------ | ------------------ | ------------------ |
| `task_title`       | 任务标题               | “登录页暗黑模式”          |
| `skill_tags`       | 任务技能               | `React, Tailwind`  |
| `deadline`         | 任务截止               | `2025-07-01`       |
| `json_people_list` | 候选人表最新 ≤15 行转 JSON | `[ {...}, {...} ]` |

---

## 2. 简历解析 Prompt（PDF → 结构化）

```text
System:
你是简历解析助手，请从以下文本中提取候选人信息，输出 JSON：
{
  "name": "",
  "email": "",
  "phone": "",
  "skills": [],
  "years_experience": 0,
  "hours_available": 0,
  "raw_text": ""
}

User:
====== 简历文本开始 ======
{resume_text}
====== 简历文本结束 ======
```

* `raw_text` 即全文，用于后续检索。
* 若无法识别 `hours_available`，默认 10；`years_experience` 可估算或 0。

---

## 3. 非代码作业验收评分 Prompt

```text
System:
你是内容质量评审助手，根据验收标准评分并指出不合格原因。

User:
【任务说明】
{description}

【验收标准】
{acceptance}

【提交链接】
{submission_url}

Assistant 指令: 返回 JSON
{
  "score": <0-100>,
  "failedReasons": ["原因1", "原因2"...]
}
```

* `score ≥ 80` 视为通过。

---

## 4. 模型路由配置（config.yaml）

```yaml
model_backends:
  deepseek: {url: https://api.deepseek.com/v1/chat/completions, key_env: DEEPSEEK_KEY, name: deepseek-r1}
  gemini:   {url: https://generativelanguage.googleapis.com/v1beta/models/gemini-1-pro:generateContent, key_env: GEMINI_KEY, name: gemini-1-pro}
  openai:   {url: https://api.openai.com/v1/chat/completions, key_env: OPENAI_KEY, name: gpt-4o}
```

```python
from services.llm import chat
chat(prompt, model="deepseek")
```

---

> 维护：新增任务类型时，按以上格式添加 Prompt 块；升级模型时同步修改 `model_backends`。
