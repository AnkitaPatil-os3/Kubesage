import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Service Configuration
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8008, env="PORT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # User Service Configuration (for authentication)
    USER_SERVICE_URL: str = Field(default="https://10.0.32.106:8001", env="USER_SERVICE_URL")
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = Field(default="localhost", env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(default=5672, env="RABBITMQ_PORT")
    RABBITMQ_USER: str = Field(default="guest", env="RABBITMQ_USER")
    RABBITMQ_PASSWORD: str = Field(default="guest", env="RABBITMQ_PASSWORD")
    RABBITMQ_VHOST: str = Field(default="/", env="RABBITMQ_VHOST")
    
    # WebSocket Configuration
    WEBSOCKET_TIMEOUT: int = Field(default=30, env="WEBSOCKET_TIMEOUT")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # SSL Configuration
    SSL_KEYFILE: str = Field(default="key.pem", env="SSL_KEYFILE")
    SSL_CERTFILE: str = Field(default="cert.pem", env="SSL_CERTFILE")
    USE_SSL: bool = Field(default=False, env="USE_SSL")

    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
