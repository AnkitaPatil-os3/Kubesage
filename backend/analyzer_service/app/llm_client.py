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
        # Updated configuration for new LLM endpoint
        self.api_key = "dummy-key"  # Some endpoints require a key even if not used
        self.model = "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
        self.base_url = "http://10.0.32.186:8080/v1"
        self.timeout = 120  # Increased timeout
        self.use_direct_openai = False
        
        logger.info(f"🚀 Initializing LLM client with:")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   Timeout: {self.timeout}s")
        
        # Initialize the client
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the LLM client"""
        if OPENAI_DIRECT_AVAILABLE:
            try:
                self.direct_client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout
                )
                self.use_direct_openai = True
                logger.info("✅ Successfully initialized LLM client")
                return
            except Exception as e:
                logger.error(f"❌ Failed to initialize LLM client: {e}")
                raise Exception(f"LLM service initialization failed: {e}")
        else:
            raise Exception("OpenAI client not available")

    def _call_direct_openai(self, prompt: str) -> str:
        """Call LLM directly"""
        try:
            logger.info(f"🤖 Making LLM API call...")
            
            response = self.direct_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert Kubernetes administrator. 
                        Respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
                        Start your response directly with { and end with }."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=3000  # Increased to prevent truncation
            )
            
            content = response.choices[0].message.content
            logger.info(f"✅ LLM API call successful, response length: {len(content) if content else 0}")
            logger.info(f"📝 Raw LLM response: {content[:200]}...")
            
            return content
        except Exception as e:
            logger.error(f"❌ LLM API call failed: {e}")
            raise Exception(f"LLM service call failed: {e}")

    def _clean_llm_response(self, response_text: str) -> str:
        """Clean and extract JSON from LLM response"""
        if not response_text:
            raise Exception("Empty response from LLM")
        
        # Log the raw response for debugging
        logger.info(f"🧹 Cleaning response: {response_text[:300]}...")
        
        # Remove common prefixes that LLMs add
        prefixes_to_remove = [
            "the solution in JSON format:",
            "here is the solution:",
            "here's the json:",
            "json:",
            "",
            ""
        ]
        
        cleaned = response_text.strip()
        
        # Remove prefixes (case insensitive)
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
        
        # Find the first { and last }
        start_idx = cleaned.find('{')
        if start_idx == -1:
            raise Exception("No JSON object found in response")
        
        # Find the matching closing brace
        brace_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(cleaned)):
            if cleaned[i] == '{':
                brace_count += 1
            elif cleaned[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            raise Exception("Incomplete JSON object in response")
        
        json_str = cleaned[start_idx:end_idx + 1]
        
        # 🔧 FIX: Replace single quotes with double quotes in JSON
        json_str = self._fix_json_quotes(json_str)
        
        logger.info(f"✅ Extracted and fixed JSON: {json_str[:200]}...")
        
        return json_str

    def _fix_json_quotes(self, json_str: str) -> str:
        """Fix single quotes to double quotes in JSON string"""
        import re
        
        # Fix array values like ['kubectl'] to ["kubectl"]
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        
        # Fix common single quote issues in JSON
        json_str = json_str.replace("'", '"')
        
        # Fix double-double quotes that might occur
        json_str = re.sub(r'""([^"]*?)""', r'"\1"', json_str)
        
        return json_str

    def analyze_incident_sync(self, incident_data: Dict[str, Any], active_executors: List[str]) -> IncidentSolution:
        """
        Synchronous method to analyze a Kubernetes incident - NO FALLBACK
        """
        try:
            incident_id = incident_data.get('id', 'unknown')
            logger.info(f"🚀 Starting LLM analysis for incident: {incident_id}")
            
            # Prepare input data with better validation
            input_data = {
                "incident_id": incident_data.get('id') or f'incident-{datetime.now().strftime("%H%M%S")}',
                "incident_type": incident_data.get('type') or 'Warning',
                "incident_reason": incident_data.get('reason') or 'Unknown',
                "incident_message": (incident_data.get('message') or 'No message provided')[:500],
                "incident_namespace": incident_data.get('metadata_namespace') or 'default',
                "incident_object_kind": incident_data.get('involved_object_kind') or 'Pod',
                "incident_object_name": incident_data.get('involved_object_name') or 'unknown-resource',
                "incident_source_component": incident_data.get('source_component') or 'kubernetes',
                "active_executors": active_executors or ["kubectl"]
            }
            
            logger.info(f"📊 Analyzing incident: {input_data}")
            
            # Build enhanced prompt
            prompt = self._build_enhanced_prompt(input_data)
            
            # Call LLM
            response_text = self._call_direct_openai(prompt)
            
            if not response_text:
                raise Exception("Empty response from LLM service")
            
            # Clean and parse JSON response
            try:
                # Clean the response text
                json_str = self._clean_llm_response(response_text)
                
                # Parse JSON
                response_json = json.loads(json_str)
                logger.info("✅ JSON parsing successful")
                
                # Validate required fields and provide defaults
                solution_data = {
                    "solution_id": response_json.get("solution_id", f"SOL-{incident_id[:8]}"),
                    "incident_id": response_json.get("incident_id", incident_id),
                    "incident_type": response_json.get("incident_type", input_data["incident_type"]),
                    "summary": response_json.get("summary", "LLM-generated solution summary"),
                    "analysis": response_json.get("analysis", "LLM-generated analysis"),
                    "steps": response_json.get("steps", []),
                    "confidence_score": response_json.get("confidence_score", 0.8),
                    "estimated_time_to_resolve_mins": response_json.get("estimated_time_to_resolve_mins", 10),
                    "severity_level": response_json.get("severity_level", self._determine_severity(input_data["incident_type"], input_data["incident_reason"])),
                    "recommendations": response_json.get("recommendations", ["Monitor the situation", "Check system resources"]),
                    "active_executors": response_json.get("active_executors", active_executors)
                }
                
                # Validate and create steps
                validated_steps = []
                for i, step_data in enumerate(solution_data["steps"]):
                    try:
                        step = SolutionStep(
                            step_id=step_data.get("step_id", i + 1),
                            action_type=step_data.get("action_type", "KUBECTL_DESCRIBE"),
                            description=step_data.get("description", f"Step {i + 1} description"),
                            target_resource=step_data.get("target_resource", {
                                "kind": input_data["incident_object_kind"],
                                "name": input_data["incident_object_name"],
                                "namespace": input_data["incident_namespace"]
                            }),
                            command_or_payload=step_data.get("command_or_payload", {"command": "get pods"}),
                            expected_outcome=step_data.get("expected_outcome", "Expected outcome"),
                            executor=step_data.get("executor", "kubectl")
                        )
                        validated_steps.append(step)
                    except Exception as step_error:
                        logger.warning(f"⚠️ Error validating step {i}: {step_error}")
                        # Create a default step
                        default_step = SolutionStep(
                            step_id=i + 1,
                            action_type="KUBECTL_DESCRIBE",
                            description=f"Investigate the {input_data['incident_reason']} issue",
                            target_resource={
                                "kind": input_data["incident_object_kind"],
                                "name": input_data["incident_object_name"],
                                "namespace": input_data["incident_namespace"]
                            },
                            command_or_payload={
                                "command": f"describe {input_data['incident_object_kind'].lower()} {input_data['incident_object_name']} -n {input_data['incident_namespace']}"
                            },
                            expected_outcome="Resource details and events",
                            executor="kubectl"
                        )
                        validated_steps.append(default_step)
                
                # Create final solution
                solution = IncidentSolution(
                    solution_id=solution_data["solution_id"],
                    incident_id=solution_data["incident_id"],
                    incident_type=solution_data["incident_type"],
                    summary=solution_data["summary"],
                    analysis=solution_data["analysis"],
                    steps=validated_steps,
                    confidence_score=solution_data["confidence_score"],
                    estimated_time_to_resolve_mins=solution_data["estimated_time_to_resolve_mins"],
                    severity_level=solution_data["severity_level"],
                    recommendations=solution_data["recommendations"],
                    active_executors=solution_data["active_executors"]
                )
                
                logger.info(f"✅ Successfully generated solution for incident: {incident_id}")
                self._print_solution_to_terminal(solution)
                return solution
                
            except json.JSONDecodeError as json_error:
                logger.error(f"❌ Failed to parse JSON response: {json_error}")
                logger.error(f"📝 Cleaned response: {json_str if 'json_str' in locals() else 'N/A'}")
                raise Exception(f"Invalid JSON response from LLM: {json_error}")
            except Exception as parse_error:
                logger.error(f"❌ Failed to validate response: {parse_error}")
                raise Exception(f"Response validation failed: {parse_error}")
                
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for incident {incident_id}: {str(e)}")
            raise Exception(f"LLM analysis failed: {str(e)}")

    def _build_enhanced_prompt(self, input_data: Dict[str, Any]) -> str:
        """Build enhanced prompt for LLM with stricter JSON requirements"""
        return f"""Analyze this Kubernetes incident and provide a solution. Respond ONLY with valid JSON using DOUBLE QUOTES for all strings and arrays.

