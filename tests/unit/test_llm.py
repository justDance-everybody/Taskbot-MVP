"""
LLM服务单元测试
测试LLM服务的各种功能和错误处理
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from app.services.llm import (
    LLMService, 
    DeepSeekBackend, 
    GeminiBackend, 
    OpenAIBackend
)


@pytest.fixture
def mock_httpx_client():
    """模拟httpx.AsyncClient"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client, mock_response


@pytest.fixture
def llm_service_with_backends():
    """创建带有模拟后端的LLM服务"""
    with patch('app.services.llm.settings') as mock_settings:
        mock_settings.deepseek_key = "test_deepseek_key"
        mock_settings.gemini_key = "test_gemini_key"
        mock_settings.openai_key = "test_openai_key"
        mock_settings.llm_timeout = 30
        mock_settings.default_llm_model = "deepseek"
        
        service = LLMService()
        return service


@pytest.fixture
def sample_candidates():
    """候选人数据示例"""
    return [
        {
            "user_id": "user1",
            "name": "张三",
            "skill_tags": ["python", "go", "fastapi"],
            "score": 85,
            "performance": 4,
            "experience": 5,
            "hours_available": 20
        },
        {
            "user_id": "user2",
            "name": "李四",
            "skill_tags": ["java", "spring", "mysql"],
            "score": 75,
            "performance": 3,
            "experience": 3,
            "hours_available": 15
        },
        {
            "user_id": "user3",
            "name": "王五",
            "skill_tags": ["python", "django", "postgresql"],
            "score": 90,
            "performance": 5,
            "experience": 7,
            "hours_available": 10
        }
    ]


@pytest.fixture
def sample_task_requirements():
    """任务需求示例"""
    return {
        "skill_tags": ["python", "fastapi"],
        "deadline": "2026-01-15",
        "urgency": "高"
    }


class TestDeepSeekBackend:
    """测试DeepSeek后端"""
    
    @pytest.mark.asyncio
    async def test_call_success(self, mock_httpx_client):
        """测试DeepSeek API调用成功"""
        mock_client, mock_response = mock_httpx_client
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试响应"}}]
        }
        
        backend = DeepSeekBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            result = await backend.call("测试提示词", "系统提示词")
            
            assert result == "测试响应"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_timeout(self):
        """测试DeepSeek API超时"""
        backend = DeepSeekBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(TimeoutError, match="AI延迟，请稍后重试"):
                await backend.call("测试提示词")
    
    @pytest.mark.asyncio
    async def test_call_api_error(self, mock_httpx_client):
        """测试DeepSeek API错误响应"""
        mock_client, mock_response = mock_httpx_client
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        backend = DeepSeekBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(Exception, match="DeepSeek API error: 500"):
                await backend.call("测试提示词")


class TestGeminiBackend:
    """测试Gemini后端"""
    
    @pytest.mark.asyncio
    async def test_call_success(self, mock_httpx_client):
        """测试Gemini API调用成功"""
        mock_client, mock_response = mock_httpx_client
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "测试响应"}]}}]
        }
        
        backend = GeminiBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            result = await backend.call("测试提示词", "系统提示词")
            
            assert result == "测试响应"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_timeout(self):
        """测试Gemini API超时"""
        backend = GeminiBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(TimeoutError, match="AI延迟，请稍后重试"):
                await backend.call("测试提示词")


class TestOpenAIBackend:
    """测试OpenAI后端"""
    
    @pytest.mark.asyncio
    async def test_call_success(self, mock_httpx_client):
        """测试OpenAI API调用成功"""
        mock_client, mock_response = mock_httpx_client
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "测试响应"}}]
        }
        
        backend = OpenAIBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            result = await backend.call("测试提示词", "系统提示词")
            
            assert result == "测试响应"
            mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_timeout(self):
        """测试OpenAI API超时"""
        backend = OpenAIBackend("test_key")
        
        with patch('httpx.AsyncClient') as mock_async_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_async_client.return_value.__aenter__.return_value = mock_client
            
            with pytest.raises(TimeoutError, match="AI延迟，请稍后重试"):
                await backend.call("测试提示词")



