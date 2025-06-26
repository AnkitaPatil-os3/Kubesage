import asyncio
from typing import List, Dict, Any, Optional
from app.config import settings
from app.logger import logger
import json
import subprocess
import time
from functools import lru_cache
from kubernetes import client, config
import os

from langchain_openai import ChatOpenAI
# Service version
KUBERNETES_SERVICE_VERSION = "2.0.0-simple"


# Add these constants and functions to your langchain_service.py file

KUBERNETES_SERVICE_VERSION = "2.0.0-simplified"

def initialize_kubernetes() -> Dict[str, Any]:
    """Initialize Kubernetes client and return status."""
    global k8s_loaded, v1, apps_v1
    
    try:
        kubeconfig_path = settings.get_kubeconfig_path()
        
        # Try to load kubeconfig
        if os.path.exists(kubeconfig_path):
            config.load_kube_config(config_file=kubeconfig_path)
            logger.info(f"✅ Loaded kubeconfig from {kubeconfig_path}")
        else:
            # Try in-cluster config
            config.load_incluster_config()
            logger.info("✅ Loaded in-cluster kubeconfig")
        
        # Initialize clients
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        
        # Test connection
        version_api = client.VersionApi()
        version_info = version_api.get_code()
        
        k8s_loaded = True
        
        return {
            "success": True,
            "cluster_version": version_info.git_version,
            "kubeconfig_path": kubeconfig_path
        }
        
    except Exception as e:
        logger.error(f"❌ Kubernetes initialization failed: {e}")
        k8s_loaded = False
        return {
            "success": False,
            "error": str(e)
        }

# Load Kubernetes config
def load_k8s_config():
    """Load Kubernetes configuration."""
    try:
        # Try in-cluster config first
        config.load_incluster_config()
        logger.info("✅ Using in-cluster Kubernetes configuration")
        return True
    except config.ConfigException:
        try:
            # Use custom kubeconfig path
            kubeconfig_path = settings.get_kubeconfig_path()
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                config.load_kube_config(config_file=kubeconfig_path)
                logger.info(f"✅ Loaded Kubernetes config from {kubeconfig_path}")
                return True
            else:
                config.load_kube_config()  # Default location
                logger.info("✅ Loaded Kubernetes config from default location")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to load Kubernetes config: {str(e)}")
            return False

# Initialize K8s clients
k8s_loaded = load_k8s_config()
if k8s_loaded:
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    batch_v1 = client.BatchV1Api()
    networking_v1 = client.NetworkingV1Api()
else:
    v1 = apps_v1 = batch_v1 = networking_v1 = None

