"""
Anomaly detection endpoints.

Provides access to detected anomalies with filtering and details.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
import logging

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.anomaly import Anomaly
from app.schemas.anomaly import (
    AnomalyResponse,
    AnomalyListResponse,
    AnomalyReportResponse,
    FeedbackRequest,
    FeedbackResponse,
    PerformanceMetrics
)
from app.core.anomaly_detector import AnomalyDetector

logger = logging.getLogger(__name__)

router = APIRouter()


# NOTE: Static routes must be defined BEFORE dynamic routes like /{document_id}
# to prevent FastAPI from matching "performance" as a document_id


@router.get(
    "/performance",
    response_model=PerformanceMetrics,
    summary="Get System Performance Metrics",
    description="""
    Get comprehensive system performance metrics for monitoring.

    **Metrics Include:**
    - Total documents analyzed
    - Total anomalies detected
    - False positive rate
    - Dismissal rate
    - Expected Calibration Error (ECE)
    - Average processing time
    - Pipeline health status

    **Health Status:**
    - `healthy`: System operating normally
    - `warning`: Some metrics need attention
    - `critical`: Immediate intervention required

    **Note:** This endpoint may require admin authentication in production.
    """,
)
async def get_performance_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get system performance metrics.

    Returns comprehensive metrics for monitoring anomaly detection quality.
    """
    logger.info(f"Performance metrics requested by user: {current_user.id}")

    try:
        # Initialize detector
        detector = AnomalyDetector()

        # Get feedback stats
        feedback_stats = detector.active_learning.get_feedback_stats()

        # Calculate aggregate metrics from database
        total_documents = db.query(func.count(Document.id)).scalar() or 0
        total_anomalies = db.query(func.count(Anomaly.id)).scalar() or 0

        # Calculate average alerts per document
        avg_alerts_per_doc = (
            total_anomalies / total_documents if total_documents > 0 else 0.0
        )

        # Calculate false positive rate from feedback
        # False positive rate = dismissals / total feedback
        false_positive_rate = feedback_stats['dismissal_rate']

        # Get ECE if calibrator is fitted
        ece = None
        if detector.confidence_calibrator.is_fitted:
            # ECE is tracked internally but not directly accessible
            # For now, return None or implement getter
            ece = None  # TODO: Add ECE getter to ConfidenceCalibrator

        # Determine health status
        # Critical: dismissal rate > 40%
        # Warning: dismissal rate > 25%
        # Healthy: dismissal rate <= 25%
        if feedback_stats['dismissal_rate'] > 0.40:
            health_status = "critical"
        elif feedback_stats['dismissal_rate'] > 0.25:
            health_status = "warning"
        else:
            health_status = "healthy"

        # Calculate average processing time
        # This would ideally come from stored metrics
        # For now, use a placeholder
        avg_processing_time = 500.0  # TODO: Track in database

        metrics = PerformanceMetrics(
            total_documents_analyzed=total_documents,
            total_anomalies_detected=total_anomalies,
            total_feedback_collected=feedback_stats['total_feedback_collected'],
            false_positive_rate=false_positive_rate,
            dismissal_rate=feedback_stats['dismissal_rate'],
            average_alerts_per_document=avg_alerts_per_doc,
            expected_calibration_error=ece,
            calibrator_fitted=feedback_stats['calibrator_fitted'],
            retrain_count=feedback_stats['retrain_count'],
            last_retrain_date=feedback_stats['last_retrain_date'],
            avg_processing_time_ms=avg_processing_time,
            pipeline_health_status=health_status
        )

        logger.info(
            f"Performance metrics: {total_documents} docs, "
            f"{total_anomalies} anomalies, "
            f"dismissal rate: {feedback_stats['dismissal_rate']:.1%}, "
            f"health: {health_status}"
        )

        return metrics

    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch performance metrics: {str(e)}"
        )


