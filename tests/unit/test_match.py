"""
Unit tests for matching service module
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.match import MatchingService, MatchScore


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    service = Mock()
    service.match_candidates = AsyncMock()
    return service


@pytest.fixture
def mock_bitable_client():
    """Mock bitable client"""
    client = Mock()
    client.list_available_persons = AsyncMock()
    return client


@pytest.fixture
def matching_service(mock_llm_service, mock_bitable_client):
    """Create MatchingService instance with mocked dependencies"""
    with patch('app.services.match.get_llm_service', return_value=mock_llm_service), \
         patch('app.services.match.get_bitable_client', return_value=mock_bitable_client):
        
        service = MatchingService()
        return service


class TestMatchingService:
    """Test MatchingService class"""
    
    def test_calculate_skill_match_exact(self, matching_service):
        """Test exact skill matching"""
        required_skills = ["Python", "FastAPI", "PostgreSQL"]
        candidate_skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
        
        score, reasons = matching_service.calculate_skill_match(required_skills, candidate_skills)
        
        assert score == 100.0
        assert "完全匹配技能" in reasons[0]
    
    def test_calculate_skill_match_partial(self, matching_service):
        """Test partial skill matching"""
        required_skills = ["Python", "FastAPI", "PostgreSQL"]
        candidate_skills = ["Python", "Django", "MySQL"]
        
        score, reasons = matching_service.calculate_skill_match(required_skills, candidate_skills)
        
        assert 0 < score < 100
        assert len(reasons) > 0
    
    def test_calculate_skill_match_no_match(self, matching_service):
        """Test no skill matching"""
        required_skills = ["Python", "FastAPI"]
        candidate_skills = ["Java", "Spring"]
        
        score, reasons = matching_service.calculate_skill_match(required_skills, candidate_skills)
        
        assert score < 50
        assert "缺少技能" in reasons[-1]
    
    def test_calculate_skill_match_no_requirements(self, matching_service):
        """Test skill matching with no requirements"""
        required_skills = []
        candidate_skills = ["Python", "FastAPI"]
        
        score, reasons = matching_service.calculate_skill_match(required_skills, candidate_skills)
        
        assert score == 100.0
        assert "无特定技能要求" in reasons[0]
    
    def test_calculate_skill_match_no_candidate_skills(self, matching_service):
        """Test skill matching with no candidate skills"""
        required_skills = ["Python", "FastAPI"]
        candidate_skills = []
        
        score, reasons = matching_service.calculate_skill_match(required_skills, candidate_skills)
        
        assert score == 0.0
        assert "候选人未填写技能信息" in reasons[0]
    
    def test_calculate_availability_score_sufficient(self, matching_service):
        """Test availability score with sufficient hours"""
        score, reasons = matching_service.calculate_availability_score(40, "medium")
        
        assert score == 100.0
        assert "时间充足" in reasons[0]
    
    def test_calculate_availability_score_adequate(self, matching_service):
        """Test availability score with adequate hours"""
        score, reasons = matching_service.calculate_availability_score(15, "medium")
        
        assert score == 80.0
        assert "时间足够" in reasons[0]
    
    def test_calculate_availability_score_tight(self, matching_service):
        """Test availability score with tight hours"""
        score, reasons = matching_service.calculate_availability_score(10, "medium")
        
        assert score == 60.0
        assert "时间紧张" in reasons[0]
    
    def test_calculate_availability_score_insufficient(self, matching_service):
        """Test availability score with insufficient hours"""
        score, reasons = matching_service.calculate_availability_score(5, "medium")
        
        assert score == 30.0
        assert "时间不足" in reasons[0]
    
    def test_calculate_performance_score_excellent(self, matching_service):
        """Test performance score for excellent performance"""
        score, reasons = matching_service.calculate_performance_score(95.0)
        
        assert score == 100.0
        assert "历史表现优秀" in reasons[0]
    
    def test_calculate_performance_score_good(self, matching_service):
        """Test performance score for good performance"""
        score, reasons = matching_service.calculate_performance_score(85.0)
        
        assert score == 85.0
        assert "历史表现良好" in reasons[0]
    
    def test_calculate_performance_score_average(self, matching_service):
        """Test performance score for average performance"""
        score, reasons = matching_service.calculate_performance_score(75.0)
        
        assert score == 70.0
        assert "历史表现一般" in reasons[0]
    
    def test_calculate_performance_score_poor(self, matching_service):
        """Test performance score for poor performance"""
        score, reasons = matching_service.calculate_performance_score(50.0)
        
        assert score == 30.0
        assert "历史表现很差" in reasons[0]
    
    def test_calculate_recency_score_recent(self, matching_service):
        """Test recency score for recent activity"""
        recent_timestamp = int((datetime.now() - timedelta(days=3)).timestamp() * 1000)
        
        score, reasons = matching_service.calculate_recency_score(recent_timestamp)
        
        assert score == 100.0
        assert "最近很活跃" in reasons[0]
    
    def test_calculate_recency_score_moderate(self, matching_service):
        """Test recency score for moderate activity"""
        moderate_timestamp = int((datetime.now() - timedelta(days=20)).timestamp() * 1000)
        
        score, reasons = matching_service.calculate_recency_score(moderate_timestamp)
        
        assert score == 80.0
        assert "最近较活跃" in reasons[0]
    
    def test_calculate_recency_score_old(self, matching_service):
        """Test recency score for old activity"""
        old_timestamp = int((datetime.now() - timedelta(days=120)).timestamp() * 1000)
        
        score, reasons = matching_service.calculate_recency_score(old_timestamp)
        
        assert score == 40.0
        assert "很久未活跃" in reasons[0]
    
    def test_calculate_recency_score_no_history(self, matching_service):
        """Test recency score for no history"""
        score, reasons = matching_service.calculate_recency_score(None)
        
        assert score == 50.0
        assert "新人，无历史记录" in reasons[0]
    
    def test_calculate_recency_score_invalid_format(self, matching_service):
        """Test recency score with invalid format"""
        score, reasons = matching_service.calculate_recency_score("invalid_date")
        
        assert score == 50.0
        assert "无法解析活跃时间" in reasons[0]
    
    def test_calculate_match_score(self, matching_service):
        """Test comprehensive match score calculation"""
        task_info = {
            "skill_tags": ["Python", "FastAPI"],
            "complexity": "medium"
        }
        
        candidate = {
            "fields": {
                "skill_tags": ["Python", "FastAPI", "PostgreSQL"],
                "hours_available": 40,
                "performance": 85.0,
                "last_done_at": int((datetime.now() - timedelta(days=5)).timestamp() * 1000)
            }
        }
        
        match_score = matching_service.calculate_match_score(task_info, candidate)
        
        assert isinstance(match_score, MatchScore)
        assert match_score.skill_score == 100.0
        assert match_score.availability_score == 100.0
        assert match_score.performance_score == 85.0
        assert match_score.recency_score == 100.0
        assert match_score.total_score > 90.0
        assert len(match_score.reasons) > 0
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_with_llm(self, matching_service, mock_llm_service, mock_bitable_client):
        """Test finding top candidates with LLM"""
        # Mock candidates
        candidates = [
            {"user_id": "user1", "fields": {"name": "Alice", "skill_tags": ["Python"]}},
            {"user_id": "user2", "fields": {"name": "Bob", "skill_tags": ["JavaScript"]}},
            {"user_id": "user3", "fields": {"name": "Charlie", "skill_tags": ["Python", "FastAPI"]}},
            {"user_id": "user4", "fields": {"name": "David", "skill_tags": ["Java"]}}
        ]
        mock_bitable_client.list_available_persons.return_value = candidates
        
        # Mock LLM response
        llm_matches = [
            {"user_id": "user3", "match_score": 95, "name": "Charlie"},
            {"user_id": "user1", "match_score": 80, "name": "Alice"},
            {"user_id": "user2", "match_score": 60, "name": "Bob"}
        ]
        mock_llm_service.match_candidates.return_value = llm_matches
        
        task_info = {"skill_tags": ["Python", "FastAPI"]}
        
        result = await matching_service.find_top_candidates(task_info, use_llm=True)
        
        assert len(result) == 3
        assert result[0]["user_id"] == "user3"
        assert result[0]["match_score"] == 95
        mock_llm_service.match_candidates.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_rule_based(self, matching_service, mock_llm_service, mock_bitable_client):
        """Test finding top candidates with rule-based matching"""
        # Mock candidates
        candidates = [
            {
                "user_id": "user1",
                "fields": {
                    "name": "Alice",
                    "skill_tags": ["Python", "FastAPI"],
                    "hours_available": 40,
                    "performance": 90.0,
                    "last_done_at": int((datetime.now() - timedelta(days=3)).timestamp() * 1000)
                }
            },
            {
                "user_id": "user2",
                "fields": {
                    "name": "Bob",
                    "skill_tags": ["JavaScript"],
                    "hours_available": 20,
                    "performance": 75.0,
                    "last_done_at": int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                }
            }
        ]
        mock_bitable_client.list_available_persons.return_value = candidates
        
        # Mock LLM failure
        mock_llm_service.match_candidates.side_effect = Exception("LLM failed")
        
        task_info = {"skill_tags": ["Python", "FastAPI"]}
        
        result = await matching_service.find_top_candidates(task_info, use_llm=True)
        
        assert len(result) == 2
        assert result[0]["user_id"] == "user1"  # Should be ranked higher
        assert result[0]["match_score"] > result[1]["match_score"]
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_no_candidates(self, matching_service, mock_bitable_client):
        """Test finding top candidates with no available candidates"""
        mock_bitable_client.list_available_persons.return_value = []
        
        task_info = {"skill_tags": ["Python"]}
        
        result = await matching_service.find_top_candidates(task_info)
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_few_candidates(self, matching_service, mock_bitable_client):
        """Test finding top candidates with few available candidates (no LLM)"""
        # Mock only 2 candidates (less than threshold for LLM)
        candidates = [
            {
                "user_id": "user1",
                "fields": {
                    "name": "Alice",
                    "skill_tags": ["Python"],
                    "hours_available": 40,
                    "performance": 85.0,
                    "last_done_at": None
                }
            },
            {
                "user_id": "user2",
                "fields": {
                    "name": "Bob",
                    "skill_tags": ["Python", "FastAPI"],
                    "hours_available": 30,
                    "performance": 90.0,
                    "last_done_at": int((datetime.now() - timedelta(days=5)).timestamp() * 1000)
                }
            }
        ]
        mock_bitable_client.list_available_persons.return_value = candidates
        
        task_info = {"skill_tags": ["Python", "FastAPI"]}
        
        result = await matching_service.find_top_candidates(task_info, use_llm=True)
        
        assert len(result) == 2
        assert result[0]["user_id"] == "user2"  # Should be ranked higher due to better skill match
        assert "match_score" in result[0]
        assert "match_reasons" in result[0]


class TestMatchScore:
    """Test MatchScore dataclass"""
    
    def test_match_score_creation(self):
        """Test MatchScore creation"""
        score = MatchScore(
            skill_score=90.0,
            availability_score=80.0,
            performance_score=85.0,
            recency_score=75.0,
            total_score=82.5,
            reasons=["Good skill match", "Sufficient time"]
        )
        
        assert score.skill_score == 90.0
        assert score.availability_score == 80.0
        assert score.performance_score == 85.0
        assert score.recency_score == 75.0
        assert score.total_score == 82.5
        assert len(score.reasons) == 2
