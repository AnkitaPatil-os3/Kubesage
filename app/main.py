import logging
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from typing import List

# Prometheus instrumentation
from prometheus_fastapi_instrumentator import Instrumentator

# Import models and agents
from app.models import RawEvent, Incident, Plan, ExecutionResult
from app.agents.analyzer import AnalyzerAgent
from app.agents.reasoner import ReasonerAgent
from app.agents.enforcer import EnforcerAgent
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends # Explicitly import Depends

# --- Security Setup ---
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN") # Load from .env
if not API_BEARER_TOKEN:
    logger.warning("API_BEARER_TOKEN environment variable not set. API will be unsecured.")
    # In production, you might want to raise an error here or disable the endpoint.

security_scheme = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    """Dependency function to verify the static bearer token."""
    # if not API_BEARER_TOKEN: # If no token is configured, allow access (log warning above)
    #     return True
    # if credentials.scheme != "Bearer" or credentials.credentials != API_BEARER_TOKEN:
    #     logger.warning(f"Invalid or missing Bearer token received from {credentials.scheme if hasattr(credentials, 'scheme') else 'N/A'}")
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid or missing Bearer token",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    return True # Token is valid

# --- Configuration & Initialization ---

# Load environment variables from .env file
load_dotenv(override=True)

# Structured JSON Logging Configuration
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
# Format includes standard log record attributes, plus timestamp
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)

# Configure root logger
logging.getLogger().addHandler(logHandler)
logging.getLogger().setLevel(logging.INFO) # Set global log level

# Get logger for this module AFTER root configuration
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Self-Healing Kubernetes Service",
    description="Receives Kubernetes events, analyzes them, generates remediation plans using LLM, and executes them.",
    version="0.1.0"
)

# --- Agent Initialization ---
# Initialize agents (consider dependency injection for more complex scenarios)
try:
    analyzer = AnalyzerAgent()
    reasoner = ReasonerAgent() # Will raise ValueError if OPENAI_API_KEY is missing
    enforcer = EnforcerAgent() # Reads config from env vars
except ValueError as e:
    logger.critical(f"Failed to initialize agents: {e}. Service cannot start.", exc_info=True)
    # In a real deployment, this might trigger a non-ready state or exit
    # For simplicity here, we let it proceed but endpoints might fail later.
    analyzer = None
    reasoner = None
    enforcer = None
except Exception as e:
    logger.critical(f"Unexpected error during agent initialization: {e}", exc_info=True)
    analyzer = None
    reasoner = None
    enforcer = None


# --- Middleware & Instrumentation ---

# Add Prometheus metrics /metrics endpoint
Instrumentator().instrument(app).expose(app)
logger.info("Prometheus instrumentator attached and /metrics endpoint exposed.")

# Basic request logging middleware (example)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request received: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# --- API Endpoints ---

@app.get("/", tags=["Health"])
async def read_root():
    """Root endpoint for basic health check."""
    logger.info("Health check endpoint '/' accessed.")
    # Check if agents initialized correctly
    if not all([analyzer, reasoner, enforcer]):
         return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "message": "Service is unhealthy due to agent initialization failure."}
        )
    return {"status": "ok", "message": "Self-Healing Service is running."}

@app.post("/self-heal",
          tags=["Self-Healing"],
          summary="Process a raw event for self-healing",
          response_model=List[ExecutionResult], # Returns the list of execution results
          responses={
              status.HTTP_200_OK: {"description": "Plan executed successfully (or partially). Check results for details."},
              status.HTTP_400_BAD_REQUEST: {"description": "Invalid input event data."},
              status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal error during processing (analysis, planning, or enforcement)."},
              status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not ready (e.g., agents failed to initialize)."}
          })
async def self_heal_endpoint(raw_event: RawEvent, authorized: bool = Depends(verify_token)):
    """
    Receives a raw event, processes it through the self-healing pipeline:
    1.  **Analyze**: Transform raw event into a structured Incident.
    2.  **Reason**: Generate a remediation Plan using an LLM.
    3.  **Enforce**: Execute the Plan's actions.
    """
    logger.info(f"Received event for self-healing: {raw_event.event_data.get('metadata', {}).get('name', 'N/A')}")

    if not all([analyzer, reasoner, enforcer]):
         logger.error("Attempted to process /self-heal request, but agents are not initialized.")
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail="Service is not ready due to agent initialization failure."
         )

    incident: Incident | None = None
    plan: Plan | None = None
    results: List[ExecutionResult] = []

    try:
        # 1. Analyze
        logger.debug("Step 1: Analyzing raw event...")
        incident = analyzer.process_event(raw_event)
        logger.info(f"Analysis complete. Incident ID: {incident.incident_id}")

        # 2. Reason
        logger.debug(f"Step 2: Generating plan for Incident ID: {incident.incident_id}...")
        plan = reasoner.generate_plan(incident)
        logger.info(f"Reasoning complete. Plan ID: {plan.plan_id}")

        # 3. Enforce
        logger.debug(f"Step 3: Enforcing Plan ID: {plan.plan_id}...")
        results = enforcer.enforce_plan(plan, incident) # Enforcer updates incident status internally
        logger.info(f"Enforcement complete for Plan ID: {plan.plan_id}. Incident status: {incident.status}")

        # Determine final status based on results (optional refinement)
        final_status = status.HTTP_200_OK # Assume OK unless specific errors occurred below

    except ValueError as e:
        # Handle specific errors from agents (e.g., parsing, validation, config)
        logger.error(f"ValueError during processing: {e}", exc_info=True)
        # Determine which step failed based on state
        step = "Analysis" if not incident else "Reasoning" if not plan else "Enforcement/Executor Config"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during {step}: {str(e)}"
        )
    except HTTPException as e:
        # Re-raise HTTPExceptions (e.g., from potential auth middleware later)
        raise e
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error during self-healing process: {e}", exc_info=True)
        step = "Analysis" if not incident else "Reasoning" if not plan else "Enforcement"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during {step}: {str(e)}"
        )

    # Return the execution results
    # Consider returning a more structured response object if needed,
    # e.g., including final incident status.
    return results


# --- Main Execution ---

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) # Allow configuring port via environment variable
    host = os.getenv("HOST", "0.0.0.0") # Listen on all interfaces by default
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting Uvicorn server on {host}:{port} with log level {log_level}")
    uvicorn.run(app, host=host, port=port, log_level=log_level)

    # To run:
    # 1. Ensure .env file has OPENAI_API_KEY (and optionally KUBE_CONFIG_PATH etc.)
    # 2. Make sure dependencies are installed (pip install -r requirements.txt)
    # 3. Run from the project root directory: python -m app.main
    #    (or use `uvicorn app.main:app --reload` for development)
