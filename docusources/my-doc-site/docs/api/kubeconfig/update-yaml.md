---
sidebar_position: 3
---

# Update YAML API

Update a Kubernetes resource by submitting new YAML.


The Update YAML API allows users to update an existing Kubernetes resource by submitting a new YAML configuration. The API validates and cleans the YAML to remove immutable or system-managed fields before applying the update. This operation triggers Kubernetes to reconcile the resource to the desired state defined in the YAML. It supports updating deployments, services, and pods by replacing their configurations with the provided YAML.

The request must include a valid YAML body representing the resource to update. The response indicates whether the update was successful.

This endpoint is essential for managing Kubernetes resources dynamically through declarative configurations.

**Endpoint:** `PUT /clusters/{id}/yaml/{namespace}/{resource_type}/{name}`


### Request

The request body should contain the full YAML definition of the Kubernetes resource to be updated. This YAML must include all necessary fields to define the resource, such as apiVersion, kind, metadata (including name and namespace), and spec. The API will clean the YAML to remove any immutable or system-generated fields before applying the update.

Example request body:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 2
  ...
```

### Response

The response is a JSON object indicating the success or failure of the update operation. A successful update returns:

```json
{
  "success": true
}
```
