from fastapi import FastAPI
from app.routes import auth_router, user_router
from app.database import create_db_and_tables
from app.consumer import start_consumers
from app.logger import logger
import uvicorn

app = FastAPI(title="KubeSage User Service")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # Start message consumers
    start_consumers()
    logger.info("User service started")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/users", tags=["users"])

def start_rabbitmq_consumer():
    global consumer_running
    if consumer_running:
        return
    
    consumer_running = True
    try:
        logger.info("Starting to consume messages")
        rabbitmq_client.start_consuming()
    except Exception as e:
        logger.error(f"RabbitMQ consumer error: {str(e)}")
        consumer_running = False
        time.sleep(5)  # Prevent rapid reconnection attempts
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)