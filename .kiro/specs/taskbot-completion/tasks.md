# Implementation Plan: TaskBot MVP Completion

## Overview

本任务清单基于需求和设计文档，将剩余开发工作分解为可执行的编码任务。任务按依赖关系排序，测试任务标记为可选(*)。

## Tasks

- [x] 1. 修改Match Service实现Top-2匹配
  - [x] 1.1 修改find_top_candidates方法默认limit为2
    - 修改 `app/services/match.py` 中的 `find_top_candidates` 方法
    - 将 `limit: int = 3` 改为 `limit: int = 2`
    - _Requirements: 1.1_
  - [x] 1.2 添加候选人池15人截断逻辑
    - 在获取候选人时添加 `limit=15` 参数
    - 按更新时间排序后截断
    - _Requirements: 1.4, 7.3_
  - [x] 1.3 移除匹配结果中的分数显示
    - 修改返回结果格式，只保留name和reason
    - 更新卡片消息模板
    - _Requirements: 1.3_
  - [x] 1.4 编写Top-2匹配属性测试
    - **Property 1: Top-2 Candidate Limit**
    - **Validates: Requirements 1.1**

- [x] 2. 创建Scheduler调度模块
  - [x] 2.1 创建scheduler.py基础结构
    - 创建 `app/services/scheduler.py`
    - 实现 `TaskScheduler` 类
    - _Requirements: 2.1_
  - [x] 2.2 实现周期过半提醒逻辑
    - 实现 `_is_past_half_deadline` 方法
    - 实现 `check_deadline_reminders` 方法
    - 添加reminded状态持久化
    - _Requirements: 2.2, 2.5_
  - [x] 2.3 实现7天归档逻辑
    - 实现 `archive_completed_tasks` 方法
    - 实现群聊重命名为 `[ARCHIVED]` 前缀
    - _Requirements: 2.3, 2.4_
  - [x] 2.4 集成调度器到main.py
    - 在lifespan中启动调度任务
    - 配置检查间隔（提醒每小时，归档每天）
    - _Requirements: 2.1_
  - [x] 2.5 编写调度器属性测试
    - **Property 4: Reminder Idempotence**
    - **Property 5: Archive Timing**
    - **Validates: Requirements 2.2, 2.3, 2.5**

- [x] 3. Checkpoint - 确保核心功能测试通过
  - 运行现有测试确保无回归
  - 验证Top-2匹配和调度器基本功能

- [x] 4. 创建独立CV Parser模块
  - [x] 4.1 创建cv_parser.py基础结构
    - 创建 `app/services/cv_parser.py`
    - 从 `llm.py` 迁移 `analyze_resume_pdf` 相关代码
    - _Requirements: 3.1_
  - [x] 4.2 实现PDF文本提取
    - 支持pdfplumber和PyPDF2双后端
    - 添加错误处理和降级逻辑
    - _Requirements: 3.1_
  - [x] 4.3 实现字段验证和默认值填充
    - 定义必需字段列表
    - 实现 `_validate_and_fill_defaults` 方法
    - 添加 `needs_review` 标记
    - _Requirements: 3.2, 3.3_
  - [x] 4.4 更新webhooks.py使用新模块
    - 修改简历上传处理逻辑
    - 导入并使用 `CVParser`
    - _Requirements: 3.1_
  - [x] 4.5 编写简历解析属性测试
    - **Property 6: Resume Parse Round-Trip**
    - **Property 7: Resume Field Completeness**
    - **Validates: Requirements 3.2, 3.5**

- [x] 5. 优化日报KPI格式
  - [x] 5.1 重构generate_daily_report方法
    - 修改 `app/services/task_manager.py`
    - 添加平均指派耗时计算
    - _Requirements: 6.1, 6.2_
  - [x] 5.2 实现Markdown卡片格式输出
    - 创建格式化模板
    - 支持飞书卡片消息格式
    - _Requirements: 6.3_
  - [x] 5.3 实现#report命令处理
    - 在webhooks.py中添加命令处理
    - 调用日报生成并发送
    - _Requirements: 6.4_
  - [x] 5.4 编写日报属性测试
    - **Property 8: Daily Report Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.3**

- [x] 6. Checkpoint - 功能完整性验证
  - 验证所有新功能正常工作
  - 确保与现有功能无冲突

- [x] 7. 增强错误处理
  - [x] 7.1 添加LLM超时处理
    - 在llm.py中添加超时异常处理
    - 返回"AI延迟"友好消息
    - _Requirements: 7.1_
  - [x] 7.2 实现GitHub Webhook去重
    - 添加delivery_id缓存
    - 跳过重复请求处理
    - _Requirements: 7.2_
  - [x] 7.3 编写错误处理属性测试
    - **Property 9: Webhook Idempotence**
    - **Validates: Requirements 7.2**

- [x] 8. 补充单元测试
  - [x] 8.1 创建test_match.py
    - 测试Top-2排序正确性
    - 测试候选人截断逻辑
    - 测试空候选人池处理
    - _Requirements: 4.3_
  - [x] 8.2 创建test_scheduler.py
    - 测试周期计算逻辑
    - 测试提醒状态持久化
    - 测试归档条件判断
    - _Requirements: 4.3_
  - [x] 8.3 创建test_cv_parser.py
    - 测试PDF文本提取
    - 测试字段验证逻辑
    - 测试默认值填充
    - _Requirements: 4.3_
  - [x] 8.4 扩展test_task_manager.py
    - 测试状态转换
    - 测试日报生成
    - _Requirements: 4.6_

- [x] 9. 补充集成测试
  - [x] 9.1 创建test_feishu_hook.py
    - 测试签名验证
    - 测试消息事件处理
    - 测试卡片动作处理
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 9.2 扩展test_api.py
    - 测试任务CRUD端点
    - 测试候选人查询端点
    - 测试日报端点
    - _Requirements: 5.4_

- [x] 10. Final Checkpoint - 测试覆盖率验证
  - 运行 `pytest --cov=app --cov-report=term-missing`
  - 确保行覆盖率 ≥ 60%
  - 确保函数覆盖率 ≥ 75%

## Notes

- 任务标记 `*` 为可选测试任务，可根据时间跳过
- 每个Checkpoint确保阶段性成果可验证
- 属性测试使用hypothesis库，每个属性至少100次迭代
- 测试应使用mock避免外部API调用
