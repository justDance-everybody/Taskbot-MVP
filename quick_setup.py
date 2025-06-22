#!/usr/bin/env python3
"""
快速配置向导
简化版配置流程
"""

import os
import sys
from pathlib import Path

def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🤖 飞书任务机器人快速配置向导")
    print("=" * 60)
    print()

def get_feishu_config():
    """获取飞书应用配置"""
    print("📱 步骤1：配置飞书应用")
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
    
    return config

def get_bitable_token():
    """获取多维表格Token"""
    print("\n📊 步骤2：配置多维表格")
    print("选择配置方式:")
    print("1. 自动创建新的多维表格")
    print("2. 使用现有的多维表格")
    print()
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == "1":
        print("\n正在创建多维表格...")
        return create_new_bitable()
    elif choice == "2":
        token = input("请输入现有多维表格的 App Token: ").strip()
        if token:
            return {'FEISHU_BITABLE_APP_TOKEN': token}
        else:
            print("❌ Token 不能为空")
            return {}
    else:
        print("❌ 无效选择")
        return {}

def create_new_bitable():
    """创建新的多维表格"""
    try:
        # 运行简化创建脚本
        import subprocess
        result = subprocess.run([
            sys.executable, 'create_bitable_simple.py'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 多维表格创建成功！")
            # 从输出中提取token
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'App Token:' in line:
                    token = line.split('App Token:')[1].strip()
                    return {'FEISHU_BITABLE_APP_TOKEN': token}
            
            # 如果没有找到token，让用户手动输入
            print("请从上面的输出中复制 App Token:")
            token = input("App Token: ").strip()
            if token:
                return {'FEISHU_BITABLE_APP_TOKEN': token}
        else:
            print("❌ 多维表格创建失败")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ 创建多维表格时出错: {e}")
    
    return {}

def get_llm_config():
    """获取LLM配置"""
    print("\n🧠 步骤3：配置LLM服务 (至少选择一个)")
    
    config = {}
    
    # DeepSeek配置
    if input("是否配置 DeepSeek? (推荐) (y/n): ").lower().startswith('y'):
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
    
    # 检查是否至少配置了一个LLM
    if not any(key.endswith('_API_KEY') for key in config.keys()):
        print("⚠️  警告: 未配置任何LLM服务，机器人将无法进行智能匹配")
    
    return config

def save_config(configs):
    """保存配置到文件"""
    print("\n💾 步骤4：保存配置")
    
    # 合并所有配置
    all_config = {}
    for cfg in configs:
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
        f.write("# 由快速配置向导生成\n\n")
        
        f.write("# 飞书应用配置\n")
        for key in ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_VERIFY_TOKEN', 'FEISHU_BITABLE_APP_TOKEN']:
            if key in all_config:
                f.write(f"{key}={all_config[key]}\n")
        
        f.write("\n# LLM服务配置\n")
        for key in ['DEEPSEEK_API_KEY', 'DEEPSEEK_BASE_URL', 'OPENAI_API_KEY', 'OPENAI_BASE_URL']:
            if key in all_config:
                f.write(f"{key}={all_config[key]}\n")
        
        f.write("\n# 应用配置\n")
        for key in ['APP_DEBUG', 'APP_LOG_LEVEL', 'APP_HOST', 'APP_PORT']:
            f.write(f"{key}={all_config[key]}\n")
    
    print(f"✅ 配置已保存到: {config_file}")
    return config_file

def main():
    """主函数"""
    print_banner()
    
    try:
        # 收集配置
        configs = []
        
        # 1. 飞书配置
        feishu_config = get_feishu_config()
        configs.append(feishu_config)
        
        # 设置环境变量供后续使用
        os.environ.update(feishu_config)
        
        # 2. 多维表格配置
        bitable_config = get_bitable_token()
        configs.append(bitable_config)
        
        # 3. LLM配置
        llm_config = get_llm_config()
        configs.append(llm_config)
        
        # 4. 保存配置
        config_file = save_config(configs)
        
        # 5. 完成提示
        print("\n" + "="*60)
        print("🎉 快速配置完成！")
        print("="*60)
        print("下一步操作:")
        print("1. 检查配置文件:", config_file)
        print("2. 启动应用:")
        print("   conda activate feishu")
        print("   python start_production.py")
        print("3. 配置飞书应用的事件订阅:")
        print("   回调地址: http://your-domain:8000/webhook/feishu")
        print()
        print("📋 多维表格配置:")
        if 'FEISHU_BITABLE_APP_TOKEN' in bitable_config:
            token = bitable_config['FEISHU_BITABLE_APP_TOKEN']
            print(f"   访问地址: https://feishu.cn/base/{token}")
            print("   请在多维表格中创建以下数据表:")
            print("   - Tasks (任务表)")
            print("   - Persons (人员表)")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
        return 1
    except Exception as e:
        print(f"\n❌ 配置过程中出错: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
