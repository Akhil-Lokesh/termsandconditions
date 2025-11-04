"""
Semantic risk pattern detection using embeddings.

Catches rephrased risky clauses that keyword matching misses.
For example:
  - "terminate anytime" vs "end service when we want"
  - "no refunds" vs "all payments are final"
  - "unlimited liability" vs "you're responsible for everything"
"""

from typing import List, Dict, Optional
from app.services.openai_service import OpenAIService
import logging

logger = logging.getLogger(__name__)


class SemanticRiskDetector:
    """Detects risky patterns using semantic similarity (embeddings)."""

    # Known risky clause templates with their embeddings
    # These are canonical examples that will be compared against
    RISKY_TEMPLATES = {
        "unilateral_termination": [
            "We can terminate your account at any time without notice or reason.",
            "Service may be discontinued immediately at our sole discretion.",
            "We reserve the right to end your access without explanation."
        ],
        "unlimited_liability": [
            "You are liable for all damages and agree to indemnify us completely.",
            "You assume full responsibility for any claims against us.",
            "You will defend and hold us harmless from all losses."
        ],
        "forced_arbitration": [
            "You waive your right to sue and agree to binding arbitration only.",
            "No class action lawsuits - all disputes must be resolved individually.",
            "You give up your right to a jury trial and court proceedings."
        ],
        "auto_payment_updates": [
            "We will automatically update your payment method without asking.",
            "Billing information may be changed using account updater services.",
            "New credit card details will be charged without your consent."
        ],
        "no_refund": [
            "All payments are final and non-refundable under any circumstances.",
            "No money back guarantees - all sales are final.",
            "You cannot get a refund even if you cancel immediately."
        ],
        "price_increase_no_notice": [
            "Prices can be changed at any time without informing you.",
            "Fees may increase without prior notification to users.",
            "We can raise rates whenever we want without warning."
        ],
        "content_loss": [
            "We are not responsible if your data is deleted or lost.",
            "Content may be removed at any time without backup or recovery.",
            "No obligation to preserve your files or information."
        ],
        "rights_waiver": [
            "You waive all legal rights and remedies against us.",
            "You give up your right to seek compensation or damages.",
            "You surrender all statutory protections and consumer rights."
        ],
        "unilateral_changes": [
            "Terms can be modified at any time without notifying users.",
            "We may change this agreement whenever we want without warning.",
            "Updates to terms are effective immediately without your consent."
        ],
        "data_sharing": [
            "Your personal information may be sold to third parties.",
            "We can share your data with advertisers and partners.",
            "Information will be transferred to affiliates without restriction."
        ],
        "broad_liability_disclaimer": [
            "No warranty of any kind - use entirely at your own risk.",
            "We are not liable for any damages whatsoever.",
            "Service provided as-is with no guarantees or protections."
        ],
        "broad_usage_rights": [
            "We get unlimited, perpetual, irrevocable rights to your content.",
            "You grant us a worldwide license to use your work for any purpose.",
            "We can sublicense and monetize your content without compensation."
        ]
    }

    # Similarity threshold for semantic matching
    SIMILARITY_THRESHOLD = 0.80  # 80% similarity = likely rephrased risk

    def __init__(self, openai_service: OpenAIService):
        """
        Initialize semantic risk detector.

        Args:
            openai_service: OpenAI service for generating embeddings
        """
        self.openai = openai_service
        self.template_embeddings: Optional[Dict[str, List[List[float]]]] = None

    async def initialize(self):
        """
        Pre-compute embeddings for all risky templates.

        This should be called once at startup to avoid recomputing.
        """
        logger.info("Initializing semantic risk detector - computing template embeddings...")

        self.template_embeddings = {}

        for risk_type, templates in self.RISKY_TEMPLATES.items():
            # Get embeddings for all templates of this risk type
            embeddings = []
            for template in templates:
                try:
                    embedding = await self.openai.create_embedding(template)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for template '{template[:50]}...': {e}")
                    continue

            self.template_embeddings[risk_type] = embeddings
            logger.debug(f"Generated {len(embeddings)} embeddings for {risk_type}")

        total_embeddings = sum(len(e) for e in self.template_embeddings.values())
        logger.info(f"✓ Semantic risk detector initialized with {total_embeddings} template embeddings")

    async def detect_semantic_risks(
        self,
        clause_text: str,
        clause_embedding: Optional[List[float]] = None
    ) -> List[Dict]:
        """
        Detect risky patterns using semantic similarity.

        Args:
            clause_text: The clause text to analyze
            clause_embedding: Pre-computed embedding (optional, will compute if not provided)

        Returns:
            List of detected semantic risks with similarity scores
        """
        if not self.template_embeddings:
            logger.warning("Template embeddings not initialized - call initialize() first")
            return []

        # Get clause embedding
        if clause_embedding is None:
            try:
                clause_embedding = await self.openai.create_embedding(clause_text)
            except Exception as e:
                logger.error(f"Failed to generate embedding for clause: {e}")
                return []

        detected_risks = []

        # Compare against all template embeddings
        for risk_type, template_embeddings in self.template_embeddings.items():
            max_similarity = 0.0
            best_match_idx = -1

            for idx, template_embedding in enumerate(template_embeddings):
                # Compute cosine similarity
                similarity = self._cosine_similarity(clause_embedding, template_embedding)

                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match_idx = idx

            # If similarity exceeds threshold, flag as semantic risk
            if max_similarity >= self.SIMILARITY_THRESHOLD:
                detected_risks.append({
                    "risk_type": risk_type,
                    "similarity": max_similarity,
                    "matched_template": self.RISKY_TEMPLATES[risk_type][best_match_idx],
                    "detection_method": "semantic",
                    "severity": self._determine_severity(risk_type),
                    "description": self._get_risk_description(risk_type)
                })

                logger.info(
                    f"Semantic risk detected: {risk_type} "
                    f"(similarity: {max_similarity:.2%})"
                )

        return detected_risks

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1)
        """
        # Compute cosine similarity without numpy
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_v1 = sum(a * a for a in vec1) ** 0.5
        norm_v2 = sum(b * b for b in vec2) ** 0.5

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        similarity = dot_product / (norm_v1 * norm_v2)

        # Clamp to [0, 1] range
        return max(0.0, min(1.0, similarity))

    def _determine_severity(self, risk_type: str) -> str:
        """
        Determine severity level for a risk type.

        Args:
            risk_type: Type of risk detected

        Returns:
            Severity level (high/medium/low)
        """
        # High severity risks
        high_severity = {
            "unilateral_termination",
            "unlimited_liability",
            "forced_arbitration",
            "auto_payment_updates",
            "price_increase_no_notice",
            "content_loss",
            "rights_waiver"
        }

        if risk_type in high_severity:
            return "high"
        else:
            return "medium"

    def _get_risk_description(self, risk_type: str) -> str:
        """
        Get human-readable description of risk type.

        Args:
            risk_type: Type of risk detected

        Returns:
            Description string
        """
        descriptions = {
            "unilateral_termination": "Company can terminate service without warning or reason",
            "unlimited_liability": "You assume unlimited liability for any issues",
            "forced_arbitration": "You cannot join class action lawsuits",
            "auto_payment_updates": "Automatic payment method updates without explicit consent",
            "no_refund": "Payments are non-refundable",
            "price_increase_no_notice": "Prices can increase without advance notice",
            "content_loss": "Risk of losing your data without compensation",
            "rights_waiver": "You waive important legal rights",
            "unilateral_changes": "Terms can change without notice",
            "data_sharing": "Your data may be shared or sold",
            "broad_liability_disclaimer": "Broad disclaimers limiting company liability",
            "broad_usage_rights": "Company gets broad rights to your content"
        }

        return descriptions.get(risk_type, "Potential consumer risk detected")

    async def augment_indicators(
        self,
        clause_text: str,
        keyword_indicators: List[Dict],
        clause_embedding: Optional[List[float]] = None
    ) -> List[Dict]:
        """
        Augment keyword-based indicators with semantic detection.

        This combines both detection methods for maximum coverage.

        Args:
            clause_text: The clause text
            keyword_indicators: Indicators from keyword matching
            clause_embedding: Pre-computed embedding (optional)

        Returns:
            Combined list of indicators (keyword + semantic)
        """
        # Get semantic risks
        semantic_risks = await self.detect_semantic_risks(clause_text, clause_embedding)

        # Convert semantic risks to indicator format
        semantic_indicators = []
        for risk in semantic_risks:
            # Check if this risk type was already detected by keywords
            already_detected = any(
                ind.get("indicator") == risk["risk_type"]
                for ind in keyword_indicators
            )

            if not already_detected:
                # Add as new indicator
                semantic_indicators.append({
                    "indicator": risk["risk_type"],
                    "severity": risk["severity"],
                    "description": risk["description"],
                    "category": "semantic_risk",
                    "detection_method": "semantic",
                    "similarity": risk["similarity"],
                    "matched_template": risk["matched_template"]
                })

        # Combine and return
        all_indicators = keyword_indicators + semantic_indicators

        if semantic_indicators:
            logger.info(
                f"Semantic detection added {len(semantic_indicators)} new indicators "
                f"(total: {len(all_indicators)})"
            )

        return all_indicators
