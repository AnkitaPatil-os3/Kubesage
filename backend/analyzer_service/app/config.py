import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LLM_SERVICE_URL: str = os.getenv("CHAT_SERVICE_URL", "https://10.0.32.106:8004")
    ENFORCER_URL: str = os.getenv("ENFORCER_URL", "http://localhost:8000")

    # Email Configuration
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "nisha30603@gmail.com")  # Use a valid email here
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "KubeSage Alert System")
    MAIL_STARTTLS: bool = True  # Updated parameter name
    MAIL_SSL_TLS: bool = False  # Updated parameter name
    ALERT_EMAIL_RECIPIENT: str = os.getenv("ALERT_EMAIL_RECIPIENT", "nisha30603@gmail.com")

settings = Settings()
