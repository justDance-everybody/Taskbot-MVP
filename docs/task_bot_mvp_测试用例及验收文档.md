# 测试与验收方案（TEST\_PLAN）——飞书远程任务 Bot MVP

> **目标**：让 AI‑Copilot 能依赖本方案 **自动生成代码 → 运行测试 → 解析失败 → 自动修补 → 直至全部通过**；人类 HR 只需查看最终测试报告红绿灯。
>
> **覆盖文档**：对应 PRD v1.0 与 DEV\_SPEC v1.1

---

## 1. 测试分层与目标

| 层级            | 工具                             | 目的                       | 典型用例数          |
| ------------- | ------------------------------ | ------------------------ | -------------- |
| **单元**        | `pytest` + mock                | 校验纯函数 / Prompt 解析，定位行级错误 | 8–10           |
| **集成**        | `FastAPI TestClient` + 固定 JSON | 校验路由、签名、幂等、防 500         | 5              |
| **端到端 (E2E)** | Playwright + 飞书沙箱组织            | 复现真实群聊流程，确保业务闭环          | 2 (成功 / CI 红灯) |

> **通过门槛**：所有测试 100% 通过，覆盖率 ≥ 60% lines，≥ 75% functions。

---

## 2. 目录结构

```
tests/
  unit/
    test_match.py
    test_match.yaml
    …
  integration/
    test_feishu_hook.py
    test_feishu_hook.yaml
  e2e/
    test_happy_flow.py
    test_ci_failure.py
    fixtures/
run_with_ai.sh          # AI 修复循环驱动脚本
prompts/
  patch_prompt.tmpl     # GPT 补丁生成模板
```

### 2.1 YAML 元数据规范

| 字段            | 说明             | 示例                                 |
| ------------- | -------------- | ---------------------------------- |
| `id`          | 用例编号           | `U-MATCH-01`                       |
| `purpose`     | 用例意图（自然语言）     | “确保 Top‑3 排序正确”                    |
| `fixtures`    | 依赖数据文件         | `[persons_fixture.json]`           |
| `focus_files` | AI 应尝试修改的目录/文件 | `['app/services/match.py']`        |
| `expected`    | 断言（自然语言或伪代码）   | `result[0].user_id == 'ou_abc123'` |

> YAML 与测试脚本同名放置，AI 在修复时读取 `focus_files`，避免全局乱改。

---

## 3. 自动化执行流程

```mermaid
graph LR
  A(pytest --json) -->|failures.json| B(parse_fail)
  B --> C(prompt GPT)
  C -->|patch.diff| D(apply_patch)
  D --> E(run_tests_again)
  E -->|pass?|
    F{≤5循环}
  F -->|有失败| B
  F -->|全部通过| G[exit 0]
```

### 3.1 主脚本 `run_with_ai.sh`

```bash
#!/usr/bin/env bash
ITER=0
max=5
pytest -q --json-report
while jq -e '.summary.num_failed>0' .report.json && [ $ITER -lt $max ]; do
  python scripts/gen_prompt.py .report.json > prompt.txt
  python scripts/call_gpt.py prompt.txt > patch.diff || exit 1
  git apply patch.diff || exit 1
  pytest -q --json-report
  ITER=$((ITER+1))
done
exit $(jq '.summary.num_failed' .report.json)
```

### 3.2 GPT Patch Prompt (`patch_prompt.tmpl` 摘要)

```
你是资深 Python 开发…
以下是失败用例与焦点文件：
{{fail_summary}}
请输出符合 unified diff 的补丁，只修改 {{focus_files}}。
```

---

## 4. 核心用例示例

### 4.1 单元 (`tests/unit/test_match.py`)

```python
from app.services.match import score

def test_match_order(persons_fixture, task_fixture):
    ranked = sorted(persons_fixture, key=lambda p: score(p, task_fixture), reverse=True)
    assert ranked[0].user_id == 'ou_abc123'
```

### 4.2 集成 (`tests/integration/test_feishu_hook.py`)

```python
client = TestClient(app)

def test_new_task_hook(feishu_new_task_event):
    res = client.post('/webhook/feishu', json=feishu_new_task_event, headers=sign(feishu_new_task_event))
    assert res.status_code == 200
    row = bitable.get_task_by_title('登录页暗黑')
    assert row.status == 'Draft'
```

### 4.3 端到端 (`tests/e2e/test_happy_flow.py`)

```python
with playwright.sync_api.sync_playwright() as p:
    # 1. 发送指令
    send_message(chat_id, '@bot 新任务: 暗黑模式')
    # 2. 自动补字段
    auto_complete_fields()
    # 3. 点击卡片按钮
    click_button('选张三')
    # 4. /done 模拟 绿灯
    send_message(child_chat, '/done https://github.com/demo/pr/1')
    assert bitable.get_status(task_id) == 'Done'
```

---

## 5. CI 集成

- **tests** Job：`make test`（单元 + 集成）
- **ai‑loop** Job（可选）：手动触发或夜间 cron，看 AI 是否能自行将失败跑绿。

```yaml
  ai-loop:
    if: github.event_name == 'workflow_dispatch'
    steps:
      - run: bash tests/run_with_ai.sh
```

---

## 6. 验收标准

1. **CI “tests” Job 全绿**（0 failed, coverage ≥60%）。
2. 本地或 AI-loop Job 在 ≤5 轮内自动修补完全部失败。
3. HR 查看 `#report` 消息 KPI 与多维表状态一致。

> 达成以上三点，即视为本次迭代功能“开发完成，可提交 Demo / 合并主干”。

---

> 文档版本 TEST\_PLAN v1.0 — 2025‑06‑18 如果新增功能需扩展测试，只需：① 新增 test\_xx.py；② 写 YAML；③ 运行 AI‑loop 即可。

