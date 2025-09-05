import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Header
import hashlib
import hmac
import lark_oapi as lark
import threading
import asyncio
from app.config import settings
from app.services.task_manager import task_manager
from app.services.feishu import FeishuService
from app.bitable import BitableClient

bitable_client = BitableClient()

logger = logging.getLogger(__name__)

# 消息去重缓存 - 存储已处理的message_id
_processed_messages = set()
_max_cache_size = 1000  # 最大缓存大小

def _get_job_level_text(job_level) -> str:
    """将数字职级转换为可读文字"""
    try:
        level_mapping = {
            1: "初级",
            2: "中级", 
            3: "高级",
            4: "专家",
            5: "架构师"
        }
        # 如果是数字，直接转换
        if isinstance(job_level, (int, float)):
            return level_mapping.get(int(job_level), f"Level {job_level}")
        # 如果是字符串，可能已经是文字或数字字符串
        elif isinstance(job_level, str):
            try:
                level_num = int(job_level)
                return level_mapping.get(level_num, job_level)
            except ValueError:
                # 已经是文字，直接返回
                return job_level
        else:
            return str(job_level)
    except:
        return "未知"

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
feishu_service = FeishuService()

# 注意：setup_event_handler函数已被移除，因为它与handle_message_event重复
# 现在统一使用setup_websocket_client中的handle_message_event和handle_card_action_event

# 注意：handle_message_receive函数已被移除，因为它与handle_message_event重复
# 现在统一使用handle_message_event函数处理所有消息

# 注意：handle_card_action函数已被移除，因为它与handle_card_action_event重复
# 现在统一使用handle_card_action_event函数处理所有卡片交互

async def handle_task_command(user_id: str, command: str):
    """处理任务相关命令"""
    try:
        parts = command.split()
        if len(parts) < 2:
            await feishu_service.send_message(
                user_id=user_id,
                message="任务命令格式：/task <action> [参数]\n可用操作：list, status, submit"
            )
            return
        
        action = parts[1]
        
        if action == 'list':
            # 获取用户任务列表
            tasks = await task_manager.get_user_tasks(user_id)
            if tasks:
                task_list = "\n".join([f"- {task.get('title', 'Unknown')} ({task.get('status', 'Unknown')})" for task in tasks])
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"您的任务列表：\n{task_list}"
                )
            else:
                await feishu_service.send_message(
                    user_id=user_id,
                    message="您当前没有任务。"
                )
        
        elif action == 'status' and len(parts) > 2:
            # 获取特定任务状态
            task_id = parts[2]
            task = await task_manager.get_task_status(task_id)
            if task:
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"任务状态：\n标题：{task.get('title', 'Unknown')}\n状态：{task.get('status', 'Unknown')}\n截止时间：{task.get('deadline', 'Unknown')}"
                )
            else:
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"任务 {task_id} 不存在。"
                )
        
        else:
            await feishu_service.send_message(
                user_id=user_id,
                message="未知的任务命令。发送 /help 查看帮助。"
            )
    
    except Exception as e:
        logger.error(f"Error handling task command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理命令时出错，请稍后重试。"
        )

# 统一消息发送函数：优先发送到群聊，没有群聊则发送私聊
async def send_smart_message(user_id: str, message: str, chat_id: str = None):
    """智能消息发送：群聊优先，私聊兜底"""
    if chat_id and chat_id != user_id:
        # 在群聊中回复
        return await feishu_service.send_message_to_chat(chat_id=chat_id, message=message)
    else:
        # 发送私聊消息
        return await feishu_service.send_message(user_id=user_id, message=message)

async def send_smart_card(user_id: str, card: Dict[str, Any], chat_id: str = None):
    """智能卡片发送：群聊优先，私聊兜底"""
    if chat_id and chat_id != user_id:
        # 在群聊中发送卡片
        return await feishu_service.send_card_message(chat_id=chat_id, card=card)
    else:
        # 发送私聊卡片
        return await feishu_service.send_card_message(user_id=user_id, card=card)

async def handle_help_command(user_id: str, chat_id: str = None):
    """处理帮助命令"""
    help_text = """
🤖 **飞书智能任务管理机器人** - 指令大全

═══════════════════════════════

🆕 **任务创建**
• `新任务 [描述]` - AI智能创建任务（推荐）
• `@机器人 新任务 [描述]` - 群聊中创建任务

📋 **任务管理**
• `/submit <任务ID> <链接> [备注]` - 提交任务作品
• `/done <提交链接>` - 快速提交当前任务
• `/status` - 查看个人状态统计
• `/status <任务ID>` - 查看任务详情
• `/mytasks` - 查看我的任务列表

📊 **任务查询**
• `/tasks` - 查看所有任务（支持翻页删除）
• `/task table` - 查看任务表格详情
• `/report` 或 `#report` - 生成每日统计报告

🔍 **任务监测**
• `/monitor` - 任务监测系统（查看帮助）
• `/monitor test` - 测试监测功能
• `/monitor start` - 启动自动监测
• `/monitor stop` - 停止自动监测
• `/monitor status` - 查看监测状态

🧪 **测试功能**
• `/testgroup` - 测试群聊创建（查看帮助）
• `/testgroup create` - 创建测试群聊
• `/testgroup create <群名称>` - 创建指定名称的测试群聊

👥 **候选人管理**
• `/candidates` - 查看候选人（默认按经验排序）
• `/candidates sort=skills` - 按技能数量排序
• `/candidates sort=score` - 按平均评分排序  
• `/candidates sort=tasks` - 按完成任务数排序
• `/candidates page=2` - 翻页查看
• `/coders` - 同 `/candidates`（别名）
• **📄 上传PDF简历** - 直接上传PDF文件自动分析录入

🗃️ **数据管理**
• `/table` - 查看候选人表格详情
• `/bitable` - 多维表格操作
• `/bitable table list` - 查看所有表格
• `/bitable record list <表ID>` - 查看记录

💡 **快速示例**

**创建任务：**
```
新任务 开发用户登录API接口，需要支持手机号和邮箱登录
```

**提交任务：**
```
/done https://github.com/user/repo/pull/123
/submit TASK001 https://github.com/project
```

**查看候选人：**
```
/candidates sort=score page=1
/coders sort=skills
```

**状态查询：**
```
/status                    # 查看个人状态
/status TASK001           # 查看任务状态
/mytasks                  # 查看我的任务
```

**任务监测：**
```
/monitor start            # 启动自动监测
/monitor test             # 测试监测功能
/monitor status           # 查看监测状态
```

**测试功能：**
```
/testgroup create         # 创建测试群聊
/testgroup create "项目讨论群"  # 创建指定名称的群聊
```

**简历上传：**
```
📎 直接上传PDF简历文件
→ AI自动解析姓名、技能、经验等信息
→ 自动录入到候选人数据库
```

🎯 **智能特性**
• ✅ AI自动分析任务需求和推荐候选人
• ✅ AI智能解析PDF简历，自动提取结构化信息
• ✅ GitHub代码任务自动CI检查
• ✅ 非代码任务AI智能评分
• ✅ 智能任务监测，周期过半自动提醒
• ✅ 一键创建测试群聊，便于功能测试
• ✅ 交互式卡片按钮操作
• ✅ 多维表格自动同步数据
• ✅ 支持分页浏览和多种排序

❓ **获取帮助**
• `/help` - 显示此帮助信息
• 联系管理员获取更多支持

═══════════════════════════════
⚡ 提示：大部分操作支持点击按钮交互，更便捷！
📄 PDF简历：支持中英文简历，自动提取姓名、技能、经验等关键信息
    """
    
    await send_smart_message(user_id=user_id, message=help_text, chat_id=chat_id)

async def handle_done_command(user_id: str, command: str, chat_id: str = None):
    """处理任务完成提交命令"""
    try:
        # 解析命令格式: /done <提交链接>
        parts = command.strip().split(maxsplit=1)
        if len(parts) < 2:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 命令格式错误！\n\n正确格式：/done <提交链接>\n\n示例：\n/done https://github.com/user/repo/pull/123\n/done https://docs.google.com/document/d/xxx"
            )
            return
        
        submission_url = parts[1].strip()
        
        # 验证URL格式
        if not submission_url.startswith(('http://', 'https://')):
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 请提供有效的链接地址（需要以 http:// 或 https:// 开头）"
            )
            return
        
        # 查找用户当前进行中的任务
        user_tasks = await task_manager.get_user_tasks(user_id)
        active_tasks = [task for task in user_tasks if task.get('status') in ['assigned', 'in_progress']]
        
        if not active_tasks:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 您当前没有进行中的任务。请先接受任务后再提交。"
            )
            return
        
        # 如果有多个任务，选择最新的一个
        current_task = active_tasks[0]
        task_id = current_task.get('record_id') or current_task.get('id')
        
        if not task_id:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 无法找到任务ID，请联系管理员。"
            )
            return
        
        # 更新任务状态为已提交
        await task_manager.submit_task(task_id, user_id, submission_url)
        
        # 发送提交确认消息
        await feishu_service.send_message(
            user_id=user_id,
            message=f"✅ 任务提交成功！\n\n📋 任务：{current_task.get('title', 'Unknown')}\n🔗 提交链接：{submission_url}\n\n🤖 正在进行自动验收，请稍候..."
        )
        
        # 如果在子群中提交，也发送到子群
        if chat_id and chat_id != user_id:
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=f"✅ @{user_id} 已提交任务\n\n📋 任务：{current_task.get('title', 'Unknown')}\n🔗 提交链接：{submission_url}\n\n🤖 正在进行自动验收..."
            )
        
        # 触发自动验收流程
        await _trigger_auto_review(task_id, current_task, submission_url, user_id, chat_id)
        
    except Exception as e:
        logger.error(f"Error handling done command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ 处理提交时出错，请稍后重试或联系管理员。"
        )

