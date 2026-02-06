"""
Context Risk Thresholds for T&C Analyzer.

Defines acceptable risk thresholds by industry and user profile.
Different contexts have different risk tolerance - what's acceptable
in developer tools may be critical in healthcare.

Threshold Actions:
- accept: Don't flag at all (expected for this context)
- warn: Flag as low severity (notable but not alarming)
- flag: Flag as medium severity (concerning)
- critical: Flag as high severity (serious risk)
"""

import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ThresholdResult:
    """Result of threshold evaluation."""

    action: str  # 'accept', 'warn', 'flag', 'critical'
    should_suppress: bool
    severity_adjustment: int  # -2, -1, 0, +1, +2
    reason: str


class ContextRiskThresholds:
    """
    Defines acceptable risk thresholds by context.

    Different users and industries have different risk tolerance:
    - Developer tools: Liability caps acceptable, biometric collection NOT
    - Social media: Data collection expected, AI training questionable
    - Healthcare: HIPAA required, data sharing critical
    """

    # =========================================================================
    # RISK THRESHOLDS BY INDUSTRY + USER PROFILE
    # =========================================================================

    # Actions: 'accept' (suppress), 'warn' (low), 'flag' (medium), 'critical' (high)
    RISK_THRESHOLDS = {
        # -----------------------------------------------------------------
        # DEVELOPER TOOLS
        # -----------------------------------------------------------------
        'developer_tools': {
            'professional': {
                # Legal terms - acceptable for professionals
                'broad_liability_disclaimer': 'accept',
                'liability_limitation': 'accept',
                'indemnification': 'accept',
                'unlimited_liability': 'warn',

                # Arbitration - acceptable in B2B
                'forced_arbitration_class_waiver': 'warn',
                'asymmetric_jurisdiction': 'accept',

                # Service terms - expected
                'unilateral_changes': 'warn',
                'unilateral_termination': 'warn',
                'explicit_account_termination': 'warn',
                'auto_renewal': 'accept',

                # IP protection - expected
                'reverse_engineering_prohibition': 'accept',

                # Data - context dependent
                'data_sharing': 'flag',
                'data_selling': 'critical',

                # Red flags - always flag
                'biometric_data_collection': 'critical',
                'perpetual_irrevocable_license': 'critical',
                'ai_training': 'flag',
                'warrantless_law_enforcement': 'critical',
            },
            'consumer': {
                # Less tolerance for consumers using dev tools
                'broad_liability_disclaimer': 'warn',
                'liability_limitation': 'warn',
                'forced_arbitration_class_waiver': 'flag',
                'biometric_data_collection': 'critical',
                'perpetual_irrevocable_license': 'critical',
            }
        },

        # -----------------------------------------------------------------
        # SOCIAL MEDIA
        # -----------------------------------------------------------------
        'social_media': {
            'consumer': {
                # Content licensing - expected but still note
                'broad_content_license': 'warn',
                'sublicensable_license': 'warn',
                'worldwide_license': 'warn',
                'royalty_free_license': 'warn',

                # Perpetual/irrevocable - problematic
                'perpetual_irrevocable_license': 'critical',

                # AI training - critical concern
                'ai_training': 'critical',

                # Data collection - expected but varies
                'data_sharing': 'flag',
                'advertising_tracking': 'warn',
                'third_party_sharing': 'flag',
                'data_selling': 'critical',

                # Biometrics - critical
                'biometric_data_collection': 'critical',
                'voice_video_retention': 'flag',

                # Platform control - expected
                'content_moderation_control': 'warn',
                'unilateral_termination': 'warn',
                'account_suspension': 'warn',

                # Legal - consumer protection concern
                'forced_arbitration_class_waiver': 'critical',
                'broad_liability_disclaimer': 'flag',

                # Surveillance
                'warrantless_law_enforcement': 'critical',
                'browsing_history_tracking': 'flag',
            },
            'vulnerable_population': {
                # Everything more severe for vulnerable users
                'data_sharing': 'critical',
                'biometric_data_collection': 'critical',
                'perpetual_irrevocable_license': 'critical',
                'ai_training': 'critical',
                'advertising_tracking': 'critical',
            }
        },

        # -----------------------------------------------------------------
        # GIG ECONOMY
        # -----------------------------------------------------------------
        'gig_economy': {
            'professional': {
                # Worker classification - flag but it's the norm
                'worker_misclassification': 'flag',

                # Income critical - anything threatening income is serious
                'unilateral_termination': 'critical',
                'explicit_account_termination': 'critical',
                'deactivation_no_appeal': 'critical',

                # Earnings protection
                'fund_holds_freezing': 'critical',
                'tip_withholding': 'critical',

                # Worker rights
                'forced_arbitration_class_waiver': 'critical',
                'unlimited_liability': 'critical',

                # Standard terms - more acceptable
                'unilateral_changes': 'flag',
                'auto_renewal': 'warn',

                # Data
                'data_sharing': 'flag',
                'location_tracking': 'warn',  # Often required for service

                # Rating/reputation
                'rating_system': 'warn',  # Expected
            }
        },

        # -----------------------------------------------------------------
        # SAAS
        # -----------------------------------------------------------------
        'saas': {
            'professional': {
                # Legal - standard B2B
                'broad_liability_disclaimer': 'accept',
                'liability_limitation': 'accept',
                'indemnification': 'accept',
                'forced_arbitration_class_waiver': 'warn',
                'asymmetric_jurisdiction': 'accept',

                # Service terms
                'unilateral_changes': 'warn',
                'unilateral_termination': 'warn',
                'auto_renewal': 'accept',

                # Data handling
                'data_retention': 'accept',
                'data_processing': 'accept',
                'data_sharing': 'flag',  # With third parties
                'data_selling': 'critical',

                # Customer data
                'ai_training': 'flag',  # On customer data
                'perpetual_irrevocable_license': 'flag',
            },
            'consumer': {
                # More protection for consumer SaaS
                'forced_arbitration_class_waiver': 'flag',
                'perpetual_irrevocable_license': 'critical',
                'ai_training': 'critical',
            }
        },

        # -----------------------------------------------------------------
        # FINANCIAL
        # -----------------------------------------------------------------
        'financial': {
            'consumer': {
                # Arbitration - very common but problematic
                'forced_arbitration_class_waiver': 'flag',  # 98% have it

                # Fund protection - critical
                'fund_holds_freezing': 'flag',  # Common but note it
                'fund_freeze_no_process': 'critical',
                'unilateral_termination': 'critical',

                # Liability
                'broad_liability_disclaimer': 'flag',
                'unlimited_liability': 'critical',

                # Data
                'data_selling': 'critical',
                'warrantless_law_enforcement': 'critical',
            }
        },

        # -----------------------------------------------------------------
        # HEALTHCARE
        # -----------------------------------------------------------------
        'healthcare': {
            'consumer': {
                # HIPAA - critical
                'hipaa_coverage_gap': 'critical',

                # Data sharing - very sensitive
                'data_sharing': 'critical',
                'insurance_data_sharing': 'critical',
                'employer_data_sharing': 'critical',
                'data_selling': 'critical',

                # Retention
                'indefinite_data_retention': 'critical',
                'data_retention': 'flag',

                # Standard terms
                'liability_limitation': 'flag',
                'forced_arbitration_class_waiver': 'flag',
            },
            'vulnerable_population': {
                # Everything critical for vulnerable health users
                'data_sharing': 'critical',
                'hipaa_coverage_gap': 'critical',
                'data_selling': 'critical',
            }
        },

        # -----------------------------------------------------------------
        # GENERAL (Default)
        # -----------------------------------------------------------------
        'general': {
            'consumer': {
                'broad_liability_disclaimer': 'flag',
                'forced_arbitration_class_waiver': 'flag',
                'perpetual_irrevocable_license': 'critical',
                'ai_training': 'critical',
                'biometric_data_collection': 'critical',
                'data_selling': 'critical',
                'warrantless_law_enforcement': 'critical',
                'unilateral_termination': 'flag',
                'auto_renewal': 'warn',
            },
            'professional': {
                'broad_liability_disclaimer': 'warn',
                'forced_arbitration_class_waiver': 'warn',
                'perpetual_irrevocable_license': 'flag',
                'ai_training': 'flag',
                'biometric_data_collection': 'critical',
                'data_selling': 'critical',
            },
            'vulnerable_population': {
                # More protection for vulnerable
                'data_sharing': 'critical',
                'biometric_data_collection': 'critical',
                'perpetual_irrevocable_license': 'critical',
                'ai_training': 'critical',
                'forced_arbitration_class_waiver': 'critical',
            }
        },
    }

    # Severity adjustment map
    ACTION_TO_ADJUSTMENT = {
        'accept': -3,     # Suppress entirely
        'warn': -1,       # Reduce severity by 1 level
        'flag': 0,        # Keep as-is
        'critical': +1,   # Increase severity by 1 level
    }

    def __init__(self):
        """Initialize risk thresholds."""
        pass

    def get_threshold(
        self,
        industry: str,
        user_profile: str,
        pattern: str
    ) -> str:
        """
        Get risk threshold for a specific context and pattern.

        Args:
            industry: Industry identifier
            user_profile: User profile type
            pattern: Pattern/indicator name

        Returns:
            Threshold action: 'accept', 'warn', 'flag', or 'critical'
        """
        # Try specific industry + profile
        industry_thresholds = self.RISK_THRESHOLDS.get(industry, {})
        profile_thresholds = industry_thresholds.get(user_profile, {})

        if pattern in profile_thresholds:
            return profile_thresholds[pattern]

        # Fallback to general + profile
        general_thresholds = self.RISK_THRESHOLDS.get('general', {})
        general_profile = general_thresholds.get(user_profile, {})

        if pattern in general_profile:
            return general_profile[pattern]

        # Default to 'flag' (no adjustment)
        return 'flag'

    def evaluate_threshold(
        self,
        industry: str,
        user_profile: str,
        pattern: str,
        base_severity: str
    ) -> ThresholdResult:
        """
        Evaluate threshold and determine action.

        Args:
            industry: Industry identifier
            user_profile: User profile type
            pattern: Pattern/indicator name
            base_severity: Original severity ('low', 'medium', 'high', 'critical')

        Returns:
            ThresholdResult with action and adjustments
        """
        action = self.get_threshold(industry, user_profile, pattern)
        adjustment = self.ACTION_TO_ADJUSTMENT.get(action, 0)

        # Determine if should suppress
        should_suppress = (action == 'accept')

        # Generate reason
        if action == 'accept':
            reason = f"Pattern '{pattern}' is expected in {industry} for {user_profile} users"
        elif action == 'warn':
            reason = f"Pattern '{pattern}' is common but notable in {industry}"
        elif action == 'critical':
            reason = f"Pattern '{pattern}' is a serious concern in {industry} for {user_profile} users"
        else:
            reason = f"Pattern '{pattern}' flagged at standard level for {industry}"

        return ThresholdResult(
            action=action,
            should_suppress=should_suppress,
            severity_adjustment=adjustment,
            reason=reason
        )

    def should_suppress(
        self,
        industry: str,
        user_profile: str,
        pattern: str
    ) -> Tuple[bool, str]:
        """
        Determine if an alert should be suppressed.

        Args:
            industry: Industry identifier
            user_profile: User profile type
            pattern: Pattern/indicator name

        Returns:
            Tuple of (should_suppress, reason)
        """
        result = self.evaluate_threshold(industry, user_profile, pattern, 'medium')
        return result.should_suppress, result.reason

    def adjust_severity(
        self,
        base_severity: str,
        adjustment: int
    ) -> str:
        """
        Adjust severity based on threshold.

        Args:
            base_severity: Original severity
            adjustment: Adjustment value (-2 to +2)

        Returns:
            Adjusted severity
        """
        severity_levels = ['low', 'medium', 'high', 'critical']

        try:
            current_index = severity_levels.index(base_severity)
        except ValueError:
            current_index = 1  # Default to medium

        new_index = max(0, min(len(severity_levels) - 1, current_index + adjustment))
        return severity_levels[new_index]
