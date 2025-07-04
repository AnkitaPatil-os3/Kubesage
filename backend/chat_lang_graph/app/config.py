import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address

# Load environment variables
load_dotenv(override=True)

class Settings(BaseSettings):
    """Application settings."""
    
    # Database Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "kubesage")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "k_chat_lang_db")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # LLM Configuration
    BASE_URL: str = os.getenv("URL", os.getenv("BASE_URL", "https://api.openai.com/v1"))
    MODEL_NAME: str = os.getenv("MODEL", os.getenv("MODEL_NAME", "gpt-3.5-turbo"))
    API_KEY: str = os.getenv("KEY", os.getenv("API_KEY", ""))
    
    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET_KEY", "your-secret-key-here"))
    ALGORITHM: str = os.getenv("ALGORITHM", os.getenv("JWT_ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    # Kubernetes Configuration
    KUBECONFIG_PATH: str = os.getenv("KUBECONFIG_PATH", os.path.expanduser("~/.kube/config"))
    KUBECTL_TIMEOUT: int = int(os.getenv("KUBECTL_TIMEOUT", "60"))
    
    def get_kubeconfig_path(self) -> str:
        """Get kubeconfig path, check if file exists."""
        if os.path.exists(self.KUBECONFIG_PATH):
            return self.KUBECONFIG_PATH
        
        # Try default locations
        default_paths = [
            os.path.expanduser("~/.kube/config"),
            "/etc/kubernetes/admin.conf"
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                return path
        
        return self.KUBECONFIG_PATH  # Return original even if not found
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8002"))
    
    # Service URLs
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "https://localhost:8001")
    
    # Chat Configuration
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "50000"))
    MAX_MESSAGES_PER_SESSION: int = int(os.getenv("MAX_MESSAGES_PER_SESSION", "100"))
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    
    # Rate Limiting Configuration
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
    RATE_LIMIT_WINDOW: str = os.getenv("RATE_LIMIT_WINDOW", "minute")
    
    # LangGraph Configuration
    LANGGRAPH_STREAMING: bool = os.getenv("LANGGRAPH_STREAMING", "true").lower() == "true"
    LANGGRAPH_RECURSION_LIMIT: int = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "10"))
    LANGGRAPH_TIMEOUT: int = int(os.getenv("LANGGRAPH_TIMEOUT", "300"))
    
    class Config:
        env_file = ".env"
        extra = "ignore"

# Create settings instance
settings = Settings()

# Legacy compatibility - expose individual variables (only LLM related)
BASE_URL = settings.BASE_URL
MODEL_NAME = settings.MODEL_NAME
API_KEY = settings.API_KEY

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
