"""
Configuration management for Feishu Bot
Supports both environment variables and YAML configuration files
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeishuConfig(BaseSettings):
    """Feishu API configuration"""
    app_id: str = Field(..., description="Feishu App ID")
    app_secret: str = Field(..., description="Feishu App Secret")
    verify_token: str = Field(..., description="Feishu Verify Token")
    encrypt_key: Optional[str] = Field(None, description="Feishu Encrypt Key")
    
    # Bitable configuration
    bitable_app_token: str = Field(..., description="Feishu Bitable App Token")
    task_table_id: Optional[str] = Field(None, description="Task Table ID")
    person_table_id: Optional[str] = Field(None, description="Person Table ID")


class LLMBackendConfig(BaseSettings):
    """LLM backend configuration"""
    api_key: str = Field(..., description="API Key")
    base_url: Optional[str] = Field(None, description="Base URL")
    model: str = Field(..., description="Model name")


class LLMConfig(BaseSettings):
    """LLM configuration"""
    default_backend: str = Field("deepseek", description="Default LLM backend")
    deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API Key")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API Key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key")


class GitHubConfig(BaseSettings):
    """GitHub configuration"""
    webhook_secret: Optional[str] = Field(None, description="GitHub Webhook Secret")


class AppConfig(BaseSettings):
    """Application configuration"""
    debug: bool = Field(False, description="Debug mode")
    log_level: str = Field("INFO", description="Log level")
    host: str = Field("0.0.0.0", description="Host")
    port: int = Field(8000, description="Port")


class TaskConfig(BaseSettings):
    """Task configuration"""
    auto_review_threshold: int = Field(80, description="Auto review threshold")
    max_retry_attempts: int = Field(2, description="Max retry attempts")
    reminder_hours: int = Field(48, description="Reminder hours")


class Settings(BaseSettings):
    """Main settings class"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__"
    )
    
    # Feishu configuration
    feishu_app_id: str = Field(..., env="FEISHU_APP_ID")
    feishu_app_secret: str = Field(..., env="FEISHU_APP_SECRET")
    feishu_verify_token: str = Field(..., env="FEISHU_VERIFY_TOKEN")
    feishu_encrypt_key: Optional[str] = Field(None, env="FEISHU_ENCRYPT_KEY")
    
    # Bitable configuration
    feishu_bitable_app_token: str = Field(..., env="FEISHU_BITABLE_APP_TOKEN")
    feishu_task_table_id: Optional[str] = Field(None, env="FEISHU_TASK_TABLE_ID")
    feishu_person_table_id: Optional[str] = Field(None, env="FEISHU_PERSON_TABLE_ID")
    
    # LLM configuration
    default_llm_backend: str = Field("deepseek", env="DEFAULT_LLM_BACKEND")
    deepseek_api_key: Optional[str] = Field(None, env="DEEPSEEK_API_KEY")
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # GitHub configuration (optional)
    github_webhook_secret: Optional[str] = Field(None, env="GITHUB_WEBHOOK_SECRET")
    
    # Application configuration
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # Task configuration
    auto_review_threshold: int = Field(80, env="AUTO_REVIEW_THRESHOLD")
    max_retry_attempts: int = Field(2, env="MAX_RETRY_ATTEMPTS")
    reminder_hours: int = Field(48, env="REMINDER_HOURS")
    
    @property
    def feishu(self) -> FeishuConfig:
        """Get Feishu configuration"""
        return FeishuConfig(
            app_id=self.feishu_app_id,
            app_secret=self.feishu_app_secret,
            verify_token=self.feishu_verify_token,
            encrypt_key=self.feishu_encrypt_key,
            bitable_app_token=self.feishu_bitable_app_token,
            task_table_id=self.feishu_task_table_id,
            person_table_id=self.feishu_person_table_id
        )
    
    @property
    def llm(self) -> LLMConfig:
        """Get LLM configuration"""
        return LLMConfig(
            default_backend=self.default_llm_backend,
            deepseek_api_key=self.deepseek_api_key,
            gemini_api_key=self.gemini_api_key,
            openai_api_key=self.openai_api_key
        )
    
    @property
    def github(self) -> Optional[GitHubConfig]:
        """Get GitHub configuration"""
        if self.github_webhook_secret:
            return GitHubConfig(webhook_secret=self.github_webhook_secret)
        return None
    
    @property
    def app(self) -> AppConfig:
        """Get application configuration"""
        return AppConfig(
            debug=self.debug,
            log_level=self.log_level,
            host=self.host,
            port=self.port
        )
    
    @property
    def task(self) -> TaskConfig:
        """Get task configuration"""
        return TaskConfig(
            auto_review_threshold=self.auto_review_threshold,
            max_retry_attempts=self.max_retry_attempts,
            reminder_hours=self.reminder_hours
        )


def load_config_from_yaml(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    if not config_file.exists():
        return {}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def merge_config_with_yaml(settings: Settings, yaml_config: Dict[str, Any]) -> Settings:
    """Merge settings with YAML configuration"""
    # This is a simplified merge - in production you might want more sophisticated merging
    for key, value in yaml_config.items():
        if hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    return settings


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        # Load YAML config first
        yaml_config = load_config_from_yaml()
        
        # Create settings from environment variables
        _settings = Settings()
        
        # Merge with YAML config if available
        if yaml_config:
            _settings = merge_config_with_yaml(_settings, yaml_config)
    
    return _settings


# Convenience function to reset settings (useful for testing)
def reset_settings():
    """Reset global settings instance"""
    global _settings
    _settings = None
