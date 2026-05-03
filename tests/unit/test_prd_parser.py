"""Unit tests for app.services.prd_parser.PRDParser.

The LLM is always mocked. We exercise: happy-path JSON parsing, JSON-fence
stripping, timeout fallback, malformed-JSON fallback, low-completeness
optimization signal, and risk-driven optimization signal.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from unittest.mock import AsyncMock

from app.services.prd_parser import (
    PRDParser,
    _extract_json_block,
    _heuristic_completeness,
    _normalize_deadline,
)


def _llm(response: str) -> AsyncMock:
    mock = AsyncMock()
    mock.call = AsyncMock(return_value=response)
    return mock


@pytest.mark.asyncio
async def test_parse_extracts_structured_fields():
    payload = {
        "title": "Python 脚本生成日报",
        "skills": ["Python", "多维表格"],
        "deadline": "2026-05-15",
        "description": "Python 脚本,定时从多维表格读数据,生成日报",
        "estimated_hours": [4, 8],
        "completeness": 88,
        "risks": [],
        "suggestions": [],
    }
    parser = PRDParser(llm=_llm(json.dumps(payload, ensure_ascii=False)))

    result = await parser.parse("需要Python脚本,定时从飞书多维表格读数据生成日报,5月15日前交付")

    assert "脚本" in result.title or "日报" in result.title
    assert "Python" in result.skills
    assert any("多维表格" in s or "Bitable" in s for s in result.skills)
    assert result.deadline == "2026-05-15"
    assert result.estimated_hours == [4.0, 8.0]
    assert result.completeness == 88
    assert result.needs_optimization is False
    assert result.needs_fallback is False


@pytest.mark.asyncio
async def test_parse_strips_markdown_fence():
    payload = {"title": "T", "skills": ["X"], "deadline": "2026-06-01",
               "description": "d", "estimated_hours": [1, 2], "completeness": 80,
               "risks": [], "suggestions": []}
    fenced = "```json\n" + json.dumps(payload) + "\n```"
    parser = PRDParser(llm=_llm(fenced))

    result = await parser.parse("some 30-character-long PRD text payload here ok")

    assert result.title == "T"
    assert result.skills == ["X"]
    assert result.completeness == 80


@pytest.mark.asyncio
async def test_low_completeness_triggers_optimization():
    payload = {
        "title": "bot",
        "skills": [],
        "deadline": None,
        "description": "做个bot",
        "estimated_hours": [0, 0],
        "completeness": 30,
        "risks": ["描述过于简短", "未指定技能要求"],
        "suggestions": ["补充技术栈", "补充截止时间"],
    }
    parser = PRDParser(llm=_llm(json.dumps(payload, ensure_ascii=False)))

    result = await parser.parse("做个bot")

    assert result.completeness < 70
    assert result.risks
    assert result.needs_optimization is True
    assert result.needs_fallback is False


@pytest.mark.asyncio
async def test_risks_alone_triggers_optimization_even_if_complete():
    payload = {
        "title": "Migration",
        "skills": ["SQL"],
        "deadline": "2026-07-01",
        "description": "Migrate 50M-row table to new schema",
        "estimated_hours": [40, 80],
        "completeness": 90,
        "risks": ["High-risk schema change without backfill plan"],
        "suggestions": ["Add explicit rollback steps"],
    }
    parser = PRDParser(llm=_llm(json.dumps(payload, ensure_ascii=False)))
    result = await parser.parse("Migrate 50M-row users table to new schema by 2026-07-01")
    assert result.completeness >= 70
    assert result.needs_optimization is True


@pytest.mark.asyncio
async def test_timeout_falls_back_to_form_flow():
    slow_llm = AsyncMock()

    async def _slow(*_args, **_kwargs):
        await asyncio.sleep(2)
        return "{}"

    slow_llm.call.side_effect = _slow
    parser = PRDParser(llm=slow_llm, timeout_seconds=0.1)

    result = await parser.parse("anything")
    assert result.needs_fallback is True
    assert result.fallback_reason == "llm_timeout"


@pytest.mark.asyncio
async def test_invalid_json_falls_back():
    parser = PRDParser(llm=_llm("not actually json at all"))
    result = await parser.parse("anything substantial enough")
    assert result.needs_fallback is True
    assert result.fallback_reason == "invalid_json"


@pytest.mark.asyncio
async def test_empty_input_falls_back_without_calling_llm():
    llm = _llm("{}")
    parser = PRDParser(llm=llm)
    result = await parser.parse("   ")
    assert result.needs_fallback is True
    assert result.fallback_reason == "empty_input"
    llm.call.assert_not_called()


@pytest.mark.asyncio
async def test_parse_handles_missing_completeness_via_heuristic():
    payload = {
        "title": "T", "skills": ["X"], "deadline": "2026-08-01",
        "description": "Some description", "estimated_hours": [2, 4],
        "risks": [], "suggestions": [],
    }
    parser = PRDParser(llm=_llm(json.dumps(payload)))
    result = await parser.parse("a 30-char-or-longer original PRD text input")
    assert result.completeness == 100  # all 5 buckets satisfied


def test_extract_json_block_with_fence():
    assert _extract_json_block("```json\n{\"a\":1}\n```") == '{"a":1}'


def test_extract_json_block_bare_object():
    assert _extract_json_block("Some prefix {\"a\":1} suffix") == '{"a":1}'


def test_normalize_deadline_accepts_dashes_and_slashes():
    assert _normalize_deadline("2026-5-1") == "2026-05-01"
    assert _normalize_deadline("2026/12/31") == "2026-12-31"


def test_normalize_deadline_rejects_garbage():
    assert _normalize_deadline("next week") is None
    assert _normalize_deadline("") is None
    assert _normalize_deadline(None) is None


def test_heuristic_completeness_scoring():
    full = {"title": "T", "skills": ["X"], "deadline": "2026-01-01", "description": "d"}
    assert _heuristic_completeness(full, "x" * 50) == 100
    assert _heuristic_completeness({}, "x") == 0
    assert _heuristic_completeness({"title": "T"}, "x") == 20
