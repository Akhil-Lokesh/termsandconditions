"""
Tests for TemporalContextFilter.

Tests the Stage 2 temporal context filtering functionality.
"""

import pytest
from datetime import datetime, timedelta
from app.core.temporal_context_filter import TemporalContextFilter


class TestTemporalContextFilter:
    """Test suite for TemporalContextFilter."""

    @pytest.fixture
    def filter(self):
        """Create a filter instance."""
        return TemporalContextFilter()

    @pytest.fixture
    def current_date(self):
        """Get current date for testing."""
        return datetime.now()

    def test_initialization(self, filter):
        """Test filter initialization."""
        assert filter is not None
        assert len(filter.TEMPORAL_DECAY_TIERS) == 4
        assert filter.VERY_OLD_THRESHOLD_DAYS == 365 * 5

    def test_decay_tiers_structure(self, filter):
        """Test that decay tiers have correct structure."""
        required_keys = ['days_min', 'days_max', 'modifier', 'label']

        for tier in filter.TEMPORAL_DECAY_TIERS:
            for key in required_keys:
                assert key in tier, f"Tier missing key: {key}"

    def test_decay_tier_modifiers(self, filter):
        """Test that decay tier modifiers are correct."""
        tiers = filter.TEMPORAL_DECAY_TIERS

        # Tier 1: 0-30 days = 3.0x
        assert tiers[0]['days_min'] == 0
        assert tiers[0]['days_max'] == 30
        assert tiers[0]['modifier'] == 3.0

        # Tier 2: 31-60 days = 2.0x
        assert tiers[1]['days_min'] == 31
        assert tiers[1]['days_max'] == 60
        assert tiers[1]['modifier'] == 2.0

        # Tier 3: 61-90 days = 1.5x
        assert tiers[2]['days_min'] == 61
        assert tiers[2]['days_max'] == 90
        assert tiers[2]['modifier'] == 1.5

        # Tier 4: 91+ days = 1.0x
        assert tiers[3]['days_min'] == 91
        assert tiers[3]['days_max'] is None
        assert tiers[3]['modifier'] == 1.0

    def test_recent_change_0_days(self, filter, current_date):
        """Test temporal adjustment for change made today (0 days)."""
        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=current_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 3.0
        assert result['adjusted_score'] == 15.0  # 5.0 * 3.0
        assert result['days_since_change'] == 0
        assert result['is_very_old'] == False
        assert 'heightened scrutiny' in result['reason'].lower()

    def test_recent_change_15_days(self, filter, current_date):
        """Test temporal adjustment for change made 15 days ago."""
        change_date = current_date - timedelta(days=15)

        result = filter.apply_temporal_adjustment(
            risk_score=6.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 3.0
        assert result['adjusted_score'] == 18.0  # 6.0 * 3.0
        assert result['days_since_change'] == 15
        assert 'heightened scrutiny' in result['reason'].lower()

    def test_recent_change_30_days(self, filter, current_date):
        """Test temporal adjustment for change made 30 days ago (boundary)."""
        change_date = current_date - timedelta(days=30)

        result = filter.apply_temporal_adjustment(
            risk_score=4.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 3.0
        assert result['adjusted_score'] == 12.0  # 4.0 * 3.0
        assert result['days_since_change'] == 30

    def test_recent_change_31_days(self, filter, current_date):
        """Test temporal adjustment for change made 31 days ago (tier 2)."""
        change_date = current_date - timedelta(days=31)

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 2.0
        assert result['adjusted_score'] == 10.0  # 5.0 * 2.0
        assert result['days_since_change'] == 31
        assert 'elevated scrutiny' in result['reason'].lower()

    def test_recent_change_45_days(self, filter, current_date):
        """Test temporal adjustment for change made 45 days ago."""
        change_date = current_date - timedelta(days=45)

        result = filter.apply_temporal_adjustment(
            risk_score=6.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 2.0
        assert result['adjusted_score'] == 12.0  # 6.0 * 2.0
        assert result['days_since_change'] == 45

    def test_recent_change_60_days(self, filter, current_date):
        """Test temporal adjustment for change made 60 days ago (boundary)."""
        change_date = current_date - timedelta(days=60)

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 2.0
        assert result['adjusted_score'] == 10.0
        assert result['days_since_change'] == 60

    def test_recent_change_61_days(self, filter, current_date):
        """Test temporal adjustment for change made 61 days ago (tier 3)."""
        change_date = current_date - timedelta(days=61)

        result = filter.apply_temporal_adjustment(
            risk_score=4.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.5
        assert result['adjusted_score'] == 6.0  # 4.0 * 1.5
        assert result['days_since_change'] == 61
        assert 'increased scrutiny' in result['reason'].lower()

    def test_recent_change_75_days(self, filter, current_date):
        """Test temporal adjustment for change made 75 days ago."""
        change_date = current_date - timedelta(days=75)

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.5
        assert result['adjusted_score'] == 7.5  # 5.0 * 1.5
        assert result['days_since_change'] == 75

    def test_recent_change_90_days(self, filter, current_date):
        """Test temporal adjustment for change made 90 days ago (boundary)."""
        change_date = current_date - timedelta(days=90)

        result = filter.apply_temporal_adjustment(
            risk_score=6.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.5
        assert result['adjusted_score'] == 9.0
        assert result['days_since_change'] == 90

    def test_change_91_days(self, filter, current_date):
        """Test temporal adjustment for change made 91 days ago (tier 4)."""
        change_date = current_date - timedelta(days=91)

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.0
        assert result['adjusted_score'] == 5.0  # 5.0 * 1.0
        assert result['days_since_change'] == 91
        assert 'standard scrutiny' in result['reason'].lower()

    def test_change_120_days(self, filter, current_date):
        """Test temporal adjustment for change made 120 days ago."""
        change_date = current_date - timedelta(days=120)

        result = filter.apply_temporal_adjustment(
            risk_score=7.0,
            last_modified=change_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.0
        assert result['adjusted_score'] == 7.0
        assert result['days_since_change'] == 120

    def test_no_change_existing_policy(self, filter, current_date):
        """Test temporal adjustment for existing policy (no change)."""
        effective_date = current_date - timedelta(days=45)

        result = filter.apply_temporal_adjustment(
            risk_score=6.0,
            effective_date=effective_date,
            is_change=False
        )

        assert result['temporal_modifier'] == 1.0
        assert result['adjusted_score'] == 6.0  # No adjustment
        assert result['days_since_change'] == 45
        assert 'existing policy' in result['reason'].lower()
        assert 'standard scrutiny' in result['scrutiny_level'].lower()

    def test_missing_dates(self, filter):
        """Test handling of missing dates."""
        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.0
        assert result['adjusted_score'] == 5.0
        assert result['days_since_change'] == 0
        assert result['warnings'] is not None
        assert any('no date' in w.lower() for w in result['warnings'])

    def test_future_date(self, filter, current_date):
        """Test handling of future dates."""
        future_date = current_date + timedelta(days=30)

        result = filter.apply_temporal_adjustment(
            risk_score=6.0,
            last_modified=future_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.0
        assert result['adjusted_score'] == 6.0
        assert 'future date' in result['reason'].lower()
        assert result['warnings'] is not None

    def test_very_old_policy_change(self, filter, current_date):
        """Test very old policy (>5 years) that was changed."""
        # 6 years ago
        old_date = current_date - timedelta(days=365 * 6)

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=old_date,
            is_change=True
        )

        assert result['temporal_modifier'] == 1.0  # Old enough for standard scrutiny
        assert result['is_very_old'] == True
        assert 'outdated' in result['reason'].lower() or 'years old' in result['reason'].lower()

    def test_very_old_policy_no_change(self, filter, current_date):
        """Test very old policy (>5 years) with no change."""
        # 7 years ago
        old_date = current_date - timedelta(days=365 * 7)

        result = filter.apply_temporal_adjustment(
            risk_score=4.0,
            effective_date=old_date,
            is_change=False
        )

        assert result['temporal_modifier'] == 1.0
        assert result['is_very_old'] == True
        assert 'years old' in result['reason'].lower()

    def test_prefer_last_modified_over_effective_date(self, filter, current_date):
        """Test that last_modified is preferred over effective_date."""
        effective_date = current_date - timedelta(days=100)
        last_modified = current_date - timedelta(days=20)  # More recent

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            effective_date=effective_date,
            last_modified=last_modified,
            is_change=True
        )

        # Should use last_modified (20 days) not effective_date (100 days)
        assert result['days_since_change'] == 20
        assert result['temporal_modifier'] == 3.0  # 0-30 days tier

    def test_get_temporal_modifier(self, filter):
        """Test getting temporal modifier directly."""
        # 15 days = 3.0x
        modifier, label = filter._get_temporal_modifier(15)
        assert modifier == 3.0
        assert 'heightened' in label.lower()

        # 45 days = 2.0x
        modifier, label = filter._get_temporal_modifier(45)
        assert modifier == 2.0
        assert 'elevated' in label.lower()

        # 75 days = 1.5x
        modifier, label = filter._get_temporal_modifier(75)
        assert modifier == 1.5
        assert 'increased' in label.lower()

        # 120 days = 1.0x
        modifier, label = filter._get_temporal_modifier(120)
        assert modifier == 1.0
        assert 'standard' in label.lower()

    def test_build_reason_today(self, filter, current_date):
        """Test reason building for change made today."""
        reason = filter._build_reason(
            days_since_change=0,
            modifier=3.0,
            scrutiny_label='Recent change, heightened scrutiny',
            is_very_old=False,
            reference_date=current_date
        )

        assert 'today' in reason.lower()
        assert '3.0x' in reason or '3x' in reason.lower()
        assert 'heightened scrutiny' in reason.lower()

    def test_build_reason_yesterday(self, filter, current_date):
        """Test reason building for change made yesterday."""
        yesterday = current_date - timedelta(days=1)

        reason = filter._build_reason(
            days_since_change=1,
            modifier=3.0,
            scrutiny_label='Recent change, heightened scrutiny',
            is_very_old=False,
            reference_date=yesterday
        )

        assert 'yesterday' in reason.lower()

    def test_build_reason_days(self, filter, current_date):
        """Test reason building for change made a few days ago."""
        change_date = current_date - timedelta(days=5)

        reason = filter._build_reason(
            days_since_change=5,
            modifier=3.0,
            scrutiny_label='Recent change, heightened scrutiny',
            is_very_old=False,
            reference_date=change_date
        )

        assert '5 days ago' in reason.lower()

    def test_build_reason_weeks(self, filter, current_date):
        """Test reason building for change made weeks ago."""
        change_date = current_date - timedelta(days=14)

        reason = filter._build_reason(
            days_since_change=14,
            modifier=3.0,
            scrutiny_label='Recent change, heightened scrutiny',
            is_very_old=False,
            reference_date=change_date
        )

        assert 'week' in reason.lower()

    def test_build_reason_months(self, filter, current_date):
        """Test reason building for change made months ago."""
        change_date = current_date - timedelta(days=60)

        reason = filter._build_reason(
            days_since_change=60,
            modifier=2.0,
            scrutiny_label='Recent change, elevated scrutiny',
            is_very_old=False,
            reference_date=change_date
        )

        assert 'month' in reason.lower()

    def test_build_reason_years(self, filter, current_date):
        """Test reason building for change made years ago."""
        change_date = current_date - timedelta(days=730)  # 2 years

        reason = filter._build_reason(
            days_since_change=730,
            modifier=1.0,
            scrutiny_label='Standard scrutiny',
            is_very_old=False,
            reference_date=change_date
        )

        assert 'year' in reason.lower()

    def test_build_reason_very_old(self, filter, current_date):
        """Test reason building for very old policy."""
        old_date = current_date - timedelta(days=365 * 6)

        reason = filter._build_reason(
            days_since_change=365 * 6,
            modifier=1.0,
            scrutiny_label='Standard scrutiny',
            is_very_old=True,
            reference_date=old_date
        )

        assert 'outdated' in reason.lower() or 'years old' in reason.lower()

    def test_get_decay_tier_info(self, filter):
        """Test getting decay tier information."""
        # 20 days
        info = filter.get_decay_tier_info(20)
        assert info['days_since_change'] == 20
        assert info['modifier'] == 3.0
        assert '0-30' in info['tier_range']

        # 50 days
        info = filter.get_decay_tier_info(50)
        assert info['days_since_change'] == 50
        assert info['modifier'] == 2.0
        assert '31-60' in info['tier_range']

        # 80 days
        info = filter.get_decay_tier_info(80)
        assert info['days_since_change'] == 80
        assert info['modifier'] == 1.5
        assert '61-90' in info['tier_range']

        # 150 days
        info = filter.get_decay_tier_info(150)
        assert info['days_since_change'] == 150
        assert info['modifier'] == 1.0
        assert '91+' in info['tier_range']

    def test_get_all_decay_tiers(self, filter):
        """Test getting all decay tier information."""
        tiers = filter.get_all_decay_tiers()

        assert len(tiers) == 4
        assert tiers[0]['modifier'] == 3.0
        assert tiers[1]['modifier'] == 2.0
        assert tiers[2]['modifier'] == 1.5
        assert tiers[3]['modifier'] == 1.0

    def test_is_policy_very_old(self, filter, current_date):
        """Test checking if policy is very old."""
        # 3 years old - not very old
        not_very_old = current_date - timedelta(days=365 * 3)
        assert filter.is_policy_very_old(not_very_old) == False

        # 6 years old - very old
        very_old = current_date - timedelta(days=365 * 6)
        assert filter.is_policy_very_old(very_old) == True

        # None - not very old
        assert filter.is_policy_very_old(None) == False

    def test_calculate_expected_decay(self, filter):
        """Test calculating expected decay over time."""
        initial_score = 8.0
        days_progression = [0, 15, 30, 45, 60, 75, 90, 120, 180]

        decay = filter.calculate_expected_decay(initial_score, days_progression)

        assert len(decay) == len(days_progression)

        # Check specific points
        assert decay[0]['adjusted_score'] == 24.0  # 8.0 * 3.0 (day 0)
        assert decay[3]['adjusted_score'] == 16.0  # 8.0 * 2.0 (day 45)
        assert decay[6]['adjusted_score'] == 12.0  # 8.0 * 1.5 (day 90)
        assert decay[7]['adjusted_score'] == 8.0   # 8.0 * 1.0 (day 120)

    def test_suggest_review_priority_critical(self, filter):
        """Test review priority suggestion for critical case."""
        # Recent change (high modifier) + high base score = critical
        result = filter.suggest_review_priority(
            days_since_change=10,
            base_risk_score=8.0
        )

        assert result['priority'] == 'CRITICAL'
        assert result['adjusted_score'] == 24.0  # 8.0 * 3.0
        assert 'immediate review' in result['reason'].lower()

    def test_suggest_review_priority_high(self, filter):
        """Test review priority suggestion for high case."""
        # Recent change + medium-high score = high
        result = filter.suggest_review_priority(
            days_since_change=40,
            base_risk_score=6.0
        )

        assert result['priority'] == 'HIGH'
        assert result['adjusted_score'] == 12.0  # 6.0 * 2.0

    def test_suggest_review_priority_medium(self, filter):
        """Test review priority suggestion for medium case."""
        result = filter.suggest_review_priority(
            days_since_change=70,
            base_risk_score=5.0
        )

        assert result['priority'] == 'MEDIUM'
        assert result['adjusted_score'] == 7.5  # 5.0 * 1.5

    def test_suggest_review_priority_low(self, filter):
        """Test review priority suggestion for low case."""
        result = filter.suggest_review_priority(
            days_since_change=100,
            base_risk_score=3.0
        )

        assert result['priority'] == 'LOW'
        assert result['adjusted_score'] == 3.0  # 3.0 * 1.0

    def test_error_handling(self, filter):
        """Test error handling in apply_temporal_adjustment."""
        # Pass invalid risk_score (should still work)
        result = filter.apply_temporal_adjustment(
            risk_score=None,  # Invalid
            is_change=True
        )

        # Should handle error gracefully or process with defaults
        assert 'error' in result or result['temporal_modifier'] >= 0

    def test_boundary_conditions(self, filter, current_date):
        """Test boundary conditions between tiers."""
        test_cases = [
            (30, 3.0),   # End of tier 1
            (31, 2.0),   # Start of tier 2
            (60, 2.0),   # End of tier 2
            (61, 1.5),   # Start of tier 3
            (90, 1.5),   # End of tier 3
            (91, 1.0),   # Start of tier 4
        ]

        for days, expected_modifier in test_cases:
            change_date = current_date - timedelta(days=days)
            result = filter.apply_temporal_adjustment(
                risk_score=5.0,
                last_modified=change_date,
                is_change=True
            )
            assert result['temporal_modifier'] == expected_modifier, \
                f"Failed for {days} days: expected {expected_modifier}, got {result['temporal_modifier']}"

    def test_all_tiers_covered(self, filter):
        """Test that all day ranges map to a tier."""
        # Test various day values
        test_days = [0, 1, 15, 30, 31, 45, 60, 61, 75, 90, 91, 100, 180, 365, 1000]

        for days in test_days:
            modifier, label = filter._get_temporal_modifier(days)
            assert modifier in [1.0, 1.5, 2.0, 3.0], f"Invalid modifier for {days} days: {modifier}"
            assert label is not None and len(label) > 0

    def test_adjusted_score_calculation(self, filter, current_date):
        """Test that adjusted score is correctly calculated."""
        test_cases = [
            (5.0, 10, 15.0),   # 5.0 * 3.0
            (4.0, 40, 8.0),    # 4.0 * 2.0
            (6.0, 70, 9.0),    # 6.0 * 1.5
            (7.0, 100, 7.0),   # 7.0 * 1.0
        ]

        for base_score, days, expected_adjusted in test_cases:
            change_date = current_date - timedelta(days=days)
            result = filter.apply_temporal_adjustment(
                risk_score=base_score,
                last_modified=change_date,
                is_change=True
            )
            assert result['adjusted_score'] == expected_adjusted

    def test_reason_includes_date(self, filter, current_date):
        """Test that reason includes the reference date."""
        change_date = current_date - timedelta(days=30)

        result = filter.apply_temporal_adjustment(
            risk_score=5.0,
            last_modified=change_date,
            is_change=True
        )

        # Should include date in YYYY-MM-DD format
        assert change_date.strftime('%Y-%m-%d') in result['reason']
