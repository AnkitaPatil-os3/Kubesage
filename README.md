# KubeSage

KubeSage is a comprehensive platform for Kubernetes cluster analysis, troubleshooting, and management. It combines AI-powered analysis with intuitive interfaces to help users identify and resolve issues in their Kubernetes environments.

## Features

- **K8sGPT Integration**: Analyze Kubernetes clusters for potential issues and get AI-powered explanations
- **Multiple AI Backend Support**: Connect to various AI providers including OpenAI, and more
- **Kubeconfig Management**: Securely store and manage multiple Kubernetes configurations
- **Command Generation**: AI-assisted generation of kubectl commands based on natural language queries
- **Analysis History**: Save and review past cluster analyses
- **Multi-user Support**: Role-based access with regular and admin user capabilities
- **Chat Service**: Interactive chat interface for Kubernetes assistance

## Architecture

KubeSage is built with a microservices architecture:

- **Frontend**: Vue-based web interface
- **Backend Services**:
  - **User Service**: Authentication and user management
  - **K8sGPT Service**: Kubernetes cluster analysis
  - **Kubeconfig Service**: Management of Kubernetes configurations
  - **AI Agent Service**: LLM integration for command generation and analysis
  - **Chat Service**: Real-time chat functionality for Kubernetes assistance

## Prerequisites

### Core Requirements

- **Node.js and npm**: [https://nodejs.org/](https://nodejs.org/) (v16 or later recommended)
- **Python**: [https://www.python.org/downloads/](https://www.python.org/downloads/) (v3.9 or later)
- **Docker and Docker Compose**: [https://docs.docker.com/get-docker/](https://docs.docker.com/get-docker/)
- **Kubernetes Cluster**: Any Kubernetes distribution (for testing, [minikube](https://minikube.sigs.k8s.io/docs/start/) is recommended)

### Infrastructure Components

- **PostgreSQL**: [https://www.postgresql.org/download/](https://www.postgresql.org/download/) (v13 or later)
- **RabbitMQ**: [https://www.rabbitmq.com/download.html](https://www.rabbitmq.com/download.html)
- **Redis**: [https://redis.io/download/](https://redis.io/download/)

### Kubernetes Tools

- **kubectl**: [https://kubernetes.io/docs/tasks/tools/](https://kubernetes.io/docs/tasks/tools/)
- **Helm**: [https://helm.sh/docs/intro/install/](https://helm.sh/docs/intro/install/)
- **K8sGPT**: [https://k8sgpt.ai/](https://k8sgpt.ai/) - Install with:
  ```bash
  helm repo add k8sgpt https://charts.k8sgpt.ai/
  helm repo update
  helm install k8sgpt k8sgpt/k8sgpt-operator -n k8sgpt --create-namespace
  ```

## Development Setup

### Getting Started

1. Clone the repository
   ```bash
   git clone https://10.0.32.141/kubesage/kubesage-development.git
   cd kubesage-development
   ```

2. Set up environment variables
   ```bash
   # Copy example env files for each service
   cp backend/user_service/.env.example backend/user_service/.env
   cp backend/k8sgpt_service/.env.example backend/k8sgpt_service/.env
   cp backend/kubeconfig_service/.env.example backend/kubeconfig_service/.env
   cp backend/ai_service/.env.example backend/ai_service/.env
   cp frontend/.env.example frontend/.env
   
   # Edit the .env files with your configuration
   ```


3. Start the backend services
    ### AI Agent Service
    ```bash
    ### Ai Agent Service
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload 

    ### User Service
    uvicorn app.main:app --host 0.0.0.0 --port 8001 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload

    ### Kubeconfig Service
    uvicorn app.main:app --host 0.0.0.0 --port 8002 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload 

    ### K8sgpt Service
    uvicorn app.main:app --host 0.0.0.0 --port 8003 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload --app-dir backend/kubeconfig_service

    ### Chat Service
    uvicorn app.main:app --host 0.0.0.0 --port 8004 --ssl-keyfile=key.pem --ssl-certfile=cert.pem --reload --app-dir backend/ai_service 
    ```

    


5. Start the frontend
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. Access the web interface at https://your-server-ip:9980



## API Documentation

API documentation is available at:
- AI Service: https://your-server-ip:8000/docs
- user Service: https://your-server-ip:8001/docs
- K8sgpt Service: https://your-server-ip:8002/docs
- Kubeconfig Service: https://your-server-ip:8003/docs
- AI Agent Service: https://your-server-ip:8004/docs


## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

