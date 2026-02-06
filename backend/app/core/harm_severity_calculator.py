"""
Harm Severity Calculator for T&C Analyzer.

Calculates context-adjusted harm severity based on:
- Industry-specific pattern impact
- User profile vulnerability
- Power dynamics (negotiable vs monopoly)
- Data sensitivity level

Formula:
    Final_Risk = Base_Risk × Industry_Mult × User_Mult × Power_Mult × Data_Mult
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HarmCalculationResult:
    """Result of harm severity calculation."""

    base_severity: str
    adjusted_severity: str
    final_multiplier: float
    industry_multiplier: float
    user_multiplier: float
    power_multiplier: float
    data_multiplier: float
    explanation: str


class HarmSeverityCalculator:
    """
    Calculates context-adjusted harm severity.

    Same pattern has different real-world impact in different contexts:
    - Termination clause: Minor annoyance in dev tools, income loss in gig economy
    - Fund holds: Irrelevant for free apps, critical for financial services
    - Arbitration: Acceptable in B2B, blocks collective action in gig work
    """

    # =========================================================================
    # INDUSTRY-SPECIFIC PATTERN MULTIPLIERS
    # =========================================================================

    # Pattern → Industry → Multiplier
    # Multiplier meaning:
    #   < 1.0: Lower harm in this context
    #   = 1.0: Standard harm
    #   > 1.0: Higher harm in this context

    PATTERN_INDUSTRY_MULTIPLIERS = {
        # -----------------------------------------------------------------
        # TERMINATION / DEACTIVATION
        # -----------------------------------------------------------------
        'unilateral_termination': {
            'developer_tools': 0.5,    # Find another API
            'social_media': 0.8,       # Loss of audience
            'gig_economy': 2.5,        # LOSS OF INCOME
            'saas': 0.7,               # Switch providers
            'financial': 2.0,          # Loss of banking access
            'healthcare': 1.5,         # Loss of medical access
            'general': 1.0,
        },
        'explicit_account_termination': {
            'developer_tools': 0.5,
            'social_media': 0.8,
            'gig_economy': 2.5,
            'financial': 2.0,
            'general': 1.0,
        },
        'deactivation_no_appeal': {
            'gig_economy': 3.0,        # Devastating for workers
            'financial': 2.5,
            'general': 1.5,
        },

        # -----------------------------------------------------------------
        # FUND HOLDS / FINANCIAL RISKS
        # -----------------------------------------------------------------
        'fund_holds_freezing': {
            'developer_tools': 0.3,    # Usually not relevant
            'social_media': 0.5,       # Creator economy
            'gig_economy': 2.5,        # Their earnings!
            'financial': 2.5,          # Their money!
            'general': 1.0,
        },
        'fund_freeze_no_process': {
            'gig_economy': 3.0,
            'financial': 3.0,
            'general': 2.0,
        },
        'tip_withholding': {
            'gig_economy': 3.0,        # Wage theft
            'general': 2.0,
        },

        # -----------------------------------------------------------------
        # DATA COLLECTION / PRIVACY
        # -----------------------------------------------------------------
        'data_sharing': {
            'developer_tools': 0.5,    # Technical data
            'social_media': 1.0,       # Expected but concerning
            'healthcare': 2.5,         # Medical data!
            'financial': 2.0,          # Financial data!
            'general': 1.2,
        },
        'data_selling': {
            'developer_tools': 1.5,
            'social_media': 2.0,
            'healthcare': 3.0,         # Medical data sale
            'financial': 3.0,
            'general': 2.0,
        },
        'biometric_data_collection': {
            'developer_tools': 2.5,    # Why would they need this?
            'social_media': 2.0,
            'healthcare': 1.5,         # May be legitimate
            'general': 2.0,
        },
        'location_tracking': {
            'gig_economy': 0.8,        # Needed for service
            'social_media': 1.5,
            'general': 1.2,
        },

        # -----------------------------------------------------------------
        # CONTENT / IP RIGHTS
        # -----------------------------------------------------------------
        'perpetual_irrevocable_license': {
            'developer_tools': 2.0,    # Your code!
            'social_media': 2.5,       # Your content forever
            'saas': 1.5,
            'general': 2.0,
        },
        'ai_training': {
            'developer_tools': 2.0,    # Training on your code
            'social_media': 2.5,       # Content exploitation
            'saas': 2.0,               # Customer data
            'general': 2.0,
        },
        'broad_content_license': {
            'developer_tools': 0.5,    # Limited content
            'social_media': 1.5,       # User content
            'general': 1.0,
        },

        # -----------------------------------------------------------------
        # ARBITRATION / LEGAL
        # -----------------------------------------------------------------
        'forced_arbitration_class_waiver': {
            'developer_tools': 0.6,    # B2B acceptable
            'social_media': 1.5,       # Consumer protection issue
            'gig_economy': 2.5,        # Blocks organizing
            'financial': 2.0,          # Consumer protection
            'saas': 0.8,               # B2B common
            'general': 1.5,
        },
        'asymmetric_jurisdiction': {
            'developer_tools': 0.5,    # Professional users
            'gig_economy': 1.5,
            'general': 1.0,
        },

        # -----------------------------------------------------------------
        # LIABILITY / INDEMNIFICATION
        # -----------------------------------------------------------------
        'broad_liability_disclaimer': {
            'developer_tools': 0.4,    # Standard B2B
            'social_media': 1.0,
            'gig_economy': 1.5,        # Worker risk
            'healthcare': 2.0,         # Medical consequences
            'financial': 1.5,
            'saas': 0.5,               # Standard B2B
            'general': 1.0,
        },
        'liability_limitation': {
            'developer_tools': 0.4,
            'saas': 0.5,
            'healthcare': 1.5,
            'general': 0.8,
        },
        'indemnification': {
            'developer_tools': 0.4,    # Standard B2B
            'saas': 0.5,
            'gig_economy': 1.5,
            'general': 1.0,
        },
        'unlimited_liability': {
            'developer_tools': 0.8,
            'gig_economy': 2.5,        # Worker bears all risk
            'financial': 2.0,
            'general': 1.5,
        },

        # -----------------------------------------------------------------
        # SERVICE TERMS
        # -----------------------------------------------------------------
        'unilateral_changes': {
            'developer_tools': 0.6,    # API evolution
            'social_media': 1.0,
            'gig_economy': 1.5,        # Terms change, income affected
            'financial': 1.5,
            'general': 1.0,
        },
        'auto_renewal': {
            'developer_tools': 0.3,
            'social_media': 0.5,
            'financial': 1.0,
            'general': 0.5,
        },

        # -----------------------------------------------------------------
        # SURVEILLANCE / LAW ENFORCEMENT
        # -----------------------------------------------------------------
        'warrantless_law_enforcement': {
            'developer_tools': 2.0,
            'social_media': 2.5,
            'healthcare': 3.0,         # Medical privacy
            'financial': 2.5,
            'general': 2.5,
        },

        # -----------------------------------------------------------------
        # HEALTHCARE SPECIFIC
        # -----------------------------------------------------------------
        'hipaa_coverage_gap': {
            'healthcare': 3.0,
            'general': 2.0,
        },
        'insurance_data_sharing': {
            'healthcare': 3.0,
            'general': 2.0,
        },
        'employer_data_sharing': {
            'healthcare': 3.0,
            'general': 2.0,
        },

        # -----------------------------------------------------------------
        # GIG ECONOMY SPECIFIC
        # -----------------------------------------------------------------
        'worker_misclassification': {
            'gig_economy': 2.0,        # It's the norm but harmful
            'general': 1.5,
        },
        'rating_system': {
            'gig_economy': 1.0,        # Expected
            'general': 0.5,
        },
    }

    # =========================================================================
    # USER PROFILE MULTIPLIERS
    # =========================================================================

    USER_PROFILE_MULTIPLIERS = {
        'professional': 0.7,       # More sophisticated, can negotiate
        'consumer': 1.0,           # Baseline
        'vulnerable_population': 1.8,  # Higher harm potential
    }

    # =========================================================================
    # POWER DYNAMICS MULTIPLIERS
    # =========================================================================

    POWER_DYNAMICS_MULTIPLIERS = {
        'negotiable': 0.5,          # Can negotiate terms
        'take_it_or_leave_it': 1.0, # Standard adhesion
        'monopoly': 1.5,            # No alternatives
    }

    # =========================================================================
    # DATA SENSITIVITY MULTIPLIERS
    # =========================================================================

    DATA_SENSITIVITY_MULTIPLIERS = {
        'low': 0.8,
        'medium': 1.0,
        'high': 1.5,
        'critical': 2.0,
    }

    # =========================================================================
    # SEVERITY LEVELS
    # =========================================================================

    SEVERITY_LEVELS = ['low', 'medium', 'high', 'critical']
    SEVERITY_SCORES = {
        'low': 1.0,
        'medium': 2.0,
        'high': 3.0,
        'critical': 4.0,
    }

    def __init__(self):
        """Initialize harm severity calculator."""
        pass

    def get_pattern_multiplier(
        self,
        pattern: str,
        industry: str
    ) -> float:
        """
        Get industry-specific multiplier for a pattern.

        Args:
            pattern: Pattern/indicator name
            industry: Industry identifier

        Returns:
            Multiplier value (default 1.0)
        """
        pattern_mults = self.PATTERN_INDUSTRY_MULTIPLIERS.get(pattern, {})
        return pattern_mults.get(industry, pattern_mults.get('general', 1.0))

    def calculate_harm(
        self,
        pattern: str,
        base_severity: str,
        industry: str,
        user_profile: str = 'consumer',
        power_dynamics: str = 'take_it_or_leave_it',
        data_sensitivity: str = 'medium'
    ) -> HarmCalculationResult:
        """
        Calculate context-adjusted harm severity.

        Args:
            pattern: Pattern/indicator name
            base_severity: Original severity ('low', 'medium', 'high', 'critical')
            industry: Industry identifier
            user_profile: User profile type
            power_dynamics: Power dynamics type
            data_sensitivity: Data sensitivity level

        Returns:
            HarmCalculationResult with adjusted severity and explanation
        """
        # Get multipliers
        industry_mult = self.get_pattern_multiplier(pattern, industry)
        user_mult = self.USER_PROFILE_MULTIPLIERS.get(user_profile, 1.0)
        power_mult = self.POWER_DYNAMICS_MULTIPLIERS.get(power_dynamics, 1.0)
        data_mult = self.DATA_SENSITIVITY_MULTIPLIERS.get(data_sensitivity, 1.0)

        # Calculate final multiplier with cap to prevent over-amplification
        raw_mult = industry_mult * user_mult * power_mult * data_mult
        # Cap multiplier at 2.5 to prevent everything becoming 'critical'
        final_mult = min(raw_mult, 2.5)

        # Convert base severity to score
        base_score = self.SEVERITY_SCORES.get(base_severity, 2.0)

        # Calculate adjusted score
        adjusted_score = base_score * final_mult

        # Convert back to severity level (pass pattern for critical override check)
        adjusted_severity = self._score_to_severity(adjusted_score, pattern)

        # Generate explanation
        explanation = self._generate_explanation(
            pattern, base_severity, adjusted_severity,
            industry, user_profile, power_dynamics, data_sensitivity,
            industry_mult, user_mult, power_mult, data_mult
        )

        return HarmCalculationResult(
            base_severity=base_severity,
            adjusted_severity=adjusted_severity,
            final_multiplier=final_mult,
            industry_multiplier=industry_mult,
            user_multiplier=user_mult,
            power_multiplier=power_mult,
            data_multiplier=data_mult,
            explanation=explanation
        )

    def _score_to_severity(self, score: float, pattern: str = None) -> str:
        """
        Convert numeric score to severity level.

        Thresholds (raised to reduce false 'critical' ratings):
        - < 1.5: low
        - < 2.5: medium
        - < 6.0: high (raised from 5.0)
        - >= 6.0: critical (raised from 5.0)

        With multiplier cap of 2.5:
        - 'low' (1.0) * 2.5 = 2.5 → 'medium'
        - 'medium' (2.0) * 2.5 = 5.0 → 'high' (not critical anymore)
        - 'high' (3.0) * 2.5 = 7.5 → 'critical'

        This means 'critical' requires:
        - Base 'high' severity with significant (2x+) amplification, OR
        - Pattern in ALWAYS_CRITICAL list (bypasses score check)
        """
        # Import here to avoid circular import
        from .constants import CriticalPatterns

        # Check for always-critical patterns first (bypass score check)
        if pattern:
            # Normalize pattern name for comparison
            pattern_normalized = pattern.lower().replace('-', '_').replace(' ', '_')
            if pattern_normalized in CriticalPatterns.ALWAYS_CRITICAL:
                return 'critical'

        # Score-based severity
        if score < 1.5:
            return 'low'
        elif score < 2.5:
            return 'medium'
        elif score < 6.0:  # Raised from 5.0
            return 'high'
        else:
            return 'critical'

    def _generate_explanation(
        self,
        pattern: str,
        base_severity: str,
        adjusted_severity: str,
        industry: str,
        user_profile: str,
        power_dynamics: str,
        data_sensitivity: str,
        industry_mult: float,
        user_mult: float,
        power_mult: float,
        data_mult: float
    ) -> str:
        """Generate human-readable explanation of adjustment."""
        parts = []

        # Industry impact
        if industry_mult < 0.8:
            parts.append(f"lower impact in {industry}")
        elif industry_mult > 1.2:
            parts.append(f"higher impact in {industry}")

        # User vulnerability
        if user_mult > 1.2:
            parts.append("increased risk for vulnerable users")
        elif user_mult < 0.8:
            parts.append("professional users can mitigate")

        # Power dynamics
        if power_mult > 1.2:
            parts.append("no alternatives available")
        elif power_mult < 0.8:
            parts.append("terms may be negotiable")

        # Data sensitivity
        if data_mult > 1.2:
            parts.append("involves sensitive data")

        # Severity change
        if adjusted_severity != base_severity:
            direction = "increased" if self.SEVERITY_LEVELS.index(adjusted_severity) > \
                       self.SEVERITY_LEVELS.index(base_severity) else "reduced"
            parts.append(f"severity {direction} from {base_severity} to {adjusted_severity}")

        if parts:
            return "; ".join(parts).capitalize()
        else:
            return "Standard risk assessment applies"

    def should_amplify(
        self,
        pattern: str,
        industry: str,
        user_profile: str = 'consumer'
    ) -> Tuple[bool, float]:
        """
        Determine if a pattern should be amplified (multiplier > 1.5).

        Args:
            pattern: Pattern/indicator name
            industry: Industry identifier
            user_profile: User profile type

        Returns:
            Tuple of (should_amplify, multiplier)
        """
        industry_mult = self.get_pattern_multiplier(pattern, industry)
        user_mult = self.USER_PROFILE_MULTIPLIERS.get(user_profile, 1.0)
        combined = industry_mult * user_mult

        return (combined > 1.5, combined)

    def should_suppress(
        self,
        pattern: str,
        industry: str,
        user_profile: str = 'consumer'
    ) -> Tuple[bool, float]:
        """
        Determine if a pattern should be suppressed (multiplier < 0.5).

        Args:
            pattern: Pattern/indicator name
            industry: Industry identifier
            user_profile: User profile type

        Returns:
            Tuple of (should_suppress, multiplier)
        """
        industry_mult = self.get_pattern_multiplier(pattern, industry)
        user_mult = self.USER_PROFILE_MULTIPLIERS.get(user_profile, 1.0)
        combined = industry_mult * user_mult

        return (combined < 0.5, combined)

    def get_critical_patterns_for_industry(self, industry: str) -> Dict[str, float]:
        """
        Get patterns that are critical for a specific industry.

        Args:
            industry: Industry identifier

        Returns:
            Dict of pattern -> multiplier for patterns with multiplier >= 2.0
        """
        critical = {}

        for pattern, mults in self.PATTERN_INDUSTRY_MULTIPLIERS.items():
            mult = mults.get(industry, mults.get('general', 1.0))
            if mult >= 2.0:
                critical[pattern] = mult

        return critical