INCIDENT DETAILS:
- ID: {input_data['incident_id']}
- Type: {input_data['incident_type']}
- Reason: {input_data['incident_reason']}
- Message: {input_data['incident_message']}
- Namespace: {input_data['incident_namespace']}
- Object: {input_data['incident_object_kind']}/{input_data['incident_object_name']}
- Source: {input_data['incident_source_component']}

CRITICAL: Use DOUBLE QUOTES for all JSON strings and arrays. Example: "active_executors": ["kubectl"]

Respond with this exact JSON structure:
{{
    "solution_id": "SOL-KUBE-{input_data['incident_id'][:4]}",
    "incident_id": "{input_data['incident_id']}",
    "incident_type": "{input_data['incident_type']}",
    "summary": "Brief technical summary of the issue and solution approach",
    "analysis": "Detailed technical analysis explaining what happened, why it happened, and the implications",
    "steps": [
        {{
            "step_id": 1,
            "action_type": "KUBECTL_DESCRIBE",
            "description": "Investigate the {input_data['incident_reason']} issue by examining the affected resource",
            "target_resource": {{
                "kind": "{input_data['incident_object_kind']}",
                "name": "{input_data['incident_object_name']}",
                "namespace": "{input_data['incident_namespace']}"
            }},
            "command_or_payload": {{
                "command": "describe {input_data['incident_object_kind'].lower()} {input_data['incident_object_name']} -n {input_data['incident_namespace']}"
            }},
            "expected_outcome": "Detailed resource information showing current state and events",
            "executor": "kubectl"
        }},
        {{
            "step_id": 2,
            "action_type": "KUBECTL_GET_LOGS",
            "description": "Check application logs for detailed error information",
            "target_resource": {{
                "kind": "{input_data['incident_object_kind']}",
                "name": "{input_data['incident_object_name']}",
                "namespace": "{input_data['incident_namespace']}"
            }},
            "command_or_payload": {{
                "command": "logs {input_data['incident_object_name']} -n {input_data['incident_namespace']} --tail=100"
            }},
            "expected_outcome": "Application logs showing error details and stack traces",
            "executor": "kubectl"
        }}
    ],
    "confidence_score": 0.85,
    "estimated_time_to_resolve_mins": {self._estimate_resolution_time(input_data['incident_type'], input_data['incident_reason'])},
    "severity_level": "{self._determine_severity(input_data['incident_type'], input_data['incident_reason'])}",
    "recommendations": [
        "Monitor the {input_data['incident_object_kind'].lower()} resource status",
        "Check cluster resource availability",
        "Review application configuration"
    ],
    "active_executors": ["kubectl"]
}}

