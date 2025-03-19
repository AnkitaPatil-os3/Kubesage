import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "test"
    POSTGRES_PASSWORD: str = "linux"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = "5432"
    POSTGRES_DB: str = "chat_db"
    
    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = "6379"
    REDIS_PASSWORD: str = "2GUuagotBcTfuJ13sDBSlNSyxYhImbfs9Xqs7J8ncGIcljTNavUOornfUK1N4KcnbqOEBHLZp/9F7MhMos3"
    
    # RabbitMQ
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = "5672"
    RABBITMQ_VHOST: str = "/"
    
    # OpenAI Integration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Service Integration
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://10.0.32.123:8000")
    KUBECONFIG_SERVICE_URL: str = os.getenv("KUBECONFIG_SERVICE_URL", "http://10.0.32.123:8001")
    K8SGPT_SERVICE_URL: str = os.getenv("K8SGPT_SERVICE_URL", "http://10.0.32.123:8002")
    
    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Service settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
settings = Settings()