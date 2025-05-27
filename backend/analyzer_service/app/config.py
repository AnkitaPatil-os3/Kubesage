import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv("app/.env")  # Adjust the path if needed

class Settings(BaseSettings):
    LLM_SERVICE_URL: str = os.getenv("CHAT_SERVICE_URL")
    ENFORCER_URL: str = os.getenv("ENFORCER_URL")

    # Email Configuration
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: str = os.getenv("MAIL_FROM")  # Use a valid email here
    MAIL_PORT: int = int(os.getenv("MAIL_PORT"))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME")
    MAIL_STARTTLS: bool = True  # Updated parameter name
    MAIL_SSL_TLS: bool = False  # Updated parameter name
    ALERT_EMAIL_RECIPIENT: str = os.getenv("MAIL_RECIPIENT")
    
    # Server configuration
    SERVER_BASE_URL: str = os.getenv("SERVER_BASE_URL")


    # Database configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")

settings = Settings()
