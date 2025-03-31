import pytest
from models import ResultCRD
from fastapi import status

def test_create_result(client, mock_k8s_client, sample_result_crd):
    mock_k8s_client.return_value.create_namespaced_custom_object.return_value = sample_result_crd
    response = client.post(
        "/results/default",
        json=sample_result_crd
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == sample_result_crd

def test_get_result(client, mock_k8s_client, sample_result_crd):
    mock_k8s_client.return_value.get_namespaced_custom_object.return_value = sample_result_crd
    response = client.get("/results/default/test-result")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == sample_result_crd

def test_list_results(client, mock_k8s_client, sample_result_crd):
    mock_k8s_client.return_value.list_namespaced_custom_object.return_value = {"items": [sample_result_crd]}
    response = client.get("/results?namespace=default")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [sample_result_crd]

def test_update_result(client, mock_k8s_client, sample_result_crd):
    updated_crd = {**sample_result_crd, "spec": {"backend": "localai"}}
    mock_k8s_client.return_value.patch_namespaced_custom_object.return_value = updated_crd
    response = client.put(
        "/results/default/test-result",
        json=updated_crd
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == updated_crd

def test_delete_result(client, mock_k8s_client):
    mock_k8s_client.return_value.delete_namespaced_custom_object.return_value = {}
    response = client.delete("/results/default/test-result")
    assert response.status_code == status.HTTP_204_NO_CONTENT

def test_watch_results(client, mock_k8s_client):
    mock_watch = mock_k8s_client.return_value.list_namespaced_custom_object
    mock_watch.return_value = [{"type": "ADDED", "object": {"metadata": {"name": "test"}}}]
    response = client.get("/results/watch?namespace=default")
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers["content-type"]

def test_result_validation(client):
    invalid_crd = {
        "apiVersion": "core.k8sgpt.ai/v1alpha1",
        "kind": "Result",
        "metadata": {"name": "test"},
        "spec": {}  # Missing required fields
    }
    response = client.post("/results/default", json=invalid_crd)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY