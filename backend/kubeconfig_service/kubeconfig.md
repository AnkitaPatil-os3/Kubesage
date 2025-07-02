# Kubernetes Configuration Service API

A comprehensive FastAPI-based service for managing Kubernetes cluster configurations, providing cluster onboarding, resource analysis, AI-powered solutions, and kubectl command execution capabilities.

## Features

- **Multi-Cluster Management**: Onboard and manage multiple Kubernetes clusters
- **Dynamic Cluster Access**: Connect to clusters using server URL and token authentication
- **AI-Powered Analysis**: Analyze Kubernetes resources with AI-generated solutions
- **Resource Monitoring**: Real-time resource usage and health monitoring
- **Secure Authentication**: JWT-based user authentication and authorization
- **Kubectl Integration**: Execute kubectl commands directly through API
- **Prometheus Integration**: Resource usage metrics and monitoring

## Technology Stack

- **Backend**: FastAPI + SQLModel
- **Database**: PostgreSQL/SQLite with SQLModel ORM
- **Authentication**: JWT tokens with user-based access control
- **Kubernetes**: Official Kubernetes Python client
- **AI/LLM**: Custom LLM service for intelligent solutions
- **Monitoring**: Prometheus integration for metrics
- **Message Queue**: Event publishing for cluster operations

## Base URL
```
https://your-domain.com/kubeconfig/
```

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## API Endpoints

### 1. Cluster Onboarding

#### Onboard New Cluster
- **URL**: `/onboard-cluster`
- **Method**: `POST`
- **Description**: Onboard a new Kubernetes cluster using server URL and token
- **Request Body**:
```json
{
    "cluster_name": "production-cluster",
    "server_url": "https://k8s-api.example.com:6443",
    "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
    "context_name": "production-context",
    "provider_name": "AWS EKS",
    "tags": ["production", "aws", "us-west-2"],
    "use_secure_tls": true,
    "ca_data": "LS0tLS1CRUdJTi...",  // Base64 encoded CA certificate (optional)
    "tls_cert": "LS0tLS1CRUdJTi...", // Base64 encoded client certificate (optional)
    "tls_key": "LS0tLS1CRUdJTi..."   // Base64 encoded client key (optional)
}
```
- **Response Success (201)**:
```json
{
    "id": 1,
    "cluster_name": "production-cluster",
    "server_url": "https://k8s-api.example.com:6443",
    "context_name": "production-context",
    "provider_name": "AWS EKS",
    "tags": ["production", "aws", "us-west-2"],
    "use_secure_tls": true,
    "ca_data": "LS0tLS1CRUdJTi...",
    "tls_key": "LS0tLS1CRUdJTi...",
    "tls_cert": "LS0tLS1CRUdJTi...",
    "user_id": 123,
    "is_operator_installed": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "message": "Cluster onboarded successfully"
}
```

### 2. Cluster Management

