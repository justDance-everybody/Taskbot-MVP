"""Two-stage match unit tests (issue #9 acceptance set).

All Bitable + LLM access is mocked. Verifies:
- prefilter_by_tags filters by skill, scores, sorts, respects limit
- rerank_by_llm parses LLM JSON, attaches recommendation_reason
- two_stage_match: empty prefilter skips LLM
- two_stage_match: simple mode never calls LLM
- two_stage_match: full mode calls LLM and returns top-N
- _norm_skill is case/whitespace insensitive
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, patch

from app.services.match import MatchService, _norm_skill


def _candidate(user_id: str, skills: list, score: float = 80.0, status: str = "available") -> dict:
    return {
        "user_id": user_id,
        "name": f"User-{user_id}",
        "skill_tags": skills,
        "average_score": score,
        "status": status,
    }


@pytest.fixture
def patched_wrapper():
    with patch("app.services.match.bitable_wrapper") as mock_wrapper:
        mock_wrapper.get_all_candidates = AsyncMock(return_value=[])
        yield mock_wrapper


@pytest.mark.asyncio
async def test_prefilter_by_tags_filters_and_scores(patched_wrapper):
    patched_wrapper.get_all_candidates.return_value = [
        _candidate("u1", ["Python", "FastAPI"], 90),
        _candidate("u2", ["Java"], 70),  # no skill overlap → dropped
        _candidate("u3", ["Python"], 60),
        _candidate("u4", ["Python", "FastAPI", "Bitable"], 85),
    ]
    svc = MatchService()
    result = await svc.prefilter_by_tags(["Python", "FastAPI"], limit=10)

    user_ids = [c["user_id"] for c in result]
    assert "u2" not in user_ids
    # u4 matches both required skills (full skill_score) → highest
    assert result[0]["user_id"] == "u4" or result[0]["user_id"] == "u1"
    for c in result:
        assert "prefilter_score" in c
        assert "matched_skills" in c


@pytest.mark.asyncio
async def test_prefilter_respects_limit(patched_wrapper):
    patched_wrapper.get_all_candidates.return_value = [
        _candidate(f"u{i}", ["Python"], 50 + i) for i in range(50)
    ]
    svc = MatchService()
    result = await svc.prefilter_by_tags(["Python"], limit=5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_prefilter_excludes_unavailable(patched_wrapper):
    patched_wrapper.get_all_candidates.return_value = [
        _candidate("u1", ["Python"], status="busy"),
        _candidate("u2", ["Python"], status="available"),
    ]
    svc = MatchService()
    result = await svc.prefilter_by_tags(["Python"], limit=10)
    assert [c["user_id"] for c in result] == ["u2"]


@pytest.mark.asyncio
async def test_rerank_by_llm_attaches_reason():
    svc = MatchService()
    svc.llm = AsyncMock()
    svc.llm.call = AsyncMock(return_value=json.dumps({
        "matches": [
            {"user_id": "u1", "match_score": 95, "recommendation_reason": "强 FastAPI 经验"},
            {"user_id": "u3", "match_score": 80, "recommendation_reason": "Python 熟练"},
        ]
    }))

    cands = [
        _candidate("u1", ["Python", "FastAPI"]),
        _candidate("u3", ["Python"]),
    ]
    result = await svc.rerank_by_llm({"title": "T", "skills": ["Python"]}, cands, top_n=2)
    assert [c["user_id"] for c in result] == ["u1", "u3"]
    assert result[0]["recommendation_reason"] == "强 FastAPI 经验"
    assert result[0]["match_score"] == 95


@pytest.mark.asyncio
async def test_rerank_by_llm_handles_invalid_json_falls_back():
    svc = MatchService()
    svc.llm = AsyncMock()
    svc.llm.call = AsyncMock(return_value="not json")
    cands = [_candidate("u1", ["X"])]
    result = await svc.rerank_by_llm({"title": "T"}, cands, top_n=2)
    # falls back to prefilter order
    assert [c["user_id"] for c in result] == ["u1"]


@pytest.mark.asyncio
async def test_empty_prefilter_skips_llm(patched_wrapper):
    """Acceptance case: empty stage-1 → never calls LLM."""
    patched_wrapper.get_all_candidates.return_value = []  # no candidates at all
    svc = MatchService()
    svc.llm = AsyncMock()
    svc.llm.call = AsyncMock(return_value="should never be called")

    result = await svc.two_stage_match({"title": "T", "skills": ["Python"]}, mode="full")
    assert result == []
    svc.llm.call.assert_not_called()


@pytest.mark.asyncio
async def test_simple_mode_no_llm_call(patched_wrapper):
    """Acceptance case: MATCH_MODE=simple → zero LLM calls."""
    patched_wrapper.get_all_candidates.return_value = [
        _candidate("u1", ["Python"], 90),
        _candidate("u2", ["Python"], 70),
        _candidate("u3", ["Python"], 60),
    ]
    svc = MatchService()
    svc.llm = AsyncMock()
    svc.llm.call = AsyncMock(return_value="should never be called")

    result = await svc.two_stage_match(
        {"title": "T", "skills": ["Python"]}, mode="simple", top_n=2
    )
    assert len(result) == 2
    svc.llm.call.assert_not_called()


@pytest.mark.asyncio
async def test_full_mode_calls_llm_and_returns_top_n(patched_wrapper):
    patched_wrapper.get_all_candidates.return_value = [
        _candidate("u1", ["Python"], 90),
        _candidate("u2", ["Python"], 70),
    ]
    svc = MatchService()
    svc.llm = AsyncMock()
    svc.llm.call = AsyncMock(return_value=json.dumps({
        "matches": [
            {"user_id": "u2", "match_score": 88, "recommendation_reason": "best fit"},
        ]
    }))
    result = await svc.two_stage_match({"title": "T", "skills": ["Python"]}, mode="full", top_n=1)
    assert len(result) == 1
    assert result[0]["user_id"] == "u2"
    assert result[0]["recommendation_reason"] == "best fit"
    svc.llm.call.assert_called_once()


def test_norm_skill_is_case_insensitive():
    assert _norm_skill("Python") == _norm_skill("python") == "python"
    assert _norm_skill("  FastAPI ") == "fastapi"
    assert _norm_skill(123) == "123"


@pytest.mark.asyncio
async def test_two_stage_uses_settings_mode_when_unspecified(patched_wrapper):
    """Defaults pull from settings.match_mode when caller passes mode=None."""
    patched_wrapper.get_all_candidates.return_value = [_candidate("u1", ["Python"])]
    svc = MatchService()
    svc.llm = AsyncMock()
    svc.llm.call = AsyncMock(return_value="never called")

    with patch("app.services.match.settings") as mock_settings:
        mock_settings.match_mode = "simple"
        mock_settings.match_prefilter_limit = 30
        mock_settings.match_top_n = 1
        result = await svc.two_stage_match({"title": "T", "skills": ["Python"]})

    assert len(result) == 1
    svc.llm.call.assert_not_called()
