"""
LLM service module
Supports multiple LLM backends (DeepSeek, Gemini, OpenAI) with routing and prompt management
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
from pathlib import Path

import openai
import google.generativeai as genai
from openai import OpenAI

from ..config import get_settings

logger = logging.getLogger(__name__)


class LLMBackend(ABC):
    """Abstract base class for LLM backends"""
    
    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], 
                               temperature: float = 0.7, 
                               max_tokens: Optional[int] = None) -> str:
        """Generate response from messages"""
        pass
    
    @abstractmethod
    async def generate_json_response(self, messages: List[Dict[str, str]],
                                    temperature: float = 0.3,
                                    max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Generate JSON response from messages"""
        pass


class DeepSeekBackend(LLMBackend):
    """DeepSeek LLM backend"""
    
    def __init__(self, api_key: str, model: str = "deepseek-reasoner"):
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        self.model = model
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                               temperature: float = 0.7, 
                               max_tokens: Optional[int] = None) -> str:
        """Generate response using DeepSeek API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise
    
    async def generate_json_response(self, messages: List[Dict[str, str]],
                                    temperature: float = 0.3,
                                    max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Generate JSON response using DeepSeek API"""
        try:
            # DeepSeek需要在系统消息中明确要求JSON格式
            messages_with_json = messages.copy()
            if messages_with_json and messages_with_json[0].get("role") == "system":
                messages_with_json[0]["content"] += "\n\n请确保你的回复是有效的JSON格式。"
            else:
                messages_with_json.insert(0, {
                    "role": "system",
                    "content": "你必须以有效的JSON格式回复，不要包含任何其他文字。"
                })

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages_with_json,
                temperature=temperature,
                max_tokens=max_tokens or 1000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            logger.info(f"DeepSeek raw response: {content}")

            if not content or content.strip() == "":
                logger.error("DeepSeek returned empty response")
                raise ValueError("Empty response from DeepSeek API")

            try:
                return json.loads(content)
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse JSON response: {content}")
                raise ValueError(f"Invalid JSON response: {json_err}")

        except Exception as e:
            logger.error(f"DeepSeek JSON API error: {e}")
            raise


class GeminiBackend(LLMBackend):
    """Google Gemini LLM backend"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                               temperature: float = 0.7, 
                               max_tokens: Optional[int] = None) -> str:
        """Generate response using Gemini API"""
        try:
            # Convert messages to Gemini format
            prompt = self._convert_messages_to_prompt(messages)
            
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def generate_json_response(self, messages: List[Dict[str, str]],
                                    temperature: float = 0.3,
                                    max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Generate JSON response using Gemini API"""
        try:
            # Add JSON format instruction to the last message
            messages_copy = messages.copy()
            if messages_copy:
                messages_copy[-1]["content"] += "\n\nPlease respond with valid JSON only."

            response_text = await self.generate_response(messages_copy, temperature, max_tokens)
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in response")
            
        except Exception as e:
            logger.error(f"Gemini JSON API error: {e}")
            raise
    
    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to Gemini prompt format"""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)


class OpenAIBackend(LLMBackend):
    """OpenAI LLM backend"""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                               temperature: float = 0.7, 
                               max_tokens: Optional[int] = None) -> str:
        """Generate response using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def generate_json_response(self, messages: List[Dict[str, str]],
                                    temperature: float = 0.3,
                                    max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Generate JSON response using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"OpenAI JSON API error: {e}")
            raise


