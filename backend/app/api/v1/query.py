"""
Q&A query endpoints with RAG implementation.

Handles document queries with semantic search and citation generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict
import hashlib
import logging

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_embedding_service,
    get_pinecone_service,
    get_cache_service,
    get_claude_service,
)
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.schemas.query import QueryRequest, QueryResponse, Citation
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService
from app.services.claude_service import ClaudeService
from app.prompts.qa_prompts import QA_SYSTEM_INSTRUCTIONS, QA_USER_TEMPLATE
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Ask Question About Document",
    description="""
    Ask a question about a T&C document and receive an AI-generated answer with citations.

    **Rate Limit:** 100 queries per hour per IP address.

    **Pipeline:**
    1. Generate embedding for question
    2. Search Pinecone for relevant clauses (top 5)
    3. Build context with citations
    4. Generate answer with Claude
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
@limiter.limit("100/hour")
async def query_document(
    request: Request,
    query_data: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    cache_service: CacheService = Depends(get_cache_service),
    claude_service: ClaudeService = Depends(get_claude_service),
):
    """
    Ask a question about a document and get an AI-generated answer with citations.

    Uses RAG (Retrieval-Augmented Generation) to provide accurate answers
    based on the actual document content.
    """
    # NOTE: Rate limiting is handled by the @limiter.limit decorator on the route
    # The incorrect inline limiter call was removed

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

    # Check if document processing completed (allow queries during anomaly detection)
    # Q&A only requires clause extraction to be complete, not full anomaly detection
    allowed_statuses = ["completed", "anomaly_detection_failed", "analyzing_anomalies"]
    if document.processing_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is still processing. Status: {document.processing_status}",
        )

    # Check cache first (optional, graceful degradation)
    q_hash = hashlib.sha256(query_data.question.encode()).hexdigest()[:16]
    cache_key = f"query:{query_data.document_id}:{q_hash}"
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
        question_embedding = await embedding_service.create_embedding(query_data.question)

        logger.info(f"Generated embedding for question")

        # ============================================================
        # STEP 2: Search Pinecone for relevant clauses
        # ============================================================
        search_results = await pinecone_service.query(
            query_embedding=question_embedding,
            namespace=settings.PINECONE_USER_NAMESPACE,
            top_k=10,  # Get more candidates
            filter={"document_id": query_data.document_id},
        )

        # Filter by relevance score (only keep scores > 0.3)
        RELEVANCE_THRESHOLD = 0.3
        relevant_results = [
            r for r in search_results
            if r.get("score", 0) >= RELEVANCE_THRESHOLD
        ]

        if not relevant_results:
            # No relevant results found
            logger.warning(f"No relevant clauses found for query: {query_data.question}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="I couldn't find any clauses in this document that directly answer your question. Could you rephrase or ask about a different aspect of the terms?",
            )

        # Take top 5 most relevant
        results = relevant_results[:5]

        logger.info(
            f"Found {len(results)} relevant clauses "
            f"(filtered from {len(search_results)} candidates)"
        )

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
                    # Chunk metadata stores the real clause number under
                    # "clause_number" (see legal_chunker); there is no "clause_id"
                    # key, so the old lookup always fell back to a synthetic index.
                    clause_id=(
                        metadata.get("clause_number")
                        or metadata.get("clause_id")
                        or f"clause_{idx + 1}"
                    ),
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
        # STEP 4: Generate answer with Claude
        # ============================================================
        user_msg = QA_USER_TEMPLATE.format(
            context=context,
            question=query_data.question,
        )

        answer = await claude_service.create_completion(
            prompt=user_msg,
            system_message=QA_SYSTEM_INSTRUCTIONS,
            temperature=0.0,
            max_tokens=500,
        )

        logger.info("Answer generated successfully with Claude")

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
                await cache_service.set(cache_key, response.dict(), ttl=3600)
                # Append to per-document query history (last 20 entries)
                history_key = f"query_history:{query_data.document_id}:{current_user.id}"
                entry = {"question": query_data.question, "answer": answer, "confidence": confidence}
                existing = await cache_service.get(history_key) or []
                existing.append(entry)
                await cache_service.set(history_key, existing[-20:], ttl=86400)
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
            detail="Query processing failed. Please try again.",
        )


@router.get(
    "/history/{document_id}",
    summary="Get Query History",
    description="Get the last 20 queries asked about a document (cached per session).",
)
async def get_query_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    cache_service: CacheService = Depends(get_cache_service),
):
    """Get recent query history for a document."""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    queries = []
    if cache_service:
        try:
            history_key = f"query_history:{document_id}:{current_user.id}"
            queries = await cache_service.get(history_key) or []
        except Exception as e:
            logger.warning(f"Failed to fetch query history: {e}")

    return {"document_id": document_id, "queries": queries, "total": len(queries)}
