"""
Feishu service module
Handles message sending, receiving, group management, and event processing
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
    CreateChatRequest,
    CreateChatRequestBody,
    CreateChatMembersRequest,
    CreateChatMembersRequestBody
)
from lark_oapi.api.contact.v3 import GetUserRequest

from ..config import get_settings

logger = logging.getLogger(__name__)


class MessageType:
    """Message types"""
    TEXT = "text"
    POST = "post"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    MEDIA = "media"
    STICKER = "sticker"
    INTERACTIVE = "interactive"
    SHARE_CHAT = "share_chat"
    SHARE_USER = "share_user"


class FeishuService:
    """Feishu service for handling messages and chats"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = lark.Client.builder() \
            .app_id(self.settings.feishu.app_id) \
            .app_secret(self.settings.feishu.app_secret) \
            .log_level(lark.LogLevel.DEBUG if self.settings.app.debug else lark.LogLevel.INFO) \
            .build()
    
    async def send_message(self, receive_id: str, msg_type: str, content: Union[str, Dict],
                          receive_id_type: str = "chat_id", reply_to_message_id: Optional[str] = None) -> str:
        """Send a message to a chat or user, optionally as a reply"""
        try:
            # 准备消息内容
            if msg_type == MessageType.TEXT and isinstance(content, str):
                content = {"text": content}
            elif msg_type == MessageType.POST and isinstance(content, dict):
                # Content is already a rich text object
                pass
            elif msg_type == MessageType.INTERACTIVE and isinstance(content, dict):
                # Content is already an interactive card object
                pass

            # 如果是回复消息，使用专门的回复API
            if reply_to_message_id:
                return await self._send_reply_message(reply_to_message_id, msg_type, content)

            # 普通消息发送
            request_body = CreateMessageRequestBody.builder() \
                .receive_id(receive_id) \
                .msg_type(msg_type) \
                .content(json.dumps(content)) \
                .build()

            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(request_body) \
                .build()

            # 发送请求
            response = self.client.im.v1.message.create(request)

            if not response.success():
                logger.error(f"Failed to send message: {response.msg}")
                raise Exception(f"Failed to send message: {response.msg}")

            message_id = response.data.message_id
            logger.info(f"Sent message with ID: {message_id}")
            return message_id

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def _send_reply_message(self, parent_message_id: str, msg_type: str, content: Dict) -> str:
        """Send a reply message using the reply API"""
        try:
            # 构建回复请求
            request_body = ReplyMessageRequestBody.builder() \
                .msg_type(msg_type) \
                .content(json.dumps(content)) \
                .build()

            request = ReplyMessageRequest.builder() \
                .message_id(parent_message_id) \
                .request_body(request_body) \
                .build()

            # 发送回复请求
            response = self.client.im.v1.message.reply(request)

            if not response.success():
                logger.error(f"Failed to send reply message: {response.msg}")
                raise Exception(f"Failed to send reply message: {response.msg}")

            message_id = response.data.message_id
            logger.info(f"Sent reply message with ID: {message_id} (reply_to: {parent_message_id})")
            return message_id

        except Exception as e:
            logger.error(f"Error sending reply message: {e}")
            raise
    
    async def send_text_message(self, receive_id: str, text: str,
                               receive_id_type: str = "chat_id", reply_to_message_id: Optional[str] = None) -> str:
        """Send a text message, optionally as a reply"""
        return await self.send_message(receive_id, MessageType.TEXT, text, receive_id_type, reply_to_message_id)
    
    async def send_interactive_card(self, receive_id: str, card: Dict[str, Any],
                                   receive_id_type: str = "chat_id", reply_to_message_id: Optional[str] = None) -> str:
        """Send an interactive card message, optionally as a reply"""
        return await self.send_message(receive_id, MessageType.INTERACTIVE, card, receive_id_type, reply_to_message_id)
    
    async def create_group_chat(self, name: str, description: str,
                               user_ids: List[str]) -> str:
        """Create a new group chat"""
        try:
            # 构建请求
            request = CreateChatRequest.builder() \
                .request_body(CreateChatRequestBody.builder()
                    .name(name)
                    .description(description)
                    .chat_mode("group")
                    .chat_type("private")
                    .owner_id(user_ids[0] if user_ids else None)
                    .user_id_list(user_ids)
                    .build()) \
                .build()

            # 发送请求
            response = self.client.im.v1.chat.create(request)

            if not response.success():
                logger.error(f"Failed to create group chat: {response.msg}")
                raise Exception(f"Failed to create group chat: {response.msg}")

            chat_id = response.data.chat_id
            logger.info(f"Created group chat {name} with ID: {chat_id}")
            return chat_id

        except Exception as e:
            logger.error(f"Error creating group chat: {e}")
            raise
    
    async def add_chat_members(self, chat_id: str, user_ids: List[str]) -> bool:
        """Add members to a chat"""
        try:
            # 构建请求
            request = CreateChatMembersRequest.builder() \
                .chat_id(chat_id) \
                .request_body(CreateChatMembersRequestBody.builder()
                    .id_list(user_ids)
                    .build()) \
                .build()

            # 发送请求
            response = self.client.im.v1.chat_members.create(request)

            if not response.success():
                logger.error(f"Failed to add chat members: {response.msg}")
                raise Exception(f"Failed to add chat members: {response.msg}")

            logger.info(f"Added {len(user_ids)} members to chat {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding chat members: {e}")
            raise
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        try:
            # 构建请求
            request = GetUserRequest.builder() \
                .user_id(user_id) \
                .user_id_type("user_id") \
                .build()

            # 发送请求
            response = self.client.contact.v3.user.get(request)

            if not response.success():
                logger.error(f"Failed to get user info: {response.msg}")
                raise Exception(f"Failed to get user info: {response.msg}")

            user = response.data.user
            return {
                "user_id": user.user_id,
                "name": user.name,
                "en_name": user.en_name,
                "email": user.email,
                "mobile": user.mobile,
                "status": user.status
            }

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise
    
    def create_task_selection_card(self, task_title: str, task_description: str, 
                                  candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an interactive card for task assignment"""
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**新任务：{task_title}**\n\n{task_description}"
                }
            },
            {
                "tag": "hr"
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**推荐候选人 Top-3：**"
                }
            }
        ]
        
        # Add candidate buttons
        for i, candidate in enumerate(candidates[:3], 1):
            elements.append({
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{i}. {candidate['name']}**"
                        }
                    },
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"匹配度: {candidate.get('match_score', 0)}%"
                        }
                    }
                ]
            })
            
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"技能: {', '.join(candidate.get('skill_tags', []))}"
                }
            })
            
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": f"✅ 选择 {candidate['name']}"
                        },
                        "type": "primary",
                        "value": {
                            "action": "select_candidate",
                            "user_id": candidate["user_id"],
                            "task_id": task_title  # This should be the actual task ID
                        }
                    }
                ]
            })
            
            if i < len(candidates[:3]):
                elements.append({"tag": "hr"})
        
        return {
            "config": {
                "wide_screen_mode": True
            },
            "elements": elements
        }
    
    def create_task_result_card(self, task_title: str, status: str, 
                               message: str, details: Optional[str] = None) -> Dict[str, Any]:
        """Create a card for task completion results"""
        color = "green" if status == "success" else "red"
        emoji = "🎉" if status == "success" else "❌"
        
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{emoji} 任务结果**"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**任务：** {task_title}"
                }
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**状态：** {message}"
                }
            }
        ]
        
        if details:
            elements.extend([
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**详情：**\n{details}"
                    }
                }
            ])
        
        return {
            "config": {
                "wide_screen_mode": True
            },
            "elements": elements
        }

    def parse_message_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse message event from webhook"""
        try:
            event = event_data.get("event", {})
            if not event:
                return None

            message = event.get("message", {})
            sender = event.get("sender", {})

            return {
                "message_id": message.get("message_id"),
                "chat_id": message.get("chat_id"),
                "chat_type": message.get("chat_type"),
                "message_type": message.get("message_type"),
                "content": message.get("content"),
                "sender_id": sender.get("sender_id", {}).get("user_id"),
                "sender_type": sender.get("sender_type"),
                "create_time": message.get("create_time")
            }

        except Exception as e:
            logger.error(f"Error parsing message event: {e}")
            return None

    def parse_card_action_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse card action event from webhook"""
        try:
            event = event_data.get("event", {})
            if not event:
                return None

            action = event.get("action", {})
            user = event.get("user", {})

            return {
                "message_id": event.get("message_id"),
                "chat_id": event.get("chat_id"),
                "action_value": action.get("value"),
                "action_tag": action.get("tag"),
                "user_id": user.get("user_id"),
                "timestamp": event.get("timestamp")
            }

        except Exception as e:
            logger.error(f"Error parsing card action event: {e}")
            return None

    def is_bot_mentioned(self, content: str) -> bool:
        """Check if bot is mentioned in the message"""
        # This is a simplified check - in practice you might want to check for @bot_name
        return "@bot" in content.lower() or "新任务" in content

    def clean_mention_text(self, content: str) -> str:
        """Clean mention text from message content"""
        import re
        # 移除@机器人相关的文本
        cleaned = re.sub(r'@[^\s]*\s*', '', content)
        cleaned = re.sub(r'@_user_\d+\s*', '', cleaned)
        cleaned = cleaned.strip()
        return cleaned

    def extract_task_from_message(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract task information from message content"""
        try:
            # Simple parsing - in practice you might want more sophisticated NLP
            if "新任务" not in content:
                return None

            # Extract task details using simple string parsing
            lines = content.split('\n')
            task_info = {
                "title": "",
                "description": "",
                "skill_tags": [],
                "deadline": None
            }

            for line in lines:
                line = line.strip()
                if line.startswith("标题:") or line.startswith("任务:"):
                    task_info["title"] = line.split(":", 1)[1].strip()
                elif line.startswith("描述:") or line.startswith("说明:"):
                    task_info["description"] = line.split(":", 1)[1].strip()
                elif line.startswith("技能:") or line.startswith("要求:"):
                    skills_str = line.split(":", 1)[1].strip()
                    task_info["skill_tags"] = [s.strip() for s in skills_str.split(",")]
                elif line.startswith("截止:") or line.startswith("deadline:"):
                    # Simple date parsing - you might want to use dateutil for better parsing
                    deadline_str = line.split(":", 1)[1].strip()
                    task_info["deadline"] = deadline_str

            # If no structured format, use the whole content as description
            if not task_info["title"] and not task_info["description"]:
                # Remove @bot mentions and "新任务" prefix
                clean_content = content.replace("@bot", "").replace("新任务", "").strip()
                task_info["description"] = clean_content
                task_info["title"] = clean_content[:50] + "..." if len(clean_content) > 50 else clean_content

            return task_info if task_info["title"] or task_info["description"] else None

        except Exception as e:
            logger.error(f"Error extracting task from message: {e}")
            return None

    async def send_daily_report(self, chat_id: str, stats: Dict[str, int]) -> str:
        """Send daily task statistics report"""
        total = stats.get("total", 0)
        done = stats.get("done", 0)
        in_progress = stats.get("in_progress", 0)
        returned = stats.get("returned", 0)

        completion_rate = (done / total * 100) if total > 0 else 0

        report_content = f"""**📊 今日任务统计报告**

**总览：**
• 总任务数：{total}
• 已完成：{done}
• 进行中：{in_progress}
• 已退回：{returned}
• 完成率：{completion_rate:.1f}%

**状态分布：**
• 草稿：{stats.get('draft', 0)}
• 已分配：{stats.get('assigned', 0)}
• 进行中：{stats.get('in_progress', 0)}
• 已退回：{stats.get('returned', 0)}
• 已完成：{stats.get('done', 0)}
• 已归档：{stats.get('archived', 0)}

---
*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""

        return await self.send_text_message(chat_id, report_content)


# Global feishu service instance
_feishu_service: Optional[FeishuService] = None


def get_feishu_service() -> FeishuService:
    """Get global feishu service instance"""
    global _feishu_service
    if _feishu_service is None:
        _feishu_service = FeishuService()
    return _feishu_service
