"""
Pinecone vector database service.

Provides methods for:
- Index initialization
- Dual-namespace strategy (user_tcs, baseline)
- Vector upsert operations
- Query/search operations
- Delete operations
- Index statistics
"""

import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from pinecone.core.client.exceptions import PineconeException

from app.core.config import settings
from app.utils.exceptions import PineconeServiceError

logger = logging.getLogger(__name__)


class PineconeService:
    """Pinecone vector database client with dual-namespace support."""

    def __init__(self):
        """Initialize Pinecone client (connection happens in initialize())."""
        self.client: Optional[Pinecone] = None
        self.index = None
        self.index_name = settings.PINECONE_INDEX_NAME
        self.user_namespace = settings.PINECONE_USER_NAMESPACE
        self.baseline_namespace = settings.PINECONE_BASELINE_NAMESPACE
        self.dimension = 1536  # OpenAI text-embedding-3-small

    async def initialize(self):
        """
        Initialize Pinecone connection and create index if needed.

        This should be called during application startup.

        Raises:
            PineconeServiceError: If initialization fails
        """
        try:
            logger.info("Initializing Pinecone service...")

            # Initialize client
            self.client = Pinecone(api_key=settings.PINECONE_API_KEY)

            # Check if index exists, create if not
            existing_indexes = self.client.list_indexes()
            index_names = [idx.name for idx in existing_indexes]

            if self.index_name not in index_names:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud=settings.PINECONE_CLOUD or "aws",
                        region=settings.PINECONE_ENVIRONMENT,
                    ),
                )
                logger.info(f"Index '{self.index_name}' created successfully")
            else:
                logger.info(f"Index '{self.index_name}' already exists")

            # Connect to index
            self.index = self.client.Index(self.index_name)

            # Get index stats
            stats = self.index.describe_index_stats()
            logger.info(
                f"Pinecone initialized - Total vectors: {stats.get('total_vector_count', 0)}"
            )
            logger.info(f"Namespaces: {list(stats.get('namespaces', {}).keys())}")

        except PineconeException as e:
            logger.error(f"Pinecone initialization error: {e}")
            raise PineconeServiceError(f"Failed to initialize Pinecone: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during Pinecone initialization: {e}", exc_info=True)
            raise PineconeServiceError(f"Unexpected error: {str(e)}") from e

    async def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        namespace: str,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Insert/update chunks into Pinecone.

        Args:
            chunks: List of dicts with 'text', 'embedding', 'metadata'
            namespace: Namespace to use ('user_tcs' or 'baseline')
            document_id: Unique document identifier

        Returns:
            Dict with upsert statistics

        Raises:
            PineconeServiceError: If upsert operation fails
        """
        if not self.index:
            raise PineconeServiceError("Pinecone not initialized. Call initialize() first.")

        try:
            # Build vectors for upsert
            vectors = []
            for idx, chunk in enumerate(chunks):
                vector_id = f"{document_id}_chunk_{idx}"
                
                # Prepare metadata (Pinecone has size limits)
                metadata = {
                    **chunk.get("metadata", {}),
                    "document_id": document_id,
                    "chunk_index": idx,
                    # Store truncated text in metadata for retrieval
                    "text": chunk["text"][:1000] if len(chunk["text"]) > 1000 else chunk["text"],
                }

                vectors.append({
                    "id": vector_id,
                    "values": chunk["embedding"],
                    "metadata": metadata,
                })

            # Upsert in batches (Pinecone recommends 100-200 per batch)
            BATCH_SIZE = 100
            total_upserted = 0

            for i in range(0, len(vectors), BATCH_SIZE):
                batch = vectors[i : i + BATCH_SIZE]
                self.index.upsert(vectors=batch, namespace=namespace)
                total_upserted += len(batch)

                logger.debug(
                    f"Upserted batch {i // BATCH_SIZE + 1} "
                    f"({len(batch)} vectors) to namespace '{namespace}'"
                )

            logger.info(
                f"Successfully upserted {total_upserted} vectors for document {document_id} "
                f"to namespace '{namespace}'"
            )

            return {
                "document_id": document_id,
                "namespace": namespace,
                "vectors_upserted": total_upserted,
            }

        except PineconeException as e:
            logger.error(f"Pinecone upsert error: {e}")
            raise PineconeServiceError(f"Failed to upsert vectors: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during upsert: {e}", exc_info=True)
            raise PineconeServiceError(f"Unexpected error: {str(e)}") from e

    async def query(
        self,
        query_embedding: List[float],
        namespace: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Query Pinecone for similar vectors.

        Args:
            query_embedding: Query vector (1536 dimensions)
            namespace: Namespace to search in
            top_k: Number of results to return
            filter: Optional metadata filter
            include_metadata: Whether to include metadata in results

        Returns:
            List of matches with scores and metadata

        Raises:
            PineconeServiceError: If query operation fails
        """
        if not self.index:
            raise PineconeServiceError("Pinecone not initialized. Call initialize() first.")

        try:
            logger.debug(
                f"Querying Pinecone: namespace={namespace}, top_k={top_k}, "
                f"filter={filter}"
            )

            results = self.index.query(
                vector=query_embedding,
                namespace=namespace,
                top_k=top_k,
                filter=filter,
                include_metadata=include_metadata,
            )

            # Parse matches
            matches = []
            for match in results.get("matches", []):
                matches.append({
                    "id": match["id"],
                    "score": match["score"],
                    "metadata": match.get("metadata", {}),
                })

            logger.debug(f"Found {len(matches)} matches")
            return matches

        except PineconeException as e:
            logger.error(f"Pinecone query error: {e}")
            raise PineconeServiceError(f"Failed to query vectors: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during query: {e}", exc_info=True)
            raise PineconeServiceError(f"Unexpected error: {str(e)}") from e

    async def delete_document(
        self,
        document_id: str,
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Delete all vectors for a document.

        Args:
            document_id: Document identifier
            namespace: Namespace to delete from

        Returns:
            Dict with deletion statistics

        Raises:
            PineconeServiceError: If delete operation fails
        """
        if not self.index:
            raise PineconeServiceError("Pinecone not initialized. Call initialize() first.")

        try:
            logger.info(
                f"Deleting document {document_id} from namespace '{namespace}'"
            )

            # Delete by metadata filter
            self.index.delete(
                filter={"document_id": document_id},
                namespace=namespace,
            )

            logger.info(
                f"Successfully deleted document {document_id} from namespace '{namespace}'"
            )

            return {
                "document_id": document_id,
                "namespace": namespace,
                "status": "deleted",
            }

        except PineconeException as e:
            logger.error(f"Pinecone delete error: {e}")
            raise PineconeServiceError(f"Failed to delete vectors: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during delete: {e}", exc_info=True)
            raise PineconeServiceError(f"Unexpected error: {str(e)}") from e

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index.

        Returns:
            Dict with index statistics

        Raises:
            PineconeServiceError: If operation fails
        """
        if not self.index:
            raise PineconeServiceError("Pinecone not initialized. Call initialize() first.")

        try:
            stats = self.index.describe_index_stats()

            # Format stats
            formatted_stats = {
                "total_vector_count": stats.get("total_vector_count", 0),
                "namespaces": {},
            }

            # Add namespace details
            for namespace, ns_stats in stats.get("namespaces", {}).items():
                formatted_stats["namespaces"][namespace] = {
                    "vector_count": ns_stats.get("vector_count", 0),
                }

            return formatted_stats

        except PineconeException as e:
            logger.error(f"Pinecone stats error: {e}")
            raise PineconeServiceError(f"Failed to get index stats: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting stats: {e}", exc_info=True)
            raise PineconeServiceError(f"Unexpected error: {str(e)}") from e

    async def close(self):
        """Close Pinecone connection (cleanup)."""
        # Pinecone client doesn't need explicit cleanup
        logger.info("Pinecone service closed")
