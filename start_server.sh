#!/bin/bash

echo "🚀 启动飞书任务管理机器人服务..."
echo ""
echo "📋 服务信息："
echo "  - 地址: http://0.0.0.0:8000"
echo "  - Webhook: http://0.0.0.0:8000/webhooks/feishu"
echo "  - API文档: http://0.0.0.0:8000/docs"
echo ""
echo "⚠️  注意事项："
echo "  1. 确保已在飞书开放平台订阅 'card.action.trigger' 事件"
echo "  2. 确保webhook地址配置正确"
echo "  3. 查看日志: tail -f app.log"
echo ""
echo "🔄 启动中..."
echo ""

# 启动服务
python main.py