async def _trigger_auto_review(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """触发自动验收流程"""
    try:
        from app.services.ci import ci_service
        
        # 判断任务类型
        task_type = _determine_task_type(task_data)
        
        if task_type == "code":
            # 代码任务：检查GitHub CI状态
            await _handle_code_task_review(task_id, task_data, submission_url, user_id, chat_id)
        else:
            # 非代码任务：使用LLM评分
            await _handle_non_code_task_review(task_id, task_data, submission_url, user_id, chat_id)
            
    except Exception as e:
        logger.error(f"Error in auto review: {str(e)}")
        # 降级到人工审核
        await feishu_service.send_message(
            user_id=user_id,
            message="⚠️ 自动验收出现问题，已转为人工审核。管理员会尽快处理。"
        )

def _determine_task_type(task_data: Dict[str, Any]) -> str:
    """判断任务类型"""
    try:
        description = task_data.get('description', '').lower()
        skill_tags = [tag.lower() for tag in task_data.get('skill_tags', [])]
        
        # 代码相关关键词
        code_keywords = ['代码', '编程', '开发', 'code', 'programming', 'development', 
                        'python', 'javascript', 'java', 'go', 'rust', 'c++', 'api',
                        'github', 'git', '仓库', 'repository', 'pull request', 'pr']
        
        # 检查描述和技能标签
        for keyword in code_keywords:
            if keyword in description or keyword in skill_tags:
                return "code"
        
        return "non_code"
        
    except Exception as e:
        logger.error(f"Error determining task type: {str(e)}")
        return "non_code"

async def _handle_code_task_review(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """处理代码任务的验收"""
    try:
        # 检查是否是GitHub链接
        if 'github.com' in submission_url:
            # 发送等待CI消息
            await feishu_service.send_message(
                user_id=user_id,
                message="🔄 检测到GitHub提交，正在等待CI检查结果...\n\n如果您的仓库配置了GitHub Actions，系统会自动获取CI状态。\n如果没有CI配置，将转为人工审核。"
            )
            
            # 模拟CI检查（实际环境中会通过webhook接收）
            import asyncio
            await asyncio.sleep(3)  # 模拟等待时间
            
            # 模拟CI结果（在实际环境中，这会通过GitHub webhook触发）
            await _simulate_ci_result(task_id, task_data, submission_url, user_id, chat_id)
        else:
            # 非GitHub链接，转为LLM评分
            await feishu_service.send_message(
                user_id=user_id,
                message="ℹ️ 非GitHub链接，转为AI评分模式..."
            )
            await _handle_non_code_task_review(task_id, task_data, submission_url, user_id, chat_id)
            
    except Exception as e:
        logger.error(f"Error in code task review: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ 代码任务验收出错，已转为人工审核。"
        )

async def _simulate_ci_result(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """模拟CI检查结果（用于演示）"""
    try:
        import random
        
        # 模拟CI结果（80%通过率）
        ci_passed = random.random() > 0.2
        
        if ci_passed:
            # CI通过
            await task_manager.complete_task(task_id, {
                'final_score': 95,
                'review_result': 'CI检查通过',
                'ci_state': 'passed'
            })
            
            success_msg = f"🎉 恭喜！您的代码任务已通过验收！\n\n📋 任务：{task_data.get('title', 'Unknown')}\n✅ CI检查：通过\n📊 评分：95分\n\n任务已完成，积分已发放！"
            
            await send_smart_message(user_id=user_id, message=success_msg, chat_id=chat_id)
        else:
            # CI失败
            failed_reasons = [
                "代码格式检查未通过",
                "单元测试失败",
                "代码覆盖率不足"
            ]
            
            await task_manager.reject_task(task_id, {
                'final_score': 45,
                'review_result': 'CI检查失败',
                'failed_reasons': failed_reasons,
                'ci_state': 'failed'
            })
            
            failure_msg = f"❌ 您的代码任务未通过验收\n\n📋 任务：{task_data.get('title', 'Unknown')}\n❌ CI检查：失败\n📊 评分：45分\n\n需要修改的问题：\n" + "\n".join([f"• {reason}" for reason in failed_reasons]) + "\n\n请修改后重新提交（您还有2次机会）。"
            
            await send_smart_message(user_id=user_id, message=failure_msg, chat_id=chat_id)
                
    except Exception as e:
        logger.error(f"Error simulating CI result: {str(e)}")

async def _handle_non_code_task_review(task_id: str, task_data: Dict[str, Any], submission_url: str, user_id: str, chat_id: str = None):
    """处理非代码任务的LLM评分"""
    try:
        from app.services.ci import ci_service
        
        # 发送评分中消息
        await send_smart_message(
            user_id=user_id,
            message="🤖 AI正在评估您的提交内容，请稍候...",
            chat_id=chat_id
        )
        
        # 调用LLM评分
        description = task_data.get('description', '')
        acceptance_criteria = task_data.get('acceptance_criteria', '按照任务要求完成即可')
        
        score, failed_reasons = await ci_service.evaluate_submission(
            description=description,
            acceptance_criteria=acceptance_criteria,
            submission_url=submission_url
        )
        
        # 判断是否通过（阈值80分）
        if score >= 80:
            # 通过验收
            await task_manager.complete_task(task_id, {
                'final_score': score,
                'review_result': 'AI评分通过',
                'ai_score': score
            })
            
            success_msg = f"🎉 恭喜！您的任务已通过验收！\n\n📋 任务：{task_data.get('title', 'Unknown')}\n🤖 AI评分：{score}分\n✅ 状态：通过\n\n任务已完成，积分已发放！"
            
            await send_smart_message(user_id=user_id, message=success_msg, chat_id=chat_id)
        else:
            # 未通过验收
            await task_manager.reject_task(task_id, {
                'final_score': score,
                'review_result': 'AI评分未通过',
                'failed_reasons': failed_reasons,
                'ai_score': score
            })
            
            failure_msg = f"❌ 您的任务未通过验收\n\n📋 任务：{task_data.get('title', 'Unknown')}\n🤖 AI评分：{score}分\n❌ 状态：需要修改\n\n需要改进的地方：\n" + "\n".join([f"• {reason}" for reason in failed_reasons]) + "\n\n请根据建议修改后重新提交（您还有2次机会）。"
            
            await send_smart_message(user_id=user_id, message=failure_msg, chat_id=chat_id)
                
    except Exception as e:
        logger.error(f"Error in non-code task review: {str(e)}")
        await send_smart_message(
            user_id=user_id,
            message="❌ AI评分出现问题，已转为人工审核。管理员会尽快处理。",
            chat_id=chat_id
        )

async def handle_status_command(user_id: str, command: str, chat_id: str = None):
    """处理个人状态查询命令"""
    try:
        # 获取用户的候选人详情
        candidate = await bitable_client.get_candidate_details(user_id)
        
        # 获取用户的任务信息
        user_tasks = await task_manager.get_user_tasks(user_id)
        
        if candidate:
            # 统计任务状态
            total_tasks = len(user_tasks) if user_tasks else 0
            pending_tasks = len([t for t in user_tasks if t.get('status') in ['pending', 'assigned']]) if user_tasks else 0
            in_progress_tasks = len([t for t in user_tasks if t.get('status') == 'in_progress']) if user_tasks else 0
            completed_tasks = len([t for t in user_tasks if t.get('status') == 'completed']) if user_tasks else 0
            
            # 构建状态信息
            skill_tags = candidate.get('skill_tags', [])
            skills_text = ', '.join(skill_tags[:5]) + ('...' if len(skill_tags) > 5 else '') if skill_tags else '暂无'
            
            status_text = f"""👤 **个人状态概览**

**基本信息**
• 姓名：{candidate.get('name', 'Unknown')}
• 用户ID：{user_id}
• 职级：{_get_job_level_text(candidate.get('job_level', 1))}
• 工作经验：{candidate.get('experience', 0)}年

**技能概况**
• 技能标签：{skills_text}
• 技能数量：{len(skill_tags)}个

**任务统计**
• 总任务数：{total_tasks}
• 待处理：{pending_tasks}
• 进行中：{in_progress_tasks}
• 已完成：{completed_tasks}

**绩效评估**
• 完成任务数：{candidate.get('total_tasks', 0)}
• 平均评分：{candidate.get('average_score', 0)}分
• 可用时间：{candidate.get('hours_available', 0)}小时/周

---
💡 使用 `/mytasks` 查看详细任务列表
💡 使用 `/status <任务ID>` 查看特定任务状态"""
        else:
            status_text = """❌ **个人信息未找到**

您的个人信息不在候选人数据库中，可能的原因：
• 您尚未注册为候选人
• 个人信息正在审核中
• 数据库访问出现问题

请联系管理员进行处理。"""
        
        await send_smart_message(user_id=user_id, message=status_text, chat_id=chat_id)
    
    except Exception as e:
        logger.error(f"Error handling status command: {str(e)}")
        await send_smart_message(
            user_id=user_id,
            message="❌ 获取状态信息时出错，请稍后重试或联系管理员。",
            chat_id=chat_id
        )

async def handle_table_command(user_id: str, command: str, chat_id: str = None):
    """处理表格查询命令"""
    try:
        # 解析命令参数
        parts = command.split()
        table_id = None
        
        # 如果指定了表格ID，则使用指定的表格
        if len(parts) > 1:
            table_id = parts[1]
        
        # 获取表格信息
        table_info = await bitable_client.get_table_info(table_id=table_id)
        
        if 'error' in table_info:
            await send_smart_message(
                user_id=user_id,
                message=f"获取表格信息失败: {table_info['error']}",
                chat_id=chat_id
            )
            return
        
        # 构建表格信息文本
        fields = table_info.get('fields', [])
        if fields:
            fields_info = "\n".join([f"- {field.get('field_name', field.get('name', 'Unknown'))}: {field.get('type', 'Unknown')}" for field in fields])
        else:
            fields_info = "无字段信息"
            
        # 打印表格信息，便于调试
        logger.info(f"表格信息: {table_info}")
        logger.info(f"字段信息: {fields}")
        logger.info(f"记录数量: {len(table_info.get('records', []))}")
        logger.info(f"总记录数: {table_info.get('total_records', 0)}")
        
        
        # 构建记录信息（最多显示5条记录）
        records = table_info.get('records', [])
        records_preview = []
        
        for i, record in enumerate(records[:5]):
            record_fields = record.get('fields', {})
            # 打印记录字段内容，便于调试
            logger.info(f"记录 {i+1} 字段内容: {record_fields}")
            
            # 格式化记录字段
            field_items = []
            for k, v in record_fields.items():
                # 处理不同类型的值
                if isinstance(v, dict):
                    # 如果值是字典，尝试提取有用信息
                    if 'text' in v:
                        field_items.append(f"{k}: {v['text']}")
                    else:
                        field_items.append(f"{k}: {str(v)}")
                elif isinstance(v, list):
                    # 如果值是列表，尝试将其连接起来
                    list_values = []
                    for item in v:
                        if isinstance(item, dict) and 'text' in item:
                            list_values.append(item['text'])
                        else:
                            list_values.append(str(item))
                    field_items.append(f"{k}: {', '.join(list_values)}")
                else:
                    field_items.append(f"{k}: {v}")
            
            field_text = ", ".join(field_items)
            records_preview.append(f"记录 {i+1}: {field_text}")
        
        records_text = "\n".join(records_preview)
        
        if len(records) > 5:
            records_text += f"\n... 还有 {len(records) - 5} 条记录未显示"
        
        table_text = f"""
📋 表格信息

表格ID: {table_info.get('table_id', 'Unknown')}
记录总数: {table_info.get('total_records', 0)}

字段列表:
{fields_info}

记录预览:
{records_text}
        """
        
        await send_smart_message(
            user_id=user_id,
            message=table_text,
            chat_id=chat_id
        )
    
    except Exception as e:
        logger.error(f"Error handling table command: {str(e)}")
        await send_smart_message(
            user_id=user_id,
            message="查询表格信息时出错，请稍后重试。",
            chat_id=chat_id
        )

async def handle_task_table_command(user_id: str, command: str, chat_id: str = None):
    """处理任务表格查询命令"""
    try:
        # 获取task表格信息
        table_info = await bitable_client.get_task_table_info()
        
        if 'error' in table_info:
            await send_smart_message(
                user_id=user_id,
                message=f"❌ 获取任务表格信息失败: {table_info['error']}",
                chat_id=chat_id
            )
            return
        
        # 构建表格信息文本
        fields = table_info.get('fields', [])
        if fields:
            fields_info = "\n".join([f"- {field.get('field_name', field.get('name', 'Unknown'))}: {field.get('type', 'Unknown')}" for field in fields])
        else:
            fields_info = "无字段信息"
        
        # 获取示例记录
        sample_records = table_info.get('sample_records', [])
        records_preview = []
        
        for i, record in enumerate(sample_records):
            record_fields = record.get('fields', {})
            if record_fields:
                # 格式化任务记录字段
                field_items = []
                
                # 按照task表的字段顺序显示
                task_fields_order = ['taskid', 'title', 'description', 'creator', 'create_time', 'status', 'skilltags', 'deadline', 'urgency']
                for field_name in task_fields_order:
                    if field_name in record_fields:
                        value = record_fields[field_name]
                        # 限制描述字段的长度
                        if field_name == 'description' and len(str(value)) > 50:
                            value = str(value)[:50] + '...'
                        field_items.append(f"{field_name}: {value}")
                
                field_text = "\n    ".join(field_items)
                records_preview.append(f"任务 {i+1}:\n    {field_text}")
        
        records_text = "\n\n".join(records_preview) if records_preview else "暂无任务记录"
        
        if table_info.get('total_records', 0) > len(sample_records):
            records_text += f"\n\n... 还有 {table_info.get('total_records', 0) - len(sample_records)} 条记录未显示"
        
        task_table_text = f"""📋 **任务表格信息**

📊 **基本信息**:
• 表格ID: {table_info.get('table_id', 'Unknown')}
• 记录总数: {table_info.get('total_records', 0)}

🔧 **字段列表**:
{fields_info}

📝 **最近任务记录**:
{records_text}

---
💡 使用 "新任务 [描述]" 命令可自动创建任务记录到此表格"""
        
        await send_smart_message(
            user_id=user_id,
            message=task_table_text,
            chat_id=chat_id
        )
    
    except Exception as e:
        logger.error(f"Error handling task table command: {str(e)}")
        await send_smart_message(
            user_id=user_id,
            message="查询任务表格信息时出错，请稍后重试。",
            chat_id=chat_id
        )

def handle_message_event(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理接收到的消息事件"""
    try:
        # 获取消息内容
        message_content = data.event.message.content
        message_type = data.event.message.message_type
        sender_id = data.event.sender.sender_id.user_id
        chat_id = data.event.message.chat_id
        chat_type = data.event.message.chat_type
        message_id = data.event.message.message_id
        
        # 消息去重检查
        global _processed_messages, _max_cache_size
        if message_id in _processed_messages:
            logger.info(f"重复消息已跳过: {message_id}")
            return
        
        # 添加到已处理缓存
        _processed_messages.add(message_id)
        
        # 缓存大小控制：超过最大限制时，清理一半的旧消息
        if len(_processed_messages) > _max_cache_size:
            messages_to_remove = list(_processed_messages)[:_max_cache_size // 2]
            for msg_id in messages_to_remove:
                _processed_messages.discard(msg_id)
            logger.info(f"清理消息缓存，移除 {len(messages_to_remove)} 条旧消息")
        
        logger.info(f"收到长连接消息: {message_content} (chat_type: {chat_type}, message_id: {message_id})")
        
        # 处理文本消息
        if message_type == "text":
            import json
            content_dict = json.loads(message_content)
            text = content_dict.get("text", "")
            
            # 处理群聊消息：检查是否@了机器人或者是特定命令
            if chat_type == "group":
                mentions = getattr(data.event.message, 'mentions', [])
                # 确保mentions不为None，防止迭代错误
                if mentions is None:
                    mentions = []
                    
                bot_mentioned = False
                
                # 检查是否@了机器人
                for mention in mentions:
                    mention_id = mention.id
                    # 检查是否@了当前机器人
                    if mention_id.open_id or mention.name == "Bot":
                        bot_mentioned = True
                        # 移除@mention部分，只保留实际命令
                        mention_key = mention.key
                        if mention_key in text:
                            text = text.replace(mention_key, "").strip()
                        break
                
                # 群聊中：被@时处理所有消息，未被@时只处理特定命令
                if not bot_mentioned:
                    # 允许特定命令不需要@机器人
                    if not (text.startswith("新任务") or text.startswith("/")):
                        logger.info(f"Group message without mention ignored: {text}")
                        return
            
            # 异步处理文本命令
        # 处理文件消息（PDF简历）
        elif message_type == "file":
            import json
            content_dict = json.loads(message_content)
            file_key = content_dict.get("file_key", "")
            file_name = content_dict.get("file_name", "")
            
            # 检查是否为PDF文件
            if file_name.lower().endswith('.pdf'):
                logger.info(f"收到PDF简历文件: {file_name} (file_key: {file_key}, message_id: {message_id})")
                
                # 异步处理PDF简历分析，传递message_id
                import asyncio
                import concurrent.futures
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _process_resume_upload_sync(sender_id, file_key, file_name, chat_id, message_id))
                    future.result()
            else:
                # 非PDF文件，提示用户
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, feishu_service.send_message(
                        user_id=sender_id,
                        message="❌ 请上传PDF格式的简历文件。目前只支持PDF格式的简历分析。"
                    ))
                    future.result()
            return
        import asyncio
        import concurrent.futures
        
        # 使用线程池执行器来避免事件循环冲突
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _process_text_command_sync(sender_id, text, chat_id))
            future.result()
            
    except Exception as e:
        logger.error(f"处理长连接消息事件失败: {str(e)}")

def handle_card_action_event(data) -> dict:
    """处理卡片动作事件"""
    try:
        # 获取动作信息
        event = data.event
        action = event.action
        user_id = event.operator.user_id
        action_value = action.value  # 获取实际的动作值
        
        logger.info(f"收到长连接卡片动作: {action_value}")
        
        # 异步处理卡片动作
        import asyncio
        import concurrent.futures
        
        # 使用线程池执行器来避免事件循环冲突
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _handle_card_action_sync(user_id, action_value))
            future.result()
        
        # 返回响应
        return {
            "toast": {
                "type": "info",
                "content": "操作已处理"
            }
        }
        
    except Exception as e:
         logger.error(f"处理长连接卡片动作事件失败: {str(e)}")
         return {
             "toast": {
                 "type": "error",
                 "content": "处理失败"
             }
         }
 
# 全局变量防止重复启动
_websocket_client_started = False
_websocket_thread = None

def setup_websocket_client():
    """设置并启动飞书长连接客户端"""
    global _websocket_client_started, _websocket_thread
    
    # 防止重复启动
    if _websocket_client_started:
        logger.info("飞书长连接客户端已经启动，跳过重复启动")
        return
    
    import threading
    
    def run_websocket_client():
        """在单独线程中运行长连接客户端"""
        try:
            # 创建事件处理器
            event_handler = lark.EventDispatcherHandler.builder("", "") \
                .register_p2_im_message_receive_v1(handle_message_event) \
                .register_p2_card_action_trigger(handle_card_action_event) \
                .build()
            
            # 创建长连接客户端
            cli = lark.ws.Client(
                settings.feishu_app_id,
                settings.feishu_app_secret,
                event_handler=event_handler,
                log_level=lark.LogLevel.DEBUG if settings.debug else lark.LogLevel.INFO
            )
            
            logger.info("飞书长连接客户端已启动")
            
            # 启动客户端（这是一个阻塞调用）
            cli.start()
            
        except Exception as e:
            logger.error(f"启动飞书长连接客户端失败: {str(e)}")
            global _websocket_client_started
            _websocket_client_started = False  # 重置状态以允许重试
    
    try:
        # 创建并启动线程
        _websocket_thread = threading.Thread(target=run_websocket_client, daemon=True)
        _websocket_thread.start()
        _websocket_client_started = True
        
        logger.info("飞书长连接客户端线程已启动")
        
    except Exception as e:
        logger.error(f"启动飞书长连接客户端线程失败: {str(e)}")
        _websocket_client_started = False

# 已移除重复的卡片动作处理器，使用下面的统一版本

async def _process_text_command_sync(user_id: str, text: str, chat_id: str = None):
    """同步版本的文本命令处理（用于长连接事件）"""
    try:
        await _process_text_command(user_id, text, chat_id)
    except Exception as e:
        logger.error(f"处理文本命令时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理命令时出错，请稍后重试。"
        )

async def _process_resume_upload_sync(user_id: str, file_key: str, file_name: str, chat_id: str = None, message_id: str = None):
    """同步版本的PDF简历上传处理（用于长连接事件）"""
    try:
        await handle_resume_upload(user_id, file_key, file_name, chat_id, message_id)
    except Exception as e:
        logger.error(f"处理PDF简历上传时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ 处理简历时出错，请稍后重试。"
        )

async def _handle_card_action_sync(user_id: str, action_value: Dict[str, Any]):
    """同步版本的卡片交互处理（用于长连接事件）"""
    try:
        # 直接处理卡片动作，避免调用已停用的函数
        action_type = action_value.get("action")
        
        if action_type == "accept_task":
            task_id = action_value.get("task_id")
            success = await task_manager.accept_task(task_id, user_id)
            
            if success:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"✅ 您已成功接受任务 {task_id}，请开始执行！"
                )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"❌ 接受任务失败，任务可能已被其他人接受。"
                )
        
        elif action_type == "reject_task":
            task_id = action_value.get("task_id")
            await feishu_service.send_text_message(
                user_id=user_id,
                text=f"您已拒绝任务 {task_id}，感谢您的关注！"
            )
        
        elif action_type == "submit_task":
            task_id = action_value.get("task_id")
            await feishu_service.send_text_message(
                user_id=user_id,
                text=f"请提交任务 {task_id} 的完成链接，格式：/submit {task_id} <链接> [备注]"
            )
        
        elif action_type == "select_candidate":
            # 处理候选人选择
            await handle_candidate_selection(user_id, action_value)
        
        elif action_type == "tasks_page":
            # 处理任务列表翻页
            page = action_value.get("page", 0)
            await handle_tasks_list_command(user_id, "/tasks", None, page)
        
        elif action_type == "tasks_refresh":
            # 处理任务列表刷新
            page = action_value.get("page", 0)
            await handle_tasks_list_command(user_id, "/tasks", None, page)
        
        elif action_type == "delete_task":
            # 处理任务删除
            await handle_task_delete(user_id, action_value)
        
        elif action_type == "confirm_delete_task":
            # 处理确认删除任务
            await handle_confirm_delete_task(user_id, action_value)
        
        elif action_type == "cancel_delete_task":
            # 处理取消删除任务
            await feishu_service.send_message(
                user_id=user_id,
                message="✅ 已取消删除操作"
            )
        
        elif action_type == "candidates_page":
            # 处理候选人列表翻页
            sort_by = action_value.get("sort_by", "experience")
            page = action_value.get("page", 0)
            await handle_candidates_command(user_id, f"/candidates sort={sort_by} page={page + 1}")
        
        elif action_type == "candidates_sort":
            # 处理候选人列表排序
            sort_by = action_value.get("sort_by", "experience")
            page = action_value.get("page", 0)
            await handle_candidates_command(user_id, f"/candidates sort={sort_by} page={page + 1}")
        
        else:
            logger.info(f"未处理的卡片动作类型: {action_type}")
            
    except Exception as e:
        logger.error(f"处理卡片交互时出错: {str(e)}")

# HTTP Webhook路由已禁用，现在使用长连接处理所有事件
# 注意：_handle_feishu_event, _handle_feishu_message, _handle_feishu_card_action 等函数已停用
# 避免与长连接处理器重复处理消息

# GitHub Webhook路由已禁用，现在使用长连接处理所有事件

async def handle_workflow_run_event(data: dict):
    """处理工作流运行事件"""
    try:
        action = data.get('action')
        workflow_run = data.get('workflow_run', {})
        
        workflow_name = workflow_run.get('name', 'Unknown')
        status = workflow_run.get('status')
        conclusion = workflow_run.get('conclusion')
        
        logger.info(f"Workflow event: {action} - {workflow_name} ({status}/{conclusion})")
        
        # 使用CI服务处理工作流事件
        if action == 'completed':
            from app.services.ci import CIService
            ci_service = CIService()
            await ci_service.process_webhook_event({
                'type': 'workflow_run',
                'action': action,
                'workflow_run': workflow_run
            })
        
    except Exception as e:
        logger.error(f"Error handling workflow run event: {str(e)}")

async def handle_check_run_event(data: dict):
    """处理检查运行事件"""
    try:
        action = data.get('action')
        check_run = data.get('check_run', {})
        
        check_name = check_run.get('name', 'Unknown')
        status = check_run.get('status')
        conclusion = check_run.get('conclusion')
        
        logger.info(f"Check run event: {action} - {check_name} ({status}/{conclusion})")
        
        # 使用CI服务处理检查运行事件
        if action == 'completed':
            from app.services.ci import CIService
            ci_service = CIService()
            await ci_service.process_webhook_event({
                'type': 'check_run',
                'action': action,
                'check_run': check_run
            })
        
    except Exception as e:
        logger.error(f"Error handling check run event: {str(e)}")

async def handle_status_event(data: dict):
    """处理状态事件"""
    try:
        state = data.get('state')
        description = data.get('description', '')
        target_url = data.get('target_url', '')
        context = data.get('context', 'Unknown')
        
        logger.info(f"Status event: {context} - {state} ({description})")
        
        # 使用CI服务处理状态事件
        from app.services.ci import CIService
        ci_service = CIService()
        await ci_service.process_webhook_event({
            'type': 'status',
            'state': state,
            'description': description,
            'target_url': target_url,
            'context': context
        })
        
    except Exception as e:
        logger.error(f"Error handling status event: {str(e)}")

# 已停用：避免与长连接处理器重复处理
# async def _handle_feishu_event(event: Dict[str, Any]):
#     """处理Feishu事件 - 已停用，使用长连接处理器"""
#     pass

# 已停用：避免与长连接处理器重复处理
# async def _handle_feishu_message(event: Dict[str, Any]):
#     """处理Feishu消息事件 - 已停用，使用长连接处理器"""
#     pass

# 已停用：避免与长连接处理器重复处理
# async def _handle_feishu_card_action(event: Dict[str, Any]):
#     """处理Feishu卡片交互事件 - 已停用，使用长连接处理器"""
#     pass

# 已停用：避免与长连接处理器重复处理  
# async def _handle_feishu_bot_menu(event: Dict[str, Any]):
#     """处理Feishu机器人菜单事件 - 已停用，使用长连接处理器"""
#     pass

async def handle_bitable_command(user_id: str, text: str, chat_id: str = None):
    """处理多维表格操作命令"""
    try:
        parts = text.split(" ", 1)
        if len(parts) == 1:
            # 显示多维表格操作帮助
            help_text = """🗂️ 多维表格操作帮助

可用命令：
• /bitable table create <表名> - 创建新的数据表
• /bitable table list - 列出所有数据表
• /bitable field add <表ID> <字段名> <字段类型> - 添加字段
• /bitable record add <表ID> <字段1>=<值1> <字段2>=<值2>... - 添加记录
• /bitable record list <表ID> [过滤条件] - 查询记录

字段类型包括：text(文本), number(数字), select(单选), multiselect(多选), date(日期), checkbox(勾选), person(人员), attachment(附件)

示例：
/bitable table create 任务列表
/bitable field add tblzZiKqQH 任务名称 text
/bitable record add tblzZiKqQH 任务名称=测试任务 状态=进行中
/bitable record list tblzZiKqQH 状态=进行中"""
            
            await feishu_service.send_text_message(
                user_id=user_id,
                text=help_text,
                chat_id=chat_id
            )
            return
        
        command = parts[1].strip()
        
        # 移除了create和list命令，因为我们使用固定的应用token
        
        if command.startswith("table "):
            # 处理表格相关命令
            table_cmd = command[6:].strip()
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            
            if table_cmd.startswith("create "):
                # 创建数据表
                table_name = table_cmd[7:].strip()
                if not table_name:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="请提供表名，格式：/bitable table create <表名>",
                        chat_id=chat_id
                    )
                    return
                
                try:
                    table_id = await bitable_client.create_table(app_token, table_name)
                    if table_id:
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[成功] 数据表创建成功！\n表ID: {table_id}\n\n您可以使用以下命令添加字段：\n/bitable field add {table_id} <字段名> <字段类型>",
                            chat_id=chat_id
                        )
                    else:
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text="[失败] 创建数据表失败，请稍后重试。",
                            chat_id=chat_id
                        )
                except Exception as e:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[错误] 创建数据表出错：{str(e)}",
                        chat_id=chat_id
                    )
            
            elif table_cmd.startswith("list"):
                # 列出应用中的数据表
                try:
                    tables = await bitable_client.list_tables(app_token)
                    if tables and len(tables) > 0:
                        table_list = "\n".join([f"• {table['name']} - ID: {table['table_id']}" for table in tables])
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[列表] 数据表列表：\n{table_list}",
                            chat_id=chat_id
                        )
                    else:
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"暂无数据表，可使用 /bitable table create <表名> 创建",
                            chat_id=chat_id
                        )
                except Exception as e:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[错误] 获取数据表列表出错：{str(e)}",
                        chat_id=chat_id
                    )
        
        elif command.startswith("field add "):
            # 添加字段
            params = command[10:].strip().split(" ", 2)
            if len(params) != 3:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供正确的参数，格式：/bitable field add <表ID> <字段名> <字段类型>",
                    chat_id=chat_id
                )
                return
            
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            table_id, field_name, field_type = params
            try:
                field_id = await bitable_client.add_field(app_token, table_id, field_name, field_type)
                if field_id:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[成功] 字段添加成功！\n字段ID: {field_id}",
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="[失败] 添加字段失败，请稍后重试。",
                        chat_id=chat_id
                    )
            except Exception as e:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"[错误] 添加字段出错：{str(e)}",
                    chat_id=chat_id
                )
        
        elif command.startswith("record add "):
            # 添加记录
            parts = command[11:].strip().split(" ", 1)
            if len(parts) < 2:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供正确的参数，格式：/bitable record add <表ID> <字段1>=<值1> <字段2>=<值2>...",
                    chat_id=chat_id
                )
                return
            
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            table_id, fields_str = parts
            
            # 解析字段值对
            fields_data = {}
            field_pairs = fields_str.split(" ")
            for pair in field_pairs:
                if "=" in pair:
                    field_name, field_value = pair.split("=", 1)
                    fields_data[field_name] = field_value
            
            if not fields_data:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供至少一个字段值对，格式：字段名=值",
                    chat_id=chat_id
                )
                return
            
            try:
                record_id = await bitable_client.add_record(app_token, table_id, fields_data)
                if record_id:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"[成功] 记录添加成功！\n记录ID: {record_id}",
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="[失败] 添加记录失败，请稍后重试。",
                        chat_id=chat_id
                    )
            except Exception as e:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"[错误] 添加记录出错：{str(e)}",
                    chat_id=chat_id
                )
        
        elif command.startswith("record list "):
            # 查询记录
            parts = command[12:].strip().split(" ", 1)
            if len(parts) < 1:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="请提供正确的参数，格式：/bitable record list <表ID> [过滤条件]",
                    chat_id=chat_id
                )
                return
            
            app_token = settings.feishu_bitable_app_token  # 使用固定的应用token
            table_id = parts[0]
            filter_str = parts[1] if len(parts) > 1 else ""
            
            try:
                records = await bitable_client.list_records(app_token, table_id, filter_str)
                if records and len(records) > 0:
                    # 格式化记录显示
                    if len(records) > 10:
                        record_count = len(records)
                        records = records[:10]  # 只显示前10条
                        record_list = "\n\n".join([f"记录 {i+1}:\n" + "\n".join([f"  {k}: {v}" for k, v in record.items()]) for i, record in enumerate(records)])
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[记录] 查询到 {record_count} 条记录，显示前10条：\n{record_list}\n\n要查看更多记录，请添加更具体的过滤条件。",
                            chat_id=chat_id
                        )
                    else:
                        record_list = "\n\n".join([f"记录 {i+1}:\n" + "\n".join([f"  {k}: {v}" for k, v in record.items()]) for i, record in enumerate(records)])
                        await feishu_service.send_text_message(
                            user_id=user_id,
                            text=f"[记录] 查询到 {len(records)} 条记录：\n{record_list}",
                            chat_id=chat_id
                        )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text="未查询到符合条件的记录。",
                        chat_id=chat_id
                    )
            except Exception as e:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"[错误] 查询记录出错：{str(e)}",
                    chat_id=chat_id
                )
        
        else:
            # 未识别的多维表格命令
            await feishu_service.send_text_message(
                user_id=user_id,
                text="未识别的多维表格命令，请输入 /bitable 查看可用命令。",
                chat_id=chat_id
            )
    
    except Exception as e:
        logger.error(f"处理多维表格命令出错: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text=f"处理命令时出错: {str(e)}",
            chat_id=chat_id
        )

async def _process_text_command(user_id: str, text: str, chat_id: str = None):
    """处理文本命令"""
    try:
        text = text.strip()
        
        if text.startswith("/submit"):
            # 任务提交命令
            parts = text.split(" ", 3)
            if len(parts) >= 3:
                task_id = parts[1]
                submission_url = parts[2]
                submission_note = parts[3] if len(parts) > 3 else ""
                
                success = await task_manager.submit_task(
                    task_id=task_id,
                    user_id=user_id,
                    submission_url=submission_url,
                    submission_note=submission_note
                )
                
                if success:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"✅ 任务 {task_id} 提交成功，正在进行质量检查...",
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"❌ 任务提交失败，请检查任务ID和权限。",
                        chat_id=chat_id
                    )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="格式错误，请使用：/submit <任务ID> <链接> [备注]",
                    chat_id=chat_id
                )
        
        elif text.startswith("/status"):
            # 查看状态：个人状态或任务状态
            parts = text.split(" ", 1)
            if len(parts) > 1:
                # 查看特定任务状态
                task_id = parts[1]
                task = await task_manager.get_task_status(task_id)
                
                if task:
                    status_text = f"""📋 **任务状态详情**

**标题**：{task.get('title', 'N/A')}
**状态**：{task.get('status', 'N/A')}
**负责人**：{task.get('assignee', '未分配')}
**截止时间**：{task.get('deadline', 'N/A')}
**创建时间**：{task.get('created_at', 'N/A')}
**创建者**：{task.get('created_by', 'N/A')}"""
                    
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=status_text,
                        chat_id=chat_id
                    )
                else:
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=f"❌ 未找到任务 {task_id}，请检查任务ID是否正确。",
                        chat_id=chat_id
                    )
            else:
                # 查看个人状态统计
                await handle_status_command(user_id, text, chat_id)
        
        elif text.startswith("/mytasks"):
            # 查看我的任务
            tasks = await task_manager.get_user_tasks(user_id)
            if tasks:
                task_list = "\n".join([
                    f"• {task['title']} ({task['status']})"
                    for task in tasks[:10]
                ])
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text=f"您的任务列表：\n{task_list}",
                    chat_id=chat_id
                )
            else:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="您当前没有任务。",
                    chat_id=chat_id
                )
        
        elif text.startswith("/help"):
            # 显示帮助
            await handle_help_command(user_id, chat_id)
        
        elif text.startswith("/bitable"):
            # 处理多维表格操作命令
            await handle_bitable_command(user_id, text, chat_id)
            
        elif text.startswith("/table"):
            # 处理表格查询命令
            await handle_table_command(user_id, text, chat_id)
        
        elif text.startswith("/task"):
            # 任务相关命令
            if "table" in text.lower():
                await handle_task_table_command(user_id, text, chat_id)
            elif "list" in text.lower():
                await handle_tasks_list_command(user_id, text, chat_id)
            else:
                await handle_task_command(user_id, text)
        
        elif text.startswith("/tasks"):
            # 任务列表命令
            await handle_tasks_list_command(user_id, text, chat_id)
        
        elif text.startswith("/done"):
            # 处理任务完成提交命令
            await handle_done_command(user_id, text, chat_id)
        
        elif text.startswith("/report") or text.startswith("#report"):
            # 处理每日报告查询命令
            await handle_report_command(user_id, text, chat_id)
            
        elif text.startswith("/audit"):
            # 处理审计日志查询命令
            await handle_audit_command(user_id, text, chat_id)
            
        elif text.startswith("/monitor"):
            # 处理任务监测命令
            await handle_monitor_command(user_id, text, chat_id)
            
        elif text.startswith("/testgroup"):
            # 处理测试群聊创建命令
            await handle_test_group_command(user_id, text, chat_id)
            
        elif text.startswith("/candidates") or text.startswith("/coders"):
            # 处理候选人信息展示命令
            await handle_candidates_command(user_id, text, chat_id)
        
        elif ('@bot' in text and '新任务' in text) or text.startswith('新任务'):
            # 处理新任务命令
            await handle_new_task_command(user_id, text, chat_id)
        
        else:
            # 未识别的命令
            await feishu_service.send_text_message(
                user_id=user_id,
                text="未识别的命令，请输入 /help 查看可用命令。",
                chat_id=chat_id
            )
        
    except Exception as e:
        logger.error(f"Error processing text command: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text="处理命令时出错，请稍后重试。",
            chat_id=chat_id
        )

async def _handle_github_push(event_data: Dict[str, Any]):
    """处理GitHub推送事件"""
    try:
        repository = event_data.get("repository", {})
        commits = event_data.get("commits", [])
        pusher = event_data.get("pusher", {})
        
        repo_name = repository.get("full_name")
        branch = event_data.get("ref", "").replace("refs/heads/", "")
        
        # 这里可以根据提交信息自动创建或更新任务
        # 例如：检查提交消息中是否包含任务ID，自动关联
        
        logger.info(f"GitHub push to {repo_name}:{branch} with {len(commits)} commits")
        
    except Exception as e:
        logger.error(f"Error handling GitHub push: {str(e)}")

async def _handle_github_pull_request(event_data: Dict[str, Any]):
    """处理GitHub Pull Request事件"""
    try:
        action = event_data.get("action")
        pull_request = event_data.get("pull_request", {})
        repository = event_data.get("repository", {})
        
        pr_number = pull_request.get("number")
        pr_title = pull_request.get("title")
        repo_name = repository.get("full_name")
        
        # 这里可以根据PR事件自动更新任务状态
        # 例如：PR合并时自动标记任务为完成
        
        logger.info(f"GitHub PR {action}: {repo_name}#{pr_number} - {pr_title}")
        
    except Exception as e:
        logger.error(f"Error handling GitHub pull request: {str(e)}")

async def _handle_github_issues(event_data: Dict[str, Any]):
    """处理GitHub Issues事件"""
    try:
        action = event_data.get("action")
        issue = event_data.get("issue", {})
        repository = event_data.get("repository", {})
        
        issue_number = issue.get("number")
        issue_title = issue.get("title")
        repo_name = repository.get("full_name")
        
        # 这里可以根据Issue事件自动创建任务
        # 例如：新Issue创建时自动生成对应任务
        
        logger.info(f"GitHub Issue {action}: {repo_name}#{issue_number} - {issue_title}")
        
    except Exception as e:
        logger.error(f"Error handling GitHub issues: {str(e)}")

async def handle_new_task_command(user_id: str, text_content: str, chat_id: str = None):
    """处理@bot新任务命令"""
    try:
        # 提取任务描述（去除@bot 新任务前缀）
        task_description = text_content.replace('@bot', '').replace('新任务', '').strip()
        
        if not task_description:
            await feishu_service.send_message(
                user_id=user_id,
                message="请提供任务描述。格式：@bot 新任务 [任务描述]"
            )
            return
        
        # 获取所有候选人信息
        candidates = await bitable_client.get_all_candidates()
        
        # 确保candidates是列表类型，防止None导致迭代错误
        if candidates is None:
            candidates = []
        
        if not candidates:
            await feishu_service.send_message(
                user_id=user_id,
                message="暂无可用候选人信息。"
            )
            return
        
        # 调用DeepSeek生成表格形式的任务描述和候选人推荐
        from app.services.llm import llm_service
        
        # 构建候选人信息字符串
        candidates_info = "\n".join([
            f"- {c.get('name', '未知')}: 技能[{', '.join(c.get('skill_tags', []))}], "
            f"经验{c.get('experience_years', 0)}年, "
            f"可用时间{c.get('hours_available', 0)}小时/周, "
            f"评分{c.get('average_score', 0)}"
            for c in candidates
        ])
        
        # 构建DeepSeek提示词
        system_prompt = """你是一个专业的项目管理助手。请根据任务描述和候选人信息，生成符合多维表格格式的完整任务信息和推荐前三名最佳候选人。

请严格按照以下JSON格式返回，确保所有字段都符合task多维表格的要求：
{
  "task_record": {
    "taskid": "TASK + 当前时间戳",
    "title": "简洁明确的任务标题（不超过50字）",
    "description": "详细任务描述（包含具体要求和验收标准）",
    "creator": "创建者ID（将自动填入）",
    "create_time": "创建时间（YYYY-MM-DD HH:MM:SS格式）",
    "status": "pending（固定值）",
    "skilltags": "技能1,技能2,技能3（逗号分隔）",
    "deadline": "YYYY-MM-DD格式的截止日期",
    "urgency": "high/normal/low之一"
  },
  "task_analysis": {
    "estimated_hours": "预估工时（小时）",
    "difficulty_level": "简单/中等/困难",
    "priority_score": "优先级评分(1-10)",
    "requirements": ["需求点1", "需求点2"],
    "deliverables": ["交付物1", "交付物2"]
  },
  "top_candidates": [
    {
      "name": "候选人姓名",
      "match_score": 数字(0-100),
      "match_reason": "匹配理由",
      "skill_tags": ["技能列表"],
      "experience": "经验描述",
      "hours_available": 数字
    }
  ]
}

注意：请确保生成的信息完整、准确，便于直接录入多维表格。"""
        
        user_prompt = f"""任务描述：{task_description}

候选人信息：
{candidates_info}

请分析任务需求，生成结构化的任务信息，并从候选人中推荐前三名最佳人选。"""
        
        # 调用DeepSeek
        response = await llm_service.call_with_retry(user_prompt, system_prompt)
        
        # 解析DeepSeek返回的JSON
        import json
        import re
        try:
            # 处理可能被markdown代码块包裹的JSON
            json_text = response.strip()
            if json_text.startswith('```json') and json_text.endswith('```'):
                # 提取markdown代码块中的JSON
                json_text = re.sub(r'^```json\s*', '', json_text)
                json_text = re.sub(r'\s*```$', '', json_text)
            elif json_text.startswith('```') and json_text.endswith('```'):
                # 提取普通代码块中的JSON
                json_text = re.sub(r'^```\s*', '', json_text)
                json_text = re.sub(r'\s*```$', '', json_text)
            
            result = json.loads(json_text)
            task_record = result.get('task_record', {})
            task_analysis = result.get('task_analysis', {})
            top_candidates = result.get('top_candidates', [])
        except json.JSONDecodeError:
            logger.error(f"DeepSeek返回的不是有效JSON: {response}")
            await feishu_service.send_message(
                user_id=user_id,
                message="AI分析任务时出错，请稍后重试。"
            )
            return
        
        # 验证和完善task_record字段
        from datetime import datetime, timedelta
        
        # 生成任务ID
        if not task_record.get('taskid'):
            task_record['taskid'] = f"TASK{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 设置其他必要字段
        task_record['creator'] = user_id
        task_record['create_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task_record['status'] = 'pending'
        
        # 验证必要字段并设置默认值
        if not task_record.get('title'):
            task_record['title'] = task_description[:50] + '...' if len(task_description) > 50 else task_description
        if not task_record.get('description'):
            task_record['description'] = task_description
        if not task_record.get('skilltags'):
            task_record['skilltags'] = '通用'
        if not task_record.get('deadline'):
            task_record['deadline'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        if not task_record.get('urgency'):
            task_record['urgency'] = 'normal'
        
        # 设置task_analysis默认值
        task_analysis.setdefault('estimated_hours', 8)
        task_analysis.setdefault('difficulty_level', '中等')
        task_analysis.setdefault('priority_score', 5)
        task_analysis.setdefault('requirements', ['待确认'])
        task_analysis.setdefault('deliverables', ['待确认'])
        
        # 使用生成的任务ID
        task_id = task_record['taskid']
        
        # 保存任务记录到多维表格task表
        try:
            record_id = await bitable_client.create_task_in_table(task_record)
            if record_id:
                save_success = True
                save_message = f"✅ 任务已成功保存到多维表格\n📝 记录ID: {record_id}"
                logger.info(f"任务 {task_id} 已保存到task表，记录ID: {record_id}")
            else:
                save_success = False
                save_message = "❌ 保存到多维表格失败，请手动录入"
                logger.error(f"任务 {task_id} 保存失败")
        except Exception as e:
            save_success = False
            save_message = f"❌ 保存到多维表格出错: {str(e)}"
            logger.error(f"保存任务 {task_id} 时出错: {str(e)}")
        
        # 发送任务记录信息和分析结果到群聊
        if chat_id:
            # 构建多维表格格式的任务记录信息
            task_record_message = f"""📋 **多维表格任务记录**

**任务ID**: {task_record['taskid']}
**标题**: {task_record['title']}
**描述**: {task_record['description']}
**创建者**: {task_record['creator']}
**创建时间**: {task_record['create_time']}
**状态**: {task_record['status']}
**技能标签**: {task_record['skilltags']}
**截止时间**: {task_record['deadline']}
**紧急程度**: {task_record['urgency']}"""
            
            # 构建任务分析信息
            requirements_text = '、'.join(task_analysis['requirements'])
            deliverables_text = '、'.join(task_analysis['deliverables'])
            
            task_analysis_message = f"""🔍 **AI任务分析**

**预估工时**: {task_analysis['estimated_hours']}小时
**难度等级**: {task_analysis['difficulty_level']}
**优先级评分**: {task_analysis['priority_score']}/10
**具体需求**: {requirements_text}
**交付物**: {deliverables_text}"""
            
            # 发送任务记录信息
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=task_record_message
            )
            
            # 发送任务分析信息
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=task_analysis_message
            )
            
            # 发送前三名候选人推荐卡片（带选择按钮）
            if top_candidates:
                await _send_candidate_selection_card(
                    user_id=user_id,
                    task_id=task_id,
                    task_info=task_record,  # 传递task_record而不是task_info
                    candidates=top_candidates[:3],
                    chat_id=chat_id
                )
        
        # 给HR发送确认消息，包含完整的表格记录信息和保存状态
        hr_message = f"""✅ **AI任务分析完成！**

{save_message}

**📋 多维表格记录信息：**
• 任务ID: {task_record['taskid']}
• 标题: {task_record['title']}
• 描述: {task_record['description']}
• 创建者: {task_record['creator']}
• 创建时间: {task_record['create_time']}
• 状态: {task_record['status']}
• 技能标签: {task_record['skilltags']}
• 截止时间: {task_record['deadline']}
• 紧急程度: {task_record['urgency']}

**🔍 AI分析结果：**
• 预估工时: {task_analysis['estimated_hours']}小时
• 难度等级: {task_analysis['difficulty_level']}
• 优先级: {task_analysis['priority_score']}/10

已发送分析结果到群聊并推荐了前三名候选人。"""
        
        await feishu_service.send_message(
            user_id=user_id,
            message=hr_message
        )
        
        # 根据保存状态记录日志
        save_status = "已保存到表格" if save_success else "保存失败"
        logger.info(f"AI任务分析完成: {task_id}, AI推荐了 {len(top_candidates)} 名候选人 ({save_status})")
        
        # 如果任务保存成功，增量更新统计数据
        if save_success:
            try:
                from app.services.task_manager import task_manager
                # 使用增量更新方法，传入任务紧急程度
                urgency = task_record.get('urgency', 'normal')
                await task_manager.increment_task_created(urgency=urgency)
                logger.info(f"任务创建后统计数据已增量更新: {task_id}, 紧急程度: {urgency}")
            except Exception as stats_error:
                logger.error(f"增量更新统计数据失败: {str(stats_error)}")
        
    except Exception as e:
        logger.error(f"处理新任务命令时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理新任务命令时出错，请稍后重试。"
        )

def _parse_new_task_text(text: str) -> Dict[str, Any]:
    """解析新任务文本"""
    try:
        # 移除@bot和新任务关键词
        text = text.replace('@bot', '').replace('新任务', '').strip()
        
        task_info = {}
        
        # 解析各个字段
        import re
        
        # 标题
        title_match = re.search(r'标题[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[描技截紧]|$)', text)
        if title_match:
            task_info['title'] = title_match.group(1).strip()
        
        # 描述
        desc_match = re.search(r'描述[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标技截紧]|$)', text)
        if desc_match:
            task_info['description'] = desc_match.group(1).strip()
        
        # 技能标签
        skill_match = re.search(r'技能[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标描截紧]|$)', text)
        if skill_match:
            skills = skill_match.group(1).strip()
            task_info['skill_tags'] = [s.strip() for s in skills.split(',') if s.strip()]
        
        # 截止时间
        deadline_match = re.search(r'截止[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标描技紧]|$)', text)
        if deadline_match:
            task_info['deadline'] = deadline_match.group(1).strip()
        
        # 紧急度
        urgency_match = re.search(r'紧急度[:：]([^\s]+(?:\s+[^\s]+)*?)(?=\s+[标描技截]|$)', text)
        if urgency_match:
            urgency_text = urgency_match.group(1).strip()
            urgency_map = {'高': 'high', '中': 'normal', '低': 'low', '紧急': 'urgent'}
            task_info['urgency'] = urgency_map.get(urgency_text, 'normal')
        
        # 验证必要字段
        required_fields = ['title', 'description', 'skill_tags', 'deadline']
        for field in required_fields:
            if field not in task_info or not task_info[field]:
                return None
        
        # 设置默认值
        task_info.setdefault('urgency', 'normal')
        task_info.setdefault('estimated_hours', 8)
        task_info.setdefault('reward_points', 100)
        
        return task_info
        
    except Exception as e:
        logger.error(f"解析新任务文本时出错: {str(e)}")
        return None

async def _send_candidate_selection_card(user_id: str, task_id: str, task_info: Dict[str, Any], candidates: List[Dict[str, Any]], chat_id: str = None):
    """发送候选人选择卡片"""
    try:
        # 构建候选人卡片
        card_elements = []
        
        # 任务信息 - 适配新的task_record格式
        skilltags = task_info.get('skilltags', '')
        if isinstance(skilltags, str):
            skill_display = skilltags
        else:
            skill_display = ', '.join(skilltags) if skilltags else '通用'
            
        card_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**新任务匹配结果**\n\n**任务**: {task_info['title']}\n**描述**: {task_info['description']}\n**技能要求**: {skill_display}\n**截止时间**: {task_info['deadline']}"
            }
        })
        
        # 分隔线
        card_elements.append({"tag": "hr"})
        
        # 候选人列表
        for i, candidate in enumerate(candidates, 1):
            match_score = candidate.get('match_score', 0)
            match_reason = candidate.get('match_reason', '无')
            
            candidate_info = f"**候选人 {i}**: {candidate.get('name', '未知')}\n" \
                           f"**匹配度**: {match_score}%\n" \
                           f"**技能**: {', '.join(candidate.get('skill_tags', []))}\n" \
                           f"**可用时间**: {candidate.get('hours_available', 0)}小时\n" \
                           f"**匹配理由**: {match_reason}"
            
            card_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": candidate_info
                }
            })
            
            # 选择按钮
            card_elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": f"✅ 选择候选人{i}"
                    },
                    "type": "primary",
                    "value": {
                        "action": "select_candidate",
                        "task_id": task_id,
                        "candidate_id": candidate.get('user_id'),
                        "candidate_rank": i
                    }
                }]
            })
            
            if i < len(candidates):
                card_elements.append({"tag": "hr"})
        
        # 构建完整卡片
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "elements": card_elements
        }
        
        # 发送卡片
        await feishu_service.send_card_message(
            user_id=user_id,
            card=card,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"发送候选人选择卡片时出错: {str(e)}")

async def handle_candidate_selection(user_id: str, action_value: Dict[str, Any]):
    """处理候选人选择"""
    try:
        task_id = action_value.get('task_id')
        candidate_id = action_value.get('candidate_id')
        candidate_rank = action_value.get('candidate_rank', 1)
        
        if not task_id or not candidate_id:
            await feishu_service.send_message(
                user_id=user_id,
                message="选择候选人失败：缺少必要参数"
            )
            return
        
        # 获取完整的任务信息，用于在群聊中重复任务描述
        task_info = await bitable_client.get_task(task_id)
        if not task_info:
            await feishu_service.send_message(
                user_id=user_id,
                message=f"获取任务信息失败：{task_id}"
            )
            return
        
        # 创建任务小群
        chat_name = f"任务协作群-{task_id[:8]}"
        # 群成员：任务发起人 + 候选人 + 机器人（如果配置了的话）
        members = [user_id, candidate_id]
        
        # 如果配置了机器人用户ID，将机器人也添加到群聊中
        from app.config import settings
        if settings.feishu_bot_user_id:
            members.append(settings.feishu_bot_user_id)
        
        try:
            # 尝试创建群聊
            chat_id = await feishu_service.create_chat(chat_name, members)
            
            if chat_id:
                # 构建完整的任务描述消息
                skilltags = task_info.get('skilltags', '')
                if isinstance(skilltags, str):
                    skill_display = skilltags
                else:
                    skill_display = ', '.join(skilltags) if skilltags else '通用'
                
                task_description_message = f"""📋 **任务协作群详情**

**任务ID**: {task_info.get('taskid', task_id)}
**任务标题**: {task_info.get('title', '未知任务')}
**任务描述**: {task_info.get('description', '无描述')}
**技能要求**: {skill_display}
**截止时间**: {task_info.get('deadline', '未设置')}
**紧急程度**: {task_info.get('urgency', '普通')}
**创建者**: {task_info.get('creator', user_id)}

**选中候选人**: 候选人{candidate_rank}

---
🎯 **协作说明**：
• 请在此群中进行任务相关的沟通协作
• 可以直接@机器人获取帮助和状态更新
• 完成任务后请使用 `/done <提交链接>` 命令提交
"""
                
                # 发送任务详情到群聊
                await feishu_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=task_description_message
                )
                
                # 通知任务发起人
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"✅ 候选人选择成功！\n" \
                           f"已创建任务协作群：{chat_name}\n" \
                           f"群聊ID：{chat_id}"
                )
                
                # 通知被选中的候选人
                await feishu_service.send_message(
                    user_id=candidate_id,
                    message=f"🎯 恭喜！您被选中参与任务协作\n" \
                           f"任务ID：{task_id}\n" \
                           f"已为您创建任务协作群：{chat_name}\n" \
                           f"请查看群聊进行后续沟通。"
                )
                
            else:
                # 群聊创建失败，回退到原有逻辑
                await feishu_service.send_message(
                    user_id=user_id,
                    message=f"候选人选择成功，但创建协作群失败。\n" \
                           f"任务ID：{task_id}\n" \
                           f"选中候选人：{candidate_id}\n" \
                           f"请手动联系候选人进行后续沟通。"
                )
                
        except Exception as chat_error:
            logger.error(f"创建任务协作群时出错: {str(chat_error)}")
            # 群聊创建失败，但候选人选择成功
            await feishu_service.send_message(
                user_id=user_id,
                message=f"候选人选择成功，但创建协作群时出现问题。\n" \
                       f"任务ID：{task_id}\n" \
                       f"选中候选人：{candidate_id}\n" \
                       f"请手动联系候选人进行后续沟通。"
            )
            
        # 记录选择日志
        logger.info(f"用户 {user_id} 为任务 {task_id} 选择了候选人 {candidate_id} (排名第{candidate_rank})")
        
        # 更新统计数据（候选人选择操作） - 这里只是刷新，不增加计数
        try:
            from app.services.task_manager import task_manager
            await task_manager._update_daily_stats()
            logger.info(f"候选人选择后统计数据已刷新: {task_id}")
        except Exception as stats_error:
            logger.error(f"刷新统计数据失败: {str(stats_error)}")
            
    except Exception as e:
        logger.error(f"处理候选人选择时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理候选人选择时发生错误，请稍后重试"
        )

def _verify_feishu_signature(body: bytes, headers: Dict[str, str]) -> bool:
    """验证Feishu请求签名"""
    try:
        # 签名验证已简化，生产环境请实现完整验证逻辑
        return True
    except Exception as e:
        logger.error(f"Error verifying Feishu signature: {str(e)}")
        return False

def _verify_github_signature(body: bytes, signature: str) -> bool:
    """验证GitHub请求签名"""
    try:
        if not signature or not settings.github_webhook_secret:
            return False
        
        # GitHub使用HMAC-SHA256签名
        expected_signature = hmac.new(
            settings.github_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # 签名格式：sha256=<hash>
        if signature.startswith("sha256="):
            provided_signature = signature[7:]
            return hmac.compare_digest(expected_signature, provided_signature)
        
        return False
        
    except Exception as e:
        logger.error(f"Error verifying GitHub signature: {str(e)}")
        return False

async def handle_report_command(user_id: str, text: str, chat_id: str = None):
    """处理 /report 和 #report 命令"""
    try:
        # 生成每日报告
        report = await task_manager.generate_daily_report()
        
        # 获取审计日志统计
        try:
            from app.services.db_audit import audit_logger
            audit_stats = audit_logger.get_daily_stats()
            report['audit_stats'] = audit_stats
        except Exception as audit_error:
            logger.error(f"获取审计统计失败: {str(audit_error)}")
            report['audit_stats'] = {"error": str(audit_error)}
        
        # 同时更新本地JSON文件
        await _update_local_stats(report)
        
        if not report:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 获取报告数据失败，请稍后重试"
            )
            return
        
        # 格式化报告消息
        report_text = _format_daily_report(report)
        
        # 发送报告
        if chat_id:
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=report_text
            )
        else:
            await feishu_service.send_message(
                user_id=user_id,
                message=report_text
            )
        
        logger.info(f"Daily report sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling report command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="生成报告时出错，请稍后重试"
        )

async def handle_audit_command(user_id: str, text: str, chat_id: str = None):
    """处理审计日志查询命令"""
    try:
        from app.services.db_audit import audit_logger
        
        # 解析命令参数
        parts = text.strip().split()
        command = parts[0]  # /audit
        
        if len(parts) == 1:
            # 显示审计日志概要
            recent_operations = audit_logger.get_recent_operations(limit=10)
            daily_stats = audit_logger.get_daily_stats()
            
            if not recent_operations and daily_stats.get('total_operations', 0) == 0:
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="📊 暂无审计日志记录",
                    chat_id=chat_id
                )
                return
            
            # 格式化审计日志概要
            audit_text = f"""📊 **数据库操作审计日志**

📅 **今日统计** ({daily_stats.get('date', 'Unknown')}):
• 🔢 总操作数: {daily_stats.get('total_operations', 0)}
• ✅ 成功: {daily_stats.get('by_result', {}).get('success', 0)}
• ❌ 失败: {daily_stats.get('by_result', {}).get('failed', 0)}

📋 **操作类型分布**:"""
            
            by_type = daily_stats.get('by_type', {})
            for op_type, count in by_type.items():
                op_icon = {
                    'create': '➕',
                    'update': '📝',
                    'delete': '🗑️',
                    'read': '👁️'
                }.get(op_type, '📄')
                audit_text += f"\n• {op_icon} {op_type}: {count}次"
            
            # 最近操作记录
            if recent_operations:
                audit_text += f"\n\n🕒 **最近操作** (最新{len(recent_operations)}条):"
                for i, op in enumerate(recent_operations[-5:], 1):  # 只显示最新5条
                    timestamp = op.get('timestamp', '')[:19]  # 截取到秒
                    op_type = op.get('operation_type', 'unknown')
                    table = op.get('table', 'unknown')
                    result = '✅' if op.get('result') == 'success' else '❌'
                    user = op.get('user_id', 'system')[:10]  # 限制用户ID长度
                    
                    audit_text += f"\n{i}. {timestamp} {result} {op_type} {table} (by {user})"
            
            audit_text += f"""

💡 **使用提示**:
• `/audit recent` - 查看最近操作
• `/audit table <表名>` - 查看特定表操作
• `/audit stats` - 详细统计信息"""
            
        elif len(parts) >= 2:
            subcommand = parts[1].lower()
            
            if subcommand == "recent":
                # 显示最近操作
                limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20
                recent_operations = audit_logger.get_recent_operations(limit=limit)
                
                if not recent_operations:
                    audit_text = "📊 暂无最近操作记录"
                else:
                    audit_text = f"🕒 **最近{len(recent_operations)}条操作记录**:\n\n"
                    for i, op in enumerate(recent_operations, 1):
                        timestamp = op.get('timestamp', '')[:19]
                        op_type = op.get('operation_type', 'unknown')
                        table = op.get('table', 'unknown')
                        result = '✅' if op.get('result') == 'success' else '❌'
                        user = op.get('user_id', 'system')
                        record_id = op.get('record_id', '')[:10] if op.get('record_id') else ''
                        
                        audit_text += f"{i}. **{timestamp}**\n"
                        audit_text += f"   {result} {op_type.upper()} {table}"
                        if record_id:
                            audit_text += f" (ID: {record_id})"
                        audit_text += f"\n   用户: {user}\n\n"
            
            elif subcommand == "table" and len(parts) > 2:
                # 显示特定表操作
                table_name = parts[2]
                table_operations = audit_logger.get_operations_by_table(table_name, limit=20)
                
                if not table_operations:
                    audit_text = f"📊 表 '{table_name}' 暂无操作记录"
                else:
                    audit_text = f"📋 **表 '{table_name}' 操作记录** (最新{len(table_operations)}条):\n\n"
                    for i, op in enumerate(table_operations, 1):
                        timestamp = op.get('timestamp', '')[:19]
                        op_type = op.get('operation_type', 'unknown')
                        result = '✅' if op.get('result') == 'success' else '❌'
                        user = op.get('user_id', 'system')
                        
                        audit_text += f"{i}. {timestamp} {result} {op_type.upper()} (by {user})\n"
            
            elif subcommand == "stats":
                # 显示详细统计
                daily_stats = audit_logger.get_daily_stats()
                
                audit_text = f"""📊 **审计日志详细统计**

📅 **日期**: {daily_stats.get('date', 'Unknown')}
🔢 **总操作数**: {daily_stats.get('total_operations', 0)}

📋 **操作类型统计**:"""
                
                by_type = daily_stats.get('by_type', {})
                for op_type, count in by_type.items():
                    audit_text += f"\n• {op_type}: {count}次"
                
                audit_text += "\n\n🗃️ **表操作统计**:"
                by_table = daily_stats.get('by_table', {})
                for table, count in by_table.items():
                    audit_text += f"\n• {table}: {count}次"
                
                audit_text += "\n\n👥 **用户操作统计**:"
                by_user = daily_stats.get('by_user', {})
                for user, count in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5]:
                    audit_text += f"\n• {user}: {count}次"
                
                audit_text += f"\n\n✅ **成功率**: {daily_stats.get('by_result', {}).get('success', 0)}/{daily_stats.get('total_operations', 0)}"
                if daily_stats.get('total_operations', 0) > 0:
                    success_rate = (daily_stats.get('by_result', {}).get('success', 0) / daily_stats.get('total_operations', 0)) * 100
                    audit_text += f" ({success_rate:.1f}%)"
            
            else:
                audit_text = """❓ **审计日志命令帮助**

可用命令：
• `/audit` - 显示审计概要
• `/audit recent [数量]` - 最近操作记录
• `/audit table <表名>` - 特定表操作
• `/audit stats` - 详细统计信息

示例：
• `/audit recent 10`
• `/audit table task_table`"""
        
        else:
            audit_text = "❓ 无效的审计命令格式，使用 `/audit` 查看帮助"
        
        # 发送审计日志信息
        await feishu_service.send_text_message(
            user_id=user_id,
            text=audit_text,
            chat_id=chat_id
        )
        
        logger.info(f"Audit log query sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error handling audit command: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text="查询审计日志时出错，请稍后重试",
            chat_id=chat_id
        )

