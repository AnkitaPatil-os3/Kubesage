from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "KubeSage K8sGPT Operations Service")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "nisha")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "n_k8sgpt_db")
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # RabbitMQ settings
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: str = os.getenv("RABBITMQ_PORT", "5672")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/k8sGPT")
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "2GUuagotBcTfuJ13sDBSlNSyxYhImbfs9Xqs7J8ncGIcljTNavUOornfUK1N4KcnbqOEBHLZp/9F7MhMos3")
   
    # Service URLs
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL")
    KUBECONFIG_SERVICE_URL: str = os.getenv("KUBECONFIG_SERVICE_URL")
    
    # SSL
    SSL_KEYFILE: Optional[str] = os.getenv("SSL_KEYFILE", "key.pem")
    SSL_CERTFILE: Optional[str] = os.getenv("SSL_CERTFILE", "cert.pem")
    
    # Analysis results directory
    ANALYSIS_DIR: str = os.getenv("ANALYSIS_DIR", "analysis_results")
    
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
