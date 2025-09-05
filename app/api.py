from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from app.services.task_manager import task_manager, TaskStatus, TaskUrgency
from app.bitable import FeishuBitableClient, bitable_client
from app.services.feishu import FeishuService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])
feishu = FeishuService()

# Pydantic模型定义
class TaskCreateRequest(BaseModel):
    """创建任务请求模型"""
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    skill_tags: List[str] = Field(..., description="技能标签")
    deadline: str = Field(..., description="截止时间")
    urgency: str = Field(default=TaskUrgency.NORMAL.value, description="紧急程度")
    acceptance_criteria: str = Field(default="", description="验收标准")
    estimated_hours: int = Field(default=8, description="预估工时")
    reward_points: int = Field(default=100, description="奖励积分")
    created_by: str = Field(..., description="创建者ID")

class TaskSubmitRequest(BaseModel):
    """提交任务请求模型"""
    submission_url: str = Field(..., description="提交链接")
    submission_note: str = Field(default="", description="提交备注")

class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str
    title: str
    description: str
    status: str
    created_at: str
    deadline: str
    assignee: Optional[str] = None
    created_by: str
    skill_tags: List[str]
    urgency: str
    estimated_hours: int
    reward_points: int

class CandidateResponse(BaseModel):
    """候选人响应模型"""
    user_id: str
    name: str
    skill_tags: List[str]
    job_level: str
    experience: int
    total_tasks: int
    average_score: float

class DailyReportResponse(BaseModel):
    """每日报告响应模型"""
    date: str
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    average_score: float
    completion_rate: float

