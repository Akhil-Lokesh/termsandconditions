"""
Service Type Context Filter for Stage 2 Anomaly Detection.

Filters anomalies based on service type context to reduce false positives.
Different service types have different expectations for what clauses are normal vs alarming.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ServiceTypeContextFilter:
    """
    Filters anomalies based on service type context.

    Reduces false positives by understanding that certain clauses are expected
    for specific service types (e.g., auto-renewal is normal for subscriptions)
    while others are alarming (e.g., auto-renewal for one-time purchases).
    """

    # Service type context definitions
    SERVICE_TYPE_CONTEXTS = {
        'subscription': {
            'expected': [
                'auto_renewal',
                'recurring_billing',
                'cancellation_policy',
                'payment_method',
                'subscription_terms',
                'billing_cycle',
                'price_changes'
            ],
            'alarming': [
                'no_cancellation',
                'cancellation_fee_over_20_percent',
                'immediate_charge_no_trial',
                'difficult_cancellation',
                'hidden_auto_renewal',
                'no_reminder_before_renewal'
            ],
            'requires_disclosure': [
                'auto_renewal',
                'price_increases',
                'billing_cycle_changes',
                'automatic_upgrades'
            ]
        },
        'one_time_purchase': {
            'expected': [
                'refund_policy',
                'warranty',
                'return_policy',
                'purchase_terms',
                'delivery_terms',
                'one_time_payment'
            ],
            'alarming': [
                'auto_renewal',
                'recurring_charges',
                'hidden_fees',
                'subscription_conversion',
                'mandatory_account',
                'data_selling',
                'forced_arbitration'
            ],
            'requires_disclosure': [
                'no_refund',
                'restocking_fee',
                'limited_warranty'
            ]
        },
        'freemium': {
            'expected': [
                'upgrade_prompts',
                'feature_limitations',
                'ads',
                'premium_features',
                'free_tier_limits',
                'data_collection_for_ads',
                'account_required'
            ],
            'alarming': [
                'auto_upgrade_to_paid',
                'cannot_delete_account',
                'forced_upgrade',
                'sell_data_beyond_ads',
                'hidden_paid_features',
                'bait_and_switch'
            ],
            'requires_disclosure': [
                'feature_limitations',
                'ads',
                'data_collection',
                'upgrade_costs'
            ]
        },
        'free_with_ads': {
            'expected': [
                'data_collection_for_ads',
                'third_party_advertisers',
                'ad_personalization',
                'cookies',
                'tracking',
                'ad_frequency',
                'free_service'
            ],
            'alarming': [
                'sell_data_beyond_ads',
                'cannot_opt_out',
                'excessive_tracking',
                'share_with_data_brokers',
                'no_privacy_controls',
                'malicious_ads'
            ],
            'requires_disclosure': [
                'data_collection_for_ads',
                'third_party_sharing',
                'tracking_extent',
                'data_selling'
            ]
        },
        'trial': {
            'expected': [
                'auto_convert_to_paid',
                'credit_card_required',
                'trial_duration',
                'trial_terms',
                'conversion_notice',
                'cancellation_before_charge'
            ],
            'alarming': [
                'immediate_charge',
                'no_reminder',
                'difficult_cancellation',
                'hidden_trial_end',
                'charge_without_notice',
                'cannot_cancel_during_trial'
            ],
            'requires_disclosure': [
                'auto_convert_to_paid',
                'trial_duration',
                'cancellation_method',
                'charge_date'
            ]
        }
    }

    def __init__(self):
        """Initialize the service type context filter."""
        logger.info("ServiceTypeContextFilter initialized")

        # Validate service type contexts
        self._validate_contexts()

    def _validate_contexts(self):
        """Validate that all service type contexts have required keys."""
        required_keys = ['expected', 'alarming', 'requires_disclosure']

        for service_type, context in self.SERVICE_TYPE_CONTEXTS.items():
            for key in required_keys:
                if key not in context:
                    logger.warning(
                        f"Service type '{service_type}' missing required key: {key}"
                    )
                elif not isinstance(context[key], list):
                    logger.warning(
                        f"Service type '{service_type}' key '{key}' is not a list"
                    )

        logger.info(
            f"Validated {len(self.SERVICE_TYPE_CONTEXTS)} service type contexts"
        )

    def filter_by_service_context(
        self,
        detection: Dict[str, Any],
        service_type: str,
        clause_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Filter anomaly detection based on service type context.

        Args:
            detection: The anomaly detection result from Stage 1
            service_type: Type of service (subscription, one_time_purchase, etc.)
            clause_metadata: Additional metadata about the clause (position, clarity, etc.)

        Returns:
            Dict containing:
                - keep_anomaly (bool): Whether to keep this as an anomaly
                - reason (str): Explanation for the decision
                - context_score (float): 0-1 score (lower = more concerning)
                - requires_clear_disclosure (bool): Whether clear disclosure is required
                - service_type (str): The service type used for filtering
                - category (str): The category of the clause
        """
        try:
            # Get category from detection
            category = detection.get('category', 'unknown')

            # Handle unknown service type
            if service_type not in self.SERVICE_TYPE_CONTEXTS:
                logger.warning(f"Unknown service type: {service_type}, using neutral handling")
                return {
                    'keep_anomaly': True,
                    'reason': f'Unknown service type "{service_type}", keeping anomaly for manual review',
                    'context_score': 0.5,
                    'requires_clear_disclosure': False,
                    'service_type': service_type,
                    'category': category
                }

            context = self.SERVICE_TYPE_CONTEXTS[service_type]

            # Check if category is expected for this service type
            is_expected = self._is_category_expected(category, context['expected'])

            # Check if category is alarming for this service type
            is_alarming = self._is_category_alarming(category, context['alarming'])

            # Check if disclosure is required
            requires_disclosure = self._requires_disclosure(category, context['requires_disclosure'])

            # Check disclosure quality if disclosure is required
            has_clear_disclosure = False
            if requires_disclosure:
                has_clear_disclosure = self._check_disclosure_quality(clause_metadata)

            # Apply filtering logic
            if is_alarming:
                # Alarming categories are always kept as anomalies
                return {
                    'keep_anomaly': True,
                    'reason': (
                        f'Category "{category}" is alarming for {service_type} services. '
                        f'This practice is concerning and should be flagged.'
                    ),
                    'context_score': 0.1,  # Very low score = very concerning
                    'requires_clear_disclosure': True,
                    'service_type': service_type,
                    'category': category
                }

            elif is_expected:
                if requires_disclosure:
                    if has_clear_disclosure:
                        # Expected with clear disclosure - not an anomaly
                        return {
                            'keep_anomaly': False,
                            'reason': (
                                f'Category "{category}" is expected for {service_type} services '
                                f'and has clear disclosure. This is a standard practice.'
                            ),
                            'context_score': 0.9,  # High score = not concerning
                            'requires_clear_disclosure': True,
                            'service_type': service_type,
                            'category': category
                        }
                    else:
                        # Expected but lacks clear disclosure - keep as anomaly
                        return {
                            'keep_anomaly': True,
                            'reason': (
                                f'Category "{category}" is expected for {service_type} services '
                                f'but lacks clear disclosure. Should be more transparent.'
                            ),
                            'context_score': 0.5,  # Medium score = moderate concern
                            'requires_clear_disclosure': True,
                            'service_type': service_type,
                            'category': category
                        }
                else:
                    # Expected and doesn't require special disclosure - not an anomaly
                    return {
                        'keep_anomaly': False,
                        'reason': (
                            f'Category "{category}" is expected for {service_type} services. '
                            f'This is a standard practice.'
                        ),
                        'context_score': 0.9,  # High score = not concerning
                        'requires_clear_disclosure': False,
                        'service_type': service_type,
                        'category': category
                    }

            else:
                # Neither expected nor alarming - neutral, keep for review
                return {
                    'keep_anomaly': True,
                    'reason': (
                        f'Category "{category}" is neither expected nor alarming for '
                        f'{service_type} services. Keeping for manual review.'
                    ),
                    'context_score': 0.5,  # Neutral score
                    'requires_clear_disclosure': requires_disclosure,
                    'service_type': service_type,
                    'category': category
                }

        except Exception as e:
            logger.error(f"Error filtering by service context: {str(e)}", exc_info=True)
            # On error, keep the anomaly to be safe
            return {
                'keep_anomaly': True,
                'reason': f'Error during context filtering: {str(e)}',
                'context_score': 0.5,
                'requires_clear_disclosure': False,
                'service_type': service_type,
                'category': detection.get('category', 'unknown'),
                'error': str(e)
            }

    def _is_category_expected(self, category: str, expected_list: List[str]) -> bool:
        """
        Check if a category is expected.

        Uses fuzzy matching to handle variations in category names.
        """
        category_lower = category.lower()

        for expected in expected_list:
            expected_lower = expected.lower()

            # Exact match
            if category_lower == expected_lower:
                return True

            # Fuzzy match - check if category contains expected or vice versa
            if expected_lower in category_lower or category_lower in expected_lower:
                return True

            # Check for common variations
            # e.g., "auto_renewal" matches "automatic_renewal"
            category_normalized = category_lower.replace('_', ' ').replace('-', ' ')
            expected_normalized = expected_lower.replace('_', ' ').replace('-', ' ')

            if category_normalized == expected_normalized:
                return True

            if expected_normalized in category_normalized or category_normalized in expected_normalized:
                return True

        return False

    def _is_category_alarming(self, category: str, alarming_list: List[str]) -> bool:
        """
        Check if a category is alarming.

        Uses fuzzy matching to handle variations in category names.
        """
        # Same logic as _is_category_expected
        return self._is_category_expected(category, alarming_list)

    def _requires_disclosure(self, category: str, disclosure_list: List[str]) -> bool:
        """
        Check if a category requires disclosure.

        Uses fuzzy matching to handle variations in category names.
        """
        # Same logic as _is_category_expected
        return self._is_category_expected(category, disclosure_list)

    def _check_disclosure_quality(self, clause_metadata: Dict[str, Any]) -> bool:
        """
        Check if the clause has clear disclosure.

        Evaluates:
        1. Clear language (not buried in legal jargon)
        2. Prominent placement (early in document)
        3. Specific details (not vague statements)

        Args:
            clause_metadata: Metadata about the clause including:
                - text: The clause text
                - position: Position in document (0-1, where 0 is start)
                - readability_score: Flesch-Kincaid or similar
                - has_specific_details: Whether it includes specific info

        Returns:
            True if disclosure is clear, False otherwise
        """
        try:
            clause_text = clause_metadata.get('text', '')
            position = clause_metadata.get('position', 1.0)  # Default to end
            readability_score = clause_metadata.get('readability_score')
            has_specific_details = clause_metadata.get('has_specific_details')

            # Track disclosure quality factors
            quality_checks = []

            # Check 1: Clear language (readability)
            if readability_score is not None:
                # Flesch-Kincaid: 60+ is considered readable
                # Higher is better (simpler language)
                is_readable = readability_score >= 60
                quality_checks.append(is_readable)
            else:
                # Fallback: check for excessive legal jargon
                is_readable = self._has_clear_language(clause_text)
                quality_checks.append(is_readable)

            # Check 2: Prominent placement
            # Consider prominent if in first 30% of document
            is_prominent = position <= 0.30
            quality_checks.append(is_prominent)

            # Check 3: Specific details
            if has_specific_details is not None:
                quality_checks.append(has_specific_details)
            else:
                # Fallback: check if text has specific information
                has_details = self._has_specific_details(clause_text)
                quality_checks.append(has_details)

            # Disclosure is clear if at least 2 out of 3 checks pass
            passes = sum(quality_checks)
            is_clear = passes >= 2

            logger.debug(
                f"Disclosure quality check: readable={quality_checks[0]}, "
                f"prominent={quality_checks[1]}, detailed={quality_checks[2]}, "
                f"overall={'CLEAR' if is_clear else 'UNCLEAR'}"
            )

            return is_clear

        except Exception as e:
            logger.error(f"Error checking disclosure quality: {str(e)}", exc_info=True)
            # If we can't determine, assume unclear (safer)
            return False

    def _has_clear_language(self, text: str) -> bool:
        """
        Check if text uses clear, plain language.

        Returns False if text is buried in legal jargon.
        """
        # List of legal jargon indicators
        jargon_patterns = [
            r'\bhereby\b',
            r'\bwhereas\b',
            r'\bhereinafter\b',
            r'\baforesaid\b',
            r'\bnotwithstanding\b',
            r'\bpursuant to\b',
            r'\bin the event that\b',
            r'\bprovided that\b',
            r'\bto the extent that\b'
        ]

        # Count jargon occurrences
        jargon_count = 0
        text_lower = text.lower()

        for pattern in jargon_patterns:
            matches = re.findall(pattern, text_lower)
            jargon_count += len(matches)

        # If more than 2 jargon terms per 100 words, consider unclear
        word_count = len(text.split())
        jargon_density = (jargon_count / max(word_count, 1)) * 100

        is_clear = jargon_density < 2.0

        return is_clear

    def _has_specific_details(self, text: str) -> bool:
        """
        Check if text includes specific details rather than vague statements.

        Looks for:
        - Specific numbers/amounts
        - Specific dates/timeframes
        - Specific procedures/steps
        """
        # Indicators of specific details
        has_numbers = bool(re.search(r'\b\d+\b', text))
        has_percentage = bool(re.search(r'\d+%', text))
        has_dollar_amount = bool(re.search(r'\$\d+', text))
        has_timeframe = bool(re.search(
            r'\b\d+\s*(day|days|week|weeks|month|months|year|years|hour|hours)\b',
            text,
            re.IGNORECASE
        ))
        has_date = bool(re.search(
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            text,
            re.IGNORECASE
        ))

        # Vague language indicators (negative signals)
        vague_patterns = [
            r'\bmay\b',
            r'\bmight\b',
            r'\bcould\b',
            r'\breasonable\b',
            r'\bappropriate\b',
            r'\bat our discretion\b',
            r'\bfrom time to time\b',
            r'\bas needed\b',
            r'\bas necessary\b'
        ]

        vague_count = 0
        text_lower = text.lower()

        for pattern in vague_patterns:
            if re.search(pattern, text_lower):
                vague_count += 1

        # Has specific details if:
        # - At least one specific indicator (numbers, dates, etc.) AND
        # - Not too much vague language (< 3 vague terms)
        has_specific_indicators = (
            has_numbers or has_percentage or has_dollar_amount or
            has_timeframe or has_date
        )
        not_too_vague = vague_count < 3

        return has_specific_indicators and not_too_vague

    def get_service_type_expectations(self, service_type: str) -> Dict[str, Any]:
        """
        Get the expectations for a given service type.

        Args:
            service_type: Type of service

        Returns:
            Dict with expected, alarming, and requires_disclosure lists
        """
        if service_type not in self.SERVICE_TYPE_CONTEXTS:
            logger.warning(f"Unknown service type: {service_type}")
            return {
                'service_type': service_type,
                'expected': [],
                'alarming': [],
                'requires_disclosure': [],
                'error': 'Unknown service type'
            }

        context = self.SERVICE_TYPE_CONTEXTS[service_type]

        return {
            'service_type': service_type,
            'expected': context['expected'].copy(),
            'alarming': context['alarming'].copy(),
            'requires_disclosure': context['requires_disclosure'].copy()
        }

    def explain_service_context(
        self,
        service_type: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Explain why a category is expected, alarming, or neutral for a service type.

        Args:
            service_type: Type of service
            category: Category to explain

        Returns:
            Dict with explanation and classification
        """
        if service_type not in self.SERVICE_TYPE_CONTEXTS:
            return {
                'service_type': service_type,
                'category': category,
                'classification': 'unknown',
                'explanation': f'Unknown service type: {service_type}'
            }

        context = self.SERVICE_TYPE_CONTEXTS[service_type]

        is_expected = self._is_category_expected(category, context['expected'])
        is_alarming = self._is_category_alarming(category, context['alarming'])
        requires_disclosure = self._requires_disclosure(category, context['requires_disclosure'])

        if is_alarming:
            classification = 'alarming'
            explanation = (
                f'Category "{category}" is alarming for {service_type} services. '
                f'This practice is concerning and should be flagged for review.'
            )
        elif is_expected:
            classification = 'expected'
            if requires_disclosure:
                explanation = (
                    f'Category "{category}" is expected for {service_type} services, '
                    f'but requires clear disclosure to users.'
                )
            else:
                explanation = (
                    f'Category "{category}" is expected for {service_type} services '
                    f'and is considered a standard practice.'
                )
        else:
            classification = 'neutral'
            explanation = (
                f'Category "{category}" is neither expected nor alarming for '
                f'{service_type} services. It should be reviewed on a case-by-case basis.'
            )

        return {
            'service_type': service_type,
            'category': category,
            'classification': classification,
            'is_expected': is_expected,
            'is_alarming': is_alarming,
            'requires_disclosure': requires_disclosure,
            'explanation': explanation
        }

    def get_all_service_types(self) -> List[str]:
        """Get list of all supported service types."""
        return list(self.SERVICE_TYPE_CONTEXTS.keys())

    def validate_service_type(self, service_type: str) -> bool:
        """Check if a service type is valid."""
        return service_type in self.SERVICE_TYPE_CONTEXTS
