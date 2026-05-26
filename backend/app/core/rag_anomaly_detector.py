"""
RAG-Based Anomaly Detection System.

This module implements TRUE RAG (Retrieval-Augmented Generation) for anomaly detection:
1. Retrieves similar clauses from a baseline corpus (Pinecone)
2. Calculates ACTUAL prevalence based on real T&C data
3. Applies risk scoring: Risk = Unusualness × Harm × Enforceability
4. Adds context tags (Industry Standard, Required by Platform, etc.)

Key Improvement over Pattern Matching:
- Pattern matching: "Does clause contain keyword X?" → Binary flag
- RAG-based: "How common is this clause across 50+ real T&Cs?" → Calculated prevalence

This fixes the overinflation problem where standard clauses (Apple boilerplate,
account termination, reverse engineering) were incorrectly rated as HIGH risk.

RAG WORKFLOW:
1. Embed the clause using sentence-transformers
2. Query Pinecone baseline namespace for similar clauses (top_k=30)
3. Calculate prevalence = (docs with similar clause) / (total docs in baseline)
4. Use retrieved clauses to determine context (industry standard, platform required, etc.)
5. Apply harm scoring based on detected patterns + RAG context
"""

import logging
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.core.constants import (
    ThreatLevel,
    CommonnessLevel,
    DisplayCategory,
    PATTERN_THREAT_LEVELS,
    CommonnessThresholds,
    get_display_category,
    get_threat_level_from_score,
)

logger = logging.getLogger(__name__)

# =============================================================================
# RAG CACHE - Speed up repeated queries
# =============================================================================
# Cache structure: {text_hash: (prevalence, similar_count, total_docs, retrieved_clauses, timestamp)}
_rag_cache: Dict[str, Tuple[float, int, int, List[Dict], float]] = {}
_CACHE_TTL = 3600  # 1 hour cache TTL


def _get_cache_key(text: str) -> str:
    """Generate cache key from text."""
    return hashlib.md5(text[:500].encode()).hexdigest()


def _get_cached_rag_result(text: str) -> Optional[Tuple[float, int, int, List[Dict]]]:
    """Get cached RAG result if available and not expired."""
    cache_key = _get_cache_key(text)
    if cache_key in _rag_cache:
        prevalence, similar_count, total_docs, retrieved, timestamp = _rag_cache[cache_key]
        if time.time() - timestamp < _CACHE_TTL:
            logger.debug(f"RAG cache hit for {cache_key[:8]}...")
            return prevalence, similar_count, total_docs, retrieved
        else:
            # Expired, remove from cache
            del _rag_cache[cache_key]
    return None


def _set_cached_rag_result(text: str, prevalence: float, similar_count: int,
                           total_docs: int, retrieved: List[Dict]):
    """Cache RAG result."""
    cache_key = _get_cache_key(text)
    _rag_cache[cache_key] = (prevalence, similar_count, total_docs, retrieved, time.time())
    logger.debug(f"RAG cached result for {cache_key[:8]}...")


# =============================================================================
# CONTEXT TAGS - Explain WHY a clause exists
# =============================================================================

class ContextTag(str, Enum):
    """Context tags that explain why a clause exists."""
    INDUSTRY_STANDARD = "industry_standard"      # 70%+ of similar services have this
    REQUIRED_BY_PLATFORM = "required_by_platform"  # Apple/Google/etc require this
    USER_TRIGGERED = "user_triggered"            # Only applies if USER violates terms
    COMPANY_TRIGGERED = "company_triggered"      # Company can invoke at discretion
    LEGALLY_REQUIRED = "legally_required"        # Law requires this (GDPR, CCPA, etc.)
    UNUSUAL = "unusual"                          # <30% prevalence - genuinely rare
    MODERATELY_UNUSUAL = "moderately_unusual"    # 30-50% prevalence


# =============================================================================
# KNOWN BOILERPLATE PATTERNS - Should NOT be flagged as high risk
# =============================================================================

# These are KNOWN standard clauses that should be LOW risk regardless of keywords
PLATFORM_REQUIRED_PATTERNS = {
    # Apple App Store Required
    "apple_no_warranty": [
        "apple has no warranty obligation",
        "apple will have no obligation",
        "apple is not responsible",
        "apple disclaims",
        "apple inc",
    ],
    "apple_maintenance": [
        "apple has no obligation whatsoever to furnish",
        "maintenance and support services",
    ],
    # Google Play Required
    "google_play_terms": [
        "google play",
        "google llc",
        "google has no obligation",
    ],
}

