import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "nisha"
    POSTGRES_PASSWORD: str = "linux"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = "5432"
    POSTGRES_DB: str = "n_chat_db"
    
    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = "6379"
    REDIS_PASSWORD: str = "GkjPb3lHsapqnapytiaylZsEh2xgK3jlMtbG+c9I4EcVU1+NxlRZNNGlP0mZOn5UnU1T8ZZxBhGvp1Ru"
    
    # RabbitMQ
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = "5672"
    RABBITMQ_VHOST: str = "/"
    
    # OpenAI Integration
    OPENAI_API_KEY: str = "ZMZwek2Mudo8m8OkStBzB3tMGDsce8jE"
    OPENAI_BASE_URL: str = "https://codestral.mistral.ai/v1/"
    OPENAI_MODEL: str = "codestral-latest"
    
    # Service Integration
    USER_SERVICE_URL: str = "https://10.0.34.129:8000"
    KUBECONFIG_SERVICE_URL: str = "https://10.0.34.129:8001"
    K8SGPT_SERVICE_URL: str = "https://10.0.34.129:8002"
    
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