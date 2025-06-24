# ENV\_SETUP – 环境与凭据指南（飞书远程任务 Bot MVP）

> **阅读对象**：远程实习生 & AI 编程助手
>
> 完成本地 / 云端部署前，请按下列步骤一次性配置全部凭据与回调。

---

## 1. 前置条件

- 飞书企业已开通，账户具备「应用开发者」权限。
- 可用公网 HTTPS：本地可用 **Ngrok**，云端可用 Render / Oracle Free VM。
- GitHub 仓库已创建，提供 Actions 免费额度（用于 CI）。

---

## 2. 创建并配置飞书机器人（10 分钟）

| 步骤                                | 操作                                                                                            | 结果                       |
| --------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------ |
| ①                                 | 企业管理后台 → **开发者空间** → 新建**内部应用**                                                               | 获得 *App ID / App Secret* |
| ②                                 | **事件订阅** → 开启 → 设置回调 URL                                                                      |                          |
| `https://<domain>/webhook/feishu` | 飞书向此地址发送所有群/私聊事件                                                                              |                          |
| ③                                 | **权限管理** → 添加权限  • `im:message` 发送/接收  • `chat:write`, `chat:update` 群管理  • `bitable:*` 读写多维表 | 点击“申请发布”，内部应用立即生效        |
| ④                                 | 生成 **Verify Token** & **Encrypt Key** (可留空)                                                   | 用于 Webhook 签名校验          |

---

## 3. 本地 `.env` 示例

```
APP_ID=cli_a1234567890
APP_SECRET=xxx
VERIFY_TOKEN=bot_verify_123
FEISHU_ENCRYPT_KEY=
DEEPSEEK_KEY=sk-deep...
GEMINI_KEY=sk-gem...
OPENAI_KEY=
GITHUB_WEBHOOK_SECRET=github_hmac_123
```

> **提示**：如仅使用 DeepSeek，可留空 GEMINI/OPENAI。CI 请在 Repo > Settings > Secrets 填同名字段。

---

## 4. 本地启动（Ngrok 示例）

```bash
make dev          # 启动 Uvicorn 端口 8000
ngrok http 8000   # 得到 https://abc123.ngrok.io
```

1. 将 `https://abc123.ngrok.io/webhook/feishu` 回填到飞书事件回调 URL。
2. 在控制室群 `@机器人 ping`，若 Bot 返回 pong 则接通。

---

## 5. 部署到 Render 免费实例

1. 登录 Render → New → Web Service → 连接 GitHub Repo。
2. 环境：Docker；启用 Auto‑Deploy。
3. Environment Variables：粘贴 `.env` 中所有键值。
4. 部署成功后，复制 `https://taskbot.onrender.com/webhook/feishu` 到飞书。
5. 若 15 分钟无流量 Render 会休眠：可在飞书发送消息唤醒。

---

## 6. 常见问题 FAQ

| 现象                  | 可能原因             | 解决方案                                                           |
| ------------------- | ---------------- | -------------------------------------------------------------- |
| 403 Forbidden       | Verify Token 不一致 | 检查飞书后台与 `.env` 中 VERIFY\_TOKEN 是否匹配                            |
| Bot 无响应，控制台 404     | 回调 URL 路径错误      | 确保 `/webhook/feishu` 与源码路由一致                                   |
| Render 部署成功但飞书仍 500 | 端口未暴露 / 进程未启动    | Dockerfile 需运行 `uvicorn app.main:app --port $PORT` 并读取 `$PORT` |

---

> **完成以上配置** 后即可进入 `make test` or `make ai-loop` 进行开发与自动化测试。

