"""
Document upload endpoints.

Handles document upload, processing, and analysis orchestration.
"""

import uuid
import tempfile
import os
from pathlib import Path
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    status,
    BackgroundTasks,
    Request,
)
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_embedding_service,
    get_pinecone_service,
    get_cache_service,
    get_claude_service,
)
from app.core.config import settings
from app.core.anomaly_detector import AnomalyDetector
from app.core.document_pipeline import DocumentProcessingPipeline
from app.models.user import User
from app.models.document import Document
from app.models.clause import Clause
from app.schemas.document import DocumentResponse, DocumentCreate, DocumentListResponse
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.services.claude_service import ClaudeService
from app.utils.exceptions import DocumentProcessingError, EmbeddingError, PineconeError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# HELPER FUNCTIONS (Extracted for clarity)
# =============================================================================


def validate_file(file: UploadFile, content: bytes) -> float:
    """
    Validate uploaded file type and size.

    Args:
        file: Uploaded file
        content: File content bytes

    Returns:
        File size in MB

    Raises:
        HTTPException: If validation fails
    """
    # Validate file type (PDF only)
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported. Please upload a .pdf file.",
        )

    file_size_mb = len(content) / (1024 * 1024)

    # Validate file size
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({file_size_mb:.1f}MB). Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    return file_size_mb


# ============================================================================
# BACKGROUND TASK: Anomaly Detection
# ============================================================================


