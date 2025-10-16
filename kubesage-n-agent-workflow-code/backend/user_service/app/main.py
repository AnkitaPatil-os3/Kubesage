import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from sqlmodel import SQLModel, Session, select
from datetime import datetime, timedelta, UTC
from app.database import SessionLocal, engine
import secrets
from app.routes import auth_router, user_router, api_key_router, license_router
from app.consumer import start_consumers
from app.logger import logger
from app.background_tasks import cleanup_expired_tokens_task, cleanup_inactive_sessions_task
from app.models import User, License
from app.auth import get_password_hash

background_tasks = []


app = FastAPI(
    title="User Service API",
    description="Enhanced user authentication with multi-session support",
    version="2.0.0",
)

# Add middleware configuration
WHITELIST_PATHS = [
    "/api/v1.0/auth/token",
    "/api/v1.0/users/me",
    "/api/v1.0/health",
    "/api/v1.0/license/status",
    "/api/v1.0/license/refresh",
    "/docs",
    "/openapi.json",
    "/redoc"
]


@app.middleware("http")
async def verify_license(request: Request, call_next):
    current_path = request.url.path
    
    # Allow whitelisted paths without license check
    if current_path in WHITELIST_PATHS:
        return await call_next(request)
    
    try:
        # Get database session
        db = SessionLocal()
        try:
            # Check if any active and non-expired license exists
            statement = select(License).where(
                License.is_active == True,
                License.expires_at > datetime.now(UTC)
            )
            license = db.exec(statement).first()
            
            if not license:
                logger.warning(f"License invalid/expired - blocking access to {current_path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "message": "Your license key is expired or invalid. Please contact your administrator.",
                        "error": "LICENSE_EXPIRED",
                        "path": current_path
                    }
                )
            
            # Log successful license validation
            logger.debug(f"License valid - allowing access to {current_path}")
            response = await call_next(request)
            return response
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error checking license for path {current_path}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"Error checking license: {str(e)}"}
        )


# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting application initialization...")
        
        # Create tables first
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created")
        
        # Initialize default data
        db = SessionLocal()
        try:
            # Check if a valid license already exists
            existing_license = db.exec(
                select(License).where(
                    License.is_active == True,
                    License.expires_at > datetime.now(UTC)
                )
            ).first()

            if not existing_license:
                # Create default license only if no valid license exists
                logger.info("Creating default license...")
                default_license = License(
                    license_key=f"KS-{secrets.token_hex(16)}",
                    expires_at=datetime.now(UTC) + timedelta(days=30),
                    is_active=True,
                    created_by="system"
                )
                db.add(default_license)
                db.commit()
                db.refresh(default_license)
                logger.info("Default license created")
            else:
                logger.info("Valid license already exists, skipping default license creation")

        finally:
            db.close()
        
        # Start consumers
        start_consumers()
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    

@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Routers
# app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# app.include_router(user_router, prefix="/users", tags=["Users"])
# app.include_router(api_key_router, prefix="/api-keys", tags=["API Keys"])
# app.include_router(license_router, prefix="/api", tags=["License"])


app.include_router(auth_router, prefix="/api/v1.0/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/api/v1.0/users", tags=["Users"])
app.include_router(api_key_router, prefix="/api/v1.0/api-keys", tags=["API Keys"])  
app.include_router(license_router, prefix="/api/v1.0", tags=["License"])
