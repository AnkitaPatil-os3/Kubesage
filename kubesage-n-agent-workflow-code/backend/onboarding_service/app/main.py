from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logger import logger
from app.database import engine
from app.models import Base
from app.routes import router
from app.rabbitmq import connect_to_rabbitmq, connection

app = FastAPI(
    title="Onboarding Service",
    description="Handles cluster onboarding and agent management",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    connect_to_rabbitmq()
    logger.info("Onboarding Service started")

@app.on_event("shutdown")
async def shutdown_event():
    global connection
    if connection and not connection.is_closed:
        connection.close()
    logger.info("Onboarding Service stopped")
