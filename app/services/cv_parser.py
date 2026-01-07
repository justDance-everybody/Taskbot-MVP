"""
CV Parser Module - 独立的简历解析模块

负责PDF简历的文本提取、结构化解析和字段验证
"""

import logging
from typing import Dict, Any
import io

logger = logging.getLogger(__name__)


class CVParser:
    """简历解析器 - 负责PDF简历的解析和结构化提取"""
    
    def __init__(self, llm_service=None):
        """
        初始化CV Parser
        
        Args:
            llm_service: LLM服务实例，用于AI解析
        """
        self.llm_service = llm_service
    
    async def parse_resume(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        分析PDF简历并提取结构化信息
        
        Args:
            file_content: PDF文件的字节内容
            file_name: 文件名
            
        Returns:
            包含简历信息的字典
        """
        try:
            # 1. 提取PDF文本内容
            pdf_text = await self._extract_pdf_text(file_content)
            
            if not pdf_text or len(pdf_text.strip()) < 50:
                logger.warning(f"PDF文本提取失败或内容过少: {file_name}, 提取字符数: {len(pdf_text) if pdf_text else 0}")
                return self._get_default_resume_data(file_name)
            
            logger.info(f"PDF文本提取成功: {file_name}, 字符数: {len(pdf_text)}")
            
            # 2. 使用LLM进行结构化解析
            if self.llm_service:
                resume_data = await self._llm_parse(pdf_text)
            else:
                logger.warning("LLM服务未配置，返回默认数据")
                return self._get_default_resume_data(file_name)
            
            # 3. 验证和填充默认值
            validated_data = self._validate_and_fill_defaults(resume_data, file_name)
            
            logger.info(f"PDF简历分析成功: {file_name}, 候选人: {validated_data.get('name', 'Unknown')}")
            return validated_data
            
        except Exception as e:
            logger.error(f"PDF简历分析失败: {str(e)}")
            return self._get_default_resume_data(file_name)
    
    async def _extract_pdf_text(self, file_content: bytes) -> str:
        """
        从PDF字节内容中提取文本
        支持pdfplumber和PyPDF2双后端，带错误处理和降级逻辑
        
        Args:
            file_content: PDF文件的字节内容
            
        Returns:
            提取的文本内容
        """
        try:
            # 尝试使用pdfplumber提取文本（优先，效果更好）
            try:
                import pdfplumber
                
                text_content = ""
                with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
                
                if text_content.strip():
                    logger.info("使用pdfplumber成功提取PDF文本")
                    return text_content.strip()
                    
            except ImportError:
                logger.warning("pdfplumber未安装，尝试降级到PyPDF2")
            except Exception as e:
                logger.warning(f"pdfplumber提取失败: {str(e)}，尝试降级到PyPDF2")
            
            # 降级：尝试使用PyPDF2提取文本
            try:
                import PyPDF2
                
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text_content = ""
                
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                if text_content.strip():
                    logger.info("使用PyPDF2成功提取PDF文本")
                    return text_content.strip()
                    
            except ImportError:
                logger.error("PyPDF2未安装，无法提取PDF文本")
            except Exception as e:
                logger.error(f"PyPDF2提取失败: {str(e)}")
            
            # 所有方法都失败
            logger.error("所有PDF文本提取方法都失败了")
            return ""
            
        except Exception as e:
            logger.error(f"PDF文本提取过程中出错: {str(e)}")
            return ""
    
    async def _llm_parse(self, pdf_text: str) -> Dict[str, Any]:
        """
        使用LLM解析简历文本
        
        Args:
            pdf_text: PDF提取的文本内容
            
        Returns:
            解析后的结构化数据
        """
        # 构建系统提示词 - 简化版本
        system_prompt = """你是简历分析助手。从简历中提取关键信息，返回紧凑的JSON格式。

JSON格式（必须完整）：
{"name":"姓名","skills":["技能1","技能2"],"job_level":数字1-5,"experience_years":年数}

职级：1初级 2中级 3高级 4专家 5架构师
只提取明确信息，不要猜测。"""
        
        # 构建用户提示词 - 简化版本
        user_prompt = f"""分析简历，提取：姓名、技能列表、工作年限、职级

简历：
{pdf_text[:2000]}

返回完整JSON，不要截断。"""
        
        # 调用LLM分析
        response = await self.llm_service.call_with_retry(
            user_prompt,
            system_prompt,
            "deepseek"  # 优先使用DeepSeek
        )
        
        # 解析AI返回的JSON
        try:
            import json
            
            # 记录AI原始返回内容（用于调试）
            logger.info(f"AI原始返回内容长度: {len(response)} 字符")
            logger.info(f"AI原始返回内容前500字符: {response[:500]}")
            
            # 处理可能被markdown代码块包裹的JSON
            json_text = response.strip()
            if json_text.startswith('```json'):
                # 移除 ```json 开头
                json_text = json_text[7:]
                # 移除 ``` 结尾
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                logger.info("检测到markdown json代码块，已移除标记")
            elif json_text.startswith('```'):
                # 移除 ``` 开头和结尾
                json_text = json_text[3:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()
                logger.info("检测到markdown代码块，已移除标记")
            
            logger.info(f"处理后的JSON文本长度: {len(json_text)} 字符")
            logger.info(f"处理后的JSON文本前200字符: {json_text[:200]}")
            
            resume_data = json.loads(json_text)
            logger.info(f"✅ JSON解析成功，提取到 {len(resume_data)} 个字段")
            
            return resume_data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析AI返回的JSON失败: {str(e)}")
            logger.error(f"错误位置: line {e.lineno}, column {e.colno}")
            logger.error(f"处理后的文本前1000字符: {json_text[:1000] if 'json_text' in locals() else response[:1000]}")
            logger.error(f"处理后的文本后200字符: {json_text[-200:] if 'json_text' in locals() else response[-200:]}")
            return {}
    
    def _validate_and_fill_defaults(self, data: Dict[str, Any], file_name: str = "unknown.pdf") -> Dict[str, Any]:
        """
        验证和清理简历数据，填充默认值
        
        Args:
            data: 原始解析数据
            file_name: 文件名
            
        Returns:
            验证后的数据，包含needs_review标记
        """
        try:
            # 定义必需字段列表
            required_fields = ['name', 'skills', 'job_level', 'experience_years', 
                             'education', 'work_experience', 'projects']
            
            # 跟踪原始数据是否缺失关键字段
            original_name_missing = not data.get('name') or str(data.get('name', '')).strip() == ''
            original_skills_missing = not data.get('skills') or (isinstance(data.get('skills'), list) and len(data.get('skills')) == 0)
            
            # 初始化验证后的数据结构
            validated = {
                'name': str(data.get('name', 'Unknown')).strip(),
                'skills': [],
                'job_level': 1,
                'experience_years': 0,
                'education': str(data.get('education', '未知')).strip(),
                'work_experience': str(data.get('work_experience', '暂无描述')).strip(),
                'projects': str(data.get('projects', '暂无项目经验')).strip(),
                'needs_review': False  # 默认不需要审核
            }
            
            # 验证技能列表
            skills = data.get('skills', [])
            if isinstance(skills, list):
                validated['skills'] = [str(skill).strip() for skill in skills if skill and str(skill).strip()]
            elif isinstance(skills, str):
                validated['skills'] = [s.strip() for s in skills.split(',') if s.strip()]
            
            # 如果技能列表为空，记录并标记需要审核
            if not validated['skills']:
                logger.warning(f"技能列表为空，请检查简历内容: {validated['name']}")
                logger.warning(f"原始技能数据: {data.get('skills', [])}")
                if validated.get('experience_years', 0) > 0:
                    logger.warning(f"候选人有{validated['experience_years']}年经验但技能为空，建议人工核查")
            
            # 验证职级 - 使用数字格式
            job_level = data.get('job_level', 1)
            try:
                if isinstance(job_level, (int, float)):
                    level_num = int(job_level)
                    validated['job_level'] = max(1, min(5, level_num))  # 限制在1-5范围内
                else:
                    # 如果是字符串，尝试映射到数字
                    level_str = str(job_level).strip().lower()
                    level_mapping = {
                        'junior': 1, '初级': 1, '1': 1,
                        'mid': 2, '中级': 2, '2': 2,
                        'senior': 3, '高级': 3, '3': 3,
                        'lead': 4, '专家': 4, '4': 4,
                        'principal': 5, '架构师': 5, '5': 5,
                        'manager': 4, '经理': 4, '主管': 4
                    }
                    validated['job_level'] = level_mapping.get(level_str, 1)
            except:
                validated['job_level'] = 1
            
            # 验证工作经验年数
            try:
                experience = data.get('experience_years', 0)
                if isinstance(experience, (int, float)):
                    validated['experience_years'] = max(0, int(experience))
                else:
                    # 尝试从字符串中提取数字
                    import re
                    match = re.search(r'(\d+)', str(experience))
                    validated['experience_years'] = int(match.group(1)) if match else 0
            except:
                validated['experience_years'] = 0
            
            # 如果姓名为空，使用文件名
            if not validated['name'] or validated['name'] == 'Unknown':
                name_from_file = file_name.replace('.pdf', '').replace('简历', '').replace('resume', '').replace('_', '').strip()
                if len(name_from_file) > 10:
                    name_from_file = name_from_file[:10]
                validated['name'] = name_from_file if name_from_file else 'Unknown'
            
            # 添加needs_review标记：如果关键字段缺失，标记需要人工审核
            # 检查原始数据中的姓名是否缺失
            if original_name_missing:
                validated['needs_review'] = True
                logger.warning(f"姓名缺失，标记需要人工审核")
            
            # 检查原始数据中的技能是否缺失
            if original_skills_missing or not validated['skills']:
                validated['needs_review'] = True
                logger.warning(f"技能列表为空，标记需要人工审核")
            
            if validated['experience_years'] == 0 and validated['job_level'] > 1:
                validated['needs_review'] = True
                logger.warning(f"经验年数为0但职级大于1，标记需要人工审核")
            
            return validated
            
        except Exception as e:
            logger.error(f"验证简历数据时出错: {str(e)}")
            return self._get_default_resume_data(file_name)
    
    def _get_default_resume_data(self, file_name: str = "unknown.pdf") -> Dict[str, Any]:
        """
        获取默认的简历数据结构
        
        Args:
            file_name: 文件名
            
        Returns:
            默认数据结构
        """
        # 从文件名尝试提取姓名
        name_from_file = file_name.replace('.pdf', '').replace('简历', '').replace('resume', '').replace('_', '').strip()
        if len(name_from_file) > 10:
            name_from_file = name_from_file[:10]
        
        # 如果文件名为空或为unknown，使用Unknown作为默认值
        if not name_from_file or name_from_file.lower() == 'unknown':
            name_from_file = 'Unknown'
        
        return {
            'name': name_from_file,
            'skills': [],
            'job_level': 1,
            'experience_years': 0,
            'education': 'PDF解析失败，请手动补充',
            'work_experience': 'PDF文本提取失败，无法AI分析。可能是PDF格式问题或包含图片/扫描件',
            'projects': 'PDF解析失败，请手动补充',
            'needs_review': True  # 标记需要人工审核
        }
