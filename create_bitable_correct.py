#!/usr/bin/env python3
"""
根据飞书官方文档正确实现多维表格创建
参考文档：
- 创建多维表格: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/create
- 新增字段: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/create
"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.append('.')

async def create_bitable_app(app_id: str, app_secret: str, name: str = "任务管理多维表格") -> str:
    """
    创建多维表格应用
    参考: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/create
    """
    print(f"📋 创建多维表格应用: {name}")
    
    try:
        import lark_oapi as lark
        from lark_oapi.api.bitable.v1 import CreateAppRequest
        
        # 创建客户端
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # 根据官方文档，创建多维表格应用
        # 请求体可以包含name和folder_token（可选）
        request = CreateAppRequest.builder().build()
        
        # 设置请求体 - 根据官方文档格式
        request.body = {
            "name": name
        }
        
        response = client.bitable.v1.app.create(request)
        
        print(f"   响应状态: {response.success()}")
        print(f"   响应消息: {response.msg}")
        print(f"   响应代码: {response.code}")
        
        if response.success():
            app_token = response.data.app.app_token
            app_url = response.data.app.url
            print(f"✅ 多维表格创建成功!")
            print(f"   App Token: {app_token}")
            print(f"   访问链接: {app_url}")
            return app_token
        else:
            raise Exception(f"创建多维表格失败: {response.msg} (code: {response.code})")
            
    except Exception as e:
        print(f"❌ 创建多维表格应用失败: {e}")
        raise

async def create_table_with_default_fields(client, app_token: str, table_name: str) -> str:
    """
    创建表格（使用默认字段，然后添加自定义字段）
    """
    print(f"📋 创建表格: {table_name}")
    
    try:
        from lark_oapi.api.bitable.v1 import (
            CreateAppTableRequest,
            CreateAppTableRequestBody,
            AppTable
        )
        
        # 创建表格对象 - 根据官方文档，只需要name
        table = AppTable.builder() \
            .name(table_name) \
            .build()
        
        # 创建请求体
        request_body = CreateAppTableRequestBody.builder() \
            .table(table) \
            .build()
        
        # 创建请求
        request = CreateAppTableRequest.builder() \
            .app_token(app_token) \
            .request_body(request_body) \
            .build()
        
        # 发送请求
        response = client.bitable.v1.app_table.create(request)
        
        print(f"   响应状态: {response.success()}")
        print(f"   响应消息: {response.msg}")
        
        if response.success():
            table_id = response.data.table_id
            print(f"✅ 表格创建成功!")
            print(f"   Table ID: {table_id}")
            return table_id
        else:
            raise Exception(f"创建表格失败: {response.msg}")
            
    except Exception as e:
        print(f"❌ 创建表格失败: {e}")
        raise

async def add_field_to_table(client, app_token: str, table_id: str, field_name: str, field_type: int, property_data: dict = None) -> str:
    """
    向表格添加字段
    参考: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/create
    """
    print(f"📋 添加字段: {field_name} (类型: {field_type})")

    try:
        from lark_oapi.api.bitable.v1 import (
            CreateAppTableFieldRequest,
            AppTableField
        )

        # 构建字段对象
        field_builder = AppTableField.builder() \
            .field_name(field_name) \
            .type(field_type)

        # 如果有属性配置，添加属性
        if property_data:
            field_builder.property(property_data)

        field = field_builder.build()

        # 创建请求 - 直接使用字段对象作为请求体
        request = CreateAppTableFieldRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(field) \
            .build()

        # 发送请求
        response = client.bitable.v1.app_table_field.create(request)

        print(f"   响应状态: {response.success()}")
        print(f"   响应消息: {response.msg}")

        if response.success():
            field_id = response.data.field.field_id
            print(f"✅ 字段添加成功!")
            print(f"   Field ID: {field_id}")
            return field_id
        else:
            print(f"❌ 字段添加失败: {response.msg}")
            return None

    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        return None

async def create_tasks_table(client, app_token: str) -> str:
    """创建任务表"""
    print("\n📊 创建任务表...")
    
    # 1. 创建表格
    table_id = await create_table_with_default_fields(client, app_token, "Tasks")
    
    # 2. 添加自定义字段
    fields_to_add = [
        {
            "name": "任务标题",
            "type": 1,  # TEXT
            "property": {}
        },
        {
            "name": "任务描述", 
            "type": 1,  # TEXT
            "property": {}
        },
        {
            "name": "任务类型",
            "type": 3,  # SINGLE_SELECT
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
            "name": "优先级",
            "type": 3,  # SINGLE_SELECT
            "property": {
                "options": [
                    {"name": "高", "color": 1},
                    {"name": "中", "color": 2},
                    {"name": "低", "color": 3}
                ]
            }
        },
        {
            "name": "状态",
            "type": 3,  # SINGLE_SELECT
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
            "name": "承接人",
            "type": 1,  # TEXT
            "property": {}
        },
        {
            "name": "发布人",
            "type": 1,  # TEXT
            "property": {}
        },
        {
            "name": "技能要求",
            "type": 4,  # MULTI_SELECT
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
            "name": "预估工时",
            "type": 2,  # NUMBER
            "property": {}
        },
        {
            "name": "任务链接",
            "type": 15,  # URL
            "property": {}
        }
    ]
    
    # 添加字段
    field_ids = []
    for field_config in fields_to_add:
        field_id = await add_field_to_table(
            client, app_token, table_id, 
            field_config["name"], 
            field_config["type"], 
            field_config.get("property")
        )
        if field_id:
            field_ids.append(field_id)
    
    print(f"✅ 任务表创建完成，共添加 {len(field_ids)} 个字段")
    return table_id

async def create_persons_table(client, app_token: str) -> str:
    """创建人员表"""
    print("\n📊 创建人员表...")
    
    # 1. 创建表格
    table_id = await create_table_with_default_fields(client, app_token, "Persons")
    
    # 2. 添加自定义字段
    fields_to_add = [
        {
            "name": "姓名",
            "type": 1,  # TEXT
            "property": {}
        },
        {
            "name": "用户ID",
            "type": 1,  # TEXT
            "property": {}
        },
        {
            "name": "邮箱",
            "type": 1,  # TEXT (使用TEXT代替EMAIL)
            "property": {}
        },
        {
            "name": "技能标签",
            "type": 4,  # MULTI_SELECT
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
            "name": "可用状态",
            "type": 3,  # SINGLE_SELECT
            "property": {
                "options": [
                    {"name": "可用", "color": 4},
                    {"name": "忙碌", "color": 1},
                    {"name": "请假", "color": 2}
                ]
            }
        },
        {
            "name": "工作负载",
            "type": 2,  # NUMBER
            "property": {}
        },
        {
            "name": "历史评分",
            "type": 2,  # NUMBER
            "property": {}
        },
        {
            "name": "完成任务数",
            "type": 2,  # NUMBER
            "property": {}
        },
        {
            "name": "活跃度",
            "type": 2,  # NUMBER
            "property": {}
        }
    ]
    
    # 添加字段
    field_ids = []
    for field_config in fields_to_add:
        field_id = await add_field_to_table(
            client, app_token, table_id, 
            field_config["name"], 
            field_config["type"], 
            field_config.get("property")
        )
        if field_id:
            field_ids.append(field_id)
    
    print(f"✅ 人员表创建完成，共添加 {len(field_ids)} 个字段")
    return table_id

async def update_env_file(app_token: str, tasks_table_id: str, persons_table_id: str):
    """自动更新.env.production文件中的配置"""
    try:
        # 读取现有配置文件
        env_file = '.env.production'
        lines = []

        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        # 要添加或更新的配置
        new_configs = {
            'FEISHU_BITABLE_APP_TOKEN': app_token,
            'FEISHU_TASK_TABLE_ID': tasks_table_id,
            'FEISHU_PERSON_TABLE_ID': persons_table_id
        }

        # 更新配置
        updated_lines = []
        updated_keys = set()

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                key = line.split('=')[0]
                if key in new_configs:
                    updated_lines.append(f"{key}={new_configs[key]}\n")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line + '\n')
            else:
                updated_lines.append(line + '\n')

        # 添加新的配置（如果不存在）
        if 'FEISHU_BITABLE_APP_TOKEN' not in updated_keys:
            updated_lines.append('\n# 飞书多维表格配置\n')
            for key, value in new_configs.items():
                if key not in updated_keys:
                    updated_lines.append(f"{key}={value}\n")

        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)

        print(f"✅ 配置已更新到 {env_file}")
        print(f"   FEISHU_BITABLE_APP_TOKEN={app_token}")
        print(f"   FEISHU_TASK_TABLE_ID={tasks_table_id}")
        print(f"   FEISHU_PERSON_TABLE_ID={persons_table_id}")

    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        print("请手动添加以下配置到 .env.production 文件:")
        print(f"FEISHU_BITABLE_APP_TOKEN={app_token}")
        print(f"FEISHU_TASK_TABLE_ID={tasks_table_id}")
        print(f"FEISHU_PERSON_TABLE_ID={persons_table_id}")

async def main():
    """主函数"""
    print("🚀 根据官方文档创建飞书多维表格...")
    print("=" * 60)

    # 加载.env.production文件
    from dotenv import load_dotenv
    load_dotenv('.env.production')
    print("✅ 已加载 .env.production 配置文件")

    # 检查环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")

    if not app_id or not app_secret:
        print("❌ 请先在 .env.production 文件中配置飞书应用信息:")
        print("   FEISHU_APP_ID=your_app_id")
        print("   FEISHU_APP_SECRET=your_app_secret")
        return 1

    print(f"✅ 飞书应用配置已加载")
    print(f"   App ID: {app_id[:10]}...")
    print(f"   App Secret: {app_secret[:10]}...")
    
    try:
        import lark_oapi as lark
        
        # 1. 创建多维表格应用
        app_token = await create_bitable_app(app_id, app_secret)
        
        # 2. 创建客户端
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # 3. 创建任务表
        tasks_table_id = await create_tasks_table(client, app_token)
        
        # 4. 创建人员表
        persons_table_id = await create_persons_table(client, app_token)
        
        # 5. 自动更新配置文件
        print("\n📝 更新配置文件...")
        await update_env_file(app_token, tasks_table_id, persons_table_id)

        # 6. 输出结果
        print("\n" + "=" * 60)
        print("🎉 多维表格创建完成！")
        print("=" * 60)
        print(f"多维表格 App Token: {app_token}")
        print(f"任务表 Table ID: {tasks_table_id}")
        print(f"人员表 Table ID: {persons_table_id}")
        print()
        print("✅ 配置已自动写入 .env.production 文件")
        print()
        print("🔗 访问多维表格:")
        print(f"https://feishu.cn/base/{app_token}")

        return 0
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