def collect_all_k8s_errors() -> Dict[str, Any]:
    """Collect all errors from all namespaces and all K8s resources."""
    if not k8s_loaded:
        return {"error": "Kubernetes client not available"}
    
    logger.info("🔍 Collecting all K8s errors from all namespaces...")
    errors = {
        "events": [],
        "pods": [],
        "deployments": [],
        "services": [],
        "jobs": [],
        "ingresses": [],
        "nodes": [],
        "summary": {
            "total_errors": 0,
            "namespaces_checked": 0,
            "collection_time": time.time()
        }
    }
    
    
    try:
        # Get all namespaces
        namespaces = v1.list_namespace()
        namespace_names = [ns.metadata.name for ns in namespaces.items]
        errors["summary"]["namespaces_checked"] = len(namespace_names)
        
        logger.info(f"📋 Checking {len(namespace_names)} namespaces for errors...")
        
        # Collect events (errors and warnings)
        try:
            all_events = v1.list_event_for_all_namespaces()
            for event in all_events.items:
                if event.type in ['Warning', 'Error'] or 'failed' in event.reason.lower():
                    errors["events"].append({
                        "namespace": event.namespace,
                        "name": event.involved_object.name,
                        "kind": event.involved_object.kind,
                        "reason": event.reason,
                        "message": event.message,
                        "type": event.type,
                        "last_timestamp": str(event.last_timestamp) if event.last_timestamp else None,
                        "count": event.count or 1
                    })
            logger.info(f"📅 Found {len(errors['events'])} error/warning events")
        except Exception as e:
            logger.error(f"❌ Error collecting events: {str(e)}")
        
        # Collect pod errors
        try:
            all_pods = v1.list_pod_for_all_namespaces()
            for pod in all_pods.items:
                pod_errors = []
                
                # Check pod phase
                if pod.status.phase in ['Failed', 'Pending']:
                    pod_errors.append(f"Pod in {pod.status.phase} state")
                
                # Check container statuses
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        if not container.ready:
                            if container.state.waiting:
                                pod_errors.append(f"Container {container.name} waiting: {container.state.waiting.reason} - {container.state.waiting.message}")
                            elif container.state.terminated:
                                if container.state.terminated.exit_code != 0:
                                    pod_errors.append(f"Container {container.name} terminated with exit code {container.state.terminated.exit_code}: {container.state.terminated.reason}")
                        
                        # Check restart count
                        if container.restart_count > 0:
                            pod_errors.append(f"Container {container.name} has restarted {container.restart_count} times")
                
                if pod_errors:
                    errors["pods"].append({
                        "namespace": pod.metadata.namespace,
                        "name": pod.metadata.name,
                        "phase": pod.status.phase,
                        "errors": pod_errors,
                        "node": pod.spec.node_name
                    })
            
            logger.info(f"🐳 Found {len(errors['pods'])} pods with errors")
        except Exception as e:
            logger.error(f"❌ Error collecting pod errors: {str(e)}")
        
        # Collect deployment errors
        try:
            all_deployments = apps_v1.list_deployment_for_all_namespaces()
            for deployment in all_deployments.items:
                deployment_errors = []
                
                # Check replica status
                desired = deployment.spec.replicas or 0
                available = deployment.status.available_replicas or 0
                ready = deployment.status.ready_replicas or 0
                
                if available < desired:
                    deployment_errors.append(f"Only {available}/{desired} replicas available")
                
                if ready < desired:
                    deployment_errors.append(f"Only {ready}/{desired} replicas ready")
                
                # Check conditions
                if deployment.status.conditions:
                    for condition in deployment.status.conditions:
                        if condition.status == 'False' and condition.type in ['Available', 'Progressing']:
                            deployment_errors.append(f"{condition.type}: {condition.reason} - {condition.message}")
                
                if deployment_errors:
                    errors["deployments"].append({
                        "namespace": deployment.metadata.namespace,
                        "name": deployment.metadata.name,
                        "desired_replicas": desired,
                        "available_replicas": available,
                        "ready_replicas": ready,
                        "errors": deployment_errors
                    })
            
            logger.info(f"🚀 Found {len(errors['deployments'])} deployments with errors")
        except Exception as e:
            logger.error(f"❌ Error collecting deployment errors: {str(e)}")
        
        # Collect service errors (services without endpoints)
        try:
            all_services = v1.list_service_for_all_namespaces()
            for service in all_services.items:
                if service.spec.type != 'ExternalName':  # Skip ExternalName services
                    try:
                        endpoints = v1.read_namespaced_endpoints(
                            name=service.metadata.name,
                            namespace=service.metadata.namespace
                        )
                        
                        # Check if service has no endpoints
                        has_endpoints = False
                        if endpoints.subsets:
                            for subset in endpoints.subsets:
                                if subset.addresses:
                                    has_endpoints = True
                                    break
                        
                        if not has_endpoints:
                            errors["services"].append({
                                "namespace": service.metadata.namespace,
                                "name": service.metadata.name,
                                "type": service.spec.type,
                                "error": "Service has no endpoints"
                            })
                    except client.ApiException as e:
                        if e.status == 404:
                            errors["services"].append({
                                "namespace": service.metadata.namespace,
                                "name": service.metadata.name,
                                "type": service.spec.type,
                                "error": "Endpoints not found"
                            })
            
            logger.info(f"🔗 Found {len(errors['services'])} services with errors")
        except Exception as e:
            logger.error(f"❌ Error collecting service errors: {str(e)}")
        
        # Collect failed jobs
        try:
            all_jobs = batch_v1.list_job_for_all_namespaces()
            for job in all_jobs.items:
                if job.status.failed and job.status.failed > 0:
                    errors["jobs"].append({
                        "namespace": job.metadata.namespace,
                        "name": job.metadata.name,
                        "failed": job.status.failed,
                        "succeeded": job.status.succeeded or 0,
                        "active": job.status.active or 0
                    })
            
            logger.info(f"⚙️ Found {len(errors['jobs'])} failed jobs")
        except Exception as e:
            logger.error(f"❌ Error collecting job errors: {str(e)}")
        
        # Collect node errors
        try:
            all_nodes = v1.list_node()
            for node in all_nodes.items:
                node_errors = []
                
                if node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == 'Ready' and condition.status != 'True':
                            node_errors.append(f"Node not ready: {condition.reason} - {condition.message}")
                        elif condition.type in ['MemoryPressure', 'DiskPressure', 'PIDPressure'] and condition.status == 'True':
                            node_errors.append(f"{condition.type}: {condition.message}")
                
                if node_errors:
                    errors["nodes"].append({
                        "name": node.metadata.name,
                        "errors": node_errors
                    })
            
            logger.info(f"🖥️ Found {len(errors['nodes'])} nodes with errors")
        except Exception as e:
            logger.error(f"❌ Error collecting node errors: {str(e)}")
        
        # Calculate total errors
        total_errors = (
            len(errors["events"]) + len(errors["pods"]) + len(errors["deployments"]) +
            len(errors["services"]) + len(errors["jobs"]) + len(errors["nodes"])
        )
        errors["summary"]["total_errors"] = total_errors
        
        logger.info(f"✅ Collected {total_errors} total errors from {len(namespace_names)} namespaces")
        return errors
        
    except Exception as e:
        logger.error(f"💥 Critical error collecting K8s errors: {str(e)}")
        return {"error": f"Failed to collect K8s errors: {str(e)}"}

