"""
Match Service 单元测试
测试Top-2匹配、候选人截断和空候选人池处理
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.match import MatchService, match_service


class TestTop2Matching:
    """测试Top-2排序正确性"""
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_returns_exactly_two(self, mock_bitable):
        """测试返回恰好2个候选人"""
        # 准备测试数据
        task_data = {
            "title": "开发API",
            "description": "开发用户登录API",
            "skill_tags": ["Python", "FastAPI"],
            "deadline": "2024-01-15"
        }
        
        # 模拟5个候选人
        mock_candidates = [
            {"user_id": f"user{i}", "name": f"候选人{i}", "skill_tags": ["Python", "FastAPI"], 
             "average_score": 80 + i, "experience": i} 
            for i in range(1, 6)
        ]
        
        # 配置mock
        mock_bitable.get_available_candidates.return_value = mock_candidates
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            
            with patch.object(service, '_llm_match_candidates', 
                            new_callable=AsyncMock) as mock_llm:
                # 模拟LLM返回带分数的候选人
                mock_llm.return_value = [
                    {**c, "match_score": 90 - i*10, "match_reason": f"理由{i}"} 
                    for i, c in enumerate(mock_candidates)
                ]
                
                result = await service.find_top_candidates(task_data, limit=2)
        
        # 验证返回恰好2个候选人
        assert len(result) == 2
        # 验证按分数降序排列
        assert result[0]["match_score"] >= result[1]["match_score"]
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_with_fewer_than_two(self, mock_bitable):
        """测试候选人少于2个时返回所有候选人"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 只有1个候选人
        mock_candidates = [
            {"user_id": "user1", "name": "候选人1", "skill_tags": ["Python"], 
             "average_score": 85, "experience": 3}
        ]
        
        # 配置mock
        mock_bitable.get_available_candidates.return_value = mock_candidates
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            
            with patch.object(service, '_llm_match_candidates', 
                            new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = [
                    {**mock_candidates[0], "match_score": 85, "match_reason": "技能匹配"}
                ]
                
                result = await service.find_top_candidates(task_data, limit=2)
        
        # 验证返回1个候选人（所有可用的）
        assert len(result) == 1
        assert result[0]["user_id"] == "user1"
    
    @pytest.mark.asyncio
    async def test_find_top_candidates_sorting_by_score(self, mock_bitable):
        """测试候选人按分数正确排序"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 3个候选人，分数不同
        mock_candidates = [
            {"user_id": "user1", "name": "候选人1", "skill_tags": ["Python"], 
             "average_score": 70, "experience": 2},
            {"user_id": "user2", "name": "候选人2", "skill_tags": ["Python"], 
             "average_score": 90, "experience": 5},
            {"user_id": "user3", "name": "候选人3", "skill_tags": ["Python"], 
             "average_score": 80, "experience": 3}
        ]
        
        # 配置mock
        mock_bitable.get_available_candidates.return_value = mock_candidates
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            
            with patch.object(service, '_llm_match_candidates', 
                            new_callable=AsyncMock) as mock_llm:
                # 返回乱序的分数
                mock_llm.return_value = [
                    {**mock_candidates[0], "match_score": 60, "match_reason": "理由1"},
                    {**mock_candidates[1], "match_score": 95, "match_reason": "理由2"},
                    {**mock_candidates[2], "match_score": 75, "match_reason": "理由3"}
                ]
                
                result = await service.find_top_candidates(task_data, limit=2)
        
        # 验证Top-2是分数最高的两个
        assert len(result) == 2
        assert result[0]["user_id"] == "user2"  # 分数95
        assert result[1]["user_id"] == "user3"  # 分数75
        assert result[0]["match_score"] == 95
        assert result[1]["match_score"] == 75


class TestCandidatePoolTruncation:
    """测试候选人截断逻辑"""
    
    @pytest.mark.asyncio
    async def test_candidate_pool_limited_to_15(self, mock_bitable):
        """测试候选人池限制为15人"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 配置mock返回空列表
        mock_bitable.get_available_candidates.return_value = []
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            
            with patch.object(service, '_llm_match_candidates', 
                            new_callable=AsyncMock, return_value=[]):
                await service.find_top_candidates(task_data)
        
        # 验证调用时传入了limit=15
        mock_bitable.get_available_candidates.assert_called_once()
        call_kwargs = mock_bitable.get_available_candidates.call_args[1]
        assert call_kwargs.get('limit') == 15
    
    @pytest.mark.asyncio
    async def test_candidate_pool_truncation_with_many_candidates(self, mock_bitable):
        """测试当候选人超过15人时的截断"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 模拟返回15个候选人（bitable已经限制为15）
        mock_candidates = [
            {"user_id": f"user{i}", "name": f"候选人{i}", "skill_tags": ["Python"], 
             "average_score": 80, "experience": 3} 
            for i in range(1, 16)  # 15个候选人
        ]
        
        # 配置mock
        mock_bitable.get_available_candidates.return_value = mock_candidates
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            
            with patch.object(service, '_llm_match_candidates', 
                            new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = [
                    {**c, "match_score": 80, "match_reason": "理由"} 
                    for c in mock_candidates
                ]
                
                result = await service.find_top_candidates(task_data, limit=2)
        
        # 验证最终返回2个
        assert len(result) == 2


class TestEmptyCandidatePool:
    """测试空候选人池处理"""
    
    @pytest.mark.asyncio
    async def test_empty_candidate_pool_returns_empty_list(self, mock_bitable):
        """测试空候选人池返回空列表"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 配置mock返回空列表
        mock_bitable.get_available_candidates.return_value = []
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            result = await service.find_top_candidates(task_data, limit=2)
        
        # 验证返回空列表
        assert result == []
    
    @pytest.mark.asyncio
    async def test_empty_candidate_pool_logs_warning(self, mock_bitable):
        """测试空候选人池记录警告日志"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 配置mock返回空列表
        mock_bitable.get_available_candidates.return_value = []
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            
            with patch('app.services.match.logger') as mock_logger:
                result = await service.find_top_candidates(task_data, limit=2)
                
                # 验证记录了警告日志
                mock_logger.warning.assert_called_once()
                assert "没有找到可用的候选人" in str(mock_logger.warning.call_args)
    
    @pytest.mark.asyncio
    async def test_exception_handling_returns_empty_list(self, mock_bitable):
        """测试异常处理返回空列表"""
        task_data = {
            "title": "开发API",
            "skill_tags": ["Python"],
            "deadline": "2024-01-15"
        }
        
        # 模拟bitable抛出异常
        mock_bitable.get_available_candidates.side_effect = Exception("数据库错误")
        
        # 使用patch替换全局bitable_client
        with patch('app.services.match.bitable_client', mock_bitable):
            service = MatchService()
            result = await service.find_top_candidates(task_data, limit=2)
        
        # 验证返回空列表
        assert result == []


class TestBasicMatchAlgorithm:
    """测试基础匹配算法（降级方案）"""
    
    def test_basic_match_with_skill_match(self):
        """测试基础匹配算法的技能匹配"""
        task_data = {
            "skill_tags": ["Python", "FastAPI"]
        }
        
        candidates = [
            {"user_id": "user1", "skill_tags": ["Python", "FastAPI"], 
             "average_score": 80, "experience": 3},
            {"user_id": "user2", "skill_tags": ["Python"], 
             "average_score": 80, "experience": 3}
        ]
        
        service = MatchService()
        result = service._basic_match_candidates(task_data, candidates)
        
        # 验证技能完全匹配的候选人分数更高
        assert result[0]["match_score"] > result[1]["match_score"]
    
    def test_basic_match_with_no_skill_requirements(self):
        """测试没有技能要求时的基础匹配"""
        task_data = {
            "skill_tags": []
        }
        
        candidates = [
            {"user_id": "user1", "skill_tags": ["Python"], 
             "average_score": 90, "experience": 5}
        ]
        
        service = MatchService()
        result = service._basic_match_candidates(task_data, candidates)
        
        # 验证返回结果
        assert len(result) == 1
        assert "match_score" in result[0]
        assert "match_reason" in result[0]
    
    def test_basic_match_score_calculation(self):
        """测试基础匹配分数计算"""
        task_data = {
            "skill_tags": ["Python", "FastAPI"]
        }
        
        # 完全匹配的候选人
        candidates = [
            {"user_id": "user1", "skill_tags": ["Python", "FastAPI"], 
             "average_score": 100, "experience": 5}
        ]
        
        service = MatchService()
        result = service._basic_match_candidates(task_data, candidates)
        
        # 验证分数计算：技能100% + 评分100% + 经验100% = 100分
        # (1.0 * 0.4 + 1.0 * 0.4 + 1.0 * 0.2) * 100 = 100
        assert result[0]["match_score"] == 100


class TestCalculateMatchScore:
    """测试单个候选人匹配分数计算"""
    
    @pytest.mark.asyncio
    async def test_calculate_match_score_perfect_match(self):
        """测试完美匹配的分数"""
        task_data = {
            "skill_tags": ["Python", "FastAPI"]
        }
        
        candidate = {
            "user_id": "user1",
            "skill_tags": ["Python", "FastAPI"],
            "average_score": 100,
            "experience": 5
        }
        
        service = MatchService()
        score, reason = await service.calculate_match_score(task_data, candidate)
        
        # 验证完美匹配得到高分
        assert score == 100
        assert "技能匹配" in reason
    
    @pytest.mark.asyncio
    async def test_calculate_match_score_partial_match(self):
        """测试部分匹配的分数"""
        task_data = {
            "skill_tags": ["Python", "FastAPI", "Docker"]
        }
        
        candidate = {
            "user_id": "user1",
            "skill_tags": ["Python", "FastAPI"],  # 只匹配2/3
            "average_score": 80,
            "experience": 3
        }
        
        service = MatchService()
        score, reason = await service.calculate_match_score(task_data, candidate)
        
        # 验证部分匹配得到中等分数
        assert 50 < score < 100
        assert "技能匹配" in reason
    
    @pytest.mark.asyncio
    async def test_calculate_match_score_exception_handling(self):
        """测试异常处理返回默认分数"""
        task_data = None  # 故意传入None引发异常
        candidate = {"user_id": "user1"}
        
        service = MatchService()
        score, reason = await service.calculate_match_score(task_data, candidate)
        
        # 验证返回默认分数
        assert score == 50
        assert "计算出错" in reason
