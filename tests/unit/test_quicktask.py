"""Unit tests for the /quicktask command handler and /test/parse_prd endpoint.

Covers acceptance script lines from issue #9:
- /test/parse_prd happy path returns structured fields
- /test/parse_prd low-quality input flags optimization
- /quicktask routes to legacy /newtask form on LLM timeout
- /quicktask sends optimization summary on low completeness
- /quicktask sends preview on success
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.prd_parser import ParsedPRD


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def _parsed_ok(**overrides):
    base = ParsedPRD(
        title="Python 脚本生成日报",
        skills=["Python", "多维表格"],
        deadline="2026-05-15",
        description="Python 脚本,定时从飞书多维表格读数据生成日报",
        estimated_hours=[4.0, 8.0],
        completeness=88,
        risks=[],
        suggestions=[],
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_parse_prd_endpoint_returns_structured_fields(client):
    parsed = _parsed_ok()
    with patch("app.router.test_endpoints.PRDParser") as ParserCls:
        ParserCls.return_value.parse = AsyncMock(return_value=parsed)
        resp = client.post(
            "/test/parse_prd",
            json={"text": "需要Python脚本,定时从飞书多维表格读数据生成日报,5月15日前交付"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "脚本" in body["title"] or "日报" in body["title"]
    assert "Python" in body["skills"]
    assert any("多维表格" in s or "Bitable" in s for s in body["skills"])
    assert body["deadline"] == "2026-05-15"
    assert body["needs_optimization"] is False
    assert body["needs_fallback"] is False


def test_parse_prd_endpoint_flags_low_quality(client):
    parsed = _parsed_ok(
        title="bot",
        skills=[],
        deadline=None,
        description="做个bot",
        estimated_hours=[0, 0],
        completeness=30,
        risks=["描述过简短"],
        suggestions=["补充技术栈"],
    )
    parsed.needs_optimization = True
    with patch("app.router.test_endpoints.PRDParser") as ParserCls:
        ParserCls.return_value.parse = AsyncMock(return_value=parsed)
        resp = client.post("/test/parse_prd", json={"text": "做个bot"})
    body = resp.json()
    assert body["completeness"] < 70
    assert body["risks"]
    assert body["needs_optimization"] is True


def test_test_match_endpoint_returns_candidates(client):
    fake_results = [
        {"user_id": "u1", "name": "Alice", "match_score": 90, "recommendation_reason": "fit"},
    ]
    with patch("app.router.test_endpoints.MatchService") as MatchCls:
        MatchCls.return_value.two_stage_match = AsyncMock(return_value=fake_results)
        resp = client.post(
            "/test/match",
            json={"title": "T", "description": "d", "skills": ["Python"], "mode": "simple"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"count": 1, "candidates": fake_results}


@pytest.mark.asyncio
async def test_quicktask_falls_back_on_llm_timeout():
    from app.webhooks import handle_quicktask_command

    parsed = ParsedPRD(needs_fallback=True, fallback_reason="llm_timeout")
    with patch("app.services.prd_parser.PRDParser.parse", AsyncMock(return_value=parsed)), \
         patch("app.webhooks.feishu_service") as feishu, \
         patch("app.webhooks.handle_new_task_command", AsyncMock()) as handle_new:
        feishu.send_text_message = AsyncMock()
        await handle_quicktask_command("user1", "/quicktask 一些内容", chat_id="chat1")

    feishu.send_text_message.assert_awaited()
    handle_new.assert_awaited_once()
    args, kwargs = handle_new.call_args
    assert args[0] == "user1"
    assert "一些内容" in args[1]


@pytest.mark.asyncio
async def test_quicktask_pushes_optimization_summary_on_low_completeness():
    from app.webhooks import handle_quicktask_command

    parsed = ParsedPRD(
        title="bot", skills=[], deadline=None, description="做个bot",
        estimated_hours=[0, 0], completeness=30,
        risks=["描述过简短"], suggestions=["补充技术栈"],
    )
    parsed.needs_optimization = True

    with patch("app.services.prd_parser.PRDParser.parse", AsyncMock(return_value=parsed)), \
         patch("app.webhooks.feishu_service") as feishu, \
         patch("app.webhooks.handle_new_task_command", AsyncMock()) as handle_new:
        feishu.send_text_message = AsyncMock()
        await handle_quicktask_command("user1", "/quicktask 做个bot", chat_id="chat1")

    feishu.send_text_message.assert_awaited_once()
    text_arg = feishu.send_text_message.await_args.kwargs["text"]
    assert "完整度" in text_arg or "30" in text_arg
    assert "描述过简短" in text_arg
    assert "补充技术栈" in text_arg
    handle_new.assert_not_called()


@pytest.mark.asyncio
async def test_quicktask_success_replies_with_preview():
    from app.webhooks import handle_quicktask_command

    parsed = _parsed_ok()
    with patch("app.services.prd_parser.PRDParser.parse", AsyncMock(return_value=parsed)), \
         patch("app.webhooks.feishu_service") as feishu:
        feishu.send_text_message = AsyncMock()
        await handle_quicktask_command(
            "user1",
            "/quicktask 需要Python脚本,定时从飞书多维表格读数据生成日报,5月15日前交付",
            chat_id="chat1",
        )

    feishu.send_text_message.assert_awaited_once()
    text_arg = feishu.send_text_message.await_args.kwargs["text"]
    assert "Python" in text_arg
    assert "2026-05-15" in text_arg
    assert "/newtask" in text_arg


@pytest.mark.asyncio
async def test_quicktask_empty_body_prints_usage():
    from app.webhooks import handle_quicktask_command
    with patch("app.webhooks.feishu_service") as feishu:
        feishu.send_text_message = AsyncMock()
        await handle_quicktask_command("u1", "/quicktask", chat_id="c1")
    text_arg = feishu.send_text_message.await_args.kwargs["text"]
    assert "/quicktask" in text_arg