# 任务相关API
@router.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest):
    """创建新任务"""
    try:
        task_data = {
            'title': request.title,
            'description': request.description,
            'skill_tags': request.skill_tags,
            'deadline': request.deadline.isoformat(),
            'urgency': request.urgency,
            'acceptance_criteria': request.acceptance_criteria,
            'estimated_hours': request.estimated_hours,
            'reward_points': request.reward_points,
            'created_by': request.created_by
        }
        
        task_id = await task_manager.create_task(task_data)
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="任务创建成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务详情"""
    try:
        task = await task_manager.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskResponse(
            task_id=task_id,
            title=task.get('title', ''),
            description=task.get('description', ''),
            status=task.get('status', ''),
            created_at=task.get('created_at', ''),
            deadline=task.get('deadline', ''),
            assignee=task.get('assignee'),
            created_by=task.get('created_by', ''),
            skill_tags=task.get('skill_tags', []),
            urgency=task.get('urgency', 'normal'),
            estimated_hours=task.get('estimated_hours', 8),
            reward_points=task.get('reward_points', 100)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/accept")
async def accept_task(task_id: str, user_id: str = Query(..., description="用户ID")):
    """接受任务"""
    try:
        success = await task_manager.accept_task(task_id, user_id)
        if success:
            return {"message": "Task accepted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to accept task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/{task_id}/submit")
async def submit_task(task_id: str, submit_data: TaskSubmitRequest, 
                     user_id: str = Query(..., description="用户ID")):
    """提交任务"""
    try:
        success = await task_manager.submit_task(
            task_id=task_id,
            user_id=user_id,
            submission_url=submit_data.submission_url,
            submission_note=submit_data.submission_note
        )
        if success:
            return {"message": "Task submitted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to submit task")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    assignee: Optional[str] = Query(None, description="负责人过滤"),
    created_by: Optional[str] = Query(None, description="创建者过滤"),
    limit: int = Query(20, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """获取任务列表"""
    try:
        # 这里需要实现实际的查询逻辑
        # 暂时返回空列表
        return []
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/tasks", response_model=List[TaskResponse])
async def get_user_tasks(user_id: str, status: Optional[str] = Query(None)):
    """获取用户任务列表"""
    try:
        tasks = await task_manager.get_user_tasks(user_id, status)
        return [
            TaskResponse(
                task_id=task.get('task_id', ''),
                title=task.get('title', ''),
                description=task.get('description', ''),
                status=task.get('status', ''),
                created_at=task.get('created_at', ''),
                deadline=task.get('deadline', ''),
                assignee=task.get('assignee'),
                created_by=task.get('created_by', ''),
                skill_tags=task.get('skill_tags', []),
                urgency=task.get('urgency', 'normal'),
                estimated_hours=task.get('estimated_hours', 8),
                reward_points=task.get('reward_points', 100)
            )
            for task in tasks
        ]
    except Exception as e:
        logger.error(f"Error getting user tasks for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 候选人相关API
@router.get("/candidates", response_model=List[CandidateResponse])
async def get_candidates():
    """获取候选人列表"""
    try:
        candidates = await bitable.get_available_candidates()
        return [
            CandidateResponse(
                user_id=candidate.get('user_id', ''),
                name=candidate.get('name', ''),
                skill_tags=candidate.get('skill_tags', []),
                job_level=candidate.get('job_level', ''),
                experience=candidate.get('experience', 0),
                total_tasks=candidate.get('total_tasks', 0),
                average_score=candidate.get('average_score', 0.0)
            )
            for candidate in candidates
        ]
    except Exception as e:
        logger.error(f"Error getting candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/{user_id}", response_model=CandidateResponse)
async def get_candidate(user_id: str):
    """获取候选人详情"""
    try:
        # 这里需要实现获取单个候选人的逻辑
        candidates = await bitable.get_available_candidates()
        candidate = next((c for c in candidates if c.get('user_id') == user_id), None)
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return CandidateResponse(
            user_id=candidate.get('user_id', ''),
            name=candidate.get('name', ''),
            skill_tags=candidate.get('skill_tags', []),
            job_level=candidate.get('job_level', ''),
            experience=candidate.get('experience', 0),
            total_tasks=candidate.get('total_tasks', 0),
            average_score=candidate.get('average_score', 0.0)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 统计和报告API
@router.get("/reports/daily", response_model=DailyReportResponse)
async def get_daily_report(date: Optional[str] = Query(None, description="日期 (YYYY-MM-DD)")):
    """获取每日报告"""
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        report = await task_manager.generate_daily_report()
        
        return DailyReportResponse(
            date=report.get('date', date),
            total_tasks=report.get('total_tasks', 0),
            completed_tasks=report.get('completed_tasks', 0),
            pending_tasks=report.get('pending_tasks', 0),
            in_progress_tasks=report.get('in_progress_tasks', 0),
            average_score=report.get('average_score', 0.0),
            completion_rate=report.get('completion_rate', 0.0)
        )
    except Exception as e:
        logger.error(f"Error getting daily report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/overview")
async def get_stats_overview():
    """获取统计概览"""
    try:
        stats = await bitable.get_daily_task_stats()
        return {
            "total_tasks": stats.get('total_tasks', 0),
            "active_users": stats.get('active_users', 0),
            "completion_rate": stats.get('completion_rate', 0.0),
            "average_score": stats.get('average_score', 0.0),
            "pending_tasks": stats.get('pending_tasks', 0),
            "in_progress_tasks": stats.get('in_progress_tasks', 0),
            "completed_today": stats.get('completed_today', 0)
        }
    except Exception as e:
        logger.error(f"Error getting stats overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 管理API
@router.post("/admin/send-reminders")
async def send_daily_reminders():
    """发送每日提醒"""
    try:
        await task_manager.send_daily_reminders()
        return {"message": "Daily reminders sent successfully"}
    except Exception as e:
        logger.error(f"Error sending daily reminders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/send-daily-report")
async def send_daily_report_to_group():
    """生成每日报告（发送功能待实现）"""
    try:
        report = await task_manager.generate_daily_report()
        
        # 注意：send_daily_report 方法已被移除，如需发送功能请重新实现
        logger.info(f"Daily report generated: {report}")
        
        return {"message": "Daily report generated successfully", "report": report}
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 健康检查API
@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查各个服务的健康状态
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "bitable": "healthy",  # 这里可以添加实际的健康检查
                "feishu": "healthy",
                "llm": "healthy"
            }
        }
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# 配置API
@router.get("/config")
async def get_config():
    """获取系统配置信息（脱敏）"""
    try:
        from app.config import settings
        
        return {
            "app_name": "Feishu Chat-Ops",
            "version": "1.0.0",
            "environment": "production",  # 可以从环境变量读取
            "features": {
                "auto_assignment": True,
                "quality_check": True,
                "daily_reports": True,
                "github_integration": bool(settings.github_webhook_secret)
            },
            "limits": {
                "max_retry_attempts": settings.max_retry_attempts,
                "min_pass_score": settings.min_pass_score,
                "llm_timeout": settings.llm_timeout
            }
        }
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))