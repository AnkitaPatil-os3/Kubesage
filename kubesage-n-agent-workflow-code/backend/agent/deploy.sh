#!/bin/bash

set -e

echo "🚀 Deploying KubeSage Agent to Kubernetes Cluster"

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo "❌ kubectl is not installed or not in PATH"
        exit 1
    fi
    echo "✅ kubectl is available"
}

# Function to check cluster connection
check_cluster_connection() {
    if ! kubectl cluster-info &> /dev/null; then
        echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig"
        exit 1
    fi
    echo "✅ Connected to Kubernetes cluster"
}

# Function to create namespace if it doesn't exist
create_namespace() {
    local namespace=${1:-default}
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        echo "📁 Creating namespace: $namespace"
        kubectl create namespace "$namespace"
    else
        echo "✅ Namespace '$namespace' already exists"
    fi
}

# Function to build Docker image
build_image() {
    echo "🔨 Building Docker image..."
    docker build -t kubesage-agent:latest .
    echo "✅ Docker image built successfully"
}

# Function to deploy manifests
deploy_manifests() {
    echo "📦 Applying Kubernetes manifests..."
    
    # Apply in order
    kubectl apply -f rbac.yaml
    echo "✅ RBAC configuration applied"
    
    kubectl apply -f configmap.yaml
    echo "✅ ConfigMap applied"
    
    kubectl apply -f secret.yaml
    echo "✅ Secret applied"
    
    kubectl apply -f deployment.yaml
    echo "✅ Deployment applied"
    
    kubectl apply -f service.yaml
    echo "✅ Service applied"
}

# Function to wait for deployment
wait_for_deployment() {
    echo "⏳ Waiting for deployment to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/kubesage-agent
    echo "✅ Deployment is ready"
}

# Function to show status
show_status() {
    echo "📊 Deployment Status:"
    kubectl get pods -l app=kubesage-agent
    kubectl get svc kubesage-agent-service
    
    echo ""
    echo "📋 Agent Logs (last 20 lines):"
    kubectl logs -l app=kubesage-agent --tail=20 || echo "No logs available yet"
}

# Main execution
main() {
    echo "Starting KubeSage Agent deployment..."
    
    check_kubectl
    check_cluster_connection
    
    # Build image if Docker is available
    if command -v docker &> /dev/null; then
        build_image
    else
        echo "⚠️  Docker not available, assuming image is already built"
    fi
    
    deploy_manifests
    wait_for_deployment
    show_status
    
    echo ""
    echo "🎉 KubeSage Agent deployed successfully!"
    echo ""
    echo "🔍 To check logs: kubectl logs -l app=kubesage-agent -f"
    echo "🔍 To check status: kubectl get pods -l app=kubesage-agent"
    echo "🔍 To delete: kubectl delete -f ."
}

# Run main function
main "$@"