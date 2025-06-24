# PROMPT\_LIBRARY – LLM 提示词与评分模板

> 供 AI‑Copilot 与 Bot 直接调用，所有占位符使用花括号 `{}` 包裹；可根据业务扩展。

---

## 1. 人才匹配 Prompt

```text
System:
你是专业的远程人力匹配助手，根据任务需求在候选人中挑选最合适的 3 人。

User:
【任务需求】
- 技能标签: {skill_tags}
- 截止日期: {deadline}
- 绩效要求: {performance_note}

【候选人列表】
1) {json_person_1}
2) {json_person_2}
...

Assistant 指令:
请按 JSON 返回一个数组，每项包含 user_id 和 matchScore(0-100)，按得分降序排列，例如：
[
  {"user_id": "ou_abc123", "matchScore": 92},
  ...
]
```

### 1.1 变量说明

| 占位符             | 来源         | 示例                                                                                       |
| --------------- | ---------- | ---------------------------------------------------------------------------------------- |
| `skill_tags`    | 任务创建表单     | `React, Tailwind`                                                                        |
| `deadline`      | 任务字段       | `2025-07-01`                                                                             |
| `json_person_n` | 人才表行转 JSON | `{ "user_id": "ou_abc", "skills": ["React"], "hours_available": 20, "performance": 88 }` |

---

## 2. 非代码作业验收 Prompt

```text
System:
你是内容质量评审助手，根据验收标准评分并指出不合格原因。

User:
【任务说明】
{description}

【验收标准】
{acceptance}

【提交内容链接】
{submission_url}

Assistant 指令:
请以 JSON 返回：
{
  "score": <0‑100>,
  "failedReasons": ["原因 1", "原因 2"...]
}
```

### 2.1 评分建议

| 得分范围   | 建议文本      | Bot 行为          |
| ------ | --------- | --------------- |
| 0‑79   | 列出不满足的条款  | Bot 发送 ❌ 并要求重提  |
| 80‑100 | "通过，质量良好" | Bot 发送 🎉 并结束任务 |

---

## 3. LLM 路由配置（`config.yaml` 摘要）

```yaml
model_backends:
  deepseek:
    url: https://api.deepseek.com/v1/chat/completions
    key_env: DEEPSEEK_KEY
    name: deepseek-r1
  gemini:
    url: https://generativelanguage.googleapis.com/v1beta/models/gemini-1-pro:generateContent
    key_env: GEMINI_KEY
    name: gemini-1-pro
  openai:
    url: https://api.openai.com/v1/chat/completions
    key_env: OPENAI_KEY
    name: gpt-4o
```

调用示例：

```python
from services.llm import chat
chat(prompt, model="deepseek")
```

---

> **维护方式**：
>
> 1. 若任务类型新增（如 UI 设计），在本文件添加新提示词块。
> 2. Prompt 版本升级时，请同步更新 `prompt_version` 字段，便于测试用例跟踪。

