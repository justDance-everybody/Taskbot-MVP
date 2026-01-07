"""
数据库审计日志测试
测试审计日志记录、查询和统计功能
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_audit_log_file():
    """创建临时审计日志文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        initial_data = {
            "created_at": datetime.now().isoformat(),
            "operations": []
        }
        json.dump(initial_data, f)
        temp_file = f.name
    
    yield temp_file
    
    # 清理
    try:
        os.unlink(temp_file)
    except:
        pass


@pytest.fixture
def audit_logger(temp_audit_log_file):
    """创建审计日志记录器实例"""
    from app.services.db_audit import DatabaseAuditLogger
    return DatabaseAuditLogger(log_file=temp_audit_log_file)


@pytest.fixture
def sample_operation_data():
    """操作数据示例"""
    return {
        "taskid": "task_123",
        "title": "开发用户登录API",
        "status": "in_progress",
        "assignee": "user_456",
        "description": "实现用户登录功能，包括密码验证和JWT token生成"
    }


@pytest.fixture
def populated_audit_logger(audit_logger, sample_operation_data):
    """填充了测试数据的审计日志记录器"""
    # 添加一些测试操作
    audit_logger.log_operation(
        operation_type="create",
        table="tasks",
        record_id="rec_001",
        data=sample_operation_data,
        user_id="user_123",
        result="success"
    )
    
    audit_logger.log_operation(
        operation_type="update",
        table="tasks",
        record_id="rec_001",
        data={"status": "completed"},
        user_id="user_123",
        result="success"
    )
    
    audit_logger.log_operation(
        operation_type="read",
        table="candidates",
        record_id="rec_002",
        user_id="user_456",
        result="success"
    )
    
    return audit_logger


# ============================================================================
# 测试类
# ============================================================================

class TestDatabaseAuditLoggerInit:
    """测试审计日志记录器初始化"""
    
    def test_init_creates_log_file(self, temp_audit_log_file):
        """测试初始化时创建日志文件"""
        from app.services.db_audit import DatabaseAuditLogger
        
        # 删除临时文件
        os.unlink(temp_audit_log_file)
        
        # 创建记录器
        logger = DatabaseAuditLogger(log_file=temp_audit_log_file)
        
        # 验证文件被创建
        assert os.path.exists(temp_audit_log_file)
        
        # 验证文件内容
        with open(temp_audit_log_file, 'r') as f:
            data = json.load(f)
            assert "created_at" in data
            assert "operations" in data
            assert data["operations"] == []
    
    def test_init_with_existing_file(self, temp_audit_log_file):
        """测试使用已存在的日志文件初始化"""
        from app.services.db_audit import DatabaseAuditLogger
        
        # 创建记录器
        logger = DatabaseAuditLogger(log_file=temp_audit_log_file)
        
        # 验证文件存在
        assert os.path.exists(temp_audit_log_file)


class TestLogOperation:
    """测试记录操作"""
    
    def test_log_operation_success(self, audit_logger, sample_operation_data):
        """测试成功记录操作"""
        # 执行
        audit_logger.log_operation(
            operation_type="create",
            table="tasks",
            record_id="rec_123",
            data=sample_operation_data,
            user_id="user_456",
            result="success"
        )
        
        # 验证
        operations = audit_logger.get_recent_operations(limit=1)
        assert len(operations) == 1
        
        op = operations[0]
        assert op["operation_type"] == "create"
        assert op["table"] == "tasks"
        assert op["record_id"] == "rec_123"
        assert op["user_id"] == "user_456"
        assert op["result"] == "success"
        assert "timestamp" in op
        assert "data_summary" in op
    
    def test_log_operation_failure(self, audit_logger):
        """测试记录失败操作"""
        # 执行
        audit_logger.log_operation(
            operation_type="delete",
            table="tasks",
            record_id="rec_456",
            user_id="user_789",
            result="failed",
            error_message="Record not found"
        )
        
        # 验证
        operations = audit_logger.get_recent_operations(limit=1)
        assert len(operations) == 1
        
        op = operations[0]
        assert op["result"] == "failed"
        assert op["error_message"] == "Record not found"
    
    def test_log_operation_without_data(self, audit_logger):
        """测试记录不带数据的操作"""
        # 执行
        audit_logger.log_operation(
            operation_type="read",
            table="candidates",
            record_id="rec_789",
            user_id="user_123"
        )
        
        # 验证
        operations = audit_logger.get_recent_operations(limit=1)
        assert len(operations) == 1
        
        op = operations[0]
        assert op["operation_type"] == "read"
        assert op["data_summary"] == {}
    
    def test_log_operation_limits_to_1000(self, audit_logger):
        """测试日志记录限制在1000条"""
        # 添加1001条记录
        for i in range(1001):
            audit_logger.log_operation(
                operation_type="create",
                table="tasks",
                record_id=f"rec_{i}",
                user_id="user_test"
            )
        
        # 验证只保留最近1000条
        log_data = audit_logger._read_log_data()
        assert len(log_data["operations"]) == 1000


