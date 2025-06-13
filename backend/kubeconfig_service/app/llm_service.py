import os
import json
import logging
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
            base_url=settings.OPENAI_BASE_URL
        )
        self.model = settings.OPENAI_MODEL
        
    def generate_solution(
        self,
        error_text: str,
        kind: Optional[str] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a solution for a Kubernetes problem using LLM"""
        
        try:
            # Prepare the prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_user_prompt(error_text, kind, name, namespace, context)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            solution_data = json.loads(response.choices[0].message.content)
            
            # Validate and structure the response
            return self._validate_solution_response(solution_data)
            
        except Exception as e:
            logger.error(f"Error generating solution: {str(e)}")
            # Return a fallback solution structure
            return {
                "solution_summary": f"Error generating solution: {str(e)}",
                "detailed_solution": "An error occurred while generating the solution. Please try again or contact support.",
                "remediation_steps": [],
                "confidence_score": 0.0,
                "estimated_time_mins": 30,
                "additional_notes": f"Error details: {str(e)}"
            }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """You are an expert Kubernetes administrator and troubleshooter. Your task is to analyze Kubernetes problems and provide detailed, actionable solutions.

When given a Kubernetes error, you should:
1. Identify the root cause of the problem
2. Provide a clear, step-by-step solution
3. Include specific kubectl commands where applicable
4. Estimate the time needed to resolve the issue
5. Provide a confidence score for your solution

Your response must be a valid JSON object with the following structure:
{
    "solution_summary": "Brief summary of the solution approach",
    "detailed_solution": "Detailed explanation of the problem and solution",
    "remediation_steps": [
        {
            "step_id": 1,
            "action_type": "KUBECTL_DESCRIBE|KUBECTL_GET_LOGS|KUBECTL_APPLY|KUBECTL_DELETE|KUBECTL_SCALE|KUBECTL_PATCH|MANUAL_CHECK|CONFIGURATION_CHANGE",
            "description": "What this step does and why",
            "command": "kubectl command (if applicable)",
            "expected_outcome": "What should happen after this step"
        }
    ],
    "confidence_score": 0.85,
    "estimated_time_mins": 15,
    "additional_notes": "Any additional considerations or warnings"
}

Focus on practical, safe solutions. Always suggest diagnostic steps before making changes."""

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
