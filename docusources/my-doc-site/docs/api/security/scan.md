---
sidebar_position: 2
---

# Security Scan API

The Security Scan API initiates a comprehensive security scan on the specified Kubernetes cluster. It analyzes the cluster for vulnerabilities, misconfigurations, and compliance issues to help maintain a secure environment. The scan results include a unique scan identifier, the current status of the scan, and the number of issues detected.

**Endpoint:** `POST /scan`

### Request

The request body must include the `cluster_id` of the Kubernetes cluster to be scanned.

Example request body:

```json
{
  "cluster_id": 1
}
```

### Response

The response provides details about the initiated scan, including a unique `scan_id` to track the scan, the current `status` of the scan (e.g., "completed", "in_progress"), and the total number of `issues_found` during the scan.

Example response body:

```json
{
  "scan_id": "abc123",
  "status": "completed",
  "issues_found": 3
}
```
}
