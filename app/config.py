from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 飞书机器人配置
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verify_token: str
    feishu_encrypt_key: Optional[str] = None
    feishu_bot_user_id: Optional[str] = None  # 机器人的用户ID（可选，用于群聊邀请）
    
    # LLM 模型配置
    deepseek_key: Optional[str] = None
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    
    # GitHub Webhook 配置
    github_webhook_secret: Optional[str] = None
    
    # 服务配置
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    debug: bool = False
    
    # 飞书多维表格配置
    feishu_bitable_app_token: str
    feishu_task_table_id: str
    feishu_person_table_id: str
    
    # LLM 配置
    default_llm_model: str = "deepseek"
    llm_timeout: int = 30
    max_retry_attempts: int = 3
    
    # 任务配置
    task_timeout_hours: int = 48
    max_revision_attempts: int = 2
    ai_score_threshold: int = 80
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }

settings = Settings()