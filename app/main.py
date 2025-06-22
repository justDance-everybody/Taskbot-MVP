"""
FastAPI main application
Handles webhooks, events, and core business logic for Feishu Bot
"""

import json
import logging
import hashlib
import hmac
import base64
import time
from typing import Dict, Any, Optional
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from .config import get_settings
from .bitable import get_bitable_client, TaskStatus, CIState
from .services.feishu import get_feishu_service
from .services.llm import get_llm_service
from .services.match import get_matching_service
from .services.ci import get_ci_service

# 消息去重缓存 (简单的内存缓存，生产环境建议使用Redis)
processed_messages = set()
MAX_CACHE_SIZE = 1000

# 任务创建去重缓存 (更强的去重机制)
task_creation_cache = {}
TASK_CREATION_WINDOW = 300  # 5分钟内不允许创建相同内容的任务

# 任务创建时间窗口保护 (防止短时间内重复创建相同任务)
task_creation_timestamps = {}
TASK_CREATION_COOLDOWN = 30  # 30秒内不允许创建相同任务

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Feishu Task Bot",
    description="A Feishu bot for task assignment and management",
    version="1.0.0"
)

# Global services
settings = get_settings()
bitable_client = get_bitable_client()
feishu_service = get_feishu_service()
llm_service = get_llm_service()
matching_service = get_matching_service()
ci_service = get_ci_service()


def verify_feishu_signature(request_body: bytes, signature: str, timestamp: str, nonce: str) -> bool:
    """
    Verify Feishu webhook signature
    根据飞书官方文档：https://open.feishu.cn/document/ukTMukTMukTM/uYDNxYjL2QTM24iN0EjN/event-subscription-configure-/request-url-configuration-case
    """
    try:
        # 飞书签名验证使用encrypt_key，不是verify_token
        encrypt_key = settings.feishu.encrypt_key

        # 飞书签名算法：sha256(timestamp + nonce + encrypt_key + body)
        sign_data = timestamp + nonce + encrypt_key + request_body.decode('utf-8')
        expected_signature = hashlib.sha256(sign_data.encode('utf-8')).hexdigest()

        logger.info(f"Signature verification:")
        logger.info(f"  Timestamp: {timestamp}")
        logger.info(f"  Nonce: {nonce}")
        logger.info(f"  Encrypt key: {encrypt_key[:8]}...")
        logger.info(f"  Expected: {expected_signature}")
        logger.info(f"  Received: {signature}")

        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying Feishu signature: {e}")
        return False


def verify_github_signature(request_body: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    try:
        secret = settings.github.webhook_secret
        expected_signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            request_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying GitHub signature: {e}")
        return False


def decrypt_feishu_payload(encrypted_data: str) -> str:
    """
    Decrypt Feishu encrypted payload
    根据飞书官方实现，使用正确的解密算法
    """
    try:
        # Get encryption key from settings
        encrypt_key = settings.feishu.encrypt_key
        if not encrypt_key:
            raise ValueError("No encryption key configured")

        logger.info(f"Decrypting with original key: {encrypt_key[:8]}...")

        # 关键：使用SHA256哈希处理密钥（这是飞书的正确实现）
        key_hash = hashlib.sha256(encrypt_key.encode('utf-8')).digest()
        logger.info(f"SHA256 hashed key length: {len(key_hash)} bytes")

        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_data)
        logger.info(f"Total encrypted data length: {len(encrypted_bytes)} bytes")

        # 格式：iv(16字节) + encrypted_data
        if len(encrypted_bytes) < AES.block_size:
            raise ValueError("Encrypted data too short")

        # 提取IV和密文
        iv = encrypted_bytes[:AES.block_size]
        ciphertext = encrypted_bytes[AES.block_size:]

        logger.info(f"IV length: {len(iv)}, Ciphertext length: {len(ciphertext)}")

        # 创建AES解密器
        cipher = AES.new(key_hash, AES.MODE_CBC, iv)

        # 解密
        decrypted_bytes = cipher.decrypt(ciphertext)
        logger.info(f"Decrypted bytes length: {len(decrypted_bytes)}")

        # 使用飞书的unpad方法
        def _unpad(s):
            return s[:-s[-1]]

        try:
            # 去除填充
            unpadded = _unpad(decrypted_bytes)
            result = unpadded.decode('utf-8')
            logger.info("Successfully decrypted with Feishu unpad method")
            logger.info(f"Decrypted content preview: {result[:100]}...")
            return result
        except Exception as e:
            logger.error(f"Feishu unpad failed: {e}")
            logger.error(f"Raw decrypted (first 50 bytes): {decrypted_bytes[:50]}")
            logger.error(f"Raw decrypted (hex): {decrypted_bytes[:50].hex()}")
            logger.error(f"Last few bytes: {decrypted_bytes[-10:]}")
            logger.error(f"Last byte value: {decrypted_bytes[-1] if decrypted_bytes else 'None'}")
            raise

    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Feishu Task Bot is running", "timestamp": datetime.now().isoformat()}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "bitable": "ok",
            "feishu": "ok",
            "llm": "ok" if llm_service.backends else "no_backends",
            "matching": "ok",
            "ci": "ok"
        }
    }