class LLMService:
    """LLM service with multiple backend support"""
    
    def __init__(self):
        self.settings = get_settings()
        self.backends: Dict[str, LLMBackend] = {}
        self._initialize_backends()
    
    def _initialize_backends(self):
        """Initialize available LLM backends"""
        llm_config = self.settings.llm
        
        # Initialize DeepSeek backend
        if llm_config.deepseek_api_key:
            try:
                self.backends["deepseek"] = DeepSeekBackend(
                    api_key=llm_config.deepseek_api_key
                )
                logger.info("DeepSeek backend initialized")
            except Exception as e:
                logger.error(f"Failed to initialize DeepSeek backend: {e}")
        
        # Initialize Gemini backend
        if llm_config.gemini_api_key:
            try:
                self.backends["gemini"] = GeminiBackend(
                    api_key=llm_config.gemini_api_key
                )
                logger.info("Gemini backend initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini backend: {e}")
        
        # Initialize OpenAI backend
        if llm_config.openai_api_key:
            try:
                self.backends["openai"] = OpenAIBackend(
                    api_key=llm_config.openai_api_key
                )
                logger.info("OpenAI backend initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI backend: {e}")
        
        if not self.backends:
            logger.warning("No LLM backends initialized")
    
    def get_backend(self, backend_name: Optional[str] = None) -> LLMBackend:
        """Get LLM backend by name or default"""
        if not backend_name:
            backend_name = self.settings.llm.default_backend
        
        if backend_name not in self.backends:
            available = list(self.backends.keys())
            if available:
                backend_name = available[0]
                logger.warning(f"Backend {backend_name} not available, using {available[0]}")
            else:
                raise ValueError("No LLM backends available")
        
        return self.backends[backend_name]

    async def generate_response(self, messages: List[Dict[str, str]],
                               backend_name: Optional[str] = None,
                               temperature: float = 0.7,
                               max_tokens: Optional[int] = None) -> str:
        """Generate response using specified or default backend"""
        backend = self.get_backend(backend_name)
        return await backend.generate_response(messages, temperature, max_tokens)

    async def generate_json_response(self, messages: List[Dict[str, str]],
                                    backend_name: Optional[str] = None,
                                    temperature: float = 0.3,
                                    max_tokens: int = 1000) -> Dict[str, Any]:
        """Generate JSON response using specified or default backend"""
        backend = self.get_backend(backend_name)
        return await backend.generate_json_response(messages, temperature, max_tokens)

    async def generate_text_response(self, messages: List[Dict[str, str]],
                                   backend_name: Optional[str] = None,
                                   temperature: float = 0.7) -> str:
        """Generate text response using specified or default backend"""
        backend = self.get_backend(backend_name)
        return await backend.generate_response(messages, temperature)

    def load_prompt_template(self, template_name: str) -> str:
        """Load prompt template from file"""
        try:
            template_path = Path("prompts") / f"{template_name}.txt"
            if template_path.exists():
                return template_path.read_text(encoding="utf-8")
            else:
                logger.warning(f"Prompt template {template_name} not found")
                return ""
        except Exception as e:
            logger.error(f"Error loading prompt template {template_name}: {e}")
            return ""

    async def match_candidates(self, task_info: Dict[str, Any],
                              candidates: List[Dict[str, Any]],
                              backend_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Match candidates to task using LLM"""
        try:
            # Load matching prompt template
            system_prompt = self.load_prompt_template("match_template")
            if not system_prompt:
                system_prompt = """你是智能人才匹配助手。根据任务需求和候选人信息，返回最匹配的Top-3候选人。

## 评分标准：
- **技能匹配度 (40%)**：候选人技能与任务要求的匹配程度
- **时间可用性 (30%)**：候选人工作负载和可用时间
- **历史表现 (20%)**：候选人过往任务的完成质量
- **活跃度 (10%)**：最近的任务参与情况

## 匹配分数说明：
- 90-100分：完美匹配，强烈推荐
- 80-89分：高度匹配，推荐
- 70-79分：良好匹配，可考虑
- 60-69分：一般匹配，需谨慎
- 60分以下：不推荐

请仔细分析每个候选人，给出合理的匹配分数和详细原因。

**重要：必须返回有效的JSON格式，不要包含任何其他文本。**

返回格式示例：
{
  "matches": [
    {
      "user_id": "候选人ID",
      "match_score": 85,
      "reasons": ["技能完全匹配Python和FastAPI", "工作负载适中", "历史表现优秀"]
    }
  ]
}"""

            # Prepare user prompt - 处理中文字段名
            title = task_info.get('title', '')
            description = task_info.get('description', '')
            skill_tags = task_info.get('skill_tags', [])
            deadline = task_info.get('deadline', '未指定')

            user_prompt = f"""任务需求:
标题: {title}
描述: {description}
技能要求: {', '.join(skill_tags) if skill_tags else '无特定要求'}
截止时间: {deadline}

候选人列表:
"""

            for i, candidate in enumerate(candidates, 1):
                # 处理中文字段名
                fields = candidate.get('fields', candidate)
                name = fields.get('姓名', fields.get('name', '未知用户'))
                user_id = fields.get('用户ID', fields.get('user_id', ''))
                skill_tags = fields.get('技能标签', fields.get('skill_tags', []))
                hours_available = fields.get('工作负载', fields.get('hours_available', 0))
                performance = fields.get('历史评分', fields.get('performance', 0))
                last_done_at = fields.get('last_done_at', fields.get('最后完成时间', '无'))

                user_prompt += f"""{i}. 用户ID: {user_id}
   姓名: {name}
   技能: {', '.join(skill_tags) if skill_tags else '无'}
   可用时间: {hours_available}小时/周
   历史表现: {performance}分
   最后完成任务: {last_done_at}

"""

            user_prompt += "\n请返回JSON格式的Top-3匹配结果。只返回JSON，不要包含任何解释文字。"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            logger.info(f"Sending LLM matching request with {len(candidates)} candidates")
            logger.debug(f"LLM prompt preview: {user_prompt[:200]}...")

            # 使用优化的参数提高响应速度
            try:
                response = await self.generate_json_response(
                    messages,
                    backend_name,
                    temperature=0.1,  # 降低温度提高速度和一致性
                    max_tokens=500    # 限制输出长度提高速度
                )
                logger.info(f"LLM response received: {response}")
            except Exception as primary_error:
                logger.warning(f"Primary LLM backend failed: {primary_error}")

                # 尝试其他可用的后端
                available_backends = list(self.backends.keys())
                if len(available_backends) > 1:
                    for backup_backend in available_backends:
                        if backup_backend != (backend_name or self.settings.llm.default_backend):
                            try:
                                logger.info(f"Trying backup backend: {backup_backend}")
                                response = await self.generate_json_response(
                                    messages,
                                    backup_backend,
                                    temperature=0.1,
                                    max_tokens=500
                                )
                                logger.info(f"Backup LLM response received: {response}")
                                break
                            except Exception as backup_error:
                                logger.warning(f"Backup backend {backup_backend} also failed: {backup_error}")
                                continue
                    else:
                        # 所有后端都失败了
                        raise primary_error
                else:
                    # 只有一个后端
                    raise primary_error

            # Process and validate response
            matches = response.get("matches", [])
            logger.info(f"Extracted {len(matches)} matches from LLM response")

            # Add candidate details to matches
            for match in matches:
                user_id = match.get("user_id")
                # 查找候选人时需要考虑中文字段名
                candidate = None
                for c in candidates:
                    c_fields = c.get('fields', c)
                    c_user_id = c_fields.get('用户ID', c_fields.get('user_id', ''))
                    if c_user_id == user_id:
                        candidate = c
                        break

                if candidate:
                    # 添加英文字段名映射
                    fields = candidate.get('fields', {})
                    # 从LLM响应中获取分数，支持多种字段名
                    score = match.get("match_score", match.get("score", 0))
                    match.update({
                        "name": fields.get('姓名', fields.get('name', '未知用户')),
                        "user_id": fields.get('用户ID', fields.get('user_id', '')),
                        "skill_tags": fields.get('技能标签', fields.get('skill_tags', [])),
                        "match_score": score,
                        "match_reasons": match.get("reasons", [])
                    })
                    logger.info(f"LLM match result: {fields.get('姓名', 'Unknown')} - Score: {score}")

            return matches[:3]  # Ensure only top 3

        except Exception as e:
            logger.error(f"Error matching candidates: {e}")
            # Fallback to rule-based matching with proper scoring
            from .match import get_matching_service

            try:
                # 使用规则匹配服务计算真实分数
                matching_service = get_matching_service()
                fallback_candidates = []

                for candidate in candidates[:3]:
                    # 计算规则匹配分数
                    match_score = matching_service.calculate_match_score(task_info, candidate)

                    fields = candidate.get('fields', {})
                    fallback_candidate = {
                        "name": fields.get('姓名', fields.get('name', '未知用户')),
                        "user_id": fields.get('用户ID', fields.get('user_id', '')),
                        "skill_tags": fields.get('技能标签', fields.get('skill_tags', [])),
                        "match_score": int(match_score.total_score),
                        "match_reasons": ["LLM匹配失败，使用规则匹配"] + match_score.reasons[:2]  # 取前2个原因
                    }
                    fallback_candidates.append(fallback_candidate)

                # 按分数排序
                fallback_candidates.sort(key=lambda x: x["match_score"], reverse=True)

                logger.info(f"Returning {len(fallback_candidates)} rule-based fallback candidates")
                return fallback_candidates

            except Exception as fallback_error:
                logger.error(f"Fallback matching also failed: {fallback_error}")
                # 最后的fallback
                simple_candidates = []
                for candidate in candidates[:3]:
                    fields = candidate.get('fields', {})
                    simple_candidate = {
                        "name": fields.get('姓名', fields.get('name', '未知用户')),
                        "user_id": fields.get('用户ID', fields.get('user_id', '')),
                        "skill_tags": fields.get('技能标签', fields.get('skill_tags', [])),
                        "match_score": 50,
                        "match_reasons": ["匹配服务暂时不可用"]
                    }
                    simple_candidates.append(simple_candidate)

                return simple_candidates

    async def review_task_submission(self, task_info: Dict[str, Any],
                                    submission_url: str,
                                    backend_name: Optional[str] = None) -> Dict[str, Any]:
        """Review task submission using LLM"""
        try:
            # Load review prompt template
            system_prompt = self.load_prompt_template("review_template")
            if not system_prompt:
                system_prompt = """你是质量评审助手。根据任务说明、验收标准和提交内容，对任务完成质量进行评分。

评分标准：
- 90-100分：完全符合要求，质量优秀
- 80-89分：基本符合要求，质量良好
- 70-79分：部分符合要求，需要改进
- 60-69分：勉强符合要求，存在明显问题
- 60分以下：不符合要求，需要重做

返回JSON格式：
{
  "score": 85,
  "passed": true,
  "failedReasons": [],
  "suggestions": ["改进建议1", "改进建议2"]
}"""

            # 处理中文字段名
            description = (
                task_info.get('任务描述', '') or
                task_info.get('description', '')
            )
            acceptance_criteria = (
                task_info.get('验收标准', '') or
                task_info.get('acceptance_criteria', '按任务说明完成')
            )

            user_prompt = f"""任务说明: {description}
验收标准: {acceptance_criteria}
提交链接: {submission_url}

请对提交内容进行评分和评价。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.generate_json_response(messages, backend_name)

            # Validate and process response
            score = response.get("score", 0)
            threshold = self.settings.task.auto_review_threshold

            result = {
                "score": score,
                "passed": score >= threshold,
                "failedReasons": response.get("failedReasons", []),
                "suggestions": response.get("suggestions", [])
            }

            return result

        except Exception as e:
            logger.error(f"Error reviewing task submission: {e}")
            # Fallback response
            return {
                "score": 0,
                "passed": False,
                "failedReasons": ["自动评审失败，请人工审核"],
                "suggestions": []
            }


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
