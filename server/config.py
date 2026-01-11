"""
Configuration for the download server
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    """Server configuration"""
    
    # Database
    db_host: str = os.getenv("DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("DB_PORT", "5433"))
    db_name: str = os.getenv("DB_NAME", "reyestr_db")
    db_user: str = os.getenv("DB_USER", "reyestr_user")
    db_password: str = os.getenv("DB_PASSWORD", "reyestr_password")
    
    # API Server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_title: str = "Reyestr Download Server API"
    api_version: str = "v1"
    
    # Security
    api_key_header: str = "X-API-Key"
    enable_auth: bool = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    
    # Task Management
    task_timeout_seconds: int = int(os.getenv("TASK_TIMEOUT_SECONDS", "3600"))  # 1 hour
    heartbeat_interval_seconds: int = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60"))
    max_tasks_per_client: int = int(os.getenv("MAX_TASKS_PER_CLIENT", "5"))
    
    # Database Connection Pool
    db_pool_minconn: int = int(os.getenv("DB_POOL_MINCONN", "10"))
    db_pool_maxconn: int = int(os.getenv("DB_POOL_MAXCONN", "250"))  # Support 10 clients × 20 concurrent requests
    
    # CORS
    cors_origins: list = ["*"]  # Configure for production
    
    # Telegram
    telegram_bot_token: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", None)
    
    # Redis Cache
    redis_host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl_tasks: int = int(os.getenv("CACHE_TTL_TASKS", "10"))  # 10 seconds for pending tasks
    cache_ttl_statistics: int = int(os.getenv("CACHE_TTL_STATISTICS", "30"))  # 30 seconds for statistics
    cache_ttl_documents: int = int(os.getenv("CACHE_TTL_DOCUMENTS", "60"))  # 60 seconds for documents
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = ServerConfig()
