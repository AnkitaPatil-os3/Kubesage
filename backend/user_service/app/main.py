from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware
from app.routes import auth_router, user_router
from app.database import create_db_and_tables
from app.consumer import start_consumers
from app.logger import logger
import uvicorn
import uuid, ssl
from app.rate_limiter import limiter, rate_limit_exceeded_handler, RateLimitExceeded
from fastapi.responses import HTMLResponse
from apscheduler.schedulers.background import BackgroundScheduler
from app.email_client import clean_expired_confirmations

app = FastAPI(title="KubeSage User Service")

# Add limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Allow frontend requests
origins = [
    "*",  # Frontend running locally   
]

# ✅ Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Set up scheduler to clean expired confirmations
# Increase the interval to avoid cleaning too frequently
scheduler = BackgroundScheduler()
scheduler.add_job(clean_expired_confirmations, 'interval', seconds=30)

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # Start message consumers
    start_consumers()
    # Start the scheduler
    scheduler.start()
    logger.info("User service started")

@app.on_event("shutdown")
async def shutdown_event():
    # Shut down the scheduler
    scheduler.shutdown()
    logger.info("User service shutting down")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True , ssl_keyfile="key.pem", ssl_certfile="cert.pem")
