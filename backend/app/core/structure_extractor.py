"""
Improved structure extractor for parsing sections and clauses from T&C documents.

Enhanced with:
- More flexible regex patterns
- Better debugging capabilities
- Paragraph-based fallback
- Text normalization

Uses regex patterns to identify hierarchical structure.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Clause:
    """Represents a clause in a T&C document."""
    section: str
    subsection: str
    clause_number: str
    text: str
    level: int  # 0=section, 1=subsection, 2=clause


class StructureExtractor:
    """
    Extracts hierarchical structure (sections and clauses) from T&C documents.

    Improvements over original:
    - More flexible regex patterns (handles variations in formatting)
    - Debug mode for troubleshooting
    - Paragraph-based fallback when patterns don't match
    - Better handling of edge cases
    """

    # Regex patterns for common T&C section formats
    # Ordered by specificity (most specific first)
    SECTION_PATTERNS = [
        r'^(\d+)\.\s+([A-Z][^\n]+)',  # "1. SECTION TITLE"
        r'^(\d+)\s+([A-Z][A-Z\s]{3,})',  # "1 SECTION TITLE" (no period, all caps)
        r'^Section\s+(\d+)\s*[:\-]?\s*([^\n]+)',  # "Section 1: Title"
        r'^SECTION\s+(\d+)\s*[:\-]?\s*([^\n]+)',  # "SECTION 1 - TITLE"
        r'^Article\s+([IVX]+)\s*[:\-]?\s*([^\n]+)',  # "Article I: Title"
        r'^([IVX]+)\.\s+([A-Z][^\n]+)',  # "I. TITLE" (Roman numerals)
        r'^([A-Z])\.\s+([A-Z][^\n]{5,})',  # "A. SECTION TITLE" (single letter, min 5 chars)
    ]

    # Regex patterns for clause numbering
    # Ordered by specificity (most specific first)
    CLAUSE_PATTERNS = [
        r'^(\d+\.\d+\.\d+)\s+(.+)',  # "1.1.1 Sub-clause text"
        r'^(\d+\.\d+)\s+(.+)',  # "1.1 Clause text"
        r'^\((\d+)\)\s+(.+)',  # "(1) Clause text"
        r'^(\d+)\)\s+(.+)',  # "1) Clause text"
        r'^\(([a-zA-Z])\)\s+(.+)',  # "(a) or (A) Clause text"
        r'^([a-z])\)\s+(.+)',  # "a) Clause text"
        r'^([A-Z])\.\s+(.+)',  # "A. Clause text"
        r'^([ivx]+)\.\s+(.+)',  # "i. Clause text" (lowercase Roman)
        r'^([IVX]+)\.\s+(.+)',  # "I. Clause text" (uppercase Roman)
    ]

    # Bullet patterns (treated as clauses)
    BULLET_PATTERNS = [
        r'^\-\s+(.+)',  # "- Bullet point"
        r'^\*\s+(.+)',  # "* Bullet point"
        r'^\•\s+(.+)',  # "• Bullet point"
        r'^●\s+(.+)',  # "● Bullet point"
        r'^○\s+(.+)',  # "○ Bullet point"
    ]

    def __init__(self, debug: bool = False):
        """Initialize structure extractor.

        Args:
            debug: Enable debug logging for pattern matching
        """
        self.debug = debug

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for better pattern matching.

        Args:
            text: Raw text

        Returns:
            Normalized text
        """
        # Handle different line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove excessive blank lines (keep max 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text

    async def extract_structure(self, text: str) -> Dict[str, Any]:
        """
        Extract hierarchical structure from T&C document.

        Strategy:
        1. Normalize text
        2. Try section patterns (ordered by specificity)
        3. If sections found, extract clauses within each
        4. If no clear structure, use paragraph-based fallback
        5. Track hierarchy

        Args:
            text: Full document text

        Returns:
            dict: {
                "sections": List[dict],
                "num_sections": int,
                "num_clauses": int,
                "extraction_method": str  # "pattern" or "paragraph"
            }
        """
        if self.debug:
            logger.info(f"Extracting structure from document ({len(text)} chars)")

        # Normalize text
        text = self._normalize_text(text)

        sections = []
        extraction_method = "pattern"

        # Try each section pattern
        for pattern_idx, pattern in enumerate(self.SECTION_PATTERNS):
            sections = await self._extract_sections_with_pattern(text, pattern)

            if sections and len(sections) >= 3:
                if self.debug:
                    logger.info(f"✓ Pattern {pattern_idx + 1} matched: {len(sections)} sections")
                    logger.info(f"  Pattern: {pattern}")
                break
            elif sections and self.debug:
                logger.debug(f"✗ Pattern {pattern_idx + 1}: Only {len(sections)} sections (need >=3)")

        # Fallback: No clear section structure
        if not sections or len(sections) < 3:
            if self.debug:
                logger.warning("No clear section structure, using paragraph fallback")

            sections = await self._extract_paragraphs_as_sections(text)
            extraction_method = "paragraph"

        # Extract clauses for each section
        total_clauses = 0
        for section in sections:
            clauses = await self._extract_clauses(section["content"])
            section["clauses"] = clauses
            total_clauses += len(clauses)

            if self.debug and len(clauses) > 0:
                logger.debug(f"Section '{section['title'][:30]}...': {len(clauses)} clauses")

        if self.debug:
            logger.info(f"Final extraction: {len(sections)} sections, {total_clauses} clauses")

        return {
            "sections": sections,
            "num_sections": len(sections),
            "num_clauses": total_clauses,
            "extraction_method": extraction_method,
        }

    async def _extract_sections_with_pattern(
        self, text: str, pattern: str
    ) -> List[Dict[str, Any]]:
        """
        Extract sections using a specific regex pattern.

        Args:
            text: Document text
            pattern: Regex pattern

        Returns:
            List[dict]: List of sections
        """
        sections = []
        lines = text.split("\n")

        # Find all section positions
        section_positions = []
        for i, line in enumerate(lines):
            match = re.match(pattern, line.strip(), re.MULTILINE)
            if match:
                section_num = match.group(1)
                section_title = match.group(2).strip() if match.lastindex >= 2 else ""
                section_positions.append((i, section_num, section_title))

        # Extract content for each section
        for idx, (line_num, sec_num, sec_title) in enumerate(section_positions):
            if idx < len(section_positions) - 1:
                end_line = section_positions[idx + 1][0]
            else:
                end_line = len(lines)

            content_lines = lines[line_num:end_line]
            content = "\n".join(content_lines).strip()

            sections.append({
                "number": sec_num,
                "title": sec_title,
                "content": content,
                "clauses": [],
            })

        return sections

    async def _extract_paragraphs_as_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Fallback: Split text into paragraphs when no section pattern matches.

        This ensures we still get multiple "clauses" even from poorly formatted documents.

        Args:
            text: Document text

        Returns:
            List[dict]: Paragraphs as pseudo-sections
        """
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)

        # Filter out very short paragraphs (< 50 chars)
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) >= 50]

        if self.debug:
            logger.info(f"Paragraph fallback: {len(paragraphs)} paragraphs found")

        sections = []
        for idx, para in enumerate(paragraphs, 1):
            # Use first 50 chars as title
            title = para[:50].replace('\n', ' ') + "..." if len(para) > 50 else para

            sections.append({
                "number": str(idx),
                "title": title,
                "content": para,
                "clauses": [],
            })

        return sections

    async def _extract_clauses(self, section_text: str) -> List[Dict[str, Any]]:
        """
        Extract clauses from section text.

        Tries clause patterns, then bullet patterns, then falls back to
        treating entire section as one clause.

        Args:
            section_text: Text of a section

        Returns:
            List[dict]: List of clauses
        """
        # Try clause patterns
        for pattern in self.CLAUSE_PATTERNS:
            found_clauses = await self._extract_clauses_with_pattern(section_text, pattern)
            if found_clauses and len(found_clauses) >= 2:
                if self.debug:
                    logger.debug(f"  Clause pattern matched: {pattern} ({len(found_clauses)} clauses)")
                return found_clauses

        # Try bullet patterns
        for pattern in self.BULLET_PATTERNS:
            found_clauses = await self._extract_clauses_with_pattern(section_text, pattern)
            if found_clauses and len(found_clauses) >= 2:
                if self.debug:
                    logger.debug(f"  Bullet pattern matched: {pattern} ({len(found_clauses)} clauses)")
                # For bullets, add a generic clause ID (no group 1)
                for clause in found_clauses:
                    if 'id' not in clause:
                        clause['id'] = str(found_clauses.index(clause) + 1)
                return found_clauses

        # Fallback: treat entire section as one clause
        if self.debug and len(section_text) > 100:
            logger.debug(f"  No clause pattern matched, using entire section as 1 clause")

        return [{"id": "1", "text": section_text}]

    async def _extract_clauses_with_pattern(
        self, text: str, pattern: str
    ) -> List[Dict[str, Any]]:
        """
        Extract clauses using a specific regex pattern.

        Args:
            text: Section text
            pattern: Regex pattern

        Returns:
            List[dict]: List of clauses
        """
        clauses = []
        lines = text.split("\n")

        # Find all clause positions
        clause_positions = []
        for i, line in enumerate(lines):
            match = re.match(pattern, line.strip())
            if match:
                # Handle both numbered clauses (group 1) and bullets (no group 1)
                clause_id = match.group(1) if match.lastindex >= 1 else str(i)
                clause_positions.append((i, clause_id))

        # Extract content for each clause
        for idx, (line_num, clause_id) in enumerate(clause_positions):
            if idx < len(clause_positions) - 1:
                end_line = clause_positions[idx + 1][0]
            else:
                end_line = len(lines)

            content_lines = lines[line_num:end_line]
            content = "\n".join(content_lines).strip()

            clauses.append({"id": clause_id, "text": content})

        return clauses

    async def extract_structure_with_stats(self, text: str) -> Dict[str, Any]:
        """
        Extract structure and return detailed statistics.

        Useful for debugging and verification.

        Args:
            text: Document text

        Returns:
            dict with structure + stats
        """
        result = await self.extract_structure(text)

        # Calculate statistics
        clause_counts = [len(s['clauses']) for s in result['sections']]

        stats = {
            **result,
            "stats": {
                "total_chars": len(text),
                "total_lines": len(text.split('\n')),
                "avg_clauses_per_section": sum(clause_counts) / len(clause_counts) if clause_counts else 0,
                "min_clauses": min(clause_counts) if clause_counts else 0,
                "max_clauses": max(clause_counts) if clause_counts else 0,
                "sections_with_multiple_clauses": sum(1 for c in clause_counts if c > 1),
            }
        }

        return stats
