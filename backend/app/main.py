"""
FastAPI application entry point.

Initializes the FastAPI app, configures middleware, and includes routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Startup:
        - Initialize external services (Pinecone, Redis)
        - Verify database connection
        - Load configuration

    Shutdown:
        - Close connections
        - Cleanup resources
    """
    logger.info("Starting up T&C Analysis API...")

    # Initialize Redis cache service
    try:
        app.state.cache = CacheService()
        await app.state.cache.connect()
        logger.info("✓ Redis cache connected")
    except Exception as e:
        logger.error(f"✗ Redis connection failed: {e}")
        logger.warning("Continuing without cache (degraded performance)")
        app.state.cache = None

    # Initialize Pinecone service
    try:
        app.state.pinecone = PineconeService()
        await app.state.pinecone.initialize()
        logger.info("✓ Pinecone initialized")
    except Exception as e:
        logger.error(f"✗ Pinecone initialization failed: {e}")
        app.state.pinecone = None

    # Initialize OpenAI service (with cache if available)
    try:
        app.state.openai = OpenAIService(cache_service=app.state.cache)
        logger.info("✓ OpenAI service initialized")
    except Exception as e:
        logger.error(f"✗ OpenAI initialization failed: {e}")
        app.state.openai = None

    logger.info("Startup complete!")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Close service connections
    if app.state.cache:
        await app.state.cache.disconnect()
        logger.info("✓ Redis disconnected")

    if app.state.openai:
        await app.state.openai.close()
        logger.info("✓ OpenAI service closed")

    if app.state.pinecone:
        await app.state.pinecone.close()
        logger.info("✓ Pinecone service closed")

    logger.info("Shutdown complete!")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-Powered Terms & Conditions Analysis System with Anomaly Detection",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status and version information
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "T&C Analysis API",
        "version": "1.0.0",
        "docs_url": f"{settings.API_V1_PREFIX}/docs",
    }


# Include API routers
from app.api.v1 import auth, upload, query, anomalies, compare, gpt5_analysis

app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    upload.router,
    prefix=f"{settings.API_V1_PREFIX}/documents",
    tags=["Documents"],
)

app.include_router(
    query.router,
    prefix=f"{settings.API_V1_PREFIX}/query",
    tags=["Q&A"],
)

app.include_router(
    anomalies.router,
    prefix=f"{settings.API_V1_PREFIX}/anomalies",
    tags=["Anomalies"],
)

app.include_router(
    compare.router,
    prefix=f"{settings.API_V1_PREFIX}/compare",
    tags=["Comparison"],
)

app.include_router(
    gpt5_analysis.router,
    prefix=f"{settings.API_V1_PREFIX}/gpt5",
    tags=["GPT-5 Analysis"],
)

logger.info("✓ API routers registered")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
