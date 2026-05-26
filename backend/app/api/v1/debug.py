"""
Debug endpoints for anomaly detection troubleshooting.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Any
import logging
import numpy as np

from app.api.deps import get_db, get_current_active_user, get_embedding_service, get_pinecone_service
from app.models.user import User
from app.models.document import Document
from app.models.clause import Clause
from app.core.anomaly_detector import AnomalyDetector
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)


def convert_numpy_types(obj: Any) -> Any:
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

router = APIRouter()


@router.get("/detection-status")
async def get_detection_status(
    current_user: User = Depends(get_current_active_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    db: Session = Depends(get_db),
):
    """
    Get the status of all anomaly detection components.
    """
    detector = AnomalyDetector(
        embedding_service=embedding_service,
        pinecone_service=pinecone_service,
        db=db
    )
    
    status = {
        "pattern_detector": {
            "available": True,  # Always available
            "risk_indicators_loaded": detector.risk_indicators is not None,
        },
        "semantic_detector": {
            "enabled": detector.enable_semantic,
            "available": detector.semantic_anomaly_detector.is_available if detector.semantic_anomaly_detector else False,
            "model_name": detector.semantic_anomaly_detector.model_name if detector.semantic_anomaly_detector else None,
            "threshold": detector.semantic_anomaly_detector.similarity_threshold if detector.semantic_anomaly_detector else None,
        },
        "statistical_detector": {
            "enabled": detector.enable_statistical,
            "is_fitted": detector.statistical_detector.is_fitted if detector.statistical_detector else False,
        },
        "method_weights": detector.method_weights,
        "thresholds": {
            "stage2_confidence": 0.25,  # From constants
            "stage2_risk_score": 3.0,
            "semantic_similarity": 0.45,
        }
    }
    
    return status


@router.get("/test-clause")
async def test_clause_detection(
    clause_text: str = Query(..., max_length=5000, description="Clause text to test"),
    current_user: User = Depends(get_current_active_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    db: Session = Depends(get_db),
):
    """
    Test anomaly detection on a single clause.
    """
    detector = AnomalyDetector(
        embedding_service=embedding_service,
        pinecone_service=pinecone_service,
        db=db
    )
    
    # Run multi-stage detection
    result = await detector._run_multi_stage_detection(
        clause_text=clause_text,
        clause_dict={'text': clause_text, 'section': 'Test'},
        service_type="general"
    )
    
    # Convert numpy types for JSON serialization
    return convert_numpy_types({
        "clause_text": clause_text[:200] + "..." if len(clause_text) > 200 else clause_text,
        "detections": result['detections'],
        "method_confidences": result['method_confidences'],
        "stage1_confidence": result['stage1_confidence'],
        "proceed_to_stage2": result['proceed_to_stage2'],
        "flags": result['flags'],
        "adaptive_weights": result.get('adaptive_weights', {}),
        "available_methods": result.get('available_methods', {}),
    })


@router.get("/test-document/{document_id}")
async def test_document_detection(
    document_id: str,
    max_clauses: int = Query(5, ge=1, le=50, description="Max clauses to test"),
    current_user: User = Depends(get_current_active_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    db: Session = Depends(get_db),
):
    """
    Test anomaly detection on clauses from a document.
    """
    # Get document
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get clauses
    clauses = db.query(Clause).filter(
        Clause.document_id == document_id
    ).limit(max_clauses).all()
    
    if not clauses:
        raise HTTPException(status_code=404, detail="No clauses found")
    
    detector = AnomalyDetector(
        embedding_service=embedding_service,
        pinecone_service=pinecone_service,
        db=db
    )
    
    results = []
    for clause in clauses:
        result = await detector._run_multi_stage_detection(
            clause_text=clause.text,
            clause_dict={'text': clause.text, 'section': clause.section},
            service_type="general"
        )
        
        results.append({
            "clause_number": clause.clause_number,
            "section": clause.section,
            "text_preview": clause.text[:100] + "..." if len(clause.text) > 100 else clause.text,
            "stage1_confidence": result['stage1_confidence'],
            "proceed_to_stage2": result['proceed_to_stage2'],
            "flags": result['flags'],
            "pattern_count": next((d['count'] for d in result['detections'] if d['method'] == 'pattern_based'), 0),
            "semantic_anomalous": next((d.get('is_anomalous', False) for d in result['detections'] if d['method'] == 'semantic'), False),
            "semantic_similarity": next((d.get('similarity_score', 0) for d in result['detections'] if d['method'] == 'semantic'), 0),
        })
    
    # Summary
    flagged_count = sum(1 for r in results if r['proceed_to_stage2'])
    
    # Convert numpy types for JSON serialization
    return convert_numpy_types({
        "document_id": document_id,
        "clauses_tested": len(results),
        "clauses_flagged": flagged_count,
        "results": results,
    })


@router.get("/test-patterns")
async def test_pattern_detection(
    clause_text: str = Query(..., max_length=5000, description="Clause text to test"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Test pattern-based (keyword) detection only.
    """
    from app.core.risk_indicators import RiskIndicators
    
    risk_indicators = RiskIndicators()
    detected = risk_indicators.detect_indicators(
        clause_text=clause_text,
        service_type="general"
    )
    
    return {
        "clause_text": clause_text,
        "detected_indicators": detected,
        "count": len(detected),
        "has_high_risk": any(ind['severity'] == 'high' for ind in detected),
        "has_medium_risk": any(ind['severity'] == 'medium' for ind in detected),
    }


@router.get("/test-semantic")
async def test_semantic_detection(
    clause_text: str = Query(..., max_length=5000, description="Clause text to test"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Test semantic anomaly detection only.
    """
    from app.core.semantic_anomaly_detector import SemanticAnomalyDetector
    from app.core.constants import ModelConfig
    
    detector = SemanticAnomalyDetector(
        model_name=ModelConfig.SEMANTIC_MODEL,
        similarity_threshold=ModelConfig.SEMANTIC_SIMILARITY_THRESHOLD
    )
    
    if not detector.is_available:
        return {
            "error": "Semantic detector not available",
            "is_available": False
        }
    
    result = detector.detect_semantic_anomalies(clause_text)
    
    # Convert numpy types for JSON serialization
    return convert_numpy_types({
        "clause_text": clause_text[:200] + "..." if len(clause_text) > 200 else clause_text,
        "is_available": True,
        "threshold": detector.similarity_threshold,
        "result": result
    })
