"""
FastAPI application entry point.

Initializes the FastAPI app, configures middleware, and includes routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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


# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    FAIL-FAST STRATEGY:
        - Redis (optional): Continues with warning if unavailable
        - Pinecone (required): Fails startup if unavailable
        - OpenAI (required): Fails startup if unavailable

    This prevents silent failures that cause crashes in endpoints.
    """
    logger.info("Starting up T&C Analysis API...")

    # Track initialization failures
    init_failures = []

    # Initialize Redis cache service (OPTIONAL - can run without)
    try:
        app.state.cache = CacheService()
        await app.state.cache.connect()
        logger.info("✓ Redis cache connected")
    except Exception as e:
        logger.warning(f"✗ Redis connection failed: {e}")
        logger.warning("Continuing without cache (degraded performance)")
        app.state.cache = None

    # Initialize Pinecone service (REQUIRED)
    try:
        app.state.pinecone = PineconeService()
        await app.state.pinecone.initialize()
        logger.info("✓ Pinecone initialized")
    except Exception as e:
        logger.error(f"✗ Pinecone initialization failed: {e}")
        init_failures.append(f"Pinecone: {e}")
        app.state.pinecone = None

    # Initialize OpenAI service (REQUIRED)
    try:
        app.state.openai = OpenAIService(cache_service=app.state.cache)
        # Test with a simple embedding to verify API key works
        test_embedding = await app.state.openai.create_embedding("test")
        logger.info("✓ OpenAI service initialized and tested")
    except Exception as e:
        logger.error(f"✗ OpenAI initialization failed: {e}")
        init_failures.append(f"OpenAI: {e}")
        app.state.openai = None

    # FAIL FAST if required services failed
    if init_failures:
        error_msg = "Critical services failed to initialize:\n" + "\n".join(
            f"  - {err}" for err in init_failures
        )
        logger.error(error_msg)
        logger.error("API cannot start. Fix configuration and restart.")
        logger.error(
            "Check: 1) API keys in .env, 2) Network connectivity, 3) Service status"
        )
        raise RuntimeError(error_msg)

    logger.info("✓ All services initialized successfully!")

    yield

    # Shutdown
    logger.info("Shutting down...")

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

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Health check endpoints
@app.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        dict: Status and version information
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/services")
async def health_check_services():
    """
    Detailed health check for all services.

    Returns service availability status. Use this to verify:
    - API is accepting requests
    - Required services (OpenAI, Pinecone) are operational
    - Optional services (Redis cache) are available

    Returns:
        dict: Service health status and availability
    """
    from fastapi import Request

    # Note: app.state is available via request context in route handlers
    # Using app directly since we're in the same module
    services = {
        "openai": app.state.openai is not None,
        "pinecone": app.state.pinecone is not None,
        "cache": app.state.cache is not None,
    }

    all_required_healthy = services["openai"] and services["pinecone"]

    return {
        "status": "healthy" if all_required_healthy else "degraded",
        "services": services,
        "message": (
            "All required services operational"
            if all_required_healthy
            else "Some required services unavailable"
        ),
        "details": {
            "openai": "✓ Connected" if services["openai"] else "✗ Unavailable",
            "pinecone": "✓ Connected" if services["pinecone"] else "✗ Unavailable",
            "cache": (
                "✓ Connected"
                if services["cache"]
                else "○ Optional (running without cache)"
            ),
        },
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
