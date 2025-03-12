from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "KubeSage User Authentication Service"
    DEBUG: bool = False
    
    # PostgreSQL connection
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "user_auth_db"
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # RabbitMQ settings
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: str = "5672"
    RABBITMQ_VHOST: str = "/"
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # Token settings
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # SSL
    SSL_KEYFILE: Optional[str] = "key.pem"
    SSL_CERTFILE: Optional[str] = "cert.pem"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL and RABBITMQ_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