class TestDataSummarization:
    """测试数据摘要功能"""
    
    def test_summarize_data_with_key_fields(self, audit_logger):
        """测试摘要包含关键字段"""
        data = {
            "taskid": "task_123",
            "title": "Test Task",
            "status": "pending",
            "extra_field": "extra_value"
        }
        
        summary = audit_logger._summarize_data(data)
        
        assert "taskid" in summary
        assert "title" in summary
        assert "status" in summary
        assert "total_fields" in summary
        assert summary["total_fields"] == 4
        assert "extra_field" not in summary
    
    def test_summarize_data_truncates_long_strings(self, audit_logger):
        """测试摘要截断长字符串"""
        data = {
            "title": "A" * 100  # 100个字符
        }
        
        summary = audit_logger._summarize_data(data)
        
        assert len(summary["title"]) == 53  # 50 + "..."
        assert summary["title"].endswith("...")
    
    def test_summarize_data_empty(self, audit_logger):
        """测试摘要空数据"""
        summary = audit_logger._summarize_data(None)
        assert summary == {}
        
        summary = audit_logger._summarize_data({})
        assert summary == {}  # Empty dict returns empty summary


class TestGetRecentOperations:
    """测试获取最近操作"""
    
    def test_get_recent_operations_default_limit(self, populated_audit_logger):
        """测试获取最近操作（默认限制）"""
        operations = populated_audit_logger.get_recent_operations()
        
        assert len(operations) == 3
        # 验证按时间顺序返回
        assert operations[0]["operation_type"] == "create"
        assert operations[1]["operation_type"] == "update"
        assert operations[2]["operation_type"] == "read"
    
    def test_get_recent_operations_custom_limit(self, populated_audit_logger):
        """测试获取最近操作（自定义限制）"""
        operations = populated_audit_logger.get_recent_operations(limit=2)
        
        assert len(operations) == 2
        # 应该返回最后2条
        assert operations[0]["operation_type"] == "update"
        assert operations[1]["operation_type"] == "read"
    
    def test_get_recent_operations_empty_log(self, audit_logger):
        """测试从空日志获取操作"""
        operations = audit_logger.get_recent_operations()
        
        assert operations == []


class TestGetOperationsByTable:
    """测试按表获取操作"""
    
    def test_get_operations_by_table_tasks(self, populated_audit_logger):
        """测试获取tasks表的操作"""
        operations = populated_audit_logger.get_operations_by_table("tasks")
        
        assert len(operations) == 2
        assert all(op["table"] == "tasks" for op in operations)
    
    def test_get_operations_by_table_candidates(self, populated_audit_logger):
        """测试获取candidates表的操作"""
        operations = populated_audit_logger.get_operations_by_table("candidates")
        
        assert len(operations) == 1
        assert operations[0]["table"] == "candidates"
    
    def test_get_operations_by_table_not_found(self, populated_audit_logger):
        """测试获取不存在的表的操作"""
        operations = populated_audit_logger.get_operations_by_table("nonexistent")
        
        assert operations == []
    
    def test_get_operations_by_table_with_limit(self, populated_audit_logger):
        """测试带限制获取表操作"""
        operations = populated_audit_logger.get_operations_by_table("tasks", limit=1)
        
        assert len(operations) == 1
        # 应该返回最后一条
        assert operations[0]["operation_type"] == "update"


