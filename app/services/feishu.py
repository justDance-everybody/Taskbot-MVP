"""飞书服务模块"""
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import *
    LARK_SDK_AVAILABLE = True
except ImportError:
    LARK_SDK_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Lark SDK not available")
from app.config import settings

logger = logging.getLogger(__name__)

class FeishuService:
    def __init__(self):
        self.app_id = settings.feishu_app_id
        self.app_secret = settings.feishu_app_secret
        
        if not LARK_SDK_AVAILABLE:
            raise ImportError("Lark SDK is required but not available. Please install lark-oapi package.")
        
        if not self.app_id or not self.app_secret:
            raise ValueError("Feishu app_id and app_secret are required")
        
        # 使用真实的飞书SDK，设置默认user_id_type
        self.client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        logger.info("FeishuService initialized with real Lark SDK")
    
    async def send_message(self, user_id: str, message: str):
        """发送消息给用户"""
        try:
            # 构建消息体
            request = CreateMessageRequest.builder() \
                .receive_id_type("user_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(user_id)
                    .msg_type("text")
                    .content(json.dumps({"text": message}, ensure_ascii=False))
                    .build()) \
                .build()
            
            # 发送消息
            response = self.client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"发送消息失败: {response.msg}")
                return False
            
            logger.info(f"消息发送成功给用户 {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息异常: {str(e)}")
            return False
    
    async def send_message_to_chat(self, chat_id: str, message: str):
        """发送消息到聊天群组"""
        try:
            # 构建消息体
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(json.dumps({"text": message}, ensure_ascii=False))
                    .build()) \
                .build()
            
            # 发送消息
            response = self.client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(f"发送消息到聊天群组失败: {response.msg}")
                return False
            
            logger.info(f"消息发送成功到聊天群组 {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息到聊天群组异常: {str(e)}")
            return False
    
    async def send_text_message(self, user_id: str = None, text: str = "", chat_id: str = None):
        """发送文本消息给用户或聊天群组"""
        if chat_id:
            return await self.send_message_to_chat(chat_id, text)
        elif user_id:
            return await self.send_message(user_id, text)
        else:
            logger.error("必须提供user_id或chat_id")
            return False
    
    async def send_candidate_cards(self, chat_id: str, candidates: List[Dict[str, Any]], task_id: str) -> bool:
        """发送候选人卡片消息"""
        try:
            # 构建候选人卡片内容
            card_content = {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**任务ID: {task_id}**\n推荐候选人:",
                            "tag": "lark_md"
                        }
                    }
                ]
            }
            
            # 添加候选人信息
            for i, candidate in enumerate(candidates[:3]):
                card_content["elements"].append({
                    "tag": "div",
                    "text": {
                        "content": f"{i+1}. {candidate.get('name', 'Unknown')} - 技能: {', '.join(candidate.get('skills', []))}",
                        "tag": "lark_md"
                    }
                })
            
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("interactive")
                    .content(json.dumps(card_content))
                    .build()) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f"Candidate cards sent successfully to {chat_id} for task {task_id}")
                return True
            else:
                logger.error(f"Failed to send candidate cards: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending candidate cards: {str(e)}")
            return False
    
    async def send_task_notification(self, user_id: str, task_data: Dict[str, Any]) -> bool:
        """发送任务通知"""
        try:
            # 构建任务通知卡片
            card_content = {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": f"**新任务通知**\n任务: {task_data.get('title', '')}\n描述: {task_data.get('description', '')}\n截止时间: {task_data.get('deadline', '')}\n优先级: {task_data.get('priority', 'medium')}",
                            "tag": "lark_md"
                        }
                    }
                ]
            }
            
            request = CreateMessageRequest.builder() \
                .receive_id_type("user_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(user_id)
                    .msg_type("interactive")
                    .content(json.dumps(card_content))
                    .build()) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f"Task notification sent successfully to {user_id}")
                return True
            else:
                logger.error(f"Failed to send task notification: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending task notification: {str(e)}")
            return False
    
    async def send_card_message(self, user_id: str = None, card: Dict[str, Any] = None, chat_id: str = None) -> bool:
        """发送交互式卡片消息"""
        try:
            if not card:
                logger.error("卡片内容不能为空")
                return False
            
            # 确定接收者类型和ID
            if chat_id:
                receive_id_type = "chat_id"
                receive_id = chat_id
            elif user_id:
                receive_id_type = "user_id"
                receive_id = user_id
            else:
                logger.error("必须提供user_id或chat_id")
                return False
            
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("interactive")
                    .content(json.dumps(card, ensure_ascii=False))
                    .build()) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f"交互式卡片发送成功到 {receive_id_type}: {receive_id}")
                return True
            else:
                logger.error(f"发送交互式卡片失败: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"发送交互式卡片异常: {str(e)}")
            return False
    
    # 用户信息和群聊成员相关方法已移除，如需要请重新实现
    
    async def create_chat(self, name: str, members: List[str]) -> Optional[str]:
        """创建群聊"""
        try:
            import httpx
            
            logger.info(f"开始创建群聊: {name}，成员: {members}")
            
            # 获取访问令牌
            access_token = await self._get_access_token()
            if not access_token:
                logger.error("无法获取访问令牌")
                return None
            
            # 构建请求体
            payload = {
                "name": name,
                "description": f"任务协作群 - {name}",
                "user_id_list": members,
                "chat_mode": "group",
                "chat_type": "private"
            }
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            
            # 构建URL，明确设置user_id_type查询参数
            url = "https://open.feishu.cn/open-apis/im/v1/chats?user_id_type=user_id"
            
            # 发送HTTP请求
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
                logger.info(f"群聊创建API调用: {url}")
                logger.info(f"请求体: {payload}")
                logger.info(f"响应状态: {response.status_code}")
                logger.info(f"响应内容: {response.text}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        chat_id = result['data']['chat_id']
                        logger.info(f"群聊创建成功: {name}, chat_id: {chat_id}")
                        return chat_id
                    else:
                        logger.error(f"群聊创建失败: {result.get('code')} - {result.get('msg')}")
                        return None
                else:
                    logger.error(f"HTTP请求失败: {response.status_code} - {response.text}")
                    return None
                
        except Exception as e:
            logger.error(f"创建群聊异常: {str(e)}")
            return None
    
    async def _get_access_token(self) -> Optional[str]:
        """获取访问令牌"""
        try:
            import httpx
            
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        return result['tenant_access_token']
                    else:
                        logger.error(f"获取访问令牌失败: {result.get('msg')}")
                        return None
                else:
                    logger.error(f"获取访问令牌HTTP请求失败: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取访问令牌异常: {str(e)}")
            return None
    
    # 以下方法已移除，如需要请重新实现：
    # - send_approval_card: 发送审批卡片
    # - handle_card_action: 处理卡片交互动作  
    # - send_daily_report: 发送日报
    # - get_message_history: 获取消息历史

# 创建全局实例
feishu_service = FeishuService()