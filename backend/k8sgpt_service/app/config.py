from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "KubeSage K8sGPT Operations Service"
    DEBUG: bool = False
    
    # PostgreSQL connection
    POSTGRES_USER: str = "preeti"
    POSTGRES_PASSWORD: str = "linux"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "p_k8sgpt_db"
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # RabbitMQ settings
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: str = "5672"
    RABBITMQ_VHOST: str = "/k8sGPT"
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "GkjPb3lHsapqnapytiaylZsEh2xgK3jlMtbG+c9I4EcVU1+NxlRZNNGlP0mZOn5UnU1T8ZZxBhGvp1Ru"
    
    # Service URLs
    USER_SERVICE_URL: str = "https://10.0.32.122:8003"
    KUBECONFIG_SERVICE_URL: str = "https://10.0.32.122:8005"
    
    # SSL
    SSL_KEYFILE: Optional[str] = "key.pem"
    SSL_CERTFILE: Optional[str] = "cert.pem"
    
    # Analysis results directory
    ANALYSIS_DIR: str = "analysis_results"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL and RABBITMQ_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        # self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()

# Ensure the analysis directory exists
os.makedirs(settings.ANALYSIS_DIR, exist_ok=True)