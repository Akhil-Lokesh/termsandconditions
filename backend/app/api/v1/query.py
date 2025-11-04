"""
Q&A query endpoints with RAG implementation.

Handles document queries with semantic search and citation generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_openai_service,
    get_pinecone_service,
    get_cache_service,
)
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.schemas.query import QueryRequest, QueryResponse, Citation
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService
from app.prompts.qa_prompts import QA_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Ask Question About Document",
    description="""
    Ask a question about a T&C document and receive an AI-generated answer with citations.

    **Pipeline:**
    1. Generate embedding for question
    2. Search Pinecone for relevant clauses (top 5)
    3. Build context with citations
    4. Generate answer with GPT-4
    5. Return answer with source citations and confidence score

    **Example Questions:**
    - "What is the refund policy?"
    - "Can the company change the terms without notice?"
    - "What personal data is collected?"
    - "How can I cancel my subscription?"
    - "What happens if I violate the terms?"

    **Returns:**
    - AI-generated answer in plain language
    - Citations with section and clause references
    - Confidence score (0-1) based on relevance
    """,
    responses={
        200: {
            "description": "Question answered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "question": "What is the refund policy?",
                        "answer": "According to the terms, all sales are final and non-refundable...",
                        "citations": [
                            {
                                "index": 1,
                                "section": "Payment Terms",
                                "clause_number": "5.2",
                                "text": "All payments are final...",
                                "relevance_score": 0.92,
                            }
                        ],
                        "confidence": 0.92,
                    }
                }
            },
        },
        404: {"description": "Document not found or no relevant clauses"},
        422: {"description": "Invalid question format"},
    },
)
async def query_document(
    request: Request,
    query_data: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    openai_service: OpenAIService = Depends(get_openai_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    cache_service: CacheService = Depends(get_cache_service),
):
    """
    Ask a question about a document and get an AI-generated answer with citations.

    Uses RAG (Retrieval-Augmented Generation) to provide accurate answers
    based on the actual document content.
    """
    logger.info(f"Query from {current_user.email}: {query_data.question[:100]}")

    # Validate question
    if not query_data.question or len(query_data.question.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question must be at least 3 characters long",
        )

    # Verify document exists and user has access
    document = (
        db.query(Document)
        .filter(
            Document.id == query_data.document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {query_data.document_id}",
        )

    # Check if document processing completed
    if document.processing_status not in ["completed", "anomaly_detection_failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is still processing. Status: {document.processing_status}",
        )

    # Check cache first (optional, graceful degradation)
    cache_key = f"query:{query_data.document_id}:{hash(query_data.question)}"
    if cache_service:
        try:
            cached = await cache_service.get(cache_key)
            if cached:
                logger.info("Returning cached query response")
                return QueryResponse(**cached)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

    try:
        # ============================================================
        # STEP 1: Generate question embedding
        # ============================================================
        question_embedding = await openai_service.create_embedding(query_data.question)

        logger.info(f"Generated embedding for question")

        # ============================================================
        # STEP 2: Search Pinecone for relevant clauses
        # ============================================================
        results = await pinecone_service.query(
            query_embedding=question_embedding,
            namespace=settings.PINECONE_USER_NAMESPACE,
            top_k=5,
            filter={"document_id": query_data.document_id},
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant clauses found in document. Try rephrasing your question or ask about a different topic.",
            )

        logger.info(f"Found {len(results)} relevant clauses")

        # ============================================================
        # STEP 3: Build context from retrieved clauses
        # ============================================================
        context_parts = []
        citations = []

        for idx, match in enumerate(results):
            metadata = match["metadata"]

            # Build numbered context for GPT
            context_parts.append(
                f"[{idx + 1}] Section: {metadata.get('section', 'Unknown')}, "
                f"Clause: {metadata.get('clause_number', 'N/A')}\n"
                f"Content: {metadata['text']}"
            )

            # Create citation object with safe relevance score
            score = match.get("score", 0.5)
            # Handle NaN scores
            if score is None or score != score:  # NaN != NaN
                score = 0.5

            citations.append(
                Citation(
                    clause_id=metadata.get("clause_id", f"clause_{idx + 1}"),
                    section=metadata.get("section", "Unknown Section"),
                    text=(
                        metadata["text"][:300] + "..."
                        if len(metadata["text"]) > 300
                        else metadata["text"]
                    ),
                    relevance_score=float(score),
                )
            )

        context = "\n\n".join(context_parts)

        logger.info(f"Built context with {len(citations)} citations")

        # ============================================================
        # STEP 4: Generate answer with GPT-4
        # ============================================================
        prompt = QA_SYSTEM_PROMPT.format(
            context=context,
            question=query_data.question,
        )

        answer = await openai_service.create_completion(
            prompt=prompt,
            model=settings.OPENAI_MODEL_GPT4,
            temperature=0.0,  # Deterministic answers
            max_tokens=500,
        )

        logger.info("Answer generated successfully")

        # ============================================================
        # STEP 5: Build response
        # ============================================================
        # Calculate confidence from relevance scores (handle NaN/None)
        confidence = 0.0
        if results and len(results) > 0:
            try:
                score = results[0]["score"]
                # Check for NaN or None
                if score is not None and score == score:  # NaN != NaN
                    confidence = float(score)
                else:
                    # Fallback: use average of all scores
                    valid_scores = [
                        r["score"]
                        for r in results
                        if r["score"] is not None and r["score"] == r["score"]
                    ]
                    confidence = (
                        sum(valid_scores) / len(valid_scores) if valid_scores else 0.5
                    )
            except (KeyError, TypeError, ValueError):
                confidence = 0.5  # Default moderate confidence

        response = QueryResponse(
            question=query_data.question,
            answer=answer,
            citations=citations,
            confidence=confidence,
        )

        # Cache response (optional, graceful degradation)
        if cache_service:
            try:
                await cache_service.set(cache_key, response.dict(), ttl=3600)  # 1 hour
                logger.info("Response cached")
            except Exception as e:
                logger.warning(f"Cache storage failed: {e}")

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}",
        )


@router.get(
    "/history/{document_id}",
    summary="Get Query History",
    description="Get recent queries for a document (future enhancement)",
)
async def get_query_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get query history for a document.

    **Note**: Not yet implemented. Returns empty list.
    """
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

    # TODO: Implement query history tracking
    return {
        "document_id": document_id,
        "queries": [],
        "message": "Query history tracking coming soon",
    }
