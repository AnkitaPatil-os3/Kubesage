from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = os.getenv("APP_NAME", "KubeSage Self-Healing Service")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # PostgreSQL connection
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "kubesage")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "kubesage_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "selfhealing_db")
    DATABASE_URL: str = ""  # Will be constructed from above settings
    
    # RabbitMQ settings
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT: str = os.getenv("RABBITMQ_PORT", "5672")
    RABBITMQ_VHOST: str = os.getenv("RABBITMQ_VHOST", "/kubesage")
    RABBITMQ_URL: str = ""  # Will be constructed from above settings
    
    # Redis settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "2GUuagotBcTfuJ13sDBSlNSyxYhImbfs9Xqs7J8ncGIcljTNavUOornfUK1N4KcnbqOEBHLZp/9F7MhMos3")
   
    # Service URLs
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
    KUBECONFIG_SERVICE_URL: str = os.getenv("KUBECONFIG_SERVICE_URL", "http://kubeconfig-service:8001")
    
    # SSL
    SSL_KEYFILE: Optional[str] = os.getenv("SSL_KEYFILE", "key.pem")
    SSL_CERTFILE: Optional[str] = os.getenv("SSL_CERTFILE", "cert.pem")
    
    # Watcher settings
    SELF_HEAL_API_ENDPOINT: str = os.getenv("SELF_HEAL_API_ENDPOINT", "http://self-healing-service:8005/self-heal")
    WATCH_NAMESPACE: str = os.getenv("WATCH_NAMESPACE", "default")
    WATCH_EVENT_TYPES: str = os.getenv("WATCH_EVENT_TYPES", "Warning")
    WATCH_OBJECT_KINDS: str = os.getenv("WATCH_OBJECT_KINDS", "Pod,Deployment,ReplicaSet,StatefulSet,DaemonSet")
    
    # Kubernetes configuration
    KUBE_CONFIG_PATH: str = os.getenv("KUBE_CONFIG_PATH", "~/.kube/config")
    
    # OpenAI settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    
    # Kubectl AI Agent settings
    KUBECTL_AI_AGENT_URL: Optional[str] = os.getenv("KUBECTL_AI_AGENT_URL")
    KUBECTL_AI_AGENT_TOKEN: Optional[str] = os.getenv("KUBECTL_AI_AGENT_TOKEN")
    KUBECTL_AI_AGENT_VERIFY_SSL: bool = os.getenv("KUBECTL_AI_AGENT_VERIFY_SSL", "true").lower() == "true"
    
    # ArgoCD settings
    ARGOCD_SERVER_URL: Optional[str] = os.getenv("ARGOCD_SERVER_URL")
    ARGOCD_API_TOKEN: Optional[str] = os.getenv("ARGOCD_API_TOKEN")
    ARGOCD_VERIFY_SSL: bool = os.getenv("ARGOCD_VERIFY_SSL", "true").lower() == "true"
    
    # API security
    API_BEARER_TOKEN: Optional[str] = os.getenv("API_BEARER_TOKEN")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Construct DATABASE_URL and RABBITMQ_URL
        self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        self.RABBITMQ_URL = f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # This allows extra fields to be ignored instead of causing errors

# Create an instance of the Settings class
settings = Settings()