#### List All Clusters
- **URL**: `/clusters`
- **Method**: `GET`
- **Description**: Get all onboarded clusters for the current user
- **Response Success (200)**:
```json
{
    "clusters": [
        {
            "id": 1,
            "cluster_name": "production-cluster",
            "server_url": "https://k8s-api.example.com:6443",
            "context_name": "production-context",
            "provider_name": "AWS EKS",
            "tags": ["production", "aws"],
            "use_secure_tls": true,
            "is_operator_installed": false,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

#### Remove Cluster
- **URL**: `/remove-cluster/{cluster_id}`
- **Method**: `DELETE`
- **Description**: Remove a cluster configuration
- **Parameters**:
  - `cluster_id` (int): ID of the cluster to remove
- **Response Success (200)**:
```json
{
    "message": "Cluster 'production-cluster' successfully removed"
}
```

### 3. Namespace Operations

#### Select Cluster and Get Namespaces
- **URL**: `/select-cluster-and-get-namespaces/{cluster_id}`
- **Method**: `POST`
- **Description**: Select a cluster and retrieve its namespaces
- **Parameters**:
  - `cluster_id` (int): ID of the cluster
- **Response Success (200)**:
```json
{
    "success": true,
    "namespaces_retrieved": true,
    "cluster_info": {
        "id": 1,
        "cluster_name": "production-cluster",
        "server_url": "https://k8s-api.example.com:6443",
        "context_name": "production-context",
        "provider_name": "AWS EKS",
        "tags": ["production", "aws"],
        "use_secure_tls": true,
        "is_operator_installed": false,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    },
    "namespaces": [
        "default",
        "kube-system",
        "kube-public",
        "production-app",
        "monitoring"
    ],
    "namespace_count": 5,
    "message": "Successfully retrieved 5 namespaces from cluster 'production-cluster'"
}
```

#### Get Namespaces from Specific Cluster
- **URL**: `/get-namespaces/{cluster_id}`
- **Method**: `GET`
- **Description**: Retrieve namespaces from a specific cluster
- **Parameters**:
  - `cluster_id` (int): ID of the cluster
- **Response Success (200)**:
```json
{
    "success": true,
    "cluster_id": 1,
    "cluster_name": "production-cluster",
    "server_url": "https://k8s-api.example.com:6443",
    "provider_name": "AWS EKS",
    "context_name": "production-context",
    "use_secure_tls": true,
    "namespace_count": 5,
    "namespaces": [
        "default",
        "kube-system",
        "kube-public",
        "production-app",
        "monitoring"
    ],
    "retrieved_at": "2024-01-15T10:35:00Z"
}
```

### 4. Cluster Credentials

#### Get Cluster Credentials by Name
- **URL**: `/cluster/{cluster_name}/credentials`
- **Method**: `GET`
- **Description**: Get cluster connection details by cluster name
- **Parameters**:
  - `cluster_name` (string): Name of the cluster
- **Response Success (200)**:
```json
{
    "success": true,
    "message": "Cluster credentials retrieved successfully",
    "cluster": {
        "cluster_id": 1,
        "cluster_name": "production-cluster",
        "server_url": "https://k8s-api.example.com:6443",
        "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
        "context_name": "production-context",
        "provider_name": "AWS EKS",
        "use_secure_tls": true,
        "tls_config": {
            "ca_data": "LS0tLS1CRUdJTi...",
            "tls_cert": "LS0tLS1CRUdJTi...",
            "tls_key": "LS0tLS1CRUdJTi..."
        },
        "is_operator_installed": false,
        "tags": ["production", "aws"],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }
}
```

### 5. AI-Powered Kubernetes Analysis

#### Analyze Kubernetes Resources with AI Solutions
- **URL**: `/analyze-k8s-with-solutions/{cluster_id}`
- **Method**: `POST`
- **Description**: Analyze Kubernetes resources and get AI-generated solutions
- **Parameters**:
  - `cluster_id` (int): ID of the cluster to analyze
- **Query Parameters**:
  - `namespace` (string, optional): Specific namespace to analyze
  - `resource_types` (array, optional): Resource types to analyze
    - Default: `["pods", "deployments", "services", "secrets", "storageclasses", "ingress", "pvc"]`
- **Example Request**:
```
POST /analyze-k8s-with-solutions/1?namespace=production-app&resource_types=pods&resource_types=deployments
```
- **Response Success (200)**:
```json
{
    "cluster_id": 1,
    "cluster_name": "production-cluster",
    "server_url": "https://k8s-api.example.com:6443",
    "provider_name": "AWS EKS",
    "namespace": "production-app",
    "analyzed_resource_types": ["pods", "deployments"],
    "total_problems": 2,
    "problems_with_solutions": [
        {
            "problem": {
                "kind": "Pod",
                "name": "nginx-deployment-abc123",
                "namespace": "production-app",
                "errors": [
                    {
                        "Text": "Pod is in Pending state",
                        "KubernetesDoc": "",
                        "Sensitive": []
                    }
                ],
                "details": "",
                "parentObject": ""
            },
            "solution": {
                "solution_summary": "Pod scheduling issue - insufficient resources",
                "detailed_solution": "The pod is pending due to insufficient CPU/memory resources in the cluster. Consider scaling the cluster or adjusting resource requests.",
                "remediation_steps": [
                    {
                        "step_id": 1,
                        "action_type": "INVESTIGATE",
                        "description": "Check cluster resource availability",
                        "command": "kubectl describe nodes",
                        "expected_outcome": "Identify nodes with available resources"
                    },
                    {
                        "step_id": 2,
                        "action_type": "SCALE",
                        "description": "Scale cluster nodes if needed",
                        "command": "kubectl get nodes -o wide",
                        "expected_outcome": "Verify node capacity and scaling options"
                    }
                ],
                "confidence_score": 0.85,
                "estimated_time_mins": 15,
                "additional_notes": "Monitor resource usage after resolution"
            }
        }
    ]
}
```

### 6. Kubectl Command Execution

#### Execute Kubectl Command Directly
- **URL**: `/execute-kubectl-direct/{cluster_id}`
- **Method**: `POST`
- **Description**: Execute kubectl commands directly on a specific cluster
- **Parameters**:
  - `cluster_id` (int): ID of the cluster
- **Request Body**:
```json
{
    "command": "kubectl get pods -n production-app"
}
```
- **Response Success (200)**:
```json
{
    "success": true,
    "output": "NAME                               READY   STATUS    RESTARTS   AGE\nnginx-deployment-abc123-xyz789     1/1     Running   0          2d\napi-service-def456-uvw012          1/1     Running   1          1d",
    "error": null,
    "command": "kubectl get pods -n production-app --server=https://k8s-api.example.com:6443 --token=eyJhbGciOiJSUzI1NiIsImtpZCI6... --insecure-skip-tls-verify=true",
    "return_code": 0,
    "cluster_info": {
        "cluster_id": 1,
        "cluster_name": "production-cluster",
        "server_url": "https://k8s-api.example.com:6443",
        "provider_name": "AWS EKS"
    },
    "executed_at": "2024-01-15T10:40:00Z",
    "execution_method": "direct"
}
```

### 7. Monitoring and Metrics

#### Get Resource Usage Metrics
- **URL**: `/metrics/resource-usage`
- **Method**: `GET`
- **Description**: Get resource usage metrics from Prometheus
- **Query Parameters**:
  - `username` (string): Username for filtering
  - `metric` (string): Metric type (`cpu` or `memory`)
  - `namespace` (string, optional): Namespace filter (default: `default`)
  - `duration` (int, optional): Time duration in seconds (default: `3600`)
  - `step` (int, optional): Step interval in seconds (default: `300`)
- **Example Request**:
```
GET /metrics/resource-usage?username=john.doe&metric=cpu&namespace=production&duration=7200&step=600
```
- **Response Success (200)**:
```json
{
    "data": [
        {
            "time": "10:00",
            "usage": 0.45
        },
        {
            "time": "10:05",
            "usage": 0.52
        },
        {
            "time": "10:10",
            "usage": 0.38
        }
    ]
}
```

#### Get Node Status Across All Clusters
- **URL**: `/nodes/status/all-clusters`
- **Method**: `GET`
- **Description**: Get node health status across all clusters
- **Response Success (200)**:
```json
{
    "clusters": {
        "production-cluster": {
            "ready": 5,
            "not_ready": 0,
            "total": 5
        },
        "staging-cluster": {
            "ready": 3,
            "not_ready": 1,
            "total": 4
        }
    },
    "totals": {
        "ready": 8,
        "not_ready": 1,
        "total": 9
    }
}
```

## Resource Types for Analysis

The following resource types are supported for Kubernetes analysis:

- **pods**: Pod status, container health, restart counts
- **deployments**: Deployment availability, replica status
- **services**: Service endpoints, connectivity issues
- **secrets**: Secret validation, usage analysis, certificate expiration
- **storageclasses**: Storage class configuration and defaults
- **ingress**: Ingress rules, TLS configuration, backend services
- **pvc**: PersistentVolumeClaim status and binding issues

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required or invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server-side error

### Error Response Format
```json
{
    "detail": "Error message describing what went wrong"
}
```

## Authentication Setup

### Getting JWT Token

1. **Login to get access token**:
```bash
curl -X POST "https://your-domain.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your-username",
    "password": "your-password"
  }'
