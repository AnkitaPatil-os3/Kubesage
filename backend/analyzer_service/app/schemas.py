from pydantic import BaseModel, EmailStr
from typing import List, Dict, Optional

class Alert(BaseModel):
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: str
    endsAt: str
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

class AlertRequest(BaseModel):
    alerts: List[Alert]
    receiver: Optional[str] = None
    status: Optional[str] = None
    groupLabels: Optional[Dict[str, str]] = None
    commonLabels: Optional[Dict[str, str]] = None
    commonAnnotations: Optional[Dict[str, str]] = None
    externalURL: Optional[str] = None
    version: Optional[str] = None
    groupKey: Optional[str] = None
    truncatedAlerts: Optional[int] = 0

class EmailSettings(BaseModel):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool = True  # Updated from MAIL_TLS
    MAIL_SSL_TLS: bool = False  # Updated from MAIL_SSL
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
