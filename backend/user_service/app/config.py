# hi
from pydantic_settings import BaseSettings
import os
from typing import Optional, ClassVar, List    #new classvar, List
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()  # This will load the .env file from the current directory
# new
ROLE_OPTIONS = [
    "Super Admin",
    "platform_engineer",
    "devops",
    "Developer",
    "Security Engineer"
]

class Settings(BaseSettings):
    ROLE_OPTIONS: ClassVar[List[str]] = [
        "Super Admin",
        "platform_engineer",
        "devops",
        "Developer",
        "Security Engineer"
    ]
# new
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "KubeSage User Authentication Service")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "vaishnavi")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "v_user_db")
    DATABASE_URL: str = ""  # Will be constructed from above settings

    # Email Configuration
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "nisha16063@gmail.com")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "jdmeiescbhgfryru")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "nisha16063@gmail.com")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587"))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "KubeSage Alert System")
    MAIL_STARTTLS: bool = os.getenv("MAIL_TLS", "True").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL", "False").lower() == "true"
    SERVER_BASE_URL: str = os.getenv("SERVER_BASE_URL", "https://10.0.32.105:8001")
    USER_CONFIRMATION_TIMEOUT: int = int(os.getenv("USER_CONFIRMATION_TIMEOUT", "3600"))
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "https://10.0.32.105:5173")
    MAIL_RECIPIENT: str = os.getenv("MAIL_RECIPIENT", "nisha.chaurasiya@os3infotech.com")

    # RabbitMQ settings
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: str = os.getenv("RABBITMQ_PORT", "5672")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/")
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # Token settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ggt767yfhgfhkkhigffjkjhkj333hkjhkjj")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # Long-lived refresh tokens
    
    # Session management
    MAX_SESSIONS_PER_USER: int = 5  # Limit concurrent sessions
    SESSION_CLEANUP_INTERVAL: int = 3600  # Cleanup every hour (seconds)
    
    # Security settings
    REQUIRE_DEVICE_FINGERPRINT: bool = True
    ALLOW_MULTIPLE_SESSIONS: bool = True
    
    # OpenAI Integration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "openvino")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "http://10.0.32.182:8000/v1/")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "Qwen2.5-7B-Instruct-int4-ov")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
    
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

# Role to permissions mapping matching frontend/src/config/permissions.ts
ROLE_PERMISSIONS = {
    "Super Admin": ["all"],

    "platform_engineer": [
        "dashboard",
        "clusters",
        "applications",
        "workloads",
        "analyze",
        "chatops",
        "insights",
        "observability",
        "carbon-emission",
        "cost",
        "backup",
        "security",
        "settings",
        "integrations",
        "help",
    ],

    "devops": [
        "dashboard",
        "clusters",
        "applications",
        "workloads",
        "chatops",
        "insights",
        "observability",
        "cost",
        "remediations",
        "backup",
        "settings",
        "integrations",
        "help",
    ],

    "Developer": [
        "dashboard",
        "applications",
        "workloads",
        "observability",
        "analyze",
        "chatops",
        "insights",
        "settings",
        "help",
    ],

    "Security Engineer": [
        "dashboard",
        "security",
        "secrets",
        "compliance",
        "remediations",
        "anomalies",
        "settings",
        "help",
    ],
}
