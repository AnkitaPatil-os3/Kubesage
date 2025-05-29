import requests
from app.config import settings
from app.logger import logger
 
def query_llm(prompt: str) -> str:
    try:
        response = requests.post(
            f"{settings.LLM_SERVICE_URL}/generate",
            json={"prompt": prompt},
            timeout=120,
            verify=False
        )
        response.raise_for_status()
        return response.json().get("action_plan", "No action plan generated")
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return "Failed to generate action plan"