"""
Local embedding service using sentence-transformers.

Uses free local embeddings (no external API required).
Uses all-mpnet-base-v2 (768 dims) and pads to 1536 for Pinecone compatibility.
"""

import logging
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model: Optional[SentenceTransformer] = None
_model_name = "all-mpnet-base-v2"  # 768 dimensions, high quality


def get_model() -> SentenceTransformer:
    """Get or load the sentence transformer model."""
    global _model
    if _model is None:
        logger.info(f"Loading sentence-transformers model: {_model_name}")
        _model = SentenceTransformer(_model_name)
        logger.info(f"Model loaded. Embedding dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


class LocalEmbeddingService:
    """Local embedding service using sentence-transformers."""
    
    def __init__(self, cache_service=None, target_dim: int = 1536):
        """
        Initialize local embedding service.
        
        Args:
            cache_service: Optional cache service for caching embeddings
            target_dim: Target dimension for Pinecone compatibility (default 1536)
        """
        self.cache = cache_service
        self.target_dim = target_dim
        self.model = get_model()
        self.native_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"LocalEmbeddingService initialized: {self.native_dim} -> {self.target_dim} dims")
    
    def _pad_embedding(self, embedding: List[float]) -> List[float]:
        """Pad embedding to target dimension."""
        if len(embedding) >= self.target_dim:
            return embedding[:self.target_dim]
        
        # Pad with zeros
        padded = np.zeros(self.target_dim)
        padded[:len(embedding)] = embedding
        return padded.tolist()
    
    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats (1536 dimensions)
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = f"local_emb:{hash(text)}"
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for embedding")
                    return cached
            
            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Pad to target dimension
            padded = self._pad_embedding(embedding.tolist())
            
            # Cache result
            if self.cache:
                await self.cache.set(cache_key, padded, ttl=86400)
            
            logger.debug(f"Generated local embedding ({len(padded)} dims)")
            return padded
            
        except Exception as e:
            logger.error(f"Local embedding error: {e}", exc_info=True)
            raise Exception(f"Failed to generate embedding: {str(e)}") from e
    
    async def batch_create_embeddings(
        self, texts: List[str], batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings in batches.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for encoding
            
        Returns:
            List of embedding vectors (1536 dims each)
        """
        try:
            logger.info(f"Generating {len(texts)} embeddings locally")
            
            # Encode all at once (sentence-transformers handles batching)
            embeddings = self.model.encode(
                texts, 
                convert_to_numpy=True,
                batch_size=batch_size,
                show_progress_bar=False
            )
            
            # Pad all embeddings
            padded = [self._pad_embedding(emb.tolist()) for emb in embeddings]
            
            logger.info(f"Generated {len(padded)} local embeddings")
            return padded
            
        except Exception as e:
            logger.error(f"Batch embedding error: {e}", exc_info=True)
            raise Exception(f"Failed to generate batch embeddings: {str(e)}") from e
    
    async def close(self):
        """No cleanup needed for local model."""
        pass
