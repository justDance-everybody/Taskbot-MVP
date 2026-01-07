# LLM API 配置指南

## 问题诊断

如果简历上传后没有 AI 分析，通常是因为 LLM API 配置有问题。

从日志中可以看到以下错误：
```
DeepSeek API error: 401 - API key invalid
Gemini API error: 404 - Model not found
OpenAI API error: 401 - Invalid API key
```

---

## 解决方案

### 方案 1：使用 DeepSeek（推荐，免费额度大）

1. **获取 API Key**：
   - 访问：https://platform.deepseek.com/
   - 注册账号并登录
   - 进入「API Keys」页面
   - 点击「创建新密钥」
   - 复制生成的 API Key（格式：`sk-xxxxxxxx`）

2. **配置 `.env` 文件**：
   ```bash
   DEEPSEEK_KEY=sk-你的真实key
   ```

3. **重启服务**：
   ```bash
   pkill -f "python.*main.py"
   source venv/bin/activate
   python3 main.py
   ```

---

### 方案 2：使用 Google Gemini（推荐，免费）

1. **获取 API Key**：
   - 访问：https://makersuite.google.com/app/apikey
   - 使用 Google 账号登录
   - 点击「Create API Key」
   - 复制生成的 API Key

2. **配置 `.env` 文件**：
   ```bash
   GEMINI_KEY=你的真实key
   GEMINI_MODEL=gemini-1.5-flash
   ```

   **可用的 Gemini 模型**：
   - `gemini-1.5-flash` - 快速，适合大多数任务（推荐）
   - `gemini-1.5-pro` - 更强大，但速度较慢
   - `gemini-2.0-flash-exp` - 实验性最新模型

3. **重启服务**：
   ```bash
   pkill -f "python.*main.py"
   source venv/bin/activate
   python3 main.py
   ```

---

### 方案 3：使用 OpenAI（付费）

1. **获取 API Key**：
   - 访问：https://platform.openai.com/api-keys
   - 登录并创建 API Key
   - 复制生成的 API Key

2. **配置 `.env` 文件**：
   ```bash
   OPENAI_KEY=sk-你的真实key
   OPENAI_BASE_URL=https://api.openai.com/v1
   OPENAI_MODEL=gpt-3.5-turbo
   ```

3. **重启服务**：
   ```bash
   pkill -f "python.*main.py"
   source venv/bin/activate
   python3 main.py
   ```

---

## 验证配置

### 1. 检查 API Key 是否有效

```bash
# 测试 DeepSeek
curl https://api.deepseek.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-你的key" \
  -d '{
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# 测试 Gemini
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=你的key" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### 2. 查看服务日志

```bash
# 实时监控日志
tail -f app.log | grep -E "LLM|API|简历"

