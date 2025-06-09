import os
import logging
import json
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from pydantic import BaseModel, Field

# Try different import approaches for compatibility
try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    ChatOpenAI = None

try:
    from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
    from langchain.chains import LLMChain
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_PROMPTS_AVAILABLE = True
except ImportError:
    LANGCHAIN_PROMPTS_AVAILABLE = False

# Fallback to direct OpenAI client if LangChain has issues
try:
    import openai
    OPENAI_DIRECT_AVAILABLE = True
except ImportError:
    OPENAI_DIRECT_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)

# Move all model definitions to the top, before the client class
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

class RemediationSolution(BaseModel):
    """Simplified remediation solution model"""
    issue_summary: str = Field(description="Brief summary of the Kubernetes problem")
    suggestion: str = Field(description="Detailed explanation of what should be done and why")
    command: str = Field(description="Single kubectl command for remediation (without kubectl prefix)")
    is_executable: bool = Field(description="Whether the command is safe to execute automatically")
    severity_level: str = Field(description="Assessed severity level")
    estimated_time_mins: int = Field(description="Estimated time to resolve in minutes")
    confidence_score: float = Field(description="Confidence in the solution")
    active_executors: List[str] = Field(description="Available executors")

class LLMRemediationOutput(BaseModel):
    """LangChain output parser model for remediation"""
    issue_summary: str = Field(description="Brief summary of the Kubernetes problem")
    suggestion: str = Field(description="Detailed explanation of what should be done and why")
    command: str = Field(description="Single kubectl command for remediation")
    is_executable: bool = Field(description="Whether the command is safe to execute")
    severity_level: str = Field(description="Assessed severity level")
    estimated_time_mins: int = Field(description="Estimated time to resolve")
    confidence_score: float = Field(description="Confidence in the solution")
    active_executors: List[str] = Field(description="Available executors")

