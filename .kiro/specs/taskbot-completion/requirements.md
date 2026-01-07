# Requirements Document

## Introduction

本文档定义了飞书远程任务Bot MVP项目的剩余开发需求，基于对现有代码的分析和PRD v1.1的对比，明确需要完成的功能模块和测试覆盖。

## Glossary

- **Task_Bot**: 飞书远程任务管理机器人系统
- **Scheduler**: 定时任务调度模块，负责周期性任务执行
- **CV_Parser**: 简历解析模块，负责PDF简历的结构化提取
- **Bitable**: 飞书多维表格，用于数据存储
- **LLM**: 大语言模型，用于智能匹配和评分
- **CI_Service**: 持续集成服务，处理GitHub CI结果

## Requirements

### Requirement 1: LLM Top-2 匹配调整

**User Story:** As a HR, I want the system to recommend exactly 2 candidates, so that I can make quick decisions without information overload.

#### Acceptance Criteria

1. WHEN a task requires candidate matching, THE Match_Service SHALL return exactly 2 candidates (Top-2)
2. WHEN fewer than 2 candidates are available, THE Match_Service SHALL return all available candidates
3. WHEN displaying match results, THE Task_Bot SHALL show candidate name and one-sentence reason without scores
4. THE Match_Service SHALL limit candidate pool to maximum 15 most recently updated candidates

### Requirement 2: 定时任务调度模块

**User Story:** As a system administrator, I want automated scheduling for reminders and archiving, so that the system runs autonomously without manual intervention.

#### Acceptance Criteria

1. THE Scheduler SHALL check for tasks at 50% deadline progress every hour
2. WHEN a task reaches 50% of its deadline AND status is In-Progress AND not yet reminded, THE Scheduler SHALL send reminder to assignee and HR
3. WHEN a task is marked Done for 7 days, THE Scheduler SHALL rename the task group to `[ARCHIVED]` prefix
4. WHEN a task is archived, THE Scheduler SHALL remove the bot from the archived group
5. THE Scheduler SHALL persist reminder status to prevent duplicate reminders

### Requirement 3: 简历解析模块独立化

**User Story:** As a developer, I want a standalone CV parser module, so that the codebase is modular and maintainable.

#### Acceptance Criteria

1. THE CV_Parser SHALL extract text from PDF files using pdfplumber or PyPDF2
2. WHEN parsing a resume, THE CV_Parser SHALL extract: name, email, phone, skills, years_experience, hours_available, raw_text
3. WHEN a required field cannot be extracted, THE CV_Parser SHALL use default values and flag for manual review
4. THE CV_Parser SHALL support both Chinese and English resumes
5. FOR ALL valid resume PDFs, parsing then formatting back SHALL preserve essential information (round-trip property)

### Requirement 4: 单元测试覆盖

**User Story:** As a developer, I want comprehensive unit tests, so that code changes can be validated automatically.

#### Acceptance Criteria

1. THE Test_Suite SHALL achieve minimum 60% line coverage
2. THE Test_Suite SHALL achieve minimum 75% function coverage
3. WHEN testing match.py, THE Test_Suite SHALL verify Top-2 ranking correctness
4. WHEN testing llm.py, THE Test_Suite SHALL verify model fallback behavior
5. WHEN testing bitable.py, THE Test_Suite SHALL verify CRUD operations
6. WHEN testing task_manager.py, THE Test_Suite SHALL verify state transitions

### Requirement 5: 集成测试

**User Story:** As a QA engineer, I want integration tests for webhook endpoints, so that API contracts are verified.

#### Acceptance Criteria

1. WHEN testing /webhook/feishu endpoint, THE Test_Suite SHALL verify signature validation
2. WHEN testing /webhook/feishu endpoint, THE Test_Suite SHALL verify message event handling
3. WHEN testing /webhook/feishu endpoint, THE Test_Suite SHALL verify card action handling
4. WHEN testing /webhook/github endpoint, THE Test_Suite SHALL verify CI result processing
5. THE Test_Suite SHALL use mock services to avoid external API calls

### Requirement 6: 日报KPI格式优化

**User Story:** As a HR, I want formatted daily reports, so that I can quickly understand task statistics.

#### Acceptance Criteria

1. WHEN generating daily report, THE Task_Bot SHALL include: total tasks, completed tasks, pending tasks, in-progress tasks
2. WHEN generating daily report, THE Task_Bot SHALL calculate average assignment time
3. WHEN generating daily report, THE Task_Bot SHALL format output as Markdown card
4. THE Task_Bot SHALL respond to `#report` command with daily statistics

### Requirement 7: 错误处理增强

**User Story:** As a system user, I want graceful error handling, so that the system remains stable under edge cases.

#### Acceptance Criteria

1. WHEN LLM API times out, THE Task_Bot SHALL display "AI延迟" message and maintain current state
2. WHEN GitHub Webhook receives duplicate delivery_id, THE Task_Bot SHALL skip processing
3. WHEN candidate list exceeds 15, THE Task_Bot SHALL truncate to 15 most recently updated
4. IF any external API fails, THEN THE Task_Bot SHALL log error and provide fallback response
