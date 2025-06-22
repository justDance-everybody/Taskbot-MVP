"""
Integration tests for webhook endpoints
"""

import json
import hmac
import hashlib
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Mock()
    settings.feishu.verify_token = "test_verify_token"
    settings.github.webhook_secret = "test_github_secret"
    settings.app.debug = True
    settings.app.host = "0.0.0.0"
    settings.app.port = 8000
    settings.app.log_level = "INFO"
    return settings


@pytest.fixture
def client(mock_settings):
    """Create test client with mocked settings"""
    with patch('app.main.get_settings', return_value=mock_settings):
        return TestClient(app)


def create_feishu_signature(body: bytes, token: str) -> str:
    """Create Feishu webhook signature"""
    return hmac.new(
        token.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()


def create_github_signature(body: bytes, secret: str) -> str:
    """Create GitHub webhook signature"""
    return "sha256=" + hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "timestamp" in data
        assert "Feishu Task Bot is running" in data["message"]
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "bitable" in data["services"]
        assert "feishu" in data["services"]


class TestFeishuWebhook:
    """Test Feishu webhook endpoint"""
    
    def test_url_verification(self, client):
        """Test URL verification challenge"""
        payload = {
            "type": "url_verification",
            "challenge": "test_challenge_string"
        }
        
        response = client.post(
            "/webhook/feishu",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test_challenge_string"
    
    def test_valid_signature(self, client, mock_settings):
        """Test webhook with valid signature"""
        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": "test_message_id",
                    "chat_id": "test_chat_id",
                    "message_type": "text",
                    "content": '{"text": "Hello"}'
                },
                "sender": {
                    "sender_id": {"user_id": "test_user_id"},
                    "sender_type": "user"
                }
            }
        }
        
        body = json.dumps(payload).encode('utf-8')
        signature = create_feishu_signature(body, mock_settings.feishu.verify_token)
        
        with patch('app.main.process_feishu_event') as mock_process:
            response = client.post(
                "/webhook/feishu",
                content=body,
                headers={"x-lark-signature": signature, "content-type": "application/json"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Event received"
    
    def test_invalid_signature(self, client):
        """Test webhook with invalid signature"""
        payload = {"test": "data"}
        body = json.dumps(payload).encode('utf-8')
        
        response = client.post(
            "/webhook/feishu",
            content=body,
            headers={"x-lark-signature": "invalid_signature", "content-type": "application/json"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid signature"
    
    def test_no_signature(self, client):
        """Test webhook without signature (should still work)"""
        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {"message": {"message_id": "test"}}
        }
        
        with patch('app.main.process_feishu_event') as mock_process:
            response = client.post("/webhook/feishu", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Event received"
    
    def test_invalid_json(self, client):
        """Test webhook with invalid JSON"""
        response = client.post(
            "/webhook/feishu",
            content=b"invalid json",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Invalid JSON payload"
    
    def test_message_event_processing(self, client):
        """Test message event processing"""
        payload = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": "test_message_id",
                    "chat_id": "test_chat_id",
                    "message_type": "text",
                    "content": '{"text": "@bot 新任务 创建API"}'
                },
                "sender": {
                    "sender_id": {"user_id": "test_user_id"},
                    "sender_type": "user"
                }
            }
        }
        
        with patch('app.main.handle_message_event') as mock_handle:
            response = client.post("/webhook/feishu", json=payload)
        
        assert response.status_code == 200
    
    def test_card_action_event_processing(self, client):
        """Test card action event processing"""
        payload = {
            "header": {"event_type": "card.action.trigger"},
            "event": {
                "message_id": "test_message_id",
                "chat_id": "test_chat_id",
                "action": {
                    "value": {"action": "select_candidate", "user_id": "test_user_id"},
                    "tag": "button"
                },
                "user": {"user_id": "test_user_id"}
            }
        }
        
        with patch('app.main.handle_card_action_event') as mock_handle:
            response = client.post("/webhook/feishu", json=payload)
        
        assert response.status_code == 200


class TestGitHubWebhook:
    """Test GitHub webhook endpoint"""
    
    def test_valid_signature(self, client, mock_settings):
        """Test GitHub webhook with valid signature"""
        payload = {
            "action": "completed",
            "workflow_run": {
                "id": 123456,
                "name": "CI",
                "status": "completed",
                "conclusion": "success",
                "html_url": "https://github.com/user/repo/actions/runs/123456",
                "head_branch": "main",
                "head_sha": "abc123def456",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "repository": {
                "name": "test-repo",
                "full_name": "user/test-repo",
                "html_url": "https://github.com/user/test-repo"
            }
        }
        
        body = json.dumps(payload).encode('utf-8')
        signature = create_github_signature(body, mock_settings.github.webhook_secret)
        
        with patch('app.main.process_github_event') as mock_process:
            response = client.post(
                "/webhook/github",
                content=body,
                headers={"x-hub-signature-256": signature, "content-type": "application/json"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Event received"
    
    def test_invalid_signature(self, client):
        """Test GitHub webhook with invalid signature"""
        payload = {"test": "data"}
        body = json.dumps(payload).encode('utf-8')
        
        response = client.post(
            "/webhook/github",
            content=body,
            headers={"x-hub-signature-256": "sha256=invalid_signature", "content-type": "application/json"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Invalid signature"
    
    def test_no_signature(self, client):
        """Test GitHub webhook without signature (should still work)"""
        payload = {
            "action": "completed",
            "workflow_run": {"id": 123456, "status": "completed"}
        }
        
        with patch('app.main.process_github_event') as mock_process:
            response = client.post("/webhook/github", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Event received"
    
    def test_invalid_json(self, client):
        """Test GitHub webhook with invalid JSON"""
        response = client.post(
            "/webhook/github",
            content=b"invalid json",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Invalid JSON payload"


class TestSignatureVerification:
    """Test signature verification functions"""
    
    def test_feishu_signature_verification(self):
        """Test Feishu signature verification"""
        from app.main import verify_feishu_signature
        
        body = b'{"test": "data"}'
        token = "test_token"
        
        # Create valid signature
        valid_signature = hmac.new(
            token.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        with patch('app.main.settings') as mock_settings:
            mock_settings.feishu.verify_token = token
            
            # Test valid signature
            assert verify_feishu_signature(body, valid_signature) is True
            
            # Test invalid signature
            assert verify_feishu_signature(body, "invalid_signature") is False
    
    def test_github_signature_verification(self):
        """Test GitHub signature verification"""
        from app.main import verify_github_signature
        
        body = b'{"test": "data"}'
        secret = "test_secret"
        
        # Create valid signature
        valid_signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        with patch('app.main.settings') as mock_settings:
            mock_settings.github.webhook_secret = secret
            
            # Test valid signature
            assert verify_github_signature(body, valid_signature) is True
            
            # Test invalid signature
            assert verify_github_signature(body, "sha256=invalid_signature") is False


class TestErrorHandling:
    """Test error handling in webhooks"""
    
    def test_feishu_webhook_exception(self, client):
        """Test Feishu webhook exception handling"""
        payload = {"header": {"event_type": "test"}}
        
        with patch('app.main.process_feishu_event', side_effect=Exception("Test error")):
            response = client.post("/webhook/feishu", json=payload)
        
        # Should still return 200 since error is handled in background
        assert response.status_code == 200
    
    def test_github_webhook_exception(self, client):
        """Test GitHub webhook exception handling"""
        payload = {"action": "test"}
        
        with patch('app.main.process_github_event', side_effect=Exception("Test error")):
            response = client.post("/webhook/github", json=payload)
        
        # Should still return 200 since error is handled in background
        assert response.status_code == 200