class TestLLMService:
    """测试LLM服务"""
    
    @pytest.mark.asyncio
    async def test_initialization_with_all_backends(self):
        """测试使用所有后端初始化LLM服务"""
        with patch('app.services.llm.settings') as mock_settings:
            mock_settings.deepseek_key = "test_deepseek_key"
            mock_settings.gemini_key = "test_gemini_key"
            mock_settings.openai_key = "test_openai_key"
            
            service = LLMService()
            
            assert 'deepseek' in service.backends
            assert 'gemini' in service.backends
            assert 'openai' in service.backends
            assert len(service.backends) == 3
    
    @pytest.mark.asyncio
    async def test_initialization_with_no_backends(self):
        """测试没有后端时初始化LLM服务"""
        with patch('app.services.llm.settings') as mock_settings:
            mock_settings.deepseek_key = None
            mock_settings.gemini_key = None
            mock_settings.openai_key = None
            
            service = LLMService()
            
            assert len(service.backends) == 0
    
    @pytest.mark.asyncio
    async def test_call_with_retry_success(self, llm_service_with_backends):
        """测试call_with_retry成功调用"""
        service = llm_service_with_backends
        
        # Mock the backend call
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "测试响应"
            
            result = await service.call_with_retry("测试提示词", "系统提示词", "deepseek")
            
            assert result == "测试响应"
            mock_call.assert_called_once_with("测试提示词", "系统提示词")
    
    @pytest.mark.asyncio
    async def test_call_with_retry_timeout_fallback(self, llm_service_with_backends):
        """测试超时后降级到其他模型"""
        service = llm_service_with_backends
        
        # Mock deepseek timeout, gemini success
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_deepseek:
            with patch.object(service.backends['gemini'], 'call', new_callable=AsyncMock) as mock_gemini:
                mock_deepseek.side_effect = TimeoutError("AI延迟，请稍后重试")
                mock_gemini.return_value = "Gemini响应"
                
                result = await service.call_with_retry("测试提示词", preferred_model="deepseek")
                
                assert result == "Gemini响应"
                mock_deepseek.assert_called_once()
                mock_gemini.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_call_with_retry_all_timeout(self, llm_service_with_backends):
        """测试所有模型都超时"""
        service = llm_service_with_backends
        
        # Mock all backends timeout
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_deepseek:
            with patch.object(service.backends['gemini'], 'call', new_callable=AsyncMock) as mock_gemini:
                with patch.object(service.backends['openai'], 'call', new_callable=AsyncMock) as mock_openai:
                    mock_deepseek.side_effect = TimeoutError("AI延迟，请稍后重试")
                    mock_gemini.side_effect = TimeoutError("AI延迟，请稍后重试")
                    mock_openai.side_effect = TimeoutError("AI延迟，请稍后重试")
                    
                    with pytest.raises(TimeoutError, match="AI延迟，请稍后重试"):
                        await service.call_with_retry("测试提示词")
    
    @pytest.mark.asyncio
    async def test_match_candidates_success(self, llm_service_with_backends, sample_task_requirements, sample_candidates):
        """测试候选人匹配成功"""
        service = llm_service_with_backends
        
        # Mock LLM response with valid JSON
        llm_response = json.dumps([
            {"user_id": "user1", "match_score": 95, "reason": "技能匹配度高"},
            {"user_id": "user3", "match_score": 88, "reason": "经验丰富"},
            {"user_id": "user2", "match_score": 70, "reason": "基本匹配"}
        ])
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = llm_response
            
            result = await service.match_candidates(sample_task_requirements, sample_candidates)
            
            assert len(result) == 3
            assert result[0]["user_id"] == "user1"
            assert result[0]["match_score"] == 95
            assert result[1]["user_id"] == "user3"
            mock_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_match_candidates_timeout_fallback(self, llm_service_with_backends, sample_task_requirements, sample_candidates):
        """测试候选人匹配超时使用降级算法"""
        service = llm_service_with_backends
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = TimeoutError("AI延迟，请稍后重试")
            
            result = await service.match_candidates(sample_task_requirements, sample_candidates)
            
            # Should use fallback matching
            assert len(result) <= 3
            assert all('user_id' in r and 'match_score' in r for r in result)
    
    @pytest.mark.asyncio
    async def test_match_candidates_invalid_json_fallback(self, llm_service_with_backends, sample_task_requirements, sample_candidates):
        """测试候选人匹配返回无效JSON使用降级算法"""
        service = llm_service_with_backends
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "这不是有效的JSON"
            
            result = await service.match_candidates(sample_task_requirements, sample_candidates)
            
            # Should use fallback matching
            assert len(result) <= 3
            assert all('user_id' in r and 'match_score' in r for r in result)
    
    @pytest.mark.asyncio
    async def test_evaluate_submission_success(self, llm_service_with_backends):
        """测试任务提交评估成功"""
        service = llm_service_with_backends
        
        llm_response = json.dumps({
            "score": 85,
            "failed_reasons": ["代码注释不够完整", "缺少单元测试"]
        })
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = llm_response
            
            score, reasons = await service.evaluate_submission(
                "开发登录API",
                "需要包含密码验证和JWT生成",
                "https://github.com/repo/pull/123"
            )
            
            assert score == 85
            assert len(reasons) == 2
            assert "代码注释不够完整" in reasons
    
    @pytest.mark.asyncio
    async def test_evaluate_submission_timeout(self, llm_service_with_backends):
        """测试任务提交评估超时"""
        service = llm_service_with_backends
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = TimeoutError("AI延迟，请稍后重试")
            
            score, reasons = await service.evaluate_submission(
                "开发登录API",
                "需要包含密码验证和JWT生成",
                "https://github.com/repo/pull/123"
            )
            
            assert score == 60
            assert "AI延迟" in reasons[0]
    
    @pytest.mark.asyncio
    async def test_analyze_resume_pdf_success(self, llm_service_with_backends):
        """测试PDF简历分析成功"""
        service = llm_service_with_backends
        
        # Mock PDF text extraction with enough content (>50 chars)
        pdf_text = "张三\n5年Python开发经验\n技能：Python, FastAPI, Django\n本科学历\n工作经历：曾在多家公司担任Python开发工程师"
        
        llm_response = json.dumps({
            "name": "张三",
            "skills": ["Python", "FastAPI", "Django"],
            "job_level": 3,
            "experience_years": 5,
            "education": "本科",
            "work_experience": "5年Python开发经验",
            "projects": "多个Web项目经验"
        })
        
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
                mock_extract.return_value = pdf_text
                mock_call.return_value = llm_response
                
                result = await service.analyze_resume_pdf(b"fake_pdf_content", "张三简历.pdf")
                
                assert result["name"] == "张三"
                assert "Python" in result["skills"]
                assert result["job_level"] == 3
                assert result["experience_years"] == 5
    
    @pytest.mark.asyncio
    async def test_analyze_resume_pdf_extraction_failed(self, llm_service_with_backends):
        """测试PDF文本提取失败"""
        service = llm_service_with_backends
        
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = ""  # Empty text
            
            result = await service.analyze_resume_pdf(b"fake_pdf_content", "test.pdf")
            
            # Should return default data
            assert result["name"] == "test"
            assert result["skills"] == []
            assert "PDF解析失败" in result["education"]
    
    @pytest.mark.asyncio
    async def test_analyze_resume_pdf_timeout(self, llm_service_with_backends):
        """测试PDF简历分析超时"""
        service = llm_service_with_backends
        
        # Mock PDF text extraction with enough content (>50 chars)
        pdf_text = "张三\n5年Python开发经验\n技能：Python, FastAPI, Django\n本科学历\n工作经历：曾在多家公司担任Python开发工程师"
        
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
                mock_extract.return_value = pdf_text
                mock_call.side_effect = TimeoutError("AI延迟，请稍后重试")
                
                result = await service.analyze_resume_pdf(b"fake_pdf_content", "test.pdf")
                
                # Should return default data with timeout message
                assert "AI延迟" in result["work_experience"]


