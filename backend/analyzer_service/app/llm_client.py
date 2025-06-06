import os
import logging
import json
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import JsonOutputParser
from app.config import settings

logger = logging.getLogger(__name__)

class SolutionStep(BaseModel):
    step_id: int = Field(description="Sequential ID of the step")
    action_type: str = Field(description="Type of action (e.g., KUBECTL_APPLY, KUBECTL_DELETE, KUBECTL_GET_LOGS, etc.)")
    description: str = Field(description="Detailed description of what this step does and why")
    target_resource: Dict[str, Any] = Field(description="Target Kubernetes resource details")
    command_or_payload: Dict[str, Any] = Field(description="Command or payload for the action")
    expected_outcome: str = Field(description="What is expected after this step is executed successfully")
    executor: str = Field(description="Which executor should handle this step (kubectl, crossplane, argocd)")

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
    active_executors: List[str] = Field(description="List of active executors used for this solution")



class LLMSolutionOutput(BaseModel):
    """LangChain output parser model"""
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
    active_executors: List[str] = Field(description="List of active executors used for this solution")

class KubernetesLLMClient:
    """
    LLM client for analyzing Kubernetes incidents and providing structured solutions using LangChain
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.base_url = settings.OPENAI_BASE_URL
        self.timeout = settings.LLM_TIMEOUT
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in configuration.")
        
        # Initialize LangChain LLM with increased limits
        llm_params = {
            "openai_api_key": self.api_key,
            "model_name": self.model,
            "temperature": 0.1,
            "max_tokens": 4000,  # Increased from 3000
            "timeout": 120,      # Increased timeout
            "request_timeout": 120
        }
        
        if self.base_url:
            llm_params["base_url"] = self.base_url
            
        self.llm = ChatOpenAI(**llm_params)
        
        # Setup LangChain prompt template
        self._setup_prompt_template()
        
        # Initialize output parser
        self.output_parser = JsonOutputParser(pydantic_object=LLMSolutionOutput)
        
        # Create LangChain chain
        self.chain = self.chat_prompt_template | self.llm | self.output_parser
        
        logger.info(f"Initialized LangChain LLM client with model: {self.model}")

    def _setup_prompt_template(self):
        """Setup LangChain prompt templates with improved structure"""
        system_prompt_str = """You are an expert Kubernetes administrator and AI assistant specialized in analyzing Kubernetes incidents and providing actionable solutions.

Your task is to analyze Kubernetes incident data and generate a comprehensive solution in JSON format.

CRITICAL: You MUST provide a complete JSON response with ALL required fields. Do not truncate your response.

Available Executors: {active_executors}

The solution MUST be structured according to this exact JSON schema with ALL fields present:

{{
  "solution_id": "SOL-KUBE-[random-4-digits]",
  "incident_id": "[provided incident ID]",
  "incident_type": "[Normal or Warning]",
  "summary": "[Brief 1-2 sentence summary]",
  "analysis": "[Detailed analysis - keep under 500 characters]",
  "steps": [
    {{
      "step_id": 1,
      "action_type": "[KUBECTL_GET_LOGS|KUBECTL_DESCRIBE|KUBECTL_SCALE|MONITOR|VERIFY]",
      "description": "[What this step does]",
      "target_resource": {{
        "kind": "[Pod|Deployment|Service|etc]",
        "name": "[resource name]",
        "namespace": "[namespace]"
      }},
      "command_or_payload": {{
        "command": "[kubectl command without 'kubectl' prefix]"
      }},
      "expected_outcome": "[Expected result]",
      "executor": "[kubectl|crossplane|argocd]"
    }}
  ],
  "confidence_score": 0.8,
  "estimated_time_to_resolve_mins": 10,
  "severity_level": "[LOW|MEDIUM|HIGH|CRITICAL]",
  "recommendations": ["[recommendation 1]", "[recommendation 2]"],
  "active_executors": {active_executors}
}}

