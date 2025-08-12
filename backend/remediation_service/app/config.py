from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "KubeSage Remediation Service")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "kubesage")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "k_remediation_db")
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # User service URL for authentication
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
    KUBECONFIG_SERVICE_URL: str = os.getenv("KUBECONFIG_SERVICE_URL", "http://localhost:8002")

    # LLM settings for remediation
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "True").lower() == "true"
    
    # SSL
    SSL_KEYFILE: Optional[str] = os.getenv("SSL_KEYFILE", "key.pem")
    SSL_CERTFILE: Optional[str] = os.getenv("SSL_CERTFILE", "cert.pem")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # This will ignore extra environment variables
settings = Settings()
