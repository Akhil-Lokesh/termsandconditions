"""
Context-Aware Industry Baselines for T&C Analyzer.

Defines expected, outlier, and red flag patterns for each industry.
This enables context-aware risk assessment where the same pattern
has different meanings in different industries.

Pattern Categories:
- Expected: Normal for this industry, suppress or reduce severity
- Outlier: Unusual for this industry, flag as concerning
- Red Flags: ALWAYS problematic, never suppress, amplify severity
"""

import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IndustryBaseline:
    """Baseline configuration for an industry."""

    name: str
    description: str

    # Pattern categories
    expected: Set[str] = field(default_factory=set)
    outlier: Set[str] = field(default_factory=set)
    red_flags: Set[str] = field(default_factory=set)

    # Risk modifier (multiplier for base risk score)
    base_modifier: float = 1.0

    # Additional context
    typical_user_profile: str = "consumer"
    typical_power_dynamics: str = "take_it_or_leave_it"


class ContextAwareBaselines:
    """
    Industry-specific baselines with expected, outlier, and red flag patterns.

    For each industry, defines:
    - Expected patterns (normal, don't flag aggressively)
    - Outlier patterns (unusual, flag as concerning)
    - Red flag patterns (always flag regardless of prevalence)
    """

    # =========================================================================
    # PHASE 1: PRIORITY INDUSTRIES
    # =========================================================================

    INDUSTRY_BASELINES = {
        # -----------------------------------------------------------------
        # DEVELOPER TOOLS
        # Professional users, B2B, liability/indemnification is standard
        # -----------------------------------------------------------------
        'developer_tools': {
            'name': 'Developer Tools',
            'description': 'APIs, SDKs, developer platforms, cloud services',
            'base_modifier': 0.8,  # Lower risk - professional users
            'typical_user_profile': 'professional',
            'typical_power_dynamics': 'take_it_or_leave_it',

            # Expected patterns - NORMAL for dev tools, suppress/reduce
            'expected': {
                # Liability & Legal
                'broad_liability_disclaimer',
                'liability_limitation',
                'indemnification',
                'unlimited_liability',  # Common in B2B

                # Service terms
                'unilateral_changes',
                'unilateral_termination',
                'explicit_account_termination',

                # Technical restrictions
                'rate_limiting',
                'api_deprecation',
                'service_availability',
                'uptime_exclusions',

                # IP protection
                'reverse_engineering_prohibition',
                'decompilation_prohibition',

                # Standard business
                'auto_renewal',
                'asymmetric_jurisdiction',
                'forced_arbitration_class_waiver',  # Common in B2B
            },

            # Outlier patterns - UNUSUAL for dev tools, flag
            'outlier': {
                'biometric_data_collection',
                'location_tracking',
                'voice_video_retention',
                'social_graph_access',
                'contact_list_access',
                'browsing_history_tracking',
                'device_fingerprinting',
            },

            # Red flags - ALWAYS flag, amplify severity
            'red_flags': {
                'code_ownership_transfer',  # Company claims your code
                'mandatory_telemetry_no_optout',
                'warrantless_law_enforcement',
                'perpetual_irrevocable_license',  # Should be limited scope
                'ai_training',  # Without consent
                'data_selling',
            },
        },

        # -----------------------------------------------------------------
        # SOCIAL MEDIA
        # Consumer users, high data collection, content exploitation risks
        # -----------------------------------------------------------------
        'social_media': {
            'name': 'Social Media',
            'description': 'Social networks, messaging platforms, content sharing',
            'base_modifier': 1.8,  # Higher risk - consumer data, content
            'typical_user_profile': 'consumer',
            'typical_power_dynamics': 'take_it_or_leave_it',

            # Expected patterns - NORMAL for social media (but still note)
            'expected': {
                # Content licensing (unfortunately standard)
                'broad_content_license',
                'sublicensable_license',
                'worldwide_license',
                'royalty_free_license',

                # Data collection (business model)
                'data_sharing',
                'advertising_tracking',
                'third_party_sharing',

                # Platform operations
                'content_moderation_control',
                'unilateral_changes',
                'account_suspension',
                'unilateral_termination',

                # Standard terms
                'auto_renewal',
                'slow_content_deletion',  # Backup delays
            },

            # Outlier patterns - UNUSUAL even for social media
            'outlier': {
                'always_on_microphone',
                'location_when_app_closed',
                'contact_sync_required',
                'biometric_data_collection',  # Without clear consent
                'cross_platform_tracking',
            },

            # Red flags - ALWAYS flag
            'red_flags': {
                'perpetual_irrevocable_license',  # Worst form
                'ai_training',  # Content exploitation
                'no_content_deletion',  # GDPR violation
                'warrantless_law_enforcement',
                'forced_arbitration_class_waiver',  # Consumer protection
                'data_selling',  # Beyond ads
                'biometric_without_consent',
            },
        },

        # -----------------------------------------------------------------
        # GIG ECONOMY
        # Workers (professional), income dependency, exploitation risks
        # -----------------------------------------------------------------
        'gig_economy': {
            'name': 'Gig Economy',
            'description': 'Rideshare, delivery, freelance platforms',
            'base_modifier': 2.0,  # High risk - worker income at stake
            'typical_user_profile': 'professional',  # Workers are professionals
            'typical_power_dynamics': 'take_it_or_leave_it',

            # Expected patterns - NORMAL for gig platforms (but concerning)
            'expected': {
                # Worker classification (standard but problematic)
                'worker_misclassification',

                # Platform operations
                'rating_system',
                'background_check',
                'flexible_schedule',

                # Payment
                'payment_terms',
                'fee_structure',

                # Standard terms
                'unilateral_changes',
                'auto_renewal',
            },

            # Outlier patterns - UNUSUAL for gig work
            'outlier': {
                'forced_exclusivity',
                'non_compete_clause',
                'equipment_purchase_required',
                'mandatory_training_cost',
            },

            # Red flags - ALWAYS flag, AMPLIFY
            'red_flags': {
                'deactivation_no_appeal',  # Loss of income
                'tip_withholding',
                'unilateral_termination',  # Critical for income
                'forced_arbitration_class_waiver',  # Blocks organizing
                'fund_holds_freezing',  # Earnings held
                'wage_below_minimum',
                'equipment_cost_deduction',
                'mandatory_arbitration_collective',  # Blocks organizing
                'unlimited_liability',  # Worker bears all risk
            },
        },

        # -----------------------------------------------------------------
        # SAAS (B2B)
        # Business users, subscription model, standard B2B terms
        # -----------------------------------------------------------------
        'saas': {
            'name': 'SaaS / B2B Software',
            'description': 'Business software, productivity tools, enterprise services',
            'base_modifier': 1.3,  # Moderate - business users
            'typical_user_profile': 'professional',
            'typical_power_dynamics': 'negotiable',  # Enterprise can negotiate

            # Expected patterns - NORMAL for SaaS
            'expected': {
                # Liability (standard B2B)
                'broad_liability_disclaimer',
                'liability_limitation',
                'indemnification',

                # Service terms
                'unilateral_changes',
                'unilateral_termination',
                'service_availability',

                # Subscription
                'auto_renewal',
                'payment_terms',

                # Data
                'data_processing',
                'data_retention',

                # Legal
                'asymmetric_jurisdiction',
                'forced_arbitration_class_waiver',  # Common in B2B

                # IP
                'reverse_engineering_prohibition',
            },

            # Outlier patterns - UNUSUAL for B2B SaaS
            'outlier': {
                'perpetual_irrevocable_license',  # Should be limited
                'ai_training',  # Customer data
                'data_sharing',  # Beyond necessary
                'biometric_data_collection',
            },

            # Red flags - ALWAYS flag
            'red_flags': {
                'data_selling',
                'warrantless_law_enforcement',
                'no_data_export',  # Vendor lock-in
                'customer_data_ownership',  # Company claims customer data
            },
        },

        # -----------------------------------------------------------------
        # GENERAL (Default/Fallback)
        # -----------------------------------------------------------------
        'general': {
            'name': 'General',
            'description': 'Default baseline for unclassified documents',
            'base_modifier': 1.0,
            'typical_user_profile': 'consumer',
            'typical_power_dynamics': 'take_it_or_leave_it',

            'expected': {
                'unilateral_changes',
                'auto_renewal',
                'liability_limitation',
            },

            'outlier': {
                'perpetual_irrevocable_license',
                'ai_training',
                'biometric_data_collection',
            },

            'red_flags': {
                'data_selling',
                'warrantless_law_enforcement',
                'forced_arbitration_class_waiver',
            },
        },

        # -----------------------------------------------------------------
        # PHASE 2 INDUSTRIES (Basic definitions, to be expanded)
        # -----------------------------------------------------------------
        'financial': {
            'name': 'Financial Services',
            'description': 'Banking, payments, investment platforms',
            'base_modifier': 2.2,
            'typical_user_profile': 'consumer',
            'typical_power_dynamics': 'take_it_or_leave_it',

            'expected': {
                'forced_arbitration_class_waiver',  # 98% have this
                'fund_holds_freezing',  # Normal for payments
                'liability_limitation',
                'indemnification',
            },

            'outlier': {
                'perpetual_irrevocable_license',
                'ai_training',
            },

            'red_flags': {
                'fund_freeze_no_process',
                'warrantless_law_enforcement',
                'data_selling',
                'unlimited_liability',  # User bears all risk
            },
        },

        'healthcare': {
            'name': 'Healthcare',
            'description': 'Medical apps, telehealth, health tracking',
            'base_modifier': 2.5,
            'typical_user_profile': 'consumer',
            'typical_power_dynamics': 'take_it_or_leave_it',

            'expected': {
                'data_retention',  # Medical records
                'liability_limitation',
            },

            'outlier': {
                'data_sharing',  # With non-medical parties
                'ai_training',
            },

            'red_flags': {
                'hipaa_coverage_gap',
                'insurance_data_sharing',
                'employer_data_sharing',
                'warrantless_law_enforcement',
                'data_selling',
                'indefinite_data_retention',
            },
        },

        'streaming': {
            'name': 'Streaming',
            'description': 'Video, music, entertainment streaming',
            'base_modifier': 1.0,  # Baseline
            'typical_user_profile': 'consumer',
            'typical_power_dynamics': 'take_it_or_leave_it',

            'expected': {
                'auto_renewal',
                'unilateral_changes',
                'content_availability',  # Content can be removed
                'geographic_restrictions',
            },

            'outlier': {
                'biometric_data_collection',
                'location_tracking',
            },

            'red_flags': {
                'digital_ownership_illusion',  # Pretending purchase = ownership
                'warrantless_law_enforcement',
                'data_selling',
            },
        },

        'ecommerce': {
            'name': 'E-commerce',
            'description': 'Online retail, marketplaces',
            'base_modifier': 1.2,
            'typical_user_profile': 'consumer',
            'typical_power_dynamics': 'take_it_or_leave_it',

            'expected': {
                'return_policy',
                'shipping_terms',
                'payment_terms',
                'liability_limitation',
            },

            'outlier': {
                'perpetual_irrevocable_license',  # Why for shopping?
                'ai_training',
            },

            'red_flags': {
                'no_refund_absolute',
                'data_selling',
                'hidden_fees',
                'bait_and_switch',
            },
        },
    }

    def __init__(self):
        """Initialize baselines with IndustryBaseline objects."""
        self.baselines: Dict[str, IndustryBaseline] = {}

        for industry, config in self.INDUSTRY_BASELINES.items():
            self.baselines[industry] = IndustryBaseline(
                name=config['name'],
                description=config['description'],
                expected=set(config.get('expected', [])),
                outlier=set(config.get('outlier', [])),
                red_flags=set(config.get('red_flags', [])),
                base_modifier=config.get('base_modifier', 1.0),
                typical_user_profile=config.get('typical_user_profile', 'consumer'),
                typical_power_dynamics=config.get('typical_power_dynamics', 'take_it_or_leave_it'),
            )

    def get_baseline(self, industry: str) -> IndustryBaseline:
        """
        Get baseline for an industry.

        Args:
            industry: Industry identifier

        Returns:
            IndustryBaseline for the industry, or 'general' if not found
        """
        return self.baselines.get(industry, self.baselines['general'])

    def classify_pattern(
        self,
        pattern: str,
        industry: str
    ) -> str:
        """
        Classify a pattern for a given industry.

        Args:
            pattern: Pattern/indicator name
            industry: Industry identifier

        Returns:
            Classification: 'expected', 'outlier', 'red_flag', or 'neutral'
        """
        baseline = self.get_baseline(industry)

        if pattern in baseline.red_flags:
            return 'red_flag'
        elif pattern in baseline.outlier:
            return 'outlier'
        elif pattern in baseline.expected:
            return 'expected'
        else:
            return 'neutral'

    def get_modifier(self, industry: str) -> float:
        """
        Get base risk modifier for an industry.

        Args:
            industry: Industry identifier

        Returns:
            Risk multiplier (e.g., 0.8 for developer_tools, 2.0 for gig_economy)
        """
        baseline = self.get_baseline(industry)
        return baseline.base_modifier

    def get_all_industries(self) -> List[str]:
        """Get list of all supported industries."""
        return list(self.baselines.keys())

    def get_industry_summary(self, industry: str) -> Dict:
        """
        Get summary of an industry's baseline.

        Args:
            industry: Industry identifier

        Returns:
            Dict with industry baseline summary
        """
        baseline = self.get_baseline(industry)
        return {
            'name': baseline.name,
            'description': baseline.description,
            'base_modifier': baseline.base_modifier,
            'typical_user_profile': baseline.typical_user_profile,
            'typical_power_dynamics': baseline.typical_power_dynamics,
            'expected_count': len(baseline.expected),
            'outlier_count': len(baseline.outlier),
            'red_flag_count': len(baseline.red_flags),
        }
