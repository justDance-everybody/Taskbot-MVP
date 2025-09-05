"""
GitHub Webhook 单元测试
测试GitHub Actions集成功能
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.router.github_hook import (
    verify_github_signature,
    handle_workflow_completed,
    process_ci_result,
    send_ci_notification,
    extract_task_id_from_commit
)


class TestGitHubWebhookSignature:
    """测试GitHub webhook签名验证"""
    
    def test_verify_signature_success(self):
        """测试签名验证成功"""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        # 计算正确的签名
        import hmac
        import hashlib
        signature = f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"
        
        assert verify_github_signature(payload, signature, secret) is True
    
    def test_verify_signature_failure(self):
        """测试签名验证失败"""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        wrong_signature = "sha256=wrong_signature"
        
        assert verify_github_signature(payload, wrong_signature, secret) is False
    
    def test_verify_signature_invalid_format(self):
        """测试无效签名格式"""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        invalid_signature = "invalid_format"
        
        assert verify_github_signature(payload, invalid_signature, secret) is False


class TestWebhookEndpoint:
    """测试webhook端点"""
    
    @pytest.mark.asyncio
    async def test_webhook_workflow_run_success(self, async_client, sample_github_webhook_payload, github_headers):
        """测试workflow_run事件处理成功"""
        payload = json.dumps(sample_github_webhook_payload)
        
        with patch('app.router.github_hook.handle_workflow_run') as mock_handler:
            response = await async_client.post(
                "/webhook/github/",
                data=payload,
                headers=github_headers
            )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["event"] == "workflow_run"
    
    @pytest.mark.asyncio
    async def test_webhook_invalid_json(self, async_client, github_headers):
        """测试无效JSON载荷"""
        invalid_payload = "invalid json"
        
        response = await async_client.post(
            "/webhook/github/",
            data=invalid_payload,
            headers=github_headers
        )
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_webhook_unknown_event(self, async_client, github_headers):
        """测试未知事件类型"""
        payload = json.dumps({"action": "test"})
        github_headers["X-GitHub-Event"] = "unknown_event"
        
        response = await async_client.post(
            "/webhook/github/",
            data=payload,
            headers=github_headers
        )
        
        assert response.status_code == 200
        assert response.json()["event"] == "unknown_event"


class TestWorkflowHandling:
    """测试工作流处理"""
    
    @pytest.mark.asyncio
    async def test_handle_workflow_completed_success(self, sample_github_webhook_payload):
        """测试成功的工作流完成处理"""
        workflow_run = sample_github_webhook_payload["workflow_run"]
        repository = sample_github_webhook_payload["repository"]
        
        with patch('app.router.github_hook.process_ci_result') as mock_process:
            await handle_workflow_completed(workflow_run, repository, sample_github_webhook_payload, "test-delivery")
            
            mock_process.assert_called_once()
            args, kwargs = mock_process.call_args
            assert args[0] == "TASK001"  # task_id
            assert args[1]["success"] is True  # ci_result
    
    @pytest.mark.asyncio
    async def test_handle_workflow_completed_failure(self, sample_github_webhook_payload):
        """测试失败的工作流完成处理"""
        # 修改为失败状态
        sample_github_webhook_payload["workflow_run"]["conclusion"] = "failure"
        sample_github_webhook_payload["task_metadata"]["ci_passed"] = False
        
        workflow_run = sample_github_webhook_payload["workflow_run"]
        repository = sample_github_webhook_payload["repository"]
        
        with patch('app.router.github_hook.process_ci_result') as mock_process:
            await handle_workflow_completed(workflow_run, repository, sample_github_webhook_payload, "test-delivery")
            
            mock_process.assert_called_once()
            args, kwargs = mock_process.call_args
            assert args[0] == "TASK001"  # task_id
            assert args[1]["success"] is False  # ci_result


class TestCIResultProcessing:
    """测试CI结果处理"""
    
    @pytest.mark.asyncio
    async def test_process_ci_result_success(self, mock_task_manager, sample_task_data):
        """测试成功CI结果处理"""
        task_id = "TASK001"
        ci_result = {
            "status": "success",
            "success": True,
            "workflow_name": "CI Pipeline",
            "html_url": "https://github.com/owner/repo/actions/runs/123",
            "details": {
                "quality_passed": True,
                "tests_passed": True,
                "integration_passed": True,
                "build_passed": True
            }
        }
        
        with patch('app.router.github_hook.task_manager', mock_task_manager), \
             patch('app.router.github_hook.send_ci_notification') as mock_notify:
            
            await process_ci_result(task_id, ci_result)
            
            mock_task_manager.get_task.assert_called_once_with(task_id)
            mock_task_manager.update_task_ci_status.assert_called_once()
            mock_task_manager.complete_task.assert_called_once()
            mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_ci_result_failure(self, mock_task_manager, sample_task_data):
        """测试失败CI结果处理"""
        task_id = "TASK001"
        ci_result = {
            "status": "failure",
            "success": False,
            "workflow_name": "CI Pipeline",
            "html_url": "https://github.com/owner/repo/actions/runs/123",
            "details": {
                "quality_passed": False,
                "tests_passed": True,
                "integration_passed": True,
                "build_passed": True
            }
        }
        
        with patch('app.router.github_hook.task_manager', mock_task_manager), \
             patch('app.router.github_hook.send_ci_notification') as mock_notify:
            
            await process_ci_result(task_id, ci_result)
            
            mock_task_manager.get_task.assert_called_once_with(task_id)
            mock_task_manager.update_task_ci_status.assert_called_once()
            # 失败时不应该完成任务
            mock_task_manager.complete_task.assert_not_called()
            mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_ci_result_task_not_found(self, mock_task_manager):
        """测试任务不存在的情况"""
        task_id = "NONEXISTENT_TASK"
        ci_result = {"status": "success", "success": True}
        
        mock_task_manager.get_task.return_value = None
        
        with patch('app.router.github_hook.task_manager', mock_task_manager):
            await process_ci_result(task_id, ci_result)
            
            mock_task_manager.get_task.assert_called_once_with(task_id)
            # 任务不存在时不应该进行后续操作
            mock_task_manager.update_task_ci_status.assert_not_called()


class TestCINotification:
    """测试CI通知"""
    
    @pytest.mark.asyncio
    async def test_send_ci_notification_success(self, mock_feishu_service, sample_task_data):
        """测试成功CI通知"""
        ci_result = {
            "success": True,
            "html_url": "https://github.com/owner/repo/actions/runs/123"
        }
        
        with patch('app.router.github_hook.feishu_service', mock_feishu_service):
            await send_ci_notification("TASK001", sample_task_data, ci_result, "user123", "chat456")
            
            # 应该发送到群聊
            mock_feishu_service.send_message_to_chat.assert_called_once()
            args, kwargs = mock_feishu_service.send_message_to_chat.call_args
            assert "🎉 CI检查通过" in kwargs["message"]
    
    @pytest.mark.asyncio
    async def test_send_ci_notification_failure(self, mock_feishu_service, sample_task_data):
        """测试失败CI通知"""
        ci_result = {
            "success": False,
            "html_url": "https://github.com/owner/repo/actions/runs/123",
            "details": {
                "quality_passed": False,
                "tests_passed": True,
                "integration_passed": False,
                "build_passed": True
            }
        }
        
        with patch('app.router.github_hook.feishu_service', mock_feishu_service):
            await send_ci_notification("TASK001", sample_task_data, ci_result, "user123", "chat456")
            
            # 应该发送到群聊
            mock_feishu_service.send_message_to_chat.assert_called_once()
            args, kwargs = mock_feishu_service.send_message_to_chat.call_args
            message = kwargs["message"]
            assert "❌ CI检查失败" in message
            assert "代码质量检查" in message
            assert "集成测试" in message
    
    @pytest.mark.asyncio
    async def test_send_ci_notification_private_chat(self, mock_feishu_service, sample_task_data):
        """测试私聊CI通知"""
        ci_result = {
            "success": True,
            "html_url": "https://github.com/owner/repo/actions/runs/123"
        }
        
        # 设置为私聊场景（chat_id与user_id相同）
        with patch('app.router.github_hook.feishu_service', mock_feishu_service):
            await send_ci_notification("TASK001", sample_task_data, ci_result, "user123", "user123")
            
            # 应该发送私聊消息
            mock_feishu_service.send_message.assert_called_once()
            args, kwargs = mock_feishu_service.send_message.call_args
            assert kwargs["user_id"] == "user123"


class TestTaskIdExtraction:
    """测试任务ID提取"""
    
    @pytest.mark.asyncio
    async def test_extract_task_id_from_commit(self):
        """测试从commit提取任务ID"""
        head_sha = "abc123def456"
        repository = {"name": "test-repo", "full_name": "owner/test-repo"}
        
        # 目前实现返回None，这是正确的占位实现
        result = await extract_task_id_from_commit(head_sha, repository)
        assert result is None


class TestHealthCheck:
    """测试健康检查"""
    
    @pytest.mark.asyncio
    async def test_github_webhook_health(self, async_client):
        """测试GitHub webhook健康检查"""
        response = await async_client.get("/webhook/github/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "github-webhook"
        assert "/webhook/github/" in data["endpoints"] 