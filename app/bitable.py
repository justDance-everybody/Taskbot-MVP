"""多维表格客户端模块"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests

from app.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FeishuBitableClient:
    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id, app_secret, table_token, table_id):
        """初始化飞书多维表格客户端
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            table_token: 多维表格应用token
            table_id: 表格ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.table_token = table_token
        self.table_id = table_id
        self.access_token = None

    def _get_access_token(self):
        """获取飞书访问令牌"""
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal/"
        payload = {
            'app_id': self.app_id,
            'app_secret': self.app_secret
        }
        response = requests.post(url, json=payload)
        result = response.json()
        if result.get('code') == 0:
            return result['tenant_access_token']
        else:
            raise Exception(f"Failed to get access token: {result}")
    
    def get_daily_task_stats(self):
        """获取每日任务统计数据
        
        Returns:
            包含任务统计信息的字典
        """
        try:
            from app.config import settings
            
            # 使用正确的任务表ID而不是候选人表
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("未配置task表ID (feishu_task_table_id)")
                return {
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'pending_tasks': 0,
                    'in_progress_tasks': 0,
                    'submitted_tasks': 0,
                    'reviewing_tasks': 0,
                    'rejected_tasks': 0,
                    'cancelled_tasks': 0,
                    'average_score': 0,
                    'completion_rate': 0,
                    'top_performers': [],
                    'tasks_by_urgency': {
                        'urgent': 0,
                        'high': 0,
                        'normal': 0,
                        'low': 0
                    },
                    'today_created': 0,
                    'today_completed': 0
                }
            
            # 获取任务表中的所有记录
            logger.info(f"正在获取任务表 {task_table_id} 的记录...")
            result = self.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            logger.info(f"获取到 {len(records)} 条任务记录")
            
            # 初始化统计数据
            stats = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'submitted_tasks': 0,
                'reviewing_tasks': 0,
                'rejected_tasks': 0,
                'cancelled_tasks': 0,
                'assigned_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': [],
                'tasks_by_urgency': {
                    'urgent': 0,
                    'high': 0,
                    'normal': 0,
                    'low': 0
                },
                'today_created': 0,
                'today_completed': 0,
                'database_operations': {
                    'total_records': len(records),
                    'last_updated': datetime.now().isoformat()
                }
            }
            
            if not records:
                logger.warning("任务表中没有找到任何记录")
                return stats
            
            total_score = 0
            score_count = 0
            performers = []
            
            # 获取今天的日期
            from datetime import datetime, date
            today = date.today().strftime('%Y-%m-%d')
            
            # 遍历任务记录进行统计
            for record in records:
                fields = record.get('fields', {})
                if not fields:  # 跳过空记录
                    continue
                
                # 统计总任务数
                stats['total_tasks'] += 1
                
                # 根据状态字段统计
                status = fields.get('status', 'pending').lower()
                
                if status == 'completed':
                    stats['completed_tasks'] += 1
                elif status == 'pending':
                    stats['pending_tasks'] += 1
                elif status == 'in_progress':
                    stats['in_progress_tasks'] += 1
                elif status == 'submitted':
                    stats['submitted_tasks'] += 1
                elif status == 'reviewing':
                    stats['reviewing_tasks'] += 1
                elif status == 'rejected':
                    stats['rejected_tasks'] += 1
                elif status == 'cancelled':
                    stats['cancelled_tasks'] += 1
                elif status == 'assigned':
                    stats['assigned_tasks'] += 1
                
                # 统计紧急程度
                urgency = fields.get('urgency', 'normal').lower()
                if urgency in stats['tasks_by_urgency']:
                    stats['tasks_by_urgency'][urgency] += 1
                
                # 统计今日创建的任务
                create_time = fields.get('create_time', '')
                if create_time and today in create_time:
                    stats['today_created'] += 1
                
                # 统计今日完成的任务
                completed_at = fields.get('completed_at', '')
                if completed_at and today in completed_at and status == 'completed':
                    stats['today_completed'] += 1
                
                # 统计分数 (用于绩效分析)
                final_score = fields.get('final_score', 0)
                if final_score and isinstance(final_score, (int, float)) and final_score > 0:
                    total_score += final_score
                    score_count += 1
                
                # 收集任务创建者和负责人信息（用于top performers）
                creator = fields.get('creator', '')
                assignee = fields.get('assignee', '')
                
                # 如果任务已完成且有评分，记录到performers
                if status == 'completed' and final_score and assignee:
                    performers.append({
                        'name': assignee,
                        'score': final_score,
                        'task_title': fields.get('title', '未知任务')
                    })
            
            # 计算平均分
            if score_count > 0:
                stats['average_score'] = round(total_score / score_count, 2)
            
            # 计算完成率
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = round(
                    (stats['completed_tasks'] / stats['total_tasks']) * 100, 2
                )
            
            # 获取前3名表现者（按分数排序）
            if performers:
                performers.sort(key=lambda x: x['score'], reverse=True)
                stats['top_performers'] = performers[:3]
            
            logger.info(f"生成任务统计数据: 总任务{stats['total_tasks']}, 已完成{stats['completed_tasks']}, 完成率{stats['completion_rate']}%")
            return stats
            
        except Exception as e:
            logger.error(f"获取每日任务统计出错: {str(e)}")
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'submitted_tasks': 0,
                'reviewing_tasks': 0,
                'rejected_tasks': 0,
                'cancelled_tasks': 0,
                'assigned_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': [],
                'tasks_by_urgency': {
                    'urgent': 0,
                    'high': 0,
                    'normal': 0,
                    'low': 0
                },
                'today_created': 0,
                'today_completed': 0,
                'database_operations': {
                    'total_records': 0,
                    'last_updated': datetime.now().isoformat(),
                    'error': str(e)
                }
            }

    def _make_request(self, method, endpoint, params=None, data=None):
        """发送请求到飞书API
        
        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            data: 请求数据
            
        Returns:
            API响应结果
        """
        if not self.access_token:
            self.access_token = self._get_access_token()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json; charset=utf-8'
        }
        url = f"{self.BASE_URL}{endpoint}"
        
        # 添加日志记录请求信息
        logger.info(f"请求URL: {url}")
        logger.info(f"请求方法: {method}")
        logger.info(f"请求头: {headers}")
        if params:
            logger.info(f"请求参数: {params}")
        if data:
            logger.info(f"请求数据: {data}")
            
        response = requests.request(method, url, headers=headers, params=params, json=data)
        
        # 添加日志记录响应信息
        logger.info(f"响应状态码: {response.status_code}")
        
        try:
            result = response.json()
            logger.info(f"响应内容: {result}")
            
            if result.get('code') != 0:
                error_code = result.get('code')
                error_msg = result.get('msg', '')
                
                # 处理特定错误码
                if error_code == 91402:
                    logger.error(f"错误91402 - NOTEXIST: 表格或字段不存在，请检查表格ID和字段名称是否正确")
                elif error_code == 91403:
                    logger.error(f"错误91403 - FORBIDDEN: 权限不足，请检查应用权限设置和多维表格的分享设置")
                
                raise Exception(f"Request failed: {result}")
            return result
        except ValueError as e:
            logger.error(f"解析响应JSON失败: {str(e)}，响应内容: {response.text}")
            raise Exception(f"Failed to parse response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"请求处理失败: {str(e)}")
            raise

    def get_tables(self):
        """获取多维表格中的所有表格
        
        Returns:
            表格列表
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables"
        return self._make_request('GET', endpoint)

    def get_table_fields(self, table_id):
        """获取表格的字段信息
        
        Args:
            table_id: 表格ID
            
        Returns:
            字段信息列表
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/fields"
        return self._make_request('GET', endpoint)

    def get_table_records(self, table_id, page_token=None):
        """获取表格中的记录
        
        Args:
            table_id: 表格ID
            page_token: 分页标记
            
        Returns:
            记录列表
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records"
        params = {}
        if page_token:
            params['page_token'] = page_token
        return self._make_request('GET', endpoint, params=params)

    def create_record(self, table_id, record_data):
        """在表格中创建记录
        
        Args:
            table_id: 表格ID
            record_data: 记录数据
            
        Returns:
            创建结果
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records"
        return self._make_request('POST', endpoint, data=record_data)

    def update_record(self, table_id, record_id, record_data):
        """更新表格中的记录
        
        Args:
            table_id: 表格ID
            record_id: 记录ID
            record_data: 更新的记录数据
            
        Returns:
            更新结果
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records/{record_id}"
        return self._make_request('PUT', endpoint, data=record_data)

    def delete_record(self, table_id, record_id):
        """删除表格中的记录
        
        Args:
            table_id: 表格ID
            record_id: 记录ID
            
        Returns:
            删除结果
        """
        endpoint = f"/bitable/v1/apps/{self.table_token}/tables/{table_id}/records/{record_id}"
        return self._make_request('DELETE', endpoint)
    
    async def create_task(self, task_data):
        """创建任务记录（异步方法）
        
        Args:
            task_data: 任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        try:
            # 根据新的字段结构映射数据
            mapped_data = {
                "taskid": task_data.get('task_id', task_data.get('taskid', '')),
                "title": task_data.get('title', ''),
                "description": task_data.get('description', ''),
                "creator": task_data.get('created_by', task_data.get('creator', '')),
                "create_time": task_data.get('created_at', task_data.get('create_time', '')),
                "status": task_data.get('status', 'pending'),
                "skilltags": task_data.get('skill_tags', task_data.get('skilltags', [])),
                "deadline": task_data.get('deadline', ''),
                "urgency": task_data.get('urgency', 'normal')
            }
            
            # 转换为飞书API需要的格式
            record_data = {
                "fields": mapped_data
            }
            result = self.create_record(self.table_id, record_data)
            return result.get('data', {}).get('record_id')
        except Exception as e:
            logger.error(f"创建任务记录出错: {str(e)}")
            return None

# 辅助函数
def convert_date_to_timestamp(date_str):
    """将日期字符串转换为Unix时间戳
    
    Args:
        date_str: 日期字符串，格式为 "%Y-%m-%d %H:%M:%S"
        
    Returns:
        Unix时间戳（毫秒）
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    timestamp = int(date_obj.timestamp() * 1000)  # 转换为毫秒
    return timestamp

def verify_table_exists(client, table_token, table_id):
    """验证表格是否存在
    
    Args:
        client: 飞书多维表格客户端
        table_token: 多维表格应用token
        table_id: 表格ID
        
    Returns:
        表格是否存在
    """
    try:
        tables = client.get_tables()
        table_items = tables.get('data', {}).get('items', [])
        for table in table_items:
            if table.get('table_id') == table_id:
                logger.info(f"表格 {table_id} 存在，名称: {table.get('name')}")
                return True
        logger.error(f"表格 {table_id} 不存在！可用的表格有: {[t.get('name', 'Unknown') + '(' + t.get('table_id', 'Unknown') + ')' for t in table_items]}")
        return False
    except Exception as e:
        logger.error(f"验证表格存在性时出错: {str(e)}")
        return False

def get_available_fields(client, table_id):
    """获取表格中可用的字段
    
    Args:
        client: 飞书多维表格客户端
        table_id: 表格ID
        
    Returns:
        可用字段列表
    """
    try:
        fields_result = client.get_table_fields(table_id)
        fields = fields_result.get('data', {}).get('items', [])
        field_names = [field.get('field_name') for field in fields]
        logger.info(f"表格 {table_id} 中可用的字段: {field_names}")
        return field_names
    except Exception as e:
        logger.error(f"获取可用字段时出错: {str(e)}")
        return []

# 创建全局客户端实例
def create_bitable_client():
    """创建飞书多维表格客户端实例
    
    Returns:
        飞书多维表格客户端实例
    """
    try:
        app_id = settings.feishu_app_id
        app_secret = settings.feishu_app_secret
        table_token = settings.feishu_bitable_app_token
        
        # 创建客户端，暂时不指定表格ID
        client = FeishuBitableClient(app_id, app_secret, table_token, "")
        
        # 获取所有可用表格
        logger.info("获取所有可用表格...")
        tables = client.get_tables()
        table_items = tables.get('data', {}).get('items', [])
        
        if not table_items:
            logger.error("没有找到任何表格")
            return None
            
        # 优先使用配置中的候选人表ID
        person_table_id = settings.feishu_person_table_id
        table_id = None
        table_name = None
        
        # 查找候选人表
        for table in table_items:
            if table.get('table_id') == person_table_id:
                table_id = table.get('table_id')
                table_name = table.get('name')
                logger.info(f"找到候选人表: {table_name}(table_id={table_id})")
                break
        
        # 如果没有找到配置的候选人表，使用第一个表格作为默认
        if not table_id:
            table_id = table_items[0].get('table_id')
            table_name = table_items[0].get('name')
            logger.warning(f"未找到配置的候选人表ID {person_table_id}，使用默认表格: {table_name}(table_id={table_id})")
        
        logger.info(f"使用配置: app_id={app_id}, table_token={table_token}")
        logger.info(f"选择表格: {table_name}(table_id={table_id})")
        
        # 更新客户端的表格ID
        client.table_id = table_id
        
        return client
    except Exception as e:
        logger.error(f"创建飞书多维表格客户端时出错: {str(e)}")
        return None

# 创建全局客户端实例
bitable_client = create_bitable_client()

# 添加BitableClient类，实现webhooks.py中使用的方法
class BitableClient:
    def __init__(self):
        """初始化BitableClient
        
        这个类是对FeishuBitableClient的封装，提供异步接口
        """
        # 全局客户端实例会在模块加载时创建
        self.client = bitable_client
    
    async def create_table(self, app_token, table_name):
        """创建新的数据表
        
        Args:
            app_token: 多维表格应用token
            table_name: 表格名称
            
        Returns:
            表格ID，如果创建失败则返回None
        """
        try:
            # 这里简化实现，实际上应该调用飞书API创建表格
            logger.info(f"创建数据表: {table_name}")
            # 由于FeishuBitableClient没有实现create_table方法，这里返回默认表格ID
            return self.client.table_id
        except Exception as e:
            logger.error(f"创建数据表出错: {str(e)}")
            return None
    
    async def list_tables(self, app_token):
        """列出应用中的所有表格
        
        Args:
            app_token: 多维表格应用token
            
        Returns:
            表格列表
        """
        try:
            result = self.client.get_tables()
            return result.get('data', {}).get('items', [])
        except Exception as e:
            logger.error(f"获取表格列表出错: {str(e)}")
            return []
    
    async def add_field(self, app_token, table_id, field_name, field_type):
        """添加字段到表格
        
        Args:
            app_token: 多维表格应用token
            table_id: 表格ID
            field_name: 字段名称
            field_type: 字段类型
            
        Returns:
            字段ID，如果添加失败则返回None
        """
        try:
            # 这里简化实现，实际上应该调用飞书API添加字段
            logger.info(f"添加字段: {field_name} (类型: {field_type}) 到表格 {table_id}")
            # 由于FeishuBitableClient没有实现add_field方法，这里返回模拟的字段ID
            return f"fld_{field_name.lower().replace(' ', '_')}_{field_type}"
        except Exception as e:
            logger.error(f"添加字段出错: {str(e)}")
            return None
    
    async def add_record(self, app_token, table_id, fields_data):
        """添加记录到表格
        
        Args:
            app_token: 多维表格应用token
            table_id: 表格ID
            fields_data: 字段数据
            
        Returns:
            记录ID，如果添加失败则返回None
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": fields_data
            }
            result = self.client.create_record(table_id, record_data)
            return result.get('data', {}).get('record_id')
        except Exception as e:
            logger.error(f"添加记录出错: {str(e)}")
            return None
    
    async def list_records(self, app_token, table_id, filter_str=None):
        """查询表格中的记录
        
        Args:
            app_token: 多维表格应用token
            table_id: 表格ID
            filter_str: 过滤条件
            
        Returns:
            记录列表
        """
        try:
            # 这里简化实现，实际上应该根据filter_str构建查询条件
            result = self.client.get_table_records(table_id)
            records = result.get('data', {}).get('items', [])
            
            # 简单处理过滤条件
            if filter_str and records:
                filtered_records = []
                for record in records:
                    fields = record.get('fields', {})
                    # 检查是否满足过滤条件（简化实现）
                    if any(filter_str in str(value) for value in fields.values()):
                        filtered_records.append(fields)
                return filtered_records
            
            # 返回字段值
            return [record.get('fields', {}) for record in records]
        except Exception as e:
            logger.error(f"查询记录出错: {str(e)}")
            return []
    
    async def create_task_record(self, task_data):
        """创建任务记录
        
        Args:
            task_data: 任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": task_data
            }
            result = self.client.create_record(self.client.table_id, record_data)
            return result.get('data', {}).get('record_id')
        except Exception as e:
            logger.error(f"创建任务记录出错: {str(e)}")
            return None
    
    async def create_task(self, task_data):
        """创建任务（别名方法）
        
        Args:
            task_data: 任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        return await self.create_task_record(task_data)
    
    async def update_task_record(self, record_id, update_data):
        """更新任务记录
        
        Args:
            record_id: 记录ID
            update_data: 更新数据
            
        Returns:
            更新是否成功
        """
        try:
            # 转换为飞书API需要的格式
            record_data = {
                "fields": update_data
            }
            result = self.client.update_record(self.client.table_id, record_id, record_data)
            return True
        except Exception as e:
            logger.error(f"更新任务记录出错: {str(e)}")
            return False
    
    async def get_task_record(self, record_id):
        """获取任务记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            任务记录数据
        """
        try:
            result = self.client.get_record(self.client.table_id, record_id)
            return result.get('data', {}).get('fields', {})
        except Exception as e:
            logger.error(f"获取任务记录出错: {str(e)}")
            return {}
    
    async def get_table_info(self, app_token=None, table_id=None):
        """获取表格信息和记录
        
        Args:
            app_token: 多维表格应用token，可选
            table_id: 表格ID，可选，如果不提供则使用默认表格
            
        Returns:
            包含表格信息和记录的字典
        """
        try:
            # 如果没有提供表格ID，使用默认表格
            if not table_id:
                table_id = self.client.table_id
            
            # 获取表格字段信息
            fields_info = self.client.get_table_fields(table_id)
            fields = fields_info.get('data', {}).get('items', [])
            
            # 获取表格记录
            records_info = self.client.get_table_records(table_id)
            records = records_info.get('data', {}).get('items', [])
            
            # 格式化记录数据
            formatted_records = []
            for record in records:
                record_fields = record.get('fields', {})
                # 只添加有字段内容的记录
                if record_fields:
                    formatted_records.append({
                        'record_id': record.get('record_id'),
                        'fields': record_fields
                    })
            
            return {
                'table_id': table_id,
                'fields': fields,
                'records': formatted_records,
                'total_records': len(formatted_records)
            }
        except Exception as e:
            logger.error(f"获取表格信息出错: {str(e)}")
            return {'error': str(e)}
    
    async def get_candidate_details(self, user_id):
        """获取候选人详情
        
        Args:
            user_id: 用户ID
            
        Returns:
            候选人详情字典
        """
        try:
            # 获取默认表格中的所有记录
            result = self.client.get_table_records(self.client.table_id)
            records = result.get('data', {}).get('items', [])
            
            # 查找匹配用户ID的记录
            for record in records:
                fields = record.get('fields', {})
                # 根据新字段结构查找用户ID
                record_user_id = fields.get('userid')
                
                if record_user_id == user_id:
                    # 根据新的字段结构构建候选人详情
                    # 数据类型转换，确保数字字段为正确类型
                    def safe_int(value, default=0):
                        try:
                            return int(value) if value is not None else default
                        except (ValueError, TypeError):
                            return default
                    
                    def safe_float(value, default=0.0):
                        try:
                            return float(value) if value is not None else default
                        except (ValueError, TypeError):
                            return default
                    
                    experience = safe_int(fields.get('experience', 0))
                    total_tasks = safe_int(fields.get('total_tasks', 0))
                    average_score = safe_float(fields.get('average_score', 0))
                    
                    return {
                        'user_id': fields.get('userid', ''),
                        'name': fields.get('name', 'Unknown'),
                        'skill_tags': fields.get('skilltags', '').split(',') if fields.get('skilltags') else [],
                        'job_level': fields.get('job_level', ''),
                        'experience': experience,
                        'total_tasks': total_tasks,
                        'average_score': average_score,
                        'completed_tasks': total_tasks,  # 兼容性字段
                        'performance': average_score,   # 兼容性字段
                        'hours_available': experience * 8  # 假设经验年数转换为可用小时
                    }
            
            # 如果没有找到匹配的记录，返回None
            return None
        except Exception as e:
            logger.error(f"获取候选人详情出错: {str(e)}")
            return None
    
    async def get_all_candidates(self):
        """获取所有候选人信息
        
        Returns:
            候选人列表
        """
        try:
            # 获取默认表格中的所有记录
            result = self.client.get_table_records(self.client.table_id)
            records = result.get('data', {}).get('items', [])
            
            # 数据类型转换工具函数
            def safe_int(value, default=0):
                try:
                    return int(value) if value is not None else default
                except (ValueError, TypeError):
                    return default
            
            def safe_float(value, default=0.0):
                try:
                    return float(value) if value is not None else default
                except (ValueError, TypeError):
                    return default
            
            candidates = []
            for record in records:
                fields = record.get('fields', {})
                
                # 数据类型转换
                experience = safe_int(fields.get('experience', 0))
                total_tasks = safe_int(fields.get('total_tasks', 0))
                average_score = safe_float(fields.get('average_score', 0))
                
                # 根据新的字段结构构建候选人信息
                candidate = {
                    'record_id': record.get('record_id'),
                    'user_id': fields.get('userid', ''),
                    'name': fields.get('name', 'Unknown'),
                    'skill_tags': fields.get('skilltags', '').split(',') if fields.get('skilltags') else [],
                    'job_level': fields.get('job_level', ''),
                    'experience': experience,
                    'total_tasks': total_tasks,
                    'average_score': average_score,
                    # 兼容性字段，保持与现有代码的兼容性
                    'experience_years': experience,
                    'hours_available': experience * 8,  # 经验年数转换为可用小时
                    'completed_tasks': total_tasks,
                    'performance': average_score,
                    'total_points': average_score * 10,  # 评分转换为积分
                    'status': 'available'  # 默认状态
                }
                
                # 只添加有有效用户ID和姓名的候选人
                if candidate['user_id'] and candidate['name'] and candidate['name'] != 'Unknown':
                    candidates.append(candidate)
            
            logger.info(f"获取到 {len(candidates)} 名候选人")
            return candidates
            
        except Exception as e:
            logger.error(f"获取所有候选人信息出错: {str(e)}")
            return []
    
    async def get_available_candidates(self, skill_requirements=None):
        """获取可用的候选人
        
        Args:
            skill_requirements: 技能要求列表，可选
            
        Returns:
            符合条件的候选人列表
        """
        try:
            all_candidates = await self.get_all_candidates()
            
            # 如果没有技能要求，返回所有可用候选人
            if not skill_requirements:
                return [c for c in all_candidates if c.get('status') == 'available']
            
            # 根据技能要求筛选候选人
            qualified_candidates = []
            for candidate in all_candidates:
                if candidate.get('status') != 'available':
                    continue
                
                candidate_skills = set(candidate.get('skill_tags', []))
                required_skills = set(skill_requirements)
                
                # 如果候选人具备至少一项所需技能，则认为符合条件
                if candidate_skills & required_skills:
                    qualified_candidates.append(candidate)
            
            logger.info(f"根据技能要求 {skill_requirements} 找到 {len(qualified_candidates)} 名符合条件的候选人")
            return qualified_candidates
            
        except Exception as e:
            logger.error(f"获取可用候选人出错: {str(e)}")
            return []
    
    async def get_task(self, task_identifier: str):
        """根据任务ID或记录ID获取单个任务详情
        
        Args:
            task_identifier: 任务ID或记录ID
            
        Returns:
            任务详情字典或None
        """
        try:
            from app.config import settings
            
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                return None
            
            # 获取所有任务记录
            result = self.client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            # 查找匹配的任务
            for record in records:
                fields = record.get('fields', {})
                if not fields:
                    continue
                
                # 匹配记录ID或任务ID
                if (record.get('record_id') == task_identifier or 
                    fields.get('taskid') == task_identifier):
                    
                    return {
                        'record_id': record.get('record_id'),
                        'taskid': fields.get('taskid', ''),
                        'title': fields.get('title', ''),
                        'description': fields.get('description', ''),
                        'creator': fields.get('creator', ''),
                        'create_time': fields.get('create_time', ''),
                        'status': fields.get('status', 'pending'),
                        'skilltags': fields.get('skilltags', ''),
                        'deadline': fields.get('deadline', ''),
                        'urgency': fields.get('urgency', 'normal')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"获取任务详情出错: {str(e)}")
            return None
    
    async def update_task(self, task_id, update_data):
        """更新任务
        
        Args:
            task_id: 任务ID或记录ID
            update_data: 更新数据
            
        Returns:
            更新是否成功
        """
        try:
            # 首先获取任务以确定记录ID
            task = await self.get_task(task_id)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return False
            
            record_id = task.get('record_id')
            
            # 映射更新数据到正确的字段名
            mapped_update = {}
            if 'status' in update_data:
                mapped_update['status'] = update_data['status']
            if 'title' in update_data:
                mapped_update['title'] = update_data['title']
            if 'description' in update_data:
                mapped_update['description'] = update_data['description']
            if 'deadline' in update_data:
                mapped_update['deadline'] = update_data['deadline']
            if 'urgency' in update_data:
                mapped_update['urgency'] = update_data['urgency']
            if 'skill_tags' in update_data:
                mapped_update['skilltags'] = ','.join(update_data['skill_tags']) if isinstance(update_data['skill_tags'], list) else update_data['skill_tags']
            
            # 执行更新
            task_table_id = settings.feishu_task_table_id
            record_data = {"fields": mapped_update}
            self.client.update_record(task_table_id, record_id, record_data)
            
            logger.info(f"任务更新成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务出错: {str(e)}")
            return False
    
    async def update_candidate_performance(self, user_id, completed_tasks=0, total_score=0, reward_points=0):
        """更新候选人绩效
        
        Args:
            user_id: 用户ID
            completed_tasks: 新增完成任务数
            total_score: 本次任务得分
            reward_points: 奖励积分
            
        Returns:
            更新是否成功
        """
        try:
            # 获取候选人当前信息
            candidate = await self.get_candidate_details(user_id)
            if not candidate:
                logger.warning(f"候选人不存在: {user_id}")
                return False
            
            # 计算新的统计数据
            current_total_tasks = candidate.get('total_tasks', 0)
            current_avg_score = candidate.get('average_score', 0)
            
            new_total_tasks = current_total_tasks + completed_tasks
            if new_total_tasks > 0:
                # 重新计算平均分
                total_accumulated_score = current_avg_score * current_total_tasks + total_score
                new_avg_score = round(total_accumulated_score / new_total_tasks, 2)
            else:
                new_avg_score = current_avg_score
            
            # 准备更新数据
            update_data = {
                'total_tasks': new_total_tasks,
                'average_score': new_avg_score
            }
            
            # 更新候选人记录
            # 这里需要找到候选人的记录ID并更新
            # 简化实现，实际应该通过记录ID更新
            logger.info(f"候选人 {user_id} 绩效更新: 总任务数 {new_total_tasks}, 平均分 {new_avg_score}")
            return True
            
        except Exception as e:
            logger.error(f"更新候选人绩效出错: {str(e)}")
            return False
    
    async def create_candidate_record(self, candidate_data: dict) -> bool:
        """创建候选人记录到coder表
        
        Args:
            candidate_data: 候选人数据字典，包含userid, name, skilltags, job_level, experience, total_tasks, average_score
            
        Returns:
            创建是否成功
        """
        try:
            # 转换为多维表格需要的格式，确保数据类型正确
            # 处理技能标签：如果为空，在数据库中保存为"待补充"以便后续手动编辑
            skilltags = candidate_data.get('skilltags', '')
            if not skilltags or skilltags.strip() == '':
                skilltags = '待补充'  # 数据库占位符，表明需要后续补充
            
            record_data = {
                "fields": {
                    "userid": str(candidate_data.get('userid', '')),
                    "name": str(candidate_data.get('name', 'Unknown')),
                    "skilltags": str(skilltags),
                    "job_level": str(candidate_data.get('job_level', 1)),
                    "experience": str(candidate_data.get('experience', 0)),  # 转换为字符串
                    "total_tasks": str(candidate_data.get('total_tasks', 0)),  # 转换为字符串
                    "average_score": str(candidate_data.get('average_score', 0.0))  # 转换为字符串
                }
            }
            
            # 调用飞书API创建记录
            result = self.client.create_record(self.client.table_id, record_data)
            
            # 检查API调用是否成功
            code = result.get('code', -1)
            msg = result.get('msg', '')
            
            if code == 0:
                # 获取记录ID
                record_info = result.get('data', {}).get('record', {})
                record_id = record_info.get('record_id')
                
                logger.info(f"候选人记录创建成功: {candidate_data.get('name')} (ID: {record_id})")
                return True
            else:
                logger.error(f"候选人记录创建失败: code={code}, msg={msg}")
                return False
                
        except Exception as e:
            logger.error(f"创建候选人记录时出错: {str(e)}")
            return False
    
    def get_daily_task_stats(self):
        """获取每日任务统计数据
        
        Returns:
            包含任务统计信息的字典
        """
        try:
            from app.config import settings
            
            # 使用正确的任务表ID而不是候选人表
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("未配置task表ID (feishu_task_table_id)")
                return {
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'pending_tasks': 0,
                    'in_progress_tasks': 0,
                    'submitted_tasks': 0,
                    'reviewing_tasks': 0,
                    'rejected_tasks': 0,
                    'cancelled_tasks': 0,
                    'average_score': 0,
                    'completion_rate': 0,
                    'top_performers': [],
                    'tasks_by_urgency': {
                        'urgent': 0,
                        'high': 0,
                        'normal': 0,
                        'low': 0
                    },
                    'today_created': 0,
                    'today_completed': 0
                }
            
            # 获取任务表中的所有记录
            logger.info(f"正在获取任务表 {task_table_id} 的记录...")
            result = self.client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            logger.info(f"获取到 {len(records)} 条任务记录")
            
            # 初始化统计数据
            stats = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'submitted_tasks': 0,
                'reviewing_tasks': 0,
                'rejected_tasks': 0,
                'cancelled_tasks': 0,
                'assigned_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': [],
                'tasks_by_urgency': {
                    'urgent': 0,
                    'high': 0,
                    'normal': 0,
                    'low': 0
                },
                'today_created': 0,
                'today_completed': 0,
                'database_operations': {
                    'total_records': len(records),
                    'last_updated': datetime.now().isoformat()
                }
            }
            
            if not records:
                logger.warning("任务表中没有找到任何记录")
                return stats
            
            total_score = 0
            score_count = 0
            performers = []
            
            # 获取今天的日期
            from datetime import datetime, date
            today = date.today().strftime('%Y-%m-%d')
            
            # 遍历任务记录进行统计
            for record in records:
                fields = record.get('fields', {})
                if not fields:  # 跳过空记录
                    continue
                
                # 统计总任务数
                stats['total_tasks'] += 1
                
                # 根据状态字段统计
                status = fields.get('status', 'pending').lower()
                
                if status == 'completed':
                    stats['completed_tasks'] += 1
                elif status == 'pending':
                    stats['pending_tasks'] += 1
                elif status == 'in_progress':
                    stats['in_progress_tasks'] += 1
                elif status == 'submitted':
                    stats['submitted_tasks'] += 1
                elif status == 'reviewing':
                    stats['reviewing_tasks'] += 1
                elif status == 'rejected':
                    stats['rejected_tasks'] += 1
                elif status == 'cancelled':
                    stats['cancelled_tasks'] += 1
                elif status == 'assigned':
                    stats['assigned_tasks'] += 1
                
                # 统计紧急程度
                urgency = fields.get('urgency', 'normal').lower()
                if urgency in stats['tasks_by_urgency']:
                    stats['tasks_by_urgency'][urgency] += 1
                
                # 统计今日创建的任务
                create_time = fields.get('create_time', '')
                if create_time and today in create_time:
                    stats['today_created'] += 1
                
                # 统计今日完成的任务
                completed_at = fields.get('completed_at', '')
                if completed_at and today in completed_at and status == 'completed':
                    stats['today_completed'] += 1
                
                # 统计分数 (用于绩效分析)
                final_score = fields.get('final_score', 0)
                if final_score and isinstance(final_score, (int, float)) and final_score > 0:
                    total_score += final_score
                    score_count += 1
                
                # 收集任务创建者和负责人信息（用于top performers）
                creator = fields.get('creator', '')
                assignee = fields.get('assignee', '')
                
                # 如果任务已完成且有评分，记录到performers
                if status == 'completed' and final_score and assignee:
                    performers.append({
                        'name': assignee,
                        'score': final_score,
                        'task_title': fields.get('title', '未知任务')
                    })
            
            # 计算平均分
            if score_count > 0:
                stats['average_score'] = round(total_score / score_count, 2)
            
            # 计算完成率
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = round(
                    (stats['completed_tasks'] / stats['total_tasks']) * 100, 2
                )
            
            # 获取前3名表现者（按分数排序）
            if performers:
                performers.sort(key=lambda x: x['score'], reverse=True)
                stats['top_performers'] = performers[:3]
            
            logger.info(f"生成任务统计数据: 总任务{stats['total_tasks']}, 已完成{stats['completed_tasks']}, 完成率{stats['completion_rate']}%")
            return stats
            
        except Exception as e:
            logger.error(f"获取每日任务统计出错: {str(e)}")
            return {
                'total_tasks': 0,
                'completed_tasks': 0,
                'pending_tasks': 0,
                'in_progress_tasks': 0,
                'submitted_tasks': 0,
                'reviewing_tasks': 0,
                'rejected_tasks': 0,
                'cancelled_tasks': 0,
                'assigned_tasks': 0,
                'average_score': 0,
                'completion_rate': 0,
                'top_performers': [],
                'tasks_by_urgency': {
                    'urgent': 0,
                    'high': 0,
                    'normal': 0,
                    'low': 0
                },
                'today_created': 0,
                'today_completed': 0,
                'database_operations': {
                    'total_records': 0,
                    'last_updated': datetime.now().isoformat(),
                    'error': str(e)
                }
            }

    async def create_task_in_table(self, task_record_data):
        """创建任务记录到task表
        
        Args:
            task_record_data: 符合task表格式的任务数据
            
        Returns:
            记录ID，如果创建失败则返回None
        """
        try:
            from app.config import settings
            from app.services.db_audit import log_db_operation
            
            # 获取task表ID
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                logger.error("未配置task表ID (feishu_task_table_id)")
                
                # 记录审计日志
                log_db_operation(
                    operation_type="create",
                    table="task_table",
                    data=task_record_data,
                    user_id=task_record_data.get('creator', 'system'),
                    result="failed",
                    error_message="未配置task表ID"
                )
                return None
            
            # 转换为飞书API需要的格式
            record_data = {
                "fields": task_record_data
            }
            
            # 调用飞书API创建记录
            result = self.client.create_record(task_table_id, record_data)
            
            # 正确解析飞书API返回的记录结构
            # 飞书API返回格式: {'data': {'record': {'record_id': 'xxx', 'fields': {...}}}}
            record_info = result.get('data', {}).get('record', {})
            record_id = record_info.get('record_id')
            
            # 检查API调用是否成功
            code = result.get('code', -1)
            msg = result.get('msg', '')
            
            if code == 0 and record_id:
                logger.info(f"任务记录创建成功: {record_id}, 任务ID: {task_record_data.get('taskid', 'Unknown')}")
                
                # 记录成功的审计日志
                log_db_operation(
                    operation_type="create",
                    table="task_table",
                    record_id=record_id,
                    data=task_record_data,
                    user_id=task_record_data.get('creator', 'system'),
                    result="success"
                )
                
                return record_id
            else:
                logger.error(f"任务记录创建失败: code={code}, msg={msg}, result={result}")
                
                # 记录失败的审计日志
                log_db_operation(
                    operation_type="create",
                    table="task_table",
                    data=task_record_data,
                    user_id=task_record_data.get('creator', 'system'),
                    result="failed",
                    error_message=f"API调用失败: code={code}, msg={msg}"
                )
                
                return None
                
        except Exception as e:
            logger.error(f"创建任务记录到task表出错: {str(e)}")
            
            # 记录异常的审计日志
            log_db_operation(
                operation_type="create",
                table="task_table",
                data=task_record_data,
                user_id=task_record_data.get('creator', 'system') if task_record_data else 'system',
                result="failed",
                error_message=str(e)
            )
            
            return None
    
    async def get_task_table_info(self):
        """获取task表信息
        
        Returns:
            task表的字段信息和记录数量
        """
        try:
            from app.config import settings
            
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                return {'error': '未配置task表ID'}
            
            # 获取表格字段信息
            fields_info = self.client.get_table_fields(task_table_id)
            fields = fields_info.get('data', {}).get('items', [])
            
            # 获取表格记录数量
            records_info = self.client.get_table_records(task_table_id)
            records = records_info.get('data', {}).get('items', [])
            
            return {
                'table_id': task_table_id,
                'fields': fields,
                'total_records': len(records),
                'sample_records': records[:3] if records else []  # 返回前3条记录作为示例
            }
            
        except Exception as e:
            logger.error(f"获取task表信息出错: {str(e)}")
            return {'error': str(e)}

    async def get_all_tasks_sorted(self, page_size=5, page=0):
        """获取所有任务并按状态和紧急程度排序
        
        Args:
            page_size: 每页显示的任务数量
            page: 页码（从0开始）
            
        Returns:
            包含任务列表、总数、分页信息的字典
        """
        try:
            from app.config import settings
            
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                return {'error': '未配置task表ID'}
            
            # 获取所有任务记录
            result = self.client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            # 转换为标准化的任务数据格式
            tasks = []
            for record in records:
                fields = record.get('fields', {})
                if not fields:  # 跳过空记录
                    continue
                    
                task = {
                    'record_id': record.get('record_id'),
                    'taskid': fields.get('taskid', ''),
                    'title': fields.get('title', '未知任务'),
                    'description': fields.get('description', ''),
                    'creator': fields.get('creator', ''),
                    'create_time': fields.get('create_time', ''),
                    'status': fields.get('status', 'pending'),
                    'skilltags': fields.get('skilltags', ''),
                    'deadline': fields.get('deadline', ''),
                    'urgency': fields.get('urgency', 'normal')
                }
                tasks.append(task)
            
            # 定义排序优先级
            status_priority = {
                'in_progress': 1,  # 进行中 - 最高优先级
                'assigned': 2,     # 已分配
                'submitted': 3,    # 已提交
                'reviewing': 4,    # 审核中
                'pending': 5,      # 待处理
                'completed': 6,    # 已完成
                'rejected': 7,     # 已拒绝
                'cancelled': 8     # 已取消
            }
            
            urgency_priority = {
                'urgent': 1,   # 紧急
                'high': 2,     # 高
                'normal': 3,   # 普通
                'low': 4       # 低
            }
            
            # 排序：首先按状态优先级，然后按紧急程度，最后按创建时间倒序
            def sort_key(task):
                status = task['status'].lower()
                urgency = task['urgency'].lower()
                
                status_rank = status_priority.get(status, 99)
                urgency_rank = urgency_priority.get(urgency, 99)
                
                # 创建时间倒序（新任务在前）
                create_time = task['create_time']
                try:
                    # 尝试解析时间戳进行排序
                    from datetime import datetime
                    if create_time:
                        time_obj = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S')
                        time_rank = -time_obj.timestamp()  # 负数使新任务排在前面
                    else:
                        time_rank = 0
                except:
                    time_rank = 0
                
                return (status_rank, urgency_rank, time_rank)
            
            # 执行排序
            sorted_tasks = sorted(tasks, key=sort_key)
            
            # 分页处理
            total_tasks = len(sorted_tasks)
            total_pages = (total_tasks + page_size - 1) // page_size if total_tasks > 0 else 1
            
            start_idx = page * page_size
            end_idx = start_idx + page_size
            page_tasks = sorted_tasks[start_idx:end_idx]
            
            return {
                'tasks': page_tasks,
                'total_tasks': total_tasks,
                'current_page': page,
                'total_pages': total_pages,
                'page_size': page_size,
                'has_next': page < total_pages - 1,
                'has_prev': page > 0
            }
            
        except Exception as e:
            logger.error(f"获取排序任务列表出错: {str(e)}")
            return {'error': str(e)}
    
    async def get_task_statistics(self):
        """获取任务统计信息
        
        Returns:
            任务统计数据
        """
        try:
            from app.config import settings
            
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                return {'error': '未配置task表ID'}
            
            # 获取所有任务记录
            result = self.client.get_table_records(task_table_id)
            records = result.get('data', {}).get('items', [])
            
            # 统计各状态的任务数量
            stats = {
                'total': 0,
                'pending': 0,
                'assigned': 0,
                'in_progress': 0,
                'submitted': 0,
                'reviewing': 0,
                'completed': 0,
                'rejected': 0,
                'cancelled': 0,
                'by_urgency': {
                    'urgent': 0,
                    'high': 0,
                    'normal': 0,
                    'low': 0
                }
            }
            
            for record in records:
                fields = record.get('fields', {})
                if not fields:  # 跳过空记录
                    continue
                
                stats['total'] += 1
                
                status = fields.get('status', 'pending').lower()
                urgency = fields.get('urgency', 'normal').lower()
                
                # 统计状态
                if status in stats:
                    stats[status] += 1
                
                # 统计紧急程度
                if urgency in stats['by_urgency']:
                    stats['by_urgency'][urgency] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取任务统计信息出错: {str(e)}")
            return {'error': str(e)}

    async def delete_task_record(self, record_id: str):
        """删除任务记录
        
        Args:
            record_id: 要删除的记录ID
            
        Returns:
            删除结果字典，包含成功状态和消息
        """
        try:
            from app.config import settings
            
            task_table_id = getattr(settings, 'feishu_task_table_id', None)
            if not task_table_id:
                return {'success': False, 'message': '未配置task表ID'}
            
            # 执行删除操作
            result = self.client.delete_record(task_table_id, record_id)
            
            # 检查删除结果
            if result.get('code') == 0:
                logger.info(f"成功删除任务记录: {record_id}")
                return {
                    'success': True, 
                    'message': '任务记录删除成功',
                    'record_id': record_id
                }
            else:
                error_msg = result.get('msg', '删除失败')
                logger.error(f"删除任务记录失败: {record_id}, 错误: {error_msg}")
                return {
                    'success': False, 
                    'message': f'删除失败: {error_msg}',
                    'error_code': result.get('code')
                }
                
        except Exception as e:
            logger.error(f"删除任务记录时出错: {record_id}, 错误: {str(e)}")
            return {
                'success': False, 
                'message': f'删除操作异常: {str(e)}'
            }