class TestFallbackMatching:
    """测试降级匹配算法"""
    
    @pytest.mark.asyncio
    async def test_fallback_matching_basic(self, llm_service_with_backends, sample_task_requirements, sample_candidates):
        """测试基础降级匹配"""
        service = llm_service_with_backends
        
        result = service._fallback_matching(sample_task_requirements, sample_candidates)
        
        assert len(result) <= 3
        assert all('user_id' in r for r in result)
        assert all('match_score' in r for r in result)
        assert all('reason' in r for r in result)
        # Should be sorted by score
        if len(result) > 1:
            assert result[0]['match_score'] >= result[1]['match_score']
    
    @pytest.mark.asyncio
    async def test_fallback_matching_skill_priority(self, llm_service_with_backends):
        """测试降级匹配优先考虑技能匹配"""
        service = llm_service_with_backends
        
        task_requirements = {"skill_tags": ["python", "fastapi"]}
        candidates = [
            {
                "user_id": "user1",
                "skill_tags": ["python", "fastapi", "django"],
                "performance": 3,
                "hours_available": 10
            },
            {
                "user_id": "user2",
                "skill_tags": ["java", "spring"],
                "performance": 5,
                "hours_available": 20
            }
        ]
        
        result = service._fallback_matching(task_requirements, candidates)
        
        # user1 should rank higher due to skill match
        assert result[0]['user_id'] == 'user1'
    
    @pytest.mark.asyncio
    async def test_fallback_matching_empty_candidates(self, llm_service_with_backends):
        """测试降级匹配空候选人列表"""
        service = llm_service_with_backends
        
        result = service._fallback_matching({"skill_tags": ["python"]}, [])
        
        assert result == []


