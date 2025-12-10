"""
FastAPI Backend Application
"""
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from backend.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="대구 공공데이터 시각화 앱 Backend API",
    description="FastAPI 기반 백엔드 서버 API",
    version="1.3.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# T087: Add request/response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all HTTP requests and responses with timestamps and duration.
    """
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status={response.status_code} Duration={duration:.3f}s"
    )

    return response


# T090: Startup event - pre-load model and verify database
@app.on_event("startup")
async def startup_event():
    """
    Execute startup tasks:
    - Pre-load ECLO model
    - Verify database connection
    """
    logger.info("=" * 50)
    logger.info("Starting backend application...")
    logger.info("=" * 50)

    # Pre-load ECLO model
    try:
        from backend.ml.model_loader import ModelLoader
        model_loader = ModelLoader()
        model = model_loader.get_model()
        logger.info("✓ ECLO model pre-loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to pre-load ECLO model: {str(e)}")
        # Don't raise - allow app to start even if model fails

    # Verify database connection
    try:
        from backend.db.session import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("✓ Database connection verified")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        # Don't raise - allow app to start for debugging

    logger.info("=" * 50)
    logger.info("Backend application startup complete")
    logger.info("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Execute cleanup tasks on shutdown.
    """
    logger.info("Shutting down backend application...")


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns service status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Include routers
from backend.api.routes import prediction, chat, datasets

app.include_router(prediction.router, prefix="/api", tags=["prediction"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