INDUSTRY_STANDARD_PATTERNS = {
    # Found in 80%+ of T&Cs - should be LOW risk
    "intro_boilerplate": [
        "these terms govern your use",
        "terms of service govern",
        "by using this service you agree",
        "by using our services",
        "please read these terms carefully",
        "your relationship with us",
        "agreement between you and",
        "agree to be bound",
        "you agree to these terms",
    ],
    "standard_termination": [
        "we may terminate",
        "suspend your account",
        "discontinue the service",
        "at our sole discretion",  # Common but needs context
    ],
    "standard_ip_protection": [
        "reverse engineer",
        "decompile",
        "disassemble",
        "create derivative works",  # Standard in 80%+ of software
    ],
    "standard_warranty": [
        "as is",
        "without warranty",
        "no warranties",
        "disclaims all warranties",
    ],
    "standard_liability": [
        "limitation of liability",
        "not liable for",
        "indirect damages",
        "consequential damages",
    ],
}

# Patterns that indicate USER-triggered liability (not unfair)
USER_TRIGGERED_PATTERNS = [
    "your breach",
    "your violation",
    "your content",
    "you are responsible",
    "your actions",
    "arising from your",
    "resulting from your",
    "caused by your",
]


@dataclass
class RAGAnomalyResult:
    """Result from RAG-based anomaly detection."""
    clause_text: str
    clause_number: str = ""
    section: str = ""

    # RAG-calculated prevalence (from actual corpus)
    corpus_prevalence: float = 0.5  # 0-1, calculated from baseline
    similar_clauses_found: int = 0
    total_corpus_docs: int = 50  # Size of baseline corpus

    # Risk assessment
    harm_score: float = 5.0  # 1-10, based on potential consumer harm
    unusualness_score: float = 5.0  # 1-10, inverse of prevalence
    enforceability_score: float = 5.0  # 1-10, how likely to be enforced

    # Final risk
    risk_score: float = 5.0  # Combined score
    risk_level: str = "medium"  # low/medium/high/critical

    # Context
    context_tags: List[ContextTag] = field(default_factory=list)
    context_explanation: str = ""

    # Matched patterns
    detected_patterns: List[str] = field(default_factory=list)
    is_anomalous: bool = False

    # Display
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    commonness_level: CommonnessLevel = CommonnessLevel.COMMON
    display_category: DisplayCategory = DisplayCategory.STANDARD_TERMS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_text": self.clause_text,
            "clause_number": self.clause_number,
            "section": self.section,
            "corpus_prevalence": self.corpus_prevalence,
            "similar_clauses_found": self.similar_clauses_found,
            "total_corpus_docs": self.total_corpus_docs,
            "harm_score": self.harm_score,
            "unusualness_score": self.unusualness_score,
            "enforceability_score": self.enforceability_score,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "context_tags": [t.value for t in self.context_tags],
            "context_explanation": self.context_explanation,
            "detected_patterns": self.detected_patterns,
            "is_anomalous": self.is_anomalous,
            "threat_level": self.threat_level.value,
            "commonness_level": self.commonness_level.value,
            "display_category": self.display_category.value,
        }


