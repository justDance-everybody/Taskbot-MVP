#!/usr/bin/env python3
"""
显示多维表格访问链接的脚本
"""

import os
from pathlib import Path

def load_env_file():
    """加载 .env.production 文件"""
    env_file = Path(".env.production")
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_bitable_info():
    """从环境变量获取多维表格信息"""
    # 先尝试加载 .env.production 文件
    load_env_file()

    app_token = os.getenv('FEISHU_BITABLE_APP_TOKEN')
    task_table_id = os.getenv('FEISHU_TASK_TABLE_ID')
    person_table_id = os.getenv('FEISHU_PERSON_TABLE_ID')

    return {
        'app_token': app_token,
        'task_table_id': task_table_id,
        'person_table_id': person_table_id
    }

def main():
    """主函数"""
    print("🔍 正在查找多维表格链接...")

    # 从环境变量获取配置
    bitable_info = get_bitable_info()
    app_token = bitable_info['app_token']

    if not app_token:
        print("❌ 未找到 FEISHU_BITABLE_APP_TOKEN 环境变量")
        print("请确保已设置以下环境变量：")
        print("  • FEISHU_BITABLE_APP_TOKEN")
        print("  • FEISHU_TASK_TABLE_ID")
        print("  • FEISHU_PERSON_TABLE_ID")
        return
    
    # 构建链接
    bitable_url = f"https://feishu.cn/base/{app_token}"
    
    print("\n" + "="*60)
    print("📊 飞书多维表格访问信息")
    print("="*60)
    print(f"\n🔗 主表格链接：")
    print(f"   {bitable_url}")
    print(f"\n📋 包含的数据表：")
    print(f"   • Tasks - 任务管理表")
    print(f"   • Persons - 人员信息表")
    print(f"\n💡 使用说明：")
    print(f"   • 点击链接可直接在浏览器中打开")
    print(f"   • 在飞书APP中打开可获得更好体验")
    print(f"   • 支持查看、编辑、导出数据")
    print(f"   • 可以创建自定义视图和筛选")
    
    print(f"\n📱 快捷访问方式：")
    print(f"   • 电脑端：复制链接到浏览器")
    print(f"   • 手机端：在飞书APP中打开链接")
    print(f"   • 机器人：发送 '表格' 命令获取链接")
    
    print(f"\n🤖 机器人命令：")
    print(f"   • 表格 - 获取表格链接")
    print(f"   • 表格信息 - 获取详细统计")
    print(f"   • #report - 查看任务日报")
    
    print("\n" + "="*60)
    
    # 尝试在浏览器中打开
    try:
        import webbrowser
        open_browser = input("\n是否在浏览器中打开表格？(y/N): ").lower().strip()
        if open_browser in ['y', 'yes', '是']:
            webbrowser.open(bitable_url)
            print("✅ 已在浏览器中打开表格")
    except ImportError:
        pass

if __name__ == "__main__":
    main()
