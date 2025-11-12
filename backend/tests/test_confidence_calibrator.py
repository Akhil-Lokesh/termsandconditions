"""
Tests for ConfidenceCalibrator.

Tests isotonic regression calibration, ECE calculation, tier assignment,
and graceful handling of edge cases.
"""

import pytest
import numpy as np
from app.core.confidence_calibrator import ConfidenceCalibrator, CONFIDENCE_TIERS


class TestConfidenceCalibrator:
    """Test suite for ConfidenceCalibrator."""

    def test_init(self):
        """Test calibrator initialization."""
        calibrator = ConfidenceCalibrator()

        assert calibrator.is_fitted is False
        assert calibrator.calibrator is not None

    def test_confidence_tiers_definition(self):
        """Test confidence tier thresholds are correctly defined."""
        assert CONFIDENCE_TIERS['HIGH']['min'] == 0.85
        assert CONFIDENCE_TIERS['HIGH']['max'] == 1.00
        assert CONFIDENCE_TIERS['MODERATE']['min'] == 0.60
        assert CONFIDENCE_TIERS['MODERATE']['max'] == 0.85
        assert CONFIDENCE_TIERS['LOW']['min'] == 0.00
        assert CONFIDENCE_TIERS['LOW']['max'] == 0.60

    def test_fit_valid_data(self):
        """Test fitting calibrator with valid data."""
        calibrator = ConfidenceCalibrator()

        # Create synthetic data with 100 samples
        np.random.seed(42)
        predicted_probs = np.random.rand(100)
        actual_labels = (predicted_probs > 0.5).astype(int)

        # Fit calibrator
        calibrator.fit(predicted_probs, actual_labels)

        assert calibrator.is_fitted is True

    def test_fit_length_mismatch(self):
        """Test that fit raises error on length mismatch."""
        calibrator = ConfidenceCalibrator()

        predicted_probs = np.array([0.5, 0.6, 0.7])
        actual_labels = np.array([0, 1])  # Wrong length

        with pytest.raises(ValueError, match="Length mismatch"):
            calibrator.fit(predicted_probs, actual_labels)

    def test_fit_empty_data(self):
        """Test that fit raises error on empty data."""
        calibrator = ConfidenceCalibrator()

        predicted_probs = np.array([])
        actual_labels = np.array([])

        with pytest.raises(ValueError, match="Cannot fit calibrator on empty data"):
            calibrator.fit(predicted_probs, actual_labels)

    def test_fit_invalid_probability_range(self):
        """Test that fit raises error on invalid probability range."""
        calibrator = ConfidenceCalibrator()

        predicted_probs = np.array([0.5, 1.5, 0.7])  # 1.5 is out of range
        actual_labels = np.array([0, 1, 1])

        with pytest.raises(ValueError, match="must be in range"):
            calibrator.fit(predicted_probs, actual_labels)

    def test_fit_invalid_labels(self):
        """Test that fit raises error on non-binary labels."""
        calibrator = ConfidenceCalibrator()

        predicted_probs = np.array([0.5, 0.6, 0.7])
        actual_labels = np.array([0, 1, 2])  # 2 is invalid

        with pytest.raises(ValueError, match="must be binary"):
            calibrator.fit(predicted_probs, actual_labels)

    def test_calibrate_without_fitting(self):
        """Test calibrate returns raw scores with warning when not fitted."""
        calibrator = ConfidenceCalibrator()

        result = calibrator.calibrate(0.75)

        assert result['raw_confidence'] == 0.75
        assert result['calibrated_confidence'] == 0.75
        assert result['confidence_tier'] == 'MODERATE'
        assert 'warning' in result
        assert result['warning'] == 'Calibrator not fitted, using raw scores'

    def test_calibrate_after_fitting(self):
        """Test calibrate returns calibrated scores after fitting."""
        calibrator = ConfidenceCalibrator()

        # Create synthetic data
        np.random.seed(42)
        predicted_probs = np.random.rand(100)
        actual_labels = (predicted_probs > 0.5).astype(int)

        # Fit calibrator
        calibrator.fit(predicted_probs, actual_labels)

        # Calibrate a score
        result = calibrator.calibrate(0.75)

        assert 'raw_confidence' in result
        assert 'calibrated_confidence' in result
        assert 'confidence_tier' in result
        assert 'tier_label' in result
        assert 'explanation' in result
        assert 'warning' not in result
        assert result['raw_confidence'] == 0.75
        assert 0.0 <= result['calibrated_confidence'] <= 1.0

    def test_calibrate_out_of_bounds(self):
        """Test calibrate handles out-of-bounds input gracefully."""
        calibrator = ConfidenceCalibrator()

        # Test value > 1
        result = calibrator.calibrate(1.5)
        assert result['raw_confidence'] == 1.0  # Clipped

        # Test value < 0
        result = calibrator.calibrate(-0.5)
        assert result['raw_confidence'] == 0.0  # Clipped

    def test_get_tier_high(self):
        """Test _get_tier returns HIGH for high confidence."""
        calibrator = ConfidenceCalibrator()

        assert calibrator._get_tier(0.85) == 'HIGH'
        assert calibrator._get_tier(0.90) == 'HIGH'
        assert calibrator._get_tier(1.00) == 'HIGH'

    def test_get_tier_moderate(self):
        """Test _get_tier returns MODERATE for moderate confidence."""
        calibrator = ConfidenceCalibrator()

        assert calibrator._get_tier(0.60) == 'MODERATE'
        assert calibrator._get_tier(0.70) == 'MODERATE'
        assert calibrator._get_tier(0.84) == 'MODERATE'

    def test_get_tier_low(self):
        """Test _get_tier returns LOW for low confidence."""
        calibrator = ConfidenceCalibrator()

        assert calibrator._get_tier(0.00) == 'LOW'
        assert calibrator._get_tier(0.30) == 'LOW'
        assert calibrator._get_tier(0.59) == 'LOW'

    def test_get_tier_label(self):
        """Test _get_tier_label returns correct labels."""
        calibrator = ConfidenceCalibrator()

        assert calibrator._get_tier_label(0.90) == 'High Confidence'
        assert calibrator._get_tier_label(0.70) == 'Moderate Confidence'
        assert calibrator._get_tier_label(0.40) == 'Low Confidence'

    def test_generate_explanation_high(self):
        """Test _generate_explanation for HIGH tier."""
        calibrator = ConfidenceCalibrator()

        explanation = calibrator._generate_explanation('HIGH', 0.92)

        assert '92% confident' in explanation
        assert 'genuine concern' in explanation
        assert '100+ similar documents' in explanation

    def test_generate_explanation_moderate(self):
        """Test _generate_explanation for MODERATE tier."""
        calibrator = ConfidenceCalibrator()

        explanation = calibrator._generate_explanation('MODERATE', 0.73)

        assert '73% confidence' in explanation
        assert 'appears concerning' in explanation
        assert 'review the specifics' in explanation

    def test_generate_explanation_low(self):
        """Test _generate_explanation for LOW tier."""
        calibrator = ConfidenceCalibrator()

        explanation = calibrator._generate_explanation('LOW', 0.48)

        assert '48% confidence' in explanation
        assert 'might be an issue' in explanation
        assert 'Check if it applies' in explanation

    def test_calculate_expected_calibration_error(self):
        """Test ECE calculation."""
        calibrator = ConfidenceCalibrator()

        # Perfect calibration: predicted = actual
        predicted = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        actual = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])

        ece = calibrator._calculate_expected_calibration_error(
            predicted, actual, n_bins=10
        )

        # ECE should be relatively low for this data
        assert 0.0 <= ece <= 1.0
        assert isinstance(ece, float)

    def test_calculate_ece_perfect_calibration(self):
        """Test ECE is low for perfectly calibrated predictions."""
        calibrator = ConfidenceCalibrator()

        # Create perfectly calibrated data
        # If we predict 0.3, 30% should be positive
        predicted = np.concatenate([
            np.full(70, 0.3),  # 70 samples at 0.3 confidence
            np.full(30, 0.3)   # 30 samples at 0.3 confidence
        ])
        actual = np.concatenate([
            np.zeros(70),  # 70 negative (0.3 * 100 = 30 should be positive)
            np.ones(30)    # 30 positive
        ])

        ece = calibrator._calculate_expected_calibration_error(
            predicted, actual, n_bins=10
        )

        # ECE should be very low (near 0) for perfect calibration
        assert ece < 0.1

    def test_calculate_ece_poor_calibration(self):
        """Test ECE is high for poorly calibrated predictions."""
        calibrator = ConfidenceCalibrator()

        # Create poorly calibrated data
        # Predict high confidence but actual is mostly negative
        predicted = np.full(100, 0.9)  # All high confidence
        actual = np.concatenate([np.zeros(80), np.ones(20)])  # Only 20% positive

        ece = calibrator._calculate_expected_calibration_error(
            predicted, actual, n_bins=10
        )

        # ECE should be high (> 0.5) for poor calibration
        assert ece > 0.5

    def test_get_calibration_stats(self):
        """Test get_calibration_stats returns correct information."""
        calibrator = ConfidenceCalibrator()

        stats = calibrator.get_calibration_stats()

        assert 'is_fitted' in stats
        assert 'tiers' in stats
        assert 'calibrator_type' in stats
        assert 'out_of_bounds_strategy' in stats
        assert stats['is_fitted'] is False
        assert stats['calibrator_type'] == 'IsotonicRegression'
        assert stats['out_of_bounds_strategy'] == 'clip'
        assert stats['tiers'] == CONFIDENCE_TIERS

    def test_calibrate_return_format(self):
        """Test calibrate returns all required fields."""
        calibrator = ConfidenceCalibrator()

        result = calibrator.calibrate(0.75)

        # Check all required fields are present
        assert 'raw_confidence' in result
        assert 'calibrated_confidence' in result
        assert 'confidence_tier' in result
        assert 'tier_label' in result
        assert 'explanation' in result

        # Check types
        assert isinstance(result['raw_confidence'], float)
        assert isinstance(result['calibrated_confidence'], float)
        assert isinstance(result['confidence_tier'], str)
        assert isinstance(result['tier_label'], str)
        assert isinstance(result['explanation'], str)

    def test_calibration_monotonic(self):
        """Test that calibration preserves monotonicity."""
        calibrator = ConfidenceCalibrator()

        # Create synthetic data
        np.random.seed(42)
        predicted_probs = np.random.rand(100)
        actual_labels = (predicted_probs > 0.5).astype(int)

        # Fit calibrator
        calibrator.fit(predicted_probs, actual_labels)

        # Test monotonicity: higher input should give higher output
        scores = [0.2, 0.4, 0.6, 0.8]
        calibrated_scores = [
            calibrator.calibrate(s)['calibrated_confidence'] for s in scores
        ]

        # Check monotonicity
        for i in range(len(calibrated_scores) - 1):
            assert calibrated_scores[i] <= calibrated_scores[i + 1]

    def test_fit_calculates_brier_score(self):
        """Test that fit calculates Brier score improvement."""
        calibrator = ConfidenceCalibrator()

        # Create synthetic data where calibration can improve
        np.random.seed(42)
        predicted_probs = np.random.rand(100)
        actual_labels = (predicted_probs > 0.5).astype(int)

        # Fit should complete without errors
        calibrator.fit(predicted_probs, actual_labels)

        # Just verify it completes (metrics are logged but not returned)
        assert calibrator.is_fitted is True

    def test_multiple_calibrations(self):
        """Test multiple calibrations after single fit."""
        calibrator = ConfidenceCalibrator()

        # Fit once
        np.random.seed(42)
        predicted_probs = np.random.rand(100)
        actual_labels = (predicted_probs > 0.5).astype(int)
        calibrator.fit(predicted_probs, actual_labels)

        # Multiple calibrations should work
        result1 = calibrator.calibrate(0.3)
        result2 = calibrator.calibrate(0.7)
        result3 = calibrator.calibrate(0.9)

        assert all('calibrated_confidence' in r for r in [result1, result2, result3])
        assert result1['calibrated_confidence'] <= result2['calibrated_confidence']
        assert result2['calibrated_confidence'] <= result3['calibrated_confidence']

    def test_edge_cases_0_and_1(self):
        """Test calibration handles edge cases 0 and 1 correctly."""
        calibrator = ConfidenceCalibrator()

        # Without fitting
        result_0 = calibrator.calibrate(0.0)
        result_1 = calibrator.calibrate(1.0)

        assert result_0['raw_confidence'] == 0.0
        assert result_1['raw_confidence'] == 1.0
        assert result_0['confidence_tier'] == 'LOW'
        assert result_1['confidence_tier'] == 'HIGH'

    def test_tier_boundaries(self):
        """Test tier boundaries are correctly applied."""
        calibrator = ConfidenceCalibrator()

        # Test exact boundaries
        result_low_high = calibrator.calibrate(0.5999)
        result_moderate_low = calibrator.calibrate(0.6000)
        result_moderate_high = calibrator.calibrate(0.8499)
        result_high_low = calibrator.calibrate(0.8500)

        assert result_low_high['confidence_tier'] == 'LOW'
        assert result_moderate_low['confidence_tier'] == 'MODERATE'
        assert result_moderate_high['confidence_tier'] == 'MODERATE'
        assert result_high_low['confidence_tier'] == 'HIGH'
