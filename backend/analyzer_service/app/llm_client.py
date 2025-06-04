import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class SolutionStep(BaseModel):
    step_id: int = Field(description="Sequential ID of the step")
    action_type: str = Field(description="Type of action (e.g., KUBECTL_APPLY, KUBECTL_DELETE, KUBECTL_GET_LOGS, etc.)")
    description: str = Field(description="Detailed description of what this step does and why")
    target_resource: Dict[str, Any] = Field(description="Target Kubernetes resource details")
    command_or_payload: Dict[str, Any] = Field(description="Command or payload for the action")
    expected_outcome: str = Field(description="What is expected after this step is executed successfully")

class IncidentSolution(BaseModel):
    solution_id: str = Field(description="Unique identifier for the solution")
    incident_id: str = Field(description="ID of the incident this solution addresses")
    incident_type: str = Field(description="Type of the incident (Normal/Warning)")
    summary: str = Field(description="Concise summary of the solution strategy")
    analysis: str = Field(description="Detailed analysis of the incident")
    steps: List[SolutionStep] = Field(description="Detailed, ordered steps for resolution")
    confidence_score: Optional[float] = Field(None, description="LLM's confidence in this solution (0.0 to 1.0)")
    estimated_time_to_resolve_mins: Optional[int] = Field(None, description="Estimated time in minutes to resolve")
    severity_level: str = Field(description="Assessed severity level of the incident")
    recommendations: List[str] = Field(description="Additional recommendations for prevention")

class KubernetesLLMClient:
    """
    LLM client for analyzing Kubernetes incidents and providing structured solutions
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.base_url = settings.OPENAI_BASE_URL
        self.timeout = settings.LLM_TIMEOUT
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in configuration.")
        
        # Initialize OpenAI client
        client_params = {
            "api_key": self.api_key,
            "timeout": self.timeout
        }
        
        if self.base_url:
            client_params["base_url"] = self.base_url
            
        self.client = OpenAI(**client_params)
        
        logger.info(f"Initialized LLM client with model: {self.model}")

    def _create_system_prompt(self) -> str:
        """Create the system prompt for incident analysis"""
        return """You are an expert Kubernetes administrator and AI assistant specialized in analyzing Kubernetes incidents and providing actionable solutions.

Your task is to analyze Kubernetes incident data and generate a comprehensive solution in JSON format.

The solution should be structured according to this exact JSON schema:

{
  "solution_id": "string (Unique identifier, e.g., SOL-KUBE-1234)",
  "incident_id": "string (ID of the incident being analyzed)",
  "incident_type": "string (Type: Normal or Warning)",
  "summary": "string (Concise summary of the solution strategy)",
  "analysis": "string (Detailed analysis of what happened and why)",
  "steps": [
    {
      "step_id": "integer (Sequential step number)",
      "action_type": "string (KUBECTL_GET_LOGS, KUBECTL_DESCRIBE, KUBECTL_SCALE, KUBECTL_APPLY, CHECK_RESOURCE_QUOTAS, MONITOR, VERIFY, etc.)",
      "description": "string (Detailed description of the action and its purpose)",
      "target_resource": {
        "kind": "string (Pod, Deployment, Service, etc.)",
        "name": "string (Resource name)",
        "namespace": "string (Kubernetes namespace)"
      },
      "command_or_payload": {
        "command": "string (kubectl command without 'kubectl' prefix)",
        "parameters": "object (additional parameters if needed)"
      },
      "expected_outcome": "string (Expected result after executing this step)"
    }
  ],
  "confidence_score": "float (0.0 to 1.0)",
  "estimated_time_to_resolve_mins": "integer (estimated minutes)",
  "severity_level": "string (LOW, MEDIUM, HIGH, CRITICAL)",
  "recommendations": ["string (prevention recommendations)"]
}

IMPORTANT GUIDELINES:
1. For Normal events: Focus on monitoring, verification, and optimization
2. For Warning events: Provide diagnostic and remediation steps
3. Use appropriate kubectl commands without the 'kubectl' prefix
4. Consider resource relationships (Deployments manage ReplicaSets manage Pods)
5. Provide practical, safe, and actionable steps
6. Include monitoring and verification steps
7. Assess severity based on incident impact and urgency

Respond ONLY with valid JSON matching the schema above."""

    def _create_user_prompt(self, incident_data: Dict[str, Any]) -> str:
        """Create the user prompt with incident data"""
        return f"""Please analyze the following Kubernetes incident and provide a comprehensive solution:

INCIDENT DATA:
- ID: {incident_data.get('id', 'N/A')}
- Type: {incident_data.get('type', 'N/A')}
- Reason: {incident_data.get('reason', 'N/A')}
- Message: {incident_data.get('message', 'N/A')}
- Namespace: {incident_data.get('metadata_namespace', 'N/A')}
- Object Kind: {incident_data.get('involved_object_kind', 'N/A')}
- Object Name: {incident_data.get('involved_object_name', 'N/A')}
- Source Component: {incident_data.get('source_component', 'N/A')}
- Source Host: {incident_data.get('source_host', 'N/A')}
- Count: {incident_data.get('count', 'N/A')}
- Creation Time: {incident_data.get('metadata_creation_timestamp', 'N/A')}
- Labels: {incident_data.get('involved_object_labels', {})}
- Annotations: {incident_data.get('involved_object_annotations', {})}

Generate a comprehensive solution following the specified JSON format."""

    def analyze_incident_sync(self, incident_data: Dict[str, Any]) -> IncidentSolution:
        """
        Synchronous method to analyze a Kubernetes incident and generate a structured solution
        
        Args:
            incident_data: Dictionary containing incident information
            
        Returns:
            IncidentSolution: Structured solution for the incident
            
        Raises:
            Exception: If analysis fails
        """
        try:
            incident_id = incident_data.get('id', 'unknown')
            logger.info(f"Starting LLM analysis for incident: {incident_id}")
            
            # Prepare messages
            messages = [
                {"role": "system", "content": self._create_system_prompt()},
                {"role": "user", "content": self._create_user_prompt(incident_data)}
            ]
            
            # Call LLM with increased timeout and retry logic
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,  # Low temperature for consistent, focused responses
                    max_tokens=2000,
                    timeout=60,  # Increased timeout to 60 seconds
                    response_format={"type": "json_object"}  # Ensure JSON response
                )
            except Exception as api_error:
                logger.error(f"LLM API call failed for incident {incident_id}: {str(api_error)}")
                # Return a fallback solution if LLM fails
                return self._create_fallback_solution(incident_data)
            
            # Extract and parse response
            response_content = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {response_content}")
            
            # Parse JSON response
            try:
                solution_dict = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                return self._create_fallback_solution(incident_data)
            
            # Validate and create IncidentSolution object
            try:
                solution = IncidentSolution.model_validate(solution_dict)
                logger.info(f"Successfully generated solution for incident: {incident_id}")
                
                # Print solution to terminal
                self._print_solution_to_terminal(solution)
                
                return solution
            except Exception as e:
                logger.error(f"Failed to validate solution structure: {e}")
                return self._create_fallback_solution(incident_data)
                
        except Exception as e:
            logger.error(f"Error analyzing incident {incident_data.get('id', 'unknown')}: {str(e)}")
            return self._create_fallback_solution(incident_data)

    def _create_fallback_solution(self, incident_data: Dict[str, Any]) -> IncidentSolution:
        """Create a fallback solution when LLM fails"""
        incident_id = incident_data.get('id', 'unknown')
        incident_type = incident_data.get('type', 'Unknown')
        reason = incident_data.get('reason', 'Unknown')
        
        fallback_steps = []
        
        # Create basic steps based on incident type
        if incident_type == "Warning":
            fallback_steps = [
                SolutionStep(
                    step_id=1,
                    action_type="KUBECTL_DESCRIBE",
                    description=f"Investigate the {reason} issue by describing the affected resource",
                    target_resource={
                        "kind": incident_data.get('involved_object_kind', 'Unknown'),
                        "name": incident_data.get('involved_object_name', 'unknown'),
                        "namespace": incident_data.get('metadata_namespace', 'default')
                    },
                    command_or_payload={
                        "command": f"describe {incident_data.get('involved_object_kind', 'pod').lower()} {incident_data.get('involved_object_name', 'unknown')} -n {incident_data.get('metadata_namespace', 'default')}"
                    },
                    expected_outcome="Detailed information about the resource state and events"
                ),
                SolutionStep(
                    step_id=2,
                    action_type="KUBECTL_GET_LOGS",
                    description="Check logs for error details",
                    target_resource={
                        "kind": incident_data.get('involved_object_kind', 'Unknown'),
                        "name": incident_data.get('involved_object_name', 'unknown'),
                        "namespace": incident_data.get('metadata_namespace', 'default')
                    },
                    command_or_payload={
                        "command": f"logs {incident_data.get('involved_object_name', 'unknown')} -n {incident_data.get('metadata_namespace', 'default')}"
                    },
                    expected_outcome="Application logs showing error details"
                )
            ]
        else:
            fallback_steps = [
                SolutionStep(
                    step_id=1,
                    action_type="MONITOR",
                    description=f"Monitor the {reason} event to ensure it completed successfully",
                    target_resource={
                        "kind": incident_data.get('involved_object_kind', 'Unknown'),
                        "name": incident_data.get('involved_object_name', 'unknown'),
                        "namespace": incident_data.get('metadata_namespace', 'default')
                    },
                    command_or_payload={
                        "command": f"get {incident_data.get('involved_object_kind', 'pod').lower()} {incident_data.get('involved_object_name', 'unknown')} -n {incident_data.get('metadata_namespace', 'default')}"
                    },
                    expected_outcome="Resource is in expected state"
                )
            ]
        
        fallback_solution = IncidentSolution(
            solution_id=f"FALLBACK-{incident_id[:8]}",
            incident_id=incident_id,
            incident_type=incident_type,
            summary=f"Basic troubleshooting steps for {reason} incident (LLM analysis unavailable)",
            analysis=f"This is a fallback analysis for incident {incident_id}. The LLM service was unavailable, so basic troubleshooting steps have been provided based on the incident type and reason.",
            steps=fallback_steps,
            confidence_score=0.5,
            estimated_time_to_resolve_mins=15,
            severity_level="MEDIUM" if incident_type == "Warning" else "LOW",
            recommendations=[
                "Check LLM service connectivity",
                "Review incident details manually",
                "Monitor system resources"
            ]
        )
        
        logger.info(f"Created fallback solution for incident: {incident_id}")
        self._print_solution_to_terminal(fallback_solution)
        
        return fallback_solution

    def _print_solution_to_terminal(self, solution: IncidentSolution):
        """Print the solution details to terminal"""
        print("\n" + "="*80)
        print("🤖 LLM INCIDENT ANALYSIS COMPLETE")
        print("="*80)
        print(f"📋 Solution ID: {solution.solution_id}")
        print(f"🎯 Incident ID: {solution.incident_id}")
        print(f"⚠️  Incident Type: {solution.incident_type}")
        print(f"🔥 Severity Level: {solution.severity_level}")
        print(f"⏱️  Estimated Time: {solution.estimated_time_to_resolve_mins} minutes")
        print(f"🎯 Confidence Score: {solution.confidence_score}")
        print("-"*80)
        
        print(f"📝 SUMMARY:")
        print(f"   {solution.summary}")
        print("-"*80)
        
        print(f"🔍 ANALYSIS:")
        print(f"   {solution.analysis}")
        print("-"*80)
        
        print(f"🔧 RESOLUTION STEPS ({len(solution.steps)} steps):")
        for i, step in enumerate(solution.steps, 1):
            print(f"   {i}. [{step.action_type}] {step.description}")
            if step.target_resource:
                print(f"      Target: {step.target_resource.get('kind', 'N/A')} '{step.target_resource.get('name', 'N/A')}' in namespace '{step.target_resource.get('namespace', 'N/A')}'")
            if step.command_or_payload.get('command'):
                print(f"      Command: kubectl {step.command_or_payload['command']}")
            print(f"      Expected: {step.expected_outcome}")
            print()
        
        print(f"💡 RECOMMENDATIONS ({len(solution.recommendations)} items):")
        for i, rec in enumerate(solution.recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("="*80)
        print("✅ Analysis Complete - Solution Ready for Implementation")
        print("="*80 + "\n")

# Global instance
llm_client = KubernetesLLMClient()

def get_llm_client() -> KubernetesLLMClient:
    """Get the global LLM client instance"""
    return llm_client

# Convenience functions
def analyze_kubernetes_incident_sync(incident_data: Dict[str, Any]) -> IncidentSolution:
    """
    Synchronous version of incident analysis
    
    Args:
        incident_data: Dictionary containing incident information
        
    Returns:
        IncidentSolution: Structured solution
    """
    client = get_llm_client()
    return client.analyze_incident_sync(incident_data)