async def handle_monitor_command(user_id: str, text: str, chat_id: str = None):
    """处理任务监测命令"""
    try:
        from app.services.task_monitor import task_monitor
        
        # 解析命令参数
        parts = text.strip().split()
        command = parts[0]  # /monitor
        
        if len(parts) == 1:
            # 显示监测帮助信息
            help_text = """🔍 **任务监测系统**

📋 **可用命令**:
• `/monitor` - 显示帮助信息
• `/monitor test` - 测试监测功能（所有任务）
• `/monitor test <任务ID>` - 测试指定任务
• `/monitor start` - 启动自动监测
• `/monitor stop` - 停止自动监测
• `/monitor status` - 查看监测状态

🎯 **功能说明**:
• 自动监测进行中和已分配的任务
• 在任务周期过半时发送提醒
• 在任务临近截止时发送紧急提醒
• 支持多种日期格式解析

⚙️ **监测规则**:
• 周期过半提醒：进度达到50%时
• 紧急提醒：截止前24小时内
• 监测频率：每小时检查一次

示例：
• `/monitor test` - 测试所有符合条件的任务
• `/monitor test TASK123` - 测试特定任务"""
            
        elif len(parts) >= 2:
            subcommand = parts[1].lower()
            
            if subcommand == "test":
                # 测试监测功能
                task_id = parts[2] if len(parts) > 2 else None
                
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="🧪 开始测试任务监测功能，请稍候...",
                    chat_id=chat_id
                )
                
                test_result = await task_monitor.test_monitoring(task_id)
                
                if test_result['status'] == 'success':
                    help_text = f"""🧪 **任务监测测试结果**

📊 **测试概况**:
• 测试任务数: {test_result['tested_tasks']}
• 发送提醒数: {test_result['reminder_sent']}

📋 **任务详情**:"""
                    
                    if test_result['tasks_details']:
                        for i, task in enumerate(test_result['tasks_details'], 1):
                            status_icon = {
                                'checked': '✅',
                                'reminder_sent': '📨',
                                'missing_time_data': '⚠️',
                                'invalid_time_format': '❌',
                                'error': '🚨'
                            }.get(task.get('status'), '❓')
                            
                            help_text += f"\n{i}. {status_icon} **{task.get('title', '未知任务')}**"
                            help_text += f"\n   ID: {task.get('task_id', 'N/A')}"
                            help_text += f"\n   进度: {round(task.get('progress_ratio', 0) * 100, 1)}%"
                            
                            if task.get('time_remaining'):
                                days = task['time_remaining'] // 86400
                                hours = (task['time_remaining'] % 86400) // 3600
                                help_text += f"\n   剩余: {days}天{hours}小时"
                            
                            help_text += f"\n   状态: {task.get('status', 'unknown')}"
                            
                            if task.get('reminder_sent'):
                                help_text += "\n   📨 已发送测试提醒"
                            
                            help_text += "\n"
                    else:
                        help_text += "\n暂无符合条件的任务"
                    
                    help_text += f"""
💡 **说明**:
• 测试模式下，进度>30%的任务会收到测试提醒
• 实际运行时，进度>50%才会发送正式提醒
• 测试消息会标明"测试"字样"""
                
                else:
                    help_text = f"❌ 测试失败: {test_result.get('message', '未知错误')}"
            
            elif subcommand == "start":
                # 启动监测服务
                if task_monitor.monitoring:
                    help_text = "⚠️ 任务监测服务已在运行中"
                else:
                    # 在后台启动监测
                    asyncio.create_task(task_monitor.start_monitoring())
                    help_text = """✅ **任务监测服务已启动**

🔄 **监测设置**:
• 检查频率: 每小时
• 监测状态: 进行中、已分配
• 提醒时机: 周期过半、临近截止

📨 **提醒规则**:
• 50% 进度提醒: 发送给执行人和创建者
• 24小时紧急提醒: 发送紧急通知

💡 监测服务将在后台持续运行"""
            
            elif subcommand == "stop":
                # 停止监测服务
                await task_monitor.stop_monitoring()
                help_text = "🛑 **任务监测服务已停止**\n\n监测功能已关闭，如需重新启动请使用 `/monitor start`"
            
            elif subcommand == "status":
                # 查看监测状态
                monitoring_status = "🟢 运行中" if task_monitor.monitoring else "🔴 已停止"
                reminded_count = len(task_monitor.reminded_tasks)
                
                help_text = f"""📊 **任务监测状态**

🔄 **服务状态**: {monitoring_status}
⏰ **检查间隔**: {task_monitor.check_interval // 60} 分钟
📝 **已提醒任务**: {reminded_count} 个
🕒 **下次检查**: {'约 {}'.format(task_monitor.check_interval // 60) + ' 分钟后' if task_monitor.monitoring else '未定'}

💡 **功能状态**:
• 自动监测: {'✅ 开启' if task_monitor.monitoring else '❌ 关闭'}
• 提醒发送: {'✅ 正常' if task_monitor.monitoring else '⏸️ 暂停'}
• 错误恢复: ✅ 自动重试"""
            
            else:
                help_text = """❓ **未知的监测命令**

可用子命令:
• `test` - 测试监测功能
• `start` - 启动自动监测  
• `stop` - 停止自动监测
• `status` - 查看监测状态

使用 `/monitor` 查看完整帮助"""
        
        else:
            help_text = "❓ 无效的监测命令格式，使用 `/monitor` 查看帮助"
        
        # 发送监测信息
        await feishu_service.send_text_message(
            user_id=user_id,
            text=help_text,
            chat_id=chat_id
        )
        
        logger.info(f"Task monitor command sent to user {user_id}: {text}")
        
    except Exception as e:
        logger.error(f"Error handling monitor command: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text="处理监测命令时出错，请稍后重试",
            chat_id=chat_id
        )

