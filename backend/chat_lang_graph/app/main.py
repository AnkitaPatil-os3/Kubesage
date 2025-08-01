import uuid
import json
from typing import Dict, List, Any
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from datetime import datetime

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

# Import LangGraph components
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# Local imports
from .config import settings, limiter, BASE_URL, MODEL_NAME, API_KEY
from .logger import logger
from . import database as db
from .k8s_tools import k8s_tools
from .models import ChatRequest, ChatResponse, SessionInfo, SessionHistory, ToolInfo, ToolResponse
from .services import ChatService, MessageService
from .auth import get_current_user
from .migrations import run_migrations, check_database_integrity
from .routes import router  # Import the router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting KubeSage LangGraph Chat Service...")
    
    try:
        # Initialize database
        db.create_db_and_tables()
        logger.info("✅ Database initialized successfully")
        
        # Run migrations
        run_migrations()
        logger.info("✅ Database migrations completed")
        
        # Check database integrity
        integrity = check_database_integrity()
        if integrity.get("integrity_ok"):
            logger.info("✅ Database integrity check passed")
        else:
            logger.warning(f"⚠️ Database integrity issues found: {integrity}")
        
        # Initialize LLM and agent
        global llm, agent
        llm = ChatOpenAI(
            base_url=BASE_URL, 
            model=MODEL_NAME, 
            api_key=API_KEY, 
            streaming=True
        )
        
        agent = create_react_agent(
            model=llm,
            tools=k8s_tools,
            prompt=(
                "You're an **expert Kubernetes assistant**. Provide **accurate, factual info** strictly "
                "about **Kubernetes concepts, operations, and tool outputs**. "
                "**Crucial guardrails:**\n"
                "- **Strictly Kubernetes-focused:** If a query isn't about Kubernetes, **do not engage**; simply state you **cannot assist** with that topic.\n"
                "- **No external info/speculation:** Do not provide personal opinions, speculate, or pull information from outside your defined Kubernetes domain or tool results.\n"
                "- **Deletion Safety:** For **any deletion operation**, you **MUST ask for explicit confirmation** using the exact phrase: 'yes, delete [resource type] [resource name]'. **Absolutely do NOT proceed without this precise confirmation.**\n"
                "Be concise, clear, and prioritize safety. Begin by confirming your role."
            ),
        )
        
        logger.info("✅ LLM and agent initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # Don't raise - allow service to start in degraded mode
    
    logger.info("🎉 Service startup completed")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down KubeSage LangGraph Chat Service...")
    logger.info("👋 Service shutdown completed")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="KubeSage LangGraph Chat API",
    description="API for interacting with Kubernetes via a LangGraph agent with PostgreSQL backend.",
    version="2.0.0",
    lifespan=lifespan
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate Limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Prometheus Monitoring ---
Instrumentator().instrument(app).expose(app)

# --- Include Routes ---
app.include_router(router)

# --- Global Exception Handlers ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("💥 Unhandled exception: {}", exc)
    return JSONResponse(
        status_code=500, 
        content={
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "service": "kubesage-langgraph-chat"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("⚠️ Validation error: {}", exc.errors())
    return JSONResponse(
        status_code=422, 
        content={
            "detail": exc.errors(),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# --- Root endpoint ---
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "KubeSage LangGraph Chat API",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
