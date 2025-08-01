from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Service configuration
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "security-service")
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # User service integration
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "https://10.0.2.30:8001")
    KUBECONFIG_SERVICE_URL: str = os.getenv("KUBECONFIG_SERVICE_URL", "https://10.0.2.30:8002")
    
    # PostgreSQL Database configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "kubesage")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "k_security_db")
    
    # Kubernetes configuration
    KUBECONFIG_PATH: Optional[str] = os.getenv("KUBECONFIG_PATH")
    
    # Database URL construction
    DATABASE_URL: str = ""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