async def handle_test_group_command(user_id: str, text: str, chat_id: str = None):
    """处理测试群聊创建命令"""
    try:
        # 解析命令参数
        parts = text.strip().split()
        command = parts[0]  # /testgroup
        
        if len(parts) == 1:
            # 显示帮助信息
            help_text = """🧪 **测试群聊创建功能**

📋 **可用命令**:
• `/testgroup` - 显示帮助信息
• `/testgroup create` - 创建测试群聊（包含你和机器人）
• `/testgroup create <群名称>` - 创建指定名称的测试群聊

🎯 **功能说明**:
• 创建包含指令发起人和机器人的新群聊
• 可以自定义群聊名称
• 用于测试群聊相关功能

示例：
• `/testgroup create` - 创建默认名称的测试群聊
• `/testgroup create "我的测试群"` - 创建指定名称的测试群聊

💡 **注意事项**:
• 机器人需要有创建群聊的权限
• 群聊创建后会自动发送欢迎消息"""
            
        elif len(parts) >= 2:
            subcommand = parts[1].lower()
            
            if subcommand == "create":
                # 创建测试群聊
                await feishu_service.send_text_message(
                    user_id=user_id,
                    text="🧪 开始创建测试群聊，请稍候...",
                    chat_id=chat_id
                )
                
                # 确定群聊名称
                if len(parts) > 2:
                    # 使用指定的群聊名称（去掉引号）
                    group_name = " ".join(parts[2:]).strip('"').strip("'")
                else:
                    # 使用默认名称
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%m%d_%H%M')
                    group_name = f"测试群聊_{timestamp}"
                
                # 准备群成员列表
                members = [user_id]  # 指令发起人
                
                # 添加机器人到群聊（如果配置了机器人用户ID）
                from app.config import settings
                feishu_bot_user_id = getattr(settings, 'feishu_bot_user_id', None)
                if feishu_bot_user_id:
                    members.append(feishu_bot_user_id)
                    logger.info(f"Adding bot {feishu_bot_user_id} to group members")
                else:
                    logger.warning("feishu_bot_user_id not configured, bot will not be added to group")
                
                # 创建群聊
                new_chat_id = await feishu_service.create_chat(
                    name=group_name,
                    members=members
                )
                
                if new_chat_id:
                    # 群聊创建成功
                    success_msg = f"""✅ **测试群聊创建成功！**

📋 **群聊信息**:
• 群聊名称: {group_name}
• 群聊ID: {new_chat_id}
• 成员数量: {len(members)}人

👥 **群成员**:
• 指令发起人: {user_id}
{f'• 机器人: {feishu_bot_user_id}' if feishu_bot_user_id else '• 机器人: 未配置用户ID'}

🎉 群聊已创建完成，可以开始测试群聊功能了！"""
                    
                    # 发送成功消息给用户
                    await feishu_service.send_text_message(
                        user_id=user_id,
                        text=success_msg,
                        chat_id=chat_id
                    )
                    
                    # 在新创建的群聊中发送欢迎消息
                    welcome_msg = f"""🎉 **欢迎来到测试群聊！**

这是一个用于测试机器人功能的群聊。

📋 **可以测试的功能**:
• 发送 "新任务 [描述]" 创建任务
• 使用 @机器人 进行交互
• 测试各种机器人指令
• 测试任务管理流程

🤖 **机器人功能**:
• 智能任务创建和管理
• 候选人推荐和选择
• 任务进度监测和提醒
• 数据统计和报告

💡 **使用提示**:
发送 "/help" 查看完整的指令列表和使用说明。

---
群聊创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
                    
                    # 延迟一下再发送欢迎消息，确保群聊完全创建好
                    import asyncio
                    await asyncio.sleep(2)
                    
                    await feishu_service.send_message_to_chat(
                        chat_id=new_chat_id,
                        message=welcome_msg
                    )
                    
                    help_text = f"""✅ 测试群聊创建完成！

