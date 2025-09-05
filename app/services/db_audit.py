"""数据库操作审计日志模块"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DatabaseAuditLogger:
    """数据库操作审计日志记录器"""
    
    def __init__(self, log_file: str = "db_audit.json"):
        """初始化审计日志记录器
        
        Args:
            log_file: 审计日志文件路径
        """
        self.log_file = log_file
        self.ensure_log_file_exists()
    
    def ensure_log_file_exists(self):
        """确保日志文件存在"""
        try:
            log_path = Path(self.log_file)
            if not log_path.exists():
                # 创建空的审计日志文件
                initial_data = {
                    "created_at": datetime.now().isoformat(),
                    "operations": []
                }
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_data, f, ensure_ascii=False, indent=2)
                logger.info(f"审计日志文件已创建: {self.log_file}")
        except Exception as e:
            logger.error(f"创建审计日志文件失败: {str(e)}")
    
    def log_operation(self, operation_type: str, table: str, record_id: str = None, 
                      data: Dict[str, Any] = None, user_id: str = None, 
                      result: str = "success", error_message: str = None):
        """记录数据库操作
        
        Args:
            operation_type: 操作类型 (create, update, delete, read)
            table: 表名
            record_id: 记录ID
            data: 操作数据
            user_id: 操作用户ID
            result: 操作结果 (success, failed)
            error_message: 错误信息
        """
        try:
            operation_log = {
                "timestamp": datetime.now().isoformat(),
                "operation_type": operation_type,
                "table": table,
                "record_id": record_id,
                "user_id": user_id,
                "result": result,
                "data_summary": self._summarize_data(data),
                "error_message": error_message
            }
            
            # 读取现有日志
            log_data = self._read_log_data()
            
            # 添加新操作
            log_data["operations"].append(operation_log)
            
            # 保持最近1000条记录
            if len(log_data["operations"]) > 1000:
                log_data["operations"] = log_data["operations"][-1000:]
            
            # 写回文件
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"审计日志已记录: {operation_type} {table} {record_id}")
            
        except Exception as e:
            logger.error(f"记录审计日志失败: {str(e)}")
    
    def _read_log_data(self) -> Dict[str, Any]:
        """读取日志数据"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取审计日志失败: {str(e)}")
            return {
                "created_at": datetime.now().isoformat(),
                "operations": []
            }
    
    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """数据摘要（避免记录敏感信息）"""
        if not data:
            return {}
        
        # 只记录关键字段的摘要
        summary = {}
        key_fields = ['taskid', 'title', 'status', 'name', 'userid', 'operation_type']
        
        for field in key_fields:
            if field in data:
                value = data[field]
                # 限制字符串长度
                if isinstance(value, str) and len(value) > 50:
                    summary[field] = value[:50] + "..."
                else:
                    summary[field] = value
        
        summary["total_fields"] = len(data)
        return summary
    
    def get_recent_operations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的操作记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            最近的操作记录列表
        """
        try:
            log_data = self._read_log_data()
            operations = log_data.get("operations", [])
            return operations[-limit:] if len(operations) > limit else operations
        except Exception as e:
            logger.error(f"获取最近操作记录失败: {str(e)}")
            return []
    
    def get_operations_by_table(self, table: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取特定表的操作记录
        
        Args:
            table: 表名
            limit: 返回记录数量限制
            
        Returns:
            特定表的操作记录列表
        """
        try:
            log_data = self._read_log_data()
            operations = log_data.get("operations", [])
            
            # 筛选特定表的操作
            table_operations = [op for op in operations if op.get("table") == table]
            return table_operations[-limit:] if len(table_operations) > limit else table_operations
        except Exception as e:
            logger.error(f"获取表{table}的操作记录失败: {str(e)}")
            return []
    
    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """获取日常操作统计
        
        Args:
            date: 日期字符串 (YYYY-MM-DD)，默认为今天
            
        Returns:
            日常操作统计
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            log_data = self._read_log_data()
            operations = log_data.get("operations", [])
            
            # 筛选指定日期的操作
            daily_operations = [
                op for op in operations 
                if op.get("timestamp", "").startswith(date)
            ]
            
            # 统计分析
            stats = {
                "date": date,
                "total_operations": len(daily_operations),
                "by_type": {},
                "by_table": {},
                "by_result": {"success": 0, "failed": 0},
                "by_user": {},
                "timeline": []
            }
            
            for op in daily_operations:
                # 按操作类型统计
                op_type = op.get("operation_type", "unknown")
                stats["by_type"][op_type] = stats["by_type"].get(op_type, 0) + 1
                
                # 按表统计
                table = op.get("table", "unknown")
                stats["by_table"][table] = stats["by_table"].get(table, 0) + 1
                
                # 按结果统计
                result = op.get("result", "unknown")
                if result in stats["by_result"]:
                    stats["by_result"][result] += 1
                
                # 按用户统计
                user_id = op.get("user_id", "system")
                stats["by_user"][user_id] = stats["by_user"].get(user_id, 0) + 1
                
                # 时间线（每小时统计）
                timestamp = op.get("timestamp", "")
                if timestamp:
                    hour = timestamp[11:13]  # 提取小时
                    stats["timeline"].append({"time": hour, "operation": op_type})
            
            return stats
            
        except Exception as e:
            logger.error(f"获取日常操作统计失败: {str(e)}")
            return {
                "date": date or "unknown",
                "total_operations": 0,
                "by_type": {},
                "by_table": {},
                "by_result": {"success": 0, "failed": 0},
                "by_user": {},
                "timeline": [],
                "error": str(e)
            }
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧的审计日志
        
        Args:
            days_to_keep: 保留天数
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            log_data = self._read_log_data()
            operations = log_data.get("operations", [])
            
            # 保留指定天数内的操作
            filtered_operations = [
                op for op in operations 
                if op.get("timestamp", "") >= cutoff_str
            ]
            
            if len(filtered_operations) < len(operations):
                log_data["operations"] = filtered_operations
                
                with open(self.log_file, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, ensure_ascii=False, indent=2)
                
                removed_count = len(operations) - len(filtered_operations)
                logger.info(f"清理了 {removed_count} 条旧的审计日志记录")
            
        except Exception as e:
            logger.error(f"清理旧审计日志失败: {str(e)}")

# 创建全局审计日志实例
audit_logger = DatabaseAuditLogger()

def log_db_operation(operation_type: str, table: str, record_id: str = None,
                     data: Dict[str, Any] = None, user_id: str = None,
                     result: str = "success", error_message: str = None):
    """便捷的数据库操作日志记录函数
    
    Args:
        operation_type: 操作类型 (create, update, delete, read)
        table: 表名  
        record_id: 记录ID
        data: 操作数据
        user_id: 操作用户ID
        result: 操作结果 (success, failed)
        error_message: 错误信息
    """
    audit_logger.log_operation(
        operation_type=operation_type,
        table=table,
        record_id=record_id,
        data=data,
        user_id=user_id,
        result=result,
        error_message=error_message
    ) 