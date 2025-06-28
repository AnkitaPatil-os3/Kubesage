from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Service configuration
    SERVICE_NAME: str = "security-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # User service integration
    USER_SERVICE_URL: str = "https://10.0.32.123:8001"
    
    # Database (if needed for caching)
    DATABASE_URL: Optional[str] = None
    
    # Kubernetes configuration
    KUBECONFIG_PATH: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()