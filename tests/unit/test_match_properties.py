"""
Property-based tests for Match Service
Feature: taskbot-completion, Property 1: Top-2 Candidate Limit
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.match import match_service


# Strategy for generating candidate data
def candidate_strategy():
    """Generate valid candidate dictionaries"""
    return st.fixed_dictionaries({
        'user_id': st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        'name': st.text(min_size=1, max_size=50),
        'skill_tags': st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10),
        'job_level': st.sampled_from(['Junior', 'Mid', 'Senior', 'Lead']),
        'experience': st.integers(min_value=0, max_value=20),
        'total_tasks': st.integers(min_value=0, max_value=100),
        'average_score': st.integers(min_value=0, max_value=100),
        'match_score': st.integers(min_value=0, max_value=100),
        'match_reason': st.text(min_size=1, max_size=200)
    })


# Strategy for generating task data
def task_strategy():
    """Generate valid task dictionaries"""
    return st.fixed_dictionaries({
        'title': st.text(min_size=1, max_size=100),
        'description': st.text(min_size=1, max_size=500),
        'skill_tags': st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10),
        'deadline': st.text(min_size=1, max_size=50),
        'urgency': st.sampled_from(['low', 'normal', 'high', 'urgent'])
    })


@pytest.mark.asyncio
@settings(max_examples=20)
@given(
    candidates=st.lists(candidate_strategy(), min_size=2, max_size=20),
    task_data=task_strategy()
)
async def test_top2_candidate_limit_property(candidates, task_data):
    """
    Property 1: Top-2 Candidate Limit
    
    For any task matching request with a candidate pool of 2 or more candidates,
    the Match_Service SHALL return exactly 2 candidates.
    
    Validates: Requirements 1.1
    Feature: taskbot-completion, Property 1: Top-2 Candidate Limit
    """
    # Ensure we have at least 2 candidates
    assume(len(candidates) >= 2)
    
    # Create a mock bitable client with get_available_candidates method
    mock_bitable = MagicMock()
    mock_bitable.get_available_candidates = AsyncMock(return_value=candidates)
    
    # Replace the match_service's bitable with our mock
    original_bitable = match_service.bitable
    match_service.bitable = mock_bitable
    
    try:
        # Mock the LLM service to return the candidates with scores
        with patch.object(match_service, '_llm_match_candidates', new_callable=AsyncMock) as mock_llm_match:
            # Return all candidates with their match_score already set
            mock_llm_match.return_value = candidates
            
            # Call the method under test
            result = await match_service.find_top_candidates(task_data, limit=2)
            
            # Property assertion: result must have exactly 2 candidates
            assert len(result) == 2, f"Expected exactly 2 candidates, got {len(result)}"
    finally:
        # Restore original bitable
        match_service.bitable = original_bitable


@pytest.mark.asyncio
@settings(max_examples=20)
@given(
    candidates=st.lists(candidate_strategy(), min_size=0, max_size=1),
    task_data=task_strategy()
)
async def test_top2_with_fewer_candidates(candidates, task_data):
    """
    Property 1 Edge Case: When fewer than 2 candidates are available
    
    For any task matching request with fewer than 2 candidates,
    the Match_Service SHALL return all available candidates.
    
    Validates: Requirements 1.2
    Feature: taskbot-completion, Property 1: Top-2 Candidate Limit
    """
    # Create a mock bitable client
    mock_bitable = MagicMock()
    mock_bitable.get_available_candidates = AsyncMock(return_value=candidates)
    
    # Replace the match_service's bitable with our mock
    original_bitable = match_service.bitable
    match_service.bitable = mock_bitable
    
    try:
        # Mock the LLM service
        with patch.object(match_service, '_llm_match_candidates', new_callable=AsyncMock) as mock_llm_match:
            mock_llm_match.return_value = candidates
            
            # Call the method under test
            result = await match_service.find_top_candidates(task_data, limit=2)
            
            # Property assertion: result must have all available candidates (0 or 1)
            assert len(result) == len(candidates), f"Expected {len(candidates)} candidates, got {len(result)}"
    finally:
        # Restore original bitable
        match_service.bitable = original_bitable


@pytest.mark.asyncio
@settings(max_examples=20)
@given(
    candidates=st.lists(candidate_strategy(), min_size=2, max_size=20),
    task_data=task_strategy()
)
async def test_top2_returns_highest_scores(candidates, task_data):
    """
    Property 1 Invariant: Top-2 candidates have highest scores
    
    For any task matching request, the returned 2 candidates SHALL have
    the highest match_score values among all candidates.
    
    Validates: Requirements 1.1
    Feature: taskbot-completion, Property 1: Top-2 Candidate Limit
    """
    # Ensure we have at least 2 candidates
    assume(len(candidates) >= 2)
    
    # Create a mock bitable client
    mock_bitable = MagicMock()
    mock_bitable.get_available_candidates = AsyncMock(return_value=candidates)
    
    # Replace the match_service's bitable with our mock
    original_bitable = match_service.bitable
    match_service.bitable = mock_bitable
    
    try:
        # Mock the LLM service
        with patch.object(match_service, '_llm_match_candidates', new_callable=AsyncMock) as mock_llm_match:
            mock_llm_match.return_value = candidates
            
            # Call the method under test
            result = await match_service.find_top_candidates(task_data, limit=2)
            
            # Property assertion: returned candidates should have the top 2 scores
            if len(result) == 2:
                all_scores = sorted([c['match_score'] for c in candidates], reverse=True)
                result_scores = sorted([c['match_score'] for c in result], reverse=True)
                
                # The top 2 scores in result should match the top 2 scores overall
                assert result_scores[0] >= all_scores[1], "First candidate should have one of the top 2 scores"
                assert result_scores[1] >= all_scores[1] or len(candidates) == 2, "Second candidate should have one of the top 2 scores"
    finally:
        # Restore original bitable
        match_service.bitable = original_bitable
