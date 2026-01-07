# 飞书多维表格权限配置指南

## ❌ 当前问题

添加测试数据时遇到 **403 Forbidden** 错误：
```
错误91403 - FORBIDDEN: 权限不足，请检查应用权限设置和多维表格的分享设置
```

这表示飞书应用没有足够的权限来写入多维表格数据。

## ✅ 解决方案

### 方案 1: 配置飞书应用权限（推荐）

1. **访问飞书开放平台**
   - 打开 https://open.feishu.cn/
   - 进入「开发者后台」→「应用管理」
   - 找到你的应用（App ID: `cli_a9d179bcda381cca`）

2. **添加多维表格权限**
   
   进入「权限管理」，确保勾选以下权限：
   
   **必需权限：**
   ```
   📊 多维表格权限
   ├── bitable:app                   # 获取多维表格信息
   ├── bitable:app:readonly          # 获取多维表格基础信息
   ├── bitable:table                 # 获取多维表格数据表信息
   ├── bitable:table:readonly        # 获取多维表格数据表基础信息
   ├── bitable:record                # ⭐ 新增、删除、修改多维表格记录（重要！）
   └── bitable:record:readonly       # 查看多维表格记录
   ```
   
   **特别注意：** `bitable:record` 权限是写入数据的关键！

3. **发布权限变更**
   - 添加权限后，点击「创建版本」
   - 提交审核（企业自建应用通常会自动通过）
   - 等待版本发布

4. **重新授权**
   - 权限变更后，需要重新获取 access_token
   - 重启你的服务即可自动获取新的 token

### 方案 2: 配置多维表格分享权限

1. **打开飞书多维表格**
   - 打开你的多维表格应用
   - URL 中包含: `ZpUKbCD9WabCcosbqFAcl4ponuh`

2. **设置分享权限**
   - 点击右上角「分享」按钮
   - 选择「添加协作者」
   - 搜索并添加你的机器人应用
   - 设置权限为「可编辑」或「可管理」

3. **或者设置为公开可编辑**
   - 点击「分享」→「更多设置」
   - 选择「获得链接的人可编辑」
   - 保存设置

### 方案 3: 手动添加测试数据（临时方案）

如果暂时无法配置权限，可以手动在飞书多维表格中添加数据：

#### 任务表字段和示例数据

**字段配置：**
| 字段名 | 类型 | 示例值 |
|--------|------|--------|
| taskid | 单行文本 | TASK_001 |
| title | 单行文本 | 开发用户认证模块 |
| description | 多行文本 | 实现基于JWT的用户认证系统... |
| status | 单选 | pending / assigned / in_progress / completed |
| creator | 单行文本 | admin_001 |
| assignee | 单行文本 | user_001 |
| deadline | 日期 | 2026-01-12 |
| skilltags | 多选 | Python, FastAPI, JWT |
| urgency | 单选 | low / normal / high / urgent |
| create_time | 日期时间 | 2026-01-05 22:00:00 |
| completed_at | 日期时间 | (完成时填写) |
| final_score | 数字 | 95 |

**示例任务：**
1. **任务1**
   - taskid: TASK_001
   - title: 开发用户认证模块
   - status: pending
   - urgency: high
   - deadline: 7天后

2. **任务2**
   - taskid: TASK_002
   - title: 前端页面优化
   - status: assigned
   - assignee: user_002
   - urgency: normal
   - deadline: 5天后

3. **任务3**
   - taskid: TASK_003
   - title: 数据库性能优化
   - status: in_progress
   - assignee: user_001
   - urgency: urgent
   - deadline: 3天后

#### 候选人表字段和示例数据

**字段配置：**
| 字段名 | 类型 | 示例值 |
|--------|------|--------|
| user_id | 单行文本 | user_001 |
| name | 单行文本 | 张三 |
| skill_tags | 多选 | Python, FastAPI, 数据库 |
| job_level | 单选 | 初级 / 中级 / 高级 / 专家 / 架构师 |
| experience | 数字 | 3 |
| total_tasks | 数字 | 15 |
| average_score | 数字 | 88.5 |
| available_hours | 数字 | 20 |

**示例候选人：**
1. **张三**
   - user_id: user_001
   - name: 张三
   - skill_tags: Python, FastAPI, 数据库
   - job_level: 中级
   - experience: 3
   - total_tasks: 15
   - average_score: 88.5

2. **李四**
   - user_id: user_002
   - name: 李四
   - skill_tags: JavaScript, React, Node.js
   - job_level: 高级
   - experience: 5
   - total_tasks: 28
   - average_score: 92.3

3. **王五**
   - user_id: user_003
   - name: 王五
   - skill_tags: Java, Spring, 微服务
   - job_level: 中级
   - experience: 4
   - total_tasks: 20
   - average_score: 85.7

## 🔍 验证权限配置

配置完成后，运行以下命令验证：

```bash
# 重启服务（获取新的 access_token）
# 停止当前服务，然后重新启动
python3 main.py

# 在另一个终端运行测试
python3 add_test_data.py
```

如果看到类似以下输出，说明权限配置成功：
```
✅ 成功添加: 张三
✅ 成功添加: 李四
...
```

## 📝 常见问题

### Q1: 权限已添加，但仍然报 403 错误？
**A:** 
1. 确保已经「创建版本」并发布
2. 重启服务以获取新的 access_token
3. 检查多维表格的分享设置

### Q2: 如何查看当前应用的权限？
**A:** 
1. 进入飞书开放平台
2. 找到你的应用
3. 查看「权限管理」页面
4. 确认 `bitable:record` 权限已勾选

### Q3: 企业自建应用需要审核吗？
**A:** 
- 企业自建应用通常会自动通过审核
- 如果需要审核，通常在几分钟内完成
- 可以联系企业管理员加速审核

## 🎯 下一步

权限配置完成后：
1. ✅ 运行 `python3 add_test_data.py` 添加测试数据
2. ✅ 运行 `python3 test_simple.py` 验证数据
3. ✅ 访问 http://localhost:8000/api/v1/reports/daily 查看报告
4. ✅ 在飞书中测试机器人功能

## 📞 需要帮助？

如果遇到问题：
1. 检查日志文件 `app.log`
2. 查看飞书开放平台的错误信息
3. 确认应用 ID 和密钥配置正确
4. 验证多维表格 App Token 正确

---

**提示：** 最简单的方法是在飞书多维表格中手动添加几条测试数据，然后运行 `python3 test_simple.py` 验证服务是否能正确读取数据。
