"""
Document Type Detector

Automatically detects the type of legal document (ToS, Privacy Policy, EULA, etc.)
based on keyword analysis and structural patterns.
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class DocumentTypeResult:
    """Result of document type detection."""
    document_type: str  # "privacy_policy", "terms_of_service", "eula", "cookie_policy", "other"
    confidence: float  # 0.0 to 1.0
    matched_indicators: List[str]  # List of matched keywords/patterns
    secondary_types: List[Tuple[str, float]]  # Other possible types with confidence


class DocumentTypeDetector:
    """Detects the type of legal document from text content."""

    # Document type patterns with keywords and section indicators
    DOCUMENT_PATTERNS = {
        "privacy_policy": {
            "title_keywords": [
                "privacy policy",
                "privacy notice",
                "privacy statement",
                "data protection policy",
                "data privacy",
                "information we collect",
            ],
            "content_keywords": [
                "personal information",
                "personal data",
                "data we collect",
                "how we use your data",
                "how we collect",
                "data processing",
                "data controller",
                "data processor",
                "gdpr",
                "ccpa",
                "right to access",
                "right to deletion",
                "opt-out",
                "cookies and tracking",
                "third-party services",
                "data retention",
                "data security",
                "data breach",
            ],
            "section_indicators": [
                "information we collect",
                "how we use",
                "data we collect",
                "data sharing",
                "your rights",
                "your privacy rights",
                "data protection",
                "cookies",
                "tracking technologies",
                "third parties",
                "international transfers",
                "children's privacy",
                "california residents",
                "eu residents",
            ],
            "weight": {
                "title": 3.0,
                "content": 1.0,
                "section": 2.0,
            }
        },
        "terms_of_service": {
            "title_keywords": [
                "terms of service",
                "terms and conditions",
                "terms of use",
                "user agreement",
                "service agreement",
                "terms & conditions",
                "tos",
                "t&c",
                "acceptable use",
            ],
            "content_keywords": [
                "user account",
                "account termination",
                "prohibited conduct",
                "acceptable use",
                "service availability",
                "intellectual property",
                "user content",
                "license grant",
                "limitation of liability",
                "indemnification",
                "arbitration",
                "governing law",
                "dispute resolution",
                "warranty disclaimer",
                "suspension of account",
            ],
            "section_indicators": [
                "acceptance of terms",
                "eligibility",
                "account registration",
                "user obligations",
                "prohibited activities",
                "prohibited uses",
                "termination",
                "suspension",
                "intellectual property rights",
                "user-generated content",
                "disclaimers",
                "limitation of liability",
                "indemnification",
                "governing law",
                "dispute resolution",
                "arbitration",
                "modifications to terms",
            ],
            "weight": {
                "title": 3.0,
                "content": 1.0,
                "section": 2.0,
            }
        },
        "eula": {
            "title_keywords": [
                "end user license agreement",
                "eula",
                "software license agreement",
                "license agreement",
                "end-user agreement",
                "software agreement",
            ],
            "content_keywords": [
                "software license",
                "license grant",
                "licensed software",
                "installation",
                "permitted uses",
                "restrictions on use",
                "reverse engineering",
                "decompile",
                "derivative works",
                "source code",
                "updates and upgrades",
                "maintenance",
                "support services",
                "license fee",
                "subscription",
            ],
            "section_indicators": [
                "grant of license",
                "scope of license",
                "restrictions",
                "ownership",
                "intellectual property",
                "updates",
                "support",
                "fees and payment",
                "warranty",
                "limited warranty",
                "license termination",
            ],
            "weight": {
                "title": 3.0,
                "content": 1.5,
                "section": 2.0,
            }
        },
        "cookie_policy": {
            "title_keywords": [
                "cookie policy",
                "cookie notice",
                "cookies policy",
                "use of cookies",
                "about cookies",
            ],
            "content_keywords": [
                "cookies",
                "web beacons",
                "tracking technologies",
                "pixel tags",
                "local storage",
                "session cookies",
                "persistent cookies",
                "first-party cookies",
                "third-party cookies",
                "analytics cookies",
                "advertising cookies",
                "functional cookies",
                "necessary cookies",
                "cookie consent",
                "manage cookies",
                "disable cookies",
            ],
            "section_indicators": [
                "what are cookies",
                "types of cookies",
                "how we use cookies",
                "third-party cookies",
                "managing cookies",
                "cookie preferences",
                "opting out",
            ],
            "weight": {
                "title": 3.0,
                "content": 1.5,
                "section": 2.0,
            }
        },
    }

    def __init__(self):
        """Initialize document type detector."""
        pass

    def detect_type(self, text: str, title: str = "") -> DocumentTypeResult:
        """
        Detect document type from text content.

        Args:
            text: Full document text
            title: Optional document title/filename

        Returns:
            DocumentTypeResult with detected type and confidence
        """
        # Normalize text for matching
        text_lower = text.lower()
        title_lower = title.lower() if title else ""

        # Extract potential section headings (lines that look like titles)
        sections = self._extract_section_headings(text)

        # Score each document type
        scores = {}
        all_matches = {}

        for doc_type, patterns in self.DOCUMENT_PATTERNS.items():
            score = 0.0
            matched_indicators = []

            # Check title keywords
            for keyword in patterns["title_keywords"]:
                if keyword in title_lower or keyword in text_lower[:500]:  # Check first 500 chars
                    score += patterns["weight"]["title"]
                    matched_indicators.append(f"title: {keyword}")

            # Check content keywords
            for keyword in patterns["content_keywords"]:
                if keyword in text_lower:
                    score += patterns["weight"]["content"]
                    matched_indicators.append(f"content: {keyword}")

            # Check section indicators
            for section_keyword in patterns["section_indicators"]:
                if self._section_matches(section_keyword, sections):
                    score += patterns["weight"]["section"]
                    matched_indicators.append(f"section: {section_keyword}")

            scores[doc_type] = score
            all_matches[doc_type] = matched_indicators

        # Normalize scores to confidence (0-1)
        max_score = max(scores.values()) if scores else 0.0

        if max_score == 0.0:
            # No matches found
            return DocumentTypeResult(
                document_type="other",
                confidence=0.0,
                matched_indicators=[],
                secondary_types=[]
            )

        # Get primary type (highest score)
        primary_type = max(scores, key=scores.get)
        primary_score = scores[primary_type]

        # Calculate confidence (with threshold adjustment)
        confidence = min(primary_score / 15.0, 1.0)  # Scale: 15+ points = 100% confidence

        # Get secondary types (sorted by score)
        secondary_types = [
            (doc_type, min(score / 15.0, 1.0))
            for doc_type, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if doc_type != primary_type and score > 0
        ]

        return DocumentTypeResult(
            document_type=primary_type,
            confidence=confidence,
            matched_indicators=all_matches[primary_type][:10],  # Top 10 matches
            secondary_types=secondary_types[:3]  # Top 3 secondary types
        )

    def _extract_section_headings(self, text: str) -> List[str]:
        """
        Extract potential section headings from text.

        Looks for lines that:
        - Are all caps or title case
        - Are short (< 100 chars)
        - Start with numbers or are preceded by blank lines
        """
        lines = text.split('\n')
        sections = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped:
                continue

            # Check if line looks like a heading
            is_heading = (
                # All caps heading
                line_stripped.isupper() and len(line_stripped) < 100
                or
                # Numbered heading (1. SECTION, I. SECTION, etc.)
                re.match(r'^(\d+\.|\d+\)|\w+\.|[IVX]+\.)\s+[A-Z]', line_stripped)
                or
                # Title case after blank line
                (i > 0 and not lines[i-1].strip() and line_stripped[0].isupper() and len(line_stripped) < 100)
            )

            if is_heading:
                sections.append(line_stripped.lower())

        return sections

    def _section_matches(self, keyword: str, sections: List[str]) -> bool:
        """
        Check if keyword matches any section heading.

        Uses fuzzy matching - all words from keyword must appear in section.
        """
        keyword_words = set(keyword.lower().split())

        for section in sections:
            section_words = set(section.split())
            # Check if all keyword words are in section
            if keyword_words.issubset(section_words):
                return True

            # Also check for partial match (at least 60% of words)
            overlap = len(keyword_words.intersection(section_words))
            if overlap / len(keyword_words) >= 0.6:
                return True

        return False

    def get_display_name(self, document_type: str) -> str:
        """
        Get user-friendly display name for document type.

        Args:
            document_type: Internal type identifier

        Returns:
            Human-readable display name
        """
        display_names = {
            "privacy_policy": "Privacy Policy",
            "terms_of_service": "Terms of Service",
            "eula": "End User License Agreement (EULA)",
            "cookie_policy": "Cookie Policy",
            "other": "Legal Document"
        }
        return display_names.get(document_type, "Unknown Document")

    def get_description(self, document_type: str) -> str:
        """
        Get description of what this document type typically contains.

        Args:
            document_type: Internal type identifier

        Returns:
            Description of document type
        """
        descriptions = {
            "privacy_policy": "Describes how personal data is collected, used, shared, and protected.",
            "terms_of_service": "Defines the rules, responsibilities, and limitations for using a service.",
            "eula": "Governs the installation and use of software or applications.",
            "cookie_policy": "Explains the use of cookies and tracking technologies on a website.",
            "other": "Legal agreement or policy document."
        }
        return descriptions.get(document_type, "Legal document of unknown type.")
