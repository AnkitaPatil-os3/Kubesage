from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Union
from enum import Enum

class BackendType(str, Enum):
    ibmwatsonxai = "ibmwatsonxai"
    openai = "openai"
    localai = "localai"
    azureopenai = "azureopenai"
    amazonbedrock = "amazonbedrock"
    cohere = "cohere"
    amazonsagemaker = "amazonsagemaker"
    google = "google"
    googlevertexai = "googlevertexai"

class AutoRemediationSpec(BaseModel):        
    enabled: bool = Field(default=False)
    resources: List[str] = Field(default=["Pod", "Deployment", "Service", "Ingress"])
    similarity_requirement: str = Field(default="90", description="Defaults to 10%")

class BackOffSpec(BaseModel):
    enabled: bool = Field(default=False)
    max_retries: int = Field(default=5)

class SecretRef(BaseModel):
    name: Optional[str]
    key: Optional[str]

class AISpec(BaseModel):
    anonymized: bool = Field(default=True)
    auto_remediation: AutoRemediationSpec
    back_off: BackOffSpec
    backend: BackendType = Field(default=BackendType.openai)
    base_url: Optional[str]
    enabled: Optional[bool]
    engine: Optional[str]
    language: str = Field(default="english")
    max_tokens: str = Field(default="2048")
    model: str = Field(default="gpt-4o-mini")
    provider_id: Optional[str]
    proxy_endpoint: Optional[str]
    region: Optional[str]
    secret: Optional[SecretRef]
    topk: str = Field(default="50")

class CustomAnalyzer(BaseModel):
    name: str
    connection: Optional[Dict[str, Union[str, int]]]

class RemoteCacheSpec(BaseModel):
    azure: Optional[Dict[str, str]]
    credentials: Optional[Dict[str, str]]
    gcs: Optional[Dict[str, str]]
    interplex: Optional[Dict[str, str]]
    s3: Optional[Dict[str, str]]

class K8sGPTSpec(BaseModel):
    ai: AISpec
    custom_analyzers: Optional[List[CustomAnalyzer]]
    filters: Optional[List[str]]
    image_pull_secrets: Optional[List[Dict[str, str]]]
    integrations: Optional[Dict[str, Dict[str, Union[bool, str]]]]
    kubeconfig: Optional[Dict[str, str]]
    no_cache: Optional[bool]
    node_selector: Optional[Dict[str, str]]
    remote_cache: Optional[RemoteCacheSpec]
    repository: str = Field(default="ghcr.io/k8sgpt-ai/k8sgpt")
    resources: Optional[Dict[str, Union[Dict[str, str], List[Dict[str, str]]]]]
    sink: Optional[Dict[str, Union[str, Dict[str, str]]]]
    target_namespace: Optional[str]
    version: Optional[str]

class K8sGPTStatus(BaseModel):
    backend: Optional[str]

class K8sGPTCRD(BaseModel):
    api_version: str = Field(default="core.k8sgpt.ai/v1alpha1", alias="apiVersion")
    kind: str = "K8sGPT"
    metadata: Dict[str, object] = Field(default_factory=dict)
    spec: K8sGPTSpec
    status: Optional[K8sGPTStatus]

class ErrorDetail(BaseModel):
    sensitive: Optional[List[Dict[str, str]]]
    text: str

class ResultSpec(BaseModel):
    backend: str
    details: str
    error: List[ErrorDetail]
    kind: str
    name: str
    parent_object: str = Field(alias="parentObject")

class ResultStatus(BaseModel):
    lifecycle: Optional[str]
    webhook: Optional[str]

class ResultCRD(BaseModel):
    api_version: str = Field(alias="apiVersion")
    kind: str = "Result"
    metadata: Dict[str, object]
    spec: ResultSpec
    status: Optional[ResultStatus]