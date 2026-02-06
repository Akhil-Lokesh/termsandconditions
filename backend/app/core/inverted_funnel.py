"""
Inverted Funnel Anomaly Detection System.

Philosophy Change:
- OLD: "Find unusual things, hide common things"
- NEW: "Find ALL concerning things, tell user which are unusual AND which are harmful"

4-Layer Architecture:
1. DETECT ALL - Cast wide net, zero suppression
2. CALCULATE COMMONNESS - Add context, don't filter
3. ASSIGN THREAT LEVEL - Based on consumer harm, not prevalence
4. COMBINE & RANK - Show user what matters most

Key Insight: A UNIVERSAL pattern can still be HIGH threat!
(e.g., perpetual license is common but still harmful)
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from app.core.constants import (
    ThreatLevel,
    CommonnessLevel,
    DisplayCategory,
    PATTERN_THREAT_LEVELS,
    CommonnessThresholds,
    UserImportanceConfig,
    get_display_category,
    get_threat_level_from_score,
    BASELINE_PREVALENCE,
)

logger = logging.getLogger(__name__)


@dataclass
class DetectedAnomaly:
    """
    A single detected anomaly with full context.
    This is the output format for the inverted funnel system.
    """
    # Basic identification
    clause_number: str
    clause_text: str
    section: str = ""

    # Detection info (Layer 1)
    detected_patterns: List[str] = field(default_factory=list)
    detection_method: str = "pattern"  # pattern, semantic, statistical
    raw_confidence: float = 0.0

    # Commonness info (Layer 2)
    commonness_level: CommonnessLevel = CommonnessLevel.COMMON
    commonness_percentage: float = 50.0
    industry_commonness: Optional[CommonnessLevel] = None

    # Threat info (Layer 3)
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    threat_score: float = 5.0
    why_threatening: str = ""

    # Combined ranking (Layer 4)
    user_importance_score: float = 0.0
    display_category: DisplayCategory = DisplayCategory.STANDARD_TERMS

    # Legacy compatibility
    severity: str = "medium"  # high, medium, low for backward compat
    risk_score: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "clause_number": self.clause_number,
            "clause_text": self.clause_text,
            "section": self.section,
            "detected_patterns": self.detected_patterns,
            "detection_method": self.detection_method,
            "raw_confidence": self.raw_confidence,
            "commonness_level": self.commonness_level.value,
            "commonness_percentage": self.commonness_percentage,
            "industry_commonness": self.industry_commonness.value if self.industry_commonness else None,
            "threat_level": self.threat_level.value,
            "threat_score": self.threat_score,
            "why_threatening": self.why_threatening,
            "user_importance_score": self.user_importance_score,
            "display_category": self.display_category.value,
            # Legacy fields
            "severity": self.severity,
            "risk_score": self.risk_score,
        }


class InvertedFunnelDetector:
    """
    Implements the 4-layer inverted funnel detection system.

    Unlike the old system that suppressed common patterns,
    this system detects ALL patterns and adds context about
    both commonness AND threat level.
    """

    def __init__(
        self,
        risk_indicators=None,
        semantic_detector=None,
        statistical_detector=None,
        prevalence_calculator=None,
    ):
        """
        Initialize with optional detection components.

        Args:
            risk_indicators: Pattern-based detector
            semantic_detector: Semantic anomaly detector
            statistical_detector: Statistical outlier detector
            prevalence_calculator: For calculating commonness
        """
        self.risk_indicators = risk_indicators
        self.semantic_detector = semantic_detector
        self.statistical_detector = statistical_detector
        self.prevalence_calculator = prevalence_calculator

        # Threat descriptions for user-friendly explanations
        self.threat_descriptions = self._build_threat_descriptions()

    def _build_threat_descriptions(self) -> Dict[str, str]:
        """Build human-readable descriptions of why patterns are threatening."""
        return {
            # Critical
            "data_selling": "Your personal data may be sold to third parties",
            "biometric_data_collection": "Biometric data (face, voice, fingerprints) collected without clear consent",
            "biometric": "Biometric data collection detected",
            "rights_waiver": "You may be waiving important legal rights",
            "coppa_violation": "Potential violations of children's privacy laws",
            "hipaa_violation": "Potential violations of health data privacy laws",

            # High
            "perpetual_irrevocable_license": "Company keeps rights to your content forever, even after you leave",
            "perpetual_license": "Company keeps permanent rights to your content",
            "broad_content_license": "Company gets extensive rights to use and modify your content",
            "user_content_license": "Other users can copy, modify, and redistribute your content",
            "forced_arbitration_class_waiver": "You cannot sue or join class actions - forced into private arbitration",
            "class_action_waiver": "You cannot join class action lawsuits",
            "unlimited_liability": "You may be liable for unlimited damages",
            "unilateral_termination": "Account can be terminated at any time without reason",
            "ai_training_data": "Your content may be used to train AI models",
            "survival_clauses": "Certain rights persist even after account deletion",
            "asymmetric_assignment": "Company can transfer agreement but you cannot",
            "fund_holds_freezing": "Your funds can be frozen without clear process",
            "content_loss": "You may lose access to purchased/created content",

            # Medium
            "auto_renewal": "Subscription auto-renews - may be charged without reminder",
            "price_changes": "Prices can change without advance notice",
            "unilateral_content_removal": "Your content can be removed at company's discretion",
            "account_inactivity_reclaim": "Your username/account can be reclaimed after inactivity",
            "modification": "Terms can change without explicit notification",
            "surveillance_monitoring": "Your activity may be monitored extensively",

            # Low
            "liability_limitation": "Company limits its responsibility for damages",
            "liability_limitation_specific": "Company limits responsibility for losses you may incur",
            "warranty_disclaimer": "No guarantees about service quality",
            "cross_platform_sync": "Your data is shared across multiple services/platforms",
            "no_content_guarantee": "No guarantee that content is accurate or legal",
            "indemnification": "You may need to cover company's legal costs",

            # Info
            "governing_law": "Standard jurisdiction clause",
            "severability": "Standard legal boilerplate",
            "entire_agreement": "Standard legal boilerplate",
        }

    # =========================================================================
    # LAYER 1: DETECT ALL
    # =========================================================================

    def layer1_detect_all(
        self,
        clause_text: str,
        clause_number: str = "",
        section: str = "",
        service_type: str = "general",
    ) -> List[Dict[str, Any]]:
        """
        Layer 1: Detect ALL possible anomalies - no suppression.

        This layer casts a wide net and returns every pattern match,
        semantic anomaly, and statistical outlier.

        Args:
            clause_text: The clause text to analyze
            clause_number: Clause identifier
            section: Section name
            service_type: Type of service for context

        Returns:
            List of raw detections with method and confidence
        """
        detections = []

        # Pattern-based detection
        if self.risk_indicators:
            pattern_matches = self.risk_indicators.detect_indicators(
                clause_text=clause_text,
                service_type=service_type,
            )
            for match in pattern_matches:
                detections.append({
                    "pattern": match.get("indicator", match.get("pattern", "unknown")),
                    "method": "pattern",
                    "confidence": 0.8 if match.get("severity") == "high" else 0.6,
                    "severity": match.get("severity", "medium"),
                    "description": match.get("description", ""),
                    "keywords_found": match.get("keywords_found", []),
                })

        # Semantic detection (if available)
        if self.semantic_detector and hasattr(self.semantic_detector, 'is_available'):
            if self.semantic_detector.is_available:
                try:
                    semantic_result = self.semantic_detector.detect_semantic_anomalies(clause_text)
                    if semantic_result.get("is_anomalous", False):
                        detections.append({
                            "pattern": "semantic_anomaly",
                            "method": "semantic",
                            "confidence": 1.0 - semantic_result.get("similarity_score", 0.5),
                            "severity": "medium",
                            "description": "Semantically unusual clause detected",
                            "similarity_score": semantic_result.get("similarity_score", 0),
                        })
                except Exception as e:
                    logger.warning(f"Semantic detection failed: {e}")

        # Statistical detection (if available and fitted)
        if self.statistical_detector and hasattr(self.statistical_detector, 'is_fitted'):
            if self.statistical_detector.is_fitted:
                try:
                    is_outlier = self.statistical_detector.is_outlier(clause_text)
                    if is_outlier:
                        detections.append({
                            "pattern": "statistical_outlier",
                            "method": "statistical",
                            "confidence": 0.7,
                            "severity": "medium",
                            "description": "Statistically unusual clause detected",
                        })
                except Exception as e:
                    logger.warning(f"Statistical detection failed: {e}")

        logger.info(f"Layer 1: Found {len(detections)} raw detections for clause {clause_number}")
        return detections

    # =========================================================================
    # LAYER 2: CALCULATE COMMONNESS
    # =========================================================================

    def layer2_calculate_commonness(
        self,
        detections: List[Dict[str, Any]],
        industry: str = "general",
    ) -> List[Dict[str, Any]]:
        """
        Layer 2: Calculate how common each detection is - but don't filter.

        Adds commonness context to each detection without removing anything.

        Args:
            detections: Raw detections from Layer 1
            industry: Industry context for industry-specific commonness

        Returns:
            Detections enriched with commonness information
        """
        enriched = []

        for detection in detections:
            pattern = detection.get("pattern", "unknown")

            # Get prevalence from baseline data
            prevalence = BASELINE_PREVALENCE.get(pattern, 0.30)  # Default to uncommon

            # Calculate commonness level
            commonness_level = CommonnessThresholds.get_level(prevalence)

            # Add commonness info
            detection["commonness_level"] = commonness_level
            detection["commonness_percentage"] = prevalence * 100

            # Industry-specific commonness (if we had industry data)
            # For now, use same as general
            detection["industry_commonness"] = commonness_level

            enriched.append(detection)

            logger.debug(
                f"Layer 2: Pattern '{pattern}' is {commonness_level.value} "
                f"({prevalence*100:.0f}% prevalence)"
            )

        return enriched

    # =========================================================================
    # LAYER 3: ASSIGN THREAT LEVEL
    # =========================================================================

    def layer3_assign_threat(
        self,
        detections: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Layer 3: Assign threat level based on consumer harm potential.

        This is INDEPENDENT of commonness - a common pattern can still
        be high threat.

        Args:
            detections: Detections with commonness from Layer 2

        Returns:
            Detections enriched with threat information
        """
        enriched = []

        for detection in detections:
            pattern = detection.get("pattern", "unknown")

            # Get threat score from mapping
            threat_score = PATTERN_THREAT_LEVELS.get(pattern, 5.0)

            # Convert to threat level
            threat_level = get_threat_level_from_score(threat_score)

            # Get human-readable explanation
            why_threatening = self.threat_descriptions.get(
                pattern,
                detection.get("description", "Potentially concerning clause")
            )

            # Add threat info
            detection["threat_score"] = threat_score
            detection["threat_level"] = threat_level
            detection["why_threatening"] = why_threatening

            enriched.append(detection)

            logger.debug(
                f"Layer 3: Pattern '{pattern}' has threat level {threat_level.value} "
                f"(score: {threat_score})"
            )

        return enriched

    # =========================================================================
    # LAYER 4: COMBINE & RANK
    # =========================================================================

    def layer4_combine_and_rank(
        self,
        detections: List[Dict[str, Any]],
        clause_text: str,
        clause_number: str = "",
        section: str = "",
    ) -> List[DetectedAnomaly]:
        """
        Layer 4: Combine detections and rank by user importance.

        Creates final DetectedAnomaly objects with all context,
        sorted by importance to the user.

        Args:
            detections: Detections with commonness and threat from Layers 2-3
            clause_text: Original clause text
            clause_number: Clause identifier
            section: Section name

        Returns:
            List of DetectedAnomaly objects, sorted by importance
        """
        if not detections:
            return []

        # Group patterns from same clause
        patterns = [d.get("pattern", "unknown") for d in detections]

        # Use highest threat detection for this clause
        max_threat_detection = max(detections, key=lambda d: d.get("threat_score", 0))

        # Calculate user importance score
        threat_score = max_threat_detection.get("threat_score", 5.0)
        commonness_level = max_threat_detection.get("commonness_level", CommonnessLevel.COMMON)

        importance_score = UserImportanceConfig.calculate_importance(
            threat_score=threat_score,
            commonness=commonness_level,
        )

        # Determine display category
        threat_level = max_threat_detection.get("threat_level", ThreatLevel.MEDIUM)
        display_category = get_display_category(threat_level, commonness_level)

        # Map threat level to legacy severity
        severity_mapping = {
            ThreatLevel.CRITICAL: "critical",
            ThreatLevel.HIGH: "high",
            ThreatLevel.MEDIUM: "medium",
            ThreatLevel.LOW: "low",
            ThreatLevel.INFO: "low",
        }
        legacy_severity = severity_mapping.get(threat_level, "medium")

        # Create final anomaly object
        anomaly = DetectedAnomaly(
            clause_number=clause_number,
            clause_text=clause_text,
            section=section,
            detected_patterns=patterns,
            detection_method=max_threat_detection.get("method", "pattern"),
            raw_confidence=max_threat_detection.get("confidence", 0.5),
            commonness_level=commonness_level,
            commonness_percentage=max_threat_detection.get("commonness_percentage", 50.0),
            industry_commonness=max_threat_detection.get("industry_commonness"),
            threat_level=threat_level,
            threat_score=threat_score,
            why_threatening=max_threat_detection.get("why_threatening", ""),
            user_importance_score=importance_score,
            display_category=display_category,
            severity=legacy_severity,
            risk_score=threat_score,
        )

        logger.info(
            f"Layer 4: Clause {clause_number} - "
            f"Category: {display_category.value}, "
            f"Importance: {importance_score:.1f}, "
            f"Patterns: {patterns}"
        )

        return [anomaly]

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    def process_clause(
        self,
        clause_text: str,
        clause_number: str = "",
        section: str = "",
        service_type: str = "general",
        industry: str = "general",
    ) -> List[DetectedAnomaly]:
        """
        Process a single clause through the 4-layer inverted funnel.

        Args:
            clause_text: The clause text to analyze
            clause_number: Clause identifier
            section: Section name
            service_type: Type of service
            industry: Industry for context

        Returns:
            List of detected anomalies with full context
        """
        # Layer 1: Detect ALL
        raw_detections = self.layer1_detect_all(
            clause_text=clause_text,
            clause_number=clause_number,
            section=section,
            service_type=service_type,
        )

        if not raw_detections:
            return []

        # Layer 2: Calculate Commonness
        with_commonness = self.layer2_calculate_commonness(
            detections=raw_detections,
            industry=industry,
        )

        # Layer 3: Assign Threat Level
        with_threat = self.layer3_assign_threat(
            detections=with_commonness,
        )

        # Layer 4: Combine & Rank
        anomalies = self.layer4_combine_and_rank(
            detections=with_threat,
            clause_text=clause_text,
            clause_number=clause_number,
            section=section,
        )

        return anomalies

    def process_document(
        self,
        clauses: List[Dict[str, Any]],
        service_type: str = "general",
        industry: str = "general",
    ) -> List[DetectedAnomaly]:
        """
        Process all clauses in a document through the inverted funnel.

        Args:
            clauses: List of clause dictionaries with 'text', 'clause_number', 'section'
            service_type: Type of service
            industry: Industry for context

        Returns:
            List of detected anomalies, sorted by user importance (highest first)
        """
        all_anomalies = []

        for clause in clauses:
            anomalies = self.process_clause(
                clause_text=clause.get("text", ""),
                clause_number=clause.get("clause_number", ""),
                section=clause.get("section", ""),
                service_type=service_type,
                industry=industry,
            )
            all_anomalies.extend(anomalies)

        # Sort by user importance (highest first)
        all_anomalies.sort(key=lambda a: a.user_importance_score, reverse=True)

        logger.info(
            f"Inverted Funnel: Processed {len(clauses)} clauses, "
            f"found {len(all_anomalies)} anomalies"
        )

        # Log category breakdown
        categories = {}
        for a in all_anomalies:
            cat = a.display_category.value
            categories[cat] = categories.get(cat, 0) + 1

        logger.info(f"Category breakdown: {categories}")

        return all_anomalies
