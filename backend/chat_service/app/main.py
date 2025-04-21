from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.database import create_db_and_tables
from app.logger import logger
import time

app = FastAPI(
    title="Chat Service",
    description="Microservice for managing chat interactions with AI for Kubernetes analysis",
    version="0.1.0"
)

# Allow frontend requests
origins = [
    "http://localhost:9980",  # Frontend running locally
    "https://10.0.32.123:9980",  # Backend API
]

# ✅ Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow all origins, or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Chat Service")
    create_db_and_tables()
    logger.info("Database tables created")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Chat Service")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {
        "service": "Chat Service",
        "version": "0.1.0",
        "status": "running"
    }