class KubernetesLLMClient:
    """
    LLM client for analyzing Kubernetes incidents and providing structured solutions
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.base_url = settings.OPENAI_BASE_URL
        self.timeout = settings.LLM_TIMEOUT
        self.use_langchain = False
        self.use_direct_openai = False
        
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in configuration.")
        
        # Try to initialize with different approaches
        self._initialize_client()
        
        logger.info(f"Initialized LLM client with model: {self.model}")

    def _initialize_client(self):
        """Initialize the LLM client with fallback approaches"""
        
        # Approach 1: Try LangChain with environment variables (avoids parameter conflicts)
        if LANGCHAIN_AVAILABLE and LANGCHAIN_PROMPTS_AVAILABLE:
            try:
                # Set environment variables to avoid parameter passing issues
                os.environ["OPENAI_API_KEY"] = self.api_key
                if self.base_url and self.base_url.strip():
                    os.environ["OPENAI_BASE_URL"] = self.base_url
                
                # Initialize with minimal parameters, relying on environment variables
                self.llm = ChatOpenAI(
                    model=self.model,
                    temperature=0.1,
                    max_tokens=4000
                )
                
                # Setup LangChain components
                self._setup_prompt_template()
                self.output_parser = JsonOutputParser(pydantic_object=LLMSolutionOutput)
                self.chain = self.chat_prompt_template | self.llm | self.output_parser
                
                self.use_langchain = True
                logger.info("Successfully initialized LangChain ChatOpenAI client")
                return
                
            except Exception as e:
                logger.warning(f"LangChain initialization failed: {e}")
        
        # Approach 2: Try direct OpenAI client
        if OPENAI_DIRECT_AVAILABLE:
            try:
                client_params = {
                    "api_key": self.api_key,
                    "timeout": self.timeout or 120
                }
                
                if self.base_url and self.base_url.strip():
                    client_params["base_url"] = self.base_url
                
                self.direct_client = openai.OpenAI(**client_params)
                self.use_direct_openai = True
                logger.info("Successfully initialized direct OpenAI client")
                return
                
            except Exception as e:
                logger.warning(f"Direct OpenAI client initialization failed: {e}")
        
        # Approach 3: Fallback mode (no LLM, use rule-based responses)
        logger.warning("All LLM initialization attempts failed. Using fallback mode.")
        self.use_langchain = False
        self.use_direct_openai = False

    def _setup_prompt_template(self):
        """Setup LangChain prompt templates with improved structure"""
        if not LANGCHAIN_PROMPTS_AVAILABLE:
            return
            
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
        9. Assign appropriate executor to each step based on the action type"""

        human_prompt_str = """Analyze this Kubernetes incident and provide a complete solution using only these active executors: {active_executors}

        Incident Details:
        - Incident ID: {incident_id}
        - Type: {incident_type}
        - Reason: {incident_reason}
        - Message: {incident_message}
        - Namespace: {incident_namespace}
        - Object: {incident_object_kind}/{incident_object_name}
        - Source: {incident_source_component}

        Provide a complete JSON solution with ALL required fields. Keep analysis brief to avoid truncation. Only use the available active executors."""

        system_message_prompt = SystemMessagePromptTemplate.from_template(system_prompt_str)
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_prompt_str)
        
        self.chat_prompt_template = ChatPromptTemplate.from_messages([
            system_message_prompt, 
            human_message_prompt
        ])

    def _call_direct_openai(self, prompt: str) -> str:
        """Call OpenAI directly without LangChain"""
        try:
            response = self.direct_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Kubernetes administrator. Provide structured JSON responses for incident analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Direct OpenAI call failed: {e}")
            return None

    def analyze_incident_sync(self, incident_data: Dict[str, Any], active_executors: List[str]) -> IncidentSolution:
        """
        Synchronous method to analyze a Kubernetes incident
        """
        try:
            incident_id = incident_data.get('id', 'unknown')
            logger.info(f"Starting LLM analysis for incident: {incident_id} with active executors: {active_executors}")
            
            # Prepare input data
            input_data = {
                "incident_id": incident_data.get('id') or 'N/A',
                "incident_type": incident_data.get('type') or 'N/A',
                "incident_reason": incident_data.get('reason') or 'N/A',
                "incident_message": (incident_data.get('message') or 'N/A')[:200],
                "incident_namespace": incident_data.get('metadata_namespace') or 'N/A',
                "incident_object_kind": incident_data.get('involved_object_kind') or 'N/A',
                "incident_object_name": incident_data.get('involved_object_name') or 'N/A',
                "incident_source_component": incident_data.get('source_component') or 'N/A',
                "active_executors": active_executors or ["kubectl"]
            }
            
            # Try LangChain approach first
            if self.use_langchain:
                try:
                    chain_output = self.chain.invoke(input_data)
                    
                    if isinstance(chain_output, dict):
                        llm_solution_output = LLMSolutionOutput.model_validate(chain_output)
                    else:
                        llm_solution_output = chain_output
                    
                    # Convert to IncidentSolution
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
                    
                except Exception as langchain_error:
                    logger.error(f"LangChain analysis failed: {langchain_error}")
            
            # Try direct OpenAI approach
            if self.use_direct_openai:
                try:
                    prompt = self._build_direct_prompt(input_data)
                    response_text = self._call_direct_openai(prompt)
                    
                    if response_text:
                        # Parse JSON response
                        try:
                            response_json = json.loads(response_text)
                            llm_solution_output = LLMSolutionOutput.model_validate(response_json)
                            
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
                            
                            logger.info(f"Successfully generated solution via direct OpenAI for incident: {incident_id}")
                            self._print_solution_to_terminal(solution)
                            return solution
                            
                        except json.JSONDecodeError as json_error:
                            logger.error(f"Failed to parse JSON response: {json_error}")
                        except Exception as parse_error:
                            logger.error(f"Failed to validate response: {parse_error}")
                
                except Exception as direct_error:
                    logger.error(f"Direct OpenAI analysis failed: {direct_error}")
            
            # Fallback to rule-based solution
            logger.warning(f"All LLM approaches failed for incident {incident_id}, using fallback")
            return self._create_fallback_solution(incident_data, active_executors)
                
        except Exception as e:
            logger.error(f"Unexpected error analyzing incident {incident_data.get('id', 'unknown')}: {str(e)}")
            return self._create_fallback_solution(incident_data, active_executors)

    def _build_direct_prompt(self, input_data: Dict[str, Any]) -> str:
        """Build prompt for direct OpenAI API call"""
        return f"""Analyze this Kubernetes incident and provide a complete solution in JSON format using only these active executors: {input_data['active_executors']}

Incident Details:
- Incident ID: {input_data['incident_id']}
- Type: {input_data['incident_type']}
- Reason: {input_data['incident_reason']}
- Message: {input_data['incident_message']}
- Namespace: {input_data['incident_namespace']}
- Object: {input_data['incident_object_kind']}/{input_data['incident_object_name']}
- Source: {input_data['incident_source_component']}

Provide a complete JSON response with this exact structure:
{{
    "solution_id": "SOL-KUBE-[random-4-digits]",
    "incident_id": "{input_data['incident_id']}",
    "incident_type": "{input_data['incident_type']}",
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
    "active_executors": {input_data['active_executors']}
}}

IMPORTANT: Return only valid JSON. For Normal events use severity_level "LOW", for Warning events use "MEDIUM" or "HIGH"."""

    def analyze_remediation_sync(self, alert_data: Dict[str, Any], active_executors: List[str]) -> RemediationSolution:
        """
        Analyze Kubernetes alert/issue and provide single-command remediation
        """
        try:
            alert_name = alert_data.get('alert_name', 'Unknown')
            logger.info(f"Starting remediation analysis for alert: {alert_name}")
            
            # Try LangChain approach first
            if self.use_langchain:
                try:
                    # Use existing remediation logic with LangChain
                    input_data = {
                        "alert_name": alert_data.get('alert_name', 'Unknown'),
                        "namespace": alert_data.get('namespace', 'default'),
                        "resource_name": alert_data.get('pod_name', alert_data.get('resource_name', 'unknown')),
                        "issue_details": self._format_issue_details(alert_data),
                        "additional_context": self._format_additional_context(alert_data),
                        "active_executors": active_executors
                    }
                    
                    remediation_parser = JsonOutputParser(pydantic_object=LLMRemediationOutput)
                    remediation_chain = self.chat_prompt_template | self.llm | remediation_parser
                    
                    chain_output = remediation_chain.invoke(input_data)
                    
                    if isinstance(chain_output, dict):
                        remediation_output = LLMRemediationOutput.model_validate(chain_output)
                    else:
                        remediation_output = chain_output
                    
                    solution = RemediationSolution(
                        issue_summary=remediation_output.issue_summary,
                        suggestion=remediation_output.suggestion,
                        command=remediation_output.command,
                        is_executable=remediation_output.is_executable,
                        severity_level=remediation_output.severity_level,
                        estimated_time_mins=remediation_output.estimated_time_mins,
                        confidence_score=remediation_output.confidence_score,
                        active_executors=remediation_output.active_executors
                    )
                    
                    logger.info(f"Successfully generated remediation for alert: {alert_name}")
                    self._print_remediation_to_terminal(solution)
                    return solution
                    
                except Exception as langchain_error:
                    logger.error(f"LangChain remediation failed: {langchain_error}")
            
            # Try direct OpenAI approach
            if self.use_direct_openai:
                try:
                    prompt = self._build_remediation_prompt(alert_data, active_executors)
                    response_text = self._call_direct_openai(prompt)
                    
                    if response_text:
                        try:
                            response_json = json.loads(response_text)
                            remediation_output = LLMRemediationOutput.model_validate(response_json)
                            
                            solution = RemediationSolution(
                                issue_summary=remediation_output.issue_summary,
                                suggestion=remediation_output.suggestion,
                                command=remediation_output.command,
                                is_executable=remediation_output.is_executable,
                                severity_level=remediation_output.severity_level,
                                estimated_time_mins=remediation_output.estimated_time_mins,
                                confidence_score=remediation_output.confidence_score,
                                active_executors=remediation_output.active_executors
                            )
                            
                            logger.info(f"Successfully generated remediation via direct OpenAI for alert: {alert_name}")
                            self._print_remediation_to_terminal(solution)
                            return solution
                            
                        except (json.JSONDecodeError, Exception) as parse_error:
                            logger.error(f"Failed to parse remediation response: {parse_error}")
                
                except Exception as direct_error:
                    logger.error(f"Direct OpenAI remediation failed: {direct_error}")
            
            # Fallback
            return self._create_fallback_remediation(alert_data, active_executors)
            
        except Exception as e:
            logger.error(f"Error in remediation analysis: {str(e)}")
            return self._create_fallback_remediation(alert_data, active_executors)

    def _build_remediation_prompt(self, alert_data: Dict[str, Any], active_executors: List[str]) -> str:
        """Build prompt for remediation analysis"""
        return f"""Analyze this Kubernetes alert and provide a single remediation command in JSON format.

Alert Details:
- Alert Name: {alert_data.get('alert_name', 'Unknown')}
- Namespace: {alert_data.get('namespace', 'default')}
- Resource: {alert_data.get('pod_name', alert_data.get('resource_name', 'unknown'))}
- Issue Details: {self._format_issue_details(alert_data)}
- Additional Context: {self._format_additional_context(alert_data)}
- Active Executors: {active_executors}

Provide a JSON response with this exact structure:
{{
    "issue_summary": "[Brief summary of the Kubernetes problem]",
    "suggestion": "[Detailed explanation of what should be done and why]",
    "command": "[Single kubectl command for remediation without kubectl prefix]",
    "is_executable": true/false,
    "severity_level": "[LOW|MEDIUM|HIGH|CRITICAL]",
    "estimated_time_mins": [number],
    "confidence_score": [0.0-1.0],
    "active_executors": {active_executors}
}}

IMPORTANT: Return only valid JSON. Command should be safe and executable."""

    def _format_issue_details(self, alert_data: Dict[str, Any]) -> str:
        """Format issue details from alert data"""
        details = []
        
        if alert_data.get('usage'):
            details.append(f"Current usage: {alert_data['usage']}")
        if alert_data.get('threshold'):
            details.append(f"Threshold: {alert_data['threshold']}")
        if alert_data.get('duration'):
            details.append(f"Duration: {alert_data['duration']}")
        if alert_data.get('status'):
            details.append(f"Status: {alert_data['status']}")
        if alert_data.get('reason'):
            details.append(f"Reason: {alert_data['reason']}")
        
        return "; ".join(details) if details else "No specific details provided"

    def _format_additional_context(self, alert_data: Dict[str, Any]) -> str:
        """Format additional context from alert data"""
        context = []
        
        if alert_data.get('node_name'):
            context.append(f"Node: {alert_data['node_name']}")
        if alert_data.get('container_name'):
            context.append(f"Container: {alert_data['container_name']}")
        if alert_data.get('deployment_name'):
            context.append(f"Deployment: {alert_data['deployment_name']}")
        
        return "; ".join(context) if context else "No additional context"

    def _create_fallback_solution(self, incident_data: Dict[str, Any], active_executors: List[str]) -> IncidentSolution:
        """Create a fallback solution when LLM fails"""
        incident_id = incident_data.get('id', 'unknown')
        incident_type = incident_data.get('type', 'Unknown')
        reason = incident_data.get('reason', 'Unknown')
        
        # Use kubectl as default executor if available, otherwise use first available
        default_executor = "kubectl" if "kubectl" in active_executors else (active_executors[0] if active_executors else "kubectl")
        
        fallback_steps = []
        
        # Create basic steps based on incident type with proper None handling
        object_kind = incident_data.get('involved_object_kind') or 'pod'
        object_name = incident_data.get('involved_object_name') or 'unknown'
        namespace = incident_data.get('metadata_namespace') or 'default'
        
        # Create basic steps based on incident type
        if incident_type == "Warning":
            fallback_steps = [
                SolutionStep(
                    step_id=1,
                    action_type="KUBECTL_DESCRIBE",
                    description=f"Investigate the {reason} issue by describing the affected resource",
                    target_resource={
                        "kind": object_kind,
                        "name": object_name,
                        "namespace": namespace
                    },
                    command_or_payload={
                        "command": f"describe {object_kind.lower()} {object_name} -n {namespace}"
                    },
                    expected_outcome="Detailed information about the resource state and events",
                    executor=default_executor
                ),
                SolutionStep(
                    step_id=2,
                    action_type="KUBECTL_GET_LOGS",
                    description="Check logs for error details",
                    target_resource={
                        "kind": object_kind,
                        "name": object_name,
                        "namespace": namespace
                    },
                    command_or_payload={
                        "command": f"logs {object_name} -n {namespace}"
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
                        "kind": object_kind,
                        "name": object_name,
                        "namespace": namespace
                    },
                    command_or_payload={
                        "command": f"get {object_kind.lower()} {object_name} -n {namespace}"
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

    def _create_fallback_remediation(self, alert_data: Dict[str, Any], active_executors: List[str]) -> RemediationSolution:
        """Create fallback remediation when LLM fails"""
        alert_name = alert_data.get('alert_name', 'Unknown')
        namespace = alert_data.get('namespace', 'default')
        resource_name = alert_data.get('pod_name', alert_data.get('resource_name', 'unknown'))
        
        # Basic remediation based on alert type
        if 'CPU' in alert_name or 'cpu' in alert_name.lower():
            command = f"top pods -n {namespace}"
            suggestion = "Check CPU usage of pods to identify resource-intensive workloads"
        elif 'Memory' in alert_name or 'memory' in alert_name.lower():
            command = f"top pods -n {namespace} --sort-by=memory"
            suggestion = "Check memory usage of pods to identify memory-intensive workloads"
        elif 'CrashLoop' in alert_name:
            command = f"logs {resource_name} -n {namespace} --previous"
            suggestion = "Check previous logs to understand why the pod is crashing"
        else:
            command = f"describe pod {resource_name} -n {namespace}"
            suggestion = "Get detailed information about the pod to diagnose the issue"
        
        return RemediationSolution(
            issue_summary=f"Kubernetes issue detected: {alert_name}",
            suggestion=suggestion,
            command=command,
            is_executable=True,
            severity_level="MEDIUM",
            estimated_time_mins=5,
            confidence_score=0.6,
            active_executors=active_executors
        )

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
        print("✅ Analysis Complete - Solution Ready for Implementation")
        print("="*80 + "\n")

    def _print_remediation_to_terminal(self, solution: RemediationSolution):
        """Print remediation solution to terminal"""
        print("\n" + "="*80)
        print("🔧 KUBERNETES REMEDIATION ASSISTANT")
        print("="*80)
        print(f"📋 Issue Summary: {solution.issue_summary}")
        print(f"🔥 Severity Level: {solution.severity_level}")
        print(f"⏱️  Estimated Time: {solution.estimated_time_mins} minutes")
        print(f"🎯 Confidence Score: {solution.confidence_score}")
        print(f"✅ Executable: {'Yes' if solution.is_executable else 'No'}")
        print("-"*80)
        
        print(f"💡 SUGGESTION:")
        print(f"   {solution.suggestion}")
        print("-"*80)
        
        print(f"🔧 REMEDIATION COMMAND:")
        print(f"   kubectl {solution.command}")
        print("-"*80)
        
        print("="*80 + "\n")


# Initialize client with error handling
try:
    llm_client = KubernetesLLMClient()
    logger.info("LLM client initialized successfully")
except Exception as init_error:
    logger.error(f"Failed to initialize LLM client: {init_error}")
    # Create a dummy client that will use fallback methods
    llm_client = None

def get_llm_client() -> Optional[KubernetesLLMClient]:
    """Get the global LLM client instance"""
    return llm_client

# Convenience functions with error handling
def analyze_kubernetes_incident_sync(incident_data: Dict[str, Any], active_executors: List[str] = None) -> IncidentSolution:
    """
    Synchronous version of incident analysis with fallback support
    
    Args:
        incident_data: Dictionary containing incident information
        active_executors: List of active executor names
        
    Returns:
        IncidentSolution: Structured solution
    """
    if active_executors is None:
        active_executors = ["kubectl"]  # Default fallback
    
    client = get_llm_client()
    if client:
        return client.analyze_incident_sync(incident_data, active_executors)
    else:
        # Create a temporary client for fallback
        temp_client = KubernetesLLMClient()
        return temp_client._create_fallback_solution(incident_data, active_executors)

def analyze_kubernetes_remediation_sync(alert_data: Dict[str, Any], active_executors: List[str] = None) -> RemediationSolution:
    """
    Convenience function for Kubernetes remediation analysis with fallback support
    
    Args:
        alert_data: Dictionary containing alert/issue information
        active_executors: List of active executor names
        
    Returns:
        RemediationSolution: Structured remediation with command
    """
    if active_executors is None:
        active_executors = ["kubectl"]
    
    client = get_llm_client()
    if client:
        return client.analyze_remediation_sync(alert_data, active_executors)
    else:
        # Create a temporary client for fallback
        temp_client = KubernetesLLMClient()
        return temp_client._create_fallback_remediation(alert_data, active_executors)