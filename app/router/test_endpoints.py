"""Diagnostic endpoints under /test/* — exposed for the issue #9 acceptance
script. These exist to let operators (or the CI harness) exercise individual
services without booting the full webhook flow.

Not for production use; gated behind ENVIRONMENT != "production" by the
caller if needed. The endpoints don't hit Feishu or commit Bitable changes,
they just call the underlying service and return the structured result.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.match import MatchService
from app.services.prd_parser import PRDParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["test"])


class ParsePRDRequest(BaseModel):
    text: str = Field(..., description="原始 PRD 描述")


class TwoStageMatchRequest(BaseModel):
    title: str = ""
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    deadline: str | None = None
    mode: str | None = None  # simple | full | None(=use settings default)
    top_n: int | None = None


@router.post("/parse_prd")
async def parse_prd(payload: ParsePRDRequest) -> dict[str, Any]:
    """Parse a free-form PRD description into structured task fields.

    Returns the full ``ParsedPRD`` dict including completeness, risks,
    suggestions, needs_optimization, and needs_fallback flags. Caller
    chooses what to do with the signals.
    """
    parsed = await PRDParser().parse(payload.text)
    return parsed.to_dict()


@router.post("/match")
async def two_stage_match(payload: TwoStageMatchRequest) -> dict[str, Any]:
    """Run the two-stage matcher and return the Top-N candidates.

    The mode parameter mirrors the MATCH_MODE env var: 'simple' skips the
    LLM rerank entirely, 'full' runs both stages.
    """
    task_data = payload.model_dump(exclude={"mode", "top_n"}, exclude_none=False)
    candidates = await MatchService().two_stage_match(
        task_data, mode=payload.mode, top_n=payload.top_n
    )
    return {"count": len(candidates), "candidates": candidates}
