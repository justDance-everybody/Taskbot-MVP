# 🚀 快速开始 - 手动添加测试数据

由于 API 权限限制（403 Forbidden），我们需要手动在飞书多维表格中添加测试数据。

## 📍 第一步：打开你的多维表格

1. 在飞书中打开多维表格应用
2. 找到以下两个表：
   - **任务表** (tblHL3XIUZBbCFJE)
   - **候选人表** (tblDtuakdqIGvL7c)

## 👥 第二步：添加候选人数据

打开「候选人表」，点击「添加记录」，复制以下数据：

### 候选人 1 - 张三
```
user_id: user_001
name: 张三
skill_tags: Python, FastAPI, 数据库
job_level: 中级
experience: 3
total_tasks: 15
average_score: 88.5
available_hours: 20
```

### 候选人 2 - 李四
```
user_id: user_002
name: 李四
skill_tags: JavaScript, React, Node.js
job_level: 高级
experience: 5
total_tasks: 28
average_score: 92.3
available_hours: 15
```

### 候选人 3 - 王五
```
user_id: user_003
name: 王五
skill_tags: Java, Spring, 微服务
job_level: 中级
experience: 4
total_tasks: 20
average_score: 85.7
available_hours: 25
```

## 📋 第三步：添加任务数据

打开「任务表」，点击「添加记录」，复制以下数据：

### 任务 1 - 待处理任务
```
taskid: TASK_001
title: 开发用户认证模块
description: 实现基于JWT的用户认证系统，包括登录、注册、密码重置功能
status: pending
creator: admin_001
deadline: 2026-01-12
skilltags: Python, FastAPI, JWT
urgency: high
create_time: 2026-01-05 22:00:00
```

### 任务 2 - 已分配任务
```
taskid: TASK_002
title: 前端页面优化
description: 优化首页加载速度，实现懒加载和代码分割
status: assigned
creator: admin_001
assignee: user_002
deadline: 2026-01-10
skilltags: JavaScript, React, 性能优化
urgency: normal
create_time: 2026-01-05 21:00:00
```

### 任务 3 - 进行中任务
```
taskid: TASK_003
title: 数据库性能优化
description: 分析慢查询日志，优化数据库索引和查询语句
status: in_progress
creator: admin_002
assignee: user_001
deadline: 2026-01-08
skilltags: 数据库, SQL, 性能优化
urgency: urgent
create_time: 2026-01-05 20:00:00
```

### 任务 4 - 已完成任务
```
taskid: TASK_004
title: CI/CD流程搭建
description: 搭建完整的CI/CD流程，包括自动化测试、代码质量检查
status: completed
creator: admin_001
assignee: user_003
deadline: 2026-01-03
completed_at: 2026-01-04 15:30:00
skilltags: Docker, Kubernetes, CI/CD
urgency: high
final_score: 95
create_time: 2026-01-03 10:00:00
```

## ✅ 第四步：验证数据

添加完数据后，在终端运行以下命令验证：

```bash
# 1. 测试数据读取
python3 test_simple.py

# 2. 查看每日报告
curl http://localhost:8000/api/v1/reports/daily | python3 -m json.tool

# 3. 运行完整测试
python3 test_api.py
```

## 🎯 预期结果

如果数据添加成功，你应该看到：

```bash
✅ 找到 3 条候选人记录
✅ 找到 4 条任务记录

任务状态统计:
  pending: 1
  assigned: 1
  in_progress: 1
  completed: 1
```

## 📊 查看报告

访问以下 URL 查看统计报告：

```
http://localhost:8000/api/v1/reports/daily
```

预期响应：
```json
{
  "date": "2026-01-05",
  "total_tasks": 4,
  "completed_tasks": 1,
  "pending_tasks": 1,
  "in_progress_tasks": 1,
  "average_score": 95.0,
  "completion_rate": 25.0
}
```

## 🔧 字段类型提示

在飞书多维表格中创建字段时，使用以下类型：

**任务表：**
- taskid, title, description, creator, assignee → 单行文本/多行文本
- status → 单选（pending, assigned, in_progress, completed, submitted, reviewing, rejected, cancelled）
- urgency → 单选（low, normal, high, urgent）
- skilltags → 多选（可以自定义标签）
- deadline → 日期
- create_time, completed_at → 日期时间
- final_score → 数字

**候选人表：**
- user_id, name → 单行文本
- skill_tags → 多选（可以自定义标签）
- job_level → 单选（初级, 中级, 高级, 专家, 架构师）
- experience, total_tasks, available_hours → 数字（整数）
- average_score → 数字（小数，保留1位）

## 💡 提示

1. **多选字段**：在添加 skill_tags 时，如果标签不存在，飞书会自动创建
2. **日期格式**：使用 YYYY-MM-DD 格式
3. **日期时间格式**：使用 YYYY-MM-DD HH:MM:SS 格式
4. **最少数据**：至少添加 2 个候选人和 3 个任务即可测试

## 🚨 常见问题

**Q: 字段名称必须完全一致吗？**
A: 是的，字段名称必须与上面列出的完全一致（区分大小写）

**Q: 可以少添加一些字段吗？**
A: 可以，但建议至少填写标记为必需的字段（taskid, title, status, creator 等）

**Q: 添加数据后看不到效果？**
A: 运行 `python3 test_simple.py` 检查数据是否正确读取

## 🎉 完成！

添加完数据后，你的飞书任务管理机器人就可以正常工作了！

接下来可以：
- 在飞书中向机器人发送消息测试
- 访问 http://localhost:8000/docs 查看 API 文档
- 查看 http://localhost:8000/api/v1/reports/daily 统计报告