```

2. **Response**:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}
```


## Configuration

### Environment Variables

Set the following environment variables for proper configuration:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/kubeconfig_db

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# LLM Configuration (for AI analysis)
LLM_ENABLED=true
LLM_API_URL=https://your-llm-service.com/api
LLM_API_KEY=your-llm-api-key

# Prometheus Configuration
PROMETHEUS_URL=http://prometheus-server:9090

# Message Queue Configuration
RABBITMQ_URL=amqp://user:password@localhost:5672/
```


## Usage Examples

### Complete Workflow Example

1. **Onboard a new cluster**:
```bash
curl -X POST "https://your-domain.com/kubeconfig/onboard-cluster" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_name": "my-production-cluster",
    "server_url": "https://k8s-api.example.com:6443",
    "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
    "context_name": "production",
    "provider_name": "AWS EKS",
    "tags": ["production", "aws"],
    "use_secure_tls": true
  }'
```

2. **List all clusters**:
```bash
curl -X GET "https://your-domain.com/kubeconfig/clusters" \
  -H "Authorization: Bearer $TOKEN"
```

3. **Get namespaces from a cluster**:
```bash
curl -X GET "https://your-domain.com/kubeconfig/get-namespaces/1" \
  -H "Authorization: Bearer $TOKEN"
