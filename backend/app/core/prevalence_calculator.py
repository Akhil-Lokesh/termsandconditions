"""
Prevalence calculator for comparing clauses to baseline corpus.

Calculates how common a clause is by comparing it to a baseline corpus
of 100+ standard Terms & Conditions documents.
"""

from typing import Dict, Any, Optional

from app.services.pinecone_service import PineconeService
from app.services.openai_service import OpenAIService
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class PrevalenceCalculator:
    """Calculates prevalence of clauses in baseline corpus."""

    def __init__(
        self,
        openai_service: Optional[OpenAIService] = None,
        pinecone_service: Optional[PineconeService] = None
    ):
        """
        Initialize prevalence calculator.

        Args:
            openai_service: Optional OpenAI service instance
            pinecone_service: Optional Pinecone service instance
        """
        self.openai = openai_service or OpenAIService()
        self.pinecone = pinecone_service or PineconeService()
    
    async def calculate_prevalence(
        self,
        clause_text: str,
        clause_type: str,
    ) -> float:
        """
        Calculate how common a clause is in baseline corpus.
        
        Args:
            clause_text: Text of the clause
            clause_type: Type of clause
            
        Returns:
            Prevalence percentage (0.0 to 1.0)
        """
        # Generate embedding for clause
        embedding = await self.openai.create_embedding(clause_text)
        
        # Search baseline corpus
        similar_clauses = await self.pinecone.search(
            embedding=embedding,
            namespace=settings.PINECONE_NAMESPACE_BASELINE,
            filter={"clause_type": clause_type},
            top_k=settings.BASELINE_SAMPLE_SIZE,
        )
        
        # Check if baseline corpus is empty
        if not similar_clauses or len(similar_clauses) == 0:
            logger.warning(f"No baseline data found for clause type: {clause_type}")
            return 0.1  # Unknown but probably unusual - low prevalence default
        
        # Count highly similar clauses (similarity > 0.85)
        num_similar = sum(1 for c in similar_clauses if c.get("score", 0) > settings.SIMILARITY_THRESHOLD)
        
        # Calculate prevalence based on actual results returned
        total_results = len(similar_clauses)
        prevalence = num_similar / total_results if total_results > 0 else 0.1
        
        logger.info(f"Prevalence: {prevalence:.2%} ({num_similar}/{total_results} similar clauses)")
        
        return prevalence
