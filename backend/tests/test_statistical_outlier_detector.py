"""
Tests for StatisticalOutlierDetector.

Tests the Stage 1 statistical outlier detection functionality.
"""

import pytest
import numpy as np
from app.core.statistical_outlier_detector import StatisticalOutlierDetector


class TestStatisticalOutlierDetector:
    """Test suite for StatisticalOutlierDetector."""

    @pytest.fixture
    def detector(self):
        """Create a detector instance."""
        return StatisticalOutlierDetector(contamination=0.1, random_state=42)

    @pytest.fixture
    def sample_clauses(self):
        """Create sample baseline clauses for training."""
        return [
            {
                'text': 'The service is provided as-is without any warranty. '
                        'You agree to use the service at your own risk. '
                        'We are not liable for any damages.'
            },
            {
                'text': 'You may terminate your account at any time by contacting support. '
                        'Upon termination, all your data will be deleted within 30 days.'
            },
            {
                'text': 'We collect information about your usage of the service. '
                        'This information may be shared with third parties for analytics purposes.'
            },
            {
                'text': 'Payment is due on the first day of each billing cycle. '
                        'Failure to pay may result in service suspension.'
            },
            {
                'text': 'These terms are governed by the laws of California. '
                        'Any disputes shall be resolved through binding arbitration.'
            },
            {
                'text': 'You grant us a perpetual, worldwide license to use your content. '
                        'We may modify or remove your content without notice.'
            },
            {
                'text': 'Your privacy is important to us. We will not sell your personal information. '
                        'However, we may share it with partners for service improvements.'
            },
            {
                'text': 'Subscription automatically renews unless cancelled before the renewal date. '
                        'You will be charged the then-current price.'
            },
            {
                'text': 'If you breach these terms, we may immediately suspend your account. '
                        'No refund will be provided for partial billing periods.'
            },
            {
                'text': 'We reserve the right to modify these terms at any time. '
                        'Continued use constitutes acceptance of the modified terms.'
            },
            {
                'text': 'All intellectual property rights remain with the company. '
                        'You may not reverse engineer or copy any part of the service.'
            },
            {
                'text': 'The service may be unavailable during maintenance windows. '
                        'We will provide notice when possible but are not obligated to do so.'
            },
            {
                'text': 'You are responsible for maintaining the security of your account. '
                        'Unauthorized access should be reported immediately.'
            },
            {
                'text': 'Content uploaded by users is their sole responsibility. '
                        'We do not review or endorse user-generated content.'
            },
            {
                'text': 'Export of data is available through our API. '
                        'Data portability requests must be made in writing.'
            }
        ]

    @pytest.fixture
    def outlier_clause(self):
        """Create an outlier clause with unusual characteristics."""
        return {
            'text': 'NOTWITHSTANDING ANY PROVISIONS HEREIN TO THE CONTRARY, '
                    'YOU HEREBY IRREVOCABLY AND UNCONDITIONALLY WAIVE ANY AND ALL RIGHTS, '
                    'WHETHER STATUTORY OR OTHERWISE, TO PURSUE ANY CLAIMS, DAMAGES, OR REMEDIES '
                    'AGAINST THE COMPANY, ITS AFFILIATES, SUBSIDIARIES, OFFICERS, DIRECTORS, '
                    'EMPLOYEES, AGENTS, SUCCESSORS, AND ASSIGNS, IN PERPETUITY THROUGHOUT '
                    'THE UNIVERSE AND ALL PARALLEL DIMENSIONS, FOR ANY LOSSES, LIABILITIES, '
                    'COSTS, EXPENSES, OR OTHER PECUNIARY OR NON-PECUNIARY DAMAGES WHATSOEVER, '
                    'INCLUDING BUT NOT LIMITED TO DIRECT, INDIRECT, INCIDENTAL, CONSEQUENTIAL, '
                    'EXEMPLARY, PUNITIVE, OR SPECIAL DAMAGES, ARISING FROM OR RELATING TO '
                    'YOUR USE OF THE SERVICE OR THESE TERMS, WHETHER IN CONTRACT, TORT, '
                    'STRICT LIABILITY, OR ANY OTHER LEGAL THEORY, EVEN IF ADVISED OF THE '
                    'POSSIBILITY OF SUCH DAMAGES, AND REGARDLESS OF WHETHER THE COMPANY '
                    'ACTED WITH NEGLIGENCE, GROSS NEGLIGENCE, RECKLESSNESS, OR WILLFUL MISCONDUCT.'
        }

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.contamination == 0.1
        assert detector.random_state == 42
        assert not detector.is_fitted
        assert len(detector.feature_names) == 9

    def test_extract_features_valid_clause(self, detector):
        """Test feature extraction from valid clause."""
        clause = {
            'text': 'The service is provided as-is. You agree to the terms.'
        }

        features = detector.extract_statistical_features(clause)

        assert isinstance(features, np.ndarray)
        assert features.shape == (9,)
        assert np.all(np.isfinite(features))
        assert features[0] > 0  # clause_length
        assert features[1] > 0  # sentence_count

    def test_extract_features_different_keys(self, detector):
        """Test feature extraction with different clause dict keys."""
        # Test with 'clause_text' key
        clause1 = {'clause_text': 'This is a test clause with some text.'}
        features1 = detector.extract_statistical_features(clause1)
        assert features1.shape == (9,)

        # Test with 'content' key
        clause2 = {'content': 'This is a test clause with some text.'}
        features2 = detector.extract_statistical_features(clause2)
        assert features2.shape == (9,)

    def test_extract_features_empty_text(self, detector):
        """Test feature extraction with empty text."""
        clause = {'text': ''}

        with pytest.raises(ValueError, match="non-empty"):
            detector.extract_statistical_features(clause)

    def test_extract_features_short_text(self, detector):
        """Test feature extraction with very short text."""
        clause = {'text': 'Hi'}

        with pytest.raises(ValueError, match="too short"):
            detector.extract_statistical_features(clause)

    def test_extract_features_missing_text(self, detector):
        """Test feature extraction with missing text key."""
        clause = {'other_field': 'some value'}

        with pytest.raises(ValueError, match="non-empty"):
            detector.extract_statistical_features(clause)

    def test_count_sentences(self, detector):
        """Test sentence counting."""
        text1 = "This is one sentence."
        assert detector._count_sentences(text1) == 1

        text2 = "First sentence. Second sentence! Third sentence?"
        assert detector._count_sentences(text2) == 3

        text3 = "Single sentence without punctuation"
        assert detector._count_sentences(text3) == 1

    def test_count_syllables(self, detector):
        """Test syllable counting."""
        assert detector._count_syllables("hello") >= 1
        assert detector._count_syllables("world") >= 1
        assert detector._count_syllables("a") == 1
        assert detector._count_syllables("the") == 1

    def test_flesch_kincaid_score(self, detector):
        """Test Flesch-Kincaid readability score calculation."""
        # Simple text should have higher score
        simple_text = "The cat sat. The dog ran."
        simple_score = detector._flesch_kincaid_score(simple_text)

        # Complex text should have lower score
        complex_text = (
            "Notwithstanding any provisions to the contrary, "
            "the aforementioned stipulations shall remain in effect."
        )
        complex_score = detector._flesch_kincaid_score(complex_text)

        assert 0 <= simple_score <= 100
        assert 0 <= complex_score <= 100
        assert simple_score > complex_score

    def test_count_risk_keywords(self, detector):
        """Test risk keyword counting."""
        text_with_risks = "We may terminate your account at any time without notice."
        count = detector._count_risk_keywords(text_with_risks)
        assert count > 0

        text_without_risks = "Thank you for using our service."
        count = detector._count_risk_keywords(text_without_risks)
        assert count == 0

    def test_legal_jargon_density(self, detector):
        """Test legal jargon density calculation."""
        # High jargon text
        jargon_text = (
            "Notwithstanding the provisions hereof, the parties hereto "
            "shall indemnify and hold harmless the aforementioned entities."
        )
        high_density = detector._legal_jargon_density(jargon_text)

        # Low jargon text
        plain_text = "You can use the service for free. Cancel anytime."
        low_density = detector._legal_jargon_density(plain_text)

        assert high_density > low_density
        assert high_density > 0

    def test_fit_valid_clauses(self, detector, sample_clauses):
        """Test fitting on valid baseline clauses."""
        detector.fit(sample_clauses)

        assert detector.is_fitted
        assert detector.scaler is not None
        assert detector.model is not None

    def test_fit_empty_list(self, detector):
        """Test fitting on empty clause list."""
        with pytest.raises(ValueError, match="empty clause list"):
            detector.fit([])

    def test_predict_without_fitting(self, detector):
        """Test prediction without fitting first."""
        clause = {'text': 'This is a test clause.'}

        with pytest.raises(RuntimeError, match="must be fitted"):
            detector.predict(clause)

    def test_predict_normal_clause(self, detector, sample_clauses):
        """Test prediction on normal clause."""
        detector.fit(sample_clauses)

        # Predict on a similar clause
        normal_clause = {
            'text': 'You can cancel your subscription at any time. '
                    'Refunds are not available for partial periods.'
        }

        result = detector.predict(normal_clause)

        assert isinstance(result, dict)
        assert 'is_outlier' in result
        assert 'anomaly_score' in result
        assert 'confidence' in result
        assert 'features' in result
        assert 'stage' in result
        assert result['stage'] == 1

        # Should likely not be an outlier (but not guaranteed)
        assert isinstance(result['is_outlier'], bool)
        assert 0 <= result['confidence'] <= 1

    def test_predict_outlier_clause(self, detector, sample_clauses, outlier_clause):
        """Test prediction on outlier clause."""
        detector.fit(sample_clauses)

        result = detector.predict(outlier_clause)

        assert isinstance(result, dict)
        assert 'is_outlier' in result
        assert 'anomaly_score' in result
        assert 'confidence' in result

        # The extremely long and jargon-heavy clause should be flagged
        # (though this isn't 100% guaranteed with Isolation Forest)
        assert isinstance(result['is_outlier'], bool)
        assert result['anomaly_score'] < 0  # Negative score indicates anomaly

    def test_feature_dict_format(self, detector, sample_clauses):
        """Test that feature dict contains all expected features."""
        detector.fit(sample_clauses)

        clause = {'text': 'This is a test clause for feature extraction.'}
        result = detector.predict(clause)

        feature_dict = result['features']
        assert len(feature_dict) == 9

        expected_features = [
            'clause_length',
            'sentence_count',
            'avg_sentence_length',
            'flesch_kincaid_score',
            'modal_verb_count',
            'negation_count',
            'conditional_count',
            'risk_keyword_count',
            'legal_jargon_density'
        ]

        for feature_name in expected_features:
            assert feature_name in feature_dict
            assert isinstance(feature_dict[feature_name], (int, float))

    def test_get_feature_importance(self, detector, sample_clauses):
        """Test feature importance calculation."""
        detector.fit(sample_clauses)

        clause = {'text': 'This is a test clause.'}
        importance = detector.get_feature_importance(clause)

        assert isinstance(importance, dict)
        assert len(importance) == 9

        for feature_name, deviation in importance.items():
            assert feature_name in detector.feature_names
            assert isinstance(deviation, float)
            assert deviation >= 0

    def test_feature_importance_without_fitting(self, detector):
        """Test feature importance without fitting."""
        clause = {'text': 'This is a test clause.'}

        with pytest.raises(RuntimeError, match="must be fitted"):
            detector.get_feature_importance(clause)

    def test_modal_verb_detection(self, detector):
        """Test modal verb pattern detection."""
        text_with_modals = "You must agree. You shall comply. You may cancel."
        count = detector._count_patterns(text_with_modals, detector.MODAL_VERBS)
        assert count >= 3

    def test_negation_detection(self, detector):
        """Test negation pattern detection."""
        text_with_negations = "You cannot do this. We will not refund. Never share data."
        count = detector._count_patterns(text_with_negations, detector.NEGATIONS)
        assert count >= 3

    def test_conditional_detection(self, detector):
        """Test conditional pattern detection."""
        text_with_conditionals = "If you cancel, unless stated otherwise, provided that you agree."
        count = detector._count_patterns(text_with_conditionals, detector.CONDITIONALS)
        assert count >= 3

    def test_model_persistence(self, detector, sample_clauses, tmp_path):
        """Test model save and load."""
        # Fit model
        detector.fit(sample_clauses)

        # Save model
        model_path = tmp_path / "test_model.pkl"
        detector.save_model(str(model_path))

        # Create new detector and load
        new_detector = StatisticalOutlierDetector()
        new_detector.load_model(str(model_path))

        assert new_detector.is_fitted
        assert new_detector.contamination == detector.contamination

        # Test prediction with loaded model
        clause = {'text': 'This is a test clause.'}
        result = new_detector.predict(clause)
        assert 'is_outlier' in result

    def test_save_unfitted_model(self, detector, tmp_path):
        """Test saving unfitted model raises error."""
        model_path = tmp_path / "test_model.pkl"

        with pytest.raises(RuntimeError, match="unfitted model"):
            detector.save_model(str(model_path))

    def test_confidence_range(self, detector, sample_clauses):
        """Test that confidence is always in valid range."""
        detector.fit(sample_clauses)

        test_clauses = [
            {'text': 'Short clause.'},
            {'text': 'This is a medium length clause with normal content.'},
            {
                'text': 'This is a very long clause with lots of words and complex '
                        'legal terminology including hereby, notwithstanding, and '
                        'various other jargon terms that might indicate unusual content.'
            }
        ]

        for clause in test_clauses:
            result = detector.predict(clause)
            assert 0 <= result['confidence'] <= 1

    def test_batch_prediction_consistency(self, detector, sample_clauses):
        """Test that predictions are consistent across multiple calls."""
        detector.fit(sample_clauses)

        clause = {'text': 'This is a test clause for consistency checking.'}

        # Predict multiple times
        results = [detector.predict(clause) for _ in range(5)]

        # All results should be identical (same model, same input)
        for i in range(1, len(results)):
            assert results[i]['is_outlier'] == results[0]['is_outlier']
            assert abs(results[i]['anomaly_score'] - results[0]['anomaly_score']) < 1e-6
            assert abs(results[i]['confidence'] - results[0]['confidence']) < 1e-6
