#!/usr/bin/env python3
"""
飞书多维表格初始化脚本
用于创建任务机器人所需的多维表格和数据表
"""

import os
import sys
import asyncio
from typing import Dict, Any, List

# 添加项目路径
sys.path.append('.')

async def create_bitable_app(app_id: str, app_secret: str) -> str:
    """创建多维表格应用"""
    import lark_oapi as lark
    from lark_oapi.api.bitable.v1 import CreateAppRequest, ReqApp

    # 创建客户端
    client = lark.Client.builder() \
        .app_id(app_id) \
        .app_secret(app_secret) \
        .log_level(lark.LogLevel.INFO) \
        .build()

    # 构建应用信息
    app_info = ReqApp.builder() \
        .name("飞书任务机器人数据表") \
        .time_zone("Asia/Shanghai") \
        .build()

    # 创建多维表格应用
    request = CreateAppRequest.builder() \
        .request_body(app_info) \
        .build()

    response = client.bitable.v1.app.create(request)

    if not response.success():
        raise Exception(f"创建多维表格失败: {response.msg}")

    app_token = response.data.app.app_token
    print(f"✅ 多维表格应用创建成功")
    print(f"   App Token: {app_token}")

    return app_token

async def create_tasks_table(client, app_token: str) -> str:
    """创建任务表"""
    from app.bitable import FieldType
    
    # 定义任务表字段
    fields = [
        {
            "field_name": "任务标题",
            "type": FieldType.TEXT.value,
            "property": {}
        },
        {
            "field_name": "任务描述", 
            "type": FieldType.TEXT.value,
            "property": {}
        },
        {
            "field_name": "任务类型",
            "type": FieldType.SINGLE_SELECT.value,
            "property": {
                "options": [
                    {"name": "代码开发", "color": 1},
                    {"name": "测试", "color": 2}, 
                    {"name": "文档", "color": 3},
                    {"name": "设计", "color": 4},
                    {"name": "其他", "color": 5}
                ]
            }
        },
        {
            "field_name": "优先级",
            "type": FieldType.SINGLE_SELECT.value,
            "property": {
                "options": [
                    {"name": "高", "color": 1},
                    {"name": "中", "color": 2},
                    {"name": "低", "color": 3}
                ]
            }
        },
        {
            "field_name": "状态",
            "type": FieldType.SINGLE_SELECT.value,
            "property": {
                "options": [
                    {"name": "Draft", "color": 1},
                    {"name": "Assigned", "color": 2},
                    {"name": "InProgress", "color": 3},
                    {"name": "Done", "color": 4},
                    {"name": "Returned", "color": 5}
                ]
            }
        },
        {
            "field_name": "承接人",
            "type": FieldType.TEXT.value,
            "property": {}
        },
        {
            "field_name": "发布人",
            "type": FieldType.TEXT.value,
            "property": {}
        },
        {
            "field_name": "技能要求",
            "type": FieldType.MULTI_SELECT.value,
            "property": {
                "options": [
                    {"name": "Python", "color": 1},
                    {"name": "JavaScript", "color": 2},
                    {"name": "Java", "color": 3},
                    {"name": "Go", "color": 4},
                    {"name": "React", "color": 5},
                    {"name": "Vue", "color": 6},
                    {"name": "数据库", "color": 7},
                    {"name": "DevOps", "color": 8},
                    {"name": "UI设计", "color": 9},
                    {"name": "测试", "color": 10}
                ]
            }
        },
        {
            "field_name": "预估工时",
            "type": FieldType.NUMBER.value,
            "property": {}
        },
        {
            "field_name": "截止时间",
            "type": FieldType.DATETIME.value,
            "property": {}
        },
        {
            "field_name": "创建时间",
            "type": FieldType.CREATED_TIME.value,
            "property": {}
        },
        {
            "field_name": "更新时间",
            "type": FieldType.LAST_MODIFIED_TIME.value,
            "property": {}
        },
        {
            "field_name": "任务链接",
            "type": FieldType.URL.value,
            "property": {}
        },
        {
            "field_name": "CI状态",
            "type": FieldType.SINGLE_SELECT.value,
            "property": {
                "options": [
                    {"name": "Success", "color": 4},
                    {"name": "Failed", "color": 1},
                    {"name": "Pending", "color": 2},
                    {"name": "Unknown", "color": 3}
                ]
            }
        }
    ]
    
    # 创建任务表
    from app.bitable import BitableClient
    bitable_client = BitableClient(app_token=app_token, client=client)
    
    table_id = await bitable_client.create_table("Tasks", fields)
    print(f"✅ 任务表创建成功")
    print(f"   Table ID: {table_id}")
    
    return table_id

