"""
Compound risk detection - identifies combinations of risky clauses.

Detects systemic risks that arise from combinations of individual clauses.
Stage 4 of the anomaly detection pipeline.
"""

import time
from typing import List, Dict, Set, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CompoundRiskDetector:
    """
    Detects compound/systemic risks from combinations of clauses.

    Identifies patterns where multiple risk indicators combine to create
    severe systemic issues that are worse than the sum of their parts.
    """

    # Compound risk patterns (6 core patterns from specification)
    COMPOUND_PATTERNS = {
        "lock_in": {
            "name": "Lock-in Trap",
            "description": "Combination of auto-renewal, difficult cancellation, and no refunds creates a subscription trap",
            "components": [
                {"indicator": "auto_renewal", "required": True, "threshold": 1},
                {"indicator": "no_refund", "required": True, "threshold": 1},
                {"indicator": "difficult_cancellation", "required": False, "threshold": 1},
                {"indicator": "price_increase_no_notice", "required": False, "threshold": 1},
                {"indicator": "cancellation_fee", "required": False, "threshold": 1}
            ],
            "base_severity": "MEDIUM",
            "compound_severity": "HIGH",
            "risk_multiplier": 2.5,
            "explanation": (
                "This pattern traps users in recurring payments by combining automatic renewals "
                "with restrictive cancellation policies and no refunds. Users find it difficult "
                "or impossible to stop charges once they start."
            ),
            "consumer_impact": "You may be charged repeatedly with no practical way to stop payments or get refunds.",
            "recommendation": (
                "1. Set calendar reminders before renewal dates\n"
                "2. Use virtual credit cards with spending limits\n"
                "3. Document all cancellation attempts\n"
                "4. Consider alternative services with better cancellation policies"
            )
        },

        "hidden_costs": {
            "name": "Hidden Cost Escalation",
            "description": "Price increases without notice combined with automatic payment updates and binding terms",
            "components": [
                {"indicator": "price_increase_no_notice", "required": True, "threshold": 1},
                {"indicator": "auto_payment_updates", "required": True, "threshold": 1},
                {"indicator": "auto_renewal", "required": False, "threshold": 1},
                {"indicator": "no_refund", "required": False, "threshold": 1},
                {"indicator": "unilateral_changes", "required": False, "threshold": 1}
            ],
            "base_severity": "MEDIUM",
            "compound_severity": "HIGH",
            "risk_multiplier": 2.2,
            "explanation": (
                "This pattern allows unlimited cost escalation without user consent. The company "
                "can raise prices at will, automatically update payment methods, and prevent users "
                "from disputing or reversing charges."
            ),
            "consumer_impact": "Your costs can increase indefinitely without your knowledge or consent.",
            "recommendation": (
                "1. Monitor all charges closely\n"
                "2. Disable automatic payment method updates\n"
                "3. Set up low balance alerts\n"
                "4. Review statements monthly for unexpected charges"
            )
        },

        "data_exploitation": {
            "name": "Data Exploitation Stack",
            "description": "Extensive data collection, sharing, and selling combined with no deletion rights",
            "components": [
                {"indicator": "data_sharing", "required": True, "threshold": 1},
                {"indicator": "data_selling", "required": True, "threshold": 1},
                {"indicator": "monitoring_surveillance", "required": False, "threshold": 1},
                {"indicator": "no_data_deletion", "required": False, "threshold": 1},
                {"indicator": "indefinite_data_retention", "required": False, "threshold": 1},
                {"indicator": "third_party_access", "required": False, "threshold": 1}
            ],
            "base_severity": "MEDIUM",
            "compound_severity": "HIGH",
            "risk_multiplier": 2.0,
            "explanation": (
                "This pattern enables comprehensive monetization of user data. The company collects, "
                "shares, and sells user information to third parties while preventing users from "
                "controlling or deleting their data."
            ),
            "consumer_impact": "Your personal information is collected, sold, and shared indefinitely without meaningful control.",
            "recommendation": (
                "1. Minimize personal information provided\n"
                "2. Use privacy-focused alternatives when possible\n"
                "3. Review privacy settings regularly\n"
                "4. Consider using VPN and ad blockers"
            )
        },

        "rights_elimination": {
            "name": "Legal Rights Elimination",
            "description": "Forced arbitration, class action waiver, and liability disclaimers eliminate legal recourse",
            "components": [
                {"indicator": "forced_arbitration_class_waiver", "required": True, "threshold": 1},
                {"indicator": "rights_waiver", "required": True, "threshold": 1},
                {"indicator": "broad_liability_disclaimer", "required": False, "threshold": 1},
                {"indicator": "unlimited_liability", "required": False, "threshold": 1},
                {"indicator": "indemnification", "required": False, "threshold": 1}
            ],
            "base_severity": "HIGH",
            "compound_severity": "CRITICAL",
            "risk_multiplier": 2.8,
            "explanation": (
                "This pattern systematically eliminates your legal protections. You waive the right "
                "to sue, cannot join class actions, and accept liability for company actions while "
                "the company disclaims all responsibility."
            ),
            "consumer_impact": "You have essentially no legal recourse if something goes wrong.",
            "recommendation": (
                "1. Consult with a lawyer before accepting\n"
                "2. Document all interactions and issues\n"
                "3. Consider arbitration insurance\n"
                "4. Look for alternative services with better legal protections"
            )
        },

        "content_grab": {
            "name": "Content Rights Appropriation",
            "description": "Broad perpetual license combined with ability to sublicense and commercialize user content",
            "components": [
                {"indicator": "broad_usage_rights", "required": True, "threshold": 1},
                {"indicator": "perpetual_license", "required": True, "threshold": 1},
                {"indicator": "sublicense_rights", "required": False, "threshold": 1},
                {"indicator": "commercial_use", "required": False, "threshold": 1},
                {"indicator": "no_attribution", "required": False, "threshold": 1}
            ],
            "base_severity": "MEDIUM",
            "compound_severity": "HIGH",
            "risk_multiplier": 1.8,
            "explanation": (
                "This pattern gives the company extensive rights to your content forever. They can "
                "use it commercially, sublicense it to others, and modify it without attribution "
                "or compensation."
            ),
            "consumer_impact": "The company owns rights to your content forever and can profit from it without paying you.",
            "recommendation": (
                "1. Only upload content you're comfortable giving away\n"
                "2. Watermark valuable content\n"
                "3. Keep original copies elsewhere\n"
                "4. Consider platforms with creator-friendly terms"
            )
        },

        "surveillance_stack": {
            "name": "Comprehensive Surveillance",
            "description": "Location tracking, device fingerprinting, and behavioral tracking create complete user profile",
            "components": [
                {"indicator": "location_tracking", "required": True, "threshold": 1},
                {"indicator": "device_fingerprinting", "required": True, "threshold": 1},
                {"indicator": "behavioral_tracking", "required": False, "threshold": 1},
                {"indicator": "cross_device_tracking", "required": False, "threshold": 1},
                {"indicator": "biometric_data", "required": False, "threshold": 1},
                {"indicator": "background_data_collection", "required": False, "threshold": 1}
            ],
            "base_severity": "MEDIUM",
            "compound_severity": "HIGH",
            "risk_multiplier": 1.8,
            "explanation": (
                "This pattern enables comprehensive surveillance of user activities. The company "
                "tracks your location, identifies your devices, monitors your behavior, and links "
                "activity across devices to build detailed user profiles."
            ),
            "consumer_impact": "Your activities, location, and behavior are comprehensively monitored and profiled.",
            "recommendation": (
                "1. Disable location services when not needed\n"
                "2. Use privacy-focused browsers and apps\n"
                "3. Clear cookies and app data regularly\n"
                "4. Review and limit app permissions"
            )
        }
    }

    def detect_compound_risks(
        self,
        anomalies: List[Dict[str, Any]],
        full_clauses: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect compound risks from anomalies.

        Args:
            anomalies: List of detected anomalies from previous stages
            full_clauses: Optional list of all document clauses for context

        Returns:
            List of detected compound risks with full metadata
        """
        logger.info(f"Starting compound risk detection on {len(anomalies)} anomalies")
        detection_start = time.time()

        if not anomalies:
            logger.info("No anomalies provided, skipping compound risk detection")
            return []

        # Extract all indicators from anomalies
        all_indicators = self._extract_all_indicators(anomalies)
        indicator_set = {ind["name"] for ind in all_indicators}

        logger.debug(f"Extracted {len(all_indicators)} indicators: {indicator_set}")

        compound_risks = []

        # Check each compound pattern
        for pattern_id, pattern in self.COMPOUND_PATTERNS.items():
            logger.debug(f"Checking pattern: {pattern_id}")

            # Check if pattern matches
            match_result = self._check_pattern(pattern, indicator_set, anomalies)

            if match_result['matches']:
                # Find all component matches
                component_matches = self._find_component_matches(
                    pattern,
                    anomalies,
                    indicator_set
                )

                # Calculate combined score
                combined_score = self._calculate_combined_score(
                    pattern,
                    match_result,
                    len(anomalies)
                )

                # Generate recommendation
                recommendation = self._generate_recommendation(
                    pattern,
                    component_matches
                )

                compound_risk = {
                    "compound_risk_type": pattern_id,
                    "name": pattern["name"],
                    "description": pattern["description"],
                    "base_severity": pattern["base_severity"],
                    "compound_severity": pattern["compound_severity"],
                    "risk_multiplier": pattern["risk_multiplier"],
                    "explanation": pattern["explanation"],
                    "consumer_impact": pattern["consumer_impact"],
                    "recommendation": recommendation,
                    "confidence": match_result['confidence'],
                    "required_components": match_result['required_components'],
                    "optional_components": match_result['optional_components'],
                    "matched_required": match_result['matched_required'],
                    "matched_optional": match_result['matched_optional'],
                    "component_matches": component_matches,
                    "combined_score": combined_score,
                    "clause_references": [
                        {
                            "clause_number": m["clause_number"],
                            "section": m["section"],
                            "indicators": m["indicators"]
                        }
                        for m in component_matches
                    ]
                }

                compound_risks.append(compound_risk)

                logger.info(
                    f"Compound risk detected: {pattern['name']} "
                    f"(confidence: {match_result['confidence']:.1%}, "
                    f"score: {combined_score:.1f}, "
                    f"severity: {pattern['compound_severity']})"
                )

        detection_duration = (time.time() - detection_start) * 1000

        logger.info(
            f"Compound risk detection complete: {len(compound_risks)} patterns detected "
            f"in {detection_duration:.2f}ms"
        )

        return compound_risks

    def _check_pattern(
        self,
        pattern: Dict[str, Any],
        indicator_set: Set[str],
        anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if a pattern matches the detected indicators.

        Args:
            pattern: Pattern definition
            indicator_set: Set of detected indicator names
            anomalies: List of anomalies

        Returns:
            Dict with match status, confidence, and component lists
        """
        components = pattern["components"]

        required_components = [c for c in components if c["required"]]
        optional_components = [c for c in components if not c["required"]]

        # Check required components
        matched_required = []
        for component in required_components:
            indicator = component["indicator"]
            if indicator in indicator_set:
                matched_required.append(indicator)

        # Check if all required components are present
        all_required_present = len(matched_required) == len(required_components)

        if not all_required_present:
            return {
                'matches': False,
                'confidence': 0.0,
                'required_components': [c["indicator"] for c in required_components],
                'optional_components': [c["indicator"] for c in optional_components],
                'matched_required': matched_required,
                'matched_optional': []
            }

        # Check optional components
        matched_optional = []
        for component in optional_components:
            indicator = component["indicator"]
            if indicator in indicator_set:
                matched_optional.append(indicator)

        # Calculate confidence
        # Base: 100% for all required
        # Boost: +5% for each optional (up to 100%)
        base_confidence = 0.70
        optional_boost = min(len(matched_optional) * 0.05, 0.30)
        confidence = base_confidence + optional_boost

        return {
            'matches': True,
            'confidence': confidence,
            'required_components': [c["indicator"] for c in required_components],
            'optional_components': [c["indicator"] for c in optional_components],
            'matched_required': matched_required,
            'matched_optional': matched_optional
        }

    def _find_component_matches(
        self,
        pattern: Dict[str, Any],
        anomalies: List[Dict[str, Any]],
        indicator_set: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Find all anomalies that contributed to this pattern match.

        Args:
            pattern: Pattern definition
            anomalies: List of anomalies
            indicator_set: Set of detected indicators

        Returns:
            List of matching anomalies with their indicators
        """
        # Get all component indicators for this pattern
        all_component_indicators = {
            c["indicator"] for c in pattern["components"]
        }

        component_matches = []

        for anomaly in anomalies:
            detected_indicators = anomaly.get("detected_indicators", [])
            anomaly_indicator_names = {ind["name"] for ind in detected_indicators}

            # Check if this anomaly has any relevant indicators
            relevant_indicators = anomaly_indicator_names.intersection(
                all_component_indicators
            )

            if relevant_indicators:
                component_matches.append({
                    "clause_number": anomaly.get("clause_number"),
                    "section": anomaly.get("section"),
                    "clause_text": anomaly.get("clause_text", "")[:150] + "...",
                    "severity": anomaly.get("severity"),
                    "indicators": list(relevant_indicators)
                })

        return component_matches

    def _calculate_combined_score(
        self,
        pattern: Dict[str, Any],
        match_result: Dict[str, Any],
        total_anomalies: int
    ) -> float:
        """
        Calculate combined risk score for the pattern.

        Args:
            pattern: Pattern definition
            match_result: Pattern match results
            total_anomalies: Total number of anomalies in document

        Returns:
            Combined score (0-10 scale)
        """
        # Base score from severity
        severity_scores = {
            "LOW": 2.0,
            "MEDIUM": 5.0,
            "HIGH": 7.0,
            "CRITICAL": 9.0
        }

        base_score = severity_scores.get(
            pattern["compound_severity"],
            5.0
        )

        # Apply risk multiplier
        score = base_score * pattern["risk_multiplier"]

        # Boost for optional components (up to +20%)
        optional_boost = len(match_result['matched_optional']) * 0.5
        score += optional_boost

        # Cap at 10.0
        score = min(score, 10.0)

        return round(score, 1)

    def _generate_recommendation(
        self,
        pattern: Dict[str, Any],
        component_matches: List[Dict[str, Any]]
    ) -> str:
        """
        Generate actionable recommendation for the compound risk.

        Args:
            pattern: Pattern definition
            component_matches: List of matching components

        Returns:
            Detailed recommendation string
        """
        # Start with pattern recommendation
        recommendation = pattern["recommendation"]

        # Add specific clause references if available
        if component_matches:
            recommendation += "\n\nSpecific clauses to review:"
            for i, match in enumerate(component_matches[:5], 1):  # Limit to 5
                recommendation += (
                    f"\n{i}. {match['section']} - Clause {match['clause_number']}: "
                    f"{match['indicators']}"
                )

            if len(component_matches) > 5:
                recommendation += f"\n... and {len(component_matches) - 5} more clauses"

        return recommendation

    def _extract_all_indicators(
        self,
        anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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

    def calculate_compound_risk_score(
        self,
        compound_risks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "detected_patterns": []
            }

        # Count by severity
        critical_count = sum(
            1 for r in compound_risks
            if r["compound_severity"] == "CRITICAL"
        )
        high_count = sum(
            1 for r in compound_risks
            if r["compound_severity"] == "HIGH"
        )
        medium_count = sum(
            1 for r in compound_risks
            if r["compound_severity"] == "MEDIUM"
        )
        low_count = sum(
            1 for r in compound_risks
            if r["compound_severity"] == "LOW"
        )

        # Calculate score (0-10 scale)
        # Critical: 4 points each
        # High: 3 points each
        # Medium: 1.5 points each
        # Low: 0.5 points each
        score = (
            (critical_count * 4.0) +
            (high_count * 3.0) +
            (medium_count * 1.5) +
            (low_count * 0.5)
        )
        score = min(score, 10.0)  # Cap at 10

        # Determine risk level
        if score >= 7.0 or critical_count > 0:
            risk_level = "Critical"
        elif score >= 5.0 or high_count >= 2:
            risk_level = "High"
        elif score >= 3.0 or high_count >= 1:
            risk_level = "Medium"
        elif score > 0:
            risk_level = "Low"
        else:
            risk_level = "None"

        return {
            "compound_risk_score": round(score, 1),
            "compound_risk_level": risk_level,
            "compound_risk_count": len(compound_risks),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "detected_patterns": [
                {
                    "type": r["compound_risk_type"],
                    "name": r["name"],
                    "severity": r["compound_severity"],
                    "score": r["combined_score"]
                }
                for r in compound_risks
            ]
        }
