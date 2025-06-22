#!/usr/bin/env python3
"""
添加测试数据到飞书多维表格
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv('.env.production')

# 导入应用模块
try:
    from app.services.bitable import BitableClient
except ImportError:
    print("❌ 无法导入BitableClient，请确保在项目根目录运行此脚本")
    sys.exit(1)

async def add_test_persons():
    """添加测试人员数据"""
    print("🧪 添加测试人员数据...")
    
    client = BitableClient()
    
    # 测试人员数据
    test_persons = [
        {
            "name": "张三",
            "user_id": "zhang_san_001",
            "email": "zhangsan@company.com",
            "skill_tags": ["Python", "FastAPI", "MySQL", "Docker"],
            "status": "可用",
            "workload": 60,
            "rating": 85,
            "completed_tasks": 12,
            "activity": 90
        },
        {
            "name": "李四", 
            "user_id": "li_si_002",
            "email": "lisi@company.com",
            "skill_tags": ["JavaScript", "React", "Node.js", "MongoDB"],
            "status": "可用",
            "workload": 40,
            "rating": 92,
            "completed_tasks": 15,
            "activity": 95
        },
        {
            "name": "王五",
            "user_id": "wang_wu_003", 
            "email": "wangwu@company.com",
            "skill_tags": ["Java", "Spring", "MySQL", "Redis"],
            "status": "可用",
            "workload": 70,
            "rating": 88,
            "completed_tasks": 8,
            "activity": 85
        },
        {
            "name": "赵六",
            "user_id": "zhao_liu_004",
            "email": "zhaoliu@company.com", 
            "skill_tags": ["Go", "Kubernetes", "Docker", "PostgreSQL"],
            "status": "忙碌",
            "workload": 90,
            "rating": 90,
            "completed_tasks": 20,
            "activity": 88
        },
        {
            "name": "钱七",
            "user_id": "qian_qi_005",
            "email": "qianqi@company.com",
            "skill_tags": ["Python", "Django", "PostgreSQL", "AWS"],
            "status": "可用", 
            "workload": 30,
            "rating": 87,
            "completed_tasks": 10,
            "activity": 92
        }
    ]
    
    added_count = 0
    for person in test_persons:
        try:
            record_id = await client.create_person(
                name=person["name"],
                user_id=person["user_id"],
                email=person["email"],
                skill_tags=person["skill_tags"],
                status=person["status"],
                workload=person["workload"],
                rating=person["rating"],
                completed_tasks=person["completed_tasks"],
                activity=person["activity"]
            )
            print(f"✅ 添加人员: {person['name']} (ID: {record_id})")
            added_count += 1
        except Exception as e:
            print(f"❌ 添加人员失败 {person['name']}: {e}")
    
    print(f"\n🎉 成功添加 {added_count} 个测试人员")
    return added_count

async def add_test_tasks():
    """添加测试任务数据"""
    print("\n🧪 添加测试任务数据...")
    
    client = BitableClient()
    
    # 测试任务数据
    test_tasks = [
        {
            "title": "用户登录功能开发",
            "description": "实现用户注册、登录、密码重置功能，包括前端页面和后端API",
            "task_type": "开发",
            "priority": "高",
            "skill_tags": ["Python", "FastAPI", "React", "MySQL"],
            "estimated_hours": 16,
            "publisher": "HR张经理"
        },
        {
            "title": "数据库性能优化",
            "description": "优化用户查询和订单查询的SQL性能，添加必要的索引",
            "task_type": "优化",
            "priority": "中",
            "skill_tags": ["MySQL", "SQL", "性能优化"],
            "estimated_hours": 8,
            "publisher": "技术总监"
        },
        {
            "title": "API文档编写",
            "description": "为新开发的用户管理API编写详细的接口文档",
            "task_type": "文档",
            "priority": "中",
            "skill_tags": ["API设计", "文档编写"],
            "estimated_hours": 4,
            "publisher": "产品经理"
        }
    ]
    
    added_count = 0
    for task in test_tasks:
        try:
            record_id = await client.create_task(
                title=task["title"],
                description=task["description"],
                task_type=task["task_type"],
                priority=task["priority"],
                skill_tags=task["skill_tags"],
                estimated_hours=task["estimated_hours"],
                publisher=task["publisher"]
            )
            print(f"✅ 添加任务: {task['title']} (ID: {record_id})")
            added_count += 1
        except Exception as e:
            print(f"❌ 添加任务失败 {task['title']}: {e}")
    
    print(f"\n🎉 成功添加 {added_count} 个测试任务")
    return added_count

async def main():
    """主函数"""
    print("🚀 开始添加测试数据...")
    print("=" * 50)
    
    try:
        # 添加测试人员
        persons_added = await add_test_persons()
        
        # 添加测试任务
        tasks_added = await add_test_tasks()
        
        print("\n" + "=" * 50)
        print("🎉 测试数据添加完成！")
        print(f"📊 统计:")
        print(f"   - 人员: {persons_added} 个")
        print(f"   - 任务: {tasks_added} 个")
        print("\n🔗 查看多维表格:")
        print(f"   https://feishu.cn/base/{os.getenv('FEISHU_BITABLE_APP_TOKEN')}")
        
    except Exception as e:
        print(f"❌ 添加测试数据失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