@router.post(
    "/reanalyze/{document_id}",
    response_model=AnomalyListResponse,
    summary="Re-analyze Document for Anomalies",
    description="""
    Re-run anomaly detection on an existing document.

    This will:
    1. Delete all existing anomalies for the document
    2. Re-run the full 6-stage anomaly detection pipeline
    3. Save new anomalies with updated prevalence scores

    Use this to refresh anomaly analysis after system improvements.
    """,
)
async def reanalyze_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Re-run anomaly detection on an existing document."""
    from app.api.deps import get_embedding_service, get_pinecone_service
    from app.models.clause import Clause

    logger.info(f"Re-analyzing document: {document_id}")

    # Verify document exists and user has access
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    # Get clauses for the document
    clauses = db.query(Clause).filter(Clause.document_id == document_id).all()

    if not clauses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No clauses found for this document",
        )

    # Build sections from clauses
    sections_dict: Dict[str, Any] = {}
    for clause in clauses:
        section_name = clause.section or "Unknown Section"
        if section_name not in sections_dict:
            sections_dict[section_name] = {
                "title": section_name,
                "clauses": []
            }
        sections_dict[section_name]["clauses"].append({
            "id": clause.clause_number,
            "text": clause.text
        })

    sections = list(sections_dict.values())

    # Delete existing anomalies
    deleted_count = db.query(Anomaly).filter(Anomaly.document_id == document_id).delete()
    db.commit()
    logger.info(f"Deleted {deleted_count} existing anomalies")

    # Initialize services
    embedding_service = get_embedding_service()
    pinecone_service = get_pinecone_service()
    await pinecone_service.initialize()

    # Run anomaly detection
    detector = AnomalyDetector(embedding_service, pinecone_service, db)

    company_name = "Unknown"
    if document.document_metadata:
        company_name = document.document_metadata.get("company_name",
                       document.document_metadata.get("company", "Unknown"))

    detection_result = await detector.detect_anomalies(
        document_id=document_id,
        sections=sections,
        company_name=company_name,
        service_type="general",
    )

    # Extract anomalies from detection result
    all_anomalies = (
        detection_result.get('high_severity_alerts', []) +
        detection_result.get('medium_severity_alerts', []) +
        detection_result.get('low_severity_alerts', [])
    )

    logger.info(f"Detected {len(all_anomalies)} anomalies")

    # Save new anomalies to database
    saved_anomalies = []
    for anomaly_data in all_anomalies:
        # Extract prevalence
        prevalence_value = anomaly_data.get("prevalence", 0.0)
        if isinstance(prevalence_value, dict):
            prevalence_value = prevalence_value.get("prevalence", 0.0)

        # Extract detected indicators
        detected_indicators = anomaly_data.get("detected_indicators", [])
        if not isinstance(detected_indicators, list):
            detected_indicators = []

        anomaly = Anomaly(
            document_id=document_id,
            clause_text=anomaly_data.get("clause_text", ""),
            section=anomaly_data.get("section", "Unknown"),
            clause_number=anomaly_data.get("clause_number", ""),
            severity=anomaly_data.get("severity", "medium"),
            explanation=anomaly_data.get("explanation", ""),
            consumer_impact=anomaly_data.get("consumer_impact", ""),
            recommendation=anomaly_data.get("recommendation", ""),
            risk_category=anomaly_data.get("risk_category", "general"),
            prevalence=float(prevalence_value) if prevalence_value else 0.0,
            detected_indicators=detected_indicators,
        )
        db.add(anomaly)
        saved_anomalies.append(anomaly)

    # Update document stats
    high_count = len([a for a in saved_anomalies if a.severity == "high"])
    medium_count = len([a for a in saved_anomalies if a.severity == "medium"])

    document.anomaly_count = len(saved_anomalies)
    document.risk_score = detection_result.get("overall_risk_score", 5)
    document.risk_level = "High" if high_count > 0 else "Medium" if medium_count > 2 else "Low"
    document.processing_status = "completed"

    db.commit()

    logger.info(f"Re-analysis complete: {len(saved_anomalies)} anomalies saved")

    # Build response
    severity_counts = {"high": high_count, "medium": medium_count, "low": len(saved_anomalies) - high_count - medium_count}

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
                risk_flags=a.risk_flags or [ind.get('name', ind.get('indicator', str(ind))) for ind in (a.detected_indicators or [])],
                created_at=a.created_at,
            )
            for a in saved_anomalies
        ],
        total=len(saved_anomalies),
        high_risk_count=severity_counts.get("high", 0),
        medium_risk_count=severity_counts.get("medium", 0),
        low_risk_count=severity_counts.get("low", 0),
    )


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
    severity: Optional[str] = Query(
        None, description="Filter by severity: low, medium, high"
    ),
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
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

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

    anomalies = (
        query.order_by(
            # Sort by severity: high > medium > low
            case(
                (Anomaly.severity == "high", 1),
                (Anomaly.severity == "medium", 2),
                (Anomaly.severity == "low", 3),
                else_=4,
            ),
            # Then by prevalence (rarest first)
            Anomaly.prevalence.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    logger.info(f"Found {total} anomalies (returning {len(anomalies)})")

    # Calculate statistics
    stats_query = (
        db.query(Anomaly.severity, func.count(Anomaly.id).label("count"))
        .filter(Anomaly.document_id == document_id)
        .group_by(Anomaly.severity)
        .all()
    )

    severity_counts = {severity: count for severity, count in stats_query}

    return AnomalyListResponse(
        anomalies=[
            AnomalyResponse(
                id=a.id,
                document_id=a.document_id,
                clause_text=(
                    a.clause_text[:500] + "..."
                    if len(a.clause_text) > 500
                    else a.clause_text
                ),
                section=a.section,
                clause_number=a.clause_number,
                severity=a.severity,
                explanation=a.explanation,
                prevalence=a.prevalence,
                # Use detected_indicators if risk_flags is empty (migration compatibility)
                risk_flags=a.risk_flags or [ind.get('name', ind.get('indicator', str(ind))) for ind in (a.detected_indicators or [])],
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
    document = (
        db.query(Document)
        .filter(
            Document.id == anomaly.document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

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
        # Use detected_indicators if risk_flags is empty (migration compatibility)
        risk_flags=anomaly.risk_flags or [ind.get('name', ind.get('indicator', str(ind))) for ind in (anomaly.detected_indicators or [])],
        created_at=anomaly.created_at,
    )


@router.get(
    "/report/{document_id}",
    response_model=AnomalyReportResponse,
    summary="Get Complete Anomaly Report",
    description="""
    Get a complete anomaly analysis report using the full 6-stage detection pipeline.

    **Pipeline Stages:**
    1. Multi-Method Detection (Pattern, Semantic, Statistical)
    2. Context Filtering (Industry, Service Type, Temporal)
    3. Clustering & Deduplication (ML-powered)
    4. Compound Risk Detection (Systemic patterns)
    5. Confidence Calibration (Isotonic regression)
    6. Alert Ranking & Budget (MAX_ALERTS=10)

    **Query Parameters:**
    - `user_preferences`: Optional JSON object for personalization
    - `force_reanalysis`: Skip cache and rerun full pipeline

    **Returns:**
    - Overall risk score (1-10)
    - Categorized alerts (HIGH/MEDIUM/LOW)
    - Compound risk patterns
    - Pipeline performance metrics
    """,
)
async def get_anomaly_report(
    document_id: str,
    user_preferences: Optional[str] = Query(
        None,
        description="Optional JSON object with user preferences"
    ),
    force_reanalysis: bool = Query(
        False,
        description="Force reanalysis, skip cache"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get complete anomaly report using full 6-stage pipeline.

    Provides comprehensive analysis with calibrated confidence scores,
    alert ranking, and compound risk detection.
    """
    logger.info(
        f"Anomaly report requested for document: {document_id} "
        f"(force_reanalysis={force_reanalysis})"
    )

    # Verify document access
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    try:
        # Parse user preferences if provided
        import json
        prefs = None
        if user_preferences:
            try:
                prefs = json.loads(user_preferences)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user_preferences JSON format"
                )

        # Initialize detector
        detector = AnomalyDetector()

        # Set user preferences if provided
        if prefs:
            detector.set_user_preferences(prefs)

        # Get document text content
        if not document.text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no content to analyze"
            )

        # Parse document text into clauses
        # Split by double newlines for paragraphs, or single newlines for lines
        clauses = [
            {"clause_number": str(i+1), "text": text.strip()}
            for i, text in enumerate(document.text.split('\n\n'))
            if text.strip()
        ]

        # If no clauses found with double newlines, try single newlines
        if not clauses:
            clauses = [
                {"clause_number": str(i+1), "text": text.strip()}
                for i, text in enumerate(document.text.split('\n'))
                if text.strip()
            ]

        if not clauses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No clauses found in document"
            )

        # Get metadata from document
        metadata = document.document_metadata or {}
        company_name = metadata.get('company_name', 'Unknown')
        service_type = metadata.get('document_type', 'general')

        # Get document context
        document_context = {
            'industry': metadata.get('industry'),
            'service_type': service_type,
            'is_change': False
        }

        # Convert clauses to sections format expected by detector
        sections = [
            {
                'section': f"Section {c['clause_number']}",
                'text': c['text'],
                'clause_number': c['clause_number']
            }
            for c in clauses
        ]

        # Run complete 6-stage pipeline (async method)
        logger.info(f"Running 6-stage pipeline on {len(sections)} sections")
        report = await detector.detect_anomalies(
            document_id=document_id,
            sections=sections,
            company_name=company_name,
            service_type=service_type,
            document_context=document_context
        )

        # Handle both dict and list return types
        if isinstance(report, list):
            # Convert list of anomalies to report format
            high_alerts = [a for a in report if a.get('severity') == 'high']
            medium_alerts = [a for a in report if a.get('severity') == 'medium']
            low_alerts = [a for a in report if a.get('severity') == 'low']

            total_shown = len(report)
            risk_score = sum(
                3 if a.get('severity') == 'high' else 2 if a.get('severity') == 'medium' else 1
                for a in report
            ) / max(len(report), 1) * 3.33

            logger.info(
                f"Pipeline complete: {total_shown} alerts, "
                f"risk score: {min(risk_score, 10):.1f}/10"
            )

            return {
                "high_severity_alerts": high_alerts,
                "medium_severity_alerts": medium_alerts,
                "low_severity_alerts": low_alerts,
                "overall_risk_score": min(risk_score, 10),
                "total_anomalies_detected": len(report),
                "total_alerts_shown": total_shown,
                "compound_risks": []
            }
        else:
            logger.info(
                f"Pipeline complete: {report.get('total_alerts_shown', 0)}/{report.get('total_anomalies_detected', 0)} "
                f"alerts shown, risk score: {report.get('overall_risk_score', 0):.1f}/10"
            )
            return report

    except Exception as e:
        logger.error(f"Error generating anomaly report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate anomaly report: {str(e)}"
        )


