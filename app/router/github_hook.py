"""
GitHub Webhook 路由处理
处理来自GitHub Actions的CI结果通知
"""

import json
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel

from app.services.task_manager import task_manager
from app.services.feishu import feishu_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook/github", tags=["GitHub Webhook"])


class GitHubWebhookPayload(BaseModel):
    """GitHub Webhook 载荷模型"""
    action: str
    workflow_run: Optional[Dict[str, Any]] = None
    check_run: Optional[Dict[str, Any]] = None
    repository: Dict[str, str]
    task_metadata: Optional[Dict[str, Any]] = None


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """验证GitHub webhook签名"""
    if not signature.startswith('sha256='):
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


@router.post("/")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
):
    """处理GitHub webhook事件"""
    
    try:
        # 获取原始载荷
        payload_bytes = await request.body()
        
        # 验证签名（如果配置了密钥）
        webhook_secret = getattr(settings, 'GITHUB_WEBHOOK_SECRET', None)
        if webhook_secret and x_hub_signature_256:
            if not verify_github_signature(payload_bytes, x_hub_signature_256, webhook_secret):
                logger.warning(f"GitHub webhook签名验证失败 - delivery: {x_github_delivery}")
                raise HTTPException(status_code=401, detail="Signature verification failed")
        
        # 解析JSON载荷
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"无法解析GitHub webhook载荷: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        logger.info(f"收到GitHub webhook事件: {x_github_event} - delivery: {x_github_delivery}")
        logger.debug(f"载荷: {payload}")
        
        # 处理不同类型的事件
        if x_github_event == "workflow_run":
            background_tasks.add_task(handle_workflow_run, payload, x_github_delivery)
        elif x_github_event == "check_run":
            background_tasks.add_task(handle_check_run, payload, x_github_delivery)
        elif x_github_event == "push":
            background_tasks.add_task(handle_push, payload, x_github_delivery)
        elif x_github_event == "pull_request":
            background_tasks.add_task(handle_pull_request, payload, x_github_delivery)
        else:
            logger.info(f"忽略GitHub事件类型: {x_github_event}")
        
        return {"status": "ok", "event": x_github_event, "delivery": x_github_delivery}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理GitHub webhook时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_workflow_run(payload: Dict[str, Any], delivery_id: str):
    """处理workflow_run事件"""
    try:
        action = payload.get('action')
        workflow_run = payload.get('workflow_run', {})
        repository = payload.get('repository', {})
        
        logger.info(f"处理workflow_run事件 - action: {action}, workflow: {workflow_run.get('name')}")
        
        if action == "completed":
            await handle_workflow_completed(workflow_run, repository, payload, delivery_id)
        elif action == "requested":
            await handle_workflow_requested(workflow_run, repository, delivery_id)
            
    except Exception as e:
        logger.error(f"处理workflow_run事件失败: {str(e)}")


async def handle_workflow_completed(workflow_run: Dict[str, Any], repository: Dict[str, Any], payload: Dict[str, Any], delivery_id: str):
    """处理工作流完成事件"""
    try:
        conclusion = workflow_run.get('conclusion')  # success, failure, cancelled, etc.
        status = workflow_run.get('status')  # completed, in_progress, etc.
        head_sha = workflow_run.get('head_sha')
        html_url = workflow_run.get('html_url')
        workflow_name = workflow_run.get('name')
        
        # 提取任务元数据（如果有）
        task_metadata = payload.get('task_metadata', {})
        task_id = task_metadata.get('task_id')
        
        logger.info(f"工作流完成 - 结论: {conclusion}, 任务ID: {task_id}")
        
        # 如果没有任务ID，尝试从commit消息中提取
        if not task_id:
            task_id = await extract_task_id_from_commit(head_sha, repository)
        
        if task_id:
            # 更新任务的CI状态
            ci_result = {
                'status': conclusion,
                'success': conclusion == 'success',
                'workflow_name': workflow_name,
                'html_url': html_url,
                'head_sha': head_sha,
                'delivery_id': delivery_id,
                'completed_at': workflow_run.get('updated_at'),
                'details': {
                    'quality_passed': task_metadata.get('quality_passed', False),
                    'tests_passed': task_metadata.get('tests_passed', False),
                    'integration_passed': task_metadata.get('integration_passed', False),
                    'build_passed': task_metadata.get('build_passed', False),
                    'coverage_url': task_metadata.get('coverage_url'),
                    'branch': task_metadata.get('branch'),
                    'pr_url': task_metadata.get('pr_url')
                }
            }
            
            # 调用任务管理器处理CI结果
            await process_ci_result(task_id, ci_result)
        else:
            logger.info(f"未找到关联的任务ID，跳过CI结果处理")
            
    except Exception as e:
        logger.error(f"处理工作流完成事件失败: {str(e)}")


async def handle_workflow_requested(workflow_run: Dict[str, Any], repository: Dict[str, Any], delivery_id: str):
    """处理工作流请求事件"""
    try:
        head_sha = workflow_run.get('head_sha')
        workflow_name = workflow_run.get('name')
        html_url = workflow_run.get('html_url')
        
        # 尝试提取任务ID
        task_id = await extract_task_id_from_commit(head_sha, repository)
        
        if task_id:
            logger.info(f"CI开始运行 - 任务ID: {task_id}, 工作流: {workflow_name}")
            
            # 通知任务系统CI开始
            await notify_ci_started(task_id, {
                'workflow_name': workflow_name,
                'html_url': html_url,
                'head_sha': head_sha,
                'delivery_id': delivery_id
            })
            
    except Exception as e:
        logger.error(f"处理工作流请求事件失败: {str(e)}")


