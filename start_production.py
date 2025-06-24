#!/usr/bin/env python3
"""
生产环境启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动生产环境"""
    print("🚀 启动飞书任务机器人生产环境...")
    
    # 检查配置文件
    env_file = Path(".env.production")
    if not env_file.exists():
        print("❌ 未找到 .env.production 配置文件")
        print("请先配置您的飞书应用信息")
        return 1
    
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv(".env.production")
    
    # 检查必需的环境变量
    required_vars = [
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET", 
        "FEISHU_VERIFY_TOKEN",
        "FEISHU_BITABLE_APP_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ 以下环境变量未配置:")
        for var in missing_vars:
            print(f"   - {var}")
        print("请在 .env.production 文件中配置这些变量")
        return 1
    
    # 验证应用
    try:
        sys.path.append('.')
        from app.main import app
        print("✅ 应用验证成功")
    except Exception as e:
        print(f"❌ 应用验证失败: {e}")
        return 1
    
    # 获取配置
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    log_level = os.getenv("APP_LOG_LEVEL", "INFO").lower()  # 转换为小写
    
    print(f"📡 启动服务器: http://{host}:{port}")
    print(f"📋 日志级别: {log_level}")
    print("按 Ctrl+C 停止服务")
    print("-" * 50)
    
    # 启动uvicorn
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            log_level=log_level,
            access_log=True,
            reload=False,  # 生产环境不使用热重载
            workers=1
        )
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
        return 0
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
