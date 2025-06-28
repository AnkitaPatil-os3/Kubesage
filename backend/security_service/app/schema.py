from pydantic import BaseModel
from typing import Dict, List, Optional, Union
from datetime import datetime

class VulnerabilityInfo(BaseModel):
    report_name: str
    namespace: str
    vulnerability_id: str
    title: str
    severity: str
    score: Optional[float]
    resource: str
    installed_version: str
    fixed_version: str
    primary_link: Optional[str]

class VulnerabilitySummary(BaseModel):
    report_name: str
    namespace: str
    container_name: Optional[str]
    image_repository: str
    image_tag: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_vulnerabilities: int

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Union[Dict, List]]
    timestamp: str

class HealthCheck(BaseModel):
    status: str
    kubernetes: str
    timestamp: str
    service: str
    version: str

class VulnerabilityFilter(BaseModel):
    severity: Optional[str] = None
    fixable_only: Optional[bool] = False
    limit: Optional[int] = None
    namespace: Optional[str] = None

class SecurityMetrics(BaseModel):
    total_reports: int
    total_vulnerabilities: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    fixable_count: int
    affected_namespaces: int
    last_updated: str