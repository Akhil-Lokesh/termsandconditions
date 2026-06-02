"""
Embedding service using local sentence-transformers.

Uses all-MiniLM-L6-v2 model for FREE local embeddings.
No external API required!
"""

import asyncio
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model = None
_model_name = "all-MiniLM-L6-v2"  # Fast, good quality, 384 dimensions


def get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {_model_name}")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_model_name)
        logger.info(f"✓ Embedding model loaded: {_model_name}")
    return _model


class EmbeddingService:
    """Local embedding service using sentence-transformers."""

    def __init__(self, cache_service=None):
        """
        Initialize embedding service.

        Args:
            cache_service: Optional Redis cache service for caching results
        """
        self.cache = cache_service
        self._model = None
        self.model_dim = 384  # all-MiniLM-L6-v2 produces 384-dim vectors
        self.embedding_dim = 1536  # Pad to match Pinecone index dimensions

    async def initialize(self):
        """Initialize the model (called on startup)."""
        # Pre-load the model
        _ = self.model
        logger.info("Embedding service initialized with local model")

    def _pad_embedding(self, embedding: List[float]) -> List[float]:
        """Pad embedding to target dimension (1536) with zeros."""
        if len(embedding) >= self.embedding_dim:
            return embedding[:self.embedding_dim]
        # Pad with zeros
        return embedding + [0.0] * (self.embedding_dim - len(embedding))

    @property
    def model(self):
        """Lazy load model on first use."""
        if self._model is None:
            self._model = get_model()
        return self._model

    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using local model.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector (384 dimensions)
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = f"embedding_local:{hash(text)}"
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for embedding: {cache_key[:25]}...")
                    return cached

            # Generate embedding locally
            logger.debug(f"Generating local embedding for text ({len(text)} chars)")
            
            # Truncate very long texts (model max is ~512 tokens)
            if len(text) > 2000:
                text = text[:2000]
            
            # model.encode is sync + CPU-bound; run it off the event loop so a
            # single embedding call doesn't block all other concurrent requests.
            embedding = await asyncio.to_thread(
                self.model.encode, text, convert_to_numpy=True
            )
            embedding_list = embedding.tolist()
            
            # Pad to 1536 dimensions to match Pinecone index
            embedding_list = self._pad_embedding(embedding_list)

            # Cache result (24 hour TTL)
            if self.cache:
                await self.cache.set(cache_key, embedding_list, ttl=86400)

            logger.debug(f"Generated local embedding with dimension {len(embedding_list)}")
            return embedding_list

        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise Exception(f"Failed to generate embedding: {str(e)}") from e

    async def batch_create_embeddings(
        self, texts: List[str], batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings in batches for efficiency.

        Args:
            texts: List of input texts
            batch_size: Number of texts per batch

        Returns:
            List of embedding vectors
        """
        try:
            # Truncate long texts
            texts = [t[:2000] if len(t) > 2000 else t for t in texts]
            
            logger.info(f"Generating {len(texts)} embeddings locally...")
            
            # Generate all at once (sentence-transformers handles batching
            # internally); run off the event loop — this is the heaviest CPU call.
            embeddings = await asyncio.to_thread(
                self.model.encode, texts, convert_to_numpy=True, show_progress_bar=False
            )
            
            # Pad each embedding to 1536 dimensions
            padded = [self._pad_embedding(emb.tolist()) for emb in embeddings]
            
            logger.info(f"✓ Generated {len(padded)} embeddings (padded to {self.embedding_dim} dims)")
            return padded

        except Exception as e:
            logger.error(f"Error during batch embedding: {e}", exc_info=True)
            raise Exception(f"Failed to generate batch embeddings: {str(e)}") from e

    async def close(self):
        """No cleanup needed for local model."""
        pass
