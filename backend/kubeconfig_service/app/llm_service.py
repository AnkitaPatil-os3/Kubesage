import os
import json
import logging
import asyncio
from functools import partial
from typing import Optional, List, Dict, Any
from datetime import datetime
from openai import OpenAI
from app.config import settings
import re  # Add this import

logger = logging.getLogger(__name__)

class K8sLLMService:
    """Service for generating Kubernetes problem solutions using LLM"""
    
    def __init__(self):
        if not settings.LLM_ENABLED:
            raise ValueError("LLM functionality is disabled")
            
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        try:
            # FIXED: Use only the most basic parameters that are guaranteed to work
            client_params = {
                "api_key": settings.OPENAI_API_KEY
            }
            
            # Only add base_url if it exists and is not None/empty
            if hasattr(settings, 'OPENAI_BASE_URL') and settings.OPENAI_BASE_URL:
                client_params["base_url"] = settings.OPENAI_BASE_URL
            
            # Initialize with minimal parameters
            self.client = OpenAI(**client_params)
            
            # Set model with fallback
            self.model = getattr(settings, 'OPENAI_MODEL', "gpt-3.5-turbo")
            
            logger.info(f"LLM Service initialized successfully with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
        
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
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1200,
                response_format={"type": "json_object"}
            )
            
            # Check if response has content
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI API")
            
            response_content = response.choices[0].message.content.strip()
            if not response_content:
                raise ValueError("Empty response content from OpenAI API")
            
            # ENHANCED: Better JSON cleaning and parsing with multiple attempts
            try:
                # First attempt: Direct parsing
                solution_data = json.loads(response_content)
            except json.JSONDecodeError as first_error:
                logger.warning(f"First JSON parse failed for user {user_id}: {str(first_error)}")
                
                try:
                    # Second attempt: Clean and parse
                    cleaned_content = self._clean_json_response(response_content)
                    solution_data = json.loads(cleaned_content)
                    logger.info(f"JSON parsing succeeded after cleaning for user {user_id}")
                except json.JSONDecodeError as second_error:
                    logger.warning(f"Second JSON parse failed for user {user_id}: {str(second_error)}")
                    
                    try:
                        # Third attempt: More aggressive cleaning
                        # Remove all problematic escape sequences
                        ultra_cleaned = response_content
                        ultra_cleaned = re.sub(r'\\+', '\\\\', ultra_cleaned)  # Fix multiple backslashes
                        ultra_cleaned = re.sub(r'\\(?!["\\/bfnrt])', '\\\\\\\\', ultra_cleaned)  # Escape invalid escapes
                        ultra_cleaned = ultra_cleaned.replace('\\"', '"')  # Remove over-escaping
                        
                        # Try to extract just the JSON part
                        json_match = re.search(r'\{.*\}', ultra_cleaned, re.DOTALL)
                        if json_match:
                            ultra_cleaned = json_match.group(0)
                        
                        solution_data = json.loads(ultra_cleaned)
                        logger.info(f"JSON parsing succeeded after ultra cleaning for user {user_id}")
                        
                    except json.JSONDecodeError as third_error:
                        logger.error(f"All JSON parsing attempts failed for user {user_id}")
                        logger.error(f"Original response (first 500 chars): {response_content[:500]}")
                        logger.error(f"Final error: {str(third_error)}")
                        
                        # Last resort: Create a basic solution structure
                        solution_data = {
                            "solution_summary": "JSON parsing failed - manual investigation required",
                            "detailed_solution": f"The AI response could not be parsed. Original error: {error_text}",
                            "remediation_steps": [
                                {
                                    "step_id": 1,
                                    "action_type": "MANUAL_CHECK",
                                    "description": "Investigate the issue manually due to parsing error",
                                    "command": f"kubectl describe {kind.lower()} {name}" + (f" -n {namespace}" if namespace else ""),
                                    "expected_outcome": "Get detailed information about the resource"
                                }
                            ],
                            "confidence_score": 0.1,
                            "estimated_time_mins": 30,
                            "additional_notes": f"AI response parsing failed: {str(third_error)}"
                        }
            
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
        """Get the system prompt for the LLM - Updated to reduce escape sequence issues"""
        return """You are a Kubernetes expert. Analyze problems and provide JSON solutions.

IMPORTANT: Use simple text without special escape sequences. Avoid backslashes in commands when possible.

Response format:
{
    "solution_summary": "Brief solution summary",
    "detailed_solution": "Detailed explanation without special characters",
    "remediation_steps": [
        {
            "step_id": 1,
            "action_type": "KUBECTL_GET_LOGS|KUBECTL_APPLY|KUBECTL_DELETE|MANUAL_CHECK",
            "description": "Step description",
            "command": "kubectl command without complex escaping",
            "expected_outcome": "Expected result"
        }
    ],
    "confidence_score": 0.85,
    "estimated_time_mins": 15,
    "additional_notes": "Additional info"
}

Keep responses simple and avoid complex escape sequences. Use forward slashes instead of backslashes where possible."""

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
        """Clean JSON response to remove invalid control characters and fix escape sequences"""
        import re
        
        # Remove invalid control characters that break JSON parsing
        response_content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response_content)
        
        # Fix common JSON issues
        response_content = response_content.replace('\n', ' ')
        response_content = response_content.replace('\t', ' ')
        response_content = re.sub(r'\s+', ' ', response_content)  # Multiple spaces to single
        
        # FIX ESCAPE SEQUENCES - This is the main fix
        # Fix invalid escape sequences that commonly cause issues
        response_content = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', response_content)
        
        # Fix specific problematic patterns
        response_content = response_content.replace('\\"', '"')  # Fix over-escaped quotes
        response_content = response_content.replace('\\n', '\\\\n')  # Fix newline escapes
        response_content = response_content.replace('\\t', '\\\\t')  # Fix tab escapes
        response_content = response_content.replace('\\r', '\\\\r')  # Fix carriage return escapes
        
        # Fix kubectl command paths and other common issues
        response_content = re.sub(r'\\([a-zA-Z])', r'\\\\\\1', response_content)  # Fix \command patterns
        
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

    # Add this method to help debug JSON issues
    def _log_json_debug_info(self, response_content: str, error: Exception, user_id: str):
        """Log detailed information about JSON parsing failures"""
        logger.error(f"JSON Debug Info for user {user_id}:")
        logger.error(f"Response length: {len(response_content)}")
        logger.error(f"Error position: {getattr(error, 'pos', 'unknown')}")
        logger.error(f"Error message: {str(error)}")
        
        # Log problematic area around the error
        if hasattr(error, 'pos') and isinstance(error.pos, int):
            start = max(0, error.pos - 50)
            end = min(len(response_content), error.pos + 50)
            problematic_area = response_content[start:end]
            logger.error(f"Problematic area: ...{problematic_area}...")
        
        # Log first and last 200 characters
        logger.error(f"Response start: {response_content[:200]}")
        logger.error(f"Response end: {response_content[-200:]}")
