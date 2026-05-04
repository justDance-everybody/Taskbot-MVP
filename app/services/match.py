import json
import logging
import re
from typing import Any

from app.bitable import BitableClient, bitable_client
from app.config import settings
from app.services.llm import llm_service

logger = logging.getLogger(__name__)


# Module-level wrapper singleton — pytest patches `app.services.match.bitable_wrapper`,
# so reading it inside MatchService.__init__ lets tests inject a mock.
bitable_wrapper = BitableClient()


class MatchService:
    """人员匹配服务"""

    def __init__(self):
        self.llm = llm_service
        self.bitable = bitable_client  # legacy: low-level FeishuBitableClient
        self.wrapper = bitable_wrapper  # new two-stage path uses the wrapper

    # ------------------------------------------------------------------
    # New two-stage matching API (issue #9)
    # ------------------------------------------------------------------

    async def two_stage_match(
        self,
        task_data: dict[str, Any],
        *,
        mode: str | None = None,
        prefilter_limit: int | None = None,
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:
        """Stage 1: prefilter_by_tags (pure Bitable, no LLM, ≤ prefilter_limit).
        Stage 2: rerank_by_llm (Top-N + recommendation_reason).

        - mode="simple": skip stage 2 entirely (zero LLM calls).
        - mode="full" (default): run both stages.
        - Empty stage-1 result → return [] without calling LLM.
        """
        mode = (mode or settings.match_mode).lower()
        prefilter_limit = prefilter_limit or settings.match_prefilter_limit
        top_n = top_n or settings.match_top_n

        skills = task_data.get("skills") or task_data.get("skill_tags") or []
        prefiltered = await self.prefilter_by_tags(skills, limit=prefilter_limit)

        if not prefiltered:
            logger.info("Stage 1 returned 0 candidates; skipping LLM rerank")
            return []

        if mode == "simple":
            logger.info("MATCH_MODE=simple — returning top-%s by stage-1 score", top_n)
            return prefiltered[:top_n]

        return await self.rerank_by_llm(task_data, prefiltered, top_n=top_n)

    async def prefilter_by_tags(
        self,
        required_skills: list[str],
        *,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Bitable-only filter. Score = #matched_skills + small recency bonus.

        Returns up to ``limit`` candidates with status=available, sorted by
        prefilter_score desc.
        """
        try:
            all_candidates = await self.wrapper.get_all_candidates()
        except Exception as exc:
            logger.error("prefilter_by_tags: get_all_candidates failed: %s", exc)
            return []

        required_set = {_norm_skill(s) for s in (required_skills or []) if s}
        scored: list[dict[str, Any]] = []

        for cand in all_candidates:
            if cand.get("status") and cand.get("status") != "available":
                continue
            cand_skills = {_norm_skill(s) for s in (cand.get("skill_tags") or []) if s}

            if required_set:
                matched = required_set & cand_skills
                if not matched:
                    continue
                skill_score = len(matched) / max(1, len(required_set))
            else:
                skill_score = 0.5  # no required skills — everyone qualifies equally

            # Light bonus for higher historical avg_score so ties break toward proven hires.
            avg = float(cand.get("average_score") or 0)
            score = round(skill_score * 100 + min(20.0, avg / 5.0), 2)

            cand_copy = dict(cand)
            cand_copy["prefilter_score"] = score
            cand_copy["matched_skills"] = sorted(required_set & cand_skills) if required_set else []
            scored.append(cand_copy)

        scored.sort(key=lambda c: c["prefilter_score"], reverse=True)
        return scored[:limit]

    async def rerank_by_llm(
        self,
        task_data: dict[str, Any],
        candidates: list[dict[str, Any]],
        *,
        top_n: int = 2,
    ) -> list[dict[str, Any]]:
        """LLM-driven Top-N reranking. Each result includes recommendation_reason."""
        if not candidates:
            return []

        system_prompt = self._build_match_system_prompt()
        user_prompt = self._build_rerank_user_prompt(task_data, candidates, top_n=top_n)

        try:
            response = await self.llm.call(user_prompt, system_prompt)
        except Exception as exc:
            logger.warning("rerank_by_llm: LLM call failed: %s; using prefilter score", exc)
            return candidates[:top_n]

        parsed = self._parse_rerank_response(response, candidates)
        if not parsed:
            logger.info("rerank_by_llm: empty parsed result; falling back to prefilter order")
            return candidates[:top_n]
        return parsed[:top_n]

    def _build_rerank_user_prompt(
        self,
        task_data: dict[str, Any],
        candidates: list[dict[str, Any]],
        *,
        top_n: int,
    ) -> str:
        skills = task_data.get("skills") or task_data.get("skill_tags") or []
        cand_lines = []
        for c in candidates:
            cand_lines.append(
                f"- user_id={c.get('user_id', '')}, name={c.get('name', '')}, "
                f"skills={c.get('skill_tags', [])}, avg_score={c.get('average_score', 0)}, "
                f"prefilter_score={c.get('prefilter_score', 0)}"
            )
        return (
            f"任务标题: {task_data.get('title', '')}\n"
            f"任务描述: {task_data.get('description', '')}\n"
            f"技能要求: {skills}\n"
            f"截止时间: {task_data.get('deadline', '')}\n\n"
            f"候选池({len(candidates)}人):\n" + "\n".join(cand_lines) + "\n\n"
            f"请挑出最合适的 {top_n} 人。返回 JSON:\n"
            "{\"matches\": [{\"user_id\": \"...\", \"match_score\": 0-100, "
            "\"recommendation_reason\": \"...\"}]}\n"
            "只返回 JSON。"
        )

    def _parse_rerank_response(
        self,
        response: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not response:
            return []
        json_str = response
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if fenced:
            json_str = fenced.group(1)
        else:
            obj = re.search(r"\{.*\}", response, re.DOTALL)
            if obj:
                json_str = obj.group(0)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("rerank_by_llm: invalid JSON; raw=%r", response[:200])
            return []

        by_id = {c.get("user_id"): c for c in candidates if c.get("user_id")}
        result: list[dict[str, Any]] = []
        for m in data.get("matches", []):
            uid = m.get("user_id")
            if uid not in by_id:
                continue
            merged = dict(by_id[uid])
            merged["match_score"] = int(m.get("match_score", 0))
            merged["recommendation_reason"] = str(m.get("recommendation_reason", "")).strip()
            result.append(merged)
        return result
    
    async def find_top_candidates(self, task_data: dict[str, Any], limit: int = 2) -> list[dict[str, Any]]:
        """为任务找到Top-N候选人（默认Top-2）"""
        try:
            # 获取所有可用候选人，限制候选人池最多15人
            skill_requirements = task_data.get("skill_tags", [])
            candidates = await self.bitable.get_available_candidates(
                skill_requirements=skill_requirements,
                limit=15  # PRD要求：候选人池最多15人
            )
            
            if not candidates:
                logger.warning("没有找到可用的候选人")
                return []
            
            # 使用LLM进行智能匹配
            matched_candidates = await self._llm_match_candidates(task_data, candidates)
            
            # 按匹配分数排序并返回Top-N
            sorted_candidates = sorted(matched_candidates, key=lambda x: x.get("match_score", 0), reverse=True)
            return sorted_candidates[:limit]
            
        except Exception as e:
            logger.error(f"匹配候选人时出错: {str(e)}")
            return []
    
    async def _llm_match_candidates(self, task_data: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """使用LLM进行候选人匹配"""
        try:
            # 构建匹配提示词
            system_prompt = self._build_match_system_prompt()
            user_prompt = self._build_match_user_prompt(task_data, candidates)
            
            # 调用LLM
            response = await self.llm.call(user_prompt, system_prompt)
            
            # 解析LLM响应
            match_results = self._parse_match_response(response, candidates)
            
            return match_results
            
        except Exception as e:
            logger.error(f"LLM匹配时出错: {str(e)}")
            # 降级到基础匹配算法
            return self._basic_match_candidates(task_data, candidates)
    
    def _build_match_system_prompt(self) -> str:
        """构建匹配系统提示词"""
        return """
你是智能人才匹配助手，负责为任务匹配最合适的候选人。

匹配原则：
1. 技能匹配度：候选人的技能标签与任务需求的匹配程度
2. 可用性：候选人的可用工时是否满足任务需求
3. 历史表现：候选人的绩效评分和完成任务的历史记录
4. 工作负载：候选人当前的工作负载情况
5. 紧急程度：任务的紧急程度与候选人的响应能力

请为每个候选人计算匹配分数（0-100），并提供匹配理由。
"""
    
    def _build_match_user_prompt(self, task_data: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
        """构建匹配用户提示词"""
        task_info = f"""
任务信息：
- 标题：{task_data.get('title', '')}
- 描述：{task_data.get('description', '')}
- 技能要求：{', '.join(task_data.get('skill_tags', []))}
- 截止时间：{task_data.get('deadline', '')}
- 紧急程度：{task_data.get('urgency', 'normal')}
"""
        
        candidates_info = "候选人列表：\n"
        for i, candidate in enumerate(candidates, 1):
            candidates_info += f"""
{i}. 候选人ID: {candidate.get('user_id', '')}
   姓名: {candidate.get('name', '')}
   技能标签: {', '.join(candidate.get('skill_tags', []))}
   职级: {candidate.get('job_level', '')}
   经验年数: {candidate.get('experience', 0)}
   总任务数: {candidate.get('total_tasks', 0)}
   平均评分: {candidate.get('average_score', 0)}
"""
        
        return f"""
{task_info}

{candidates_info}

请返回JSON格式的匹配结果，包含每个候选人的user_id、match_score(0-100)和match_reason：
{{
  "matches": [
    {{
      "user_id": "候选人ID",
      "match_score": 85,
      "match_reason": "匹配理由"
    }}
  ]
}}
"""
    
    def _parse_match_response(self, response: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """解析LLM匹配响应"""
        try:
            # 尝试解析JSON响应
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            match_data = json.loads(json_str)
            matches = match_data.get("matches", [])
            
            # 将匹配结果与候选人信息合并
            result = []
            for match in matches:
                user_id = match.get("user_id")
                candidate = next((c for c in candidates if c.get("user_id") == user_id), None)
                if candidate:
                    candidate_copy = candidate.copy()
                    candidate_copy["match_score"] = match.get("match_score", 0)
                    candidate_copy["match_reason"] = match.get("match_reason", "")
                    result.append(candidate_copy)
            
            return result
            
        except Exception as e:
            logger.error(f"解析LLM匹配响应时出错: {str(e)}")
            # 降级到基础匹配
            return self._basic_match_candidates({}, candidates)
    
    def _basic_match_candidates(self, task_data: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """基础匹配算法（降级方案）"""
        try:
            skill_requirements = set(task_data.get("skill_tags", []))
            
            for candidate in candidates:
                candidate_skills = set(candidate.get("skill_tags", []))
                
                # 计算技能匹配度
                if skill_requirements:
                    skill_match = len(skill_requirements & candidate_skills) / len(skill_requirements)
                else:
                    skill_match = 1.0
                
                # 计算平均评分分数 (0-100 -> 0-1)
                avg_score = candidate.get("average_score", 0) / 100.0
                
                # 计算经验分数 (年数转换为评分)
                experience_years = candidate.get("experience", 0)
                experience_score = min(experience_years / 5.0, 1.0)  # 5年经验为满分
                
                # 综合评分
                match_score = int((skill_match * 0.4 + avg_score * 0.4 + experience_score * 0.2) * 100)
                
                candidate["match_score"] = match_score
                candidate["match_reason"] = f"技能匹配度: {skill_match:.1%}, 平均评分: {avg_score:.1%}, 经验: {experience_score:.1%}"
            
            return candidates
            
        except Exception as e:
            logger.error(f"基础匹配算法出错: {str(e)}")
            return candidates
    
    async def calculate_match_score(self, task_data: dict[str, Any], candidate: dict[str, Any]) -> tuple[int, str]:
        """计算单个候选人的匹配分数"""
        try:
            skill_requirements = set(task_data.get("skill_tags", []))
            candidate_skills = set(candidate.get("skill_tags", []))
            
            # 技能匹配度 (40%)
            if skill_requirements:
                skill_match = len(skill_requirements & candidate_skills) / len(skill_requirements)
            else:
                skill_match = 1.0
            
            # 平均评分 (40%)
            avg_score = candidate.get("average_score", 0) / 100.0
            
            # 经验匹配度 (20%)
            experience_years = candidate.get("experience", 0)
            experience_score = min(experience_years / 5.0, 1.0)  # 5年经验为满分
            
            # 综合评分
            total_score = int((skill_match * 0.4 + avg_score * 0.4 + experience_score * 0.2) * 100)
            
            # 生成匹配理由
            reason = f"技能匹配: {skill_match:.1%}, 平均评分: {avg_score:.1%}, 经验: {experience_score:.1%}"
            
            return total_score, reason
            
        except Exception as e:
            logger.error(f"计算匹配分数时出错: {str(e)}")
            return 50, "计算出错，使用默认分数"

def _norm_skill(skill: Any) -> str:
    """Case-insensitive skill normalization for set operations."""
    return str(skill).strip().lower()


# 创建全局实例
match_service = MatchService()