async def create_persons_table(client, app_token: str) -> str:
    """创建人员表"""
    from app.bitable import FieldType
    
    # 定义人员表字段
    fields = [
        {
            "field_name": "姓名",
            "type": FieldType.TEXT.value,
            "property": {}
        },
        {
            "field_name": "用户ID",
            "type": FieldType.TEXT.value,
            "property": {}
        },
        {
            "field_name": "邮箱",
            "type": FieldType.EMAIL.value,
            "property": {}
        },
        {
            "field_name": "技能标签",
            "type": FieldType.MULTI_SELECT.value,
            "property": {
                "options": [
                    {"name": "Python", "color": 1},
                    {"name": "JavaScript", "color": 2},
                    {"name": "Java", "color": 3},
                    {"name": "Go", "color": 4},
                    {"name": "React", "color": 5},
                    {"name": "Vue", "color": 6},
                    {"name": "数据库", "color": 7},
                    {"name": "DevOps", "color": 8},
                    {"name": "UI设计", "color": 9},
                    {"name": "测试", "color": 10}
                ]
            }
        },
        {
            "field_name": "可用状态",
            "type": FieldType.SINGLE_SELECT.value,
            "property": {
                "options": [
                    {"name": "可用", "color": 4},
                    {"name": "忙碌", "color": 1},
                    {"name": "请假", "color": 2}
                ]
            }
        },
        {
            "field_name": "工作负载",
            "type": FieldType.NUMBER.value,
            "property": {}
        },
        {
            "field_name": "历史评分",
            "type": FieldType.NUMBER.value,
            "property": {}
        },
        {
            "field_name": "完成任务数",
            "type": FieldType.NUMBER.value,
            "property": {}
        },
        {
            "field_name": "活跃度",
            "type": FieldType.NUMBER.value,
            "property": {}
        },
        {
            "field_name": "加入时间",
            "type": FieldType.CREATED_TIME.value,
            "property": {}
        },
        {
            "field_name": "最后活跃",
            "type": FieldType.LAST_MODIFIED_TIME.value,
            "property": {}
        }
    ]
    
    # 创建人员表
    from app.bitable import BitableClient
    bitable_client = BitableClient(app_token=app_token, client=client)
    
    table_id = await bitable_client.create_table("Persons", fields)
    print(f"✅ 人员表创建成功")
    print(f"   Table ID: {table_id}")
    
    return table_id

async def add_sample_data(client, app_token: str, tasks_table_id: str, persons_table_id: str):
    """添加示例数据"""
    from app.bitable import BitableClient
    bitable_client = BitableClient(app_token=app_token, client=client)
    
    # 添加示例人员
    sample_persons = [
        {
            "姓名": "张三",
            "用户ID": "user_001",
            "邮箱": "zhangsan@example.com",
            "技能标签": ["Python", "数据库"],
            "可用状态": "可用",
            "工作负载": 3,
            "历史评分": 85,
            "完成任务数": 12,
            "活跃度": 90
        },
        {
            "姓名": "李四", 
            "用户ID": "user_002",
            "邮箱": "lisi@example.com",
            "技能标签": ["JavaScript", "React", "Vue"],
            "可用状态": "可用",
            "工作负载": 2,
            "历史评分": 92,
            "完成任务数": 8,
            "活跃度": 85
        },
        {
            "姓名": "王五",
            "用户ID": "user_003", 
            "邮箱": "wangwu@example.com",
            "技能标签": ["Java", "DevOps"],
            "可用状态": "忙碌",
            "工作负载": 5,
            "历史评分": 88,
            "完成任务数": 15,
            "活跃度": 95
        }
    ]
    
    for person in sample_persons:
        await bitable_client.add_record(persons_table_id, person)
    
    print(f"✅ 示例人员数据添加成功 ({len(sample_persons)}条)")
    
    # 添加示例任务
    sample_tasks = [
        {
            "任务标题": "优化数据库查询性能",
            "任务描述": "分析并优化用户查询接口的数据库性能",
            "任务类型": "代码开发",
            "优先级": "高",
            "状态": "Draft",
            "技能要求": ["Python", "数据库"],
            "预估工时": 8,
            "发布人": "产品经理"
        },
        {
            "任务标题": "前端页面重构",
            "任务描述": "使用React重构用户管理页面",
            "任务类型": "代码开发", 
            "优先级": "中",
            "状态": "Draft",
            "技能要求": ["JavaScript", "React"],
            "预估工时": 16,
            "发布人": "技术经理"
        }
    ]
    
    for task in sample_tasks:
        await bitable_client.add_record(tasks_table_id, task)
    
    print(f"✅ 示例任务数据添加成功 ({len(sample_tasks)}条)")

async def main():
    """主函数"""
    print("🚀 开始初始化飞书多维表格...")
    print()
    
    # 检查环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        print("❌ 请先设置飞书应用配置:")
        print("   export FEISHU_APP_ID='your_app_id'")
        print("   export FEISHU_APP_SECRET='your_app_secret'")
        return 1
    
    try:
        # 1. 创建多维表格应用
        print("📋 创建多维表格应用...")
        app_token = await create_bitable_app(app_id, app_secret)
        
        # 2. 创建客户端
        import lark_oapi as lark
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # 3. 创建任务表
        print("\n📋 创建任务表...")
        tasks_table_id = await create_tasks_table(client, app_token)
        
        # 4. 创建人员表
        print("\n📋 创建人员表...")
        persons_table_id = await create_persons_table(client, app_token)
        
        # 5. 添加示例数据
        print("\n📋 添加示例数据...")
        await add_sample_data(client, app_token, tasks_table_id, persons_table_id)
        
        # 6. 输出配置信息
        print("\n" + "="*50)
        print("🎉 多维表格初始化完成！")
        print("="*50)
        print(f"多维表格 App Token: {app_token}")
        print(f"任务表 Table ID: {tasks_table_id}")
        print(f"人员表 Table ID: {persons_table_id}")
        print()
        print("请将以下配置添加到 .env.production 文件中:")
        print(f"FEISHU_BITABLE_APP_TOKEN={app_token}")
        print()
        print("🔗 访问多维表格:")
        print(f"https://feishu.cn/base/{app_token}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