IMPORTANT: 
1. Return ONLY the JSON object above, no additional text
2. Use DOUBLE QUOTES for all strings and arrays
3. Do NOT use single quotes anywhere
4. Ensure the JSON is complete and valid"""

    def _determine_severity(self, incident_type: str, reason: str) -> str:
        """Determine severity level based on incident type and reason"""
        if incident_type == "Warning":
            critical_reasons = ["ImagePullBackOff", "CrashLoopBackOff", "OOMKilled", "Failed"]
            high_reasons = ["Unhealthy", "FailedMount", "NetworkNotReady"]
            
            if any(critical in reason for critical in critical_reasons):
                return "CRITICAL"
            elif any(high in reason for high in high_reasons):
                return "HIGH"
            else:
                return "MEDIUM"
        else:  # Normal events
            return "LOW"

    def _estimate_resolution_time(self, incident_type: str, reason: str) -> int:
        """Estimate resolution time based on incident type and reason"""
        if incident_type == "Warning":
            if any(critical in reason for critical in ["CrashLoopBackOff", "OOMKilled"]):
                return 30
            elif any(medium in reason for medium in ["ImagePullBackOff", "FailedMount"]):
                return 15
            else:
                return 10
        else:  # Normal events
            return 5

    def analyze_remediation_sync(self, alert_data: Dict[str, Any], active_executors: List[str]) -> RemediationSolution:
        """
        Analyze Kubernetes alert/issue and provide single-command remediation - NO FALLBACK
        """
        try:
            alert_name = alert_data.get('alert_name', 'Unknown')
            logger.info(f"🚀 Starting remediation analysis for alert: {alert_name}")
            
            prompt = self._build_remediation_prompt(alert_data, active_executors)
            response_text = self._call_direct_openai(prompt)
            
            if not response_text:
                raise Exception("Empty response from LLM service")
            
            # Parse JSON response
            try:
                # Clean the response
                json_str = self._clean_llm_response(response_text)
                response_json = json.loads(json_str)
                
                solution = RemediationSolution(
                    issue_summary=response_json.get("issue_summary", f"Kubernetes issue: {alert_name}"),
                    suggestion=response_json.get("suggestion", "LLM-generated remediation suggestion"),
                    command=response_json.get("command", "get pods"),
                    is_executable=response_json.get("is_executable", True),
                    severity_level=response_json.get("severity_level", "MEDIUM"),
                    estimated_time_mins=response_json.get("estimated_time_mins", 5),
                    confidence_score=response_json.get("confidence_score", 0.8),
                    active_executors=response_json.get("active_executors", active_executors)
                )
                
                logger.info(f"✅ Successfully generated remediation for alert: {alert_name}")
                self._print_remediation_to_terminal(solution)
                return solution
                
            except json.JSONDecodeError as json_error:
                logger.error(f"❌ Failed to parse remediation JSON: {json_error}")
                raise Exception(f"Invalid JSON response from LLM: {json_error}")
                
        except Exception as e:
            logger.error(f"❌ Remediation analysis failed: {str(e)}")
            raise Exception(f"Remediation analysis failed: {str(e)}")

    def _build_remediation_prompt(self, alert_data: Dict[str, Any], active_executors: List[str]) -> str:
        """Build prompt for remediation analysis"""
        return f"""Analyze this Kubernetes alert and provide a single remediation command in JSON format.

