import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # Database Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "kubesage_chat")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # LLM Configuration - Support multiple providers
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mistral")  # mistral, openai, ollama
    
    # Mistral Configuration
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "dq4yY78RkujcBjUMjgTwXRmAbE4zrt4h")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "codestral-latest")
    MISTRAL_BASE_URL: str = os.getenv("MISTRAL_BASE_URL", "https://codestral.mistral.ai/v1/")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration based on provider."""
        if self.LLM_PROVIDER.lower() == "mistral":
            return {
                "provider": "mistral",
                "api_key": self.MISTRAL_API_KEY,
                "model": self.MISTRAL_MODEL,
                "base_url": self.MISTRAL_BASE_URL
            }
        elif self.LLM_PROVIDER.lower() == "openai":
            return {
                "provider": "openai",
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "base_url": self.OPENAI_BASE_URL
            }
        elif self.LLM_PROVIDER.lower() == "ollama":
            return {
                "provider": "ollama",
                "api_key": "",
                "model": self.OLLAMA_MODEL,
                "base_url": self.OLLAMA_BASE_URL
            }
        else:
            # Default to Mistral
            return {
                "provider": "mistral",
                "api_key": self.MISTRAL_API_KEY,
                "model": self.MISTRAL_MODEL,
                "base_url": self.MISTRAL_BASE_URL
            }
    
    # Kubernetes Configuration
    KUBECONFIG_PATH: str = os.getenv("KUBECONFIG_PATH", "/home/aastha/rancher.yaml")
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
    
    # JWT Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET_KEY", "your-secret-key-here"))
    ALGORITHM: str = os.getenv("ALGORITHM", os.getenv("JWT_ALGORITHM", "HS256"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Application Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Service URLs
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "https://localhost:8001")
    
    # Chat Configuration
    MAX_MESSAGE_LENGTH: int = int(os.getenv("MAX_MESSAGE_LENGTH", "50000"))
    MAX_MESSAGES_PER_SESSION: int = int(os.getenv("MAX_MESSAGES_PER_SESSION", "100"))
    SESSION_TIMEOUT_HOURS: int = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    
    # Error Collection Configuration
    COLLECT_ERRORS_ON_NEW_CHAT: bool = os.getenv("COLLECT_ERRORS_ON_NEW_CHAT", "true").lower() == "true"
    MAX_ERRORS_PER_TYPE: int = int(os.getenv("MAX_ERRORS_PER_TYPE", "10"))
    ERROR_COLLECTION_TIMEOUT: int = int(os.getenv("ERROR_COLLECTION_TIMEOUT", "30"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