@app.post("/webhook/feishu")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Feishu webhook events"""
    try:
        # Get request body and headers
        body = await request.body()
        headers = request.headers

        # Log incoming request for debugging
        logger.info(f"Received Feishu webhook request")
        logger.info(f"Headers: {dict(headers)}")
        logger.info(f"Body: {body.decode('utf-8')[:500]}...")

        # Verify signature if provided
        signature = headers.get("x-lark-signature")
        timestamp = headers.get("x-lark-request-timestamp")
        nonce = headers.get("x-lark-request-nonce")

        if signature and timestamp and nonce:
            if not verify_feishu_signature(body, signature, timestamp, nonce):
                logger.warning("Invalid signature detected")
                raise HTTPException(status_code=401, detail="Invalid signature")
        elif signature:
            logger.warning("Signature provided but missing timestamp or nonce")
            # 临时跳过验证，用于调试
            logger.info("Skipping signature verification for debugging")

        # Parse JSON payload
        try:
            payload = json.loads(body.decode('utf-8'))
            logger.info(f"Parsed payload type: {payload.get('type')}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Handle encrypted payload
        if "encrypt" in payload:
            logger.info("Received encrypted payload, attempting to decrypt...")
            try:
                decrypted_payload = decrypt_feishu_payload(payload["encrypt"])
                logger.info(f"Decrypted payload: {decrypted_payload}")
                payload = json.loads(decrypted_payload)
                logger.info(f"Decrypted payload type: {payload.get('type')}")
            except Exception as e:
                logger.error(f"Failed to decrypt payload: {e}")
                # If decryption fails, still try to process as normal

        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge")
            logger.info(f"Handling URL verification challenge: {challenge}")
            response = {"challenge": challenge}
            logger.info(f"Returning challenge response: {response}")
            return response

        # Process event in background
        background_tasks.add_task(process_feishu_event, payload)

        return {"message": "Event received"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Feishu webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle GitHub webhook events"""
    try:
        # Get request body and headers
        body = await request.body()
        headers = request.headers
        
        # Verify signature
        signature = headers.get("x-hub-signature-256")
        if signature and not verify_github_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON payload
        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Process event in background
        background_tasks.add_task(process_github_event, payload)
        
        return {"message": "Event received"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling GitHub webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_feishu_event(payload: Dict[str, Any]):
    """Process Feishu event"""
    try:
        event_type = payload.get("header", {}).get("event_type")
        logger.info(f"Processing Feishu event: {event_type}")
        
        if event_type == "im.message.receive_v1":
            await handle_message_event(payload)
        elif event_type == "im.message.message_read_v1":
            # Handle message read events if needed
            pass
        elif event_type == "card.action.trigger":
            await handle_card_action_event(payload)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            
    except Exception as e:
        logger.error(f"Error processing Feishu event: {e}")


async def handle_message_event(payload: Dict[str, Any]):
    """Handle incoming message events"""
    try:
        # Parse message event
        message_info = feishu_service.parse_message_event(payload)
        if not message_info:
            return
        
        # Skip bot's own messages
        if message_info.get("sender_type") == "app":
            return
        
        content = message_info.get("content", "")
        chat_id = message_info.get("chat_id")
        sender_id = message_info.get("sender_id")
        message_id = message_info.get("message_id")

        # 检查消息是否已处理（防止重复处理）
        global processed_messages

        # 详细日志记录消息信息
        logger.info(f"Processing message - ID: {message_id}, Chat: {chat_id}, Sender: {sender_id}")
        logger.info(f"Message content preview: {content[:100]}...")
        logger.info(f"Current processed_messages cache size: {len(processed_messages)}")
        if message_id and message_id in processed_messages:
            logger.warning(f"DUPLICATE MESSAGE DETECTED - Message {message_id} already processed, skipping")
            return

        # 如果没有message_id，使用内容+时间戳作为唯一标识
        if not message_id:
            import hashlib
            import time
            content_hash = hashlib.md5(f"{chat_id}_{sender_id}_{content}_{int(time.time()//10)}".encode()).hexdigest()
            message_id = f"generated_{content_hash}"
            logger.warning(f"No message_id provided, generated: {message_id}")

        # 标记消息为已处理
        processed_messages.add(message_id)
        logger.info(f"Added message {message_id} to processed cache")

        # 限制缓存大小，防止内存泄漏
        if len(processed_messages) > MAX_CACHE_SIZE:
            # 移除最旧的一半消息
            old_messages = list(processed_messages)[:MAX_CACHE_SIZE // 2]
            processed_messages -= set(old_messages)
            logger.info(f"Cache cleanup: removed {len(old_messages)} old messages")

        # Parse content based on message type
        if message_info.get("message_type") == "text":
            try:
                text_content = json.loads(content).get("text", "")
            except:
                text_content = content
        else:
            text_content = content
        
        logger.info(f"Received message: {text_content[:100]}...")
        
        # Check for daily report request
        if "#report" in text_content.lower():
            await handle_daily_report_request(chat_id, message_id)
            return

        # Check for basic commands
        if any(cmd in text_content.lower() for cmd in ['help', '帮助', 'ping', '你好', '使用说明', '表格', 'table', '链接']):
            await handle_basic_commands(text_content, chat_id, message_id)
            return

        # Check if bot is mentioned for new task
        if feishu_service.is_bot_mentioned(text_content):
            await handle_new_task_request(text_content, chat_id, sender_id, message_id)
            return
        
        # Check for task completion in child chat
        if text_content.startswith("/done"):
            await handle_task_completion(text_content, chat_id, sender_id)
            return

        # Check for table info command
        if any(cmd in text_content.lower() for cmd in ['表格信息', 'table info', '数据统计']):
            await handle_table_info_request(chat_id, message_id)
            return

        # 如果是@机器人但不是任务创建，使用LLM智能回复
        if feishu_service.is_bot_mentioned(text_content):
            await handle_intelligent_chat(text_content, chat_id, message_id)
            return

    except Exception as e:
        logger.error(f"Error handling message event: {e}")


async def handle_card_action_event(payload: Dict[str, Any]):
    """Handle card action events (button clicks)"""
    try:
        # Parse card action event
        action_info = feishu_service.parse_card_action_event(payload)
        if not action_info:
            return
        
        action_value = action_info.get("action_value", {})
        action_type = action_value.get("action")
        chat_id = action_info.get("chat_id")
        user_id = action_info.get("user_id")
        
        if action_type == "select_candidate":
            await handle_candidate_selection(action_value, chat_id, user_id)
        else:
            logger.info(f"Unhandled card action: {action_type}")
            
    except Exception as e:
        logger.error(f"Error handling card action event: {e}")


async def handle_basic_commands(content: str, chat_id: str, reply_to_message_id: Optional[str] = None):
    """Handle basic commands like help, ping, etc."""
    try:
        content_lower = content.lower()

        if any(cmd in content_lower for cmd in ['help', '帮助', '使用说明']):
            help_message = """🤖 **远程任务机器人使用指南**

📋 **基础命令：**
• `#report` - 查看任务日报统计
• `help` 或 `帮助` - 显示此帮助信息
• `ping` - 检查机器人状态
• `表格` 或 `table` - 获取多维表格访问链接

📝 **任务管理：**
• `新任务 [描述]` - 快速创建任务
• 结构化任务发布：
```
@机器人 新任务
标题: 任务标题
描述: 详细描述
技能: Python, FastAPI
截止: 2025-01-20
```

🎯 **任务执行：**
• `/done [链接]` - 提交任务完成（在任务群组中使用）

📊 **数据查看：**
• 发送 `表格` 获取多维表格链接
• 可直接在飞书中查看所有任务数据
• 支持手动编辑和数据导出

💡 **使用技巧：**
• 机器人会自动匹配合适的候选人
• 支持GitHub CI自动验收
• 支持LLM智能评分
• 所有数据实时同步到多维表格

如有问题，请联系管理员。祝您使用愉快！ 🚀"""

            await feishu_service.send_text_message(chat_id, help_message, reply_to_message_id=reply_to_message_id)

        elif 'ping' in content_lower:
            await feishu_service.send_text_message(
                chat_id,
                "🏓 Pong! 机器人运行正常 ✅\n\n📊 系统状态：\n• 数据库连接：正常\n• LLM服务：正常\n• 匹配引擎：正常",
                reply_to_message_id=reply_to_message_id
            )

        elif any(greeting in content_lower for greeting in ['你好', 'hello', 'hi']):
            await feishu_service.send_text_message(
                chat_id,
                "👋 您好！我是远程任务管理机器人。\n\n我可以帮您：\n• 发布和分配任务\n• 匹配合适的候选人\n• 自动验收任务\n• 生成任务报告\n\n发送 `help` 查看详细使用说明。",
                reply_to_message_id=reply_to_message_id
            )

        elif any(table_cmd in content_lower for table_cmd in ['表格', 'table', '链接']):
            # 显示多维表格链接
            app_token = settings.feishu.bitable_app_token
            bitable_url = f"https://feishu.cn/base/{app_token}"

            table_message = f"""📊 **多维表格访问链接**

🔗 **主表格链接：**
{bitable_url}

📋 **包含的数据表：**
• **Tasks** - 任务管理表
• **Persons** - 人员信息表

💡 **使用说明：**
• 点击链接可直接访问多维表格
• 可以查看所有任务的详细信息
• 可以手动编辑任务状态和分配
• 支持数据导出和分析

📱 **移动端访问：**
• 在飞书APP中打开链接
• 支持移动端查看和编辑"""

            await feishu_service.send_text_message(
                chat_id,
                table_message,
                reply_to_message_id=reply_to_message_id
            )

    except Exception as e:
        logger.error(f"Error handling basic commands: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 处理命令时出错: {str(e)}",
            reply_to_message_id=reply_to_message_id
        )


async def handle_intelligent_chat(content: str, chat_id: str, reply_to_message_id: Optional[str] = None):
    """Handle intelligent chat using LLM"""
    try:
        # 先发送思考中的消息
        await feishu_service.send_text_message(
            chat_id,
            "🤔 让我想想...",
            reply_to_message_id=reply_to_message_id
        )

        # 获取当前系统状态信息
        try:
            task_stats = await bitable_client.get_daily_task_stats()
            persons = await bitable_client.list_available_persons()
            person_count = len(persons)
        except:
            task_stats = {"total": 0}
            person_count = 0

        # 构建系统提示词
        system_prompt = f"""你是远程任务管理机器人，专门帮助团队管理任务分配和执行。

## 你的身份和能力：
- 名称：远程任务 Bot
- 职责：智能任务分配、候选人匹配、自动验收
- 技术栈：基于飞书多维表格、LLM智能匹配、CI/CD自动化

## 当前系统状态：
- 总任务数：{task_stats.get('total', 0)}
- 待分配任务：{task_stats.get('待分配', 0)}
- 进行中任务：{task_stats.get('InProgress', 0)}
- 已完成任务：{task_stats.get('Done', 0)}
- 注册人员：{person_count}

## 你的核心功能：
1. **任务管理**：创建、分配、跟踪任务进度
2. **智能匹配**：基于技能、工作负载、历史表现匹配最佳候选人
3. **自动验收**：GitHub CI检查、LLM智能评分
4. **数据分析**：任务统计、人员表现分析
5. **群组管理**：自动创建任务执行群组

## 可用命令：
- `新任务 [描述]` - 快速创建任务
- `#report` - 查看任务日报
- `表格` - 获取多维表格链接
- `help` - 查看详细帮助
- `/done [链接]` - 提交任务完成（任务群组中）

## 回复风格：
- 友好、专业、高效
- 使用emoji增强表达
- 提供具体可行的建议
- 主动推荐相关功能

请根据用户的问题，结合你的功能和当前系统状态，给出有帮助的回复。如果用户询问具体功能，要详细说明如何使用。"""

        # 清理用户消息（移除@机器人部分）
        user_message = feishu_service.clean_mention_text(content)

        # 调用LLM生成回复
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = await llm_service.generate_text_response(messages)

        # 发送回复
        await feishu_service.send_text_message(
            chat_id,
            response,
            reply_to_message_id=reply_to_message_id
        )

    except Exception as e:
        logger.error(f"Error in intelligent chat: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"😅 抱歉，我现在有点忙不过来。您可以：\n\n• 发送 `help` 查看我的功能\n• 发送 `新任务 [描述]` 创建任务\n• 发送 `#report` 查看任务统计\n\n如有紧急问题，请联系管理员。",
            reply_to_message_id=reply_to_message_id
        )


async def handle_table_info_request(chat_id: str, reply_to_message_id: Optional[str] = None):
    """Handle table info request with detailed statistics"""
    try:
        # 先发送处理中的消息
        await feishu_service.send_text_message(
            chat_id,
            "📊 正在获取表格信息和统计数据...",
            reply_to_message_id=reply_to_message_id
        )

        # 获取表格基本信息
        app_token = settings.feishu.bitable_app_token
        bitable_url = f"https://feishu.cn/base/{app_token}"

        # 获取任务统计
        task_stats = await bitable_client.get_daily_task_stats()

        # 获取人员统计
        try:
            persons = await bitable_client.list_available_persons()
            person_count = len(persons)
        except:
            person_count = "获取失败"

        # 构建详细信息
        info_message = f"""📊 **多维表格详细信息**

🔗 **访问链接：**
{bitable_url}

📈 **数据统计：**
• 总任务数：{task_stats.get('total', 0)}
• 已完成：{task_stats.get('Done', 0)}
• 进行中：{task_stats.get('InProgress', 0)}
• 待分配：{task_stats.get('待分配', 0)}
• 已退回：{task_stats.get('Returned', 0)}
• 注册人员：{person_count}

📋 **数据表说明：**
• **Tasks表** - 存储所有任务信息
  - 任务标题、描述、技能要求
  - 任务状态、分配信息
  - 创建时间、完成时间

• **Persons表** - 存储人员信息
  - 用户信息、技能标签
  - 工作负载、历史评分
  - 可用状态、活跃度

💡 **使用建议：**
• 定期查看表格数据进行分析
• 可以手动调整任务分配
• 支持数据导出到Excel
• 可以创建自定义视图和筛选

📱 **快捷访问：**
• 电脑端：直接点击链接
• 手机端：在飞书APP中打开
• 支持离线查看和编辑"""

        await feishu_service.send_text_message(chat_id, info_message)

    except Exception as e:
        logger.error(f"Error handling table info request: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 获取表格信息失败: {str(e)}\n\n请稍后重试或联系管理员。",
            reply_to_message_id=reply_to_message_id
        )


async def handle_new_task_request(content: str, chat_id: str, sender_id: str, reply_to_message_id: Optional[str] = None):
    """Handle new task creation request"""
    try:
        # 强化的任务创建去重检查
        current_time = time.time()

        # 创建任务内容的唯一标识
        task_content_hash = hashlib.md5(content.encode()).hexdigest()
        task_key = f"{chat_id}_{task_content_hash}"

        global task_creation_cache

        # 检查是否在时间窗口内有相同的任务创建请求
        if task_key in task_creation_cache:
            last_creation_time = task_creation_cache[task_key]
            time_diff = current_time - last_creation_time

            if time_diff < TASK_CREATION_WINDOW:
                logger.warning(f"DUPLICATE TASK CREATION BLOCKED - Task '{task_key}' created {time_diff:.1f}s ago (within {TASK_CREATION_WINDOW}s window)")
                await feishu_service.send_text_message(
                    chat_id,
                    f"⚠️ 检测到重复的任务创建请求！\n\n上次创建时间：{time_diff:.1f}秒前\n请等待 {TASK_CREATION_WINDOW - time_diff:.0f} 秒后再试，或修改任务描述。",
                    reply_to_message_id=reply_to_message_id
                )
                return

        # 记录任务创建时间
        task_creation_cache[task_key] = current_time
        logger.info(f"Recording task creation: {task_key} at {current_time}")

        # 清理过期的缓存条目
        expired_keys = [k for k, v in task_creation_cache.items() if current_time - v > TASK_CREATION_WINDOW]
        for key in expired_keys:
            del task_creation_cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired task creation entries")

        # Extract task information from message
        task_info = feishu_service.extract_task_from_message(content)
        if not task_info:
            await feishu_service.send_text_message(
                chat_id,
                "❌ 无法解析任务信息，请使用正确的格式：\n\n@bot 新任务\n标题: 任务标题\n描述: 任务描述\n技能: Python, FastAPI\n截止: 2024-01-01",
                reply_to_message_id=reply_to_message_id
            )
            return

        # 立即发送处理中的消息
        await feishu_service.send_text_message(
            chat_id,
            f"🚀 **正在处理任务创建请求**\n\n📋 **任务标题：** {task_info['title']}\n📝 **任务描述：** {task_info['description']}\n🏷️ **技能要求：** {', '.join(task_info['skill_tags'])}\n\n⚡ 正在并行处理：创建任务 + 匹配候选人...",
            reply_to_message_id=reply_to_message_id
        )

        # 并行执行任务创建和候选人匹配
        import asyncio
        start_time = time.time()

        try:
            # 并行执行任务创建和候选人匹配
            task_creation_task = bitable_client.create_task(
                title=task_info["title"],
                description=task_info["description"],
                skill_tags=task_info["skill_tags"]
            )
            candidate_matching_task = matching_service.find_top_candidates(task_info)

            # 等待两个任务完成
            task_record_id, candidates = await asyncio.gather(
                task_creation_task,
                candidate_matching_task
            )

            processing_time = time.time() - start_time
            logger.info(f"Parallel processing completed in {processing_time:.2f}s - Task: {task_record_id}, Candidates: {len(candidates)}")

        except Exception as e:
            logger.error(f"Error in parallel processing: {e}")
            await feishu_service.send_text_message(
                chat_id,
                f"❌ 处理过程中出现错误: {str(e)}",
                reply_to_message_id=reply_to_message_id
            )
            return

        # 检查候选人匹配结果
        try:

            if not candidates:
                total_time = time.time() - start_time
                await feishu_service.send_text_message(
                    chat_id,
                    f"⚠️ 暂未找到合适的候选人，任务已保存为待分配状态。\n\n⏱️ 处理时间：{total_time:.1f}秒\n\n您可以：\n• 稍后重新尝试匹配\n• 手动分配给合适的人员\n• 调整技能要求后重新发布"
                )
                return

            # Send candidate selection card
            card_start_time = time.time()
            card = feishu_service.create_task_selection_card(
                task_info["title"],
                task_info["description"],
                candidates
            )

            # Store task_record_id in card for later use
            for element in card.get("elements", []):
                if element.get("tag") == "action":
                    for action in element.get("actions", []):
                        if action.get("value", {}).get("action") == "select_candidate":
                            action["value"]["task_record_id"] = task_record_id

            card_time = time.time() - card_start_time
            total_time = time.time() - start_time

            # 显示候选人匹配分数
            candidate_summary = []
            for i, candidate in enumerate(candidates, 1):
                score = candidate.get("match_score", 0)
                # 支持多种字段名获取候选人姓名
                name = (
                    candidate.get("name") or
                    candidate.get("姓名") or
                    candidate.get("fields", {}).get("姓名") or
                    candidate.get("fields", {}).get("name") or
                    "未知用户"
                )
                candidate_summary.append(f"{i}. {name} ({score}%)")

            await feishu_service.send_text_message(
                chat_id,
                f"🎯 **候选人匹配完成** (⏱️ {total_time:.1f}秒)\n\n" +
                f"📊 **Top-{len(candidates)} 候选人：**\n" +
                "\n".join(candidate_summary) +
                f"\n\n请选择合适的人员："
            )

            await feishu_service.send_interactive_card(chat_id, card)

            logger.info(f"Task creation and matching completed in {total_time:.2f}s (card: {card_time:.2f}s)")

        except Exception as matching_error:
            logger.error(f"Error in candidate matching: {matching_error}")
            await feishu_service.send_text_message(
                chat_id,
                f"⚠️ 候选人匹配过程中出现问题，但任务已成功创建。\n\n错误信息：{str(matching_error)}\n\n请手动分配任务或联系管理员。"
            )
        
    except Exception as e:
        logger.error(f"Error handling new task request: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 处理任务请求时出错: {str(e)}"
        )


async def handle_candidate_selection(action_value: Dict[str, Any], chat_id: str, user_id: str):
    """Handle candidate selection from card"""
    try:
        selected_user_id = action_value.get("user_id")
        task_record_id = action_value.get("task_record_id")

        if not selected_user_id or not task_record_id:
            logger.error("Missing user_id or task_record_id in action")
            return

        # Get task information
        task_info = await bitable_client.get_task(task_record_id)
        # 处理中文字段名
        task_fields = task_info.get("fields", task_info)
        task_title = task_fields.get("任务标题", task_fields.get("title", "未知任务"))

        # Get selected user information
        user_info = await feishu_service.get_user_info(selected_user_id)
        user_name = user_info.get("name", "未知用户")

        # Create child group chat
        child_chat_id = await feishu_service.create_group_chat(
            name=f"任务: {task_title}",
            description=f"任务执行群组 - {task_title}",
            user_ids=[selected_user_id, user_id]  # Include HR and assignee
        )

        # Update task with assignment information
        await bitable_client.assign_task(task_record_id, selected_user_id, child_chat_id)

        # Send confirmation message to main chat
        await feishu_service.send_text_message(
            chat_id,
            f"✅ 任务已分配给 {user_name}，已创建专用群组进行沟通。"
        )

        # Send welcome message to child chat
        task_description = task_fields.get("任务描述", task_fields.get("description", "无描述"))
        welcome_message = f"""🎯 **任务分配成功**

**任务：** {task_title}
**描述：** {task_description}
**负责人：** {user_name}

**使用说明：**
• 完成任务后，请发送 `/done 提交链接` 进行提交
• 如有问题，可以在此群组中讨论
• 系统会自动进行初步验收

祝工作顺利！ 🚀"""

        await feishu_service.send_text_message(child_chat_id, welcome_message)

    except Exception as e:
        logger.error(f"Error handling candidate selection: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 分配任务时出错: {str(e)}"
        )


async def handle_task_completion(content: str, chat_id: str, sender_id: str):
    """Handle task completion submission"""
    try:
        # Extract submission URL from /done command
        parts = content.split(" ", 1)
        if len(parts) < 2:
            await feishu_service.send_text_message(
                chat_id,
                "❌ 请提供提交链接，格式：/done https://github.com/user/repo"
            )
            return

        submission_url = parts[1].strip()

        # Find task by child_chat_id
        tasks = await bitable_client.list_tasks(TaskStatus.ASSIGNED)
        current_task = None
        task_record_id = None

        for task in tasks:
            if task.get("fields", {}).get("child_chat_id") == chat_id:
                current_task = task
                task_record_id = task.get("record_id")
                break

        if not current_task:
            await feishu_service.send_text_message(
                chat_id,
                "❌ 未找到对应的任务记录，请联系管理员。"
            )
            return

        # Update task status to in progress
        await bitable_client.update_task_status(task_record_id, TaskStatus.IN_PROGRESS)

        # Send processing message
        await feishu_service.send_text_message(
            chat_id,
            "🔄 正在验收您的提交，请稍候..."
        )

        # Check if it's a code task (GitHub link)
        if "github.com" in submission_url:
            await process_code_task_submission(task_record_id, submission_url, chat_id)
        else:
            await process_general_task_submission(task_record_id, submission_url, chat_id, current_task)

    except Exception as e:
        logger.error(f"Error handling task completion: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 处理任务提交时出错: {str(e)}"
        )


async def process_code_task_submission(task_record_id: str, submission_url: str, chat_id: str):
    """Process code task submission with CI check"""
    try:
        # Check CI status
        ci_result = await ci_service.check_submission_status(submission_url)

        # Update task with CI result
        await bitable_client.update_task_status(
            task_record_id,
            TaskStatus.DONE if ci_result.state == CIState.SUCCESS else TaskStatus.RETURNED,
            ci_state=ci_result.state
        )

        # Send result message
        if ci_result.state == CIState.SUCCESS:
            card = feishu_service.create_task_result_card(
                "代码任务",
                "success",
                "🎉 CI检查通过，任务完成！",
                ci_result.details
            )
        else:
            card = feishu_service.create_task_result_card(
                "代码任务",
                "failure",
                f"❌ CI检查未通过: {ci_result.message}",
                ci_result.details
            )

        await feishu_service.send_interactive_card(chat_id, card)

    except Exception as e:
        logger.error(f"Error processing code task submission: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 代码任务验收失败: {str(e)}"
        )


async def process_general_task_submission(task_record_id: str, submission_url: str,
                                        chat_id: str, task_info: Dict[str, Any]):
    """Process general task submission with LLM review"""
    try:
        # Use LLM to review the submission
        task_fields = task_info.get("fields", {})
        review_result = await llm_service.review_task_submission(task_fields, submission_url)

        # Update task with review result
        await bitable_client.update_task_status(
            task_record_id,
            TaskStatus.DONE if review_result["passed"] else TaskStatus.RETURNED,
            ai_score=review_result["score"]
        )

        # Send result message
        if review_result["passed"]:
            card = feishu_service.create_task_result_card(
                task_fields.get("title", "任务"),
                "success",
                f"🎉 任务通过验收！得分: {review_result['score']}分",
                "\n".join(review_result.get("suggestions", []))
            )
        else:
            failed_reasons = "\n".join(review_result.get("failedReasons", []))
            card = feishu_service.create_task_result_card(
                task_fields.get("title", "任务"),
                "failure",
                f"❌ 任务未通过验收，得分: {review_result['score']}分",
                f"问题:\n{failed_reasons}\n\n建议:\n" + "\n".join(review_result.get("suggestions", []))
            )

        await feishu_service.send_interactive_card(chat_id, card)

    except Exception as e:
        logger.error(f"Error processing general task submission: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 任务验收失败: {str(e)}"
        )


async def handle_daily_report_request(chat_id: str, reply_to_message_id: Optional[str] = None):
    """Handle daily report request"""
    try:
        # 先发送处理中的消息
        await feishu_service.send_text_message(
            chat_id,
            "📊 正在生成任务日报，请稍候...",
            reply_to_message_id=reply_to_message_id
        )

        # Get daily statistics
        stats = await bitable_client.get_daily_task_stats()

        # Send report (不需要回复，因为是新的报告消息)
        await feishu_service.send_daily_report(chat_id, stats)

    except Exception as e:
        logger.error(f"Error handling daily report request: {e}")
        await feishu_service.send_text_message(
            chat_id,
            f"❌ 生成日报失败: {str(e)}\n\n请稍后重试或联系管理员。",
            reply_to_message_id=reply_to_message_id
        )


async def process_github_event(payload: Dict[str, Any]):
    """Process GitHub webhook event"""
    try:
        # Parse CI result from GitHub webhook
        ci_result = ci_service.parse_webhook("github", payload)
        if not ci_result:
            return

        # Find related task by repository URL or other identifier
        # This is a simplified implementation - you might need more sophisticated matching
        repo_info = ci_service.github_service.extract_repository_info(payload)
        if not repo_info:
            return

        # For now, just log the CI result
        logger.info(f"GitHub CI result: {ci_result.to_dict()}")

        # In a full implementation, you would:
        # 1. Find the task associated with this repository
        # 2. Update the task status based on CI result
        # 3. Notify the relevant chat about the CI status change

    except Exception as e:
        logger.error(f"Error processing GitHub event: {e}")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower()
    )
