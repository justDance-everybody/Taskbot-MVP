# ENV\_SETUP – 环境与凭据指南（飞书远程任务 Bot MVP v1.1）

> **目标**：让开发人员在 15 分钟内跑通本地开发或部署到 Render 免费层。所有密钥均放 `.env`，环境完全可复制。

---

## 1. 前置条件

* 已开通 **飞书企业**，并具备应用开发者权限。
* 机器可装 **Docker**（本地或云服务器）。
* GitHub 仓库 / Actions 免费额度可用（仅跑测试）。

---

## 2. 创建飞书机器人（≈10 分钟）

| 步骤 | 操作                                                                                             | 结果                         |
| -- | ---------------------------------------------------------------------------------------------- | -------------------------- |
| ①  | 管理后台 → **开发者空间** → 新建**内部应用**                                                                  | 获得 `APP_ID / APP_SECRET`   |
| ②  | **事件订阅** → 启用 → 回调 URL `https://<domain>/webhook/feishu`                                       | Bot 能接收消息事件                |
| ③  | **权限管理** → 勾选<br>• `im:message` 发/收消息<br>• `chat:write chat:update` 群管理<br>• `bitable:*` 读写多维表 | 保存后“开发版”立即生效               |
| ④  | 生成 **Verify Token**（自定义）                                                                       | `.env` 中 `VERIFY_TOKEN` 同步 |

> ⚠️ 生产环境建议启用 **Encrypt Key**；MVP 阶段可留空。

---

## 3. `.env` 示例

```
APP_ID=cli_a1b2c3d4
APP_SECRET=sec_XXXXX
VERIFY_TOKEN=bot_verify_123
DEEPSEEK_KEY=sk-deepseek...
GEMINI_KEY=
OPENAI_KEY=
GITHUB_WEBHOOK_SECRET=github_hmac_123
```

* **至少填一个模型密钥**；为空的可留空。
* CI Secrets 同名填入 Repo → Settings → Secrets。

---

## 4. 本地快速启动 （Ngrok 免费）

```bash
make dev            # Uvicorn 8000
ngrok http 8000     # 得到 https://abc.ngrok.io
# 回填飞书事件订阅 URL
```

验证：在控制室群 `@机器人 ping` → Bot 回复 `pong`。

---

## 5. 免费云部署（Render.com）

1. Render → New Web Service → 连接 GitHub Repo。
2. 选择 **Docker** 部署；环境变量同 `.env`。
3. 首次构建后复制生成 URL `https://taskbot.onrender.com/webhook/feishu` 回填飞书。
4. Render 免费层若 15 分钟无请求会休眠；发送任意消息即可唤醒。

> **Oracle Free VM** 步骤：`git clone` → `docker-compose up -d` → Nginx 反向代理 + LetsEncrypt，流程略。

---

## 6. 常见问题 FAQ

| 症状               | 可能原因                | 处理                                                                  |
| ---------------- | ------------------- | ------------------------------------------------------------------- |
| 飞书 403           | VERIFY\_TOKEN 不一致   | 检查后台 & `.env`                                                       |
| Bot 无响应          | 回调 URL 路径错误 / 应用未启用 | 确认 `/webhook/feishu` & 应用「开发版」已启用                                   |
| Render 构建成功但 502 | 未暴露 `$PORT`         | Dockerfile 需 `CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

---

> 完成本指南，即可 `make test` 跑自动化测试或 `/done` 提交任务。
