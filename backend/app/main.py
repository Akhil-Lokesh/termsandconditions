"""
FastAPI application entry point.

Initializes the FastAPI app, configures middleware, and includes routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.claude_service import ClaudeService
from app.services.embedding_service import EmbeddingService
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

    FAIL-FAST STRATEGY:
        - Redis (optional): Continues with warning if unavailable
        - Pinecone (required): Fails startup if unavailable
        - Claude (required): Fails startup if unavailable
        - Embeddings (required): Fails startup if unavailable

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

    # Initialize Claude service (REQUIRED - for LLM completions)
    try:
        app.state.claude = ClaudeService(cache_service=app.state.cache)
        # Test with a simple completion to verify API key works
        test_response = await app.state.claude.create_completion("Say 'ok'", max_tokens=10)
        logger.info("✓ Claude service initialized and tested")
    except Exception as e:
        logger.error(f"✗ Claude initialization failed: {e}")
        init_failures.append(f"Claude: {e}")
        app.state.claude = None

    # Initialize local embedding service (REQUIRED)
    try:
        app.state.embedding = EmbeddingService()
        await app.state.embedding.initialize()
        # Test with a simple embedding
        test_embedding = await app.state.embedding.create_embedding("test")
        logger.info(f"✓ Local embedding service initialized ({len(test_embedding)} dimensions)")
    except Exception as e:
        logger.error(f"✗ Embedding service initialization failed: {e}")
        init_failures.append(f"Embedding: {e}")
        app.state.embedding = None

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

    # Embedding service doesn't need explicit closing
    logger.info("✓ Embedding service closed")

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Add ProxyHeadersMiddleware so X-Forwarded-For from trusted proxies is used
# for rate limiting. trusted_hosts restricts which upstream IPs are trusted.
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
trusted_proxy = getattr(settings, "TRUSTED_PROXY_IPS", "127.0.0.1")
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_proxy)

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
    - Required services (Embedding, Pinecone, Claude) are operational
    - Optional services (Redis cache) are available

    Returns:
        dict: Service health status and availability
    """
    from fastapi import Request

    # Note: app.state is available via request context in route handlers
    # Using app directly since we're in the same module
    services = {
        "embedding": app.state.embedding is not None,
        "pinecone": app.state.pinecone is not None,
        "claude": app.state.claude is not None,
        "cache": app.state.cache is not None,
    }

    all_required_healthy = services["embedding"] and services["pinecone"] and services["claude"]

    return {
        "status": "healthy" if all_required_healthy else "degraded",
        "services": services,
        "message": (
            "All required services operational"
            if all_required_healthy
            else "Some required services unavailable"
        ),
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
from app.api.v1 import auth, upload, query, anomalies, compare

if settings.DEBUG or settings.ENVIRONMENT == "development":
    from app.api.v1 import debug

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

if settings.DEBUG or settings.ENVIRONMENT == "development":
    app.include_router(
        debug.router,
        prefix=f"{settings.API_V1_PREFIX}/debug",
        tags=["Debug"],
    )

logger.info("✓ API routers registered")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