群聊ID: {new_chat_id}
已在新群聊中发送欢迎消息。"""
                    
                else:
                    # 群聊创建失败 - 提供更详细的诊断信息
                    help_text = f"""❌ **测试群聊创建失败**

🔍 **诊断信息**:
• 尝试创建群聊: {group_name}
• 用户ID: {user_id}
• 用户ID格式: {'✅ 正确' if len(user_id) > 5 else '❌ 可能不正确'}
• 机器人用户ID: {feishu_bot_user_id if feishu_bot_user_id else '未配置'}
• 成员列表: {members}

🚨 **可能的原因**:
• 机器人缺少创建群聊的权限
• 用户ID格式不正确（需要完整的飞书用户ID）
• 网络连接问题
• 飞书API限制或配额问题

📋 **权限检查清单**:
1. ✅ 机器人是否有 `im:chat:readonly` 权限
2. ✅ 机器人是否有 `im:chat` 权限
3. ✅ 机器人是否有 `contact:user.id:readonly` 权限
4. ✅ 用户ID是否为有效的飞书用户ID

🔧 **解决建议**:
1. 检查机器人应用权限配置
2. 确认用户ID格式正确
3. 查看应用日志获取详细错误信息
4. 尝试使用其他用户测试

💡 **获取帮助**:
• 查看应用日志: 检查具体的API错误代码
• 联系管理员: 确认权限配置
• 飞书开发文档: https://open.feishu.cn/document/server-docs/group/chat/create"""
            
            else:
                help_text = """❓ **未知的群聊命令**

可用子命令:
• `create` - 创建测试群聊
• `create <群名称>` - 创建指定名称的测试群聊

使用 `/testgroup` 查看完整帮助"""
        
        else:
            help_text = "❓ 无效的群聊命令格式，使用 `/testgroup` 查看帮助"
        
        # 发送帮助信息
        await feishu_service.send_text_message(
            user_id=user_id,
            text=help_text,
            chat_id=chat_id
        )
        
        logger.info(f"Test group command handled for user {user_id}: {text}")
        
    except Exception as e:
        logger.error(f"Error handling test group command: {str(e)}")
        await feishu_service.send_text_message(
            user_id=user_id,
            text="处理群聊创建命令时出错，请稍后重试",
            chat_id=chat_id
        )

