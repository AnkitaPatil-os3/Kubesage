import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "test"
    POSTGRES_PASSWORD: str = "linux"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = "5432"
    POSTGRES_DB: str = "chat_db"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "2GUuagotBcTfuJ13sDBSlNSyxYhImbfs9Xqs7J8ncGIcljTNavUOornfUK1N4KcnbqOEBHLZp/9F7MhMos3"
    
    # RabbitMQ
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = "5672"
    RABBITMQ_VHOST: str = "/"
    
    # OpenAI Integration
    # OPENAI_API_KEY: str = "ZMZwek2Mudo8m8OkStBzB3tMGDsce8jE"
    # OPENAI_BASE_URL: str = "https://codestral.mistral.ai/v1/"
    # OPENAI_MODEL: str = "codestral-latest"

    OPENAI_API_KEY: str = "openvino"
    OPENAI_BASE_URL: str = "http://10.0.32.182:8000/v1/"
    OPENAI_MODEL: str = "llama3.1"

    # Service Integration
    USER_SERVICE_URL: str = "https://10.0.32.123:8001"
    KUBECONFIG_SERVICE_URL: str = "https://10.0.32.123:8002"
    K8SGPT_SERVICE_URL: str = "https://10.0.32.123:8003"
    
    # Security
    JWT_SECRET_KEY: str =  "hkfiurhrugtieruyueryu"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Service settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
settings = Settings()