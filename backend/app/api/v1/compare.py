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
    
    Args:
        comparison_data: Request with document IDs to compare
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Comparison results highlighting key differences
        
    Raises:
        HTTPException: If documents not found or comparison fails
    """
    logger.info(f"Document comparison requested by user {current_user.email}")
    
    # Verify all documents exist and belong to user
    documents = db.query(Document).filter(
        Document.id.in_(comparison_data.document_ids),
        Document.user_id == current_user.id,
    ).all()
    
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
        # TODO: Implement comparison logic
        # This will compare:
        # - Cancellation policies
        # - Privacy practices
        # - Liability terms
        # - Payment terms
        # - Overall risk scores
        
        return ComparisonResponse(
            documents=[],
            differences=[],
            recommendations="",
        )
        
    except Exception as e:
        logger.error(f"Document comparison failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document comparison failed: {str(e)}",
        )
