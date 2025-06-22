#!/usr/bin/env python3
"""
简单的测试数据添加脚本
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv('.env.production')

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

async def add_test_data():
    """添加测试数据"""
    print("🧪 添加测试数据到多维表格...")
    
    # 创建客户端
    client = lark.Client.builder() \
        .app_id(os.getenv("FEISHU_APP_ID")) \
        .app_secret(os.getenv("FEISHU_APP_SECRET")) \
        .build()
    
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    
    # 获取表格列表
    request = ListAppTableRequest.builder() \
        .app_token(app_token) \
        .build()
    
    response = await client.bitable.v1.app_table.alist(request)
    
    if not response.success():
        print(f"❌ 获取表格列表失败: {response.msg}")
        return
    
    tables = response.data.items
    print(f"📋 找到 {len(tables)} 个表格:")
    
    task_table_id = None
    person_table_id = None
    
    for table in tables:
        print(f"   - {table.name} (ID: {table.table_id})")
        if "task" in table.name.lower() or "任务" in table.name:
            task_table_id = table.table_id
        elif "person" in table.name.lower() or "人员" in table.name:
            person_table_id = table.table_id
    
    # 添加测试人员数据
    if person_table_id:
        print(f"\n👥 添加测试人员到表格: {person_table_id}")
        
        test_persons = [
            {
                "姓名": "张三",
                "用户ID": "zhang_san_001",
                "邮箱": "zhangsan@company.com",
                "技能标签": ["Python", "FastAPI", "MySQL"],  # 多选字段：使用选项名称数组
                "可用状态": "可用",      # 单选字段：使用选项名称
                "工作负载": 60,         # 数字字段：使用数字
                "历史评分": 85,         # 数字字段：使用数字
                "完成任务数": 12,       # 数字字段：使用数字
                "活跃度": 90           # 数字字段：使用数字
            },
            {
                "姓名": "李四",
                "用户ID": "li_si_002",
                "邮箱": "lisi@company.com",
                "技能标签": ["JavaScript", "React", "Node.js"],
                "可用状态": "可用",
                "工作负载": 40,
                "历史评分": 92,
                "完成任务数": 15,
                "活跃度": 95
            },
            {
                "姓名": "王五",
                "用户ID": "wang_wu_003",
                "邮箱": "wangwu@company.com",
                "技能标签": ["Java", "Spring", "MySQL"],  # 使用存在的选项
                "可用状态": "可用",
                "工作负载": 70,
                "历史评分": 88,
                "完成任务数": 8,
                "活跃度": 85
            },
            {
                "姓名": "赵六",
                "用户ID": "zhao_liu_004",
                "邮箱": "zhaoliu@company.com",
                "技能标签": ["Go", "Docker", "Kubernetes"],
                "可用状态": "忙碌",
                "工作负载": 90,
                "历史评分": 90,
                "完成任务数": 20,
                "活跃度": 88
            }
        ]
        
        for person in test_persons:
            try:
                request = CreateAppTableRecordRequest.builder() \
                    .app_token(app_token) \
                    .table_id(person_table_id) \
                    .request_body({
                        "fields": person
                    }) \
                    .build()

                response = await client.bitable.v1.app_table_record.acreate(request)

                if response.success():
                    print(f"✅ 添加人员: {person['姓名']}")
                else:
                    print(f"❌ 添加人员失败 {person['姓名']}: {response.msg}")

            except Exception as e:
                print(f"❌ 添加人员异常 {person['姓名']}: {e}")
    
    # 添加测试任务数据
    if task_table_id:
        print(f"\n📋 添加测试任务到表格: {task_table_id}")
        
        test_tasks = [
            {
                "任务标题": "用户登录功能开发",
                "任务描述": "实现用户注册、登录、密码重置功能，包括前端页面和后端API",
                "任务类型": "开发",  # 单选字段：使用选项名称
                "优先级": "高",      # 单选字段：使用选项名称
                "状态": "待分配",    # 单选字段：使用选项名称
                "技能要求": ["Python", "FastAPI", "React"],  # 多选字段：使用选项名称数组
                "预估工时": 16,      # 数字字段：使用数字
                "发布人": "HR张经理",
                "任务链接": {        # 超链接字段：使用对象格式
                    "text": "GitHub仓库",
                    "link": "https://github.com/company/user-auth"
                }
            },
            {
                "任务标题": "API文档编写",
                "任务描述": "为新开发的用户管理API编写详细的接口文档",
                "任务类型": "文档",
                "优先级": "中",
                "状态": "待分配",
                "技能要求": ["文档编写"],  # 注意：只使用存在的选项
                "预估工时": 4,
                "发布人": "产品经理",
                "任务链接": {
                    "text": "文档站点",
                    "link": "https://docs.company.com/api"
                }
            },
            {
                "任务标题": "数据库性能优化",
                "任务描述": "优化用户查询和订单查询的SQL性能，添加必要的索引",
                "任务类型": "优化",
                "优先级": "中",
                "状态": "待分配",
                "技能要求": ["MySQL", "数据库"],  # 使用存在的选项
                "预估工时": 8,
                "发布人": "技术总监",
                "任务链接": {
                    "text": "优化方案",
                    "link": "https://github.com/company/db-optimization"
                }
            },
            {
                "任务标题": "前端组件库开发",
                "任务描述": "开发公司统一的React组件库，包括按钮、表单、表格等基础组件",
                "任务类型": "开发",
                "优先级": "中",
                "状态": "待分配",
                "技能要求": ["React", "JavaScript"],  # 移除CSS，因为选项中没有
                "预估工时": 24,
                "发布人": "前端负责人",
                "任务链接": {
                    "text": "组件库",
                    "link": "https://github.com/company/ui-components"
                }
            }
        ]
        
        for task in test_tasks:
            try:
                request = CreateAppTableRecordRequest.builder() \
                    .app_token(app_token) \
                    .table_id(task_table_id) \
                    .request_body({
                        "fields": task
                    }) \
                    .build()

                response = await client.bitable.v1.app_table_record.acreate(request)

                if response.success():
                    print(f"✅ 添加任务: {task['任务标题']}")
                else:
                    print(f"❌ 添加任务失败 {task['任务标题']}: {response.msg}")

            except Exception as e:
                print(f"❌ 添加任务异常 {task['任务标题']}: {e}")
    
    print(f"\n🎉 测试数据添加完成！")
    print(f"🔗 查看多维表格: https://feishu.cn/base/{app_token}")

if __name__ == "__main__":
    asyncio.run(add_test_data())
