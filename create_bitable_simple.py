#!/usr/bin/env python3
"""
简化版飞书多维表格创建脚本
直接使用飞书SDK创建多维表格
"""

import os
import sys
import asyncio

async def main():
    """主函数"""
    print("🚀 创建飞书多维表格...")
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
        import lark_oapi as lark
        from lark_oapi.api.bitable.v1 import CreateAppRequest, ReqApp
        
        # 创建客户端
        client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        print("📋 创建多维表格应用...")
        
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
            print(f"❌ 创建多维表格失败: {response.msg}")
            print(f"   错误码: {response.code}")
            return 1
        
        app_token = response.data.app.app_token
        print(f"✅ 多维表格应用创建成功")
        print(f"   App Token: {app_token}")
        
        # 输出配置信息
        print("\n" + "="*50)
        print("🎉 多维表格创建完成！")
        print("="*50)
        print(f"多维表格 App Token: {app_token}")
        print()
        print("请将以下配置添加到 .env.production 文件中:")
        print(f"FEISHU_BITABLE_APP_TOKEN={app_token}")
        print()
        print("🔗 访问多维表格:")
        print(f"https://feishu.cn/base/{app_token}")
        print()
        print("📋 下一步:")
        print("1. 复制上面的 App Token 到配置文件")
        print("2. 在飞书中打开多维表格，手动创建以下数据表:")
        print("   - Tasks (任务表)")
        print("   - Persons (人员表)")
        print("3. 或者运行完整的表格创建脚本")
        
        return 0
        
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
