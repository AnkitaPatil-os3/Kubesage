from fastapi import FastAPI
from app.routes import kubeconfig_router
from app.database import create_db_and_tables
from app.consumer import start_consumers
from app.logger import logger
from fastapi.middleware.cors import CORSMiddleware  # Import CORSMiddleware


app = FastAPI(title="KubeSage KubeConfig Service")

# Allow frontend requests
origins = [
    "http://localhost:9980",  # Frontend running locally
    "https://10.0.34.168:8005", # If using HTTPS locally
    "https://10.0.34.168:9980",
    "https://localhost:9980"  # Backend API
]

# ✅ Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow all origins, or specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True ,  ssl_keyfile="key.pem", ssl_certfile="cert.pem")




    