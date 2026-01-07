# Design Document

## Overview

本设计文档描述飞书远程任务Bot MVP项目剩余功能的技术实现方案，包括Top-2匹配调整、定时调度模块、简历解析模块独立化、测试覆盖提升等。

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
├─────────────────────────────────────────────────────────────┤
│  Webhooks Layer                                              │
│  ├── /webhook/feishu (消息/卡片事件)                          │
│  └── /webhook/github (CI结果)                                │
├─────────────────────────────────────────────────────────────┤
│  Services Layer                                              │
│  ├── task_manager.py   (任务生命周期管理)                      │
│  ├── match.py          (Top-2候选人匹配) ← 需修改              │
│  ├── llm.py            (LLM路由)                             │
│  ├── cv_parser.py      (简历解析) ← 新增                      │
│  ├── scheduler.py      (定时任务) ← 新增                      │
│  ├── ci.py             (CI状态处理)                          │
│  └── feishu.py         (飞书API封装)                         │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  └── bitable.py        (多维表格CRUD)                        │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Match Service (修改)

**文件**: `app/services/match.py`

**修改内容**:
- 将 `find_top_candidates(limit=3)` 改为 `limit=2`
- 添加候选人池截断逻辑（最多15人）
- 移除匹配分数显示，只保留理由

```python
async def find_top_candidates(self, task_data: Dict[str, Any], limit: int = 2) -> List[Dict[str, Any]]:
    """为任务找到Top-2候选人"""
    # 获取候选人，限制最多15人
    candidates = await self.bitable.get_available_candidates(
        skill_requirements=task_data.get("skill_tags", []),
        limit=15  # PRD要求最多15人
    )
    # ... 匹配逻辑
    return sorted_candidates[:limit]  # 返回Top-2
```

### 2. Scheduler Module (新增)

**文件**: `app/services/scheduler.py`

**职责**:
- 周期过半提醒检查（每小时）
- 7天归档处理（每天）

```python
class TaskScheduler:
    async def check_deadline_reminders(self):
        """检查需要提醒的任务"""
        tasks = await self.bitable.get_in_progress_tasks()
        for task in tasks:
            if self._is_past_half_deadline(task) and not task.get('reminded'):
                await self._send_reminder(task)
                await self.bitable.mark_reminded(task['id'])
    
    async def archive_completed_tasks(self):
        """归档完成超过7天的任务"""
        tasks = await self.bitable.get_tasks_for_archiving(days=7)
        for task in tasks:
            await self._archive_task(task)
    
    def _is_past_half_deadline(self, task: Dict) -> bool:
        """判断是否已过半周期"""
        created = datetime.fromisoformat(task['created_at'])
        deadline = datetime.fromisoformat(task['deadline'])
        total_span = deadline - created
        half_point = created + total_span / 2
        return datetime.now() >= half_point
```

### 3. CV Parser Module (新增)

**文件**: `app/services/cv_parser.py`

**职责**:
- PDF文本提取
- LLM结构化解析
- 字段验证和默认值处理

```python
class CVParser:
    async def parse_resume(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """解析简历PDF"""
        # 1. 提取PDF文本
        text = await self._extract_pdf_text(file_content)
        
        # 2. LLM结构化解析
        structured_data = await self._llm_parse(text)
        
        # 3. 验证和填充默认值
        return self._validate_and_fill_defaults(structured_data, file_name)
    
    def _validate_and_fill_defaults(self, data: Dict, file_name: str) -> Dict:
        """验证数据并填充默认值"""
        defaults = {
            'name': file_name.replace('.pdf', ''),
            'email': '',
            'phone': '',
            'skills': [],
            'years_experience': 0,
            'hours_available': 10,
            'raw_text': '',
            'needs_review': False
        }
        # 标记需要人工审核的情况
        if not data.get('name') or not data.get('skills'):
            data['needs_review'] = True
        return {**defaults, **data}
```

### 4. Daily Report Enhancement

**修改文件**: `app/services/task_manager.py`

**输出格式**:
```markdown
📊 **每日任务报告** - {date}

**任务概览**
• 总任务数: {total}
• 已完成: {completed} ✅
• 进行中: {in_progress} 🔄
• 待分配: {pending} ⏳

**效率指标**
• 平均指派耗时: {avg_assign_time}
• 完成率: {completion_rate}%

**今日动态**
• 新建任务: {today_created}
• 完成任务: {today_completed}
```

## Data Models

### Task State Machine

