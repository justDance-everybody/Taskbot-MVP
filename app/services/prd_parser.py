"""PRD parser — converts free-form task descriptions into structured task data.

Pipeline:
1. Send PRD text to the configured LLM with an extraction prompt.
2. Parse the JSON response into ``ParsedPRD``: title / skills / deadline /
   description / estimated_hours / completeness / risks / suggestions.
3. If completeness < threshold (default 70) OR risks list is non-empty,
   ``needs_optimization`` is True so the caller pushes the HR optimization
   card before matching.
4. On LLM timeout or hard failure, return a sentinel with
   ``needs_fallback=True`` so the caller falls back to the existing
   ``/newtask`` interactive form.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm import llm_service

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """你是 PRD 解析助手。把用户给的中文任务描述抽成结构化 JSON。

字段定义:
- title: 简短任务标题(<=20字)
- skills: 技能标签数组,从描述中识别技术栈/工具(如 Python, FastAPI, 多维表格, React)
- deadline: 截止时间,ISO 8601 格式 YYYY-MM-DD;如果原文给"X月X日"按当年解析,若已过当前日期顺延到次年;若完全无,给 null
- description: 任务详细描述(原文要点提炼)
- estimated_hours: [low, high] 小时数估计区间,基于任务复杂度
- completeness: 0-100 整数,衡量描述完整度(标题/技能/时限/描述/可验收点都齐全 = 100)
- risks: 风险点列表,每项一个字符串(描述模糊/时限过紧/缺验收标准等)
- suggestions: 改进建议列表,每项一个字符串(候选人需要补充的信息)

只返回 JSON,不要任何其它文字。
"""


_USER_PROMPT_TMPL = """请解析以下 PRD:

```
{text}
```

返回 JSON 示例:
{{
  "title": "Python 脚本生成日报",
  "skills": ["Python", "多维表格"],
  "deadline": "2026-05-15",
  "description": "需要 Python 脚本,定时从飞书多维表格读数据生成日报",
  "estimated_hours": [4, 8],
  "completeness": 85,
  "risks": [],
  "suggestions": []
}}
"""


@dataclass
class ParsedPRD:
    title: str = ""
    skills: List[str] = field(default_factory=list)
    deadline: Optional[str] = None
    description: str = ""
    estimated_hours: List[float] = field(default_factory=lambda: [0.0, 0.0])
    completeness: int = 0
    risks: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    needs_optimization: bool = False
    needs_fallback: bool = False
    fallback_reason: Optional[str] = None
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PRDParser:
    def __init__(
        self,
        llm: Any = None,
        timeout_seconds: Optional[int] = None,
        completeness_threshold: Optional[int] = None,
    ) -> None:
        self.llm = llm or llm_service
        self.timeout_seconds = timeout_seconds or settings.prd_parse_timeout_seconds
        self.completeness_threshold = (
            completeness_threshold or settings.prd_completeness_threshold
        )

    async def parse(self, text: str) -> ParsedPRD:
        text = (text or "").strip()
        if not text:
            return ParsedPRD(needs_fallback=True, fallback_reason="empty_input")

        try:
            response = await asyncio.wait_for(
                self.llm.call(_USER_PROMPT_TMPL.format(text=text), _SYSTEM_PROMPT),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("PRD parse timed out after %ss; falling back", self.timeout_seconds)
            return ParsedPRD(needs_fallback=True, fallback_reason="llm_timeout")
        except Exception as exc:  # pragma: no cover - generic safety net
            logger.warning("PRD parse failed: %s; falling back", exc)
            return ParsedPRD(needs_fallback=True, fallback_reason=f"llm_error:{type(exc).__name__}")

        parsed = self._parse_response(response, original_text=text)
        parsed.needs_optimization = (
            parsed.completeness < self.completeness_threshold or bool(parsed.risks)
        )
        return parsed

    def _parse_response(self, response: str, *, original_text: str) -> ParsedPRD:
        if not response:
            return ParsedPRD(
                needs_fallback=True,
                fallback_reason="empty_llm_response",
                raw_response=response,
            )

        json_str = _extract_json_block(response)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("PRD response not valid JSON; falling back. Raw: %r", response[:200])
            return ParsedPRD(
                needs_fallback=True,
                fallback_reason="invalid_json",
                raw_response=response,
            )

        skills = data.get("skills") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        estimated = data.get("estimated_hours") or [0, 0]
        if isinstance(estimated, (int, float)):
            estimated = [float(estimated), float(estimated)]
        elif isinstance(estimated, list) and len(estimated) == 1:
            estimated = [float(estimated[0]), float(estimated[0])]
        elif isinstance(estimated, list) and len(estimated) >= 2:
            estimated = [float(estimated[0]), float(estimated[1])]
        else:
            estimated = [0.0, 0.0]

        completeness = data.get("completeness")
        if completeness is None:
            completeness = _heuristic_completeness(data, original_text)
        completeness = max(0, min(100, int(completeness)))

        return ParsedPRD(
            title=str(data.get("title") or "").strip(),
            skills=[str(s).strip() for s in skills if str(s).strip()],
            deadline=_normalize_deadline(data.get("deadline")),
            description=str(data.get("description") or "").strip(),
            estimated_hours=estimated,
            completeness=completeness,
            risks=[str(r).strip() for r in (data.get("risks") or []) if str(r).strip()],
            suggestions=[str(s).strip() for s in (data.get("suggestions") or []) if str(s).strip()],
            raw_response=response,
        )


def _extract_json_block(text: str) -> str:
    """Pull the first JSON object out of an LLM response (handles ```json fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    obj = re.search(r"\{.*\}", text, re.DOTALL)
    return obj.group(0) if obj else text.strip()


def _normalize_deadline(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    s = str(value).strip()
    # Accept YYYY-MM-DD or YYYY/MM/DD; reject obvious garbage.
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if not m:
        return None
    year, month, day = m.groups()
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _heuristic_completeness(data: Dict[str, Any], original_text: str) -> int:
    """Score 0-100 when LLM didn't supply one. Each present field worth ~20 pts."""
    score = 0
    if data.get("title"):
        score += 20
    skills = data.get("skills") or []
    if skills:
        score += 20
    if data.get("deadline"):
        score += 20
    desc = (data.get("description") or "").strip()
    if desc:
        score += 20
    # Bonus for non-trivially long original input — heuristic for "user gave detail".
    if len(original_text) >= 30:
        score += 20
    return score
