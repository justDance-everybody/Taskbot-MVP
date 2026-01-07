# Implementation Plan: Test Coverage Improvement

## Overview

本任务清单将测试覆盖率从24%提升至60%，修复33个失败测试。按优先级分为三个阶段：P0修复失败测试和高价值覆盖，P1完善服务层测试，P2补充基础模块测试。

## Tasks

- [x] 1. 修复test_cv_parser.py失败测试
  - [x] 1.1 修复PDF文本提取测试的mock配置
    - 修复 `test_extract_pdf_text_with_pdfplumber` mock
    - 修复 `test_extract_pdf_text_fallback_to_pypdf2` mock
    - 修复 `test_extract_pdf_text_both_methods_fail` 错误处理
    - _Requirements: 1.1_
  - [x] 1.2 修复字段验证和默认值测试
    - 修复 `test_validate_and_fill_defaults_missing_name` 断言
    - 修复 `test_get_default_resume_data` 返回值
    - 修复 `test_parse_resume_success` 集成测试
    - _Requirements: 1.1_

- [x] 2. 修复test_match.py失败测试
  - [x] 2.1 修复Top-2匹配测试的mock配置
    - 在conftest.py中添加mock_bitable fixture
    - 修复 `test_find_top_candidates_returns_exactly_two`
    - 修复 `test_find_top_candidates_with_fewer_than_two`
    - 修复 `test_find_top_candidates_sorting_by_score`
    - _Requirements: 1.2_
  - [x] 2.2 修复候选人池截断测试
    - 修复 `test_candidate_pool_limited_to_15`
    - 修复 `test_candidate_pool_truncation_with_many_candidates`
    - _Requirements: 1.2_
  - [x] 2.3 修复空候选人池测试
    - 修复 `test_empty_candidate_pool_returns_empty_list`
    - 修复 `test_empty_candidate_pool_logs_warning`
    - 修复 `test_exception_handling_returns_empty_list`
    - _Requirements: 1.2_

- [x] 3. 修复test_scheduler.py失败测试
  - [x] 3.1 修复提醒持久化测试
    - 修复 `test_mark_reminded_updates_database` mock
    - 修复 `test_mark_reminded_without_record_id` 错误处理
    - _Requirements: 1.3_
  - [x] 3.2 修复任务查询测试
    - 修复 `test_get_in_progress_tasks_filters_correctly`
    - 修复 `test_get_completed_tasks_filters_correctly`
    - _Requirements: 1.3_

- [x] 4. 修复test_task_manager.py失败测试
  - [x] 4.1 修复状态转换测试
    - 修复 `test_create_task_sets_pending_status`
    - 修复 `test_accept_task_transitions_to_in_progress`
    - 修复 `test_accept_task_wrong_status_fails`
    - 修复 `test_submit_task_transitions_to_submitted`
    - 修复 `test_submit_task_wrong_assignee_fails`
    - 修复 `test_complete_task_transitions_to_completed`
    - 修复 `test_reject_task_transitions_to_rejected`
    - _Requirements: 1.4_
  - [x] 4.2 修复任务创建和分配测试
    - 修复 `test_create_task_with_all_fields`
    - 修复 `test_create_task_generates_task_id`
    - 修复 `test_assign_task_to_candidate`
    - _Requirements: 1.4_
  - [x] 4.3 修复任务状态查询测试
    - 修复 `test_get_task_status_success`
    - 修复 `test_get_task_status_not_found`
    - _Requirements: 1.4_

- [x] 5. Checkpoint - 验证所有测试通过
  - 运行 `pytest tests/unit/ -v`
  - 确保0个失败测试
  - 验证现有覆盖率基线

- [x] 6. 添加Bitable数据层测试
  - [x] 6.1 创建test_bitable.py基础结构
    - 创建 `tests/unit/test_bitable.py`
    - 添加mock httpx.AsyncClient fixture
    - 添加sample data fixtures
    - _Requirements: 2.1_
  - [x] 6.2 实现任务CRUD操作测试
    - 测试 `create_task_record`
    - 测试 `get_task_by_id`
    - 测试 `update_task_status`
    - 测试 `list_tasks_with_filters`
    - _Requirements: 2.2_
  - [x] 6.3 实现候选人CRUD操作测试
    - 测试 `create_candidate_record`
    - 测试 `get_candidate_by_id`
    - 测试 `get_available_candidates`
    - 测试 `update_candidate_status`
    - _Requirements: 2.3_
  - [x] 6.4 实现错误处理测试
    - 测试API超时处理
    - 测试API错误响应
    - 测试无效record_id处理
    - _Requirements: 2.5_