class TestResumeDataValidation:
    """测试简历数据验证"""
    
    def test_validate_resume_data_complete(self, llm_service_with_backends):
        """测试验证完整的简历数据"""
        service = llm_service_with_backends
        
        data = {
            "name": "张三",
            "skills": ["Python", "FastAPI"],
            "job_level": 3,
            "experience_years": 5,
            "education": "本科",
            "work_experience": "5年开发经验",
            "projects": "多个项目"
        }
        
        result = service._validate_resume_data(data)
        
        assert result["name"] == "张三"
        assert len(result["skills"]) == 2
        assert result["job_level"] == 3
        assert result["experience_years"] == 5
    
    def test_validate_resume_data_missing_fields(self, llm_service_with_backends):
        """测试验证缺失字段的简历数据"""
        service = llm_service_with_backends
        
        data = {"name": "李四"}
        
        result = service._validate_resume_data(data)
        
        assert result["name"] == "李四"
        assert result["skills"] == []
        assert result["job_level"] == 1
        assert result["experience_years"] == 0
    
    def test_validate_resume_data_invalid_job_level(self, llm_service_with_backends):
        """测试验证无效职级"""
        service = llm_service_with_backends
        
        data = {
            "name": "王五",
            "job_level": 10  # Invalid, should be clamped to 1-5
        }
        
        result = service._validate_resume_data(data)
        
        assert result["job_level"] == 5  # Should be clamped to max
    
    def test_validate_resume_data_string_skills(self, llm_service_with_backends):
        """测试验证字符串格式的技能"""
        service = llm_service_with_backends
        
        data = {
            "name": "赵六",
            "skills": "Python, FastAPI, Django"
        }
        
        result = service._validate_resume_data(data)
        
        assert len(result["skills"]) == 3
        assert "Python" in result["skills"]
    
    def test_get_default_resume_data(self, llm_service_with_backends):
        """测试获取默认简历数据"""
        service = llm_service_with_backends
        
        result = service._get_default_resume_data("张三简历.pdf")
        
        assert result["name"] == "张三"  # File name is truncated to 10 chars
        assert result["skills"] == []
        assert result["job_level"] == 1
        assert "PDF解析失败" in result["education"]



