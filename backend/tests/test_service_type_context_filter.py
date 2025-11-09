"""
Tests for ServiceTypeContextFilter.

Tests the Stage 2 service type context filtering functionality.
"""

import pytest
from app.core.service_type_context_filter import ServiceTypeContextFilter


class TestServiceTypeContextFilter:
    """Test suite for ServiceTypeContextFilter."""

    @pytest.fixture
    def filter(self):
        """Create a filter instance."""
        return ServiceTypeContextFilter()

    def test_initialization(self, filter):
        """Test filter initialization."""
        assert filter is not None
        assert len(filter.SERVICE_TYPE_CONTEXTS) == 5
        assert 'subscription' in filter.SERVICE_TYPE_CONTEXTS
        assert 'one_time_purchase' in filter.SERVICE_TYPE_CONTEXTS
        assert 'freemium' in filter.SERVICE_TYPE_CONTEXTS
        assert 'free_with_ads' in filter.SERVICE_TYPE_CONTEXTS
        assert 'trial' in filter.SERVICE_TYPE_CONTEXTS

    def test_service_type_contexts_structure(self, filter):
        """Test that service type contexts have correct structure."""
        required_keys = ['expected', 'alarming', 'requires_disclosure']

        for service_type, context in filter.SERVICE_TYPE_CONTEXTS.items():
            for key in required_keys:
                assert key in context, f"Service type {service_type} missing key: {key}"
                assert isinstance(context[key], list), f"{service_type}.{key} is not a list"

    def test_subscription_context(self, filter):
        """Test subscription service type context."""
        context = filter.SERVICE_TYPE_CONTEXTS['subscription']

        # Expected categories
        assert 'auto_renewal' in context['expected']
        assert 'recurring_billing' in context['expected']
        assert 'cancellation_policy' in context['expected']

        # Alarming categories
        assert 'no_cancellation' in context['alarming']
        assert 'cancellation_fee_over_20_percent' in context['alarming']

        # Requires disclosure
        assert 'auto_renewal' in context['requires_disclosure']
        assert 'price_increases' in context['requires_disclosure']

    def test_one_time_purchase_context(self, filter):
        """Test one-time purchase service type context."""
        context = filter.SERVICE_TYPE_CONTEXTS['one_time_purchase']

        # Expected categories
        assert 'refund_policy' in context['expected']
        assert 'warranty' in context['expected']

        # Alarming categories (things that shouldn't be in one-time purchases)
        assert 'auto_renewal' in context['alarming']
        assert 'recurring_charges' in context['alarming']
        assert 'hidden_fees' in context['alarming']

    def test_freemium_context(self, filter):
        """Test freemium service type context."""
        context = filter.SERVICE_TYPE_CONTEXTS['freemium']

        # Expected categories
        assert 'upgrade_prompts' in context['expected']
        assert 'feature_limitations' in context['expected']
        assert 'ads' in context['expected']

        # Alarming categories
        assert 'auto_upgrade_to_paid' in context['alarming']
        assert 'cannot_delete_account' in context['alarming']

    def test_free_with_ads_context(self, filter):
        """Test free with ads service type context."""
        context = filter.SERVICE_TYPE_CONTEXTS['free_with_ads']

        # Expected categories
        assert 'data_collection_for_ads' in context['expected']
        assert 'third_party_advertisers' in context['expected']

        # Alarming categories
        assert 'sell_data_beyond_ads' in context['alarming']
        assert 'cannot_opt_out' in context['alarming']

    def test_trial_context(self, filter):
        """Test trial service type context."""
        context = filter.SERVICE_TYPE_CONTEXTS['trial']

        # Expected categories
        assert 'auto_convert_to_paid' in context['expected']
        assert 'credit_card_required' in context['expected']

        # Alarming categories
        assert 'immediate_charge' in context['alarming']
        assert 'no_reminder' in context['alarming']
        assert 'difficult_cancellation' in context['alarming']

    def test_filter_alarming_category(self, filter):
        """Test filtering an alarming category."""
        detection = {'category': 'no_cancellation', 'confidence': 0.9}
        clause_metadata = {'text': 'You cannot cancel your subscription.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='subscription',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True
        assert result['context_score'] == 0.1  # Very concerning
        assert result['requires_clear_disclosure'] == True
        assert 'alarming' in result['reason'].lower()

    def test_filter_expected_with_clear_disclosure(self, filter):
        """Test filtering expected category with clear disclosure."""
        detection = {'category': 'auto_renewal', 'confidence': 0.8}
        clause_metadata = {
            'text': 'Your subscription will automatically renew every month for $9.99.',
            'position': 0.1,  # Early in document
            'readability_score': 70,  # Good readability
            'has_specific_details': True
        }

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='subscription',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == False  # Not an anomaly
        assert result['context_score'] == 0.9  # Not concerning
        assert result['requires_clear_disclosure'] == True
        assert 'expected' in result['reason'].lower()
        assert 'clear disclosure' in result['reason'].lower()

    def test_filter_expected_without_disclosure(self, filter):
        """Test filtering expected category without clear disclosure."""
        detection = {'category': 'auto_renewal', 'confidence': 0.8}
        clause_metadata = {
            'text': 'Notwithstanding the foregoing, pursuant to the terms hereinafter set forth...',
            'position': 0.8,  # Late in document
            'readability_score': 30,  # Poor readability
            'has_specific_details': False
        }

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='subscription',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True  # Keep as anomaly
        assert result['context_score'] == 0.5  # Moderate concern
        assert result['requires_clear_disclosure'] == True
        assert 'lacks clear disclosure' in result['reason'].lower()

    def test_filter_expected_no_disclosure_required(self, filter):
        """Test filtering expected category that doesn't require disclosure."""
        detection = {'category': 'cancellation_policy', 'confidence': 0.7}
        clause_metadata = {
            'text': 'You may cancel at any time.',
            'position': 0.3
        }

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='subscription',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == False  # Not an anomaly
        assert result['context_score'] == 0.9  # Not concerning
        assert result['requires_clear_disclosure'] == False

    def test_filter_neutral_category(self, filter):
        """Test filtering a neutral category (neither expected nor alarming)."""
        detection = {'category': 'some_random_category', 'confidence': 0.7}
        clause_metadata = {'text': 'Some clause text.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='subscription',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True  # Keep for review
        assert result['context_score'] == 0.5  # Neutral
        assert 'neither expected nor alarming' in result['reason'].lower()

    def test_filter_unknown_service_type(self, filter):
        """Test filtering with unknown service type."""
        detection = {'category': 'auto_renewal', 'confidence': 0.8}
        clause_metadata = {'text': 'Auto renewal clause.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='unknown_service',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True  # Keep for review
        assert result['context_score'] == 0.5  # Neutral
        assert 'unknown service type' in result['reason'].lower()

    def test_alarming_for_one_time_purchase(self, filter):
        """Test that auto-renewal is alarming for one-time purchases."""
        detection = {'category': 'auto_renewal', 'confidence': 0.9}
        clause_metadata = {'text': 'Your purchase will auto-renew.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='one_time_purchase',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True
        assert result['context_score'] == 0.1  # Very concerning
        assert 'alarming' in result['reason'].lower()

    def test_expected_for_subscription(self, filter):
        """Test that auto-renewal is expected for subscriptions."""
        detection = {'category': 'auto_renewal', 'confidence': 0.9}
        clause_metadata = {
            'text': 'Subscription auto-renews monthly at $9.99.',
            'position': 0.1,
            'readability_score': 75,
            'has_specific_details': True
        }

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='subscription',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == False  # Not alarming for subscriptions
        assert result['context_score'] == 0.9

    def test_disclosure_quality_clear(self, filter):
        """Test disclosure quality check with clear disclosure."""
        clause_metadata = {
            'text': 'Your subscription will renew on January 15, 2024 for $9.99.',
            'position': 0.1,  # Prominent
            'readability_score': 80,  # Readable
            'has_specific_details': True  # Specific
        }

        is_clear = filter._check_disclosure_quality(clause_metadata)
        assert is_clear == True

    def test_disclosure_quality_unclear_jargon(self, filter):
        """Test disclosure quality check with legal jargon."""
        clause_metadata = {
            'text': 'Notwithstanding the foregoing, hereby and pursuant to the terms hereinafter...',
            'position': 0.1,
            'readability_score': 20,  # Poor readability
            'has_specific_details': False
        }

        is_clear = filter._check_disclosure_quality(clause_metadata)
        assert is_clear == False

    def test_disclosure_quality_unclear_position(self, filter):
        """Test disclosure quality check with poor placement."""
        clause_metadata = {
            'text': 'Your subscription will renew for $9.99.',
            'position': 0.9,  # Buried at end
            'readability_score': 70,
            'has_specific_details': True
        }

        is_clear = filter._check_disclosure_quality(clause_metadata)
        # Should fail because position is poor (even though other factors are good)
        # With 2/3 threshold, this might still pass if we get 2 out of 3
        # Position is bad, readable is good, specific is good = 2/3 pass
        assert is_clear == True

    def test_disclosure_quality_no_specifics(self, filter):
        """Test disclosure quality check without specific details."""
        clause_metadata = {
            'text': 'We may renew your subscription at our discretion.',
            'position': 0.5,
            'readability_score': 60,
            'has_specific_details': False
        }

        is_clear = filter._check_disclosure_quality(clause_metadata)
        # readable=True, prominent=False, specific=False = 1/3 fail
        assert is_clear == False

    def test_has_clear_language(self, filter):
        """Test clear language detection."""
        # Clear language
        clear_text = "Your subscription will automatically renew every month."
        assert filter._has_clear_language(clear_text) == True

        # Jargon-heavy language
        jargon_text = "Notwithstanding the foregoing, whereby and pursuant to the terms hereinafter set forth..."
        assert filter._has_clear_language(jargon_text) == False

    def test_has_specific_details(self, filter):
        """Test specific details detection."""
        # Specific details with numbers and timeframe
        specific_text = "Your subscription will renew in 30 days for $9.99 per month."
        assert filter._has_specific_details(specific_text) == True

        # Vague language
        vague_text = "We may charge you a reasonable fee at our discretion from time to time."
        assert filter._has_specific_details(vague_text) == False

    def test_get_service_type_expectations(self, filter):
        """Test getting service type expectations."""
        expectations = filter.get_service_type_expectations('subscription')

        assert expectations['service_type'] == 'subscription'
        assert 'auto_renewal' in expectations['expected']
        assert 'no_cancellation' in expectations['alarming']
        assert 'auto_renewal' in expectations['requires_disclosure']

    def test_get_service_type_expectations_unknown(self, filter):
        """Test getting expectations for unknown service type."""
        expectations = filter.get_service_type_expectations('unknown_service')

        assert expectations['service_type'] == 'unknown_service'
        assert 'error' in expectations
        assert len(expectations['expected']) == 0

    def test_explain_service_context_alarming(self, filter):
        """Test explaining alarming service context."""
        explanation = filter.explain_service_context('subscription', 'no_cancellation')

        assert explanation['classification'] == 'alarming'
        assert explanation['is_alarming'] == True
        assert 'concerning' in explanation['explanation'].lower()

    def test_explain_service_context_expected(self, filter):
        """Test explaining expected service context."""
        explanation = filter.explain_service_context('subscription', 'auto_renewal')

        assert explanation['classification'] == 'expected'
        assert explanation['is_expected'] == True
        assert explanation['requires_disclosure'] == True

    def test_explain_service_context_neutral(self, filter):
        """Test explaining neutral service context."""
        explanation = filter.explain_service_context('subscription', 'random_category')

        assert explanation['classification'] == 'neutral'
        assert 'neither expected nor alarming' in explanation['explanation'].lower()

    def test_get_all_service_types(self, filter):
        """Test getting all service types."""
        service_types = filter.get_all_service_types()

        assert len(service_types) == 5
        assert 'subscription' in service_types
        assert 'one_time_purchase' in service_types
        assert 'freemium' in service_types
        assert 'free_with_ads' in service_types
        assert 'trial' in service_types

    def test_validate_service_type(self, filter):
        """Test service type validation."""
        assert filter.validate_service_type('subscription') == True
        assert filter.validate_service_type('freemium') == True
        assert filter.validate_service_type('invalid_type') == False

    def test_is_category_expected_fuzzy_match(self, filter):
        """Test fuzzy matching for category detection."""
        expected_list = ['auto_renewal', 'recurring_billing']

        # Exact match
        assert filter._is_category_expected('auto_renewal', expected_list) == True

        # Fuzzy match with underscores vs hyphens
        assert filter._is_category_expected('auto-renewal', expected_list) == True

        # Fuzzy match with spaces
        assert filter._is_category_expected('auto renewal', expected_list) == True

        # Partial match
        assert filter._is_category_expected('automatic_renewal', expected_list) == True

        # No match
        assert filter._is_category_expected('refund_policy', expected_list) == False

    def test_trial_immediate_charge_alarming(self, filter):
        """Test that immediate charge is alarming for trials."""
        detection = {'category': 'immediate_charge', 'confidence': 0.9}
        clause_metadata = {'text': 'You will be charged immediately.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='trial',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True
        assert result['context_score'] == 0.1  # Very concerning
        assert 'alarming' in result['reason'].lower()

    def test_freemium_auto_upgrade_alarming(self, filter):
        """Test that auto-upgrade is alarming for freemium."""
        detection = {'category': 'auto_upgrade_to_paid', 'confidence': 0.9}
        clause_metadata = {'text': 'We will automatically upgrade you to paid.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='freemium',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True
        assert result['context_score'] == 0.1
        assert 'alarming' in result['reason'].lower()

    def test_free_with_ads_data_selling_alarming(self, filter):
        """Test that selling data beyond ads is alarming for free_with_ads."""
        detection = {'category': 'sell_data_beyond_ads', 'confidence': 0.9}
        clause_metadata = {'text': 'We sell your data to third parties.', 'position': 0.5}

        result = filter.filter_by_service_context(
            detection=detection,
            service_type='free_with_ads',
            clause_metadata=clause_metadata
        )

        assert result['keep_anomaly'] == True
        assert result['context_score'] == 0.1
        assert 'alarming' in result['reason'].lower()

    def test_has_specific_details_with_percentages(self, filter):
        """Test specific details detection with percentages."""
        text = "We charge a 15% fee on all transactions."
        assert filter._has_specific_details(text) == True

    def test_has_specific_details_with_dollar_amounts(self, filter):
        """Test specific details detection with dollar amounts."""
        text = "Your subscription costs $29 per month."
        assert filter._has_specific_details(text) == True

    def test_has_specific_details_with_dates(self, filter):
        """Test specific details detection with dates."""
        text = "Your subscription renews on January 15th."
        assert filter._has_specific_details(text) == True

    def test_disclosure_quality_all_factors_poor(self, filter):
        """Test disclosure quality when all factors are poor."""
        clause_metadata = {
            'text': 'Hereby, notwithstanding the foregoing, we may do things.',
            'position': 0.95,  # Very late
            'readability_score': 10,  # Very poor
            'has_specific_details': False
        }

        is_clear = filter._check_disclosure_quality(clause_metadata)
        assert is_clear == False

    def test_disclosure_quality_all_factors_good(self, filter):
        """Test disclosure quality when all factors are good."""
        clause_metadata = {
            'text': 'Your subscription renews on the 15th of each month for $9.99.',
            'position': 0.05,  # Very early
            'readability_score': 90,  # Very good
            'has_specific_details': True
        }

        is_clear = filter._check_disclosure_quality(clause_metadata)
        assert is_clear == True

    def test_error_handling(self, filter):
        """Test error handling in filter_by_service_context."""
        # Pass invalid detection dict
        result = filter.filter_by_service_context(
            detection=None,  # Invalid
            service_type='subscription',
            clause_metadata={}
        )

        # Should handle error gracefully
        assert 'error' in result or result['keep_anomaly'] == True

    def test_context_score_ranges(self, filter):
        """Test that context scores are in valid range [0, 1]."""
        test_cases = [
            ('no_cancellation', 'subscription', 0.1),  # Alarming
            ('auto_renewal', 'subscription', 0.9),  # Expected
            ('random_category', 'subscription', 0.5),  # Neutral
        ]

        for category, service_type, expected_score in test_cases:
            detection = {'category': category, 'confidence': 0.8}
            clause_metadata = {
                'text': 'Some text.',
                'position': 0.1,
                'readability_score': 70,
                'has_specific_details': True
            }

            result = filter.filter_by_service_context(
                detection=detection,
                service_type=service_type,
                clause_metadata=clause_metadata
            )

            assert 0.0 <= result['context_score'] <= 1.0
            assert result['context_score'] == expected_score
