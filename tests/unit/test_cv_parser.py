"""
CV Parser 单元测试
测试PDF文本提取、字段验证逻辑和默认值填充
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, mock_open
import io
import sys
from app.services.cv_parser import CVParser


class TestPDFTextExtraction:
    """测试PDF文本提取"""
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_with_pdfplumber(self):
        """测试使用pdfplumber提取PDF文本"""
        mock_pdf_content = b"fake pdf content"
        expected_text = "这是简历内容\n姓名：张三\n技能：Python, FastAPI"
        
        # 模拟pdfplumber模块
        mock_pdfplumber = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = expected_text
        
        mock_pdf = MagicMock()
        mock_pdf.__enter__.return_value.pages = [mock_page]
        mock_pdf.__exit__ = MagicMock()
        
        mock_pdfplumber.open.return_value = mock_pdf
        
        parser = CVParser()
        
        with patch.dict('sys.modules', {'pdfplumber': mock_pdfplumber}):
            result = await parser._extract_pdf_text(mock_pdf_content)
        
        # 验证提取的文本
        assert result == expected_text.strip()
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_fallback_to_pypdf2(self):
        """测试降级到PyPDF2提取文本"""
        mock_pdf_content = b"fake pdf content"
        expected_text = "简历内容\n姓名：李四"
        
        # 模拟pdfplumber失败
        mock_pdfplumber = MagicMock()
        mock_pdfplumber.open.side_effect = Exception("pdfplumber failed")
        
        # 模拟PyPDF2成功
        mock_pypdf2 = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = expected_text
        
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pypdf2.PdfReader.return_value = mock_reader
        
        parser = CVParser()
        
        with patch.dict('sys.modules', {'pdfplumber': mock_pdfplumber, 'PyPDF2': mock_pypdf2}):
            result = await parser._extract_pdf_text(mock_pdf_content)
        
        # 验证使用PyPDF2提取的文本
        assert expected_text in result
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_both_methods_fail(self):
        """测试两种方法都失败时返回空字符串"""
        mock_pdf_content = b"fake pdf content"
        
        # 模拟pdfplumber失败
        mock_pdfplumber = MagicMock()
        mock_pdfplumber.open.side_effect = Exception("pdfplumber failed")
        
        # 模拟PyPDF2也失败
        mock_pypdf2 = MagicMock()
        mock_pypdf2.PdfReader.side_effect = Exception("PyPDF2 failed")
        
        parser = CVParser()
        
        with patch.dict('sys.modules', {'pdfplumber': mock_pdfplumber, 'PyPDF2': mock_pypdf2}):
            result = await parser._extract_pdf_text(mock_pdf_content)
        
        # 验证返回空字符串
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_empty_content(self):
        """测试提取空PDF内容"""
        mock_pdf_content = b"fake pdf content"
        
        # 模拟pdfplumber返回空文本
        mock_pdfplumber = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = MagicMock()
        mock_pdf.__enter__.return_value.pages = [mock_page]
        mock_pdf.__exit__ = MagicMock()
        mock_pdfplumber.open.return_value = mock_pdf
        
        # 模拟PyPDF2也返回空
        mock_pypdf2 = MagicMock()
        mock_reader = MagicMock()
        mock_reader.pages = []
        mock_pypdf2.PdfReader.return_value = mock_reader
        
        parser = CVParser()
        
        with patch.dict('sys.modules', {'pdfplumber': mock_pdfplumber, 'PyPDF2': mock_pypdf2}):
            result = await parser._extract_pdf_text(mock_pdf_content)
        
        # 验证返回空字符串
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_pdf_text_multiple_pages(self):
        """测试提取多页PDF文本"""
        mock_pdf_content = b"fake pdf content"
        
        # 模拟多页PDF
        mock_pdfplumber = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "第一页内容"
        
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "第二页内容"
        
        mock_pdf = MagicMock()
        mock_pdf.__enter__.return_value.pages = [mock_page1, mock_page2]
        mock_pdf.__exit__ = MagicMock()
        mock_pdfplumber.open.return_value = mock_pdf
        
        parser = CVParser()
        
        with patch.dict('sys.modules', {'pdfplumber': mock_pdfplumber}):
            result = await parser._extract_pdf_text(mock_pdf_content)
        
        # 验证包含所有页面内容
        assert "第一页内容" in result
        assert "第二页内容" in result


class TestFieldValidation:
    """测试字段验证逻辑"""
    
    def test_validate_and_fill_defaults_complete_data(self):
        """测试完整数据的验证"""
        data = {
            "name": "张三",
            "skills": ["Python", "FastAPI", "Docker"],
            "job_level": 3,
            "experience_years": 5,
            "education": "本科",
            "work_experience": "5年Python开发经验",
            "projects": "开发过多个Web项目"
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "张三_简历.pdf")
        
        # 验证所有字段都存在
        assert result["name"] == "张三"
        assert len(result["skills"]) == 3
        assert result["job_level"] == 3
        assert result["experience_years"] == 5
        assert result["needs_review"] is False
    
    def test_validate_and_fill_defaults_missing_name(self):
        """测试缺少姓名时的处理"""
        data = {
            "skills": ["Python"],
            "job_level": 2,
            "experience_years": 3
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "候选人A_简历.pdf")
        
        # 验证使用文件名作为姓名
        assert result["name"] == "候选人A"
        # 验证标记需要审核
        assert result["needs_review"] is True
    
    def test_validate_and_fill_defaults_empty_skills(self):
        """测试技能列表为空时的处理"""
        data = {
            "name": "李四",
            "skills": [],
            "job_level": 2,
            "experience_years": 3
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "李四_简历.pdf")
        
        # 验证技能列表为空
        assert result["skills"] == []
        # 验证标记需要审核
        assert result["needs_review"] is True
    
    def test_validate_and_fill_defaults_skills_as_string(self):
        """测试技能为字符串时的转换"""
        data = {
            "name": "王五",
            "skills": "Python, FastAPI, Docker",
            "job_level": 3,
            "experience_years": 4
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "王五_简历.pdf")
        
        # 验证字符串被转换为列表
        assert isinstance(result["skills"], list)
        assert len(result["skills"]) == 3
        assert "Python" in result["skills"]
    
    def test_validate_and_fill_defaults_job_level_mapping(self):
        """测试职级映射"""
        test_cases = [
            ("junior", 1),
            ("初级", 1),
            ("mid", 2),
            ("中级", 2),
            ("senior", 3),
            ("高级", 3),
            ("lead", 4),
            ("专家", 4),
            ("principal", 5),
            ("架构师", 5)
        ]
        
        parser = CVParser()
        
        for level_str, expected_level in test_cases:
            data = {
                "name": "测试",
                "skills": ["Python"],
                "job_level": level_str,
                "experience_years": 3
            }
            
            result = parser._validate_and_fill_defaults(data, "test.pdf")
            assert result["job_level"] == expected_level
    
    def test_validate_and_fill_defaults_job_level_out_of_range(self):
        """测试职级超出范围时的处理"""
        # 测试超过5的职级
        data = {
            "name": "测试",
            "skills": ["Python"],
            "job_level": 10,
            "experience_years": 3
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "test.pdf")
        
        # 验证限制在1-5范围内
        assert result["job_level"] == 5
        
        # 测试小于1的职级
        data["job_level"] = 0
        result = parser._validate_and_fill_defaults(data, "test.pdf")
        assert result["job_level"] == 1
    
    def test_validate_and_fill_defaults_experience_years_extraction(self):
        """测试从字符串提取经验年数"""
        data = {
            "name": "测试",
            "skills": ["Python"],
            "job_level": 2,
            "experience_years": "5年工作经验"
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "test.pdf")
        
        # 验证提取数字
        assert result["experience_years"] == 5
    
    def test_validate_and_fill_defaults_experience_years_negative(self):
        """测试负数经验年数的处理"""
        data = {
            "name": "测试",
            "skills": ["Python"],
            "job_level": 2,
            "experience_years": -5
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "test.pdf")
        
        # 验证转换为0
        assert result["experience_years"] == 0
    
    def test_validate_and_fill_defaults_needs_review_logic(self):
        """测试needs_review标记逻辑"""
        parser = CVParser()
        
        # 情况1：姓名和技能都缺失
        data1 = {
            "skills": [],
            "job_level": 1,
            "experience_years": 0
        }
        result1 = parser._validate_and_fill_defaults(data1, "test.pdf")
        assert result1["needs_review"] is True
        
        # 情况2：只有姓名缺失
        data2 = {
            "skills": ["Python"],
            "job_level": 2,
            "experience_years": 3
        }
        result2 = parser._validate_and_fill_defaults(data2, "test.pdf")
        assert result2["needs_review"] is True
        
        # 情况3：只有技能缺失
        data3 = {
            "name": "张三",
            "skills": [],
            "job_level": 2,
            "experience_years": 3
        }
        result3 = parser._validate_and_fill_defaults(data3, "test.pdf")
        assert result3["needs_review"] is True
        
        # 情况4：经验为0但职级大于1
        data4 = {
            "name": "李四",
            "skills": ["Python"],
            "job_level": 3,
            "experience_years": 0
        }
        result4 = parser._validate_and_fill_defaults(data4, "test.pdf")
        assert result4["needs_review"] is True
        
        # 情况5：所有关键字段都正常
        data5 = {
            "name": "王五",
            "skills": ["Python"],
            "job_level": 2,
            "experience_years": 3
        }
        result5 = parser._validate_and_fill_defaults(data5, "test.pdf")
        assert result5["needs_review"] is False


class TestDefaultValueFilling:
    """测试默认值填充"""
    
    def test_get_default_resume_data(self):
        """测试获取默认简历数据"""
        parser = CVParser()
        result = parser._get_default_resume_data("张三_简历.pdf")
        
        # 验证所有必需字段都存在
        assert "name" in result
        assert "skills" in result
        assert "job_level" in result
        assert "experience_years" in result
        assert "education" in result
        assert "work_experience" in result
        assert "projects" in result
        assert "needs_review" in result
        
        # 验证默认值
        assert result["name"] == "张三"
        assert result["skills"] == []
        assert result["job_level"] == 1
        assert result["experience_years"] == 0
        assert result["needs_review"] is True
    
    def test_get_default_resume_data_long_filename(self):
        """测试长文件名的处理"""
        parser = CVParser()
        long_filename = "这是一个非常长的文件名超过十个字符_简历.pdf"
        result = parser._get_default_resume_data(long_filename)
        
        # 验证文件名被截断
        assert len(result["name"]) <= 10
    
    def test_get_default_resume_data_no_filename(self):
        """测试没有文件名时的处理"""
        parser = CVParser()
        result = parser._get_default_resume_data()
        
        # 验证使用默认姓名
        assert result["name"] == "Unknown"
    
    def test_validate_fills_missing_fields(self):
        """测试验证时填充缺失字段"""
        data = {
            "name": "张三"
            # 缺少其他字段
        }
        
        parser = CVParser()
        result = parser._validate_and_fill_defaults(data, "test.pdf")
        
        # 验证所有字段都被填充
        assert result["skills"] == []
        assert result["job_level"] == 1
        assert result["experience_years"] == 0
        assert result["education"] == "未知"
        assert result["work_experience"] == "暂无描述"
        assert result["projects"] == "暂无项目经验"


class TestParseResume:
    """测试完整的简历解析流程"""
    
    @pytest.mark.asyncio
    async def test_parse_resume_success(self):
        """测试成功解析简历"""
        mock_pdf_content = b"fake pdf content"
        # 确保文本长度超过50字符
        mock_pdf_text = "姓名：张三\n技能：Python, FastAPI, Docker, React\n经验：5年开发经验，熟悉微服务架构"
        
        mock_llm_response = {
            "name": "张三",
            "skills": ["Python", "FastAPI"],
            "job_level": 3,
            "experience_years": 5,
            "education": "本科",
            "work_experience": "5年开发经验",
            "projects": "多个项目"
        }
        
        mock_llm_service = AsyncMock()
        mock_llm_service.call_with_retry = AsyncMock(
            return_value='{"name": "张三", "skills": ["Python", "FastAPI"], "job_level": 3, "experience_years": 5, "education": "本科", "work_experience": "5年开发经验", "projects": "多个项目"}'
        )
        
        parser = CVParser(llm_service=mock_llm_service)
        
        with patch.object(parser, '_extract_pdf_text', 
                         new_callable=AsyncMock, return_value=mock_pdf_text):
            result = await parser.parse_resume(mock_pdf_content, "张三_简历.pdf")
        
        # 验证解析结果
        assert result["name"] == "张三"
        assert "Python" in result["skills"]
        assert result["job_level"] == 3
        assert result["experience_years"] == 5
    
    @pytest.mark.asyncio
    async def test_parse_resume_pdf_extraction_fails(self):
        """测试PDF提取失败时返回默认数据"""
        mock_pdf_content = b"fake pdf content"
        
        mock_llm_service = AsyncMock()
        parser = CVParser(llm_service=mock_llm_service)
        
        with patch.object(parser, '_extract_pdf_text', 
                         new_callable=AsyncMock, return_value=""):
            result = await parser.parse_resume(mock_pdf_content, "test.pdf")
        
        # 验证返回默认数据
        assert result["needs_review"] is True
        assert result["name"] == "test"
    
    @pytest.mark.asyncio
    async def test_parse_resume_pdf_text_too_short(self):
        """测试PDF文本过短时返回默认数据"""
        mock_pdf_content = b"fake pdf content"
        short_text = "短"  # 少于50字符
        
        mock_llm_service = AsyncMock()
        parser = CVParser(llm_service=mock_llm_service)
        
        with patch.object(parser, '_extract_pdf_text', 
                         new_callable=AsyncMock, return_value=short_text):
            result = await parser.parse_resume(mock_pdf_content, "test.pdf")
        
        # 验证返回默认数据
        assert result["needs_review"] is True
    
    @pytest.mark.asyncio
    async def test_parse_resume_no_llm_service(self):
        """测试没有LLM服务时返回默认数据"""
        mock_pdf_content = b"fake pdf content"
        mock_pdf_text = "这是一段足够长的简历文本内容，包含了各种信息，超过了50个字符的限制要求。"
        
        parser = CVParser(llm_service=None)
        
        with patch.object(parser, '_extract_pdf_text', 
                         new_callable=AsyncMock, return_value=mock_pdf_text):
            result = await parser.parse_resume(mock_pdf_content, "test.pdf")
        
        # 验证返回默认数据
        assert result["needs_review"] is True
    
    @pytest.mark.asyncio
    async def test_parse_resume_llm_parse_exception(self):
        """测试LLM解析异常时返回默认数据"""
        mock_pdf_content = b"fake pdf content"
        mock_pdf_text = "这是一段足够长的简历文本内容，包含了各种信息，超过了50个字符的限制要求。"
        
        mock_llm_service = AsyncMock()
        mock_llm_service.call_with_retry = AsyncMock(
            side_effect=Exception("LLM服务异常")
        )
        
        parser = CVParser(llm_service=mock_llm_service)
        
        with patch.object(parser, '_extract_pdf_text', 
                         new_callable=AsyncMock, return_value=mock_pdf_text):
            result = await parser.parse_resume(mock_pdf_content, "test.pdf")
        
        # 验证返回默认数据
        assert result["needs_review"] is True


class TestLLMParse:
    """测试LLM解析"""
    
    @pytest.mark.asyncio
    async def test_llm_parse_valid_json(self):
        """测试解析有效的JSON响应"""
        pdf_text = "简历内容"
        json_response = '{"name": "张三", "skills": ["Python"], "job_level": 2, "experience_years": 3, "education": "本科", "work_experience": "3年经验", "projects": "项目A"}'
        
        mock_llm_service = AsyncMock()
        mock_llm_service.call_with_retry = AsyncMock(return_value=json_response)
        
        parser = CVParser(llm_service=mock_llm_service)
        result = await parser._llm_parse(pdf_text)
        
        # 验证解析结果
        assert result["name"] == "张三"
        assert result["skills"] == ["Python"]
        assert result["job_level"] == 2
    
    @pytest.mark.asyncio
    async def test_llm_parse_json_with_markdown(self):
        """测试解析带markdown代码块的JSON"""
        pdf_text = "简历内容"
        json_response = '```json\n{"name": "李四", "skills": ["Java"], "job_level": 3, "experience_years": 5, "education": "硕士", "work_experience": "5年经验", "projects": "项目B"}\n```'
        
        mock_llm_service = AsyncMock()
        mock_llm_service.call_with_retry = AsyncMock(return_value=json_response)
        
        parser = CVParser(llm_service=mock_llm_service)
        result = await parser._llm_parse(pdf_text)
        
        # 验证解析结果
        assert result["name"] == "李四"
        assert result["skills"] == ["Java"]
    
    @pytest.mark.asyncio
    async def test_llm_parse_invalid_json(self):
        """测试解析无效JSON时返回空字典"""
        pdf_text = "简历内容"
        invalid_json = "这不是有效的JSON"
        
        mock_llm_service = AsyncMock()
        mock_llm_service.call_with_retry = AsyncMock(return_value=invalid_json)
        
        parser = CVParser(llm_service=mock_llm_service)
        result = await parser._llm_parse(pdf_text)
        
        # 验证返回空字典
        assert result == {}
