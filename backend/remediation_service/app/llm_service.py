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
            
            logger.info(f"Sending request to LLM with model: {self.model}")
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            # Get the response content
            response_content = response.choices[0].message.content
            logger.info(f"LLM response content: {response_content[:200]}...")
            
            # Check if response is empty
            if not response_content or response_content.strip() == "":
                logger.error("LLM returned empty response")
                raise ValueError("Empty response from LLM")
            
            # Clean the response content to fix common JSON issues
            cleaned_content = self._clean_json_response(response_content)
            
            # Parse the response
            try:
                solution_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response: {response_content}")
                logger.error(f"Cleaned response: {cleaned_content}")
                raise ValueError(f"Invalid JSON response from LLM: {e}")
            
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

    def _clean_json_response(self, response_content: str) -> str:
        """Clean JSON response to fix common formatting issues"""
        try:
            # Fix common escape sequence issues
            cleaned = response_content
            
            # Fix invalid escape sequences
            cleaned = cleaned.replace('\\*', '*')  # Fix \* to *
            cleaned = cleaned.replace('\\"', '"')  # Fix \" to "
            cleaned = cleaned.replace('\\-', '-')  # Fix \- to -
            cleaned = cleaned.replace('\\[', '[')  # Fix \[ to [
            cleaned = cleaned.replace('\\]', ']')  # Fix \] to ]
            cleaned = cleaned.replace('\\{', '{')  # Fix \{ to {
            cleaned = cleaned.replace('\\}', '}')  # Fix \} to }
            
            # Fix double backslashes that might be needed
            cleaned = cleaned.replace('\\\\', '\\')
            
            # Fix common JSON syntax issues
            import re
            # Remove any trailing commas before closing braces/brackets
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            
            # Fix missing commas between array elements
            cleaned = re.sub(r'}\s*{', r'}, {', cleaned)
            
            # Fix missing commas between object properties
            cleaned = re.sub(r'"\s*"', r'", "', cleaned)
            
            # Fix quotes inside JSON strings - escape them properly
            # This is a more conservative approach to fix nested quotes
            lines = cleaned.split('\n')
            fixed_lines = []
            for line in lines:
                # If line contains command with nested quotes, fix them
                if '"command":' in line and line.count('"') > 4:
                    # Find the command value and escape internal quotes
                    import json
                    try:
                        # Try to extract and fix the command part
                        if '"command": "' in line:
                            start = line.find('"command": "') + 12
                            end = line.rfind('"')
                            if start < end:
                                command_part = line[start:end]
                                # Escape internal quotes
                                command_part = command_part.replace('"', '\\"')
                                line = line[:start] + command_part + line[end:]
                    except:
                        pass
                fixed_lines.append(line)
            
            cleaned = '\n'.join(fixed_lines)
            
            return cleaned
            
        except Exception as e:
            logger.warning(f"Error cleaning JSON response: {e}")
            return response_content
    
    def _get_system_prompt(self, executor_type: ExecutorType) -> str:
        """Get the system prompt for the LLM based on executor type"""
        base_prompt = """You are an expert Kubernetes Site Reliability Engineer (SRE) and incident response specialist. Your task is to analyze Kubernetes incidents and provide detailed, actionable remediation solutions for ANY type of Kubernetes incident.

You can handle ALL types of incidents including:
- Pod failures, crashes, restarts
- Deployment issues, scaling problems
- Service connectivity issues
- Resource constraints (CPU, memory, storage)
- Configuration errors
- Network issues
- Security incidents
- Performance problems
- Any other Kubernetes-related incidents

When given ANY Kubernetes incident, you should:
1. Identify the root cause of the incident
2. Provide a clear, step-by-step remediation solution
3. Include specific commands for the designated executor
4. Estimate the time needed to resolve the incident
5. Provide a confidence score for your solution
6. Consider the safety and impact of each remediation step

CRITICAL JSON FORMATTING RULES:
- Use simple double quotes for all strings
- Do NOT use single quotes inside command strings
- Use escaped quotes (\") for nested quotes in commands
- Ensure proper comma placement between all array elements and object properties
- Use simple command syntax without complex nested quotes

Your response must be a valid JSON object with this exact structure:
{
    "solution_summary": "Brief summary of the remediation approach",
    "detailed_solution": "Detailed explanation of the incident and remediation steps",
    "remediation_steps": [
        {
            "step_id": 1,
            "action_type": "DIAGNOSTIC",
            "description": "What this step does and why",
            "command": "kubectl get pods -n namespace",
            "expected_outcome": "What should happen after this step",
            "critical": false,
            "timeout_seconds": 300
        }
    ],
    "confidence_score": 0.85,
    "estimated_time_mins": 15,
    "additional_notes": "Any additional considerations",
    "commands": ["kubectl get pods", "kubectl describe pod"]
}

IMPORTANT: Always use simple command syntax. Avoid complex nested quotes. Use basic kubectl commands that are safe and effective."""

        executor_specific = {
            ExecutorType.KUBECTL: """
You are working with kubectl commands for direct Kubernetes cluster operations.
- Handle ALL types of Kubernetes incidents (pods, deployments, services, etc.)
- Use kubectl commands for all operations
- Include proper namespace specifications
- Use appropriate output formats (-o json, -o yaml when needed)
- Consider resource dependencies and order of operations
- Include verification steps after each major change
- Use safe commands like 'get', 'describe', 'logs' for diagnostics
- Be cautious with 'delete', 'scale', 'patch' operations
- Use simple command syntax without complex quotes
- Provide solutions for any incident type: failures, errors, warnings, scaling issues, etc.
""",
            ExecutorType.ARGOCD: """
You are working with ArgoCD for GitOps-based remediation of ANY incident type.
- Handle application deployment issues, sync problems, configuration errors
- Use argocd CLI commands for application management
- Focus on application sync, rollback, and configuration issues
- Consider Git repository state and application health
- Include application status checks and sync operations
""",
            ExecutorType.CROSSPLANE: """
You are working with Crossplane for infrastructure remediation of ANY incident type.
- Handle infrastructure provisioning issues, resource problems
- Use kubectl commands for Crossplane custom resources
- Focus on Compositions, CompositeResourceDefinitions, and Claims
- Handle Provider configurations and infrastructure provisioning issues
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