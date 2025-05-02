import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "nisha")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "n_chat_db")
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "2GUuagotBcTfuJ13sDBSlNSyxYhImbfs9Xqs7J8ncGIcljTNavUOornfUK1N4KcnbqOEBHLZp/9F7MhMos3")
    
    # RabbitMQ
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    
    # OpenAI Integration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "openvino")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "Mistral-7B-Instruct-v0.2-fp16-ov")

    # Service Integration
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL")
    KUBECONFIG_SERVICE_URL: str = os.getenv("KUBECONFIG_SERVICE_URL")
    K8SGPT_SERVICE_URL: str = os.getenv("K8SGPT_SERVICE_URL")
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "hkfiurhrugtieruyueryu")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Service settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
settings = Settings()