async def _update_local_stats(report_data: Dict[str, Any]):
    """更新本地统计文件"""
    try:
        import json
        import os
        from datetime import datetime
        
        stats_file = "daily_stats.json"
        
        # 准备统计数据
        stats = {
            "date": report_data.get('date', datetime.now().strftime('%Y-%m-%d')),
            "total_tasks": report_data.get('total_tasks', 0),
            "completed_tasks": report_data.get('completed_tasks', 0),
            "pending_tasks": report_data.get('pending_tasks', 0),
            "in_progress_tasks": report_data.get('in_progress_tasks', 0),
            "submitted_tasks": report_data.get('submitted_tasks', 0),
            "rejected_tasks": report_data.get('rejected_tasks', 0),
            "average_score": report_data.get('average_score', 0.0),
            "completion_rate": report_data.get('completion_rate', 0.0),
            "tasks_by_status": {
                "published": report_data.get('published_tasks', 0),
                "in_progress": report_data.get('in_progress_tasks', 0),
                "submitted": report_data.get('submitted_tasks', 0),
                "reviewing": report_data.get('reviewing_tasks', 0),
                "completed": report_data.get('completed_tasks', 0),
                "rejected": report_data.get('rejected_tasks', 0)
            },
            "top_performers": report_data.get('top_performers', []),
            "last_updated": datetime.now().isoformat()
        }
        
        # 写入文件
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Local stats updated: {stats_file}")
        
    except Exception as e:
        logger.error(f"Error updating local stats: {str(e)}")

def _format_daily_report(report: Dict[str, Any]) -> str:
    """格式化每日报告消息"""
    try:
        date = report.get('date', 'Unknown')
        total_tasks = report.get('total_tasks', 0)
        completed_tasks = report.get('completed_tasks', 0)
        pending_tasks = report.get('pending_tasks', 0)
        in_progress_tasks = report.get('in_progress_tasks', 0)
        submitted_tasks = report.get('submitted_tasks', 0)
        reviewing_tasks = report.get('reviewing_tasks', 0)
        rejected_tasks = report.get('rejected_tasks', 0)
        assigned_tasks = report.get('assigned_tasks', 0)
        average_score = report.get('average_score', 0)
        completion_rate = report.get('completion_rate', 0)
        
        # 今日数据
        today_created = report.get('today_created', 0)
        today_completed = report.get('today_completed', 0)
        
        # 紧急程度统计
        tasks_by_urgency = report.get('tasks_by_urgency', {})
        urgent_tasks = tasks_by_urgency.get('urgent', 0)
        high_tasks = tasks_by_urgency.get('high', 0)
        normal_tasks = tasks_by_urgency.get('normal', 0)
        low_tasks = tasks_by_urgency.get('low', 0)
        
        # Top performers
        top_performers = report.get('top_performers', [])
        
        # 数据库操作信息
        db_operations = report.get('database_operations', {})
        total_records = db_operations.get('total_records', 0)
        last_updated = db_operations.get('last_updated', 'Unknown')
        
        # 计算完成率百分比
        completion_percentage = completion_rate if completion_rate else 0
        
        # 构建完整的报告
        report_text = f"""📊 **每日任务管理统计报告**

📅 **报告日期**: {date}
⏰ **数据更新**: {last_updated[:19] if last_updated != 'Unknown' else 'Unknown'}

📈 **任务总览**:
• 📊 总任务数: {total_tasks}
• ✅ 已完成: {completed_tasks}
• 🔄 进行中: {in_progress_tasks}
• ⏳ 待处理: {pending_tasks}
• 📤 已提交: {submitted_tasks}
• 🔍 审核中: {reviewing_tasks}
• 📋 已分配: {assigned_tasks}
• ❌ 已拒绝: {rejected_tasks}

🎯 **绩效指标**:
• 📊 完成率: {completion_percentage:.1f}%
• ⭐ 平均评分: {average_score:.1f}分
• 🆕 今日新增: {today_created}个
• 🎉 今日完成: {today_completed}个

🚨 **优先级分布**:
• 🚨 紧急: {urgent_tasks}个
• 🔴 高优先级: {high_tasks}个
• 🟡 普通: {normal_tasks}个
• 🟢 低优先级: {low_tasks}个"""

        # 添加Top Performers信息
        if top_performers:
            report_text += f"\n\n🏆 **Top表现者**:"
            for i, performer in enumerate(top_performers, 1):
                name = performer.get('name', '未知')
                score = performer.get('score', 0)
                task_title = performer.get('task_title', '')[:30] + ('...' if len(performer.get('task_title', '')) > 30 else '')
                report_text += f"\n{i}. {name} - {score}分 ({task_title})"
        
        # 添加数据库操作信息
        audit_stats = report.get('audit_stats', {})
        audit_operations = audit_stats.get('total_operations', 0)
        audit_by_type = audit_stats.get('by_type', {})
        audit_by_result = audit_stats.get('by_result', {})
        
        report_text += f"""

🗄️ **数据库状态**:
• 📝 总记录数: {total_records}
• 💾 数据源: 飞书多维表格
• 🔄 同步状态: {'正常' if total_records > 0 else '异常'}

📊 **今日数据库操作审计**:
• 🔢 总操作数: {audit_operations}
• ✅ 成功操作: {audit_by_result.get('success', 0)}
• ❌ 失败操作: {audit_by_result.get('failed', 0)}"""

        # 添加操作类型统计
        if audit_by_type:
            report_text += "\n• 📋 操作类型:"
            for op_type, count in audit_by_type.items():
                op_icon = {
                    'create': '➕',
                    'update': '📝', 
                    'delete': '🗑️',
                    'read': '👁️'
                }.get(op_type, '📄')
                report_text += f"\n  {op_icon} {op_type}: {count}次"
        
        report_text += """

---
💡 本报告基于任务表实时数据生成
📈 数据每次操作后自动更新
🔍 包含完整的数据库操作审计"""
        
        return report_text
        
    except Exception as e:
        logger.error(f"Error formatting daily report: {str(e)}")
        return "❌ 报告格式化失败"

