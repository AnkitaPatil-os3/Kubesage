import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_k8s_client():
    with patch('kubernetes.client.CustomObjectsApi') as mock:
        yield mock

@pytest.fixture
def mock_k8s_config():
    with patch('kubernetes.config.load_kube_config'), \
         patch('kubernetes.config.load_incluster_config'):
        yield

@pytest.fixture
def sample_k8sgpt_crd():
    return {
        "apiVersion": "core.k8sgpt.ai/v1alpha1",
        "kind": "K8sGPT",
        "metadata": {"name": "test-k8sgpt", "namespace": "default"},
        "spec": {
            "ai": {
                "backend": "openai",
                "anonymized": True,
                "autoRemediation": {
                    "enabled": False,
                    "resources": ["Pod", "Deployment"],
                    "similarityRequirement": "90"
                }
            }
        }
    }

@pytest.fixture
def sample_result_crd():
    return {
        "apiVersion": "core.k8sgpt.ai/v1alpha1",
        "kind": "Result",
        "metadata": {"name": "test-result", "namespace": "default"},
        "spec": {
            "backend": "openai",
            "details": "test details",
            "error": [{"text": "test error"}],
            "kind": "Pod",
            "name": "test-pod",
            "parentObject": "test-parent"
        }
    }