async def handle_check_run(payload: Dict[str, Any], delivery_id: str):
    """处理check_run事件"""
    try:
        action = payload.get('action')
        check_run = payload.get('check_run', {})
        
        if action == "completed":
            conclusion = check_run.get('conclusion')
            name = check_run.get('name')
            html_url = check_run.get('html_url')
            head_sha = check_run.get('head_sha')
            
            logger.info(f"检查运行完成 - 名称: {name}, 结论: {conclusion}")
            
            # 这里可以添加更细粒度的CI检查处理逻辑
            
    except Exception as e:
        logger.error(f"处理check_run事件失败: {str(e)}")


async def handle_push(payload: Dict[str, Any], delivery_id: str):
    """处理push事件"""
    try:
        commits = payload.get('commits', [])
        ref = payload.get('ref')
        repository = payload.get('repository', {})
        
        # 如果是主分支的推送，可能触发CI
        if ref == 'refs/heads/main' or ref == 'refs/heads/master':
            for commit in commits:
                commit_message = commit.get('message', '')
                if 'TASK' in commit_message.upper():
                    logger.info(f"检测到任务相关的推送: {commit_message[:100]}")
                    
    except Exception as e:
        logger.error(f"处理push事件失败: {str(e)}")


async def handle_pull_request(payload: Dict[str, Any], delivery_id: str):
    """处理pull_request事件"""
    try:
        action = payload.get('action')
        pull_request = payload.get('pull_request', {})
        
        if action in ['opened', 'synchronize', 'closed']:
            title = pull_request.get('title', '')
            if 'TASK' in title.upper():
                logger.info(f"检测到任务相关的PR: {action} - {title}")
                
    except Exception as e:
        logger.error(f"处理pull_request事件失败: {str(e)}")


async def extract_task_id_from_commit(head_sha: str, repository: Dict[str, Any]) -> Optional[str]:
    """从commit消息中提取任务ID"""
    try:
        # 这里需要调用GitHub API获取commit信息
        # 由于没有GitHub API客户端，暂时返回None
        # 实际实现需要根据head_sha获取commit详情
        return None
        
    except Exception as e:
        logger.error(f"提取任务ID失败: {str(e)}")
        return None


async def process_ci_result(task_id: str, ci_result: Dict[str, Any]):
    """处理CI结果"""
    try:
        logger.info(f"处理任务 {task_id} 的CI结果: {ci_result['status']}")
        
        # 获取任务信息
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            logger.warning(f"任务 {task_id} 不存在")
            return
        
        assignee_id = task_data.get('assignee_id')
        chat_id = task_data.get('chat_id')
        
        # 更新任务的CI状态
        await task_manager.update_task_ci_status(task_id, ci_result)
        
        # 发送通知
        await send_ci_notification(task_id, task_data, ci_result, assignee_id, chat_id)
        
        # 如果CI通过且任务类型是代码任务，自动完成任务
        if ci_result['success'] and task_data.get('task_type') == 'code':
            await task_manager.complete_task(task_id, {
                'completion_method': 'auto_ci',
                'ci_details': ci_result
            })
            
            logger.info(f"任务 {task_id} 通过CI自动完成")
            
    except Exception as e:
        logger.error(f"处理CI结果失败: {str(e)}")


async def send_ci_notification(task_id: str, task_data: Dict[str, Any], ci_result: Dict[str, Any], assignee_id: str, chat_id: Optional[str]):
    """发送CI通知"""
    try:
        task_title = task_data.get('title', 'Unknown')
        success = ci_result['success']
        html_url = ci_result.get('html_url', '')
        
        if success:
            message = f"""🎉 CI检查通过！

📋 任务：{task_title}
✅ 状态：所有检查通过
🔗 详情：{html_url}

任务已自动完成！"""
        else:
            details = ci_result.get('details', {})
            failed_checks = []
            
            if not details.get('quality_passed'):
                failed_checks.append("代码质量检查")
            if not details.get('tests_passed'):
                failed_checks.append("单元测试")
            if not details.get('integration_passed'):
                failed_checks.append("集成测试")
            if not details.get('build_passed'):
                failed_checks.append("构建测试")
                
            message = f"""❌ CI检查失败

📋 任务：{task_title}
❌ 状态：检查未通过
🔗 详情：{html_url}

失败的检查项：
""" + "\n".join([f"• {check}" for check in failed_checks]) + """

请修复问题后重新提交。"""

        # 发送通知
        if chat_id and chat_id != assignee_id:
            # 群聊中发送
            await feishu_service.send_message_to_chat(chat_id=chat_id, message=message)
        else:
            # 私聊发送
            await feishu_service.send_message(user_id=assignee_id, message=message)
            
    except Exception as e:
        logger.error(f"发送CI通知失败: {str(e)}")


async def notify_ci_started(task_id: str, ci_info: Dict[str, Any]):
    """通知CI开始运行"""
    try:
        task_data = await task_manager.get_task(task_id)
        if not task_data:
            return
            
        assignee_id = task_data.get('assignee_id')
        chat_id = task_data.get('chat_id')
        task_title = task_data.get('title', 'Unknown')
        
        message = f"""🔄 CI检查开始

📋 任务：{task_title}
🤖 状态：正在运行自动化检查
🔗 进度：{ci_info.get('html_url', '')}

预计需要几分钟完成，请耐心等待..."""

        # 发送通知
        if chat_id and chat_id != assignee_id:
            await feishu_service.send_message_to_chat(chat_id=chat_id, message=message)
        else:
            await feishu_service.send_message(user_id=assignee_id, message=message)
            
    except Exception as e:
        logger.error(f"发送CI开始通知失败: {str(e)}")


# 健康检查端点
@router.get("/health")
async def github_webhook_health():
    """GitHub webhook健康检查"""
    return {
        "status": "ok",
        "service": "github-webhook",
        "endpoints": [
            "/webhook/github/"
        ]
    } 