#!/bin/bash

# 飞书任务机器人部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始部署飞书任务机器人..."

# 1. 检查conda环境
echo "📋 检查conda环境..."
if ! conda info --envs | grep -q "feishu"; then
    echo "❌ 未找到feishu conda环境，请先创建环境"
    exit 1
fi

# 2. 激活环境
echo "🔧 激活feishu环境..."
source ~/anaconda3/etc/profile.d/conda.sh
conda activate feishu

# 3. 检查依赖
echo "📦 检查依赖..."
python -c "
import lark_oapi
import fastapi
import uvicorn
print('✅ 所有依赖已安装')
"

# 4. 检查配置文件
echo "⚙️  检查配置文件..."
if [ ! -f ".env.production" ]; then
    echo "❌ 未找到.env.production配置文件"
    echo "请复制.env.production模板并填入真实配置"
    exit 1
fi

# 5. 验证应用
echo "🧪 验证应用..."
python -c "
import sys
import os
sys.path.append('.')

# 加载生产环境配置
from dotenv import load_dotenv
load_dotenv('.env.production')

try:
    from app.main import app
    print('✅ 应用验证成功')
except Exception as e:
    print(f'❌ 应用验证失败: {e}')
    sys.exit(1)
"

# 6. 创建日志目录
echo "📁 创建日志目录..."
mkdir -p logs

# 7. 启动应用
echo "🎯 启动应用..."
echo "应用将在 http://0.0.0.0:8000 启动"
echo "按 Ctrl+C 停止应用"

# 使用生产环境配置启动
export $(cat .env.production | grep -v '^#' | xargs)

# 启动uvicorn服务器
uvicorn app.main:app \
    --host ${APP_HOST:-0.0.0.0} \
    --port ${APP_PORT:-8000} \
    --workers 1 \
    --log-level ${APP_LOG_LEVEL:-info} \
    --access-log \
    --log-config logging.conf 2>/dev/null || \
uvicorn app.main:app \
    --host ${APP_HOST:-0.0.0.0} \
    --port ${APP_PORT:-8000} \
    --workers 1 \
    --log-level ${APP_LOG_LEVEL:-info} \
    --access-log
