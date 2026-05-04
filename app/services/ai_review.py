"""AI pre-verification — issue #12 §3.

When a candidate sends ``/done <PR URL>`` the GitHub Actions workflow
``acceptance.yaml`` runs the ci_required jobs. The check_run webhook
event lands in :func:`handle_check_run`; we then:

1. Pull CI conclusion + PR diff stats.
2. Apply the static rules (max_pr_lines, forbid_files, coverage_min).
3. Ask the LLM to score the PR 1-5 against the issue description.
4. Route per AUTO_VERIFY_THRESHOLD:
   - score >= threshold AND CI green → auto merge + COMPLETED
   - 2 <= score < threshold      → send to HR for manual decision
   - score <= 1 OR CI red        → auto bounce with feedback card

Step 4's bounce hands off to :mod:`app.services.revision`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.config import settings
from app.services.acceptance import AcceptanceContract

logger = logging.getLogger(__name__)


@dataclass
class StaticIssue:
    rule: str           # max_pr_lines / forbid_files / coverage_min / ci_required
    message: str
    severity: str = "blocking"  # blocking | warning


@dataclass
class LLMIssue:
    category: str       # responds_to_issue / antipattern / commit_quality / other
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    how_to_fix: str = ""  # required field — must always be present
    severity: str = "blocking"


@dataclass
class ReviewResult:
    score: int                                 # 1-5
    decision: str                              # auto_merge | hr_review | auto_bounce
    static_issues: list[StaticIssue] = field(default_factory=list)
    llm_issues: list[LLMIssue] = field(default_factory=list)
    ci_passed: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_static_rules(
    diff_stats: dict[str, Any],
    contract: AcceptanceContract,
    *,
    ci_results: Optional[dict[str, str]] = None,
    coverage_pct: Optional[float] = None,
) -> list[StaticIssue]:
    issues: list[StaticIssue] = []

    # max_pr_lines
    if contract.max_pr_lines:
        total = int(diff_stats.get("additions", 0)) + int(diff_stats.get("deletions", 0))
        if total > contract.max_pr_lines:
            issues.append(StaticIssue(
                rule="max_pr_lines",
                message=f"PR {total} 行 > max_pr_lines={contract.max_pr_lines},请拆分。",
            ))

    # forbid_files
    changed_files = diff_stats.get("changed_files") or []
    for pattern in contract.forbid_files:
        for f in changed_files:
            if _glob_match(pattern, f):
                issues.append(StaticIssue(
                    rule="forbid_files",
                    message=f"禁止修改 `{f}` (匹配 {pattern})",
                ))

    # coverage_min
    if contract.coverage_min and coverage_pct is not None and coverage_pct < contract.coverage_min:
        issues.append(StaticIssue(
            rule="coverage_min",
            message=f"覆盖率 {coverage_pct:.1f}% < {contract.coverage_min}%",
        ))

    # ci_required missing/failed
    if contract.ci_required and ci_results is not None:
        for required in contract.ci_required:
            status = ci_results.get(required)
            if status != "success":
                issues.append(StaticIssue(
                    rule="ci_required",
                    message=f"CI job `{required}` 状态: {status or 'missing'}",
                ))

    return issues


def _glob_match(pattern: str, path: str) -> bool:
    """Tiny glob — supports `*` (filename only) and exact path match."""
    import fnmatch
    return fnmatch.fnmatch(path, pattern) or path == pattern


_LLM_REVIEW_SYSTEM = """你是代码 PR 审查助手,根据任务 issue 描述判断 PR 是否真的解决了问题。
评分标准(1-5,5 最好):
- 5: 完美解决 + 测试到位 + 无反模式
- 4: 解决了主要问题,小瑕疵
- 3: 大致解决但有疑虑
- 2: 走捷径或绕过关键点
- 1: 没解决,甚至更糟

每个 issue 必须包含 `how_to_fix` 字段(具体修法),缺失则视为无效。

返回 JSON:
{
  "score": 4,
  "issues": [
    {"category": "antipattern", "message": "...", "file": "x.py", "line": 12,
     "how_to_fix": "用 select_related 替代 N+1", "severity": "blocking"}
  ],
  "summary": "简评一句"
}
只返回 JSON。
"""


async def llm_review(
    task_data: dict[str, Any],
    diff_text: str,
    *,
    llm: Any = None,
    timeout: int = 30,
) -> tuple[int, list[LLMIssue], str]:
    """Score 1-5 + structured issues. Retries once if how_to_fix missing."""
    if llm is None:
        from app.services.llm import llm_service
        llm = llm_service

    prompt = _build_llm_prompt(task_data, diff_text)
    try:
        raw = await asyncio.wait_for(llm.call(prompt, _LLM_REVIEW_SYSTEM), timeout=timeout)
    except Exception as exc:
        logger.warning("llm_review: call failed: %s; defaulting to score=3", exc)
        return 3, [], "LLM 不可用,降级人工审"

    parsed = _parse_review_json(raw)
    if parsed is None:
        return 3, [], "LLM 响应解析失败,降级人工审"

    score = int(parsed.get("score", 3))
    issues = [_to_llm_issue(i) for i in parsed.get("issues", [])]
    if any(not i.how_to_fix for i in issues):
        # Retry once: ask LLM to fix missing how_to_fix
        try:
            raw2 = await asyncio.wait_for(
                llm.call(prompt + "\n\n注意:每条 issue 必须有 how_to_fix 字段。",
                         _LLM_REVIEW_SYSTEM),
                timeout=timeout,
            )
            parsed2 = _parse_review_json(raw2)
            if parsed2 is not None:
                issues2 = [_to_llm_issue(i) for i in parsed2.get("issues", [])]
                if all(i.how_to_fix for i in issues2):
                    issues = issues2
        except Exception:
            pass

    # Final degradation: stamp a templated how_to_fix on any still-missing
    for issue in issues:
        if not issue.how_to_fix:
            issue.how_to_fix = "(LLM 未给具体修法,请人工评审后补充)"

    return max(1, min(5, score)), issues, str(parsed.get("summary", ""))


def _build_llm_prompt(task: dict[str, Any], diff: str) -> str:
    return (
        f"任务标题: {task.get('title', '')}\n"
        f"任务描述: {task.get('description', '')}\n\n"
        f"PR diff:\n```diff\n{diff[:8000]}\n```\n"
    )


def _parse_review_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    payload = fenced.group(1) if fenced else None
    if payload is None:
        obj = re.search(r"\{.*\}", raw, re.DOTALL)
        payload = obj.group(0) if obj else None
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _to_llm_issue(d: dict[str, Any]) -> LLMIssue:
    return LLMIssue(
        category=str(d.get("category", "other")),
        message=str(d.get("message", "")).strip(),
        file=d.get("file"),
        line=d.get("line"),
        how_to_fix=str(d.get("how_to_fix", "")).strip(),
        severity=str(d.get("severity", "blocking")),
    )


def decide(
    score: int,
    static_issues: list[StaticIssue],
    ci_passed: bool,
    threshold: Optional[int] = None,
) -> str:
    """Return one of: auto_merge | hr_review | auto_bounce."""
    threshold = threshold or settings.auto_verify_threshold
    blocking_static = [s for s in static_issues if s.severity == "blocking"]
    if not ci_passed or blocking_static or score <= 1:
        return "auto_bounce"
    if score >= threshold:
        return "auto_merge"
    return "hr_review"
