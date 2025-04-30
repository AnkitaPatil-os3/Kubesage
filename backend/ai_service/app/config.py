from pydantic_settings import BaseSettings
import os
from typing import Optional
from cachetools import TTLCache
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.logger import logger

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "KubeSage AI Service")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    API_PREFIX: str = os.getenv("API_PREFIX", "/ai")
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "10/minute")
    
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "nisha")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "n_ai_db")
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # RabbitMQ settings
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: str = os.getenv("RABBITMQ_PORT", "5672")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # User service URL for authentication
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL")
    
    # SSL
    SSL_KEYFILE: Optional[str] = os.getenv("SSL_KEYFILE", "key.pem")
    SSL_CERTFILE: Optional[str] = os.getenv("SSL_CERTFILE", "cert.pem")
    
    # LLM configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))  # seconds
    
    # Command execution configuration
    EXECUTION_TIMEOUT: int = int(os.getenv("EXECUTION_TIMEOUT", "30"))  # seconds
    
    # Cache configuration
    CACHE_MAXSIZE: int = int(os.getenv("CACHE_MAXSIZE", "100"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # seconds
    
    # API authentication
    API_AUTH_KEY: str = os.getenv("API_AUTH_KEY", "")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL and RABBITMQ_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields that aren't defined in the model

settings = Settings()

# Cache Setup
cache = TTLCache(maxsize=settings.CACHE_MAXSIZE, ttl=settings.CACHE_TTL)

# Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

# Log warnings for missing configurations
if not settings.API_AUTH_KEY:
    logger.warning("API_AUTH_KEY environment variable not set. API authentication is disabled.")
if not settings.OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables. LLM functionality will likely fail.")