async def handle_tasks_list_command(user_id: str, command: str, chat_id: str = None, page: int = 0):
    """处理任务列表展示命令"""
    try:
        # 获取排序后的任务列表
        tasks_data = await bitable_client.get_all_tasks_sorted(page_size=5, page=page)
        
        if 'error' in tasks_data:
            await feishu_service.send_message(
                user_id=user_id,
                message=f"❌ 获取任务列表失败: {tasks_data['error']}"
            )
            return
        
        # 获取任务统计信息
        stats = await bitable_client.get_task_statistics()
        
        # 生成任务列表卡片
        await _send_tasks_list_card(
            user_id=user_id,
            tasks_data=tasks_data,
            stats=stats,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"Error handling tasks list command: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="获取任务列表时出错，请稍后重试。"
        )

async def _send_tasks_list_card(user_id: str, tasks_data: dict, stats: dict, chat_id: str = None):
    """发送任务列表卡片"""
    try:
        tasks = tasks_data.get('tasks', [])
        current_page = tasks_data.get('current_page', 0)
        total_pages = tasks_data.get('total_pages', 1)
        total_tasks = tasks_data.get('total_tasks', 0)
        has_next = tasks_data.get('has_next', False)
        has_prev = tasks_data.get('has_prev', False)
        
        # 构建卡片元素
        card_elements = []
        
        # 标题和统计信息
        if 'error' not in stats:
            stats_text = f"📊 **任务总览** (第 {current_page + 1}/{total_pages} 页)\n\n" \
                        f"📈 总任务: {stats.get('total', 0)} | " \
                        f"🔥 进行中: {stats.get('in_progress', 0)} | " \
                        f"⏳ 待处理: {stats.get('pending', 0)} | " \
                        f"✅ 已完成: {stats.get('completed', 0)}\n" \
                        f"🚨 紧急: {stats.get('by_urgency', {}).get('urgent', 0)} | " \
                        f"🔴 高优先级: {stats.get('by_urgency', {}).get('high', 0)}"
        else:
            stats_text = f"📊 **任务列表** (第 {current_page + 1}/{total_pages} 页)\n\n共 {total_tasks} 个任务"
        
        card_elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": stats_text
            }
        })
        
        card_elements.append({"tag": "hr"})
        
        # 任务列表
        if not tasks:
            card_elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "📝 暂无任务记录"
                }
            })
        else:
            for i, task in enumerate(tasks, 1):
                # 状态和紧急程度图标
                status_icon = _get_status_icon(task['status'])
                urgency_icon = _get_urgency_icon(task['urgency'])
                
                # 描述预览（限制长度）
                description = task['description']
                if len(description) > 80:
                    description = description[:80] + "..."
                
                # 技能标签格式化
                skills = task['skilltags'].replace(',', ' • ') if task['skilltags'] else '暂无'
                
                # 截止时间格式化
                deadline = task['deadline'] if task['deadline'] else '未设置'
                
                task_content = f"**{i}. {task['title']}**\n\n" \
                             f"{status_icon} **状态**: {_get_status_display(task['status'])} | " \
                             f"{urgency_icon} **优先级**: {_get_urgency_display(task['urgency'])}\n" \
                             f"🏷️ **ID**: {task['taskid']}\n" \
                             f"📝 **描述**: {description}\n" \
                             f"🛠️ **技能**: {skills}\n" \
                             f"📅 **截止**: {deadline} | " \
                             f"👤 **创建者**: {task['creator']}\n" \
                             f"⏰ **创建时间**: {task['create_time']}"
                
                card_elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": task_content
                    }
                })
                
                # 添加任务操作按钮
                actions = []
                
                # 添加删除按钮（所有状态的任务都可以删除）
                actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "🗑️ 删除"},
                    "type": "danger",
                    "value": {
                        "action": "delete_task",
                        "task_id": task['taskid'],
                        "record_id": task['record_id'],
                        "task_title": task['title']
                    }
                })
                
                if actions:
                    card_elements.append({
                        "tag": "action",
                        "actions": actions
                    })
                
                # 添加分隔线（除了最后一个任务）
                if i < len(tasks):
                    card_elements.append({"tag": "hr"})
        
        # 翻页按钮
        if total_pages > 1:
            card_elements.append({"tag": "hr"})
            
            page_actions = []
            
            if has_prev:
                page_actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "◀️ 上一页"},
                    "type": "default",
                    "value": {
                        "action": "tasks_page",
                        "page": current_page - 1
                    }
                })
            
            # 显示页码信息
            page_actions.append({
                "tag": "button",
                "text": {"tag": "plain_text", "content": f"📄 {current_page + 1}/{total_pages}"},
                "type": "default",
                "value": {
                    "action": "tasks_refresh",
                    "page": current_page
                }
            })
            
            if has_next:
                page_actions.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "▶️ 下一页"},
                    "type": "primary",
                    "value": {
                        "action": "tasks_page",
                        "page": current_page + 1
                    }
                })
            
            if page_actions:
                card_elements.append({
                    "tag": "action",
                    "actions": page_actions
                })
        
        # 构建完整卡片
        card = {
            "config": {"wide_screen_mode": True},
            "elements": card_elements
        }
        
        # 发送卡片
        await feishu_service.send_card_message(
            user_id=user_id,
            card=card,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"发送任务列表卡片时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="生成任务列表时出错，请稍后重试。"
        )

def _get_status_icon(status: str) -> str:
    """获取任务状态对应的图标"""
    status_icons = {
        'pending': '⏳',
        'assigned': '📋',
        'in_progress': '🔥',
        'submitted': '📤',
        'reviewing': '🔍',
        'completed': '✅',
        'rejected': '❌',
        'cancelled': '🚫'
    }
    return status_icons.get(status.lower(), '❓')

def _get_urgency_icon(urgency: str) -> str:
    """获取紧急程度对应的图标"""
    urgency_icons = {
        'urgent': '🚨',
        'high': '🔴',
        'normal': '🟡',
        'low': '🟢'
    }
    return urgency_icons.get(urgency.lower(), '⚪')

def _get_status_display(status: str) -> str:
    """获取任务状态的显示名称"""
    status_display = {
        'pending': '待处理',
        'assigned': '已分配',
        'in_progress': '进行中',
        'submitted': '已提交',
        'reviewing': '审核中',
        'completed': '已完成',
        'rejected': '已拒绝',
        'cancelled': '已取消'
    }
    return status_display.get(status.lower(), status)

def _get_urgency_display(urgency: str) -> str:
    """获取紧急程度的显示名称"""
    urgency_display = {
        'urgent': '紧急',
        'high': '高',
        'normal': '普通',
        'low': '低'
    }
    return urgency_display.get(urgency.lower(), urgency)

async def handle_task_delete(user_id: str, action_value: Dict[str, Any]):
    """处理任务删除"""
    try:
        task_id = action_value.get('task_id')
        record_id = action_value.get('record_id')
        task_title = action_value.get('task_title', '未知任务')
        
        if not record_id:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 无效的记录ID，无法删除任务"
            )
            return
        
        # 发送确认删除卡片
        await _send_delete_confirmation_card(user_id, task_id, record_id, task_title)
        
    except Exception as e:
        logger.error(f"处理任务删除时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="处理删除请求时出错，请稍后重试。"
        )

async def _send_delete_confirmation_card(user_id: str, task_id: str, record_id: str, task_title: str):
    """发送删除确认卡片"""
    try:
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"⚠️ **确认删除任务**\n\n您确定要删除以下任务吗？此操作不可撤销！\n\n📝 **任务标题**: {task_title}\n🏷️ **任务ID**: {task_id or '无'}\n🆔 **记录ID**: {record_id}"
                    }
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 确认删除"},
                            "type": "danger",
                            "value": {
                                "action": "confirm_delete_task",
                                "record_id": record_id,
                                "task_id": task_id,
                                "task_title": task_title
                            }
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "❌ 取消"},
                            "type": "default",
                            "value": {
                                "action": "cancel_delete_task"
                            }
                        }
                    ]
                }
            ]
        }
        
        await feishu_service.send_card_message(
            user_id=user_id,
            card=card
        )
        
    except Exception as e:
        logger.error(f"发送删除确认卡片时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="生成确认删除界面时出错，请稍后重试。"
        )

async def handle_confirm_delete_task(user_id: str, action_value: Dict[str, Any]):
    """处理确认删除任务"""
    try:
        record_id = action_value.get('record_id')
        task_id = action_value.get('task_id')
        task_title = action_value.get('task_title', '未知任务')
        
        if not record_id:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 删除失败：无效的记录ID"
            )
            return
        
        # 执行删除操作
        delete_result = await bitable_client.delete_task_record(record_id)
        
        if delete_result.get('success'):
            # 删除成功
            success_message = f"""✅ **任务删除成功**

📝 **任务**: {task_title}
🏷️ **ID**: {task_id or '无'}
🆔 **记录ID**: {record_id}

✨ 任务已从多维表格中永久删除。
💡 您可以使用 `/tasks` 命令查看更新后的任务列表。"""
            
            await feishu_service.send_message(
                user_id=user_id,
                message=success_message
            )
        else:
            # 删除失败
            error_message = f"""❌ **任务删除失败**

📝 **任务**: {task_title}
🏷️ **ID**: {task_id or '无'}
🆔 **记录ID**: {record_id}

❗ **错误信息**: {delete_result.get('message', '未知错误')}

请稍后重试或联系管理员。"""
            
            await feishu_service.send_message(
                user_id=user_id,
                message=error_message
            )
            
    except Exception as e:
        logger.error(f"确认删除任务时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="删除任务时出错，请稍后重试。"
        )

async def handle_candidates_command(user_id: str, command: str, chat_id: str = None):
    """处理候选人信息展示命令"""
    try:
        # 解析命令参数
        parts = command.strip().split()
        sort_by = 'experience'  # 默认按经验排序
        page = 0
        
        # 解析排序和分页参数
        for part in parts[1:]:
            if part.startswith('sort='):
                sort_value = part.split('=')[1].lower()
                if sort_value in ['experience', 'exp', '经验']:
                    sort_by = 'experience'
                elif sort_value in ['skills', 'skill', '技能']:
                    sort_by = 'skills'
                elif sort_value in ['score', '评分']:
                    sort_by = 'score'
                elif sort_value in ['tasks', '任务数']:
                    sort_by = 'tasks'
            elif part.startswith('page='):
                try:
                    page = max(0, int(part.split('=')[1]) - 1)  # 用户输入1开始，内部0开始
                except:
                    page = 0
        
        # 获取所有候选人数据
        candidates = await bitable_client.get_all_candidates()
        
        if not candidates:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ 暂无候选人信息，请联系管理员检查数据表配置。"
            )
            return
        
        # 排序候选人
        sorted_candidates = _sort_candidates(candidates, sort_by)
        
        # 分页处理 (每页7人)
        page_size = 7
        total_candidates = len(sorted_candidates)
        total_pages = (total_candidates + page_size - 1) // page_size if total_candidates > 0 else 1
        
        # 确保页码有效
        if page >= total_pages:
            page = total_pages - 1
        
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_candidates = sorted_candidates[start_idx:end_idx]
        
        # 发送候选人信息卡片
        await _send_candidates_list_card(
            user_id=user_id,
            candidates=page_candidates,
            sort_by=sort_by,
            page=page,
            total_pages=total_pages,
            total_candidates=total_candidates,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"处理候选人展示命令时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="获取候选人信息时出错，请稍后重试。"
        )

def _sort_candidates(candidates: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
    """排序候选人列表"""
    try:
        if sort_by == 'experience':
            # 按工作经验年数排序（降序）
            return sorted(candidates, key=lambda x: x.get('experience', 0), reverse=True)
        elif sort_by == 'skills':
            # 按技能数量排序（降序）
            return sorted(candidates, key=lambda x: len(x.get('skill_tags', [])), reverse=True)
        elif sort_by == 'score':
            # 按平均评分排序（降序）
            return sorted(candidates, key=lambda x: x.get('average_score', 0), reverse=True)
        elif sort_by == 'tasks':
            # 按完成任务数排序（降序）
            return sorted(candidates, key=lambda x: x.get('total_tasks', 0), reverse=True)
        else:
            # 默认按经验排序
            return sorted(candidates, key=lambda x: x.get('experience', 0), reverse=True)
    except Exception as e:
        logger.error(f"排序候选人时出错: {str(e)}")
        return candidates

async def _send_candidates_list_card(user_id: str, candidates: List[Dict[str, Any]], sort_by: str, 
                                   page: int, total_pages: int, total_candidates: int, chat_id: str = None):
    """发送候选人列表卡片"""
    try:
        # 排序方式显示文本
        sort_display = {
            'experience': '工作经验',
            'skills': '技能数量', 
            'score': '平均评分',
            'tasks': '完成任务数'
        }
        
        # 构建候选人列表文本
        candidates_text = ""
        for i, candidate in enumerate(candidates, start=page * 7 + 1):
            skill_tags = candidate.get('skill_tags', [])
            skills_text = ', '.join(skill_tags[:3]) + ('...' if len(skill_tags) > 3 else '')
            
            candidate_info = f"""
**{i}. {candidate.get('name', '未知')}** 
🏷️ ID: {candidate.get('user_id', '无')}
💼 职级: {_get_job_level_text(candidate.get('job_level', 1))}
⏰ 经验: {candidate.get('experience', 0)}年
🎯 技能: {skills_text or '未知'}
📊 完成任务: {candidate.get('total_tasks', 0)}个
⭐ 平均评分: {candidate.get('average_score', 0)}分
"""
            candidates_text += candidate_info
        
        # 构建卡片内容
        card_content = f"""👥 **候选人信息列表**

📋 **当前排序**: {sort_display.get(sort_by, '默认')}
📄 **页码**: {page + 1}/{total_pages} (共{total_candidates}人)

{candidates_text}

🔍 **使用说明**:
• `/candidates sort=experience` - 按工作经验排序
• `/candidates sort=skills` - 按技能数量排序  
• `/candidates sort=score` - 按平均评分排序
• `/candidates sort=tasks` - 按完成任务数排序
• `/candidates page=2` - 查看第2页
• `/candidates sort=experience page=2` - 组合使用

💡 **提示**: 默认每页显示7人，按工作经验降序排列。"""
        
        # 如果候选人数量较多，添加翻页按钮
        if total_pages > 1:
            # 构建带翻页按钮的卡片
            await _send_candidates_card_with_buttons(
                user_id=user_id,
                content=card_content,
                sort_by=sort_by,
                page=page,
                total_pages=total_pages,
                chat_id=chat_id
            )
        else:
            # 发送简单文本消息
            await feishu_service.send_message(
                user_id=user_id,
                message=card_content
            )
        
    except Exception as e:
        logger.error(f"发送候选人列表卡片时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="显示候选人信息时出错，请稍后重试。"
        )

async def _send_candidates_card_with_buttons(user_id: str, content: str, sort_by: str, 
                                           page: int, total_pages: int, chat_id: str = None):
    """发送带翻页按钮的候选人卡片"""
    try:
        # 构建翻页按钮
        buttons = []
        
        # 上一页按钮
        if page > 0:
            buttons.append({
                "tag": "button",
                "text": {
                    "tag": "plain_text",
                    "content": "⬅️ 上一页"
                },
                "type": "primary",
                "value": {
                    "action": "candidates_page",
                    "sort_by": sort_by,
                    "page": page - 1
                }
            })
        
        # 排序按钮
        sort_options = [
            ("经验", "experience"),
            ("技能", "skills"), 
            ("评分", "score"),
            ("任务", "tasks")
        ]
        
        for name, value in sort_options:
            if value != sort_by:  # 只显示非当前排序的按钮
                buttons.append({
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": f"📊 按{name}排序"
                    },
                    "type": "default",
                    "value": {
                        "action": "candidates_sort",
                        "sort_by": value,
                        "page": 0  # 排序后回到第一页
                    }
                })
        
        # 下一页按钮
        if page < total_pages - 1:
            buttons.append({
                "tag": "button", 
                "text": {
                    "tag": "plain_text",
                    "content": "下一页 ➡️"
                },
                "type": "primary",
                "value": {
                    "action": "candidates_page",
                    "sort_by": sort_by,
                    "page": page + 1
                }
            })
        
        # 构建卡片
        card = {
            "config": {"wide_screen_mode": True},
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": content
                    }
                }
            ]
        }
        
        # 如果有按钮，添加到卡片中
        if buttons:
            # 将按钮分组，每行最多3个
            button_rows = []
            for i in range(0, len(buttons), 3):
                row_buttons = buttons[i:i+3]
                button_rows.append({
                    "tag": "action",
                    "actions": row_buttons
                })
            
            card["elements"].extend(button_rows)
        
        # 发送卡片
        await feishu_service.send_card_message(
            user_id=user_id,
            card=card,
            chat_id=chat_id
        )
        
    except Exception as e:
        logger.error(f"发送候选人卡片按钮时出错: {str(e)}")
        # 降级到文本消息
        await feishu_service.send_message(
            user_id=user_id,
            message=content
        )

