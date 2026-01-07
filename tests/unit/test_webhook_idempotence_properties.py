"""
Property-based tests for GitHub Webhook Idempotence
Feature: taskbot-completion, Property 9: Webhook Idempotence
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request
from fastapi.testclient import TestClient
import json
import hashlib
import hmac


# Strategy for generating GitHub webhook payloads
def github_webhook_payload_strategy():
    """Generate valid GitHub webhook payloads"""
    return st.fixed_dictionaries({
        'action': st.sampled_from(['completed', 'requested', 'in_progress']),
        'workflow_run': st.fixed_dictionaries({
            'id': st.integers(min_value=1, max_value=999999),
            'name': st.text(min_size=1, max_size=50),
            'head_sha': st.text(min_size=40, max_size=40, alphabet='0123456789abcdef'),
            'conclusion': st.sampled_from(['success', 'failure', 'cancelled', 'skipped']),
            'status': st.sampled_from(['completed', 'in_progress', 'queued']),
            'html_url': st.text(min_size=10, max_size=100),
            'updated_at': st.text(min_size=10, max_size=30)
        }),
        'repository': st.fixed_dictionaries({
            'name': st.text(min_size=1, max_size=50),
            'full_name': st.text(min_size=1, max_size=100),
            'html_url': st.text(min_size=10, max_size=100)
        }),
        'task_metadata': st.fixed_dictionaries({
            'task_id': st.text(min_size=1, max_size=20),
            'ci_passed': st.booleans()
        })
    })


def generate_github_signature(payload: bytes, secret: str) -> str:
    """Generate GitHub webhook signature"""
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    payload=github_webhook_payload_strategy(),
    delivery_id=st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=33, max_codepoint=126)),
    event_type=st.sampled_from(['workflow_run', 'check_run', 'push', 'pull_request'])
)
async def test_webhook_idempotence_property(payload, delivery_id, event_type):
    """
    Property 9: Webhook Idempotence
    
    For any GitHub webhook with the same delivery_id, processing it multiple times
    SHALL have the same effect as processing it once.
    
    Validates: Requirements 7.2
    Feature: taskbot-completion, Property 9: Webhook Idempotence
    """
    from app.router.github_hook import router, clear_delivery_cache
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    
    # Clear the cache before test
    clear_delivery_cache()
    
    # Create a test app
    app = FastAPI()
    app.include_router(router)
    
    # Prepare payload
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate signature
    secret = "test_secret"
    signature = generate_github_signature(payload_bytes, secret)
    
    # Prepare headers
    headers = {
        "X-GitHub-Event": event_type,
        "X-GitHub-Delivery": delivery_id,
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json"
    }
    
    # Mock the settings to include webhook secret
    with patch('app.router.github_hook.settings') as mock_settings:
        mock_settings.GITHUB_WEBHOOK_SECRET = secret
        
        # Mock the handler functions to track calls
        with patch('app.router.github_hook.handle_workflow_run', new_callable=AsyncMock) as mock_handler:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # First request - should be processed
                response1 = await client.post(
                    "/webhook/github/",
                    content=payload_bytes,
                    headers=headers
                )
                
                # Second request with same delivery_id - should be skipped
                response2 = await client.post(
                    "/webhook/github/",
                    content=payload_bytes,
                    headers=headers
                )
                
                # Third request with same delivery_id - should be skipped
                response3 = await client.post(
                    "/webhook/github/",
                    content=payload_bytes,
                    headers=headers
                )
                
                # Property assertion: All responses should be successful
                assert response1.status_code == 200, f"First request failed with status {response1.status_code}"
                assert response2.status_code == 200, f"Second request failed with status {response2.status_code}"
                assert response3.status_code == 200, f"Third request failed with status {response3.status_code}"
                
                # Property assertion: Handler should only be called once (idempotence)
                # The first request processes, subsequent requests are skipped
                if event_type == 'workflow_run':
                    assert mock_handler.call_count <= 1, \
                        f"Handler called {mock_handler.call_count} times, expected at most 1 (idempotence violated)"
                
                # Property assertion: Second and third responses should indicate duplicate
                response2_data = response2.json()
                response3_data = response3.json()
                
                assert response2_data.get('status') == 'ok', "Second request should return ok status"
                assert response3_data.get('status') == 'ok', "Third request should return ok status"
                
                # Check that duplicate deliveries are acknowledged
                if 'message' in response2_data:
                    assert 'duplicate' in response2_data['message'].lower() or 'skipped' in response2_data['message'].lower(), \
                        "Second request should indicate duplicate delivery"


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    payload=github_webhook_payload_strategy(),
    delivery_ids=st.lists(
        st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=33, max_codepoint=126)),
        min_size=2,
        max_size=5,
        unique=True
    ),
    event_type=st.sampled_from(['workflow_run', 'check_run'])
)
async def test_different_delivery_ids_processed_independently(payload, delivery_ids, event_type):
    """
    Property 9 Invariant: Different delivery IDs are processed independently
    
    For any set of webhooks with different delivery_ids, each SHALL be processed
    independently regardless of identical payload content.
    
    Validates: Requirements 7.2
    Feature: taskbot-completion, Property 9: Webhook Idempotence
    """
    from app.router.github_hook import router, clear_delivery_cache
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    
    # Clear the cache before test
    clear_delivery_cache()
    
    # Create a test app
    app = FastAPI()
    app.include_router(router)
    
    # Prepare payload (same for all requests)
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate signature
    secret = "test_secret"
    signature = generate_github_signature(payload_bytes, secret)
    
    # Mock the settings
    with patch('app.router.github_hook.settings') as mock_settings:
        mock_settings.GITHUB_WEBHOOK_SECRET = secret
        
        # Mock the handler functions to track calls
        with patch('app.router.github_hook.handle_workflow_run', new_callable=AsyncMock) as mock_handler:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                responses = []
                
                # Send requests with different delivery IDs
                for delivery_id in delivery_ids:
                    headers = {
                        "X-GitHub-Event": event_type,
                        "X-GitHub-Delivery": delivery_id,
                        "X-Hub-Signature-256": signature,
                        "Content-Type": "application/json"
                    }
                    
                    response = await client.post(
                        "/webhook/github/",
                        content=payload_bytes,
                        headers=headers
                    )
                    responses.append(response)
                
                # Property assertion: All requests should succeed
                for i, response in enumerate(responses):
                    assert response.status_code == 200, \
                        f"Request {i+1} with delivery_id {delivery_ids[i]} failed with status {response.status_code}"
                
                # Property assertion: Each unique delivery_id should be processed
                # (handler called once per unique delivery_id for workflow_run events)
                if event_type == 'workflow_run':
                    expected_calls = len(delivery_ids)
                    assert mock_handler.call_count == expected_calls, \
                        f"Handler called {mock_handler.call_count} times, expected {expected_calls} for {len(delivery_ids)} unique delivery IDs"


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    payload=github_webhook_payload_strategy(),
    delivery_id=st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=33, max_codepoint=126)),
    num_duplicates=st.integers(min_value=2, max_value=10)
)
async def test_webhook_idempotence_with_multiple_duplicates(payload, delivery_id, num_duplicates):
    """
    Property 9 Stress Test: Multiple duplicate deliveries
    
    For any webhook delivery_id, processing it N times (N > 1) SHALL have
    the same effect as processing it once, regardless of N.
    
    Validates: Requirements 7.2
    Feature: taskbot-completion, Property 9: Webhook Idempotence
    """
    from app.router.github_hook import router, clear_delivery_cache
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    
    # Clear the cache before test
    clear_delivery_cache()
    
    # Create a test app
    app = FastAPI()
    app.include_router(router)
    
    # Prepare payload
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate signature
    secret = "test_secret"
    signature = generate_github_signature(payload_bytes, secret)
    
    # Prepare headers
    headers = {
        "X-GitHub-Event": "workflow_run",
        "X-GitHub-Delivery": delivery_id,
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json"
    }
    
    # Mock the settings
    with patch('app.router.github_hook.settings') as mock_settings:
        mock_settings.GITHUB_WEBHOOK_SECRET = secret
        
        # Mock the handler to track calls
        with patch('app.router.github_hook.handle_workflow_run', new_callable=AsyncMock) as mock_handler:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                responses = []
                
                # Send the same request multiple times
                for i in range(num_duplicates):
                    response = await client.post(
                        "/webhook/github/",
                        content=payload_bytes,
                        headers=headers
                    )
                    responses.append(response)
                
                # Property assertion: All responses should be successful
                for i, response in enumerate(responses):
                    assert response.status_code == 200, \
                        f"Request {i+1} failed with status {response.status_code}"
                
                # Property assertion: Handler should only be called once (strong idempotence)
                assert mock_handler.call_count <= 1, \
                    f"Handler called {mock_handler.call_count} times for {num_duplicates} duplicate requests, expected at most 1"
                
                # Property assertion: After first request, all subsequent should indicate duplicate
                for i in range(1, len(responses)):
                    response_data = responses[i].json()
                    assert 'duplicate' in str(response_data).lower() or 'skipped' in str(response_data).lower(), \
                        f"Request {i+1} should indicate duplicate delivery"
