from fastapi import FastAPI
from app.routes import kubeconfig_router
from app.database import create_db_and_tables
from app.consumer import start_consumers
from app.logger import logger

app = FastAPI(title="KubeSage KubeConfig Service")

@app.on_event("startup")
async def startup_event():
    create_db_and_tables()
    # Start message consumers
    start_consumers()
    logger.info("KubeConfig service started")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(kubeconfig_router, prefix="/kubeconfig", tags=["kubeconfig"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)