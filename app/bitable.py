"""
Feishu Bitable (Multi-dimensional Table) API wrapper
Provides CRUD operations for Feishu Bitable tables
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import (
    CreateAppTableRequest,
    CreateAppTableRequestBody,
    AppTable,
    CreateAppTableRecordRequest,
    BatchCreateAppTableRecordRequestBody,
    UpdateAppTableRecordRequest,
    BatchUpdateAppTableRecordRequestBody,
    GetAppTableRecordRequest,
    ListAppTableRecordRequest,
    DeleteAppTableRecordRequest,
    AppTableField
)

from .config import get_settings

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """Bitable field types"""
    TEXT = 1  # 多行文本
    NUMBER = 2  # 数字
    SINGLE_SELECT = 3  # 单选
    MULTI_SELECT = 4  # 多选
    DATE_TIME = 5  # 日期时间
    CHECKBOX = 7  # 复选框
    USER = 11  # 人员
    PHONE = 13  # 电话号码
    URL = 15  # 超链接
    ATTACHMENT = 17  # 附件
    SINGLE_LINK = 18  # 单向关联
    LOOKUP = 19  # 查找引用
    FORMULA = 20  # 公式
    DUAL_LINK = 21  # 双向关联
    LOCATION = 22  # 地理位置
    GROUP_CHAT = 23  # 群组
    CREATED_TIME = 1001  # 创建时间
    MODIFIED_TIME = 1002  # 最后更新时间
    CREATED_USER = 1003  # 创建人
    MODIFIED_USER = 1004  # 修改人
    AUTO_NUMBER = 1005  # 自动编号


class TaskStatus(Enum):
    """Task status enumeration"""
    DRAFT = "Draft"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "InProgress"
    RETURNED = "Returned"
    DONE = "Done"
    ARCHIVED = "Archived"


class CIState(Enum):
    """CI state enumeration"""
    PENDING = "Pending"
    SUCCESS = "Success"
    FAILURE = "Failure"
    ERROR = "Error"


class BitableClient:
    """Feishu Bitable API client"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = lark.Client.builder() \
            .app_id(self.settings.feishu.app_id) \
            .app_secret(self.settings.feishu.app_secret) \
            .log_level(lark.LogLevel.DEBUG if self.settings.app.debug else lark.LogLevel.INFO) \
            .build()
        
        self.app_token = self.settings.feishu.bitable_app_token
        self.task_table_id = self.settings.feishu.task_table_id
        self.person_table_id = self.settings.feishu.person_table_id
    
    async def create_table(self, table_name: str, fields: List[Dict[str, Any]]) -> str:
        """Create a new table in the bitable"""
        try:
            # 构建字段列表
            field_list = []
            for field in fields:
                field_obj = AppTableField.builder() \
                    .field_name(field["field_name"]) \
                    .type(field["type"]) \
                    .build()
                if "property" in field:
                    field_obj.property = field["property"]
                field_list.append(field_obj)

            # 构建表格对象
            table = AppTable.builder() \
                .name(table_name) \
                .default_view_name("默认视图") \
                .fields(field_list) \
                .build()

            # 构建请求体
            request_body = CreateAppTableRequestBody.builder() \
                .table(table) \
                .build()

            # 构建请求
            request = CreateAppTableRequest.builder() \
                .app_token(self.app_token) \
                .request_body(request_body) \
                .build()

            # 发送请求
            response = self.client.bitable.v1.app_table.create(request)

            if not response.success():
                logger.error(f"Failed to create table: {response.msg}")
                raise Exception(f"Failed to create table: {response.msg}")

            table_id = response.data.table_id
            logger.info(f"Created table {table_name} with ID: {table_id}")
            return table_id

        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise
    
    async def create_task_table(self) -> str:
        """Create the task table with predefined schema"""
        fields = [
            {
                "field_name": "title",
                "type": FieldType.TEXT.value,
                "property": {}
            },
            {
                "field_name": "description", 
                "type": FieldType.TEXT.value,
                "property": {}
            },
            {
                "field_name": "skill_tags",
                "type": FieldType.MULTI_SELECT.value,
                "property": {
                    "options": [
                        {"name": "Python", "color": 1},
                        {"name": "JavaScript", "color": 2},
                        {"name": "React", "color": 3},
                        {"name": "Vue", "color": 4},
                        {"name": "Node.js", "color": 5},
                        {"name": "数据分析", "color": 6},
                        {"name": "UI设计", "color": 7},
                        {"name": "文案写作", "color": 8},
                        {"name": "测试", "color": 9},
                        {"name": "运维", "color": 10}
                    ]
                }
            },
            {
                "field_name": "deadline",
                "type": FieldType.DATE_TIME.value,
                "property": {}
            },
            {
                "field_name": "assignee_id",
                "type": FieldType.TEXT.value,
                "property": {}
            },
            {
                "field_name": "child_chat_id",
                "type": FieldType.TEXT.value,
                "property": {}
            },
            {
                "field_name": "status",
                "type": FieldType.SINGLE_SELECT.value,
                "property": {
                    "options": [
                        {"name": TaskStatus.DRAFT.value, "color": 1},
                        {"name": TaskStatus.ASSIGNED.value, "color": 2},
                        {"name": TaskStatus.IN_PROGRESS.value, "color": 3},
                        {"name": TaskStatus.RETURNED.value, "color": 4},
                        {"name": TaskStatus.DONE.value, "color": 5},
                        {"name": TaskStatus.ARCHIVED.value, "color": 6}
                    ]
                }
            },
            {
                "field_name": "ci_state",
                "type": FieldType.SINGLE_SELECT.value,
                "property": {
                    "options": [
                        {"name": CIState.PENDING.value, "color": 1},
                        {"name": CIState.SUCCESS.value, "color": 2},
                        {"name": CIState.FAILURE.value, "color": 3},
                        {"name": CIState.ERROR.value, "color": 4}
                    ]
                }
            },
            {
                "field_name": "ai_score",
                "type": FieldType.NUMBER.value,
                "property": {}
            },
            {
                "field_name": "created_at",
                "type": FieldType.CREATED_TIME.value,
                "property": {}
            },
            {
                "field_name": "assigned_at",
                "type": FieldType.DATE_TIME.value,
                "property": {}
            },
            {
                "field_name": "done_at",
                "type": FieldType.DATE_TIME.value,
                "property": {}
            }
        ]
        
        return await self.create_table("Tasks", fields)
    
    async def create_person_table(self) -> str:
        """Create the person table with predefined schema"""
        fields = [
            {
                "field_name": "user_id",
                "type": FieldType.TEXT.value,
                "property": {}
            },
            {
                "field_name": "name",
                "type": FieldType.TEXT.value,
                "property": {}
            },
            {
                "field_name": "skill_tags",
                "type": FieldType.MULTI_SELECT.value,
                "property": {
                    "options": [
                        {"name": "Python", "color": 1},
                        {"name": "JavaScript", "color": 2},
                        {"name": "React", "color": 3},
                        {"name": "Vue", "color": 4},
                        {"name": "Node.js", "color": 5},
                        {"name": "数据分析", "color": 6},
                        {"name": "UI设计", "color": 7},
                        {"name": "文案写作", "color": 8},
                        {"name": "测试", "color": 9},
                        {"name": "运维", "color": 10}
                    ]
                }
            },
            {
                "field_name": "hours_available",
                "type": FieldType.NUMBER.value,
                "property": {}
            },
            {
                "field_name": "performance",
                "type": FieldType.NUMBER.value,
                "property": {}
            },
            {
                "field_name": "last_done_at",
                "type": FieldType.DATE_TIME.value,
                "property": {}
            }
        ]
        
        return await self.create_table("Persons", fields)

    async def add_record(self, table_id: str, fields: Dict[str, Any]) -> str:
        """Add a record to the specified table"""
        try:
            # 使用批量创建API来创建单个记录
            records = [{"fields": fields}]

            request_body = BatchCreateAppTableRecordRequestBody.builder() \
                .records(records) \
                .build()

            # 构建请求 - 使用批量创建API
            from lark_oapi.api.bitable.v1 import BatchCreateAppTableRecordRequest
            request = BatchCreateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .request_body(request_body) \
                .build()

            # 发送请求
            response = self.client.bitable.v1.app_table_record.batch_create(request)

            if not response.success():
                logger.error(f"Failed to add record: {response.msg}")
                raise Exception(f"Failed to add record: {response.msg}")

            # 获取第一个记录的ID
            record_id = response.data.records[0].record_id
            logger.info(f"Added record with ID: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Error adding record: {e}")
            raise

    async def update_record(self, table_id: str, record_id: str, fields: Dict[str, Any]) -> bool:
        """Update a record in the specified table"""
        try:
            # 使用批量更新API来更新单个记录
            records = [{"record_id": record_id, "fields": fields}]

            request_body = BatchUpdateAppTableRecordRequestBody.builder() \
                .records(records) \
                .build()

            # 构建请求 - 使用批量更新API
            from lark_oapi.api.bitable.v1 import BatchUpdateAppTableRecordRequest
            request = BatchUpdateAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .request_body(request_body) \
                .build()

            # 发送请求
            response = self.client.bitable.v1.app_table_record.batch_update(request)

            if not response.success():
                logger.error(f"Failed to update record: {response.msg}")
                raise Exception(f"Failed to update record: {response.msg}")

            logger.info(f"Updated record {record_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating record: {e}")
            raise

    async def get_record(self, table_id: str, record_id: str) -> Dict[str, Any]:
        """Get a record from the specified table"""
        try:
            # 构建请求
            request = GetAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .record_id(record_id) \
                .build()

            # 发送请求
            response = self.client.bitable.v1.app_table_record.get(request)

            if not response.success():
                logger.error(f"Failed to get record: {response.msg}")
                raise Exception(f"Failed to get record: {response.msg}")

            return response.data.record.fields

        except Exception as e:
            logger.error(f"Error getting record: {e}")
            raise

    async def list_records(self, table_id: str, page_size: int = 100,
                          filter_condition: Optional[str] = None) -> List[Dict[str, Any]]:
        """List records from the specified table"""
        try:
            # 构建请求
            request_builder = ListAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .page_size(page_size)

            if filter_condition:
                request_builder.filter(filter_condition)

            request = request_builder.build()

            # 发送请求
            response = self.client.bitable.v1.app_table_record.list(request)

            if not response.success():
                logger.error(f"Failed to list records: {response.msg}")
                raise Exception(f"Failed to list records: {response.msg}")

            records = []
            # 检查 response.data 和 items 是否存在
            if response.data and response.data.items:
                for item in response.data.items:
                    records.append({
                        "record_id": item.record_id,
                        "fields": item.fields,
                        "created_time": item.created_time,
                        "last_modified_time": item.last_modified_time
                    })
            else:
                logger.info("No records found or empty response")

            return records

        except Exception as e:
            logger.error(f"Error listing records: {e}")
            raise

    async def delete_record(self, table_id: str, record_id: str) -> bool:
        """Delete a record from the specified table"""
        try:
            # 构建请求
            request = DeleteAppTableRecordRequest.builder() \
                .app_token(self.app_token) \
                .table_id(table_id) \
                .record_id(record_id) \
                .build()

            # 发送请求
            response = self.client.bitable.v1.app_table_record.delete(request)

            if not response.success():
                logger.error(f"Failed to delete record: {response.msg}")
                raise Exception(f"Failed to delete record: {response.msg}")

            logger.info(f"Deleted record {record_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            raise

    # Task-specific methods
    async def create_task(self, title: str, description: str, skill_tags: List[str],
                         deadline: Optional[datetime] = None) -> str:
        """Create a new task"""
        # 使用实际表格中的中文字段名
        fields = {
            "任务标题": title,
            "任务描述": description,
            "技能要求": skill_tags,
            "状态": "待分配"  # 使用表格中实际存在的状态选项
        }

        # 暂时不设置deadline，因为需要确认字段名
        # if deadline:
        #     fields["deadline"] = int(deadline.timestamp() * 1000)

        return await self.add_record(self.task_table_id, fields)

    async def assign_task(self, task_record_id: str, assignee_id: str, child_chat_id: str) -> bool:
        """Assign a task to a person"""
        fields = {
            "assignee_id": assignee_id,
            "child_chat_id": child_chat_id,
            "status": TaskStatus.ASSIGNED.value,
            "assigned_at": int(datetime.now().timestamp() * 1000)
        }

        return await self.update_record(self.task_table_id, task_record_id, fields)

    async def update_task_status(self, task_record_id: str, status: TaskStatus,
                                ci_state: Optional[CIState] = None,
                                ai_score: Optional[int] = None) -> bool:
        """Update task status and related fields"""
        fields = {"status": status.value}

        if ci_state:
            fields["ci_state"] = ci_state.value

        if ai_score is not None:
            fields["ai_score"] = ai_score

        if status == TaskStatus.DONE:
            fields["done_at"] = int(datetime.now().timestamp() * 1000)

        return await self.update_record(self.task_table_id, task_record_id, fields)

    async def get_task(self, task_record_id: str) -> Dict[str, Any]:
        """Get a task by record ID"""
        return await self.get_record(self.task_table_id, task_record_id)

    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by status"""
        filter_condition = None
        if status:
            filter_condition = f'CurrentValue.[status] = "{status.value}"'

        return await self.list_records(self.task_table_id, filter_condition=filter_condition)

    # Person-specific methods
    async def create_person(self, user_id: str, name: str, skill_tags: List[str],
                           hours_available: int = 40, performance: float = 80.0) -> str:
        """Create a new person record"""
        fields = {
            "user_id": user_id,
            "name": name,
            "skill_tags": skill_tags,
            "hours_available": hours_available,
            "performance": performance
        }

        return await self.add_record(self.person_table_id, fields)

    async def update_person_performance(self, person_record_id: str, performance: float) -> bool:
        """Update person's performance score"""
        fields = {
            "performance": performance,
            "last_done_at": int(datetime.now().timestamp() * 1000)
        }

        return await self.update_record(self.person_table_id, person_record_id, fields)

    async def get_person_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a person by user ID"""
        filter_condition = f'CurrentValue.[user_id] = "{user_id}"'
        records = await self.list_records(self.person_table_id, filter_condition=filter_condition)

        return records[0] if records else None

    async def list_available_persons(self, required_skills: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List available persons, optionally filtered by required skills"""
        # For now, just return all persons - skill matching will be done in the match service
        return await self.list_records(self.person_table_id)

    async def get_daily_task_stats(self, date: Optional[datetime] = None) -> Dict[str, int]:
        """Get daily task statistics"""
        try:
            # 简化版本：获取所有任务，不做时间过滤
            # 在实际应用中可以根据需要添加时间过滤
            tasks = await self.list_records(self.task_table_id)
            logger.info(f"Retrieved {len(tasks)} tasks for statistics")

            stats = {
                "total": len(tasks),
                "待分配": 0,
                "Draft": 0,
                "Assigned": 0,
                "InProgress": 0,
                "Done": 0,
                "Returned": 0
            }

            for task in tasks:
                # 使用实际的中文字段名
                status = task["fields"].get("状态")
                if status and status in stats:
                    stats[status] += 1

            return stats

        except Exception as e:
            logger.error(f"Error getting daily task stats: {e}")
            # 返回默认统计
            return {
                "total": 0,
                "draft": 0,
                "assigned": 0,
                "in_progress": 0,
                "returned": 0,
                "done": 0,
                "archived": 0
            }


# Global bitable client instance
_bitable_client: Optional[BitableClient] = None


def get_bitable_client() -> BitableClient:
    """Get global bitable client instance"""
    global _bitable_client
    if _bitable_client is None:
        _bitable_client = BitableClient()
    return _bitable_client