ALERT DETAILS:
- Alert Name: {alert_data.get('alert_name', 'Unknown')}
- Namespace: {alert_data.get('namespace', 'default')}
- Resource: {alert_data.get('pod_name', alert_data.get('resource_name', 'unknown'))}
- Issue Details: {self._format_issue_details(alert_data)}
- Additional Context: {self._format_additional_context(alert_data)}
- Active Executors: {active_executors}

Provide a JSON response with this exact structure:
{{
    "issue_summary": "Brief technical summary of the Kubernetes problem",
    "suggestion": "Detailed explanation of what should be done and why, including technical context",
    "command": "Single kubectl command for remediation without kubectl prefix",
    "is_executable": true,
    "severity_level": "MEDIUM",
    "estimated_time_mins": 5,
    "confidence_score": 0.8,
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


# Initialize client with strict error handling - NO FALLBACK
try:
    llm_client = KubernetesLLMClient()
    logger.info("✅ LLM client initialized successfully")
except Exception as init_error:
    logger.error(f"❌ Failed to initialize LLM client: {init_error}")
    llm_client = None

def get_llm_client() -> Optional[KubernetesLLMClient]:
    """Get the global LLM client instance"""
    return llm_client

# Convenience functions with NO FALLBACK
def analyze_kubernetes_incident_sync(incident_data: Dict[str, Any], active_executors: List[str] = None) -> IncidentSolution:
    """
    Synchronous version of incident analysis - NO FALLBACK, ONLY LLM
    """
    if active_executors is None:
        active_executors = ["kubectl"]
    
    client = get_llm_client()
    if not client:
        raise Exception("LLM client not available - service initialization failed")
    
    return client.analyze_incident_sync(incident_data, active_executors)

def analyze_kubernetes_remediation_sync(alert_data: Dict[str, Any], active_executors: List[str] = None) -> RemediationSolution:
    """
    Convenience function for Kubernetes remediation analysis - NO FALLBACK, ONLY LLM
    """
    if active_executors is None:
        active_executors = ["kubectl"]
    
    client = get_llm_client()
    if not client:
        raise Exception("LLM client not available - service initialization failed")
    
    return client.analyze_remediation_sync(alert_data, active_executors)