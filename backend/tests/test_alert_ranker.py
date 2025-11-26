"""
Tests for AlertRanker.

Tests ranking, filtering, budget enforcement, scoring, and edge cases.
"""

import pytest
from app.core.alert_ranker import AlertRanker


class TestAlertRanker:
    """Test suite for AlertRanker."""

    @pytest.fixture
    def ranker(self):
        """Create a default alert ranker."""
        return AlertRanker()

    @pytest.fixture
    def sample_anomaly(self):
        """Create a sample anomaly for testing."""
        return {
            'clause_number': '1.1',
            'clause_text': 'Test clause',
            'severity': 'high',
            'risk_category': 'data_collection',
            'confidence_calibration': {
                'calibrated_confidence': 0.85,
                'confidence_tier': 'HIGH'
            },
            'detected_indicators': [
                {'name': 'data_selling', 'severity': 'high'}
            ]
        }

    def test_init_default(self):
        """Test initialization with defaults."""
        ranker = AlertRanker()

        assert ranker.MAX_ALERTS == 10
        assert ranker.TARGET_ALERTS == 5
        assert ranker.user_preferences == {}

    def test_init_with_preferences(self):
        """Test initialization with user preferences."""
        prefs = {
            'priority_categories': ['data_collection'],
            'concern_level': 'high'
        }
        ranker = AlertRanker(user_preferences=prefs)

        assert ranker.user_preferences == prefs

    def test_rank_and_filter_empty(self, ranker):
        """Test ranking with empty anomalies."""
        result = ranker.rank_and_filter([], None, None)

        assert result['total_detected'] == 0
        assert result['total_shown'] == 0
        assert result['high_severity'] == []
        assert result['medium_severity'] == []
        assert result['low_severity'] == []
        assert result['suppressed'] == []

    def test_rank_and_filter_single_anomaly(self, ranker, sample_anomaly):
        """Test ranking with single anomaly."""
        result = ranker.rank_and_filter([sample_anomaly])

        assert result['total_detected'] == 1
        assert result['total_shown'] == 1
        assert len(result['high_severity']) == 1
        assert result['high_severity'][0]['clause_number'] == '1.1'

    def test_rank_and_filter_within_budget(self, ranker):
        """Test ranking when all anomalies fit within budget."""
        anomalies = [
            {
                'clause_number': f'1.{i}',
                'severity': 'high',
                'confidence_calibration': {
                    'calibrated_confidence': 0.9,
                    'confidence_tier': 'HIGH'
                },
                'detected_indicators': []
            }
            for i in range(3)
        ]

        result = ranker.rank_and_filter(anomalies)

        assert result['total_detected'] == 3
        assert result['total_shown'] == 3
        assert len(result['high_severity']) == 3
        assert len(result['suppressed']) == 0

    def test_rank_and_filter_exceeds_target(self, ranker):
        """Test ranking when high confidence exceeds TARGET_ALERTS."""
        # Create 8 HIGH confidence anomalies (TARGET_ALERTS = 5)
        anomalies = [
            {
                'clause_number': f'1.{i}',
                'severity': 'high',
                'confidence_calibration': {
                    'calibrated_confidence': 0.9 - (i * 0.01),  # Decreasing confidence
                    'confidence_tier': 'HIGH'
                },
                'detected_indicators': []
            }
            for i in range(8)
        ]

        result = ranker.rank_and_filter(anomalies)

        assert result['total_detected'] == 8
        # Should keep 5 in HIGH, move 3 to MODERATE, total = 8 (within MAX_ALERTS=10)
        assert len(result['high_severity']) == 5
        assert len(result['medium_severity']) == 3
        assert len(result['suppressed']) == 0

    def test_rank_and_filter_exceeds_max(self, ranker):
        """Test ranking when total anomalies exceed MAX_ALERTS."""
        # Create 15 anomalies (MAX_ALERTS = 10)
        anomalies = [
            {
                'clause_number': f'1.{i}',
                'severity': 'medium',
                'confidence_calibration': {
                    'calibrated_confidence': 0.7,
                    'confidence_tier': 'MODERATE'
                },
                'detected_indicators': []
            }
            for i in range(15)
        ]

        result = ranker.rank_and_filter(anomalies)

        assert result['total_detected'] == 15
        assert result['total_shown'] == 10  # MAX_ALERTS
        assert len(result['suppressed']) == 5

    def test_rank_and_filter_mixed_tiers(self, ranker):
        """Test ranking with mixed confidence tiers."""
        anomalies = [
            # 3 HIGH
            *[{
                'clause_number': f'high_{i}',
                'severity': 'high',
                'confidence_calibration': {'calibrated_confidence': 0.9, 'confidence_tier': 'HIGH'},
                'detected_indicators': []
            } for i in range(3)],
            # 5 MODERATE
            *[{
                'clause_number': f'mod_{i}',
                'severity': 'medium',
                'confidence_calibration': {'calibrated_confidence': 0.7, 'confidence_tier': 'MODERATE'},
                'detected_indicators': []
            } for i in range(5)],
            # 4 LOW
            *[{
                'clause_number': f'low_{i}',
                'severity': 'low',
                'confidence_calibration': {'calibrated_confidence': 0.4, 'confidence_tier': 'LOW'},
                'detected_indicators': []
            } for i in range(4)]
        ]

        result = ranker.rank_and_filter(anomalies)

        assert result['total_detected'] == 12
        assert result['total_shown'] == 10  # MAX_ALERTS
        assert len(result['high_severity']) == 3
        assert len(result['medium_severity']) == 5
        assert len(result['low_severity']) == 2
        assert len(result['suppressed']) == 2

    def test_rank_and_filter_show_all_preference(self):
        """Test ranking with show_all preference."""
        ranker = AlertRanker(user_preferences={'show_all': True})

        anomalies = [
            {
                'clause_number': f'1.{i}',
                'severity': 'low',
                'confidence_calibration': {'calibrated_confidence': 0.5, 'confidence_tier': 'LOW'},
                'detected_indicators': []
            }
            for i in range(20)
        ]

        result = ranker.rank_and_filter(anomalies)

        assert result['total_detected'] == 20
        assert result['total_shown'] == 20  # All shown, budget bypassed
        assert len(result['suppressed']) == 0

    def test_rank_and_filter_with_compound_risks(self, ranker):
        """Test ranking with compound risks included."""
        anomalies = [
            {
                'clause_number': '1.1',
                'severity': 'medium',
                'confidence_calibration': {'calibrated_confidence': 0.7, 'confidence_tier': 'MODERATE'},
                'detected_indicators': []
            }
        ]

        compound_risks = [
            {
                'compound_risk_type': 'lock_in',
                'name': 'Lock-in Trap',
                'description': 'Compound risk description',
                'compound_severity': 'HIGH',
                'confidence': 0.9
            }
        ]

        result = ranker.rank_and_filter(anomalies, compound_risks)

        assert result['total_detected'] == 2  # 1 anomaly + 1 compound
        assert result['total_shown'] == 2

    def test_score_anomaly_base(self, ranker, sample_anomaly):
        """Test basic anomaly scoring."""
        score_result = ranker._score_anomaly(sample_anomaly, {})

        assert 'final_score' in score_result
        assert 'breakdown' in score_result
        assert score_result['breakdown']['severity_weight'] == 3.0  # high = 3.0
        assert score_result['breakdown']['confidence'] == 0.85

    def test_score_anomaly_with_bonuses(self, ranker):
        """Test anomaly scoring with bonuses."""
        anomaly = {
            'severity': 'high',
            'confidence_calibration': {'calibrated_confidence': 0.9},
            'is_compound_risk': True,
            'detected_indicators': [{'name': 'gdpr_violation'}],
            'risk_category': 'data_selling'
        }

        context = {
            'industry': 'health_apps',
            'is_change': True
        }

        score_result = ranker._score_anomaly(anomaly, context)

        # Should have multiple bonuses
        assert 'compound_risk' in score_result['breakdown']['bonuses']
        assert 'recent_change' in score_result['breakdown']['bonuses']
        assert 'industry_critical' in score_result['breakdown']['bonuses']
        assert 'regulatory_violation' in score_result['breakdown']['bonuses']

    def test_calculate_user_relevance_no_preferences(self, ranker, sample_anomaly):
        """Test user relevance with no preferences."""
        relevance = ranker._calculate_user_relevance(sample_anomaly)
        assert relevance == 1.0  # Neutral

    def test_calculate_user_relevance_priority_match(self, sample_anomaly):
        """Test user relevance with priority category match."""
        ranker = AlertRanker(user_preferences={
            'priority_categories': ['data_collection']
        })

        relevance = ranker._calculate_user_relevance(sample_anomaly)
        assert relevance == 1.5  # High relevance

    def test_calculate_user_relevance_concern_level(self):
        """Test user relevance with concern level."""
        ranker = AlertRanker(user_preferences={'concern_level': 'high'})

        anomaly = {
            'severity': 'high',
            'risk_category': 'other'
        }

        relevance = ranker._calculate_user_relevance(anomaly)
        assert relevance == 1.3

    def test_is_industry_critical_true(self, ranker):
        """Test industry critical detection - true case."""
        anomaly = {
            'risk_category': 'data_selling',
            'detected_indicators': [{'name': 'data_selling'}]
        }

        context = {'industry': 'health_apps'}

        assert ranker._is_industry_critical(anomaly, context) is True

    def test_is_industry_critical_false(self, ranker):
        """Test industry critical detection - false case."""
        anomaly = {
            'risk_category': 'auto_renewal',
            'detected_indicators': [{'name': 'auto_renewal'}]
        }

        context = {'industry': 'health_apps'}

        assert ranker._is_industry_critical(anomaly, context) is False

    def test_is_industry_critical_unknown_industry(self, ranker):
        """Test industry critical with unknown industry."""
        anomaly = {
            'risk_category': 'data_selling',
            'detected_indicators': []
        }

        context = {'industry': 'unknown_industry'}

        assert ranker._is_industry_critical(anomaly, context) is False

    def test_is_regulatory_violation_true(self, ranker):
        """Test regulatory violation detection - true case."""
        anomaly = {
            'risk_category': 'gdpr_violation',
            'detected_indicators': [{'name': 'gdpr_violation'}]
        }

        assert ranker._is_regulatory_violation(anomaly) is True

    def test_is_regulatory_violation_false(self, ranker):
        """Test regulatory violation detection - false case."""
        anomaly = {
            'risk_category': 'auto_renewal',
            'detected_indicators': [{'name': 'auto_renewal'}]
        }

        assert ranker._is_regulatory_violation(anomaly) is False

    def test_convert_compound_to_anomaly(self, ranker):
        """Test compound risk conversion to anomaly format."""
        compound_risk = {
            'compound_risk_type': 'lock_in',
            'name': 'Lock-in Trap',
            'description': 'Test description',
            'compound_severity': 'HIGH',
            'confidence': 0.9
        }

        anomaly = ranker._convert_compound_to_anomaly(compound_risk)

        assert anomaly['clause_number'] == 'COMPOUND_lock_in'
        assert anomaly['is_compound_risk'] is True
        assert anomaly['severity'] == 'high'
        assert anomaly['confidence_calibration']['calibrated_confidence'] == 0.9

    def test_get_top_categories(self, ranker):
        """Test getting top categories from anomalies."""
        anomalies = [
            {'risk_category': 'data_collection'},
            {'risk_category': 'data_collection'},
            {'risk_category': 'liability'},
            {'risk_category': 'liability'},
            {'risk_category': 'liability'},
            {'risk_category': 'other'}
        ]

        top_categories = ranker._get_top_categories(anomalies, top_n=3)

        assert len(top_categories) == 3
        assert top_categories[0]['category'] == 'liability'
        assert top_categories[0]['count'] == 3
        assert top_categories[1]['category'] == 'data_collection'
        assert top_categories[1]['count'] == 2

    def test_adjust_budget(self, ranker):
        """Test adjusting alert budget dynamically."""
        assert ranker.MAX_ALERTS == 10
        assert ranker.TARGET_ALERTS == 5

        ranker.adjust_budget(max_alerts=15, target_alerts=8)

        assert ranker.MAX_ALERTS == 15
        assert ranker.TARGET_ALERTS == 8

    def test_severity_weights(self, ranker):
        """Test severity weight constants."""
        assert ranker.SEVERITY_WEIGHTS['low'] == 1.0
        assert ranker.SEVERITY_WEIGHTS['medium'] == 2.0
        assert ranker.SEVERITY_WEIGHTS['high'] == 3.0
        assert ranker.SEVERITY_WEIGHTS['critical'] == 4.0

    def test_bonus_constants(self, ranker):
        """Test bonus score constants."""
        assert ranker.BONUS_COMPOUND_RISK == 5.0
        assert ranker.BONUS_RECENT_CHANGE == 2.0
        assert ranker.BONUS_INDUSTRY_CRITICAL == 1.5
        assert ranker.BONUS_REGULATORY_VIOLATION == 3.0

    def test_ranking_metadata(self, ranker):
        """Test ranking metadata in output."""
        anomalies = [
            {
                'clause_number': f'1.{i}',
                'severity': 'medium',
                'risk_category': 'data_collection',
                'confidence_calibration': {'calibrated_confidence': 0.7, 'confidence_tier': 'MODERATE'},
                'detected_indicators': []
            }
            for i in range(5)
        ]

        result = ranker.rank_and_filter(anomalies)

        metadata = result['ranking_metadata']
        assert 'total_detected' in metadata
        assert 'total_shown' in metadata
        assert 'suppression_rate' in metadata
        assert 'avg_score' in metadata
        assert 'top_categories' in metadata
        assert metadata['alert_budget_applied'] is True

    def test_scoring_breakdown_in_output(self, ranker, sample_anomaly):
        """Test scoring breakdown included in output."""
        result = ranker.rank_and_filter([sample_anomaly])

        anomaly = result['high_severity'][0]
        assert 'ranking_score' in anomaly
        assert 'scoring_breakdown' in anomaly
        assert 'severity_weight' in anomaly['scoring_breakdown']
        assert 'confidence' in anomaly['scoring_breakdown']
        assert 'bonuses' in anomaly['scoring_breakdown']

    def test_sorting_by_score(self, ranker):
        """Test anomalies are sorted by score descending."""
        anomalies = [
            {
                'clause_number': '1.1',
                'severity': 'low',  # Will have low score
                'confidence_calibration': {'calibrated_confidence': 0.5, 'confidence_tier': 'LOW'},
                'detected_indicators': []
            },
            {
                'clause_number': '1.2',
                'severity': 'high',  # Will have high score
                'confidence_calibration': {'calibrated_confidence': 0.9, 'confidence_tier': 'HIGH'},
                'detected_indicators': []
            },
            {
                'clause_number': '1.3',
                'severity': 'medium',  # Will have medium score
                'confidence_calibration': {'calibrated_confidence': 0.7, 'confidence_tier': 'MODERATE'},
                'detected_indicators': []
            }
        ]

        result = ranker.rank_and_filter(anomalies)

        # High score should be first in its tier
        assert result['high_severity'][0]['clause_number'] == '1.2'

    def test_industry_critical_combinations(self, ranker):
        """Test all industry critical combinations are defined."""
        assert 'health_apps' in ranker.INDUSTRY_CRITICAL_COMBINATIONS
        assert 'financial_apps' in ranker.INDUSTRY_CRITICAL_COMBINATIONS
        assert 'children_apps' in ranker.INDUSTRY_CRITICAL_COMBINATIONS
        assert 'dating_apps' in ranker.INDUSTRY_CRITICAL_COMBINATIONS

    def test_regulatory_violations_list(self, ranker):
        """Test all regulatory violations are defined."""
        expected = [
            'gdpr_violation',
            'ccpa_violation',
            'coppa_violation',
            'hipaa_violation',
            'cfpb_prohibited_term'
        ]
        assert ranker.REGULATORY_VIOLATIONS == expected
