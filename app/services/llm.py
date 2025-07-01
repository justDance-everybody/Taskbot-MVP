import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import asyncio
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class LLMBackend(ABC):
    """LLM后端抽象基类"""
    
    @abstractmethod
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        """调用LLM API"""
        pass

class DeepSeekBackend(LLMBackend):
    """DeepSeek API后端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                    raise Exception(f"DeepSeek API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            raise

class GeminiBackend(LLMBackend):
    """Google Gemini API后端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                response = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": full_prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.1,
                            "maxOutputTokens": 2000
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                    raise Exception(f"Gemini API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            raise

class OpenAIBackend(LLMBackend):
    """OpenAI API后端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    async def call(self, prompt: str, system_prompt: str = "") -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    raise Exception(f"OpenAI API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise

class LLMService:
    """LLM服务管理器"""
    
    def __init__(self):
        self.backends = {}
        self._initialize_backends()
    
    def _initialize_backends(self):
        """初始化可用的LLM后端"""
        if settings.deepseek_key:
            self.backends['deepseek'] = DeepSeekBackend(settings.deepseek_key)
            logger.info("DeepSeek backend initialized")
        
        if settings.gemini_key:
            self.backends['gemini'] = GeminiBackend(settings.gemini_key)
            logger.info("Gemini backend initialized")
        
        if settings.openai_key:
            self.backends['openai'] = OpenAIBackend(settings.openai_key)
            logger.info("OpenAI backend initialized")
        
        if not self.backends:
            logger.warning("No LLM backends available")
    
    async def call_with_retry(self, prompt: str, system_prompt: str = "", 
                             preferred_model: str = None) -> str:
        """LLM调用（已移除重试机制）"""
        model_order = [preferred_model] if preferred_model else []
        model_order.extend([m for m in self.backends.keys() if m != preferred_model])
        
        last_error = None
        
        for model_name in model_order:
            if model_name not in self.backends:
                continue
                
            backend = self.backends[model_name]
            
            try:
                logger.info(f"Calling {model_name}")
                result = await backend.call(prompt, system_prompt)
                logger.info(f"Successfully called {model_name}")
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to call {model_name}: {str(e)}")
                # 继续尝试下一个模型，不重试当前模型
        
        raise Exception(f"All LLM backends failed. Last error: {str(last_error)}")
    
    async def match_candidates(self, task_requirements: Dict[str, Any], 
                             candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """候选人匹配"""
        try:
            # 构建系统提示词
            system_prompt = """你是智能人才匹配助手。根据任务需求和候选人信息，分析匹配度并返回Top-3推荐。

候选人数据字段说明：
- name: 候选人姓名
- skill_tags: 技能标签列表（如：['go', 'python', 'java']）
- score: 候选人评分（0-100）
- performance: 历史表现评级（1-5）
- experience: 工作经验（年数）
- user_id: 候选人唯一标识

评分标准：
1. 技能匹配度 (40%): 候选人skill_tags与任务要求的匹配程度
2. 综合能力 (30%): 基于score和performance的综合评估
3. 经验匹配 (20%): experience是否满足任务复杂度要求
4. 可用性 (10%): 候选人当前状态和可用性

请返回JSON格式，包含top-3的候选人user_id和匹配分数(0-100)。"""
            
            # 构建用户提示词
            skill_tags = task_requirements.get('skill_tags', [])
            deadline = task_requirements.get('deadline', '')
            
            candidates_text = "\n".join([
                f"{i+1}) {json.dumps(candidate, ensure_ascii=False)}"
                for i, candidate in enumerate(candidates)
            ])
            
            user_prompt = f"""任务需求:
- 技能要求: {skill_tags}
- 截止时间: {deadline}
- 紧急程度: {task_requirements.get('urgency', '普通')}

候选人列表:
{candidates_text}

请仔细分析每个候选人的skill_tags字段与任务技能要求的匹配度，结合score、performance、experience等指标进行综合评估。

请返回JSON数组格式的匹配结果，例如：
[{{"user_id": "候选人ID", "match_score": 95, "reason": "技能匹配度高，具备go和python技能，评分85分，经验丰富"}}]"""
            
            # 调用LLM
            response = await self.call_with_retry(
                user_prompt, 
                system_prompt, 
                settings.default_llm_model
            )
            
            # 解析响应
            try:
                matches = json.loads(response)
                if isinstance(matches, list) and len(matches) > 0:
                    return matches[:3]  # 返回Top-3
                else:
                    logger.warning("LLM returned invalid format, using fallback")
                    return self._fallback_matching(task_requirements, candidates)
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM response, using fallback")
                return self._fallback_matching(task_requirements, candidates)
                
        except Exception as e:
            logger.error(f"Error in candidate matching: {str(e)}")
            return self._fallback_matching(task_requirements, candidates)
    
    async def evaluate_submission(self, task_description: str, acceptance_criteria: str, 
                                submission_url: str) -> Tuple[int, List[str]]:
        """评估任务提交"""
        try:
            system_prompt = """你是质量评审助手。根据任务说明、验收标准和提交内容，进行客观评分。

评分标准：
- 90-100分: 完全满足要求，质量优秀
- 80-89分: 基本满足要求，质量良好
- 70-79分: 部分满足要求，需要改进
- 60-69分: 勉强满足要求，问题较多
- 0-59分: 不满足要求，需要重做

请返回JSON格式：{"score": 分数, "failed_reasons": ["问题列表"]}"""
            
            user_prompt = f"""任务说明: {task_description}

验收标准: {acceptance_criteria}

提交链接: {submission_url}

请评估提交内容的质量并给出分数和改进建议。"""
            
            response = await self.call_with_retry(
                user_prompt,
                system_prompt,
                settings.default_llm_model
            )
            
            try:
                result = json.loads(response)
                score = result.get('score', 0)
                failed_reasons = result.get('failed_reasons', [])
                return score, failed_reasons
            except json.JSONDecodeError:
                logger.warning("Failed to parse evaluation response")
                return 60, ["AI评估失败，请人工审核"]
                
        except Exception as e:
            logger.error(f"Error in submission evaluation: {str(e)}")
            return 60, ["AI评估失败，请人工审核"]
    
    def _fallback_matching(self, task_requirements: Dict[str, Any], 
                          candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """降级匹配算法"""
        try:
            required_skills = set(task_requirements.get('skill_tags', []))
            scored_candidates = []
            
            for candidate in candidates:
                candidate_skills = set(candidate.get('skill_tags', []))
                skill_match = len(required_skills & candidate_skills) / len(required_skills) if required_skills else 0
                performance = candidate.get('performance', 0) / 5.0  # 归一化到0-1
                availability = min(candidate.get('hours_available', 0) / 8.0, 1.0)  # 归一化到0-1
                
                # 简单加权评分
                score = int((skill_match * 0.5 + performance * 0.3 + availability * 0.2) * 100)
                
                scored_candidates.append({
                    "user_id": candidate.get('user_id'),
                    "match_score": score,
                    "reason": f"技能匹配{skill_match*100:.0f}%, 历史表现{performance*100:.0f}%"
                })
            
            # 按分数排序并返回Top-3
            scored_candidates.sort(key=lambda x: x['match_score'], reverse=True)
            return scored_candidates[:3]
            
        except Exception as e:
            logger.error(f"Error in fallback matching: {str(e)}")
            return []
    
    async def analyze_resume_pdf(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """分析PDF简历并提取结构化信息"""
        try:
            # 首先尝试提取PDF文本内容
            pdf_text = await self._extract_pdf_text(file_content)
            
            if not pdf_text or len(pdf_text.strip()) < 50:
                logger.warning(f"PDF文本提取失败或内容过少: {file_name}, 提取字符数: {len(pdf_text) if pdf_text else 0}")
                return self._get_default_resume_data(file_name)
            
            logger.info(f"PDF文本提取成功: {file_name}, 字符数: {len(pdf_text)}")
            
            # 构建系统提示词
            system_prompt = """你是简历分析助手。请从简历文本中提取信息，只提取明确提到的内容，不要猜测。

请返回JSON格式：
{
  "name": "姓名",
  "skills": ["技能1", "技能2"],
  "job_level": 数字(1-5),
  "experience_years": 年数,
  "education": "教育背景", 
  "work_experience": "工作经历描述",
  "projects": "项目经验描述"
}

职级对应：1=初级 2=中级 3=高级 4=专家 5=架构师"""
            
            # 构建用户提示词，包含实际的简历文本内容
            user_prompt = f"""请分析以下简历内容：

简历文本：
{pdf_text}

提取以下信息：
- 姓名
- 技能（编程语言、技术栈、工具等）
- 工作年限
- 职级水平（根据经验判断1-5）
- 教育背景
- 工作经历
- 项目经验

只提取简历中明确提到的信息，不要添加推测内容。"""
            
            # 根据设置选择模型
            preferred_model = "deepseek"  # 优先使用DeepSeek，因为它支持文件上传
            
            # 调用LLM分析
            response = await self.call_with_retry(
                user_prompt,
                system_prompt,
                preferred_model
            )
            
            # 解析AI返回的JSON
            try:
                # 记录AI原始返回内容（用于调试）
                logger.info(f"AI原始返回内容: {response[:500]}...")  # 只记录前500字符
                
                # 处理可能被markdown代码块包裹的JSON
                json_text = response.strip()
                if json_text.startswith('```json') and json_text.endswith('```'):
                    json_text = json_text[7:-3].strip()
                elif json_text.startswith('```') and json_text.endswith('```'):
                    json_text = json_text[3:-3].strip()
                
                resume_data = json.loads(json_text)
                logger.info(f"解析后的简历数据: {resume_data}")  # 记录解析后的数据
                
                # 验证和清理数据
                validated_data = self._validate_resume_data(resume_data)
                logger.info(f"验证后的数据: {validated_data}")  # 记录验证后的数据
                
                logger.info(f"PDF简历分析成功: {file_name}, 候选人: {validated_data.get('name', 'Unknown')}")
                return validated_data
                
            except json.JSONDecodeError as e:
                logger.error(f"解析AI返回的JSON失败: {str(e)}, 原始回复: {response}")
                # 返回默认数据结构
                return self._get_default_resume_data(file_name)
                
        except Exception as e:
            logger.error(f"PDF简历分析失败: {str(e)}")
            # 返回默认数据结构
            return self._get_default_resume_data(file_name)
    
    async def _extract_pdf_text(self, file_content: bytes) -> str:
        """从PDF字节内容中提取文本"""
        try:
            # 尝试使用PyPDF2提取文本
            try:
                import PyPDF2
                import io
                
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
                text_content = ""
                
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                
                if text_content.strip():
                    logger.info("使用PyPDF2成功提取PDF文本")
                    return text_content.strip()
                    
            except ImportError:
                logger.warning("PyPDF2未安装，尝试其他方法")
            except Exception as e:
                logger.warning(f"PyPDF2提取失败: {str(e)}")
            
            # 尝试使用pdfplumber提取文本
            try:
                import pdfplumber
                import io
                
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
                logger.warning("pdfplumber未安装，尝试其他方法")
            except Exception as e:
                logger.warning(f"pdfplumber提取失败: {str(e)}")
            
            # 如果都失败了，返回空字符串
            logger.error("所有PDF文本提取方法都失败了")
            return ""
            
        except Exception as e:
            logger.error(f"PDF文本提取过程中出错: {str(e)}")
            return ""
    
    def _validate_resume_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证和清理简历数据"""
        try:
            validated = {
                'name': str(data.get('name', 'Unknown')).strip(),
                'skills': [],
                'job_level': 1,  # 默认为1（初级）
                'experience_years': 0,
                'education': str(data.get('education', '未知')).strip(),
                'work_experience': str(data.get('work_experience', '暂无描述')).strip(),
                'projects': str(data.get('projects', '暂无项目经验')).strip()
            }
            
            # 验证技能列表
            skills = data.get('skills', [])
            if isinstance(skills, list):
                validated['skills'] = [str(skill).strip() for skill in skills if skill and str(skill).strip()]
            elif isinstance(skills, str):
                validated['skills'] = [s.strip() for s in skills.split(',') if s.strip()]
            
            # 如果技能列表为空，记录并分析原因
            if not validated['skills']:
                logger.warning(f"技能列表为空，请检查简历内容: {validated['name']}")
                logger.warning(f"原始技能数据: {data.get('skills', [])}")
                # 如果工作经验大于0但没有技能，可能提取有问题
                if validated.get('experience_years', 0) > 0:
                    logger.warning(f"候选人有{validated['experience_years']}年经验但技能为空，建议人工核查")
                # 保持为空，等待后续数据库填充占位符
            
            # 验证职级 - 现在使用数字格式
            job_level = data.get('job_level', 1)
            try:
                # 如果是数字，直接使用
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
                validated['job_level'] = 1  # 默认为初级
            
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
            
            return validated
            
        except Exception as e:
            logger.error(f"验证简历数据时出错: {str(e)}")
            return self._get_default_resume_data()
    
    def _get_default_resume_data(self, file_name: str = "unknown.pdf") -> Dict[str, Any]:
        """获取默认的简历数据结构"""
        # 从文件名尝试提取姓名
        name_from_file = file_name.replace('.pdf', '').replace('简历', '').replace('resume', '').strip()
        if len(name_from_file) > 10:
            name_from_file = name_from_file[:10]
        
        return {
            'name': name_from_file if name_from_file else 'Unknown',
            'skills': [],  # PDF解析失败，无法提取技能
            'job_level': 1,  # 默认为1（初级）
            'experience_years': 0,
            'education': 'PDF解析失败，请手动补充',
            'work_experience': 'PDF文本提取失败，无法AI分析。可能是PDF格式问题或包含图片/扫描件',
            'projects': 'PDF解析失败，请手动补充'
        }

# 全局实例
llm_service = LLMService()