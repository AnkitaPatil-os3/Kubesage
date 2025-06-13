import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from openai import OpenAI
from app.config import settings
from app.models import ExecutorType, Incident

logger = logging.getLogger(__name__)

class RemediationLLMService:
    """Service for generating Kubernetes incident remediation solutions using LLM"""
    
    def __init__(self):
        if not settings.LLM_ENABLED:
            raise ValueError("LLM functionality is disabled")
            
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
            
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
        
    def generate_remediation_solution(
        self,
        incident: Incident,
        executor_type: ExecutorType,
        cluster_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a remediation solution for a Kubernetes incident using LLM"""
        
        try:
            # Prepare the prompt
            system_prompt = self._get_system_prompt(executor_type)
            user_prompt = self._build_incident_prompt(incident, executor_type, cluster_context)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Lower temperature for more consistent remediation
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            solution_data = json.loads(response.choices[0].message.content)
            
            # Validate and structure the response
            return self._validate_remediation_response(solution_data, executor_type)
            
        except Exception as e:
            logger.error(f"Error generating remediation solution: {str(e)}")
            # Return a fallback solution structure
            return {
                "solution_summary": f"Error generating solution: {str(e)}",
                "detailed_solution": "An error occurred while generating the remediation solution. Please try again or contact support.",
                "remediation_steps": [],
                "confidence_score": 0.0,
                "estimated_time_mins": 30,
                "additional_notes": f"Error details: {str(e)}",
                "executor_type": executor_type.value,
                "commands": []
            }
    
    def _get_system_prompt(self, executor_type: ExecutorType) -> str:
        """Get the system prompt for the LLM based on executor type"""
        base_prompt = """You are an expert Kubernetes Site Reliability Engineer (SRE) and incident response specialist. Your task is to analyze Kubernetes incidents and provide detailed, actionable remediation solutions.

When given a Kubernetes incident, you should:
1. Identify the root cause of the incident
2. Provide a clear, step-by-step remediation solution
3. Include specific commands for the designated executor
4. Estimate the time needed to resolve the incident
5. Provide a confidence score for your solution
6. Consider the safety and impact of each remediation step

Your response must be a valid JSON object with the following structure:
{
    "solution_summary": "Brief summary of the remediation approach",
    "detailed_solution": "Detailed explanation of the incident and remediation steps",
    "remediation_steps": [
        {
            "step_id": 1,
            "action_type": "DIAGNOSTIC|REMEDIATION|VERIFICATION|ROLLBACK",
            "description": "What this step does and why",
            "command": "specific command to execute",
            "expected_outcome": "What should happen after this step",
            "critical": false,
            "timeout_seconds": 300
        }
    ],
    "confidence_score": 0.85,
    "estimated_time_mins": 15,
    "additional_notes": "Any additional considerations, warnings, or prerequisites",
    "commands": ["list", "of", "all", "commands", "to", "execute"]
}

Focus on practical, safe solutions. Always include diagnostic steps before making changes."""

        executor_specific = {
            ExecutorType.KUBECTL: """
You are specifically working with kubectl commands for direct Kubernetes cluster operations.
- Use kubectl commands for all operations
- Include proper namespace specifications
- Use appropriate output formats (-o json, -o yaml when needed)
- Consider resource dependencies and order of operations
- Include verification steps after each major change
- Use safe commands like 'get', 'describe', 'logs' for diagnostics
- Be cautious with 'delete', 'scale', 'patch' operations
""",
            ExecutorType.ARGOCD: """
You are specifically working with ArgoCD for GitOps-based remediation.
- Use argocd CLI commands for application management
- Focus on application sync, rollback, and configuration issues
- Consider Git repository state and application health
- Include application status checks and sync operations
- Handle ArgoCD-specific resources like Applications, Projects, Repositories
- Consider sync policies and automated sync behavior
""",
            ExecutorType.CROSSPLANE: """
You are specifically working with Crossplane for infrastructure remediation.
- Use kubectl commands for Crossplane custom resources
- Focus on Compositions, CompositeResourceDefinitions, and Claims
- Handle Provider configurations and infrastructure provisioning issues
- Consider infrastructure dependencies and provisioning order
- Include status checks for infrastructure resources
- Handle Crossplane-specific resource lifecycle and conditions
"""
        }
        
        return base_prompt + executor_specific.get(executor_type, "")
    
    def _build_incident_prompt(
        self,
        incident: Incident,
        executor_type: ExecutorType,
        cluster_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the user prompt with incident details"""
        
        prompt_parts = [
            f"Please analyze and provide a remediation solution for this Kubernetes incident:",
            f"",
            f"INCIDENT DETAILS:",
            f"- Incident ID: {incident.incident_id}",
            f"- Type: {incident.type.value}",
            f"- Reason: {incident.reason}",
            f"- Message: {incident.message}",
            f"- Namespace: {incident.metadata_namespace or 'N/A'}",
            f"- Involved Object: {incident.involved_object_kind}/{incident.involved_object_name}",
            f"- Source Component: {incident.source_component or 'N/A'}",
            f"- Reporting Component: {incident.reporting_component or 'N/A'}",
            f"- Count: {incident.count}",
            f"- First Timestamp: {incident.first_timestamp}",
            f"- Last Timestamp: {incident.last_timestamp}",
            f"",
            f"EXECUTOR TYPE: {executor_type.value}",
            f"",
        ]
        
        # Add labels if available
        if incident.involved_object_labels:
            labels = incident.get_labels_dict()
            if labels:
                prompt_parts.append(f"RESOURCE LABELS:")
                for key, value in labels.items():
                    prompt_parts.append(f"- {key}: {value}")
                prompt_parts.append("")
        
        # Add annotations if available
        if incident.involved_object_annotations:
            annotations = incident.get_annotations_dict()
            if annotations:
                prompt_parts.append(f"RESOURCE ANNOTATIONS:")
                for key, value in annotations.items():
                    prompt_parts.append(f"- {key}: {value}")
                prompt_parts.append("")
        
        # Add cluster context if provided
        if cluster_context:
            prompt_parts.append(f"CLUSTER CONTEXT:")
            prompt_parts.append(json.dumps(cluster_context, indent=2))
            prompt_parts.append("")
        
        # Add resolution history if this incident has been attempted before
        if incident.resolution_attempts > 0:
            prompt_parts.append(f"RESOLUTION HISTORY:")
            prompt_parts.append(f"- Previous attempts: {incident.resolution_attempts}")
            prompt_parts.append(f"- Last attempt: {incident.last_resolution_attempt}")
            prompt_parts.append(f"- Currently resolved: {incident.is_resolved}")
            prompt_parts.append("")
        
        prompt_parts.append("Please provide a comprehensive remediation solution using the specified executor type.")
        
        return "\n".join(prompt_parts)
    
    def _validate_remediation_response(self, solution_data: Dict[str, Any], executor_type: ExecutorType) -> Dict[str, Any]:
        """Validate and clean the LLM response"""
        
        # Ensure required fields exist
        required_fields = ["solution_summary", "detailed_solution", "remediation_steps"]
        for field in required_fields:
            if field not in solution_data:
                solution_data[field] = ""
        
        # Validate remediation steps
        if not isinstance(solution_data.get("remediation_steps"), list):
            solution_data["remediation_steps"] = []
        
        # Validate each remediation step
        validated_steps = []
        commands = []
        
        for step in solution_data.get("remediation_steps", []):
            if isinstance(step, dict):
                validated_step = {
                    "step_id": step.get("step_id", len(validated_steps) + 1),
                    "action_type": step.get("action_type", "DIAGNOSTIC"),
                    "description": step.get("description", ""),
                    "command": step.get("command", ""),
                    "expected_outcome": step.get("expected_outcome", ""),
                    "critical": step.get("critical", False),
                    "timeout_seconds": step.get("timeout_seconds", 300)
                }
                validated_steps.append(validated_step)
                
                # Collect commands
                if validated_step["command"]:
                    commands.append(validated_step["command"])
        
        solution_data["remediation_steps"] = validated_steps
        solution_data["commands"] = commands
        
        # Ensure confidence score is within valid range
        confidence = solution_data.get("confidence_score", 0.5)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            solution_data["confidence_score"] = 0.5
        
        # Ensure estimated time is positive integer
        estimated_time = solution_data.get("estimated_time_mins", 30)
        if not isinstance(estimated_time, int) or estimated_time < 0:
            solution_data["estimated_time_mins"] = 30
        
        # Add executor type
        solution_data["executor_type"] = executor_type.value
        
        # Ensure additional notes exist
        if "additional_notes" not in solution_data:
            solution_data["additional_notes"] = ""
            
        return solution_data