class TestLLMErrorHandling:
    """测试LLM错误处理"""
    
    @pytest.mark.asyncio
    async def test_handle_api_timeout(self, llm_service_with_backends):
        """测试API超时处理"""
        service = llm_service_with_backends
        
        # Mock all backends to timeout
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_deepseek:
            with patch.object(service.backends['gemini'], 'call', new_callable=AsyncMock) as mock_gemini:
                with patch.object(service.backends['openai'], 'call', new_callable=AsyncMock) as mock_openai:
                    mock_deepseek.side_effect = TimeoutError("AI延迟，请稍后重试")
                    mock_gemini.side_effect = TimeoutError("AI延迟，请稍后重试")
                    mock_openai.side_effect = TimeoutError("AI延迟，请稍后重试")
                    
                    with pytest.raises(TimeoutError, match="AI延迟，请稍后重试"):
                        await service.call_with_retry("测试提示词")
    
    @pytest.mark.asyncio
    async def test_handle_invalid_response_format(self, llm_service_with_backends, sample_task_requirements, sample_candidates):
        """测试无效响应格式处理"""
        service = llm_service_with_backends
        
        # Test with non-JSON response
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "这是一个无效的响应格式"
            
            result = await service.match_candidates(sample_task_requirements, sample_candidates)
            
            # Should fallback to algorithm
            assert isinstance(result, list)
            assert len(result) <= 3
    
    @pytest.mark.asyncio
    async def test_handle_empty_response(self, llm_service_with_backends, sample_task_requirements, sample_candidates):
        """测试空响应处理"""
        service = llm_service_with_backends
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "[]"
            
            result = await service.match_candidates(sample_task_requirements, sample_candidates)
            
            # Should fallback to algorithm
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_handle_malformed_json(self, llm_service_with_backends):
        """测试格式错误的JSON处理"""
        service = llm_service_with_backends
        
        with patch.object(service, 'call_with_retry', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = '{"score": 85, "failed_reasons": [incomplete'
            
            score, reasons = await service.evaluate_submission(
                "测试任务",
                "测试标准",
                "https://test.com"
            )
            
            # Should return default values
            assert score == 60
            assert "AI评估失败" in reasons[0]
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self, llm_service_with_backends):
        """测试速率限制错误处理"""
        service = llm_service_with_backends
        
        # Mock first backend with rate limit, second succeeds
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_deepseek:
            with patch.object(service.backends['gemini'], 'call', new_callable=AsyncMock) as mock_gemini:
                mock_deepseek.side_effect = Exception("Rate limit exceeded")
                mock_gemini.return_value = "成功响应"
                
                result = await service.call_with_retry("测试提示词", preferred_model="deepseek")
                
                # Should fallback to next model
                assert result == "成功响应"
                mock_deepseek.assert_called_once()
                mock_gemini.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_network_error(self, llm_service_with_backends):
        """测试网络错误处理"""
        service = llm_service_with_backends
        
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_deepseek:
            with patch.object(service.backends['gemini'], 'call', new_callable=AsyncMock) as mock_gemini:
                mock_deepseek.side_effect = Exception("Network error")
                mock_gemini.return_value = "成功响应"
                
                result = await service.call_with_retry("测试提示词", preferred_model="deepseek")
                
                assert result == "成功响应"
    
    @pytest.mark.asyncio
    async def test_handle_all_backends_fail(self, llm_service_with_backends):
        """测试所有后端都失败"""
        service = llm_service_with_backends
        
        # Mock all backends to fail with non-timeout errors
        for backend_name in ['deepseek', 'gemini', 'openai']:
            backend = service.backends[backend_name]
            with patch.object(backend, 'call', new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="All LLM backends failed"):
            await service.call_with_retry("测试提示词")
    
    @pytest.mark.asyncio
    async def test_handle_pdf_extraction_exception(self, llm_service_with_backends):
        """测试PDF提取异常处理"""
        service = llm_service_with_backends
        
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("PDF extraction failed")
            
            result = await service.analyze_resume_pdf(b"fake_content", "test.pdf")
            
            # Should return default data
            assert result["name"] == "test"
            assert "PDF解析失败" in result["education"]
    
    @pytest.mark.asyncio
    async def test_handle_invalid_candidate_data(self, llm_service_with_backends):
        """测试无效候选人数据处理"""
        service = llm_service_with_backends
        
        task_requirements = {"skill_tags": ["python"]}
        invalid_candidates = [
            {"user_id": "user1"},  # Missing required fields
            {"name": "test"}  # Missing user_id
        ]
        
        # Should not crash
        result = service._fallback_matching(task_requirements, invalid_candidates)
        
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_handle_missing_preferred_model(self, llm_service_with_backends):
        """测试首选模型不存在的处理"""
        service = llm_service_with_backends
        
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "成功响应"
            
            # Request non-existent model
            result = await service.call_with_retry("测试提示词", preferred_model="non_existent")
            
            # Should use available models
            assert result == "成功响应"
    
    @pytest.mark.asyncio
    async def test_handle_concurrent_timeout_and_error(self, llm_service_with_backends):
        """测试同时处理超时和其他错误"""
        service = llm_service_with_backends
        
        with patch.object(service.backends['deepseek'], 'call', new_callable=AsyncMock) as mock_deepseek:
            with patch.object(service.backends['gemini'], 'call', new_callable=AsyncMock) as mock_gemini:
                with patch.object(service.backends['openai'], 'call', new_callable=AsyncMock) as mock_openai:
                    mock_deepseek.side_effect = TimeoutError("Timeout")
                    mock_gemini.side_effect = Exception("API Error")
                    mock_openai.side_effect = TimeoutError("Timeout")
                    
                    # Should raise TimeoutError since timeout occurred
                    with pytest.raises(TimeoutError, match="AI延迟，请稍后重试"):
                        await service.call_with_retry("测试提示词")


class TestPDFExtraction:
    """测试PDF文本提取"""
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_success(self, llm_service_with_backends):
        """测试PDF文本提取成功（通过mock整个方法）"""
        service = llm_service_with_backends
        
        mock_pdf_content = b"fake_pdf_content"
        
        # Mock the entire extraction method to return text
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = "测试文本内容"
            
            result = await service._extract_pdf_text(mock_pdf_content)
            
            assert "测试文本内容" in result
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_returns_empty_on_failure(self, llm_service_with_backends):
        """测试PDF提取失败返回空字符串"""
        service = llm_service_with_backends
        
        mock_pdf_content = b"fake_pdf_content"
        
        # Mock the extraction to return empty
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = ""
            
            result = await service._extract_pdf_text(mock_pdf_content)
            
            assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_exception_handling(self, llm_service_with_backends):
        """测试PDF提取异常处理"""
        service = llm_service_with_backends
        
        mock_pdf_content = b"fake_pdf_content"
        
        # Mock the extraction to raise exception
        with patch.object(service, '_extract_pdf_text', new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("Extraction failed")
            
            with pytest.raises(Exception, match="Extraction failed"):
                await service._extract_pdf_text(mock_pdf_content)
