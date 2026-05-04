"""Integration tests for AI pre-verification (issue #12 §3, §4)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.acceptance import AcceptanceContract, parse_acceptance_yaml
from app.services.ai_review import (
    LLMIssue,
    StaticIssue,
    decide,
    evaluate_static_rules,
    llm_review,
)


# ----------------------------------------------------------------------
# Acceptance case 1
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_green_ci_high_score_auto_merge():
    """Green CI + LLM score ≥ threshold → decide returns auto_merge."""
    llm = MagicMock()
    llm.call = AsyncMock(return_value=json.dumps({
        "score": 5,
        "issues": [],
        "summary": "Clean fix.",
    }))
    score, issues, _ = await llm_review(
        {"title": "X", "description": "fix bug"}, "diff text", llm=llm,
    )
    assert score == 5
    assert issues == []
    decision = decide(score, [], ci_passed=True)
    assert decision == "auto_merge"


# ----------------------------------------------------------------------
# Acceptance case 2
# ----------------------------------------------------------------------
def test_low_score_routes_to_hr():
    """2 ≤ score < threshold AND CI green → hr_review."""
    assert decide(3, [], ci_passed=True, threshold=4) == "hr_review"
    assert decide(2, [], ci_passed=True, threshold=4) == "hr_review"


def test_red_ci_routes_to_auto_bounce_regardless_of_score():
    """CI red → auto_bounce even if LLM score is high."""
    assert decide(5, [], ci_passed=False) == "auto_bounce"


# ----------------------------------------------------------------------
# Acceptance case 3
# ----------------------------------------------------------------------
def test_acceptance_yaml_parsed_from_issue():
    """Issue body with the documented YAML fence parses into a contract."""
    body = """
Some prose about the task.

Acceptance criteria:

```yaml
acceptance:
  ci_required:
    - test
    - lint
  coverage_min: 80
  custom_commands:
    - "pytest tests/integration/test_xxx.py"
  forbid_files:
    - .env
    - "*.pem"
  max_pr_lines: 2000
```

More prose.
"""
    contract = parse_acceptance_yaml(body)
    assert contract.ci_required == ["test", "lint"]
    assert contract.coverage_min == 80
    assert contract.max_pr_lines == 2000
    assert ".env" in contract.forbid_files
    assert "*.pem" in contract.forbid_files
    assert "pytest tests/integration/test_xxx.py" in contract.custom_commands


def test_acceptance_missing_yaml_returns_default():
    contract = parse_acceptance_yaml("body without any yaml block")
    assert contract.is_default


# ----------------------------------------------------------------------
# Acceptance case 4
# ----------------------------------------------------------------------
def test_max_pr_lines_violation_auto_bounce():
    """PR exceeds max_pr_lines → static issue + auto_bounce."""
    contract = AcceptanceContract(max_pr_lines=2000)
    diff_stats = {"additions": 1500, "deletions": 700}
    static = evaluate_static_rules(diff_stats, contract)
    assert any(s.rule == "max_pr_lines" for s in static)
    decision = decide(score=5, static_issues=static, ci_passed=True)
    assert decision == "auto_bounce"


def test_forbid_files_static_check():
    """Touching a forbidden file → blocking static issue."""
    contract = AcceptanceContract(forbid_files=[".env", "*.pem"])
    diff_stats = {"additions": 10, "deletions": 0,
                  "changed_files": [".env", "src/main.py"]}
    static = evaluate_static_rules(diff_stats, contract)
    assert any(s.rule == "forbid_files" for s in static)


def test_coverage_min_static_check():
    contract = AcceptanceContract(coverage_min=80)
    diff_stats = {"additions": 1, "deletions": 1}
    static = evaluate_static_rules(diff_stats, contract, coverage_pct=72.5)
    assert any(s.rule == "coverage_min" for s in static)


@pytest.mark.asyncio
async def test_llm_review_retries_on_missing_how_to_fix():
    """First response missing how_to_fix → retry; final fallback fills template."""
    llm = MagicMock()
    bad = json.dumps({"score": 3, "issues": [
        {"category": "antipattern", "message": "N+1", "file": "x.py", "line": 5},
    ]})
    good = json.dumps({"score": 3, "issues": [
        {"category": "antipattern", "message": "N+1", "file": "x.py", "line": 5,
         "how_to_fix": "Use select_related()"},
    ]})
    llm.call = AsyncMock(side_effect=[bad, good])
    score, issues, _ = await llm_review({"title": "T", "description": ""}, "diff", llm=llm)
    assert llm.call.await_count == 2
    assert all(i.how_to_fix for i in issues)


@pytest.mark.asyncio
async def test_llm_review_template_fallback_when_retry_also_missing():
    """If retry STILL omits how_to_fix, we stamp a templated value."""
    llm = MagicMock()
    bad = json.dumps({"score": 2, "issues": [
        {"category": "other", "message": "msg", "file": None, "line": None},
    ]})
    llm.call = AsyncMock(return_value=bad)
    _, issues, _ = await llm_review({"title": "T", "description": ""}, "diff", llm=llm)
    assert all(i.how_to_fix for i in issues)
