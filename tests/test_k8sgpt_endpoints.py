import pytest
from models import K8sGPTCRD
from fastapi import status

def test_create_k8sgpt(client, mock_k8s_client, sample_k8sgpt_crd):
    mock_k8s_client.return_value.create_namespaced_custom_object.return_value = sample_k8sgpt_crd
    response = client.post(
        "/k8sgpt/default",
        json=sample_k8sgpt_crd
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == sample_k8sgpt_crd

def test_get_k8sgpt(client, mock_k8s_client, sample_k8sgpt_crd):
    mock_k8s_client.return_value.get_namespaced_custom_object.return_value = sample_k8sgpt_crd
    response = client.get("/k8sgpt/default/test-k8sgpt")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == sample_k8sgpt_crd

def test_list_k8sgpts(client, mock_k8s_client, sample_k8sgpt_crd):
    mock_k8s_client.return_value.list_namespaced_custom_object.return_value = {"items": [sample_k8sgpt_crd]}
    response = client.get("/k8sgpt?namespace=default")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [sample_k8sgpt_crd]

def test_update_k8sgpt(client, mock_k8s_client, sample_k8sgpt_crd):
    updated_crd = {**sample_k8sgpt_crd, "spec": {"ai": {"backend": "localai"}}}
    mock_k8s_client.return_value.patch_namespaced_custom_object.return_value = updated_crd
    response = client.put(
        "/k8sgpt/default/test-k8sgpt",
        json=updated_crd
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == updated_crd

def test_delete_k8sgpt(client, mock_k8s_client):
    mock_k8s_client.return_value.delete_namespaced_custom_object.return_value = {}
    response = client.delete("/k8sgpt/default/test-k8sgpt")
    assert response.status_code == status.HTTP_204_NO_CONTENT

def test_watch_k8sgpts(client, mock_k8s_client):
    mock_watch = mock_k8s_client.return_value.list_namespaced_custom_object
    mock_watch.return_value = [{"type": "ADDED", "object": {"metadata": {"name": "test"}}}]
    response = client.get("/k8sgpt/watch?namespace=default")
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers["content-type"]

def test_k8sgpt_validation(client):
    invalid_crd = {
        "apiVersion": "core.k8sgpt.ai/v1alpha1",
        "kind": "K8sGPT",
        "metadata": {"name": "test"},
        "spec": {"ai": {}}  # Missing required backend field
    }
    response = client.post("/k8sgpt/default", json=invalid_crd)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY