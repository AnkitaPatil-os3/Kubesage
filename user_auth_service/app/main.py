from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from app.routes import auth_router, user_router
from app.database import create_db_and_tables
from app.queue import rabbitmq_client
from app.logger import logger

app = FastAPI(title="KubeSage User Authentication Service")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/users", tags=["Users"])

@app.on_event("startup")
def on_startup():
    logger.info("Starting User Authentication Service")
    create_db_and_tables()
    
    # Start RabbitMQ consumer in a separate thread
    def start_rabbitmq_consumer():
        try:
            rabbitmq_client.start_consuming()
        except Exception as e:
            logger.error(f"RabbitMQ consumer error: {str(e)}")
    
    threading.Thread(target=start_rabbitmq_consumer, daemon=True).start()

@app.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down User Authentication Service")
    rabbitmq_client.close()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        ssl_keyfile="key.pem",
        ssl_certfile="cert.pem"
    )
