# PDF简历解析功能说明

## 功能概述

系统实现了完整的PDF简历自动解析功能，可以：
1. 接收PDF格式的简历文件
2. 提取PDF中的文本内容
3. 使用LLM智能分析文本，提取结构化信息
4. 自动验证和填充默认值
5. 标记需要人工审核的字段
6. 将候选人信息写入飞书多维表格

## 技术实现

### 核心模块
- **文件位置**: `app/services/cv_parser.py`
- **主类**: `CVParser`

### PDF文本提取
支持两种PDF解析库，自动降级：

1. **pdfplumber** (优先)
   - 提取效果更好
   - 支持复杂布局
   
2. **PyPDF2** (降级)
   - 作为备选方案
   - 兼容性更好

```python
async def _extract_pdf_text(self, file_content: bytes) -> str:
    # 1. 尝试使用pdfplumber
    # 2. 失败则降级到PyPDF2
    # 3. 返回提取的文本
```

### LLM智能解析
使用大语言模型分析简历文本，提取结构化信息：

```python
async def _llm_parse(self, pdf_text: str) -> Dict[str, Any]:
    # 构建提示词
    # 调用LLM服务
    # 解析JSON响应
```

**提取的字段**:
- `name`: 姓名
- `skills`: 技能列表 (数组)
- `job_level`: 职级 (1-5)
  - 1 = 初级
  - 2 = 中级
  - 3 = 高级
  - 4 = 专家
  - 5 = 架构师
- `experience_years`: 工作年限
- `education`: 教育背景
- `work_experience`: 工作经历
- `projects`: 项目经验

### 数据验证与审核标记
自动验证数据完整性，标记需要人工审核的情况：

```python
def _validate_and_fill_defaults(self, data: Dict, file_name: str) -> Dict:
    # 验证必需字段
    # 填充默认值
    # 标记needs_review
```

**自动标记审核的情况**:
- 姓名缺失或为空
- 技能列表为空
- 经验年数为0但职级大于1
- PDF文本提取失败

## 使用流程

### 1. 在飞书中上传简历
HR在飞书群聊中上传PDF简历文件

### 2. Bot接收文件
```python
# 在webhooks.py中处理文件消息
file_key = message_content.get('file_key')
file_content = await feishu_service.download_file(file_key)
```

### 3. 调用解析器
```python
from app.services.cv_parser import CVParser
from app.services.llm import llm_service

cv_parser = CVParser(llm_service=llm_service)
parsed_data = await cv_parser.parse_resume(file_content, filename)
```

### 4. 写入多维表格
```python
from app.bitable import BitableClient

bitable = BitableClient()
await bitable.create_candidate_record({
    'userid': generate_user_id(),
    'name': parsed_data['name'],
    'skilltags': ','.join(parsed_data['skills']),
    'job_level': str(parsed_data['job_level']),
    'experience': str(parsed_data['experience_years']),
    'total_tasks': '0',
    'average_score': '0.0'
})
```

### 5. 通知HR
```python
if parsed_data.get('needs_review'):
    await feishu_service.send_message(
        chat_id,
        f"✅ 简历已解析：{parsed_data['name']}\n"
        f"⚠️ 部分信息需要人工审核，请在多维表格中补充完善"
    )
else:
    await feishu_service.send_message(
        chat_id,
        f"✅ 简历已解析：{parsed_data['name']}\n"
        f"候选人信息已自动录入系统"
    )
```

## 解析示例

### 输入: PDF简历文件
```
张三的简历

个人信息：
姓名：张三
邮箱：zhangsan@example.com
电话：13800138000

技能：
- Python (5年)
- Django (3年)
- PostgreSQL (4年)
- FastAPI (2年)
- Docker (2年)

教育背景：
本科 - 计算机科学与技术
某某大学 (2015-2019)

工作经历：
高级Python工程师 | ABC科技公司 | 2019-2024
- 负责后端系统开发和维护
- 使用Django和FastAPI开发RESTful API
- 数据库设计和优化

项目经验：
1. 电商平台后端系统 (2022-2023)
   - 使用FastAPI构建高性能API
   - PostgreSQL数据库设计
   - Docker容器化部署

2. 用户管理系统 (2020-2021)
   - Django框架开发
   - 实现用户认证和权限管理
```

### 输出: 结构化数据
```json
{
  "name": "张三",
  "skills": [
    "Python",
    "Django",
    "PostgreSQL",
    "FastAPI",
    "Docker"
  ],
  "job_level": 3,
  "experience_years": 5,
  "education": "本科 - 计算机科学与技术",
  "work_experience": "高级Python工程师 | ABC科技公司 | 2019-2024",
  "projects": "电商平台后端系统、用户管理系统",
  "needs_review": false
}
```

## 错误处理

### PDF提取失败
如果PDF文本提取失败（扫描件、图片PDF等），返回默认数据并标记需要审核：

```json
{
  "name": "从文件名提取",
  "skills": [],
  "job_level": 1,
  "experience_years": 0,
  "education": "PDF解析失败，请手动补充",
  "work_experience": "PDF文本提取失败，无法AI分析",
  "projects": "PDF解析失败，请手动补充",
  "needs_review": true
}
```

### LLM解析失败
如果LLM服务不可用或解析失败，同样返回默认数据并标记审核。

## 依赖安装

### 必需依赖
```bash
pip install pdfplumber PyPDF2
```

### 可选优化
```bash
# 如果需要处理图片PDF（OCR）
pip install pytesseract pillow
```

## 测试

### 单元测试
```bash
# 测试CV解析器
pytest tests/unit/test_cv_parser.py -v

# 测试属性验证
pytest tests/unit/test_cv_parser_properties.py -v
```

### E2E测试
```bash
# 运行完整的端到端测试（包含简历解析）
python3 test_e2e_workflow.py
```

## 性能指标

- **PDF文本提取**: 通常 < 1秒
- **LLM解析**: 2-5秒（取决于LLM服务）
- **总处理时间**: 3-6秒
- **成功率**: 
  - 文本PDF: > 95%
  - 扫描PDF: 需要OCR支持
  - 图片PDF: 需要OCR支持

## 最佳实践

### 1. 简历格式建议
- 使用文本PDF（非扫描件）
- 清晰的章节结构
- 标准的简历格式

### 2. 人工审核流程
对于标记 `needs_review: true` 的简历：
1. HR在飞书多维表格中查看
2. 补充缺失的信息
3. 修正错误的字段
4. 确认后即可用于任务匹配

### 3. 技能标签规范化
建议维护一个技能标签库，对LLM提取的技能进行规范化：
- Python → Python
- python → Python
- py → Python

## 未来优化方向

1. **OCR支持**: 处理扫描版PDF
2. **多语言支持**: 英文简历解析
3. **批量处理**: 一次上传多份简历
4. **简历评分**: 自动评估候选人匹配度
5. **去重检测**: 识别重复提交的简历

---

**相关文件**:
- 实现: `app/services/cv_parser.py`
- 测试: `tests/unit/test_cv_parser.py`
- E2E测试: `test_e2e_workflow.py` (步骤BONUS)
- Webhook处理: `app/webhooks.py`
