"""
Alert ranker for Stage 6 of anomaly detection pipeline.

Ranks and filters anomalies based on severity, confidence, user preferences,
and alert budget constraints. Prevents alert fatigue by surfacing only the
most critical and relevant issues.

Stage 6: Alert Ranking & Budget Management
"""

from typing import List, Dict, Any, Optional
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AlertRanker:
    """
    Ranks and filters anomalies for user presentation.

    Implements alert budget management to avoid overwhelming users with
    too many alerts. Uses sophisticated scoring that combines severity,
    confidence, user preferences, and contextual factors.

    Constants:
        MAX_ALERTS: Maximum total alerts to show (10)
        TARGET_ALERTS: Target number of high-priority alerts (5)
    """

    # Alert budget constants (set high to show all anomalies)
    MAX_ALERTS = 100  # Increased from 10 to show all anomalies
    TARGET_ALERTS = 50  # Increased from 5

    # Severity weights for scoring
    SEVERITY_WEIGHTS = {
        'low': 1.0,
        'medium': 2.0,
        'high': 3.0,
        'critical': 4.0
    }

    # Bonus scores for special conditions
    BONUS_COMPOUND_RISK = 5.0
    BONUS_RECENT_CHANGE = 2.0
    BONUS_INDUSTRY_CRITICAL = 1.5
    BONUS_REGULATORY_VIOLATION = 3.0

    # Industry-specific critical indicators
    INDUSTRY_CRITICAL_COMBINATIONS = {
        'health_apps': ['data_selling', 'hipaa_violation', 'medical_data_sharing'],
        'financial_apps': ['unauthorized_transaction_liability', 'financial_data_selling', 'liability_waiver'],
        'children_apps': ['coppa_violation', 'market_to_children', 'collect_child_data'],
        'dating_apps': ['sexual_orientation_sharing', 'precise_location', 'sensitive_data_sharing']
    }

    # Regulatory violation categories
    REGULATORY_VIOLATIONS = [
        'gdpr_violation',
        'ccpa_violation',
        'coppa_violation',
        'hipaa_violation',
        'cfpb_prohibited_term'
    ]

    def __init__(self, user_preferences: Optional[Dict[str, Any]] = None):
        """
        Initialize alert ranker.

        Args:
            user_preferences: Optional dict with user preferences for personalization
                Example:
                {
                    'priority_categories': ['data_collection', 'liability'],
                    'concern_level': 'high',  # 'low', 'medium', 'high'
                    'show_all': False  # Override budget if True
                }
        """
        self.user_preferences = user_preferences or {}
        logger.info(
            f"Alert ranker initialized "
            f"(MAX_ALERTS={self.MAX_ALERTS}, TARGET_ALERTS={self.TARGET_ALERTS})"
        )

    def rank_and_filter(
        self,
        calibrated_anomalies: List[Dict[str, Any]],
        compound_risks: Optional[List[Dict[str, Any]]] = None,
        document_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Rank and filter anomalies based on alert budget.

        Combines regular anomalies and compound risks, scores them,
        enforces alert budget, and categorizes for presentation.

        Args:
            calibrated_anomalies: List of anomalies from Stage 5
            compound_risks: Optional list of compound risks from Stage 4
            document_context: Optional document context (industry, etc.)

        Returns:
            Dict containing:
                - high_severity: List of high-priority alerts (show immediately)
                - medium_severity: List of medium-priority alerts (expandable)
                - low_severity: List of low-priority alerts (detail view only)
                - suppressed: List of suppressed alerts (logged but hidden)
                - total_detected: Total anomalies detected
                - total_shown: Total alerts shown to user
                - ranking_metadata: Scoring breakdown and stats
        """
        logger.info(
            f"Starting Stage 6 alert ranking on {len(calibrated_anomalies)} anomalies"
        )

        # Default context
        if document_context is None:
            document_context = {}

        # STEP 1: Combine regular anomalies and compound risks
        all_anomalies = list(calibrated_anomalies)

        if compound_risks:
            logger.info(f"Converting {len(compound_risks)} compound risks to anomalies")
            for compound_risk in compound_risks:
                anomaly = self._convert_compound_to_anomaly(compound_risk)
                all_anomalies.append(anomaly)

        total_detected = len(all_anomalies)
        logger.info(f"Total anomalies to rank: {total_detected}")

        # STEP 2: Score each anomaly
        scored_anomalies = []
        for anomaly in all_anomalies:
            score_result = self._score_anomaly(anomaly, document_context)
            scored_anomaly = {
                **anomaly,
                'ranking_score': score_result['final_score'],
                'scoring_breakdown': score_result['breakdown']
            }
            scored_anomalies.append(scored_anomaly)

        # STEP 3: Sort by final_score descending
        scored_anomalies.sort(key=lambda x: x['ranking_score'], reverse=True)

        logger.info("Top 5 scored anomalies:")
        for i, anomaly in enumerate(scored_anomalies[:5], 1):
            logger.info(
                f"  {i}. Score: {anomaly['ranking_score']:.2f}, "
                f"Clause: {anomaly.get('clause_number', 'unknown')}, "
                f"Severity: {anomaly.get('severity', 'unknown')}"
            )

        # STEP 4: Categorize by confidence tier
        high_confidence = []
        moderate_confidence = []
        low_confidence = []

        for anomaly in scored_anomalies:
            # Get confidence tier from calibration
            tier = anomaly.get('confidence_calibration', {}).get('confidence_tier', 'LOW')

            if tier == 'HIGH':
                high_confidence.append(anomaly)
            elif tier == 'MODERATE':
                moderate_confidence.append(anomaly)
            else:
                low_confidence.append(anomaly)

        logger.info(
            f"Categorized by confidence: "
            f"HIGH={len(high_confidence)}, "
            f"MODERATE={len(moderate_confidence)}, "
            f"LOW={len(low_confidence)}"
        )

        # STEP 5: Enforce alert budget
        high_severity = []
        medium_severity = []
        low_severity = []
        suppressed = []

        # Check if user wants to see all alerts
        if self.user_preferences.get('show_all', False):
            logger.info("User preference 'show_all' enabled, bypassing alert budget")
            high_severity = high_confidence
            medium_severity = moderate_confidence
            low_severity = low_confidence
        else:
            # Apply budget constraints
            # Keep best TARGET_ALERTS from HIGH tier
            if len(high_confidence) <= self.TARGET_ALERTS:
                high_severity = high_confidence
                remaining_budget = self.MAX_ALERTS - len(high_severity)
            else:
                # Take top TARGET_ALERTS, move rest to moderate
                high_severity = high_confidence[:self.TARGET_ALERTS]
                moderate_confidence = high_confidence[self.TARGET_ALERTS:] + moderate_confidence
                remaining_budget = self.MAX_ALERTS - self.TARGET_ALERTS

            logger.info(
                f"Alert budget: {len(high_severity)} HIGH alerts selected, "
                f"remaining budget: {remaining_budget}"
            )

            # Fill remaining budget with moderate confidence
            if remaining_budget > 0 and moderate_confidence:
                medium_severity = moderate_confidence[:remaining_budget]
                remaining = moderate_confidence[remaining_budget:]
                low_confidence = remaining + low_confidence
                remaining_budget -= len(medium_severity)

            logger.info(
                f"Alert budget: {len(medium_severity)} MODERATE alerts selected, "
                f"remaining budget: {remaining_budget}"
            )

            # Fill any remaining budget with low confidence
            if remaining_budget > 0 and low_confidence:
                low_severity = low_confidence[:remaining_budget]
                suppressed = low_confidence[remaining_budget:]
            else:
                suppressed = low_confidence

            logger.info(
                f"Alert budget: {len(low_severity)} LOW alerts selected, "
                f"{len(suppressed)} suppressed"
            )

        total_shown = len(high_severity) + len(medium_severity) + len(low_severity)

        # STEP 6: Calculate ranking metadata
        avg_score = sum(a['ranking_score'] for a in scored_anomalies) / len(scored_anomalies) if scored_anomalies else 0
        top_categories = self._get_top_categories(scored_anomalies[:total_shown])

        ranking_metadata = {
            'total_detected': total_detected,
            'total_shown': total_shown,
            'total_suppressed': len(suppressed),
            'suppression_rate': len(suppressed) / total_detected if total_detected > 0 else 0,
            'avg_score': avg_score,
            'top_score': scored_anomalies[0]['ranking_score'] if scored_anomalies else 0,
            'top_categories': top_categories,
            'alert_budget_applied': not self.user_preferences.get('show_all', False),
            'user_preferences_applied': bool(self.user_preferences)
        }

        logger.info(
            f"Stage 6 complete: {total_shown}/{total_detected} alerts shown "
            f"({ranking_metadata['suppression_rate']:.1%} suppressed)"
        )

        return {
            'high_severity': high_severity,
            'medium_severity': medium_severity,
            'low_severity': low_severity,
            'suppressed': suppressed,
            'total_detected': total_detected,
            'total_shown': total_shown,
            'ranking_metadata': ranking_metadata
        }

    def _score_anomaly(
        self,
        anomaly: Dict[str, Any],
        document_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate scoring for an anomaly.

        Score = (Severity_Weight × Confidence × User_Relevance) + Bonuses

        Args:
            anomaly: Anomaly to score
            document_context: Document context for contextual scoring

        Returns:
            Dict with final_score and breakdown
        """
        # Get base severity weight
        severity = anomaly.get('severity', 'medium').lower()
        severity_weight = self.SEVERITY_WEIGHTS.get(severity, 2.0)

        # Get calibrated confidence (default to 0.5 if not available)
        confidence = anomaly.get('confidence_calibration', {}).get('calibrated_confidence')
        if confidence is None:
            confidence = anomaly.get('stage2_confidence', 0.5)

        # Calculate user relevance
        user_relevance = self._calculate_user_relevance(anomaly)

        # Base score
        base_score = severity_weight * confidence * user_relevance

        # Calculate bonuses
        bonuses = {}
        bonus_total = 0.0

        # Compound risk bonus
        if anomaly.get('is_compound_risk', False) or anomaly.get('compound_risks'):
            bonuses['compound_risk'] = self.BONUS_COMPOUND_RISK
            bonus_total += self.BONUS_COMPOUND_RISK

        # Recent change bonus
        if document_context.get('is_change', False):
            bonuses['recent_change'] = self.BONUS_RECENT_CHANGE
            bonus_total += self.BONUS_RECENT_CHANGE

        # Industry critical bonus
        if self._is_industry_critical(anomaly, document_context):
            bonuses['industry_critical'] = self.BONUS_INDUSTRY_CRITICAL
            bonus_total += self.BONUS_INDUSTRY_CRITICAL

        # Regulatory violation bonus
        if self._is_regulatory_violation(anomaly):
            bonuses['regulatory_violation'] = self.BONUS_REGULATORY_VIOLATION
            bonus_total += self.BONUS_REGULATORY_VIOLATION

        # Final score
        final_score = base_score + bonus_total

        return {
            'final_score': final_score,
            'breakdown': {
                'severity_weight': severity_weight,
                'confidence': confidence,
                'user_relevance': user_relevance,
                'base_score': base_score,
                'bonuses': bonuses,
                'bonus_total': bonus_total
            }
        }

    def _calculate_user_relevance(self, anomaly: Dict[str, Any]) -> float:
        """
        Calculate user relevance multiplier based on preferences.

        Returns value between 0.5 (low relevance) and 1.5 (high relevance).

        Args:
            anomaly: Anomaly to evaluate

        Returns:
            User relevance multiplier (0.5 - 1.5)
        """
        if not self.user_preferences:
            return 1.0  # Neutral relevance

        # Check if anomaly category matches user priorities
        priority_categories = self.user_preferences.get('priority_categories', [])
        anomaly_category = anomaly.get('risk_category', '')

        if priority_categories and anomaly_category in priority_categories:
            # High relevance
            return 1.5

        # Check concern level
        concern_level = self.user_preferences.get('concern_level', 'medium')
        anomaly_severity = anomaly.get('severity', 'medium')

        if concern_level == 'high' and anomaly_severity in ['high', 'critical']:
            return 1.3
        elif concern_level == 'low' and anomaly_severity == 'low':
            return 0.7

        return 1.0  # Neutral relevance

    def _is_industry_critical(
        self,
        anomaly: Dict[str, Any],
        document_context: Dict[str, Any]
    ) -> bool:
        """
        Check if anomaly is critical for the industry.

        Args:
            anomaly: Anomaly to check
            document_context: Document context with industry

        Returns:
            True if industry-critical combination detected
        """
        industry = document_context.get('industry', '')
        if not industry or industry not in self.INDUSTRY_CRITICAL_COMBINATIONS:
            return False

        # Get critical indicators for this industry
        critical_indicators = self.INDUSTRY_CRITICAL_COMBINATIONS[industry]

        # Check if anomaly has any of these indicators
        anomaly_indicators = [
            ind['name'] for ind in anomaly.get('detected_indicators', [])
        ]
        anomaly_category = anomaly.get('risk_category', '')

        # Check indicators
        for critical in critical_indicators:
            if critical in anomaly_indicators or critical == anomaly_category:
                logger.debug(
                    f"Industry-critical match: {industry} + {critical} "
                    f"for clause {anomaly.get('clause_number', 'unknown')}"
                )
                return True

        return False

    def _is_regulatory_violation(self, anomaly: Dict[str, Any]) -> bool:
        """
        Check if anomaly involves regulatory violation.

        Args:
            anomaly: Anomaly to check

        Returns:
            True if regulatory violation detected
        """
        # Check indicators
        anomaly_indicators = [
            ind['name'] for ind in anomaly.get('detected_indicators', [])
        ]

        # Check category
        anomaly_category = anomaly.get('risk_category', '')

        for violation in self.REGULATORY_VIOLATIONS:
            if violation in anomaly_indicators or violation == anomaly_category:
                logger.debug(
                    f"Regulatory violation detected: {violation} "
                    f"for clause {anomaly.get('clause_number', 'unknown')}"
                )
                return True

        return False

    def _convert_compound_to_anomaly(
        self,
        compound_risk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert compound risk to anomaly format for ranking.

        Args:
            compound_risk: Compound risk from Stage 4

        Returns:
            Anomaly dict
        """
        return {
            'clause_number': f"COMPOUND_{compound_risk.get('compound_risk_type', 'unknown')}",
            'clause_text': compound_risk.get('description', ''),
            'severity': compound_risk.get('compound_severity', 'high').lower(),
            'risk_category': 'compound_risk',
            'is_compound_risk': True,
            'compound_risk_type': compound_risk.get('compound_risk_type'),
            'compound_risk_name': compound_risk.get('name'),
            'confidence_calibration': {
                'calibrated_confidence': compound_risk.get('confidence', 0.8),
                'confidence_tier': 'HIGH' if compound_risk.get('confidence', 0.8) >= 0.85 else 'MODERATE'
            },
            'detected_indicators': [],
            'explanation': compound_risk.get('description', ''),
            'consumer_impact': compound_risk.get('consumer_impact', ''),
            'recommendation': compound_risk.get('recommendation', '')
        }

    def _get_top_categories(
        self,
        anomalies: List[Dict[str, Any]],
        top_n: int = 5
    ) -> List[Dict[str, int]]:
        """
        Get top N risk categories from anomalies.

        Args:
            anomalies: List of anomalies
            top_n: Number of top categories to return

        Returns:
            List of dicts with category and count
        """
        category_counts = {}
        for anomaly in anomalies:
            category = anomaly.get('risk_category', 'other')
            category_counts[category] = category_counts.get(category, 0) + 1

        # Sort by count
        sorted_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            {'category': cat, 'count': count}
            for cat, count in sorted_categories[:top_n]
        ]

    def adjust_budget(self, max_alerts: int, target_alerts: int) -> None:
        """
        Adjust alert budget dynamically.

        Args:
            max_alerts: New maximum total alerts
            target_alerts: New target high-priority alerts
        """
        logger.info(
            f"Adjusting alert budget: "
            f"MAX_ALERTS {self.MAX_ALERTS} → {max_alerts}, "
            f"TARGET_ALERTS {self.TARGET_ALERTS} → {target_alerts}"
        )
        self.MAX_ALERTS = max_alerts
        self.TARGET_ALERTS = target_alerts
