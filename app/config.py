
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 飞书机器人配置
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verify_token: str
    feishu_encrypt_key: str | None = None
    feishu_bot_user_id: str | None = None  # 机器人的用户ID（可选，用于群聊邀请）
    
    # LLM 模型配置
    deepseek_key: str | None = None
    gemini_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"  # Gemini 模型名称
    openai_key: str | None = None
    
    # GitHub Webhook 配置
    github_webhook_secret: str | None = None
    
    # 服务配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False
    enable_websocket: bool = False  # 默认禁用WebSocket，使用Webhook模式
    
    # 飞书多维表格配置
    feishu_bitable_app_token: str
    feishu_task_table_id: str
    feishu_person_table_id: str
    
    # LLM 配置
    default_llm_model: str = "deepseek"
    llm_timeout: int = 30
    max_retry_attempts: int = 3
    prd_parse_timeout_seconds: int = 30
    prd_completeness_threshold: int = 70

    # 匹配配置
    match_mode: str = "full"  # "simple"=零 LLM 仅 prefilter, "full"=两阶段
    match_prefilter_limit: int = 30
    match_top_n: int = 2

    # 任务配置
    task_timeout_hours: int = 48
    max_revision_attempts: int = 2
    ai_score_threshold: int = 80

    # 分配模式: "manual"(默认,HR 选), "auto"(N1 算完直接派 Top-1)
    assign_mode: str = "manual"
    max_qa_rounds: int = 3
    reject_fallback_seconds: int = 5
    idempotency_ttl_hours: int = 24
    idempotency_db_path: str = "/tmp/taskbot_idempotency.sqlite3"

    # PR-D: 主动追踪 + AI 预验收 + 修订循环
    proactive_scan_interval_hours: int = 6
    auto_verify_threshold: int = 4   # 5 分制,>= 该值自动 merge
    max_revisions: int = 3           # 修订上限,超过升级 HR
    progress_idle_grace_hours: int = 24  # 近 24h 有进度则跳过催办
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }

settings = Settings()