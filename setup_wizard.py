#!/usr/bin/env python3
"""
飞书任务机器人配置向导
帮助用户一步步完成配置
"""

import os
import sys
import asyncio
from pathlib import Path

def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🤖 飞书任务机器人配置向导")
    print("=" * 60)
    print()

def get_feishu_config():
    """获取飞书应用配置"""
    print("📱 第一步：配置飞书应用")
    print("请在飞书开放平台创建应用并获取以下信息:")
    print("🔗 https://open.feishu.cn/app")
    print()
    
    config = {}
    
    # 获取App ID
    while True:
        app_id = input("请输入 App ID: ").strip()
        if app_id:
            config['FEISHU_APP_ID'] = app_id
            break
        print("❌ App ID 不能为空")
    
    # 获取App Secret
    while True:
        app_secret = input("请输入 App Secret: ").strip()
        if app_secret:
            config['FEISHU_APP_SECRET'] = app_secret
            break
        print("❌ App Secret 不能为空")
    
    # 获取Verify Token
    while True:
        verify_token = input("请输入 Verify Token: ").strip()
        if verify_token:
            config['FEISHU_VERIFY_TOKEN'] = verify_token
            break
        print("❌ Verify Token 不能为空")
    
    # 获取Encrypt Key（可选）
    encrypt_key = input("请输入 Encrypt Key (可选，直接回车跳过): ").strip()
    if encrypt_key:
        config['FEISHU_ENCRYPT_KEY'] = encrypt_key
    
    return config

def get_llm_config():
    """获取LLM配置"""
    print("\n🧠 第二步：配置LLM服务")
    print("请选择要使用的LLM服务 (可多选):")
    print("1. DeepSeek (推荐，性价比高)")
    print("2. OpenAI GPT")
    print("3. Google Gemini")
    print()
    
    config = {}
    
    # DeepSeek配置
    if input("是否配置 DeepSeek? (y/n): ").lower().startswith('y'):
        api_key = input("请输入 DeepSeek API Key: ").strip()
        if api_key:
            config['DEEPSEEK_API_KEY'] = api_key
            config['DEEPSEEK_BASE_URL'] = 'https://api.deepseek.com'
    
    # OpenAI配置
    if input("是否配置 OpenAI? (y/n): ").lower().startswith('y'):
        api_key = input("请输入 OpenAI API Key: ").strip()
        if api_key:
            config['OPENAI_API_KEY'] = api_key
            config['OPENAI_BASE_URL'] = 'https://api.openai.com/v1'
    
    # Google Gemini配置
    if input("是否配置 Google Gemini? (y/n): ").lower().startswith('y'):
        api_key = input("请输入 Google API Key: ").strip()
        if api_key:
            config['GOOGLE_API_KEY'] = api_key
    
    return config

def get_github_config():
    """获取GitHub配置"""
    print("\n🔧 第三步：配置GitHub集成 (可选)")
    print("如果需要CI集成功能，请配置GitHub Webhook Secret")
    print()
    
    config = {}
    
    if input("是否配置 GitHub 集成? (y/n): ").lower().startswith('y'):
        webhook_secret = input("请输入 GitHub Webhook Secret: ").strip()
        if webhook_secret:
            config['GITHUB_WEBHOOK_SECRET'] = webhook_secret
    
    return config

async def create_bitable(feishu_config):
    """创建多维表格"""
    print("\n📊 第四步：创建多维表格")
    print("正在为您创建任务管理所需的多维表格...")
    print()
    
    # 设置环境变量
    os.environ.update(feishu_config)
    
    try:
        # 导入并运行多维表格创建脚本
        sys.path.append('.')
        from setup_bitable import main as setup_main
        
        result = await setup_main()
        if result == 0:
            # 从输出中提取app_token（这里简化处理）
            print("✅ 多维表格创建成功！")
            app_token = input("请输入刚才创建的 App Token: ").strip()
            return {'FEISHU_BITABLE_APP_TOKEN': app_token}
        else:
            print("❌ 多维表格创建失败")
            return {}
    except Exception as e:
        print(f"❌ 创建多维表格时出错: {e}")
        print("您可以稍后手动运行: python setup_bitable.py")
        return {}

def save_config(config):
    """保存配置到文件"""
    print("\n💾 第五步：保存配置")
    
    # 合并所有配置
    all_config = {}
    for cfg in config:
        all_config.update(cfg)
    
    # 添加默认配置
    all_config.update({
        'APP_DEBUG': 'false',
        'APP_LOG_LEVEL': 'INFO',
        'APP_HOST': '0.0.0.0',
        'APP_PORT': '8000'
    })
    
    # 写入配置文件
    config_file = Path('.env.production')
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write("# 飞书任务机器人生产环境配置\n")
        f.write("# 由配置向导自动生成\n\n")
        
        f.write("# 飞书应用配置\n")
        for key in ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_VERIFY_TOKEN', 'FEISHU_ENCRYPT_KEY', 'FEISHU_BITABLE_APP_TOKEN']:
            if key in all_config:
                f.write(f"{key}={all_config[key]}\n")
        
        f.write("\n# LLM服务配置\n")
        for key in ['DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'GOOGLE_API_KEY']:
            if key in all_config:
                f.write(f"{key}={all_config[key]}\n")
        
        f.write("\n# GitHub集成配置\n")
        if 'GITHUB_WEBHOOK_SECRET' in all_config:
            f.write(f"GITHUB_WEBHOOK_SECRET={all_config['GITHUB_WEBHOOK_SECRET']}\n")
        
        f.write("\n# 应用配置\n")
        for key in ['APP_DEBUG', 'APP_LOG_LEVEL', 'APP_HOST', 'APP_PORT']:
            f.write(f"{key}={all_config[key]}\n")
    
    print(f"✅ 配置已保存到: {config_file}")
    return config_file

async def main():
    """主函数"""
    print_banner()
    
    try:
        # 收集配置
        configs = []
        
        # 1. 飞书配置
        feishu_config = get_feishu_config()
        configs.append(feishu_config)
        
        # 2. LLM配置
        llm_config = get_llm_config()
        configs.append(llm_config)
        
        # 3. GitHub配置
        github_config = get_github_config()
        configs.append(github_config)
        
        # 4. 创建多维表格
        if input("\n是否现在创建多维表格? (y/n): ").lower().startswith('y'):
            bitable_config = await create_bitable(feishu_config)
            configs.append(bitable_config)
        else:
            print("⚠️  您可以稍后运行以下命令创建多维表格:")
            print("   python setup_bitable.py")
        
        # 5. 保存配置
        config_file = save_config(configs)
        
        # 6. 完成提示
        print("\n" + "="*60)
        print("🎉 配置完成！")
        print("="*60)
        print("下一步操作:")
        print("1. 检查配置文件:", config_file)
        print("2. 启动应用: conda activate feishu && python start_production.py")
        print("3. 配置飞书应用的事件订阅和回调地址")
        print()
        print("🔗 有用的链接:")
        print("   飞书开放平台: https://open.feishu.cn/")
        print("   应用管理: https://open.feishu.cn/app")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
        return 1
    except Exception as e:
        print(f"\n❌ 配置过程中出错: {e}")
        return 1

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