IMPORTANT RULES:
1. For Normal events: Use severity_level "LOW", focus on monitoring steps
2. For Warning events: Use severity_level "MEDIUM" or "HIGH", provide diagnostic steps
3. Always include at least 1 step and 1 recommendation
4. Keep analysis under 500 characters to avoid truncation
5. Provide complete JSON - do not truncate the response
6. Use simple, actionable kubectl commands
7. ALWAYS check if resources exist before trying to access them
8. ONLY use executors from the active_executors list
9. Assign appropriate executor to each step based on the action type:
   - kubectl: For basic Kubernetes operations (get, describe, logs, apply, delete)
   - crossplane: For infrastructure provisioning and cloud resource management
   - argocd: For GitOps deployments and application management

Respond ONLY with valid, complete JSON matching the schema above."""

        human_prompt_str = """Analyze this Kubernetes incident and provide a complete solution using only these active executors: {active_executors}

Incident ID: {incident_id}
Type: {incident_type}
Reason: {incident_reason}
Message: {incident_message}
Namespace: {incident_namespace}
Object: {incident_object_kind}/{incident_object_name}
Source: {incident_source_component}

Provide a complete JSON solution with ALL required fields. Keep analysis brief to avoid truncation. Only use the available active executors."""

        system_message_prompt = SystemMessagePromptTemplate.from_template(system_prompt_str)
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_prompt_str)
        self.chat_prompt_template = ChatPromptTemplate.from_messages([
            system_message_prompt, 
            human_message_prompt
        ])

    def analyze_incident_sync(self, incident_data: Dict[str, Any], active_executors: List[str]) -> IncidentSolution:
        """
        Synchronous method to analyze a Kubernetes incident using LangChain
        """
        try:
            incident_id = incident_data.get('id', 'unknown')
            logger.info(f"Starting LangChain LLM analysis for incident: {incident_id} with active executors: {active_executors}")
            
            # Prepare simplified input data for LangChain chain
            input_data = {
                "incident_id": incident_data.get('id', 'N/A'),
                "incident_type": incident_data.get('type', 'N/A'),
                "incident_reason": incident_data.get('reason', 'N/A'),
                "incident_message": incident_data.get('message', 'N/A')[:200],  # Limit message length
                "incident_namespace": incident_data.get('metadata_namespace', 'N/A'),
                "incident_object_kind": incident_data.get('involved_object_kind', 'N/A'),
                "incident_object_name": incident_data.get('involved_object_name', 'N/A'),
                "incident_source_component": incident_data.get('source_component', 'N/A'),
                "active_executors": active_executors
            }
            
            # Invoke LangChain chain with better error handling
            try:
                logger.info(f"Invoking LangChain chain for incident: {incident_id}")
                chain_output: Union[LLMSolutionOutput, dict] = self.chain.invoke(input_data)
                logger.info(f"LangChain returned output type: {type(chain_output)}")
                
                # Log the raw output for debugging
                if isinstance(chain_output, dict):
                    logger.info(f"Chain output keys: {list(chain_output.keys())}")
                    logger.debug(f"Chain output: {chain_output}")
                
                # Validate the output has required fields
                if isinstance(chain_output, dict):
                    missing_fields = []
                    required_fields = ['solution_id', 'incident_id', 'incident_type', 'summary', 'analysis', 'steps', 'severity_level', 'recommendations', 'active_executors']
                    
                    for field in required_fields:
                        if field not in chain_output:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        logger.error(f"LangChain output missing required fields: {missing_fields}")
                        logger.error(f"Available fields: {list(chain_output.keys())}")
                        return self._create_fallback_solution(incident_data, active_executors)
                    
                    # Validate steps is not empty
                    if not chain_output.get('steps') or len(chain_output.get('steps', [])) == 0:
                        logger.error("LangChain output has empty steps array")
                        return self._create_fallback_solution(incident_data, active_executors)
                    
                    try:
                        llm_solution_output = LLMSolutionOutput.model_validate(chain_output)
                        logger.info("Successfully validated LangChain output")
                    except Exception as pydantic_exc:
                        logger.error(f"Failed to validate LangChain output: {pydantic_exc}")
                        logger.error(f"Chain output: {chain_output}")
                        return self._create_fallback_solution(incident_data, active_executors)
                        
                elif isinstance(chain_output, LLMSolutionOutput):
                    llm_solution_output = chain_output
                    logger.info("LangChain returned LLMSolutionOutput model directly")
                else:
                    logger.error(f"Unexpected output type from LangChain: {type(chain_output)}")
                    return self._create_fallback_solution(incident_data, active_executors)
                
            except Exception as chain_error:
                logger.error(f"LangChain chain invocation failed for incident {incident_id}: {str(chain_error)}")
                return self._create_fallback_solution(incident_data, active_executors)
            
            # Convert to IncidentSolution
            try:
                solution = IncidentSolution(
                    solution_id=llm_solution_output.solution_id,
                    incident_id=llm_solution_output.incident_id,
                    incident_type=llm_solution_output.incident_type,
                    summary=llm_solution_output.summary,
                    analysis=llm_solution_output.analysis,
                    steps=llm_solution_output.steps,
                    confidence_score=llm_solution_output.confidence_score,
                    estimated_time_to_resolve_mins=llm_solution_output.estimated_time_to_resolve_mins,
                    severity_level=llm_solution_output.severity_level,
                    recommendations=llm_solution_output.recommendations,
                    active_executors=llm_solution_output.active_executors
                )
                
                logger.info(f"Successfully generated solution for incident: {incident_id}")
                self._print_solution_to_terminal(solution)
                return solution
                
            except Exception as conversion_error:
                logger.error(f"Failed to convert LLMSolutionOutput to IncidentSolution: {conversion_error}")
                return self._create_fallback_solution(incident_data, active_executors)
                
        except Exception as e:
            logger.error(f"Unexpected error analyzing incident {incident_data.get('id', 'unknown')}: {str(e)}")
            return self._create_fallback_solution(incident_data, active_executors)

    def _create_fallback_solution(self, incident_data: Dict[str, Any], active_executors: List[str]) -> IncidentSolution:
        """Create a fallback solution when LLM fails"""
        incident_id = incident_data.get('id', 'unknown')
        incident_type = incident_data.get('type', 'Unknown')
        reason = incident_data.get('reason', 'Unknown')
        
        # Use kubectl as default executor if available, otherwise use first available
        default_executor = "kubectl" if "kubectl" in active_executors else (active_executors[0] if active_executors else "kubectl")
        
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
                    expected_outcome="Detailed information about the resource state and events",
                    executor=default_executor
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
                    expected_outcome="Application logs showing error details",
                    executor=default_executor
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
                    expected_outcome="Resource is in expected state",
                    executor=default_executor
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
            ],
            active_executors=active_executors
        )
        
        logger.info(f"Created fallback solution for incident: {incident_id}")
        self._print_solution_to_terminal(fallback_solution)
        
        return fallback_solution

    def _print_solution_to_terminal(self, solution: IncidentSolution):
        """Print the solution details to terminal"""
        print("\n" + "="*80)
        print("🤖 LANGCHAIN LLM INCIDENT ANALYSIS COMPLETE")
        print("="*80)
        print(f"📋 Solution ID: {solution.solution_id}")
        print(f"🎯 Incident ID: {solution.incident_id}")
        print(f"⚠️  Incident Type: {solution.incident_type}")
        print(f"🔥 Severity Level: {solution.severity_level}")
        print(f"⏱️  Estimated Time: {solution.estimated_time_to_resolve_mins} minutes")
        print(f"🎯 Confidence Score: {solution.confidence_score}")
        print(f"🔧 Active Executors: {', '.join(solution.active_executors)}")
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
            print(f"      Executor: {step.executor}")
            print()
        
        print(f"💡 RECOMMENDATIONS ({len(solution.recommendations)} items):")
        for i, rec in enumerate(solution.recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("="*80)
        print("✅ LangChain Analysis Complete - Solution Ready for Implementation")
        print("="*80 + "\n")

# Global instance
llm_client = KubernetesLLMClient()

def get_llm_client() -> KubernetesLLMClient:
    """Get the global LLM client instance"""
    return llm_client

# Convenience functions
def analyze_kubernetes_incident_sync(incident_data: Dict[str, Any], active_executors: List[str] = None) -> IncidentSolution:
    """
    Synchronous version of incident analysis using LangChain
    
    Args:
        incident_data: Dictionary containing incident information
        active_executors: List of active executor names
        
    Returns:
        IncidentSolution: Structured solution
    """
    if active_executors is None:
        active_executors = ["kubectl"]  # Default fallback
    
    client = get_llm_client()
    return client.analyze_incident_sync(incident_data, active_executors)
