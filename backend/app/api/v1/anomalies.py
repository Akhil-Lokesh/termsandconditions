"""
Anomaly detection endpoints.

Provides access to detected anomalies with filtering and details.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import logging

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.anomaly import Anomaly
from app.schemas.anomaly import AnomalyResponse, AnomalyListResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{document_id}",
    response_model=AnomalyListResponse,
    summary="Get Document Anomalies",
    description="""
    Retrieve all anomalies detected in a document with optional filtering.

    **Filters:**
    - `severity`: Filter by severity level (low, medium, high)
    - `section`: Filter by section name (partial match)
    - `skip`: Pagination offset
    - `limit`: Maximum results to return

    **Returns:**
    - List of anomalies with details
    - Statistics by severity
    - Total count and pagination info
    """,
)
async def get_anomalies(
    document_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high"),
    section: Optional[str] = Query(None, description="Filter by section name"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all anomalies for a document with optional filters.

    Anomalies are sorted by severity (high first) then prevalence (rarest first).
    """
    logger.info(f"Anomalies requested for document: {document_id}")

    # Verify document access
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    # Build query
    query = db.query(Anomaly).filter(Anomaly.document_id == document_id)

    # Apply filters
    if severity:
        query = query.filter(Anomaly.severity == severity.lower())
        logger.info(f"Filtering by severity: {severity}")

    if section:
        query = query.filter(Anomaly.section.ilike(f"%{section}%"))
        logger.info(f"Filtering by section: {section}")

    # Get total count
    total = query.count()

    # Get anomalies with pagination and sorting
    from sqlalchemy import case
    anomalies = query.order_by(
        # Sort by severity: high > medium > low
        case(
            (Anomaly.severity == "high", 1),
            (Anomaly.severity == "medium", 2),
            (Anomaly.severity == "low", 3),
            else_=4
        ),
        # Then by prevalence (rarest first)
        Anomaly.prevalence.asc(),
    ).offset(skip).limit(limit).all()

    logger.info(f"Found {total} anomalies (returning {len(anomalies)})")

    # Calculate statistics
    stats_query = db.query(
        Anomaly.severity,
        func.count(Anomaly.id).label("count")
    ).filter(
        Anomaly.document_id == document_id
    ).group_by(Anomaly.severity).all()

    severity_counts = {severity: count for severity, count in stats_query}

    return AnomalyListResponse(
        anomalies=[
            AnomalyResponse(
                id=a.id,
                document_id=a.document_id,
                clause_text=a.clause_text[:500] + "..." if len(a.clause_text) > 500 else a.clause_text,
                section=a.section,
                clause_number=a.clause_number,
                severity=a.severity,
                explanation=a.explanation,
                prevalence=a.prevalence,
                risk_flags=a.risk_flags or [],
                created_at=a.created_at,
            )
            for a in anomalies
        ],
        total=total,
        high_risk_count=severity_counts.get("high", 0),
        medium_risk_count=severity_counts.get("medium", 0),
        low_risk_count=severity_counts.get("low", 0),
    )


@router.get(
    "/detail/{anomaly_id}",
    response_model=AnomalyResponse,
    summary="Get Anomaly Details",
    description="Get full details of a specific anomaly including complete clause text.",
)
async def get_anomaly_detail(
    anomaly_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get detailed information about a specific anomaly.

    Returns full clause text (not truncated) and all metadata.
    """
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly not found: {anomaly_id}",
        )

    # Verify user has access to this document
    document = db.query(Document).filter(
        Document.id == anomaly.document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this anomaly",
        )

    logger.info(f"Anomaly detail requested: {anomaly_id}")

    return AnomalyResponse(
        id=anomaly.id,
        document_id=anomaly.document_id,
        clause_text=anomaly.clause_text,  # Full text for detail view
        section=anomaly.section,
        clause_number=anomaly.clause_number,
        severity=anomaly.severity,
        explanation=anomaly.explanation,
        prevalence=anomaly.prevalence,
        risk_flags=anomaly.risk_flags or [],
        created_at=anomaly.created_at,
    )