```

4. **Analyze cluster with AI solutions**:
```bash
curl -X POST "https://your-domain.com/kubeconfig/analyze-k8s-with-solutions/1?namespace=production&resource_types=pods&resource_types=deployments" \
  -H "Authorization: Bearer $TOKEN"
```

5. **Execute kubectl command**:
```bash
curl -X POST "https://your-domain.com/kubeconfig/execute-kubectl-direct/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "kubectl get pods -n production"
  }'
```

### Python Client Example

```python
import requests
import json

class KubeConfigClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def onboard_cluster(self, cluster_data):
        """Onboard a new cluster"""
        response = requests.post(
            f"{self.base_url}/onboard-cluster",
            headers=self.headers,
            json=cluster_data
        )
        return response.json()
    
    def list_clusters(self):
        """Get all clusters"""
        response = requests.get(
            f"{self.base_url}/clusters",
            headers=self.headers
        )
        return response.json()
    
    def get_namespaces(self, cluster_id):
        """Get namespaces from a cluster"""
        response = requests.get(
            f"{self.base_url}/get-namespaces/{cluster_id}",
            headers=self.headers
        )
        return response.json()
    
    def analyze_cluster(self, cluster_id, namespace=None, resource_types=None):
        """Analyze cluster with AI solutions"""
        params = {}
        if namespace:
            params['namespace'] = namespace
        if resource_types:
            params['resource_types'] = resource_types
        
        response = requests.post(
            f"{self.base_url}/analyze-k8s-with-solutions/{cluster_id}",
            headers=self.headers,
            params=params
        )
        return response.json()
    
    def execute_kubectl(self, cluster_id, command):
        """Execute kubectl command"""
        response = requests.post(
            f"{self.base_url}/execute-kubectl-direct/{cluster_id}",
            headers=self.headers,
            json={'command': command}
        )
        return response.json()


