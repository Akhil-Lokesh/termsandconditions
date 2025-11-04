"""
Legal-aware chunker for creating semantic chunks from T&C clauses.

Preserves clause boundaries and includes contextual metadata.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LegalChunker:
    """Creates semantic chunks for embedding generation."""

    def __init__(self, max_chunk_size: int = 500, overlap: int = 50):
        """
        Initialize legal chunker.

        Args:
            max_chunk_size: Maximum number of words per chunk
            overlap: Number of words to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    async def create_chunks(
        self, sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert sections and clauses into embeddable chunks with metadata.

        Strategy:
        - Keep clauses together if < max_chunk_size
        - Split long clauses with overlap
        - Include context (section, clause number) in metadata

        Args:
            sections: List of sections with clauses

        Returns:
            List[dict]: List of chunks with text and metadata
        """
        chunks = []

        for section in sections:
            section_num = section.get("number", "")
            section_title = section.get("title", "")

            for clause in section.get("clauses", []):
                clause_id = clause.get("id", "")
                clause_text = clause.get("text", "")

                # Count words
                word_count = len(clause_text.split())

                if word_count <= self.max_chunk_size:
                    # Clause fits in one chunk
                    chunks.append(
                        self._create_chunk(
                            text=clause_text,
                            section=section_title,
                            section_number=section_num,
                            clause_number=clause_id,
                            chunk_index=0,
                        )
                    )
                else:
                    # Split large clause
                    sub_chunks = self._split_text(clause_text)
                    for idx, sub_text in enumerate(sub_chunks):
                        chunks.append(
                            self._create_chunk(
                                text=sub_text,
                                section=section_title,
                                section_number=section_num,
                                clause_number=clause_id,
                                chunk_index=idx,
                            )
                        )

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _create_chunk(
        self,
        text: str,
        section: str,
        section_number: str,
        clause_number: str,
        chunk_index: int,
    ) -> Dict[str, Any]:
        """
        Create chunk dict with metadata.

        Args:
            text: Chunk text
            section: Section title
            section_number: Section number
            clause_number: Clause number
            chunk_index: Index within clause (for split clauses)

        Returns:
            dict: Chunk with text and metadata
        """
        return {
            "text": text,
            "metadata": {
                "section": section,
                "section_number": section_number,
                "clause_number": clause_number,
                "chunk_index": chunk_index,
                # Full context for better retrieval
                "context": f"Section {section_number}: {section} - Clause {clause_number}",
            },
        }

    def _split_text(self, text: str) -> List[str]:
        """
        Split text with overlap for large clauses.

        Uses word-based splitting for cleaner breaks.

        Args:
            text: Text to split

        Returns:
            List[str]: List of text chunks
        """
        words = text.split()
        chunks = []

        start = 0
        while start < len(words):
            # Take max_chunk_size words
            end = min(start + self.max_chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)

            # Move start with overlap
            if end < len(words):
                start = end - self.overlap
            else:
                break

        return chunks
