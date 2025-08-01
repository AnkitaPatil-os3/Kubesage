# Kubernetes Cluster Onboarding & Management API – Professional Guide

This document provides a comprehensive, step-by-step explanation of the **Kubernetes Cluster Onboarding and Management API** in the Kubesage platform. It is designed for onboarding new developers, SREs, and platform engineers, ensuring a deep understanding of the code, data flow, and best practices.

---

## 1. Overview

The **Kubeconfig Service** enables users to securely onboard, manage, and interact with multiple Kubernetes clusters. It abstracts away kubeconfig files, storing cluster credentials and TLS data in a secure database, and exposes a set of RESTful APIs for all cluster lifecycle operations.

---

## 2. Key Concepts

- **ClusterConfig**: The main database model representing a Kubernetes cluster’s connection details (name, server URL, token, TLS config, user ownership, etc.).
- **User Isolation**: Each cluster is always associated with a specific user (`user_id`), ensuring strict multi-tenancy.
- **TLS Support**: Supports both secure (TLS) and insecure connections, with optional CA, client cert, and key fields.
- **Event Publishing**: All major actions (onboard, activate, delete, etc.) publish events to a message queue for audit and automation.

---

## 3. API Endpoints & Workflows

### 3.1. Onboard a Cluster

**POST** `/onboard-cluster`

- **Purpose**: Register a new Kubernetes cluster for the current user.
- **Request**: `ClusterConfigRequest` (includes cluster name, server URL, token, TLS options, etc.)
- **Workflow**:
  1. **Duplicate Check**: Ensures the user does not already have a cluster with the same name.
  2. **Record Creation**: Stores all cluster details in the `ClusterConfig` table.
  3. **Event Publishing**: Publishes a `cluster_onboarded` event for downstream consumers.
  4. **Response**: Returns a `ClusterConfigResponse` with all cluster details and a success message.

**Best Practices**:
- Never store plaintext tokens in logs.
- Always validate TLS fields if `use_secure_tls` is true.

---

### 3.2. List All Clusters

**GET** `/clusters`

- **Purpose**: Retrieve all clusters onboarded by the current user.
- **Workflow**:
  1. Queries the `ClusterConfig` table filtered by `user_id`.
  2. Returns a list of `ClusterConfigResponse` objects.

---

### 3.3. Remove a Cluster

**DELETE** `/remove-cluster/{cluster_id}`

- **Purpose**: Permanently delete a cluster configuration.
- **Workflow**:
  1. Verifies ownership (`user_id`).
  2. Deletes the record from the database.
  3. Publishes a `cluster_deleted` event.
  4. Returns a confirmation message.

---

### 3.4. Get Cluster Credentials

**GET** `/cluster/{cluster_name}/credentials`

- **Purpose**: Retrieve server URL, token, and TLS config for a named cluster.
- **Workflow**:
  1. Verifies the user owns the cluster.
  2. Returns all connection details (never logs the token).

---

### 3.5. Get Namespaces from a Cluster

**GET** `/get-namespaces/{cluster_id}`

- **Purpose**: List all namespaces in a specific cluster.
- **Workflow**:
  1. Loads cluster credentials from the database.
  2. Dynamically configures the Kubernetes Python client.
  3. Calls the Kubernetes API to list namespaces.
  4. Returns the namespace list and cluster info.

**Security**: All API calls use the user’s own token and cluster credentials, never static kubeconfig files.

---

### 3.6. Select Cluster and Get Namespaces

**POST** `/select-cluster-and-get-namespaces/{cluster_id}`

- **Purpose**: (Optional) Activate a cluster and immediately fetch its namespaces.
- **Workflow**:
  1. Verifies and activates the cluster for the user.
  2. Fetches namespaces as above.
  3. Publishes a `cluster_selected_and_namespaces_retrieved` event.

---

### 3.7. Advanced: Analyze Cluster Resources with AI

**POST** `/analyze-k8s-with-solutions/{cluster_id}`

- **Purpose**: Analyze cluster resources (pods, deployments, etc.) and get AI-generated solutions for detected issues.
- **Workflow**:
  1. Loads cluster credentials.
  2. Runs resource analysis in a background thread (supports high concurrency).
  3. For each detected problem, calls the LLM service for remediation advice.
  4. Returns a list of problems and suggested solutions.

---

### 3.8. Direct Kubectl Command Execution

**POST** `/execute-kubectl-direct/{cluster_id}`

- **Purpose**: Run arbitrary `kubectl` commands against a cluster using stored credentials (no kubeconfig file needed).
- **Workflow**:
  1. Prepares the command with `--server`, `--token`, and TLS flags.
  2. Executes in a thread pool for scalability.
  3. Returns command output, error, and metadata.

**Warning**: Only allow trusted users to use this endpoint. Always validate and sanitize input commands.

---

## 4. Data Model Deep Dive

### ClusterConfig (models.py)
```python
class ClusterConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cluster_name: str
    server_url: str
    token: str
    context_name: Optional[str]
    provider_name: Optional[str]
    tags: Optional[str]
    use_secure_tls: bool = False
    ca_data: Optional[str]
    tls_key: Optional[str]
    tls_cert: Optional[str]
    user_id: int
    is_operator_installed: bool = False
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
```

---

## 5. Security & Best Practices

- **Token Security**: Tokens are never exposed in logs or error messages.
- **TLS**: Always use `use_secure_tls` and provide CA/cert/key for production clusters.
- **User Isolation**: All queries are filtered by `user_id`.
- **Event Logging**: All major actions are published to a message queue for auditability.
- **Error Handling**: All exceptions are logged and returned as structured HTTP errors.

---

## 6. Extending the Service

- Add new endpoints for cluster health, metrics, or workload introspection.
- Integrate with external secrets managers for token storage.
- Add RBAC checks for fine-grained access control.

---

## 7. Troubleshooting

- **Cluster Not Found**: Ensure the cluster exists and belongs to the current user.
- **TLS Errors**: Double-check CA/cert/key fields and base64 encoding.
- **Kubernetes API Errors**: Check server URL, token validity, and network connectivity.

---

## 8. References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kubernetes Python Client](https://github.com/kubernetes-client/python)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Kubesage Demo Source Code](../backend/kubeconfig_service/app/)

---
