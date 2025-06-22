"""
Mock implementation of Feishu Bitable API for testing and development
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class FieldType(Enum):
    """Bitable field types"""
    TEXT = 1
    NUMBER = 2
    SINGLE_SELECT = 3
    MULTI_SELECT = 4
    DATE_TIME = 5
    CHECKBOX = 7
    USER = 11
    PHONE = 13
    URL = 15
    ATTACHMENT = 17
    SINGLE_LINK = 18
    LOOKUP = 19
    FORMULA = 20
    DUAL_LINK = 21
    LOCATION = 22
    GROUP_CHAT = 23
    CREATED_TIME = 1001
    MODIFIED_TIME = 1002
    CREATED_USER = 1003
    MODIFIED_USER = 1004
    AUTO_NUMBER = 1005


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


class MockBitableClient:
    """Mock Feishu Bitable API client for testing"""
    
    def __init__(self):
        # Mock data storage
        self._tables = {}
        self._records = {}
        self._record_counter = 1000
        
        # Initialize with some mock data
        self._init_mock_data()
    
    def _init_mock_data(self):
        """Initialize mock data"""
        # Create mock persons
        self._records["persons"] = [
            {
                "record_id": "rec_person_1",
                "fields": {
                    "user_id": "user_123",
                    "name": "张三",
                    "skill_tags": ["Python", "FastAPI", "PostgreSQL"],
                    "hours_available": 40,
                    "performance": 90.0,
                    "last_done_at": int((datetime.now().timestamp() - 86400 * 3) * 1000)
                },
                "created_time": "2024-01-01T00:00:00Z",
                "last_modified_time": "2024-01-01T00:00:00Z"
            },
            {
                "record_id": "rec_person_2",
                "fields": {
                    "user_id": "user_456",
                    "name": "李四",
                    "skill_tags": ["JavaScript", "React", "Node.js"],
                    "hours_available": 30,
                    "performance": 85.0,
                    "last_done_at": int((datetime.now().timestamp() - 86400 * 7) * 1000)
                },
                "created_time": "2024-01-01T00:00:00Z",
                "last_modified_time": "2024-01-01T00:00:00Z"
            },
            {
                "record_id": "rec_person_3",
                "fields": {
                    "user_id": "user_789",
                    "name": "王五",
                    "skill_tags": ["Python", "Django", "MySQL"],
                    "hours_available": 35,
                    "performance": 80.0,
                    "last_done_at": None
                },
                "created_time": "2024-01-01T00:00:00Z",
                "last_modified_time": "2024-01-01T00:00:00Z"
            }
        ]
        
        # Create mock tasks
        self._records["tasks"] = [
            {
                "record_id": "rec_task_1",
                "fields": {
                    "title": "创建用户API",
                    "description": "实现用户注册和登录功能",
                    "skill_tags": ["Python", "FastAPI"],
                    "status": TaskStatus.DONE.value,
                    "assignee_id": "user_123",
                    "ai_score": 90
                },
                "created_time": "2024-01-01T00:00:00Z",
                "last_modified_time": "2024-01-01T10:00:00Z"
            }
        ]
    
    async def create_table(self, table_name: str, fields: List[Dict[str, Any]]) -> str:
        """Create a new table"""
        table_id = f"tbl_{table_name.lower().replace(' ', '_')}"
        self._tables[table_id] = {
            "name": table_name,
            "fields": fields
        }
        logger.info(f"Created mock table {table_name} with ID: {table_id}")
        return table_id
    
    async def add_record(self, table_id: str, fields: Dict[str, Any]) -> str:
        """Add a record to table"""
        record_id = f"rec_{self._record_counter}"
        self._record_counter += 1
        
        # Determine table type from table_id
        table_key = "tasks" if "task" in table_id else "persons"
        
        if table_key not in self._records:
            self._records[table_key] = []
        
        record = {
            "record_id": record_id,
            "fields": fields,
            "created_time": datetime.now().isoformat() + "Z",
            "last_modified_time": datetime.now().isoformat() + "Z"
        }
        
        self._records[table_key].append(record)
        logger.info(f"Added mock record {record_id} to {table_key}")
        return record_id
    
    async def update_record(self, table_id: str, record_id: str, fields: Dict[str, Any]) -> bool:
        """Update a record"""
        table_key = "tasks" if "task" in table_id else "persons"
        
        if table_key in self._records:
            for record in self._records[table_key]:
                if record["record_id"] == record_id:
                    record["fields"].update(fields)
                    record["last_modified_time"] = datetime.now().isoformat() + "Z"
                    logger.info(f"Updated mock record {record_id}")
                    return True
        
        logger.warning(f"Record {record_id} not found for update")
        return False
    
    async def get_record(self, table_id: str, record_id: str) -> Dict[str, Any]:
        """Get a record"""
        table_key = "tasks" if "task" in table_id else "persons"
        
        if table_key in self._records:
            for record in self._records[table_key]:
                if record["record_id"] == record_id:
                    return record["fields"]
        
        raise Exception(f"Record {record_id} not found")
    
    async def list_records(self, table_id: str, page_size: int = 100, 
                          filter_condition: Optional[str] = None) -> List[Dict[str, Any]]:
        """List records from table"""
        table_key = "tasks" if "task" in table_id else "persons"
        
        if table_key not in self._records:
            return []
        
        records = self._records[table_key].copy()
        
        # Simple filter implementation
        if filter_condition and "status" in filter_condition:
            # Extract status value from filter condition
            import re
            match = re.search(r'"([^"]+)"', filter_condition)
            if match:
                status_value = match.group(1)
                records = [r for r in records if r["fields"].get("status") == status_value]
        
        return records[:page_size]
    
    async def delete_record(self, table_id: str, record_id: str) -> bool:
        """Delete a record"""
        table_key = "tasks" if "task" in table_id else "persons"
        
        if table_key in self._records:
            for i, record in enumerate(self._records[table_key]):
                if record["record_id"] == record_id:
                    del self._records[table_key][i]
                    logger.info(f"Deleted mock record {record_id}")
                    return True
        
        return False
    
    # Task-specific methods
    async def create_task(self, title: str, description: str, skill_tags: List[str], 
                         deadline: Optional[datetime] = None) -> str:
        """Create a new task"""
        fields = {
            "title": title,
            "description": description,
            "skill_tags": skill_tags,
            "status": TaskStatus.DRAFT.value
        }
        
        if deadline:
            fields["deadline"] = int(deadline.timestamp() * 1000)
        
        return await self.add_record("task_table", fields)
    
    async def assign_task(self, task_record_id: str, assignee_id: str, child_chat_id: str) -> bool:
        """Assign a task to a person"""
        fields = {
            "assignee_id": assignee_id,
            "child_chat_id": child_chat_id,
            "status": TaskStatus.ASSIGNED.value,
            "assigned_at": int(datetime.now().timestamp() * 1000)
        }
        
        return await self.update_record("task_table", task_record_id, fields)
    
    async def update_task_status(self, task_record_id: str, status: TaskStatus, 
                                ci_state: Optional[CIState] = None, 
                                ai_score: Optional[int] = None) -> bool:
        """Update task status"""
        fields = {"status": status.value}
        
        if ci_state:
            fields["ci_state"] = ci_state.value
        
        if ai_score is not None:
            fields["ai_score"] = ai_score
        
        if status == TaskStatus.DONE:
            fields["done_at"] = int(datetime.now().timestamp() * 1000)
        
        return await self.update_record("task_table", task_record_id, fields)
    
    async def get_task(self, task_record_id: str) -> Dict[str, Any]:
        """Get a task by record ID"""
        return await self.get_record("task_table", task_record_id)
    
    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """List tasks"""
        filter_condition = None
        if status:
            filter_condition = f'CurrentValue.[status] = "{status.value}"'
        
        return await self.list_records("task_table", filter_condition=filter_condition)
    
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
        
        return await self.add_record("person_table", fields)
    
    async def get_person_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a person by user ID"""
        records = await self.list_records("person_table")
        
        for record in records:
            if record["fields"].get("user_id") == user_id:
                return record
        
        return None
    
    async def list_available_persons(self, required_skills: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List available persons"""
        return await self.list_records("person_table")
    
    async def get_daily_task_stats(self, date: Optional[datetime] = None) -> Dict[str, int]:
        """Get daily task statistics"""
        tasks = await self.list_records("task_table")
        
        stats = {
            "total": len(tasks),
            "draft": 0,
            "assigned": 0,
            "in_progress": 0,
            "returned": 0,
            "done": 0,
            "archived": 0
        }
        
        for task in tasks:
            status = task["fields"].get("status", "").lower().replace(" ", "_")
            if status in stats:
                stats[status] += 1
        
        return stats


# Global mock client instance
_mock_bitable_client: Optional[MockBitableClient] = None


def get_bitable_client() -> MockBitableClient:
    """Get global mock bitable client instance"""
    global _mock_bitable_client
    if _mock_bitable_client is None:
        _mock_bitable_client = MockBitableClient()
    return _mock_bitable_client
