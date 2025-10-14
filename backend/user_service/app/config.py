from pydantic_settings import BaseSettings
import os
from typing import Optional, ClassVar, List    #new classvar, List
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()  # This will load the .env file from the current directory
# new
ROLE_OPTIONS = [
    "Super Admin",
    "Platform Engineer",
    "DevOps",
    "Developer",
    "Security Engineer"
]

class Settings(BaseSettings):
    ROLE_OPTIONS: ClassVar[List[str]] = [
        "Super Admin",
        "Platform Engineer",
        "DevOps",
        "Developer",
        "Security Engineer"
    ]
# new
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "KubeSage User Authentication Service")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    DATABASE_URL: str = ""  # Will be constructed from above settings

    # Email Configuration
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str = os.getenv("MAIL_FROM")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME")
    MAIL_STARTTLS: bool = os.getenv("MAIL_TLS", "True").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL", "False").lower() == "true"
    SERVER_BASE_URL: str = os.getenv("SERVER_BASE_URL")
    USER_CONFIRMATION_TIMEOUT: int = int(os.getenv("USER_CONFIRMATION_TIMEOUT"))
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL")
    MAIL_RECIPIENT: str = os.getenv("MAIL_RECIPIENT")

    # RabbitMQ settings
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST")
    RABBITMQ_PORT: str = os.getenv("RABBITMQ_PORT")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST")
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # Token settings
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Long-lived refresh tokens
    
    # Session management
    MAX_SESSIONS_PER_USER: int = 5  # Limit concurrent sessions
    SESSION_CLEANUP_INTERVAL: int = 3600  # Cleanup every hour (seconds)
    
    # Security settings
    REQUIRE_DEVICE_FINGERPRINT: bool = True
    ALLOW_MULTIPLE_SESSIONS: bool = True
   
    
    # SSL
    SSL_KEYFILE: Optional[str] = os.getenv("SSL_KEYFILE", "key.pem")
    SSL_CERTFILE: Optional[str] = os.getenv("SSL_CERTFILE", "cert.pem")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL and RABBITMQ_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/{self.RABBITMQ_VHOST}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
