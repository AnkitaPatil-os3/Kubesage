import os
import json
import logging
import asyncio
from functools import partial
from typing import Optional, List, Dict, Any
from datetime import datetime
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)

class K8sLLMService:
    """Service for generating Kubernetes problem solutions using LLM"""
    
    def __init__(self):
        if not settings.LLM_ENABLED:
            raise ValueError("LLM functionality is disabled")
            
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
            
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            timeout=600.0  # 10 minutes timeout for the client
        )
        self.model = settings.OPENAI_MODEL
        
    def _generate_solution_sync(
        self,
        error_text: str,
        kind: Optional[str] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous solution generation - will be run in executor"""
        
        try:
            logger.info(f"Generating solution for user {user_id}, resource: {kind}/{name}")
            
            # Prepare the prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_user_prompt(error_text, kind, name, namespace, context)
            
            # Call OpenAI API with 10-minute timeout
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1200,  # Increased back for better solutions
                response_format={"type": "json_object"},
                timeout=600  # 10 minutes (600 seconds) timeout
            )
            
            # Check if response has content
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI API")
            
            response_content = response.choices[0].message.content.strip()
            if not response_content:
                raise ValueError("Empty response content from OpenAI API")
            
            # Clean response content to remove invalid characters
            response_content = self._clean_json_response(response_content)
            
            # Parse the response
            try:
                solution_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for user {user_id}: {response_content}")
                raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")
            
            # Validate and structure the response
            logger.info(f"Solution generated successfully for user {user_id}")
            return self._validate_solution_response(solution_data)
            
        except Exception as e:
            logger.error(f"Error generating solution for user {user_id}: {str(e)}")
            # Return a fallback solution structure
            return {
                "solution_summary": f"Error generating solution: {str(e)}",
                "detailed_solution": "An error occurred while generating the solution. Please try again or contact support.",
                "remediation_steps": [],
                "confidence_score": 0.0,
                "estimated_time_mins": 30,
                "additional_notes": f"Error details: {str(e)}"
            }
    
    async def generate_solution(
        self,
        error_text: str,
        kind: Optional[str] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a solution for a Kubernetes problem using LLM (async)"""
        
        loop = asyncio.get_event_loop()
        
        # Use asyncio.wait_for with 10-minute timeout
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    partial(
                        self._generate_solution_sync,
                        error_text,
                        kind,
                        name,
                        namespace,
                        context,
                        user_id
                    )
                ),
                timeout=600  # 10 minutes timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"LLM request timed out after 10 minutes for user {user_id}")
            return {
                "solution_summary": "Request timed out after 10 minutes",
                "detailed_solution": "The LLM request took too long to complete. This might be due to high server load or complex analysis requirements.",
                "remediation_steps": [
                    {
                        "step_id": 1,
                        "action_type": "MANUAL_CHECK",
                        "description": "Try the analysis again or contact support",
                        "command": f"kubectl describe {kind.lower()} {name} -n {namespace}" if namespace else f"kubectl describe {kind.lower()} {name}",
                        "expected_outcome": "Get detailed information about the resource"
                    }
                ],
                "confidence_score": 0.0,
                "estimated_time_mins": 30,
                "additional_notes": "LLM request timed out after 10 minutes. Please try again."
            }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are a Kubernetes expert. Analyze problems and provide JSON solutions.

Response format:
{
    "solution_summary": "Brief solution summary",
    "detailed_solution": "Detailed explanation",
    "remediation_steps": [
        {
            "step_id": 1,
            "action_type": "KUBECTL_GET_LOGS|KUBECTL_APPLY|KUBECTL_DELETE|MANUAL_CHECK",
            "description": "Step description",
            "command": "kubectl command",
            "expected_outcome": "Expected result"
        }
    ],
    "confidence_score": 0.85,
    "estimated_time_mins": 15,
    "additional_notes": "Additional info"
}

Keep responses concise and focused. Use only valid JSON characters."""

    def _build_user_prompt(
        self,
        error_text: str,
        kind: Optional[str] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the user prompt with error details"""
        
        prompt_parts = [
            f"Please analyze and provide a solution for this Kubernetes problem:",
            f"Error: {error_text}"
        ]
        
        if kind:
            prompt_parts.append(f"Resource Kind: {kind}")
        if name:
            prompt_parts.append(f"Resource Name: {name}")
        if namespace:
            prompt_parts.append(f"Namespace: {namespace}")
            
        if context:
            prompt_parts.append(f"Additional Context: {json.dumps(context, indent=2)}")
            
        return "\n".join(prompt_parts)
    
    def _validate_solution_response(self, solution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the LLM response"""
        
        # Ensure required fields exist
        required_fields = ["solution_summary", "detailed_solution", "remediation_steps"]
        for field in required_fields:
            if field not in solution_data:
                solution_data[field] = ""
        
        # Validate remediation steps
        if not isinstance(solution_data.get("remediation_steps"), list):
            solution_data["remediation_steps"] = []
        
        # Ensure confidence score is within valid range
        confidence = solution_data.get("confidence_score", 0.5)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            solution_data["confidence_score"] = 0.5
        
        # Ensure estimated time is positive integer
        estimated_time = solution_data.get("estimated_time_mins", 30)
        if not isinstance(estimated_time, int) or estimated_time < 0:
            solution_data["estimated_time_mins"] = 30
            
        return solution_data

    def _clean_json_response(self, response_content: str) -> str:
        """Clean JSON response to remove invalid control characters"""
        import re
        
        # Remove invalid control characters that break JSON parsing
        response_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response_content)
        
        # Fix common JSON issues
        response_content = response_content.replace('\n', ' ')
        response_content = response_content.replace('\t', ' ')
        response_content = re.sub(r'\s+', ' ', response_content)  # Multiple spaces to single
        
        # Ensure proper JSON structure
        if not response_content.startswith('{'):
            start_idx = response_content.find('{')
            if start_idx != -1:
                response_content = response_content[start_idx:]
        
        if not response_content.endswith('}'):
            end_idx = response_content.rfind('}')
            if end_idx != -1:
                response_content = response_content[:end_idx + 1]
        
        return response_content

    def _fix_json_issues(self, content: str) -> str:
        """Additional JSON fixes for common issues"""
        import re
        
        # Fix specific kubectl command issues
        fixes = [
            # Fix complex JSONPath expressions
            (r'kubectl logs \$\(kubectl get pods[^)]+\)', 'kubectl logs -l app=crashloop-deployment --tail=50'),
            # Fix malformed JSONPath
            (r'\{range \.items\[[^\]]+\][^}]*\}', '$(kubectl get pods -o name | head -1)'),
            # Fix wildcard issues
            (r'crashloop-deployment-\*[^"]*', 'crashloop-deployment'),
            # Fix escape sequences
            (r'\\([^"\\\/bfnrt])', r'\1'),
            # Fix trailing commas
            (r',(\s*[}\]])', r'\1'),
        ]
        
        for pattern, replacement in fixes:
            content = re.sub(pattern, replacement, content)
        
        return content