async def handle_resume_upload(user_id: str, file_key: str, file_name: str, chat_id: str = None, message_id: str = None):
    """处理PDF简历上传和分析"""
    try:
        # 发送处理提示
        await feishu_service.send_message(
            user_id=user_id,
            message=f"📄 正在分析简历文件：{file_name}\n\n⏳ AI正在解析PDF内容，请稍候..."
        )
        
        # 下载PDF文件
        file_content = await _download_feishu_file(file_key, message_id)
        if not file_content:
            # 提供更详细的错误提示和解决方案
            error_message = """❌ **文件下载失败**

可能的原因和解决方案：

🔧 **技术问题**：
• 网络连接问题 - 请稍后重试
• 文件可能已过期 - 请重新上传

👨‍💻 **管理员配置**：
• 可能需要开通更多API权限
• 建议联系管理员检查应用权限配置

💡 **建议操作**：
• 请重新上传PDF文件
• 确保文件大小不超过10MB
• 确保文件格式为PDF

如问题持续，请联系管理员。"""
            
            await feishu_service.send_message(
                user_id=user_id,
                message=error_message
            )
            return
        
        # 使用AI分析PDF简历
        from app.services.llm import llm_service
        resume_data = await llm_service.analyze_resume_pdf(file_content, file_name)
        
        if not resume_data:
            await feishu_service.send_message(
                user_id=user_id,
                message="❌ AI分析简历失败，请确保PDF内容清晰可读。"
            )
            return
        
        # 验证和完善候选人数据
        candidate_data = _prepare_candidate_data(resume_data, user_id)
        
        # 保存到coder表格
        save_success = await _save_candidate_to_table(candidate_data)
        
        # 构建分析结果消息
        save_message = "✅ **候选人信息已保存到多维表格**" if save_success else "⚠️ **候选人信息保存失败，但分析完成**"
        
        analysis_message = f"""🎉 **AI简历分析完成！**

{save_message}

📋 **候选人基本信息：**
• 姓名: {candidate_data.get('name', 'N/A')}
• 用户ID: {candidate_data.get('userid', user_id)}
• 职级: {_get_job_level_text(candidate_data.get('job_level', 1))}
• 工作经验: {candidate_data.get('experience', 0)}年

🛠️ **技能信息：**
• 技能标签: {candidate_data.get('skilltags', 'N/A') if candidate_data.get('skilltags', '').strip() else '待补充 (AI未识别到明确技能)'}
• 技能数量: {len(candidate_data.get('skilltags', '').split(',')) if candidate_data.get('skilltags') else 0}个

📊 **统计信息：**
• 总任务数: {candidate_data.get('total_tasks', 0)}
• 平均评分: {candidate_data.get('average_score', 0.0)}分

---
💡 您可以使用以下命令查看候选人信息：
• `/candidates` - 查看所有候选人
• `/status` - 查看个人状态"""
        
        await feishu_service.send_message(
            user_id=user_id,
            message=analysis_message
        )
        
        # 如果是在群聊中，也发送简要信息
        if chat_id:
            group_message = f"""👥 **新候选人已加入**

📄 简历文件：{file_name}
👤 候选人：{candidate_data.get('name', 'N/A')}
🎯 主要技能：{candidate_data.get('skilltags', 'N/A')[:50]}{'...' if len(candidate_data.get('skilltags', '')) > 50 else ''}
⭐ 工作经验：{candidate_data.get('experience', 0)}年

已自动录入候选人数据库。"""
            
            await feishu_service.send_message_to_chat(
                chat_id=chat_id,
                message=group_message
            )
        
        logger.info(f"AI简历分析完成: {file_name}, 候选人: {candidate_data.get('name', 'Unknown')} ({'已保存' if save_success else '保存失败'})")
        
    except Exception as e:
        logger.error(f"处理简历上传时出错: {str(e)}")
        await feishu_service.send_message(
            user_id=user_id,
            message="❌ 处理简历时出错，请稍后重试或联系管理员。"
        )

async def _download_feishu_file(file_key: str, message_id: str = None) -> bytes:
    """下载飞书文件"""
    try:
        import httpx
        
        # 判断文件类型：消息附件 vs 云文档文件
        if file_key.startswith('file_v3_'):
            logger.info(f"检测到消息附件文件: {file_key}")
            return await _download_message_attachment(file_key, message_id)
        else:
            logger.info(f"检测到云文档文件: {file_key}")
            return await _download_drive_file(file_key)
                
    except Exception as e:
        logger.error(f"下载文件异常: {str(e)}")
        return None

async def _download_message_attachment(file_key: str, message_id: str = None) -> bytes:
    """下载消息附件文件"""
    try:
        import httpx
        
        # 获取访问令牌
        token = await _get_feishu_access_token()
        if not token:
            logger.error("无法获取访问令牌")
            return None
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # 方法1：使用标准的消息附件下载API (添加type参数)
        if message_id:
            download_url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=file"
            logger.info(f"尝试使用消息ID下载附件: {download_url}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(download_url, headers=headers)
                if response.status_code == 200:
                    logger.info(f"消息附件下载成功: {file_key}")
                    return response.content
                else:
                    logger.error(f"消息附件下载失败: {response.status_code}, 响应: {response.text}")
                    
                    # 尝试其他type参数
                    for file_type in ['image', 'video', 'audio']:
                        logger.info(f"尝试type={file_type}参数...")
                        alt_url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/resources/{file_key}?type={file_type}"
                        response2 = await client.get(alt_url, headers=headers)
                        if response2.status_code == 200:
                            logger.info(f"使用type={file_type}下载成功: {file_key}")
                            return response2.content
                        else:
                            logger.debug(f"type={file_type}下载失败: {response2.status_code}")
        
        # 方法2：尝试不同的消息资源API
        resource_apis = [
            f"https://open.feishu.cn/open-apis/im/v1/messages/resources/{file_key}?type=file",
            f"https://open.feishu.cn/open-apis/im/v1/messages/resources/{file_key}",
            f"https://open.feishu.cn/open-apis/im/v1/images/{file_key}",
            f"https://open.feishu.cn/open-apis/im/v1/files/{file_key}"
        ]
        
        for api_url in resource_apis:
            logger.info(f"尝试资源API: {api_url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url, headers=headers)
                if response.status_code == 200:
                    logger.info(f"资源API下载成功: {file_key}")
                    return response.content
                else:
                    logger.debug(f"资源API失败: {response.status_code}")
        
        # 方法3：尝试文件直接下载API (如果有权限的话)
        logger.info("尝试文件直接下载API...")
        file_download_url = f"https://open.feishu.cn/open-apis/drive/v1/files/{file_key}/download"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(file_download_url, headers=headers)
            if response.status_code == 200:
                logger.info(f"文件直接下载成功: {file_key}")
                return response.content
            elif response.status_code == 400:
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                if '99991672' in str(response_data.get('code', '')):
                    logger.warning("文件下载权限不足，建议管理员开通drive相关权限")
                    logger.warning("权限申请链接: https://open.feishu.cn/app/cli_a8d880f40cf8100c/auth")
                else:
                    logger.error(f"文件直接下载失败: {response.status_code}, 响应: {response.text}")
            else:
                logger.error(f"文件直接下载失败: {response.status_code}, 响应: {response.text}")
        
        return None
                
    except Exception as e:
        logger.error(f"下载消息附件异常: {str(e)}")
        return None

async def _download_drive_file(file_key: str) -> bytes:
    """下载云文档文件"""
    try:
        import httpx
        
        # 方法1：尝试获取临时下载链接
        download_url = await _get_file_download_url(file_key)
        if download_url:
            # 下载文件内容
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(download_url)
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"通过下载链接下载文件失败: {response.status_code}")
        
        # 方法2：直接通过API下载文件内容
        logger.info("尝试直接API下载文件...")
        token = await _get_feishu_access_token()
        if not token:
            logger.error("无法获取访问令牌用于直接下载")
            return None
        
        # 直接下载文件内容API
        download_api_url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{file_key}/download"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(download_api_url, headers=headers)
            if response.status_code == 200:
                logger.info(f"直接API下载文件成功: {file_key}")
                return response.content
            else:
                logger.error(f"直接API下载文件失败: {response.status_code}, 响应: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"下载云文档文件异常: {str(e)}")
        return None

async def _get_file_download_url(file_key: str) -> str:
    """获取文件下载链接"""
    try:
        # 使用飞书官方的文件下载API
        from lark_oapi.api.drive.v1 import GetDriveV1MediasByFileTokenDownloadUrlRequest
        
        # 尝试不同的API调用方式
        try:
            # 方法1：使用标准的文件下载API
            request = GetDriveV1MediasByFileTokenDownloadUrlRequest.builder() \
                .file_token(file_key) \
                .build()
            
            response = feishu_service.client.drive.v1.media.download_url(request)
            
            if response.success():
                return response.data.download_url
            else:
                logger.error(f"获取下载链接失败: {response.code} - {response.msg}")
                return None
                
        except ImportError:
            # 方法2：如果API类名不正确，使用直接HTTP请求
            logger.warning("SDK API类名可能不正确，尝试直接HTTP请求")
            return await _get_file_download_url_http(file_key)
            
    except Exception as e:
        logger.error(f"获取下载链接异常: {str(e)}")
        # 降级到HTTP请求方式
        try:
            return await _get_file_download_url_http(file_key)
        except:
            return None

async def _get_file_download_url_http(file_key: str) -> str:
    """通过HTTP请求获取文件下载链接（备用方案）"""
    try:
        import httpx
        
        # 首先获取访问令牌
        token = await _get_feishu_access_token()
        if not token:
            logger.error("无法获取访问令牌")
            return None
        
        # 构建API请求
        url = f"https://open.feishu.cn/open-apis/drive/v1/medias/{file_key}/download_url"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return data.get('data', {}).get('download_url')
                else:
                    logger.error(f"获取下载链接API错误: {data.get('msg')}")
                    return None
            else:
                logger.error(f"HTTP请求失败: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"HTTP方式获取下载链接失败: {str(e)}")
        return None

async def _get_feishu_access_token() -> str:
    """获取飞书访问令牌"""
    try:
        import httpx
        from app.config import settings
        
        # 使用飞书的token API
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": settings.feishu_app_id,
            "app_secret": settings.feishu_app_secret
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    return result.get('tenant_access_token')
                else:
                    logger.error(f"获取token失败: {result.get('msg')}")
                    return None
            else:
                logger.error(f"获取token HTTP请求失败: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"获取飞书访问令牌失败: {str(e)}")
        return None

def _prepare_candidate_data(resume_data: dict, user_id: str) -> dict:
    """准备候选人数据"""
    try:
        # 从AI分析结果中提取和转换数据
        skills_list = resume_data.get('skills', [])
        # 严格模式：如果AI没有提取到技能，就保持为空，但在数据库中需要一个占位符
        if skills_list:
            skilltags = ','.join(skills_list)
        else:
            skilltags = ''  # 严格为空，在保存时再处理
            
        candidate_data = {
            'userid': user_id,  # 使用上传者的用户ID
            'name': resume_data.get('name', 'Unknown'),
            'skilltags': skilltags,
            'job_level': resume_data.get('job_level', 1),  # 现在使用数字格式
            'experience': max(0, resume_data.get('experience_years', 0)),  # 确保为非负数
            'total_tasks': 0,  # 新候选人默认为0
            'average_score': 0.0  # 新候选人默认为0
        }
        
        # 数据验证和清理
        if not candidate_data['name'] or candidate_data['name'] == 'Unknown':
            candidate_data['name'] = f"候选人_{user_id[-6:]}"  # 使用用户ID后6位作为默认名称
        
        # 限制技能标签长度
        if len(candidate_data['skilltags']) > 200:
            skills_list = candidate_data['skilltags'].split(',')[:10]  # 最多保留10个技能
            candidate_data['skilltags'] = ','.join(skills_list)
        
        return candidate_data
        
    except Exception as e:
        logger.error(f"准备候选人数据时出错: {str(e)}")
        # 返回最基本的数据
        return {
            'userid': user_id,
            'name': f"候选人_{user_id[-6:]}",
            'skilltags': '',
            'job_level': 'Junior',
            'experience': 0,
            'total_tasks': 0,
            'average_score': 0.0
        }

async def _save_candidate_to_table(candidate_data: dict) -> bool:
    """保存候选人数据到多维表格"""
    try:
        # 检查候选人是否已存在
        existing_candidate = await bitable_client.get_candidate_details(candidate_data['userid'])
        if existing_candidate:
            logger.info(f"候选人已存在，更新信息: {candidate_data['userid']}")
            # 可以选择更新现有候选人信息或跳过
            return True
        
        # 创建新候选人记录
        success = await bitable_client.create_candidate_record(candidate_data)
        if success:
            logger.info(f"候选人记录创建成功: {candidate_data['name']} ({candidate_data['userid']})")
            return True
        else:
            logger.error(f"候选人记录创建失败: {candidate_data['userid']}")
            return False
            
    except Exception as e:
        logger.error(f"保存候选人到表格时出错: {str(e)}")
        return False