@router.post(
    "/{anomaly_id}/feedback",
    response_model=FeedbackResponse,
    summary="Submit User Feedback",
    description="""
    Submit user feedback on a detected anomaly for active learning.

    **User Actions:**
    - `helpful`: User found the anomaly helpful
    - `acted_on`: User took action based on the anomaly
    - `dismiss`: User dismissed as not important
    - `not_applicable`: Anomaly doesn't apply to user's situation

    **Active Learning:**
    - Feedback improves confidence calibration over time
    - Calibrator retrains automatically after 100 samples
    - System monitors dismissal rate for quality control

    **Returns:**
    - Success status
    - Current feedback statistics
    - Buffer progress toward next retraining
    """,
)
async def submit_feedback(
    anomaly_id: str,
    feedback: FeedbackRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Submit user feedback on an anomaly detection.

    Feedback is used for active learning to improve confidence calibration.
    """
    logger.info(f"Feedback received for anomaly: {anomaly_id}")

    # Verify anomaly exists and user has access
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly not found: {anomaly_id}"
        )

    # Verify user has access to this document
    document = (
        db.query(Document)
        .filter(
            Document.id == anomaly.document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this anomaly"
        )

    try:
        # Initialize detector (to access active learning manager)
        detector = AnomalyDetector()

        # Map user action to internal format
        # API uses: helpful, dismiss, not_applicable, acted_on
        # Internal uses: helpful, dismissed, false_positive, acted_on
        action_mapping = {
            'helpful': 'helpful',
            'dismiss': 'dismissed',
            'not_applicable': 'false_positive',
            'acted_on': 'acted_on'
        }
        internal_action = action_mapping.get(feedback.user_action)

        if not internal_action:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user action: {feedback.user_action}"
            )

        # Collect feedback
        result = detector.collect_user_feedback(
            anomaly_id=anomaly_id,
            user_action=internal_action,
            confidence_at_detection=feedback.confidence_at_detection
        )

        logger.info(
            f"Feedback collected: action={feedback.user_action}, "
            f"confidence={feedback.confidence_at_detection:.3f}"
        )

        # Log optional text feedback
        if feedback.feedback_text:
            logger.info(f"User feedback text: {feedback.feedback_text[:200]}")

        # Get current stats
        from app.schemas.anomaly import FeedbackStats
        stats = FeedbackStats(**result['feedback_stats'])

        return FeedbackResponse(
            success=result['success'],
            message=result['message'],
            feedback_stats=stats
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect feedback: {str(e)}"
        )
