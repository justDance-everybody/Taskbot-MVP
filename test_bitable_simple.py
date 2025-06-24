#!/usr/bin/env python3
"""
简化的多维表格测试脚本
用于验证基本的API调用
"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.append('.')

async def test_create_app_only():
    """只测试创建多维表格应用"""
    print("🧪 测试创建多维表格应用...")

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
        return None
    
    try:
        import lark_oapi as lark
        from lark_oapi.api.bitable.v1 import CreateAppRequest
        
        # 创建客户端
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        print(f"✅ 客户端创建成功")
        print(f"   App ID: {app_id[:10]}...")
        
        # 创建多维表格应用
        request = CreateAppRequest.builder().build()
        
        # 设置请求体
        request.body = {
            "name": "测试任务管理表格"
        }
        
        print("📋 发送创建请求...")
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
            print(f"❌ 创建失败: {response.msg}")
            # 打印更多调试信息
            if hasattr(response, 'raw_response'):
                print(f"   原始响应: {response.raw_response}")
            return None
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_create_simple_table(app_token: str):
    """测试创建简单表格"""
    print(f"\n🧪 测试创建表格...")
    
    try:
        import lark_oapi as lark
        from lark_oapi.api.bitable.v1 import (
            CreateAppTableRequest,
            CreateAppTableRequestBody,
            AppTable
        )
        
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        # 创建表格对象
        table = AppTable.builder() \
            .name("测试任务表") \
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
        
        print("📋 发送创建表格请求...")
        response = client.bitable.v1.app_table.create(request)
        
        print(f"   响应状态: {response.success()}")
        print(f"   响应消息: {response.msg}")
        print(f"   响应代码: {response.code}")
        
        if response.success():
            table_id = response.data.table_id
            print(f"✅ 表格创建成功!")
            print(f"   Table ID: {table_id}")
            return table_id
        else:
            print(f"❌ 表格创建失败: {response.msg}")
            return None
            
    except Exception as e:
        print(f"❌ 表格创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_add_simple_field(app_token: str, table_id: str):
    """测试添加简单字段"""
    print(f"\n🧪 测试添加字段...")
    
    try:
        import lark_oapi as lark
        from lark_oapi.api.bitable.v1 import (
            CreateAppTableFieldRequest,
            AppTableField
        )
        
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        # 创建字段对象
        field = AppTableField.builder() \
            .field_name("任务标题") \
            .type(1) \
            .build()  # TEXT类型
        
        # 创建请求
        request = CreateAppTableFieldRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(field) \
            .build()
        
        print("📋 发送添加字段请求...")
        response = client.bitable.v1.app_table_field.create(request)
        
        print(f"   响应状态: {response.success()}")
        print(f"   响应消息: {response.msg}")
        print(f"   响应代码: {response.code}")
        
        if response.success():
            field_id = response.data.field.field_id
            print(f"✅ 字段添加成功!")
            print(f"   Field ID: {field_id}")
            return field_id
        else:
            print(f"❌ 字段添加失败: {response.msg}")
            return None
            
    except Exception as e:
        print(f"❌ 字段添加测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """主测试函数"""
    print("🚀 开始简化的多维表格API测试...")
    print("=" * 50)
    
    # 步骤1: 创建多维表格应用
    app_token = await test_create_app_only()
    if not app_token:
        print("❌ 无法创建多维表格应用，测试终止")
        return 1
    
    # 步骤2: 创建表格
    table_id = await test_create_simple_table(app_token)
    if not table_id:
        print("❌ 无法创建表格，但应用已创建")
        print(f"App Token: {app_token}")
        return 1
    
    # 步骤3: 添加字段
    field_id = await test_add_simple_field(app_token, table_id)
    
    print("\n" + "=" * 50)
    print("🎉 测试完成!")
    print("=" * 50)
    print(f"多维表格 App Token: {app_token}")
    print(f"表格 Table ID: {table_id}")
    if field_id:
        print(f"字段 Field ID: {field_id}")
    print()
    print("请将以下配置添加到 .env.production 文件中:")
    print(f"FEISHU_BITABLE_APP_TOKEN={app_token}")
    print()
    print("🔗 访问多维表格:")
    print(f"https://feishu.cn/base/{app_token}")
    
    return 0

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