def execute_kubectl_command(command: str) -> str:
    """Execute kubectl commands with full access."""
    try:
        logger.info(f"🚀 Executing kubectl command: {command}")
        
        if not command or not isinstance(command, str):
            return "Error: No command provided"
        
        command = command.strip()
        
        # Parse command arguments
        if command.startswith("kubectl "):
            args = command[8:].strip().split()
        else:
            args = command.split()
        
        if not args:
            return "Error: No command arguments provided"
        
        # Build full kubectl command
        cmd = ["kubectl"] + args
        
        # Set environment for kubeconfig
        env = os.environ.copy()
        kubeconfig_path = settings.get_kubeconfig_path()
        if kubeconfig_path:
            env["KUBECONFIG"] = kubeconfig_path
        
        logger.info(f"🔧 Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.KUBECTL_TIMEOUT,
                check=False,
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown error"
                logger.error(f"❌ kubectl command failed (exit {result.returncode}): {error_msg}")
                return f"kubectl error (exit code {result.returncode}): {error_msg}"
            
            output = result.stdout.strip()
            if not output:
                return "✅ Command executed successfully (no output)"
            
            # Limit output size for very large responses
            if len(output) > 20000:
                output = output[:20000] + "\n... (output truncated due to length)"
            
            logger.info(f"✅ kubectl command successful, output length: {len(output)}")
            return output
            
        except subprocess.TimeoutExpired:
            logger.error("⏰ kubectl command timed out")
            return f"Error: kubectl command timed out after {settings.KUBECTL_TIMEOUT} seconds"
        except FileNotFoundError:
            logger.error("❌ kubectl not found")
            return "Error: kubectl command not found. Please ensure kubectl is installed and in PATH"
        except Exception as e:
            logger.error(f"❌ Unexpected error executing kubectl: {str(e)}")
            return f"Error executing kubectl: {str(e)}"
            
    except Exception as e:
        logger.error(f"💥 Critical error in execute_kubectl_command: {str(e)}")
        return f"Critical error: {str(e)}"

@lru_cache(maxsize=10)
def get_llm():
    """Get LLM instance based on configuration."""
    llm_config = settings.get_llm_config()
    
    return ChatOpenAI(
        model=llm_config["model"],
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        temperature=0.4,
        max_retries=3
    )


async def process_with_llm(
    user_message: str,
    k8s_errors: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Process user message with LLM, including K8s errors context."""
    try:
        logger.info(f"🤖 Processing message with LLM: {user_message[:100]}...")
        
        # Build context for LLM
        context_parts = []
        
        # Add system prompt
        system_prompt = """You are KubeSage, an expert Kubernetes troubleshooting assistant. You help users diagnose and fix Kubernetes cluster issues.

CAPABILITIES:
- Analyze Kubernetes errors and provide solutions
- Generate kubectl commands for troubleshooting
- Explain Kubernetes concepts and best practices
- Provide step-by-step remediation guides

RESPONSE FORMAT:
- Use clear, structured markdown
- Include kubectl commands in code blocks
- Provide explanations for your recommendations
- Prioritize critical issues first
- Be concise but thorough"""

        context_parts.append(system_prompt)
        
        # Add conversation history if available
        if conversation_history:
            context_parts.append("\n## Previous Conversation:")
            for msg in conversation_history[-6:]:  # Last 6 messages for context
                role = "User" if msg["role"] == "user" else "Assistant"
                context_parts.append(f"**{role}:** {msg['content'][:500]}...")
        
        # Add K8s errors context if available
        if k8s_errors and not k8s_errors.get("error"):
            context_parts.append("\n## Current Cluster Status:")
            
            summary = k8s_errors.get("summary", {})
            total_errors = summary.get("total_errors", 0)
            namespaces_checked = summary.get("namespaces_checked", 0)
            
            context_parts.append(f"**Cluster Overview:** {total_errors} issues found across {namespaces_checked} namespaces")
            
            # Add critical errors
            if k8s_errors.get("events"):
                critical_events = [e for e in k8s_errors["events"] if e.get("type") == "Error"][:5]
                if critical_events:
                    context_parts.append("\n**Critical Events:**")
                    for event in critical_events:
                        context_parts.append(f"- {event['namespace']}/{event['name']} ({event['kind']}): {event['reason']} - {event['message']}")
            
            # Add pod errors
            if k8s_errors.get("pods"):
                context_parts.append(f"\n**Pod Issues:** {len(k8s_errors['pods'])} pods with problems")
                for pod in k8s_errors["pods"][:3]:  # Top 3 pod issues
                    context_parts.append(f"- {pod['namespace']}/{pod['name']}: {', '.join(pod['errors'])}")
            
            # Add deployment errors
            if k8s_errors.get("deployments"):
                context_parts.append(f"\n**Deployment Issues:** {len(k8s_errors['deployments'])} deployments with problems")
                for deploy in k8s_errors["deployments"][:3]:  # Top 3 deployment issues
                    context_parts.append(f"- {deploy['namespace']}/{deploy['name']}: {', '.join(deploy['errors'])}")
            
            # Add node errors
            if k8s_errors.get("nodes"):
                context_parts.append(f"\n**Node Issues:** {len(k8s_errors['nodes'])} nodes with problems")
                for node in k8s_errors["nodes"]:
                    context_parts.append(f"- {node['name']}: {', '.join(node['errors'])}")
        
        # Add user message
        context_parts.append(f"\n## User Question:\n{user_message}")
        
        # Combine all context
        full_context = "\n".join(context_parts)
        
        # Limit context size
        if len(full_context) > 15000:
            full_context = full_context[:15000] + "\n... (context truncated)"
        
        logger.info(f"📝 Built context with {len(full_context)} characters")
        
        # Get LLM response
        llm = get_llm()
        start_time = time.time()
        
        response = await llm.ainvoke(full_context)
        execution_time = time.time() - start_time
        
        assistant_message = response.content.strip()
        
        logger.info(f"✅ LLM response generated in {execution_time:.2f}s, length: {len(assistant_message)}")
        
        return {
            "success": True,
            "response": assistant_message,
            "execution_time": execution_time,
            "context_length": len(full_context),
            "errors_included": bool(k8s_errors and not k8s_errors.get("error"))
        }
        
    except Exception as e:
        logger.error(f"💥 Error processing with LLM: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to process with LLM: {str(e)}",
            "response": f"❌ **Error:** I encountered an issue processing your request: {str(e)}\n\n💡 **Please try again** or contact support if the issue persists."
        }

def perform_cluster_health_check() -> Dict[str, Any]:
    """Perform comprehensive cluster health check."""
    health_info = {
        "kubernetes_client": k8s_loaded,
        "kubectl_available": False,
        "cluster_accessible": False,
        "cluster_version": None,
        "node_count": 0,
        "namespace_count": 0,
        "error_messages": []
    }
    
    try:
        # Check kubectl availability
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client=true"],
                capture_output=True,
                text=True,
                timeout=10
            )
            health_info["kubectl_available"] = result.returncode == 0
        except Exception as e:
            health_info["error_messages"].append(f"kubectl check failed: {str(e)}")
        
        # Check cluster accessibility
        if k8s_loaded:
            try:
                # Get cluster version
                version_api = client.VersionApi()
                version_info = version_api.get_code()
                health_info["cluster_version"] = version_info.git_version
                health_info["cluster_accessible"] = True
                
                # Get node count
                nodes = v1.list_node()
                health_info["node_count"] = len(nodes.items)
                
                # Get namespace count
                namespaces = v1.list_namespace()
                health_info["namespace_count"] = len(namespaces.items)
                
                logger.info(f"✅ Cluster health check: {health_info['node_count']} nodes, {health_info['namespace_count']} namespaces")
                
            except Exception as e:
                health_info["error_messages"].append(f"Cluster access failed: {str(e)}")
                logger.error(f"❌ Cluster access failed: {str(e)}")
        else:
            health_info["error_messages"].append("Kubernetes client not loaded")
    
    except Exception as e:
        health_info["error_messages"].append(f"Health check failed: {str(e)}")
        logger.error(f"💥 Health check failed: {str(e)}")
    
    return health_info

def get_cluster_summary() -> Dict[str, Any]:
    """Get a quick cluster summary."""
    if not k8s_loaded:
        return {"error": "Kubernetes client not available"}
    
    try:
        summary = {
            "nodes": 0,
            "namespaces": 0,
            "pods": {"total": 0, "running": 0, "pending": 0, "failed": 0},
            "deployments": {"total": 0, "ready": 0},
            "services": 0,
            "timestamp": time.time()
        }
        
        # Count nodes
        nodes = v1.list_node()
        summary["nodes"] = len(nodes.items)
        
        # Count namespaces
        namespaces = v1.list_namespace()
        summary["namespaces"] = len(namespaces.items)
        
        # Count pods by status
        pods = v1.list_pod_for_all_namespaces()
        summary["pods"]["total"] = len(pods.items)
        for pod in pods.items:
            phase = pod.status.phase.lower()
            if phase == "running":
                summary["pods"]["running"] += 1
            elif phase == "pending":
                summary["pods"]["pending"] += 1
            elif phase == "failed":
                summary["pods"]["failed"] += 1
        
        # Count deployments
        deployments = apps_v1.list_deployment_for_all_namespaces()
        summary["deployments"]["total"] = len(deployments.items)
        for deployment in deployments.items:
            desired = deployment.spec.replicas or 0
            ready = deployment.status.ready_replicas or 0
            if ready == desired:
                summary["deployments"]["ready"] += 1
        
        # Count services
        services = v1.list_service_for_all_namespaces()
        summary["services"] = len(services.items)
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error getting cluster summary: {str(e)}")
        return {"error": f"Failed to get cluster summary: {str(e)}"}

# Memory management for conversation history
def create_memory_from_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Create conversation memory from message history."""
    try:
        memory = []
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role and content:
                memory.append({"role": role, "content": content})
        
        return memory
    except Exception as e:
        logger.error(f"❌ Error creating memory from messages: {str(e)}")
        return []

def get_memory_summary(memory: List[Dict[str, str]]) -> Dict[str, Any]:
    """Get a summary of the memory state for debugging."""
    try:
        return {
            "message_count": len(memory),
            "user_messages": len([m for m in memory if m.get("role") == "user"]),
            "assistant_messages": len([m for m in memory if m.get("role") == "assistant"]),
            "total_characters": sum(len(m.get("content", "")) for m in memory)
        }
    except Exception as e:
        logger.error(f"❌ Error getting memory summary: {str(e)}")
        return {"error": str(e)}