```
┌─────────┐    创建     ┌─────────┐    匹配     ┌──────────┐
│  Draft  │ ─────────▶ │ Pending │ ─────────▶ │ Assigned │
└─────────┘            └─────────┘            └──────────┘
                                                   │
                                                   │ 接受
                                                   ▼
┌─────────┐    通过     ┌──────────┐   提交    ┌─────────────┐
│  Done   │ ◀───────── │ Reviewing│ ◀──────── │ In_Progress │
└─────────┘            └──────────┘           └─────────────┘
     │                      │
     │ 7天后                 │ 未通过
     ▼                      ▼
┌──────────┐           ┌──────────┐
│ Archived │           │ Returned │
└──────────┘           └──────────┘
```

### Reminder Record

```python
@dataclass
class ReminderRecord:
    task_id: str
    reminded_at: datetime
    reminder_type: str  # 'half_deadline' | 'overdue'
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Top-2 Candidate Limit

*For any* task matching request with a candidate pool of 2 or more candidates, the Match_Service SHALL return exactly 2 candidates.

**Validates: Requirements 1.1**

### Property 2: Candidate Pool Truncation

*For any* candidate pool exceeding 15 candidates, the Match_Service SHALL truncate to the 15 most recently updated candidates before matching.

**Validates: Requirements 1.4, 7.3**

### Property 3: Match Result Format

*For any* match result, the output SHALL contain candidate name and reason string, but SHALL NOT contain numeric match scores.

**Validates: Requirements 1.3**

### Property 4: Reminder Idempotence

*For any* task that has been reminded, calling the reminder check function again SHALL NOT send duplicate reminders (idempotence property).

**Validates: Requirements 2.2, 2.5**

### Property 5: Archive Timing

*For any* task marked Done, the task SHALL be archived exactly when 7 days have passed since completion, not before.

**Validates: Requirements 2.3**

### Property 6: Resume Parse Round-Trip

*For any* valid resume data structure, serializing to display format then parsing back SHALL preserve all essential fields (name, skills, experience).

**Validates: Requirements 3.5**

### Property 7: Resume Field Completeness

*For any* parsed resume, the output SHALL contain all required fields: name, email, phone, skills, years_experience, hours_available, raw_text.

**Validates: Requirements 3.2**

### Property 8: Daily Report Completeness

*For any* daily report generation, the output SHALL contain: total_tasks, completed_tasks, pending_tasks, in_progress_tasks, and average_assignment_time.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 9: Webhook Idempotence

*For any* GitHub webhook with the same delivery_id, processing it multiple times SHALL have the same effect as processing it once.

**Validates: Requirements 7.2**

## Error Handling

| 场景 | 处理方式 |
|-----|---------|
| LLM API超时 | 返回"AI延迟"消息，状态不变 |
| GitHub Webhook重复 | 比对delivery_id，跳过重复 |
| 候选人超过15人 | 截断到最近更新的15人 |
| PDF解析失败 | 使用默认值，标记需人工审核 |
| 多维表格API失败 | 记录日志，返回空结果 |

## Testing Strategy

### 测试分层

| 层级 | 工具 | 目标覆盖率 |
|-----|------|----------|
| 单元测试 | pytest + mock | 60% lines, 75% functions |
| 集成测试 | FastAPI TestClient | 关键路由100% |
| 属性测试 | hypothesis | 核心逻辑 |

### 单元测试重点

1. **match.py**: Top-2排序、候选人截断
2. **scheduler.py**: 周期计算、提醒逻辑
3. **cv_parser.py**: PDF提取、字段验证
4. **task_manager.py**: 状态转换、日报生成

### 属性测试配置

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(candidates=st.lists(st.fixed_dictionaries({
    'user_id': st.text(min_size=1),
    'skills': st.lists(st.text()),
    'score': st.integers(0, 100)
}), min_size=3, max_size=20))
def test_top2_always_returns_two(candidates):
    """Property 1: Top-2 Candidate Limit"""
    result = match_service.find_top_candidates_sync(task_data, candidates)
    assert len(result) == 2
```

### 测试文件结构

```
tests/
├── unit/
│   ├── test_match.py          # Top-2匹配测试
│   ├── test_scheduler.py      # 调度器测试
│   ├── test_cv_parser.py      # 简历解析测试
│   ├── test_task_manager.py   # 任务管理测试
│   └── test_github_webhook.py # (已存在)
├── integration/
│   ├── test_feishu_hook.py    # 飞书webhook测试
│   └── test_api.py            # API端点测试
├── property/
│   ├── test_match_properties.py
│   └── test_report_properties.py
└── conftest.py
```
