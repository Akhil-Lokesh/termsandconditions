"""
Main API v1 router that combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1 import auth, upload, query, anomalies, compare

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
