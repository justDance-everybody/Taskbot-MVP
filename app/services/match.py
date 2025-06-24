"""
Personnel matching service
Implements Top-3 candidate matching algorithm based on skills and availability
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .llm import get_llm_service
from ..bitable import get_bitable_client

logger = logging.getLogger(__name__)


@dataclass
class MatchScore:
    """Match score breakdown"""
    skill_score: float
    availability_score: float
    performance_score: float
    recency_score: float
    total_score: float
    reasons: List[str]


class MatchingService:
    """Service for matching candidates to tasks"""
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.bitable_client = get_bitable_client()

        # 候选人列表缓存
        self._candidates_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5分钟缓存
    
    def calculate_skill_match(self, required_skills: List[str], 
                             candidate_skills: List[str]) -> Tuple[float, List[str]]:
        """Calculate skill matching score"""
        if not required_skills:
            return 100.0, ["无特定技能要求"]
        
        if not candidate_skills:
            return 0.0, ["候选人未填写技能信息"]
        
        # Convert to lowercase for comparison
        required_lower = [skill.lower() for skill in required_skills]
        candidate_lower = [skill.lower() for skill in candidate_skills]
        
        # Calculate exact matches
        exact_matches = set(required_lower) & set(candidate_lower)
        exact_score = len(exact_matches) / len(required_lower) * 100
        
        # Calculate partial matches (contains relationship)
        partial_matches = set()
        for req_skill in required_lower:
            for cand_skill in candidate_lower:
                if req_skill in cand_skill or cand_skill in req_skill:
                    partial_matches.add(req_skill)
        
        partial_score = len(partial_matches) / len(required_lower) * 50
        
        # Final skill score (prioritize exact matches)
        skill_score = min(100.0, exact_score + partial_score)
        
        reasons = []
        if exact_matches:
            reasons.append(f"完全匹配技能: {', '.join(exact_matches)}")
        if partial_matches - exact_matches:
            reasons.append(f"部分匹配技能: {', '.join(partial_matches - exact_matches)}")
        if skill_score < 50:
            missing_skills = set(required_lower) - exact_matches - partial_matches
            reasons.append(f"缺少技能: {', '.join(missing_skills)}")
        
        return skill_score, reasons
    
    def calculate_availability_score(self, hours_available: int, 
                                   task_complexity: str = "medium") -> Tuple[float, List[str]]:
        """Calculate availability score based on hours and task complexity"""
        # Define required hours for different complexity levels
        complexity_hours = {
            "low": 5,
            "medium": 15,
            "high": 30
        }
        
        required_hours = complexity_hours.get(task_complexity.lower(), 15)
        
        if hours_available >= required_hours * 1.5:
            score = 100.0
            reason = f"时间充足 ({hours_available}h >= {required_hours * 1.5}h)"
        elif hours_available >= required_hours:
            score = 80.0
            reason = f"时间足够 ({hours_available}h >= {required_hours}h)"
        elif hours_available >= required_hours * 0.7:
            score = 60.0
            reason = f"时间紧张 ({hours_available}h < {required_hours}h)"
        else:
            score = 30.0
            reason = f"时间不足 ({hours_available}h << {required_hours}h)"
        
        return score, [reason]
    
    def calculate_performance_score(self, performance: float) -> Tuple[float, List[str]]:
        """Calculate performance score"""
        if performance >= 90:
            return 100.0, ["历史表现优秀 (≥90分)"]
        elif performance >= 80:
            return 85.0, ["历史表现良好 (80-89分)"]
        elif performance >= 70:
            return 70.0, ["历史表现一般 (70-79分)"]
        elif performance >= 60:
            return 55.0, ["历史表现较差 (60-69分)"]
        else:
            return 30.0, ["历史表现很差 (<60分)"]
    
    def calculate_recency_score(self, last_done_at: Optional[str]) -> Tuple[float, List[str]]:
        """Calculate recency score based on last task completion"""
        if not last_done_at or last_done_at == "无":
            return 50.0, ["新人，无历史记录"]
        
        try:
            # Parse timestamp (assuming milliseconds)
            if isinstance(last_done_at, (int, float)):
                last_done = datetime.fromtimestamp(last_done_at / 1000)
            else:
                # Try to parse string format
                last_done = datetime.fromisoformat(str(last_done_at))
            
            days_since = (datetime.now() - last_done).days
            
            if days_since <= 7:
                return 100.0, ["最近很活跃 (≤7天)"]
            elif days_since <= 30:
                return 80.0, ["最近较活跃 (≤30天)"]
            elif days_since <= 90:
                return 60.0, ["最近不太活跃 (≤90天)"]
            else:
                return 40.0, [f"很久未活跃 ({days_since}天前)"]
                
        except Exception as e:
            logger.warning(f"Error parsing last_done_at: {e}")
            return 50.0, ["无法解析活跃时间"]
    
    def calculate_match_score(self, task_info: Dict[str, Any],
                             candidate: Dict[str, Any]) -> MatchScore:
        """Calculate comprehensive match score for a candidate"""
        # Extract task requirements
        required_skills = task_info.get("skill_tags", [])
        task_complexity = task_info.get("complexity", "medium")

        # Extract candidate information (支持中文字段名)
        candidate_fields = candidate.get("fields", candidate)

        # 处理中文字段名映射
        candidate_skills = (
            candidate_fields.get("技能标签", []) or
            candidate_fields.get("skill_tags", [])
        )
        hours_available = (
            candidate_fields.get("工作负载", 0) or
            candidate_fields.get("hours_available", 0)
        )
        performance = (
            candidate_fields.get("历史评分", 70.0) or
            candidate_fields.get("performance", 70.0)
        )
        last_done_at = (
            candidate_fields.get("last_done_at") or
            candidate_fields.get("最后完成时间")
        )

        # 添加调试日志
        logger.info(f"Matching candidate: {candidate_fields.get('姓名', 'Unknown')}")
        logger.info(f"  Required skills: {required_skills}")
        logger.info(f"  Candidate skills: {candidate_skills}")
        logger.info(f"  Hours available: {hours_available}")
        logger.info(f"  Performance: {performance}")
        logger.info(f"  Last done at: {last_done_at}")
        
        # Calculate individual scores
        skill_score, skill_reasons = self.calculate_skill_match(required_skills, candidate_skills)
        availability_score, availability_reasons = self.calculate_availability_score(
            hours_available, task_complexity
        )
        performance_score, performance_reasons = self.calculate_performance_score(performance)
        recency_score, recency_reasons = self.calculate_recency_score(last_done_at)
        
        # Calculate weighted total score
        weights = {
            "skill": 0.4,
            "availability": 0.25,
            "performance": 0.2,
            "recency": 0.15
        }
        
        total_score = (
            skill_score * weights["skill"] +
            availability_score * weights["availability"] +
            performance_score * weights["performance"] +
            recency_score * weights["recency"]
        )
        
        # Combine all reasons
        all_reasons = skill_reasons + availability_reasons + performance_reasons + recency_reasons
        
        return MatchScore(
            skill_score=skill_score,
            availability_score=availability_score,
            performance_score=performance_score,
            recency_score=recency_score,
            total_score=total_score,
            reasons=all_reasons
        )

    async def get_cached_candidates(self) -> List[Dict[str, Any]]:
        """Get candidates with caching for better performance"""
        import time
        current_time = time.time()

        # Check if cache is valid
        if (self._candidates_cache is not None and
            current_time - self._cache_timestamp < self._cache_ttl):
            logger.info(f"Using cached candidates ({len(self._candidates_cache)} candidates)")
            return self._candidates_cache

        # Fetch fresh candidates
        logger.info("Fetching fresh candidates from database")
        candidates = await self.bitable_client.list_available_persons()

        # Update cache
        self._candidates_cache = candidates
        self._cache_timestamp = current_time

        logger.info(f"Cached {len(candidates)} candidates")
        return candidates

    async def find_top_candidates(self, task_info: Dict[str, Any],
                                 use_llm: bool = False) -> List[Dict[str, Any]]:
        """Find top 3 candidates for a task"""
        try:
            # Get all available candidates (with caching)
            candidates = await self.get_cached_candidates()
            
            if not candidates:
                logger.warning("No candidates available")
                return []
            
            # 暂时禁用LLM匹配，直接使用规则匹配确保稳定性
            if use_llm and len(candidates) >= 1:
                logger.info("LLM matching is temporarily disabled for stability")
                # try:
                #     import asyncio
                #     logger.info(f"Attempting LLM matching with {len(candidates)} candidates")
                #
                #     # 设置3秒超时，确保总响应时间在10秒内
                #     llm_matches = await asyncio.wait_for(
                #         self.llm_service.match_candidates(task_info, candidates),
                #         timeout=3.0
                #     )
                #
                #     if llm_matches:
                #         logger.info(f"LLM matching successful in time, found {len(llm_matches)} matches")
                #         return llm_matches
                #     else:
                #         logger.warning("LLM matching returned empty results")
                #
                # except asyncio.TimeoutError:
                #     logger.warning("LLM matching timeout (3s), falling back to rule-based matching")
                # except Exception as e:
                #     logger.warning(f"LLM matching failed, falling back to rule-based: {e}")
            
            # 使用规则匹配（高性能、稳定）
            logger.info("Using rule-based matching for fast and reliable results")
            scored_candidates = []

            for candidate in candidates:
                match_score = self.calculate_match_score(task_info, candidate)

                # Add score information to candidate
                candidate_with_score = candidate.copy()

                # 添加英文字段名映射，以便前端使用
                fields = candidate.get("fields", {})
                candidate_name = fields.get("姓名", fields.get("name", "未知用户"))

                candidate_with_score.update({
                    # 基本信息
                    "name": candidate_name,
                    "user_id": fields.get("用户ID", fields.get("user_id", "")),
                    "skill_tags": fields.get("技能标签", fields.get("skill_tags", [])),

                    # 匹配分数信息
                    "match_score": int(match_score.total_score),
                    "match_reasons": match_score.reasons,
                    "score_breakdown": {
                        "skill": match_score.skill_score,
                        "availability": match_score.availability_score,
                        "performance": match_score.performance_score,
                        "recency": match_score.recency_score
                    }
                })

                logger.info(f"Rule-based match: {candidate_name} - Score: {int(match_score.total_score)}%")
                scored_candidates.append(candidate_with_score)
            
            # Sort by total score and return top 3
            scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)
            top_candidates = scored_candidates[:3]
            
            logger.info(f"Found {len(top_candidates)} top candidates")
            return top_candidates
            
        except Exception as e:
            logger.error(f"Error finding top candidates: {e}")
            return []


# Global matching service instance
_matching_service: Optional[MatchingService] = None


def get_matching_service() -> MatchingService:
    """Get global matching service instance"""
    global _matching_service
    if _matching_service is None:
        _matching_service = MatchingService()
    return _matching_service
