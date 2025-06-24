#!/usr/bin/env python3
"""
检查多维表格的字段结构
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv('.env.production')

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

async def check_table_fields():
    """检查表格字段结构"""
    print("🔍 检查多维表格字段结构...")
    
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
    
    for table in tables:
        print(f"\n📊 表格: {table.name} (ID: {table.table_id})")
        
        # 获取字段列表
        field_request = ListAppTableFieldRequest.builder() \
            .app_token(app_token) \
            .table_id(table.table_id) \
            .build()
        
        field_response = await client.bitable.v1.app_table_field.alist(field_request)
        
        if field_response.success():
            fields = field_response.data.items
            print(f"   字段数量: {len(fields)}")
            
            for field in fields:
                field_type_name = {
                    1: "单行文本",
                    2: "数字", 
                    3: "单选",
                    4: "多选",
                    5: "日期",
                    7: "复选框",
                    11: "人员",
                    13: "电话号码",
                    15: "超链接",
                    17: "附件",
                    18: "单向关联",
                    19: "查找引用",
                    20: "公式",
                    21: "双向关联",
                    22: "地理位置",
                    23: "群组",
                    1001: "创建时间",
                    1002: "最后更新时间",
                    1003: "创建人",
                    1004: "修改人"
                }.get(field.type, f"未知类型({field.type})")
                
                print(f"   - {field.field_name} (ID: {field.field_id}, 类型: {field_type_name})")
                
                # 如果是选择类型，显示选项
                if hasattr(field, 'property') and field.property:
                    if hasattr(field.property, 'options') and field.property.options:
                        print(f"     选项: {[opt.name for opt in field.property.options]}")
        else:
            print(f"   ❌ 获取字段失败: {field_response.msg}")

if __name__ == "__main__":
    asyncio.run(check_table_fields())