class RAGAnomalyDetector:
    """
    RAG-Based Anomaly Detector.

    Uses retrieval from a baseline corpus to calculate ACTUAL prevalence,
    then applies risk scoring based on:
    - Unusualness (inverse of prevalence)
    - Harm potential (how much it could hurt the user)
    - Enforceability (how likely the company is to enforce it)

    This fixes the overinflation problem where standard clauses were
    incorrectly flagged as high risk.

    RAG Strategy:
    1. Query Pinecone for similar clauses (top_k=30, threshold=0.3)
    2. Count unique documents with similar content
    3. Calculate prevalence = similar_docs / total_docs
    4. Combine with pattern matching for comprehensive detection
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        pinecone_service: Optional[PineconeService] = None,
        baseline_namespace: str = "baseline",
        similarity_threshold: float = 0.30,  # Lower threshold since embeddings are padded
    ):
        self.embedding_service = embedding_service
        self.pinecone_service = pinecone_service
        self.baseline_namespace = baseline_namespace
        self.similarity_threshold = similarity_threshold  # 0.3 for padded 384->1536 embeddings

        # Harm scores by pattern type (1-10)
        self.harm_scores = {
            # CRITICAL harm (9-10)
            "data_selling": 10,
            "data_sharing_marketing": 10,  # Sharing with third parties for marketing
            "biometric_data_collection": 10,
            "biometric_data": 10,
            "rights_waiver": 9,
            "perpetual_irrevocable_license": 9,
            "one_year_limitation": 9,  # Very unusual, very harmful

            # HIGH harm (7-8)
            "forced_arbitration_class_waiver": 8,
            "broad_content_license": 8,  # Worldwide, royalty-free, sub-licensable, transferable
            "broad_indemnification": 7,
            "user_content_license": 8,  # Other users can use your content
            "unilateral_termination_no_reason": 7,
            "fund_holds": 7,

            # MEDIUM harm (5-6)
            "auto_renewal": 6,
            "price_changes": 5,
            "content_removal": 5,
            "account_inactivity": 5,

            # LOW harm (3-4) - Standard protection clauses
            "standard_termination": 3,  # 90% of services have this
            "standard_liability": 3,
            "standard_warranty": 3,
            "reverse_engineering": 2,  # 80% of software has this
            "apple_boilerplate": 2,
            "intro_boilerplate": 1,
        }

    async def detect_anomalies(
        self,
        clauses: List[Dict[str, Any]],
        industry: str = "general",
        service_type: str = "general",
    ) -> List[RAGAnomalyResult]:
        """
        Detect anomalies using RAG-based baseline comparison.

        For each clause:
        1. Embed the clause
        2. Query baseline corpus for similar clauses
        3. Calculate prevalence from matches
        4. Apply context tags
        5. Calculate final risk score

        Args:
            clauses: List of clause dicts with 'text', 'clause_number', 'section'
            industry: Industry for context (social_media, financial, etc.)
            service_type: Service type for context

        Returns:
            List of RAGAnomalyResult objects
        """
        results = []

        for clause in clauses:
            result = await self.analyze_clause(
                clause_text=clause.get("text", ""),
                clause_number=clause.get("clause_number", ""),
                section=clause.get("section", ""),
                industry=industry,
                service_type=service_type,
            )
            results.append(result)

        # Sort by risk score (highest first)
        results.sort(key=lambda x: x.risk_score, reverse=True)

        return results

    async def analyze_clause(
        self,
        clause_text: str,
        clause_number: str,
        section: str,
        industry: str,
        service_type: str,
    ) -> RAGAnomalyResult:
        """Analyze a single clause using RAG."""

        result = RAGAnomalyResult(
            clause_text=clause_text,
            clause_number=clause_number,
            section=section,
        )

        # Step 1: Check for platform-required boilerplate (instant LOW risk)
        platform_match = self._check_platform_required(clause_text)
        if platform_match:
            result.context_tags.append(ContextTag.REQUIRED_BY_PLATFORM)
            result.context_explanation = f"Required by {platform_match} - standard for all apps"
            result.corpus_prevalence = 0.95
            result.harm_score = 2
            result.risk_score = 2
            result.risk_level = "low"
            result.threat_level = ThreatLevel.INFO
            result.commonness_level = CommonnessLevel.UNIVERSAL
            result.display_category = DisplayCategory.STANDARD_TERMS
            return result

        # Step 2: Check for industry-standard boilerplate
        standard_match = self._check_industry_standard(clause_text)
        if standard_match:
            result.context_tags.append(ContextTag.INDUSTRY_STANDARD)
            result.corpus_prevalence = 0.85

        # Step 3: Check if user-triggered (indemnification for YOUR actions)
        if self._is_user_triggered(clause_text):
            result.context_tags.append(ContextTag.USER_TRIGGERED)
            result.context_explanation = "Only applies if YOU breach the terms"

        # Step 4: RAG - Query baseline corpus for similar clauses
        # This is the TRUE RAG step - we retrieve similar clauses from Pinecone
        rag_prevalence, similar_count, total_docs, retrieved_clauses = await self._query_baseline(clause_text)
        result.similar_clauses_found = similar_count
        result.total_corpus_docs = total_docs

        # Step 4b: Combine RAG prevalence with pattern-based estimation
        # This handles cases where RAG finds few matches due to embedding limitations
        corpus_prevalence = self._combine_rag_and_pattern_prevalence(
            rag_prevalence=rag_prevalence,
            rag_similar_count=similar_count,
            clause_text=clause_text,
        )
        result.corpus_prevalence = corpus_prevalence

        logger.debug(
            f"Combined prevalence: RAG={rag_prevalence:.0%} ({similar_count} matches) -> Combined={corpus_prevalence:.0%}"
        )

        # Step 4c: Analyze retrieved clauses for additional context
        rag_analysis = self._analyze_retrieved_clauses(retrieved_clauses)
        if rag_analysis.get("highly_similar_count", 0) >= 3:
            # If we found 3+ highly similar clauses, this is definitely industry standard
            if ContextTag.INDUSTRY_STANDARD not in result.context_tags:
                result.context_tags.append(ContextTag.INDUSTRY_STANDARD)
            logger.debug(
                f"RAG found {rag_analysis['highly_similar_count']} highly similar clauses - marking as industry standard"
            )

        # Step 5: Detect specific risk patterns
        detected_patterns = self._detect_patterns(clause_text)
        result.detected_patterns = detected_patterns

        # Step 6: Calculate harm score
        harm_score = self._calculate_harm_score(detected_patterns, clause_text)
        result.harm_score = harm_score

        # Step 7: Calculate unusualness score (inverse of prevalence)
        unusualness = self._calculate_unusualness(corpus_prevalence)
        result.unusualness_score = unusualness

        # Step 8: Calculate enforceability
        enforceability = self._calculate_enforceability(clause_text, detected_patterns)
        result.enforceability_score = enforceability

        # Step 9: Calculate final risk score
        # Formula: Risk = (Harm × 0.5) + (Unusualness × 0.3) + (Enforceability × 0.2)
        # RAG-based prevalence is used to cap risk for common clauses
        raw_risk = (harm_score * 0.5) + (unusualness * 0.3) + (enforceability * 0.2)

        # Apply RAG-based prevalence cap
        # High prevalence (from RAG) means this is common across T&Cs
        if corpus_prevalence >= 0.70:
            # RAG shows 70%+ of T&Cs have this - cap at medium unless extremely harmful
            raw_risk = min(raw_risk, 5.0) if harm_score < 9 else raw_risk
            if ContextTag.INDUSTRY_STANDARD not in result.context_tags:
                result.context_tags.append(ContextTag.INDUSTRY_STANDARD)
        elif corpus_prevalence >= 0.50:
            # Common but not universal
            raw_risk = min(raw_risk, 6.5) if harm_score < 9 else raw_risk
        elif corpus_prevalence < 0.30:
            # Genuinely unusual - boost risk slightly
            result.context_tags.append(ContextTag.UNUSUAL)
            raw_risk = min(raw_risk * 1.1, 10.0)

        result.risk_score = round(raw_risk, 1)

        # Step 10: Determine risk level
        result.risk_level = self._get_risk_level(result.risk_score)
        result.is_anomalous = result.risk_score >= 5.0 or corpus_prevalence < 0.30

        # Step 11: Map to threat/commonness levels
        result.threat_level = get_threat_level_from_score(result.harm_score)
        result.commonness_level = CommonnessThresholds.get_level(corpus_prevalence)
        result.display_category = get_display_category(result.threat_level, result.commonness_level)

        # Step 12: Generate context explanation
        if not result.context_explanation:
            result.context_explanation = self._generate_context_explanation(result)

        return result

    def _check_platform_required(self, text: str) -> Optional[str]:
        """Check if clause is required by a platform (Apple, Google)."""
        text_lower = text.lower()

        for platform, patterns in PLATFORM_REQUIRED_PATTERNS.items():
            if any(p in text_lower for p in patterns):
                if "apple" in platform:
                    return "Apple App Store"
                elif "google" in platform:
                    return "Google Play Store"

        return None

    def _check_industry_standard(self, text: str) -> Optional[str]:
        """Check if clause matches known industry-standard patterns."""
        text_lower = text.lower()

        for category, patterns in INDUSTRY_STANDARD_PATTERNS.items():
            match_count = sum(1 for p in patterns if p in text_lower)
            # For intro_boilerplate, one match is enough (these are unique phrases)
            # For other patterns, need at least 2 matches
            if category == "intro_boilerplate" and match_count >= 1:
                return category
            elif match_count >= 2:
                return category

        return None

    def _is_user_triggered(self, text: str) -> bool:
        """Check if the clause is user-triggered (only applies if user violates)."""
        text_lower = text.lower()
        return any(p in text_lower for p in USER_TRIGGERED_PATTERNS)

    async def _query_baseline(self, clause_text: str) -> Tuple[float, int, int, List[Dict]]:
        """
        Query baseline corpus using RAG to calculate ACTUAL prevalence.

        This is TRUE RAG - we embed the clause and find similar clauses
        in the Pinecone baseline corpus to determine how common it is.

        Returns:
            (prevalence, similar_count, total_docs, retrieved_clauses)
        """
        # Check cache first for speed
        cached = _get_cached_rag_result(clause_text)
        if cached:
            return cached

        # If RAG services not available, fallback to pattern-based estimation
        if not self.embedding_service or not self.pinecone_service:
            logger.debug("RAG services not available, using pattern-based estimation")
            prevalence, similar, total = self._estimate_prevalence(clause_text)
            return prevalence, similar, total, []

        try:
            # STEP 1: Embed the clause using sentence-transformers
            logger.debug(f"RAG: Embedding clause ({len(clause_text)} chars)...")
            embedding = await self.embedding_service.create_embedding(clause_text)

            # STEP 2: Query Pinecone baseline namespace for similar clauses
            logger.debug(f"RAG: Querying Pinecone baseline namespace...")
            matches = await self.pinecone_service.query(
                query_embedding=embedding,
                namespace=self.baseline_namespace,
                top_k=30,  # Get top 30 similar clauses
                include_metadata=True,
            )

            # STEP 3: Analyze retrieved clauses
            similar_docs = set()
            retrieved_clauses = []

            for match in matches:
                score = match.get("score", 0)
                metadata = match.get("metadata", {})
                doc_id = metadata.get("document_id", "")
                text = metadata.get("text", "")

                # Store retrieved clause for context analysis
                if score >= 0.5:  # Include moderately similar clauses
                    retrieved_clauses.append({
                        "score": score,
                        "text": text[:500],  # Truncate for efficiency
                        "document_id": doc_id,
                        "company": metadata.get("company_name", ""),
                        "industry": metadata.get("industry", ""),
                    })

                # Count as "similar" if above threshold
                if score >= self.similarity_threshold and doc_id:
                    similar_docs.add(doc_id)

            # STEP 4: Get total docs in baseline for prevalence calculation
            try:
                stats = self.pinecone_service.index.describe_index_stats()
                total_vectors = stats.get("namespaces", {}).get(
                    self.baseline_namespace, {}
                ).get("vector_count", 0)

                # Estimate unique docs (average ~20 clauses per T&C document)
                total_docs = max(1, total_vectors // 20) if total_vectors > 0 else 50
            except Exception:
                total_docs = 50  # Default if stats unavailable

            # STEP 5: Calculate prevalence
            prevalence = len(similar_docs) / total_docs if total_docs > 0 else 0.5

            logger.info(
                f"RAG query complete: {len(similar_docs)}/{total_docs} docs have similar clause "
                f"(prevalence: {prevalence:.0%}, retrieved: {len(retrieved_clauses)} clauses)"
            )

            # Cache the result for speed
            _set_cached_rag_result(clause_text, prevalence, len(similar_docs),
                                   total_docs, retrieved_clauses)

            return prevalence, len(similar_docs), total_docs, retrieved_clauses

        except Exception as e:
            logger.warning(f"RAG query failed, using pattern-based estimation: {e}")
            prevalence, similar, total = self._estimate_prevalence(clause_text)
            return prevalence, similar, total, []

    def _combine_rag_and_pattern_prevalence(
        self,
        rag_prevalence: float,
        rag_similar_count: int,
        clause_text: str,
    ) -> float:
        """
        Combine RAG-based prevalence with pattern-based estimation.

        When RAG finds few matches (due to embedding limitations), we use
        pattern matching as a fallback to estimate prevalence.

        Strategy:
        - If RAG finds matches (>0), trust RAG
        - If RAG finds nothing, check pattern-based estimation
        - Blend results if both have data

        Returns:
            Combined prevalence estimate (0-1)
        """
        # Get pattern-based estimate
        pattern_prevalence, _, _ = self._estimate_prevalence(clause_text)

        # If RAG found matches, weight it higher
        if rag_similar_count > 0:
            # RAG found something - blend 70% RAG, 30% pattern
            return (rag_prevalence * 0.7) + (pattern_prevalence * 0.3)
        else:
            # RAG found nothing - check if pattern matching thinks it's common
            # If pattern says >70% common, trust pattern
            if pattern_prevalence >= 0.70:
                logger.debug(
                    f"RAG found no matches but pattern says {pattern_prevalence:.0%} prevalence - using pattern"
                )
                return pattern_prevalence
            else:
                # Neither found strong evidence - default to moderately common
                return 0.50

    def _analyze_retrieved_clauses(self, retrieved: List[Dict]) -> Dict[str, Any]:
        """
        Analyze retrieved clauses to determine context.

        Uses the retrieved clauses from RAG to understand:
        - Which industries have this clause
        - Which companies have this clause
        - Average similarity score

        Returns:
            Dict with analysis results
        """
        if not retrieved:
            return {"industries": [], "companies": [], "avg_similarity": 0}

        industries = []
        companies = []
        total_score = 0

        for clause in retrieved:
            if clause.get("industry"):
                industries.append(clause["industry"])
            if clause.get("company"):
                companies.append(clause["company"])
            total_score += clause.get("score", 0)

        return {
            "industries": list(set(industries)),
            "companies": list(set(companies)),
            "avg_similarity": total_score / len(retrieved) if retrieved else 0,
            "highly_similar_count": sum(1 for c in retrieved if c.get("score", 0) >= 0.85),
        }

    def _estimate_prevalence(self, text: str) -> Tuple[float, int, int]:
        """
        Estimate prevalence when RAG is unavailable.
        Uses pattern matching as fallback.
        """
        text_lower = text.lower()

        # Check platform-required (95% prevalence)
        if self._check_platform_required(text):
            return 0.95, 48, 50

        # Check industry-standard (85% prevalence)
        if self._check_industry_standard(text):
            return 0.85, 43, 50

        # Check for common patterns
        common_patterns = [
            ("terminate", 0.90),
            ("suspend", 0.85),
            ("sole discretion", 0.80),
            ("warranty", 0.85),
            ("liability", 0.85),
            ("reverse engineer", 0.80),
            ("decompile", 0.80),
            ("as is", 0.85),
        ]

        for pattern, prevalence in common_patterns:
            if pattern in text_lower:
                return prevalence, int(prevalence * 50), 50

        # Default: moderately common
        return 0.50, 25, 50

    def _detect_patterns(self, text: str) -> List[str]:
        """Detect specific risk patterns in the clause."""
        text_lower = text.lower()
        detected = []

        # High-harm patterns (CRITICAL/HIGH risk) - need 2+ keyword matches
        high_harm = {
            "perpetual_irrevocable_license": ["perpetual", "irrevocable", "worldwide"],
            "one_year_limitation": ["one year", "12 months", "within one (1) year"],
            "forced_arbitration_class_waiver": ["arbitration", "class action", "waive"],
            "broad_indemnification": ["indemnify", "defend", "hold harmless"],
            "biometric_data": ["biometric", "faceprint", "voiceprint", "facial recognition"],
        }

        for pattern_name, keywords in high_harm.items():
            if sum(1 for k in keywords if k in text_lower) >= 2:
                detected.append(pattern_name)

        # BROAD CONTENT LICENSE detection - catches licenses that grant extensive rights
        # even without "perpetual" or "irrevocable" language
        # TikTok uses: "worldwide", "royalty-free", "sub-licensable", "transferable"
        broad_license_keywords = [
            "worldwide",
            "royalty-free",
            "royalty free",
            "sub-licensable",
            "sublicensable",
            "sub-license",
            "sublicense",
            "transferable",
            "non-exclusive",
            "license to use",
            "grant us",
            "grant tiktok",
            "you grant",
            "license you grant",
        ]

        # Also check for context words that indicate content licensing
        license_context_words = [
            "user content",
            "your content",
            "content you",
            "post",
            "upload",
            "submit",
            "share",
            "create",
        ]

        # Count broad license indicators
        broad_license_count = sum(1 for k in broad_license_keywords if k in text_lower)
        has_license_context = any(k in text_lower for k in license_context_words)

        # If we find 3+ broad license keywords AND it's about content → HIGH risk
        if broad_license_count >= 3 and has_license_context:
            # Check if we already detected perpetual_irrevocable_license
            if "perpetual_irrevocable_license" not in detected:
                detected.append("broad_content_license")
        # Even 2 keywords with context is concerning
        elif broad_license_count >= 2 and has_license_context:
            # Only add if "worldwide" + one other right-granting keyword
            if "worldwide" in text_lower:
                if "perpetual_irrevocable_license" not in detected:
                    detected.append("broad_content_license")

        # User-to-user content license (other users can use your content)
        user_to_user_keywords = [
            "grant to each user",
            "license to other users",
            "other users may",
            "other users of",
            "licence to access",
            "license to access",
            "each user of the services",
        ]
        if any(k in text_lower for k in user_to_user_keywords):
            detected.append("user_content_license")

        # Critical harm patterns (single keyword is enough)
        critical_patterns = {
            "data_selling": ["sell your data", "sell your information", "monetize your data",
                            "sell or share your personal", "share your personal information with third parties for marketing"],
            "data_sharing_marketing": ["marketing purposes without your consent", "third parties for marketing"],
        }

        for pattern_name, keywords in critical_patterns.items():
            if any(k in text_lower for k in keywords):
                detected.append(pattern_name)

        # Medium-harm patterns
        medium_harm = {
            "auto_renewal": ["auto-renew", "automatically renew", "renewal"],
            "price_changes": ["price may change", "change the price", "modify the fee"],
            "content_removal": ["remove your content", "delete your content"],
            "account_inactivity": ["reclaim your account", "inactive for", "not logged in for"],
        }

        for pattern_name, keywords in medium_harm.items():
            if any(k in text_lower for k in keywords):
                detected.append(pattern_name)

        return detected

    def _calculate_harm_score(self, patterns: List[str], text: str) -> float:
        """Calculate harm score based on detected patterns."""
        if not patterns:
            return 3.0  # Default low harm if no patterns

        # Get max harm from detected patterns
        max_harm = 3.0
        for pattern in patterns:
            harm = self.harm_scores.get(pattern, 3.0)
            max_harm = max(max_harm, harm)

        return max_harm

    def _calculate_unusualness(self, prevalence: float) -> float:
        """
        Calculate unusualness score (inverse of prevalence).

        High prevalence (90%) → Low unusualness (2)
        Low prevalence (10%) → High unusualness (9)
        """
        if prevalence >= 0.90:
            return 1.0
        elif prevalence >= 0.70:
            return 3.0
        elif prevalence >= 0.50:
            return 5.0
        elif prevalence >= 0.30:
            return 7.0
        else:
            return 9.0

    def _calculate_enforceability(self, text: str, patterns: List[str]) -> float:
        """Calculate how likely the clause is to be enforced."""
        # Most boilerplate is rarely enforced
        if self._check_industry_standard(text):
            return 3.0

        # User-triggered clauses are more enforceable
        if self._is_user_triggered(text):
            return 7.0

        # Arbitration clauses are highly enforced
        if "arbitration" in text.lower():
            return 9.0

        # Default medium enforceability
        return 5.0

    def _get_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 8.0:
            return "critical"
        elif score >= 6.0:
            return "high"
        elif score >= 4.0:
            return "medium"
        else:
            return "low"

    def _generate_context_explanation(self, result: RAGAnomalyResult) -> str:
        """Generate human-readable context explanation."""
        parts = []

        # Prevalence context
        if result.corpus_prevalence >= 0.70:
            parts.append(f"Found in {result.corpus_prevalence*100:.0f}% of similar services (industry standard)")
        elif result.corpus_prevalence >= 0.30:
            parts.append(f"Found in {result.corpus_prevalence*100:.0f}% of similar services (moderately common)")
        else:
            parts.append(f"Found in only {result.corpus_prevalence*100:.0f}% of similar services (unusual)")

        # Context tags
        if ContextTag.REQUIRED_BY_PLATFORM in result.context_tags:
            parts.append("Required by app platform")
        if ContextTag.USER_TRIGGERED in result.context_tags:
            parts.append("Only applies if you breach the terms")
        if ContextTag.INDUSTRY_STANDARD in result.context_tags:
            parts.append("Standard legal boilerplate")

        return ". ".join(parts)
