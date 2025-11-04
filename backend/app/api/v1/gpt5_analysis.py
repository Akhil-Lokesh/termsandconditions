"""
GPT-5 Two-Stage Analysis API Endpoints.

Provides endpoints for running GPT-5 two-stage analysis on T&C documents.
Replaces the old anomaly detection system with cost-optimized cascade.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.anomaly import Anomaly
from app.models.analysis_log import AnalysisLog
from app.services.gpt5_two_stage_orchestrator import GPT5TwoStageOrchestrator, AnalysisResult
from app.schemas.document import DocumentResponse
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.post(
    "/documents/{document_id}/analyze",
    response_model=dict,
    summary="Run GPT-5 Two-Stage Analysis",
    description="""
    Analyze a T&C document using the GPT-5 two-stage cascade system.

    **Two-Stage Process:**
    1. Stage 1 (GPT-5-Nano): Fast classification ($0.0006/doc)
    2. Stage 2 (GPT-5): Deep analysis if confidence < 0.55 ($0.015/doc)

    **Expected Cost:** ~$0.0039/doc average (73% savings vs single-stage)

    **Returns:** Complete analysis with anomalies, risk score, and cost breakdown
    """
)
async def analyze_document_gpt5(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Run GPT-5 two-stage analysis on a document.

    Replaces old anomaly detection with cost-optimized cascade analysis.
    """
    logger.info(f"GPT-5 analysis requested for document {document_id} by user {current_user.email}")

    # Check document exists and belongs to user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get document text
    if not document.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no text content"
        )

    # Extract metadata
    company_name = "Unknown"
    industry = "general"
    if document.document_metadata:
        company_name = document.document_metadata.get("company", "Unknown")
        # TODO: Auto-detect industry from metadata or document content

    # Run two-stage analysis
    try:
        orchestrator = GPT5TwoStageOrchestrator()

        result = await orchestrator.analyze_document(
            document_text=document.text,
            document_id=document_id,
            company_name=company_name,
            industry=industry
        )

        logger.info(
            f"Analysis complete for {document_id}: "
            f"stage={result.stage}, risk={result.overall_risk}, "
            f"confidence={result.confidence:.2f}, cost=${result.cost:.6f}"
        )

        # Save analysis log
        analysis_log = _create_analysis_log(result, current_user.id, company_name, industry)
        db.add(analysis_log)

        # Save anomalies to database
        anomalies_saved = _save_anomalies(db, document_id, result.clauses)

        # Update document with results
        document.anomaly_count = len(anomalies_saved)
        document.risk_score = _convert_risk_to_score(result.overall_risk)
        document.risk_level = result.overall_risk
        document.processing_status = "completed"

        db.commit()

        logger.info(
            f"Saved {len(anomalies_saved)} anomalies and analysis log for {document_id}"
        )

        # Return comprehensive response
        return {
            "document_id": document_id,
            "analysis": result.to_dict(),
            "anomalies": [a.to_dict() for a in anomalies_saved[:10]],  # Top 10
            "anomaly_count": len(anomalies_saved),
            "risk_score": document.risk_score,
            "risk_level": document.risk_level,
            "cost_breakdown": {
                "stage1_cost": result.stage1_result.get("cost") if result.stage1_result else 0,
                "stage2_cost": result.stage2_result.get("cost") if result.stage2_result else 0,
                "total_cost": result.cost,
                "savings_vs_single_stage": round(0.015 - result.cost, 6)
            },
            "metrics": {
                "stage_reached": result.stage,
                "escalated": result.escalated,
                "processing_time": result.processing_time,
                "confidence": result.confidence
            }
        }

    except Exception as e:
        logger.error(f"GPT-5 analysis failed for {document_id}: {e}", exc_info=True)

        # Update document status
        document.processing_status = "analysis_failed"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get(
    "/analytics/cost-summary",
    response_model=dict,
    summary="Get Cost Analytics",
    description="Get cost and performance analytics for GPT-5 two-stage system"
)
async def get_cost_analytics(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get cost analytics for user's analyses.

    Shows cost savings, escalation rate, and performance metrics.
    """
    # Get recent analysis logs for user
    logs = db.query(AnalysisLog).filter(
        AnalysisLog.user_id == current_user.id
    ).order_by(AnalysisLog.created_at.desc()).limit(limit).all()

    if not logs:
        return {
            "total_analyses": 0,
            "total_cost": 0.0,
            "average_cost": 0.0,
            "escalation_rate": 0.0,
            "total_savings": 0.0
        }

    # Calculate metrics
    total_cost = sum(log.total_cost for log in logs)
    escalations = sum(1 for log in logs if log.escalated)
    escalation_rate = escalations / len(logs) if logs else 0
    average_cost = total_cost / len(logs) if logs else 0

    # Calculate savings vs single-stage
    single_stage_cost = 0.015 * len(logs)
    total_savings = single_stage_cost - total_cost

    # Breakdown by stage
    stage1_only = sum(1 for log in logs if log.stage_reached == 1)
    stage2_reached = sum(1 for log in logs if log.stage_reached == 2)

    return {
        "total_analyses": len(logs),
        "total_cost": round(total_cost, 4),
        "average_cost_per_document": round(average_cost, 6),
        "escalation_rate": round(escalation_rate * 100, 1),  # As percentage
        "total_savings_vs_single_stage": round(total_savings, 4),
        "percent_savings": round((total_savings / single_stage_cost) * 100, 1) if single_stage_cost > 0 else 0,
        "stage_distribution": {
            "stage1_only": stage1_only,
            "stage2_escalated": stage2_reached
        },
        "average_processing_time": round(
            sum(log.total_processing_time for log in logs) / len(logs), 2
        ) if logs else 0,
        "target_metrics": {
            "target_cost": 0.0039,
            "target_escalation_rate": 24.0,
            "cost_vs_target": round(((average_cost - 0.0039) / 0.0039) * 100, 1) if logs else 0
        }
    }


@router.get(
    "/documents/{document_id}/analysis-history",
    response_model=List[dict],
    summary="Get Analysis History",
    description="Get all analysis runs for a document"
)
async def get_analysis_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all analysis runs for a specific document."""
    # Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get analysis logs
    logs = db.query(AnalysisLog).filter(
        AnalysisLog.document_id == document_id
    ).order_by(AnalysisLog.created_at.desc()).all()

    return [log.to_dict() for log in logs]


def _create_analysis_log(
    result: AnalysisResult,
    user_id: str,
    company_name: str,
    industry: str
) -> AnalysisLog:
    """Create analysis log from orchestrator result."""
    # Count anomalies by severity
    high_count = len([c for c in result.clauses if c.get("risk_level") == "high"])
    medium_count = len([c for c in result.clauses if c.get("risk_level") == "medium"])
    low_count = len([c for c in result.clauses if c.get("risk_level") == "low"])

    return AnalysisLog(
        id=str(uuid.uuid4()),
        document_id=result.document_id,
        user_id=user_id,
        stage_reached=result.stage,
        escalated=result.escalated,

        # Stage 1
        stage1_confidence=result.stage1_result.get("confidence") if result.stage1_result else None,
        stage1_risk=result.stage1_result.get("overall_risk") if result.stage1_result else None,
        stage1_cost=result.stage1_result.get("cost") if result.stage1_result else None,
        stage1_processing_time=result.stage1_result.get("processing_time") if result.stage1_result else None,
        stage1_result=result.stage1_result,

        # Stage 2
        stage2_confidence=result.stage2_result.get("confidence") if result.stage2_result else None,
        stage2_risk=result.stage2_result.get("overall_risk") if result.stage2_result else None,
        stage2_cost=result.stage2_result.get("cost") if result.stage2_result else None,
        stage2_processing_time=result.stage2_result.get("processing_time") if result.stage2_result else None,
        stage2_result=result.stage2_result,

        # Final
        final_risk=result.overall_risk,
        final_confidence=result.confidence,
        total_cost=result.cost,
        total_processing_time=result.processing_time,

        # Anomalies
        anomaly_count=len(result.clauses),
        high_risk_count=high_count,
        medium_risk_count=medium_count,
        low_risk_count=low_count,

        # Metadata
        company_name=company_name,
        industry=industry
    )


def _save_anomalies(db: Session, document_id: str, clauses: List[dict]) -> List[Anomaly]:
    """Save detected anomalies to database."""
    anomalies = []

    for clause_data in clauses:
        # Only save problematic clauses
        if clause_data.get("classification") in ["ANOMALY", "FLAGGED", "PROBLEMATIC", "UNUSUAL"]:
            anomaly = Anomaly(
                id=str(uuid.uuid4()),
                document_id=document_id,
                section=clause_data.get("section", "Unknown"),
                clause_number=clause_data.get("clause_id", ""),
                clause_text=clause_data.get("legal_reasoning", clause_data.get("reason", ""))[:5000],  # Truncate if too long
                severity=clause_data.get("risk_level", "medium"),
                explanation=clause_data.get("legal_reasoning", clause_data.get("reason", "")),
                consumer_impact=clause_data.get("consumer_impact", ""),
                recommendation=clause_data.get("recommendation", ""),
                risk_category=clause_data.get("risk_category", "other"),
                prevalence=0.0,  # GPT-5 doesn't calculate prevalence
                detected_indicators=[]
            )
            anomalies.append(anomaly)

    # Bulk save
    if anomalies:
        db.bulk_save_objects(anomalies)

    return anomalies


def _convert_risk_to_score(risk_level: str) -> float:
    """Convert risk level to numeric score (1-10)."""
    mapping = {
        "low": 2.0,
        "medium": 5.5,
        "high": 8.5
    }
    return mapping.get(risk_level, 5.0)