class TestGetDailyStats:
    """测试获取日常统计"""
    
    def test_get_daily_stats_today(self, populated_audit_logger):
        """测试获取今天的统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats = populated_audit_logger.get_daily_stats(date=today)
        
        assert stats["date"] == today
        assert stats["total_operations"] == 3
        assert "by_type" in stats
        assert "by_table" in stats
        assert "by_result" in stats
        assert "by_user" in stats
        assert "timeline" in stats
    
    def test_get_daily_stats_by_type(self, populated_audit_logger):
        """测试按操作类型统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats = populated_audit_logger.get_daily_stats(date=today)
        
        assert stats["by_type"]["create"] == 1
        assert stats["by_type"]["update"] == 1
        assert stats["by_type"]["read"] == 1
    
    def test_get_daily_stats_by_table(self, populated_audit_logger):
        """测试按表统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats = populated_audit_logger.get_daily_stats(date=today)
        
        assert stats["by_table"]["tasks"] == 2
        assert stats["by_table"]["candidates"] == 1
    
    def test_get_daily_stats_by_result(self, populated_audit_logger):
        """测试按结果统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats = populated_audit_logger.get_daily_stats(date=today)
        
        assert stats["by_result"]["success"] == 3
        assert stats["by_result"]["failed"] == 0
    
    def test_get_daily_stats_by_user(self, populated_audit_logger):
        """测试按用户统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        stats = populated_audit_logger.get_daily_stats(date=today)
        
        assert stats["by_user"]["user_123"] == 2
        assert stats["by_user"]["user_456"] == 1
    
    def test_get_daily_stats_no_data(self, audit_logger):
        """测试没有数据的日期统计"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        stats = audit_logger.get_daily_stats(date=yesterday)
        
        assert stats["date"] == yesterday
        assert stats["total_operations"] == 0
        assert stats["by_type"] == {}
        assert stats["by_table"] == {}
    
    def test_get_daily_stats_default_today(self, populated_audit_logger):
        """测试默认获取今天的统计"""
        stats = populated_audit_logger.get_daily_stats()
        
        today = datetime.now().strftime('%Y-%m-%d')
        assert stats["date"] == today
        assert stats["total_operations"] == 3


class TestCleanupOldLogs:
    """测试清理旧日志"""
    
    def test_cleanup_old_logs_removes_old_entries(self, audit_logger):
        """测试清理旧日志条目"""
        # 添加旧日志
        old_date = (datetime.now() - timedelta(days=40)).isoformat()
        recent_date = datetime.now().isoformat()
        
        # 手动添加旧操作
        log_data = audit_logger._read_log_data()
        log_data["operations"].append({
            "timestamp": old_date,
            "operation_type": "create",
            "table": "tasks",
            "result": "success"
        })
        log_data["operations"].append({
            "timestamp": recent_date,
            "operation_type": "update",
            "table": "tasks",
            "result": "success"
        })
        
        with open(audit_logger.log_file, 'w') as f:
            json.dump(log_data, f)
        
        # 执行清理（保留30天）
        audit_logger.cleanup_old_logs(days_to_keep=30)
        
        # 验证
        operations = audit_logger.get_recent_operations()
        assert len(operations) == 1
        assert operations[0]["timestamp"] == recent_date
    
    def test_cleanup_old_logs_keeps_recent(self, populated_audit_logger):
        """测试清理保留最近的日志"""
        # 执行清理
        populated_audit_logger.cleanup_old_logs(days_to_keep=30)
        
        # 验证所有最近的操作都保留
        operations = populated_audit_logger.get_recent_operations()
        assert len(operations) == 3
    
    def test_cleanup_old_logs_no_operations(self, audit_logger):
        """测试清理空日志"""
        # 执行清理
        audit_logger.cleanup_old_logs(days_to_keep=30)
        
        # 验证不会出错
        operations = audit_logger.get_recent_operations()
        assert operations == []


class TestGlobalAuditLogger:
    """测试全局审计日志实例"""
    
    def test_global_audit_logger_exists(self):
        """测试全局审计日志实例存在"""
        from app.services.db_audit import audit_logger
        
        assert audit_logger is not None
        assert hasattr(audit_logger, 'log_operation')
    
    def test_log_db_operation_function(self):
        """测试便捷日志记录函数"""
        from app.services.db_audit import log_db_operation
        
        # 验证函数存在且可调用
        assert callable(log_db_operation)


class TestErrorHandling:
    """测试错误处理"""
    
    def test_log_operation_with_invalid_file(self):
        """测试日志文件无效时的错误处理"""
        from app.services.db_audit import DatabaseAuditLogger
        
        # 使用无效路径
        logger = DatabaseAuditLogger(log_file="/invalid/path/audit.json")
        
        # 应该不会抛出异常
        logger.log_operation(
            operation_type="create",
            table="tasks",
            record_id="rec_123"
        )
    
    def test_read_log_data_with_corrupted_file(self, audit_logger):
        """测试读取损坏的日志文件"""
        # 写入无效JSON
        with open(audit_logger.log_file, 'w') as f:
            f.write("invalid json content")
        
        # 应该返回默认数据结构
        log_data = audit_logger._read_log_data()
        
        assert "created_at" in log_data
        assert "operations" in log_data
        assert log_data["operations"] == []
    
    def test_get_daily_stats_with_error(self, audit_logger):
        """测试统计时发生错误"""
        # 写入无效JSON
        with open(audit_logger.log_file, 'w') as f:
            f.write("invalid json")
        
        # 应该返回错误统计
        stats = audit_logger.get_daily_stats()
        
        assert stats["total_operations"] == 0
        assert "error" in stats or stats["by_type"] == {}
