"""
Prevalence calculator for comparing clauses to baseline corpus.

Calculates how common a clause is by comparing it to a baseline corpus
of 100+ standard Terms & Conditions documents.
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.pinecone_service import PineconeService
from app.services.embedding_service import EmbeddingService
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PrevalenceCalculator:
    """Calculates prevalence of clauses in baseline corpus."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        pinecone_service: Optional[PineconeService] = None,
        db: Optional[Session] = None,
    ):
        """
        Initialize prevalence calculator.

        Args:
            embedding_service: Optional embedding service instance
            pinecone_service: Optional Pinecone service instance
            db: Optional database session for future use
        """
        self.embedding = embedding_service or EmbeddingService()
        self.pinecone = pinecone_service or PineconeService()
        self.db = db  # Store for potential future use

    async def calculate_prevalence(
        self,
        clause_text: str,
        clause_type: str,
    ) -> float:
        """
        Calculate how common a clause is in baseline corpus.

        Uses a similarity-based approach:
        - High similarity scores (>0.7) = clause is common in baseline
        - Low similarity scores (<0.5) = clause is rare/unusual

        Args:
            clause_text: Text of the clause
            clause_type: Type of clause

        Returns:
            Prevalence percentage (0.0 to 1.0)
        """
        try:
            # Generate embedding for clause
            embedding = await self.embedding.create_embedding(clause_text)

            # Search baseline corpus using query method (no filter for broader search)
            similar_clauses = await self.pinecone.query(
                query_embedding=embedding,
                namespace=settings.PINECONE_BASELINE_NAMESPACE,
                top_k=20,  # Get top 20 similar clauses
            )

            # Check if baseline corpus is empty
            if not similar_clauses or len(similar_clauses) == 0:
                logger.warning(f"No baseline data found for clause type: {clause_type}")
                return 0.1  # Unknown but probably unusual

            # Calculate prevalence based on similarity scores
            # Use the average of top 5 similarity scores
            scores = [c.get("score", 0) for c in similar_clauses[:5]]
            avg_similarity = sum(scores) / len(scores) if scores else 0

            # Convert similarity to prevalence:
            # - Similarity > 0.75 = very common (prevalence 60-90%)
            # - Similarity 0.5-0.75 = somewhat common (prevalence 30-60%)
            # - Similarity < 0.5 = rare (prevalence 0-30%)
            if avg_similarity > 0.75:
                prevalence = 0.6 + (avg_similarity - 0.75) * 1.2  # 60-90%
            elif avg_similarity > 0.5:
                prevalence = 0.3 + (avg_similarity - 0.5) * 1.2  # 30-60%
            else:
                prevalence = avg_similarity * 0.6  # 0-30%

            # Clamp to 0-1 range
            prevalence = max(0.0, min(1.0, prevalence))

            logger.info(
                f"Prevalence: {prevalence:.1%} (avg similarity: {avg_similarity:.2f} from top {len(scores)} matches)"
            )

            return prevalence

        except Exception as e:
            logger.warning(f"Prevalence calculation failed: {e}")
            return 0.1  # Default to low prevalence on error
