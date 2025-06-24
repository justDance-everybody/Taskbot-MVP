#!/bin/bash

# 飞书任务机器人完整配置脚本

set -e  # 遇到错误立即退出

echo "🚀 飞书任务机器人完整配置..."
echo "=" * 50

# 1. 检查conda环境
echo "📋 检查conda环境..."
if ! conda info --envs | grep -q "feishu"; then
    echo "❌ 未找到feishu conda环境"
    exit 1
fi

# 2. 激活环境
echo "🔧 激活feishu环境..."
source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null || source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate feishu

# 3. 检查配置文件
echo "⚙️  检查配置文件..."
if [ ! -f ".env.production" ]; then
    echo "❌ 未找到.env.production配置文件"
    echo "请先配置飞书应用信息"
    exit 1
fi

# 4. 加载环境变量
echo "📦 加载环境变量..."
export $(cat .env.production | grep -v '^#' | grep -v '^$' | xargs)

# 5. 检查必需配置
echo "🔍 检查必需配置..."
if [ -z "$FEISHU_APP_ID" ] || [ -z "$FEISHU_APP_SECRET" ]; then
    echo "❌ 缺少飞书应用配置"
    echo "请在.env.production中配置FEISHU_APP_ID和FEISHU_APP_SECRET"
    exit 1
fi

# 6. 测试基本API连接
echo "🧪 测试API连接..."
python -c "
import sys
sys.path.append('.')
try:
    from test_bitable_simple import test_create_app_only
    import asyncio
    result = asyncio.run(test_create_app_only())
    if result:
        print('✅ API连接测试成功')
        exit(0)
    else:
        print('❌ API连接测试失败')
        exit(1)
except Exception as e:
    print(f'❌ 测试失败: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ 基本配置验证通过"
else
    echo "❌ 基本配置验证失败，请检查飞书应用配置"
    exit 1
fi

# 7. 创建多维表格
echo "📊 创建多维表格..."
if [ -z "$FEISHU_BITABLE_APP_TOKEN" ]; then
    echo "正在创建多维表格..."
    python create_bitable_correct.py
    
    if [ $? -eq 0 ]; then
        echo "✅ 多维表格创建成功"
        echo "请将生成的FEISHU_BITABLE_APP_TOKEN添加到.env.production文件中"
    else
        echo "❌ 多维表格创建失败"
        exit 1
    fi
else
    echo "✅ 多维表格配置已存在"
fi

# 8. 验证完整配置
echo "🔍 验证完整配置..."
python -c "
import sys
import os
sys.path.append('.')

# 重新加载环境变量
from dotenv import load_dotenv
load_dotenv('.env.production')

try:
    from app.main import app
    print('✅ 应用配置验证成功')
except Exception as e:
    print(f'❌ 应用配置验证失败: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ 完整配置验证通过"
else
    echo "❌ 完整配置验证失败"
    exit 1
fi

echo ""
echo "=" * 50
echo "🎉 配置完成！"
echo "=" * 50
echo "下一步："
echo "1. 启动应用: python start_production.py"
echo "2. 配置飞书应用的事件订阅"
echo "3. 测试机器人功能"
echo ""
