# K8sGPT CRD API

A FastAPI application for managing K8sGPT Custom Resource Definitions (CRDs) in Kubernetes clusters.

## Features

- Full CRUD operations for K8sGPT and Result CRDs
- Secure kubeconfig authentication
- Watch endpoints for real-time changes
- Comprehensive input validation
- OpenAPI documentation
- Production-ready with Docker support

## Requirements

- Python 3.11+
- Kubernetes cluster with K8sGPT CRDs installed
- kubectl configured with cluster access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/k8sgpt-crd-api.git
cd k8sgpt-crd-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development
```bash
uvicorn main:app --reload
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker build -t k8sgpt-crd-api .
docker run -p 8000:8000 k8sgpt-crd-api
```

## API Documentation

After starting the application, access the interactive docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Usage

### Create a K8sGPT CRD
```bash
curl -X POST "http://localhost:8000/k8sgpt/default" \
  -H "Content-Type: application/json" \
  -d '{
    "apiVersion": "core.k8sgpt.ai/v1alpha1",
    "kind": "K8sGPT",
    "metadata": {"name": "my-k8sgpt"},
    "spec": {
      "ai": {
        "backend": "openai",
        "model": "gpt-4"
      }
    }
  }'
```

### List Results
```bash
curl "http://localhost:8000/results?namespace=default"
```

### Watch for Changes
```bash
curl "http://localhost:8000/k8sgpt/watch"
```

## Testing

Run tests with:
```bash
pytest tests/
```

## Deployment Considerations

- Ensure proper RBAC permissions are configured
- Use HTTPS in production
- Consider adding authentication middleware
- Monitor resource usage when watching many namespaces

## License

MIT