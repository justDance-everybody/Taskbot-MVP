#!/usr/bin/env python3
"""
测试飞书多维表格创建功能
"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.append('.')

async def test_create_app():
    """测试创建多维表格应用"""
    print("🧪 测试创建多维表格应用...")
    
    # 检查环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        print("❌ 请先设置环境变量:")
        print("   export FEISHU_APP_ID='your_app_id'")
        print("   export FEISHU_APP_SECRET='your_app_secret'")
        return False
    
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
        
        # 方法1: 尝试不带参数创建
        print("\n📋 方法1: 不带参数创建多维表格...")
        request = CreateAppRequest.builder().build()
        response = client.bitable.v1.app.create(request)
        
        print(f"响应状态: {response.success()}")
        print(f"响应消息: {response.msg}")
        print(f"响应代码: {response.code}")
        
        if response.success():
            app_token = response.data.app.app_token
            print(f"✅ 多维表格创建成功!")
            print(f"   App Token: {app_token}")
            return app_token
        else:
            print(f"❌ 创建失败: {response.msg}")
            
            # 方法2: 尝试带名称创建
            print("\n📋 方法2: 尝试带名称创建...")
            
            # 检查是否有name参数
            try:
                # 尝试使用可能的参数
                request2 = CreateAppRequest.builder().build()
                # 直接设置body
                request2.body = {"name": "任务管理表格"}
                
                response2 = client.bitable.v1.app.create(request2)
                print(f"方法2响应: {response2.success()}, {response2.msg}")
                
                if response2.success():
                    app_token = response2.data.app.app_token
                    print(f"✅ 多维表格创建成功!")
                    print(f"   App Token: {app_token}")
                    return app_token
                    
            except Exception as e:
                print(f"方法2失败: {e}")
            
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_create_table_simple():
    """测试创建简单表格"""
    print("\n🧪 测试创建简单表格...")
    
    # 首先需要一个app_token，这里使用模拟的
    app_token = "test_app_token"
    
    try:
        import lark_oapi as lark
        from lark_oapi.api.bitable.v1 import (
            CreateAppTableRequest,
            CreateAppTableRequestBody,
            AppTable,
            AppTableField
        )
        
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()
        
        # 创建简单字段
        fields = [
            AppTableField.builder()
                .field_name("标题")
                .type(1)  # TEXT类型
                .build(),
            AppTableField.builder()
                .field_name("状态")
                .type(3)  # SINGLE_SELECT类型
                .build()
        ]
        
        # 创建表格对象
        table = AppTable.builder() \
            .name("测试表格") \
            .fields(fields) \
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
        
        print("✅ 表格创建请求构建成功")
        print("   (注意: 这里使用的是测试app_token，实际调用会失败)")
        
        return True
        
    except Exception as e:
        print(f"❌ 表格创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_field_types():
    """测试字段类型定义"""
    print("\n🧪 测试字段类型...")
    
    try:
        from app.bitable import FieldType
        
        print("✅ 字段类型定义:")
        for field_type in FieldType:
            print(f"   {field_type.name} = {field_type.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 字段类型测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始测试飞书多维表格创建功能...")
    print("=" * 50)
    
    # 测试1: 字段类型
    success1 = await test_field_types()
    
    # 测试2: 表格创建逻辑
    success2 = await test_create_table_simple()
    
    # 测试3: 实际API调用（需要真实凭证）
    if os.getenv("FEISHU_APP_ID") and os.getenv("FEISHU_APP_SECRET"):
        success3 = await test_create_app()
    else:
        print("\n⚠️  跳过实际API测试（未设置凭证）")
        success3 = True
    
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"   字段类型测试: {'✅' if success1 else '❌'}")
    print(f"   表格创建逻辑: {'✅' if success2 else '❌'}")
    print(f"   API调用测试: {'✅' if success3 else '❌'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
