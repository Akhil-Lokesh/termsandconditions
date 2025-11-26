"""
Confidence calibrator for anomaly detection.

Calibrates raw confidence scores to improve reliability and interpretability.
Uses isotonic regression to map raw scores to calibrated probabilities.

Stage 5 of the anomaly detection pipeline: Confidence Calibration
"""

from typing import Dict, Any, Optional
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# Confidence tier thresholds
CONFIDENCE_TIERS = {
    'HIGH': {'min': 0.85, 'max': 1.00, 'label': 'High Confidence'},
    'MODERATE': {'min': 0.60, 'max': 0.85, 'label': 'Moderate Confidence'},
    'LOW': {'min': 0.00, 'max': 0.60, 'label': 'Low Confidence'}
}


class ConfidenceCalibrator:
    """
    Calibrates confidence scores using isotonic regression.

    Isotonic regression is a non-parametric method that learns a monotonic
    mapping from raw confidence scores to calibrated probabilities. This
    ensures that higher confidence scores correspond to higher accuracy.

    Attributes:
        calibrator: sklearn IsotonicRegression instance
        is_fitted: Whether the calibrator has been trained
    """

    def __init__(self):
        """
        Initialize confidence calibrator.

        Creates an IsotonicRegression calibrator with out_of_bounds clipping
        to handle scores outside the training range.
        """
        self.calibrator = IsotonicRegression(
            out_of_bounds='clip',  # Clip scores outside [0, 1]
            y_min=0.0,
            y_max=1.0
        )
        self.is_fitted = False

        logger.info("Confidence calibrator initialized")

    def fit(
        self,
        predicted_probs: np.ndarray,
        actual_labels: np.ndarray
    ) -> None:
        """
        Fit the calibrator on training data.

        Trains isotonic regression to map raw confidence scores to
        calibrated probabilities. Calculates calibration metrics.

        Args:
            predicted_probs: Raw confidence scores (0-1) from model
            actual_labels: Ground truth binary labels (0 or 1)

        Raises:
            ValueError: If inputs are invalid or incompatible
        """
        logger.info(f"Fitting calibrator on {len(predicted_probs)} samples")

        # Validate inputs
        if len(predicted_probs) != len(actual_labels):
            raise ValueError(
                f"Length mismatch: {len(predicted_probs)} predictions vs "
                f"{len(actual_labels)} labels"
            )

        if len(predicted_probs) == 0:
            raise ValueError("Cannot fit calibrator on empty data")

        # Convert to numpy arrays
        predicted_probs = np.asarray(predicted_probs)
        actual_labels = np.asarray(actual_labels)

        # Validate ranges
        if np.any((predicted_probs < 0) | (predicted_probs > 1)):
            raise ValueError("predicted_probs must be in range [0, 1]")

        if not np.all(np.isin(actual_labels, [0, 1])):
            raise ValueError("actual_labels must be binary (0 or 1)")

        # Fit isotonic regression
        try:
            self.calibrator.fit(predicted_probs, actual_labels)
            self.is_fitted = True
            logger.info("Calibrator fitted successfully")
        except Exception as e:
            logger.error(f"Failed to fit calibrator: {e}")
            raise

        # Calculate calibration metrics
        try:
            # Get calibrated predictions
            calibrated_probs = self.calibrator.predict(predicted_probs)

            # Calculate Expected Calibration Error (ECE)
            ece = self._calculate_expected_calibration_error(
                predicted_probs, actual_labels, n_bins=10
            )

            # Calculate Brier score (before and after calibration)
            brier_before = brier_score_loss(actual_labels, predicted_probs)
            brier_after = brier_score_loss(actual_labels, calibrated_probs)

            # Log calibration quality metrics
            logger.info("=" * 60)
            logger.info("Calibration Quality Metrics")
            logger.info("=" * 60)
            logger.info(f"Expected Calibration Error (ECE): {ece:.4f}")
            logger.info(f"Brier Score (before calibration): {brier_before:.4f}")
            logger.info(f"Brier Score (after calibration):  {brier_after:.4f}")
            logger.info(f"Brier Score Improvement: {(brier_before - brier_after):.4f}")
            logger.info(f"Number of training samples: {len(predicted_probs)}")
            logger.info("=" * 60)

            # Print calibration quality assessment
            if ece < 0.05:
                quality = "Excellent"
            elif ece < 0.10:
                quality = "Good"
            elif ece < 0.15:
                quality = "Fair"
            else:
                quality = "Poor"

            print(f"\n✓ Calibration Quality: {quality} (ECE={ece:.4f})")
            print(f"  Brier Score: {brier_before:.4f} → {brier_after:.4f} "
                  f"({((brier_before - brier_after) / brier_before * 100):.1f}% improvement)")

        except Exception as e:
            logger.warning(f"Failed to calculate calibration metrics: {e}")

    def calibrate(self, raw_confidence: float) -> Dict[str, Any]:
        """
        Calibrate a raw confidence score.

        Maps raw confidence to calibrated probability and determines
        confidence tier with explanation.

        Args:
            raw_confidence: Raw confidence score (0-1)

        Returns:
            Dictionary containing:
                - raw_confidence: Original score
                - calibrated_confidence: Calibrated score
                - confidence_tier: Tier name (HIGH/MODERATE/LOW)
                - tier_label: Human-readable tier label
                - explanation: Explanation of confidence level
        """
        # Validate input
        if not 0 <= raw_confidence <= 1:
            logger.warning(
                f"raw_confidence {raw_confidence} outside [0, 1], clipping"
            )
            raw_confidence = np.clip(raw_confidence, 0.0, 1.0)

        # Check if calibrator is fitted
        if not self.is_fitted:
            logger.warning(
                "Calibrator not fitted, returning raw confidence with warning"
            )
            tier = self._get_tier(raw_confidence)
            return {
                'raw_confidence': raw_confidence,
                'calibrated_confidence': raw_confidence,
                'confidence_tier': tier,
                'tier_label': self._get_tier_label(raw_confidence),
                'explanation': self._generate_explanation(tier, raw_confidence),
                'warning': 'Calibrator not fitted, using raw scores'
            }

        # Calibrate confidence
        try:
            calibrated_confidence = float(
                self.calibrator.predict(np.array([raw_confidence]))[0]
            )

            # Ensure calibrated score is in valid range
            calibrated_confidence = np.clip(calibrated_confidence, 0.0, 1.0)

            # Determine tier based on calibrated confidence
            tier = self._get_tier(calibrated_confidence)
            tier_label = self._get_tier_label(calibrated_confidence)
            explanation = self._generate_explanation(tier, calibrated_confidence)

            logger.debug(
                f"Calibrated: {raw_confidence:.3f} → {calibrated_confidence:.3f} "
                f"({tier})"
            )

            return {
                'raw_confidence': raw_confidence,
                'calibrated_confidence': calibrated_confidence,
                'confidence_tier': tier,
                'tier_label': tier_label,
                'explanation': explanation
            }

        except Exception as e:
            logger.error(f"Calibration failed: {e}, returning raw confidence")
            tier = self._get_tier(raw_confidence)
            return {
                'raw_confidence': raw_confidence,
                'calibrated_confidence': raw_confidence,
                'confidence_tier': tier,
                'tier_label': self._get_tier_label(raw_confidence),
                'explanation': self._generate_explanation(tier, raw_confidence),
                'error': str(e)
            }

    def _get_tier(self, confidence: float) -> str:
        """
        Get confidence tier for a given confidence score.

        Args:
            confidence: Confidence score (0-1)

        Returns:
            Tier name: 'HIGH', 'MODERATE', or 'LOW'
        """
        if confidence >= CONFIDENCE_TIERS['HIGH']['min']:
            return 'HIGH'
        elif confidence >= CONFIDENCE_TIERS['MODERATE']['min']:
            return 'MODERATE'
        else:
            return 'LOW'

    def _get_tier_label(self, confidence: float) -> str:
        """
        Get human-readable tier label for a given confidence score.

        Args:
            confidence: Confidence score (0-1)

        Returns:
            Tier label: 'High Confidence', 'Moderate Confidence', or 'Low Confidence'
        """
        tier = self._get_tier(confidence)
        return CONFIDENCE_TIERS[tier]['label']

    def _generate_explanation(self, tier: str, confidence: float) -> str:
        """
        Generate explanation text for confidence tier.

        Provides context-appropriate explanation based on confidence level.

        Args:
            tier: Confidence tier ('HIGH', 'MODERATE', 'LOW')
            confidence: Confidence score (0-1)

        Returns:
            Explanation string
        """
        confidence_pct = int(confidence * 100)

        if tier == 'HIGH':
            return (
                f"We are {confidence_pct}% confident this is a genuine concern "
                f"based on our analysis of 100+ similar documents."
            )
        elif tier == 'MODERATE':
            return (
                f"This appears concerning ({confidence_pct}% confidence), "
                f"but review the specifics for your situation."
            )
        else:  # LOW
            return (
                f"This might be an issue ({confidence_pct}% confidence). "
                f"Check if it applies to your use case."
            )

    def _calculate_expected_calibration_error(
        self,
        predicted: np.ndarray,
        actual: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """
        Calculate Expected Calibration Error (ECE).

        ECE measures the difference between predicted confidence and actual
        accuracy across different confidence bins. Lower ECE means better
        calibration.

        Args:
            predicted: Predicted probabilities (0-1)
            actual: Actual binary labels (0 or 1)
            n_bins: Number of bins for ECE calculation

        Returns:
            ECE value (0-1, lower is better)
        """
        # Create bins
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        ece = 0.0

        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            # Find samples in this bin
            in_bin = (predicted > bin_lower) & (predicted <= bin_upper)

            if np.sum(in_bin) > 0:
                # Calculate average confidence in bin
                avg_confidence = np.mean(predicted[in_bin])

                # Calculate average accuracy in bin
                avg_accuracy = np.mean(actual[in_bin])

                # Calculate bin weight (proportion of samples in bin)
                bin_weight = np.sum(in_bin) / len(predicted)

                # Add weighted absolute difference to ECE
                ece += bin_weight * abs(avg_confidence - avg_accuracy)

        return ece

    def get_calibration_stats(self) -> Dict[str, Any]:
        """
        Get calibration statistics.

        Returns:
            Dictionary containing calibration status and parameters
        """
        return {
            'is_fitted': self.is_fitted,
            'tiers': CONFIDENCE_TIERS,
            'calibrator_type': 'IsotonicRegression',
            'out_of_bounds_strategy': 'clip'
        }
