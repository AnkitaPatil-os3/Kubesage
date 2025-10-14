import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # User Service
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "https://10.0.32.106:8001")
    
    # RabbitMQ
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    # Service
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8007))
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"

    # Database - PostgreSQL Configuration
    POSTGRES_USER = os.getenv("POSTGRES_USER", "kubesage")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "linux")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
    POSTGRES_DB = os.getenv("POSTGRES_DB", "onboard_db")
    
    # Build PostgreSQL URL
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    SKIP_TLS_VERIFY = os.getenv("SKIP_TLS_VERIFY", "false").lower() == "true"

    # Agent
    @staticmethod
    def generate_agent_id():
        import uuid
        return str(uuid.uuid4())

settings = Settings()
