---
sidebar_position: 2
---

# Trigger Remediation API

The Trigger Remediation API initiates an automated remediation process for a detected issue within a Kubernetes cluster. By providing the issue identifier and the target cluster, this endpoint generates and optionally executes remediation steps to resolve the problem. It leverages AI-driven solutions to determine the best course of action, improving system reliability and reducing manual intervention.

**Endpoint:** `POST /remediate`

### Request

The request body must include the `issue_id` representing the specific problem to remediate and the `cluster_id` indicating the target Kubernetes cluster where the remediation should be applied.

Example request body:

```json
{
  "issue_id": "pod_crash_loop",
  "cluster_id": 1
}
```

### Response

The response indicates the status of the remediation process initiation. A typical successful response includes a status message and a description of the action taken or planned.

Example response body:

```json
{
  "status": "remediation_started",
  "action": "Restarted pod"
}
```
}
