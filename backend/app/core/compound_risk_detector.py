"""
Compound risk detection - identifies combinations of risky clauses.

Detects systemic risks that arise from combinations of individual clauses.
For example:
  - Auto-renewal + No refunds + Price increases = "Subscription trap"
  - Unilateral termination + No data backup = "Data loss risk"
  - Broad liability + Rights waiver + Forced arbitration = "Legal protection elimination"
"""

from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class CompoundRiskDetector:
    """Detects compound/systemic risks from combinations of clauses."""

    # Compound risk patterns (combinations that create systemic issues)
    COMPOUND_PATTERNS = {
        "subscription_trap": {
            "required_indicators": ["auto_renewal", "no_refund"],
            "optional_indicators": ["price_increase_no_notice", "unilateral_changes"],
            "severity": "high",
            "description": "Subscription Trap: Auto-renewal combined with no refunds makes it difficult to escape",
            "consumer_impact": "You may be charged repeatedly with no way to get your money back.",
            "recommendation": "Carefully track renewal dates and ensure you can cancel before renewal.",
        },
        "data_loss_vulnerability": {
            "required_indicators": ["content_loss", "unilateral_termination"],
            "optional_indicators": ["broad_liability_disclaimer"],
            "severity": "high",
            "description": "Data Loss Vulnerability: Service can be terminated without notice and data deleted without liability",
            "consumer_impact": "Your data could be permanently lost without warning or compensation.",
            "recommendation": "Maintain regular backups of all important data stored with this service.",
        },
        "legal_protection_elimination": {
            "required_indicators": ["forced_arbitration_class_waiver", "rights_waiver"],
            "optional_indicators": [
                "unlimited_liability",
                "broad_liability_disclaimer",
            ],
            "severity": "high",
            "description": "Legal Protection Elimination: Multiple clauses combine to remove your legal recourse",
            "consumer_impact": "You have extremely limited ability to seek legal remedies if something goes wrong.",
            "recommendation": "Consider whether you're comfortable waiving this level of legal protection.",
        },
        "payment_exploitation": {
            "required_indicators": ["auto_payment_updates", "price_increase_no_notice"],
            "optional_indicators": ["no_refund", "auto_renewal"],
            "severity": "high",
            "description": "Payment Exploitation: Automatic payment updates combined with price increases without notice",
            "consumer_impact": "You could be charged increasing amounts on updated cards without your knowledge.",
            "recommendation": "Monitor your billing closely and disable automatic payment updates if possible.",
        },
        "content_rights_grab": {
            "required_indicators": ["broad_usage_rights"],
            "optional_indicators": ["unilateral_changes", "no_refund"],
            "severity": "medium",
            "description": "Content Rights Grab: Broad perpetual license to your content",
            "consumer_impact": "The company can use your content indefinitely for any purpose, including commercial use.",
            "recommendation": "Only upload content you're comfortable with the company using without restriction.",
        },
        "privacy_vulnerability": {
            "required_indicators": ["data_sharing", "monitoring_surveillance"],
            "optional_indicators": ["unilateral_changes"],
            "severity": "medium",
            "description": "Privacy Vulnerability: Extensive monitoring combined with unrestricted data sharing",
            "consumer_impact": "Your activities are tracked and shared with third parties without meaningful restriction.",
            "recommendation": "Assume all your activity is monitored and may be sold to advertisers.",
        },
        "unilateral_control": {
            "required_indicators": ["unilateral_changes", "unilateral_termination"],
            "optional_indicators": ["broad_liability_disclaimer"],
            "severity": "medium",
            "description": "Unilateral Control: Company retains complete control to change or end terms at will",
            "consumer_impact": "The company can change the rules or kick you out at any time without warning.",
            "recommendation": "Don't rely heavily on this service for critical needs.",
        },
        "liability_asymmetry": {
            "required_indicators": [
                "unlimited_liability",
                "broad_liability_disclaimer",
            ],
            "optional_indicators": ["rights_waiver"],
            "severity": "high",
            "description": "Liability Asymmetry: You have unlimited liability while company has none",
            "consumer_impact": "You're responsible for everything, but the company isn't responsible for anything.",
            "recommendation": "Consider liability insurance or alternative services with more balanced terms.",
        },
    }

    def detect_compound_risks(self, anomalies: List[Dict]) -> List[Dict]:
        """
        Detect compound risks from detected anomalies.

        Args:
            anomalies: List of detected anomalies for the document

        Returns:
            List of compound risk detections
        """
        if not anomalies:
            return []

        # Extract all risk indicators from anomalies
        all_indicators = self._extract_all_indicators(anomalies)

        # Track which indicators are present
        indicator_set = {ind["name"] for ind in all_indicators}

        logger.debug(f"Checking for compound risks with indicators: {indicator_set}")

        compound_risks = []

        # Check each compound pattern
        for pattern_name, pattern_data in self.COMPOUND_PATTERNS.items():
            # Check if all required indicators are present
            required = set(pattern_data["required_indicators"])
            optional = set(pattern_data.get("optional_indicators", []))

            has_required = required.issubset(indicator_set)

            if has_required:
                # Count how many optional indicators are present
                present_optional = indicator_set.intersection(optional)

                # Confidence based on how many optional indicators match
                confidence = 1.0  # Start at 100% for having all required
                if optional:
                    optional_match_rate = len(present_optional) / len(optional)
                    confidence = 0.7 + (0.3 * optional_match_rate)  # 70%-100%

                # Find related anomalies
                related_anomalies = self._find_related_anomalies(
                    anomalies, required.union(present_optional)
                )

                compound_risk = {
                    "compound_risk_type": pattern_name,
                    "severity": pattern_data["severity"],
                    "description": pattern_data["description"],
                    "consumer_impact": pattern_data["consumer_impact"],
                    "recommendation": pattern_data["recommendation"],
                    "confidence": confidence,
                    "required_indicators": list(required),
                    "matched_optional_indicators": list(present_optional),
                    "related_anomalies": related_anomalies,
                    "anomaly_count": len(related_anomalies),
                }

                compound_risks.append(compound_risk)

                logger.info(
                    f"Compound risk detected: {pattern_name} "
                    f"(confidence: {confidence:.0%}, {len(related_anomalies)} related anomalies)"
                )

        return compound_risks

    def _extract_all_indicators(self, anomalies: List[Dict]) -> List[Dict]:
        """
        Extract all risk indicators from anomalies.

        Args:
            anomalies: List of anomalies

        Returns:
            Flattened list of all indicators
        """
        all_indicators = []

        for anomaly in anomalies:
            detected_indicators = anomaly.get("detected_indicators", [])
            all_indicators.extend(detected_indicators)

        return all_indicators

    def _find_related_anomalies(
        self, anomalies: List[Dict], relevant_indicators: Set[str]
    ) -> List[Dict]:
        """
        Find anomalies that contain any of the relevant indicators.

        Args:
            anomalies: All detected anomalies
            relevant_indicators: Set of indicator names to match

        Returns:
            List of related anomalies (simplified for embedding in compound risk)
        """
        related = []

        for anomaly in anomalies:
            detected_indicators = anomaly.get("detected_indicators", [])

            # Check if this anomaly has any relevant indicators
            anomaly_indicator_names = {ind["name"] for ind in detected_indicators}

            if anomaly_indicator_names.intersection(relevant_indicators):
                # Include simplified version
                related.append(
                    {
                        "section": anomaly.get("section"),
                        "clause_number": anomaly.get("clause_number"),
                        "clause_text": anomaly.get("clause_text", "")[:100]
                        + "...",  # Truncate
                        "severity": anomaly.get("severity"),
                    }
                )

        return related

    def calculate_compound_risk_score(self, compound_risks: List[Dict]) -> Dict:
        """
        Calculate overall compound risk score for document.

        Args:
            compound_risks: List of detected compound risks

        Returns:
            Dictionary with score and breakdown
        """
        if not compound_risks:
            return {
                "compound_risk_score": 0.0,
                "compound_risk_level": "None",
                "compound_risk_count": 0,
                "high_severity_count": 0,
                "medium_severity_count": 0,
            }

        # Count by severity
        high_count = sum(1 for r in compound_risks if r["severity"] == "high")
        medium_count = sum(1 for r in compound_risks if r["severity"] == "medium")

        # Calculate score (0-10 scale)
        # High severity: 3 points each
        # Medium severity: 1.5 points each
        score = (high_count * 3.0) + (medium_count * 1.5)
        score = min(score, 10.0)  # Cap at 10

        # Determine risk level
        if score >= 6.0:
            risk_level = "High"
        elif score >= 3.0:
            risk_level = "Medium"
        elif score > 0:
            risk_level = "Low"
        else:
            risk_level = "None"

        return {
            "compound_risk_score": round(score, 1),
            "compound_risk_level": risk_level,
            "compound_risk_count": len(compound_risks),
            "high_severity_count": high_count,
            "medium_severity_count": medium_count,
            "detected_patterns": [r["compound_risk_type"] for r in compound_risks],
        }