# 查看最近的错误
tail -100 app.log | grep -i error
```

### 3. 测试简历分析

上传一个 PDF 简历到飞书群聊，观察日志输出：

**成功的日志**：
```
✅ PDF文本提取成功: resume.pdf, 字符数: 1500
✅ Calling deepseek
✅ DeepSeek API调用成功
✅ AI简历分析完成
```

**失败的日志**：
```
❌ DeepSeek API error: 401
❌ Gemini API error: 404
❌ OpenAI API error: 401
❌ PDF简历分析失败: All LLM backends failed
```

---

## 常见问题

### Q1: DeepSeek API 返回 401 错误

**原因**：
- API Key 无效或已过期
- API Key 格式错误（应该以 `sk-` 开头）
- 账户余额不足

**解决方案**：
1. 登录 DeepSeek 平台检查 API Key 状态
2. 重新生成一个新的 API Key
3. 检查账户余额（新用户通常有免费额度）

### Q2: Gemini API 返回 404 错误

**原因**：
- 模型名称错误
- API Key 无效
- 区域限制（某些地区无法访问）

**解决方案**：
1. 确认模型名称正确：
   ```bash
   # 错误示例
   GEMINI_MODEL=gemini-3-falsh-preview  ❌
   GEMINI_MODEL=gemini-pro              ❌ (已废弃)
   
   # 正确示例
   GEMINI_MODEL=gemini-1.5-flash        ✅
   GEMINI_MODEL=gemini-1.5-pro          ✅
   ```

2. 测试 API Key：
   ```bash
   curl "https://generativelanguage.googleapis.com/v1beta/models?key=你的key"
   ```

3. 如果在中国大陆，可能需要使用代理

### Q3: 所有 LLM 都失败了怎么办？

**临时解决方案**：
系统会使用基础的文本提取功能，虽然没有 AI 分析，但仍会保存简历文件名作为候选人姓名。

**长期解决方案**：
至少配置一个有效的 LLM API Key。推荐顺序：
1. **DeepSeek**（免费额度大，国内访问快）
2. **Gemini**（完全免费，但可能需要代理）
3. **OpenAI**（付费，但最稳定）

### Q4: 如何查看 API 使用情况？

**DeepSeek**：
- 访问：https://platform.deepseek.com/usage
- 查看 API 调用次数和余额

**Gemini**：
- 访问：https://makersuite.google.com/app/apikey
- 查看配额使用情况

**OpenAI**：
- 访问：https://platform.openai.com/usage
- 查看详细的使用统计

---

## 推荐配置

### 最佳实践：配置多个 LLM 作为备份

```bash
# .env 文件配置示例
DEEPSEEK_KEY=sk-你的deepseek_key        # 主要使用
GEMINI_KEY=你的gemini_key                # 备用1
GEMINI_MODEL=gemini-1.5-flash
OPENAI_KEY=sk-你的openai_key            # 备用2（可选）
OPENAI_MODEL=gpt-3.5-turbo
```

**优势**：
- 如果 DeepSeek 失败，自动切换到 Gemini
- 如果 Gemini 也失败，再切换到 OpenAI
- 提高系统可用性

---

## 成本对比

| LLM 服务 | 免费额度 | 付费价格 | 速度 | 推荐度 |
|---------|---------|---------|------|--------|
| **DeepSeek** | 500万 tokens | ¥1/百万tokens | 快 | ⭐⭐⭐⭐⭐ |
| **Gemini** | 无限制（有速率限制） | 免费 | 中等 | ⭐⭐⭐⭐ |
| **OpenAI** | $5 新用户 | $0.5/百万tokens | 快 | ⭐⭐⭐ |

**推荐**：
- **个人开发/测试**：使用 Gemini（完全免费）
- **小规模生产**：使用 DeepSeek（性价比高）
- **大规模生产**：使用 OpenAI（最稳定）

---

## 快速修复脚本

创建一个测试脚本 `test_llm.py`：

```python
import os
from dotenv import load_dotenv
import requests

load_dotenv()

def test_deepseek():
    api_key = os.getenv("DEEPSEEK_KEY")
    if not api_key or api_key == "test_key":
        print("❌ DeepSeek: API Key 未配置")
        return False
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hello"}]
            },
            timeout=10
        )
        if response.status_code == 200:
            print("✅ DeepSeek: API 正常")
            return True
        else:
            print(f"❌ DeepSeek: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ DeepSeek: {str(e)}")
        return False

def test_gemini():
    api_key = os.getenv("GEMINI_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    if not api_key or api_key == "test_key":
        print("❌ Gemini: API Key 未配置")
        return False
    
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": "Hello"}]}]},
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Gemini: API 正常")
            return True
        else:
            print(f"❌ Gemini: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Gemini: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== LLM API 配置测试 ===\n")
    
    deepseek_ok = test_deepseek()
    gemini_ok = test_gemini()
    
    print("\n=== 测试结果 ===")
    if deepseek_ok or gemini_ok:
        print("✅ 至少有一个 LLM API 可用，简历分析功能正常")
    else:
        print("❌ 所有 LLM API 都不可用，请检查配置")
        print("\n请参考 LLM_API_SETUP.md 配置至少一个 LLM API")
```

运行测试：
```bash
python3 test_llm.py
```

---

## 获取帮助

如果仍然无法解决问题：

1. **查看完整日志**：
   ```bash
   tail -200 app.log > debug_llm.log
   ```

2. **检查环境变量**：
   ```bash
   grep -E "DEEPSEEK_KEY|GEMINI_KEY|OPENAI_KEY" .env
   ```

3. **重新配置**：
   - 删除旧的 API Key
   - 重新生成新的 API Key
   - 更新 `.env` 文件
   - 重启服务

---

**记住**：至少需要配置一个有效的 LLM API Key，简历分析功能才能正常工作！
