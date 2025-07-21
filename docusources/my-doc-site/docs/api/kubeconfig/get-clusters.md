---
sidebar_position: 2
---

# Get Clusters API

The Get Clusters API retrieves a list of all Kubernetes clusters configured for the currently authenticated user. This endpoint provides detailed information about each cluster, including its unique identifier, name, server URL, context, provider, security settings, and other metadata. It is used to display available clusters for management, monitoring, or further operations within the system.

**Endpoint:** `GET /clusters`

### Request

This endpoint requires the user to be authenticated. No request body is needed as it is a GET request. The server uses the authentication token to identify the current user and fetch their configured clusters.

### Response

The response is a list of cluster objects configured for the authenticated user. Each object contains the cluster's unique identifier (`id`), the cluster's name (`name`), and the server URL (`server_url`) used to connect to the Kubernetes API.

```json
[
  {
    "id": 1,
    "name": "dev-cluster",
    "server_url": "https://10.0.0.1:6443"
  }
]
