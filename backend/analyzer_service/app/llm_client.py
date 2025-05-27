import requests
from app.config import settings
from app.logger import logger

def query_llm(prompt: str) -> str:
    try:
        response = requests.post(
            f"{settings.LLM_SERVICE_URL}/chat",
            json={"prompt": prompt},
            timeout=10
        )
        response.raise_for_status()
        action_plan = response.json().get("action_plan", "No action plan generated")
        logger.info(f"Successfully received action plan from LLM service")
        return action_plan
    except requests.exceptions.Timeout:
        logger.error("LLM request timed out after 10 seconds")
        return "Failed to generate action plan: Service timeout"
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to LLM service at {settings.LLM_SERVICE_URL}")
        return "Failed to generate action plan: Connection error"
    except requests.exceptions.HTTPError as e:
        logger.error(f"LLM service HTTP error: {e}")
        return f"Failed to generate action plan: HTTP error {e.response.status_code}"
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        return "Failed to generate action plan: Unknown error"