- [x] 7. 添加Webhook处理器测试
  - [x] 7.1 创建test_webhooks.py基础结构
    - 创建 `tests/unit/test_webhooks.py`
    - 添加mock services fixtures
    - _Requirements: 3.1_
  - [x] 7.2 实现消息路由测试
    - 测试文本消息路由
    - 测试卡片动作路由
    - 测试未知事件处理
    - _Requirements: 3.2_
  - [x] 7.3 实现命令解析测试
    - 测试help命令解析
    - 测试status命令解析
    - 测试report命令解析
    - 测试无效命令处理
    - _Requirements: 3.4_
  - [x] 7.4 实现错误处理测试
    - 测试无效签名处理
    - 测试格式错误payload
    - 测试服务异常处理
    - _Requirements: 3.5_

- [x] 8. Checkpoint - 验证覆盖率提升
  - 运行 `pytest --cov=app --cov-report=term`
  - 验证bitable.py覆盖率 ≥ 60%
  - 验证webhooks.py覆盖率 ≥ 40%
  - 验证整体覆盖率 ≥ 45%

- [x] 9. 添加Feishu服务测试
  - [x] 9.1 创建test_feishu.py
    - 创建 `tests/unit/test_feishu.py`
    - 添加mock httpx fixtures
    - _Requirements: 4.1_
  - [x] 9.2 实现API客户端测试
    - 测试send_message成功场景
    - 测试send_message超时
    - 测试send_message API错误
    - 测试get_user_info
    - _Requirements: 4.1_
  - [x] 9.3 实现重试逻辑测试
    - 测试超时重试
    - 测试速率限制重试
    - 测试最大重试次数
    - _Requirements: 4.5_

- [x] 10. 添加LLM服务测试
  - [x] 10.1 创建test_llm.py
    - 创建 `tests/unit/test_llm.py`
    - 添加mock OpenAI client
    - _Requirements: 4.2_
  - [x] 10.2 实现LLM服务测试
    - 测试analyze_resume成功
    - 测试analyze_resume超时
    - 测试模型降级
    - 测试match_candidates
    - _Requirements: 4.2_
  - [x] 10.3 实现错误处理测试
    - 测试API超时处理
    - 测试无效响应处理
    - 测试速率限制处理
    - _Requirements: 4.3, 4.4_

- [x] 11. 完善Task Manager和Scheduler测试
  - [x] 11.1 扩展test_task_manager.py
    - 添加日报生成测试
    - 添加任务统计测试
    - 添加批量操作测试
    - _Requirements: 1.4_
  - [x] 11.2 扩展test_scheduler.py
    - 添加周期计算边界测试
    - 添加并发提醒测试
    - 添加归档批处理测试
    - _Requirements: 1.3_

- [x] 12. Checkpoint - 验证P1目标达成
  - 运行 `pytest --cov=app --cov-report=term`
  - 验证feishu.py覆盖率 ≥ 50%
  - 验证llm.py覆盖率 ≥ 50%
  - 验证整体覆盖率 ≥ 55%

- [x] 13. 添加CI服务基础测试
  - [x] 13.1 创建test_ci.py
    - 创建 `tests/unit/test_ci.py`
    - 添加mock fixtures
    - _Requirements: 5.1_
  - [x] 13.2 实现基础功能测试
    - 测试process_ci_result成功
    - 测试process_ci_result失败
    - 测试update_task_status
    - _Requirements: 5.1, 5.4_

- [x] 14. 添加DB Audit基础测试
  - [x] 14.1 创建test_db_audit.py
    - 创建 `tests/unit/test_db_audit.py`
    - 添加mock fixtures
    - _Requirements: 5.2_
  - [x] 14.2 实现基础功能测试
    - 测试log_operation
    - 测试query_audit_logs
    - 测试export_audit_report
    - _Requirements: 5.2, 5.4_

- [x] 15. 添加Task Monitor基础测试
  - [x] 15.1 创建test_task_monitor.py
    - 创建 `tests/unit/test_task_monitor.py`
    - 添加mock fixtures
    - _Requirements: 5.3_
  - [x] 15.2 实现基础功能测试
    - 测试check_task_health
    - 测试detect_stuck_tasks
    - 测试send_alerts
    - _Requirements: 5.3, 5.5_

- [x] 16. 优化共享测试基础设施
  - [x] 16.1 完善conftest.py
    - 添加所有常用mock fixtures
    - 添加sample data fixtures
    - 添加helper functions
    - _Requirements: 7.1, 7.2_
  - [x] 16.2 标准化测试模式
    - 统一async测试装饰器使用
    - 统一mock配置模式
    - 统一断言模式
    - _Requirements: 7.2, 7.3_

- [x] 17. Final Checkpoint - 验证覆盖率目标
  - 运行 `pytest --cov=app --cov-report=term-missing --cov-report=html`
  - 验证行覆盖率 ≥ 60%
  - 验证函数覆盖率 ≥ 75%
  - 验证0个失败测试
  - 验证执行时间 < 30秒
  - 生成HTML覆盖率报告

## Notes

- 优先修复失败测试，确保测试套件可靠
- 重点关注bitable.py和webhooks.py，可快速提升覆盖率
- 使用conftest.py共享fixtures，提高测试可维护性
- 所有测试使用mock避免外部API调用
- 每个checkpoint验证阶段性成果