async def run_anomaly_detection_background(
    document_id: str,
    sections: list,
    metadata: dict,
    embedding_service: EmbeddingService,
    pinecone_service: PineconeService,
):
    """
    Run anomaly detection in background after document upload completes.

    This task:
    1. Detects anomalies by comparing clauses to baseline corpus
    2. Generates risk assessment report
    3. Saves anomalies to database
    4. Updates document processing status

    Args:
        document_id: Document ID
        sections: Parsed document sections with clauses
        metadata: Document metadata (company name, etc.)
        embedding_service: Embedding service instance
        pinecone_service: Pinecone service instance
    """
    # Create a NEW database session for the background task
    # The original session from the request is already closed
    from app.db.session import SessionLocal
    import asyncio

    # Small delay to ensure the main transaction is committed and visible
    await asyncio.sleep(1)

    db = SessionLocal()

    try:
        logger.info(f"Starting background anomaly detection for {document_id}...")

        # Verify document exists with retry (handles race conditions)
        max_retries = 3
        for attempt in range(max_retries):
            document_check = db.query(Document).filter(Document.id == document_id).first()
            if document_check:
                logger.info(f"Document {document_id} verified (attempt {attempt + 1})")
                break
            logger.warning(f"Document {document_id} not found, retrying... (attempt {attempt + 1})")
            db.close()
            await asyncio.sleep(2)
            db = SessionLocal()
        else:
            logger.error(f"Document {document_id} not found after {max_retries} retries")
            return

        # Extract company name from metadata
        company_name = metadata.get("company", "Unknown")

        # Detect anomalies - returns comprehensive report dict
        detector = AnomalyDetector(embedding_service, pinecone_service, db)
        detection_result = await detector.detect_anomalies(
            document_id=document_id,
            sections=sections,
            company_name=company_name,
            service_type="general",  # TODO: Auto-detect service type from metadata
        )

        # Extract anomalies from the detection result
        # The new pipeline returns a report dict with categorized alerts
        all_anomalies = (
            detection_result.get('high_severity_alerts', []) +
            detection_result.get('medium_severity_alerts', []) +
            detection_result.get('low_severity_alerts', [])
        )
        
        # Get risk score directly from the pipeline result
        overall_risk_score = detection_result.get('overall_risk_score', 0.0)
        
        # Determine risk level from score
        if overall_risk_score >= 7.0:
            risk_level = "High"
        elif overall_risk_score >= 4.0:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        logger.info(
            f"Anomaly detection completed: {len(all_anomalies)} anomalies found, "
            f"Risk Score: {overall_risk_score}/10 ({risk_level})"
        )

        # Save anomalies to database
        from app.models.anomaly import Anomaly

        for anomaly_data in all_anomalies:
            # Extract prevalence - handle both float and dict formats
            prevalence_value = anomaly_data.get("prevalence", 0.0)
            if isinstance(prevalence_value, dict):
                prevalence_value = prevalence_value.get("prevalence", 0.0)

            # Convert detected_indicators to JSON-serializable format
            detected_indicators = anomaly_data.get("detected_indicators", [])
            if isinstance(detected_indicators, str):
                import json
                try:
                    detected_indicators = json.loads(detected_indicators)
                except:
                    detected_indicators = []

            anomaly = Anomaly(
                id=str(uuid.uuid4()),
                document_id=document_id,
                section=anomaly_data.get("section", "Unknown"),
                clause_number=anomaly_data.get("clause_number", "0"),
                clause_text=anomaly_data.get("clause_text", ""),
                severity=anomaly_data.get("severity", "low"),
                explanation=anomaly_data.get("explanation", ""),
                consumer_impact=anomaly_data.get("consumer_impact", ""),
                recommendation=anomaly_data.get("recommendation", ""),
                risk_category=anomaly_data.get("risk_category", "other"),
                prevalence=float(prevalence_value) if prevalence_value else 0.0,
                detected_indicators=detected_indicators,
            )
            db.add(anomaly)

        # Update document with risk assessment
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.anomaly_count = len(all_anomalies)
            document.risk_score = overall_risk_score
            document.risk_level = risk_level
            document.processing_status = "completed"
            db.commit()

            logger.info(
                f"Background anomaly detection complete for {document_id}: "
                f"{len(all_anomalies)} anomalies saved, "
                f"Risk Score: {overall_risk_score}/10 ({risk_level})"
            )
        else:
            logger.error(f"Document {document_id} not found when updating anomaly results")

    except Exception as e:
        logger.error(f"Background anomaly detection failed for {document_id}: {e}", exc_info=True)

        # Update document status to failed
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.processing_status = "anomaly_detection_failed"
                document.anomaly_count = 0
                document.risk_score = 0.0
                document.risk_level = "Unknown"
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update document status after error: {db_error}")
    
    finally:
        # Always close the session when done
        db.close()
        logger.info(f"Background task session closed for {document_id}")


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload T&C Document",
    description="""
    Upload a Terms & Conditions PDF document for comprehensive analysis.

    **Rate Limit:** 10 uploads per hour per IP address.

    **Processing Pipeline:**
    1. Validate file type and size
    2. Extract text from PDF (pdfplumber primary, PyPDF2 fallback)
    3. Parse document structure (sections, clauses)
    4. Create semantic chunks with metadata
    5. Generate embeddings (local sentence-transformers)
    6. Extract metadata (company, jurisdiction, dates) using Claude
    7. Store vectors in Pinecone (user_tcs namespace)
    8. Run anomaly detection (compare to baseline corpus)
    9. Save analysis results to database

    **Returns:** Document metadata with anomaly count and processing status
    """,
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file (max 10MB)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    claude_service: ClaudeService = Depends(get_claude_service),
):
    """
    Upload and process a T&C document.

    This endpoint orchestrates the full document processing pipeline including
    text extraction, structure parsing, embedding generation, vector storage,
    and anomaly detection.
    """
    logger.info(f"Document upload started by user: {current_user.email}")

    # Read and validate file
    content = await file.read()
    file_size_mb = validate_file(file, content)
    logger.info(f"File validated: {file.filename} ({file_size_mb:.2f}MB)")

    # Generate unique document ID
    doc_id = str(uuid.uuid4())

    # Save file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / f"{doc_id}.pdf"

    try:
        # Write temp file
        with open(temp_path, "wb") as f:
            f.write(content)
        logger.info(f"Temp file created: {temp_path}")

        # Run the processing pipeline
        pipeline = DocumentProcessingPipeline(embedding_service, pinecone_service, claude_service)
        result = await pipeline.process_document(str(temp_path), doc_id)

        # Save document and clauses to database
        document = Document(
            id=doc_id,
            user_id=current_user.id,
            filename=file.filename,
            text=result.text,
            document_metadata=result.metadata,
            page_count=result.page_count,
            clause_count=result.num_clauses,
            processing_status="embedding_completed",
        )

        db.add(document)
        for clause_record in result.clause_records:
            db.add(clause_record)
        db.commit()
        db.refresh(document)

        logger.info(f"Document and {len(result.clause_records)} clauses saved: {doc_id}")

        # Schedule background anomaly detection
        document.processing_status = "analyzing_anomalies"
        db.commit()

        background_tasks.add_task(
            run_anomaly_detection_background,
            document_id=doc_id,
            sections=result.sections,
            metadata=result.metadata,
            embedding_service=embedding_service,
            pinecone_service=pinecone_service,
        )

        logger.info(f"Document upload complete: {doc_id} (anomaly detection in background)")

        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            metadata=result.metadata,
            page_count=result.page_count,
            clause_count=result.num_clauses,
            anomaly_count=0,  # Will be populated when background task completes
            processing_status="analyzing_anomalies",
            created_at=document.created_at,
        )

    except DocumentProcessingError as e:
        logger.error(f"Document processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    except EmbeddingError as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate embeddings. Embedding service may be unavailable.",
        )

    except PineconeError as e:
        logger.error(f"Vector storage failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to store document vectors. Pinecone service may be unavailable.",
        )

    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )

    finally:
        # Cleanup temp file
        if temp_path.exists():
            os.remove(temp_path)
        if Path(temp_dir).exists():
            os.rmdir(temp_dir)
        logger.info("Temp files cleaned up")


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get Document Details",
    description="Retrieve full details of a specific document by ID.",
)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get document metadata and analysis results by ID.
    """
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

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        metadata=document.document_metadata,
        page_count=document.page_count,
        clause_count=document.clause_count,
        anomaly_count=document.anomaly_count,
        processing_status=document.processing_status,
        created_at=document.created_at,
    )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List User Documents",
    description="Get a list of all documents uploaded by the current user.",
)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all documents for the current user with pagination.
    """
    # Get total count
    total = db.query(Document).filter(Document.user_id == current_user.id).count()

    # Get documents with pagination
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                filename=doc.filename,
                metadata=doc.document_metadata,
                page_count=doc.page_count,
                clause_count=doc.clause_count,
                anomaly_count=doc.anomaly_count,
                processing_status=doc.processing_status,
                created_at=doc.created_at,
            )
            for doc in documents
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document",
    description="Delete a document and all associated data (vectors, clauses, anomalies).",
)
async def delete_document(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
):
    """
    Delete document and cleanup all associated resources.
    """
    # Find document
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
        # Delete from Pinecone
        await pinecone_service.delete_document(
            document_id=document_id,
            namespace=settings.PINECONE_USER_NAMESPACE,
        )
        logger.info(f"Deleted vectors from Pinecone: {document_id}")

        # Delete from database (cascades to clauses and anomalies)
        db.delete(document)
        db.commit()

        logger.info(f"Document deleted: {document_id}")

    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )
