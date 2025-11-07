"""
Document comparison endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.schemas.document import ComparisonRequest, ComparisonResponse
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/", response_model=ComparisonResponse)
async def compare_documents(
    comparison_data: ComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Compare multiple T&C documents side-by-side.

    Highlights differences in:
    - Cancellation policies
    - Privacy practices
    - Liability terms
    - Payment terms
    - Overall risk scores
    """
    logger.info(f"Document comparison requested by user {current_user.email}")

    # Verify all documents exist and belong to user
    documents = (
        db.query(Document)
        .filter(
            Document.id.in_(comparison_data.document_ids),
            Document.user_id == current_user.id,
        )
        .all()
    )

    if len(documents) != len(comparison_data.document_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more documents not found",
        )

    if len(documents) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 documents required for comparison",
        )

    try:
        # Get anomalies for each document
        from app.models.anomaly import Anomaly

        comparisons = []
        for doc in documents:
            anomalies = (
                db.query(Anomaly)
                .filter(Anomaly.document_id == doc.id)
                .all()
            )

            comparisons.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "company": doc.document_metadata.get("company", "Unknown"),
                "risk_score": doc.risk_score or 0.0,
                "risk_level": doc.risk_level or "Unknown",
                "anomaly_count": len(anomalies),
                "high_risk_count": sum(1 for a in anomalies if a.severity == "high"),
                "categories": list(set(a.risk_category for a in anomalies if a.risk_category)),
            })

        # Identify key differences
        differences = []

        # Compare risk scores
        risk_scores = [c["risk_score"] for c in comparisons]
        if max(risk_scores) - min(risk_scores) > 2.0:
            differences.append({
                "category": "risk_score",
                "description": f"Significant difference in risk levels: {min(risk_scores):.1f} to {max(risk_scores):.1f}",
                "documents": [c["document_id"] for c in comparisons],
            })

        # Compare anomaly counts
        anomaly_counts = [c["anomaly_count"] for c in comparisons]
        if max(anomaly_counts) > min(anomaly_counts) * 2:
            differences.append({
                "category": "anomaly_count",
                "description": f"Large difference in concerning clauses: {min(anomaly_counts)} to {max(anomaly_counts)}",
                "documents": [c["document_id"] for c in comparisons],
            })

        # Find unique risk categories
        all_categories = set()
        for c in comparisons:
            all_categories.update(c["categories"])

        for category in all_categories:
            docs_with_category = [
                c["document_id"] for c in comparisons
                if category in c["categories"]
            ]
            if len(docs_with_category) < len(documents):
                differences.append({
                    "category": category,
                    "description": f"Only {len(docs_with_category)} of {len(documents)} documents have {category} concerns",
                    "documents": docs_with_category,
                })

        # Generate recommendation
        best_doc = min(comparisons, key=lambda x: x["risk_score"])
        worst_doc = max(comparisons, key=lambda x: x["risk_score"])

        recommendation = (
            f"Based on risk analysis:\n\n"
            f"✓ BEST: {best_doc['company']} ({best_doc['filename']}) "
            f"with risk score {best_doc['risk_score']:.1f}/10\n\n"
            f"⚠️ MOST CONCERNING: {worst_doc['company']} ({worst_doc['filename']}) "
            f"with risk score {worst_doc['risk_score']:.1f}/10 and "
            f"{worst_doc['high_risk_count']} high-risk clauses\n\n"
            f"Key differences: {len(differences)} significant variations found"
        )

        return ComparisonResponse(
            documents=comparisons,
            differences=differences,
            recommendations=recommendation,
        )

    except Exception as e:
        logger.error(f"Document comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document comparison failed: {str(e)}",
        )
