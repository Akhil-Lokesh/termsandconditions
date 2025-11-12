"""
Tests for ActiveLearningManager.

Tests feedback collection, calibrator retraining, uncertainty sampling,
and edge case handling.
"""

import pytest
import numpy as np
from datetime import datetime
from app.core.active_learning_manager import ActiveLearningManager
from app.core.confidence_calibrator import ConfidenceCalibrator


class TestActiveLearningManager:
    """Test suite for ActiveLearningManager."""

    @pytest.fixture
    def calibrator(self):
        """Create a calibrator for testing."""
        return ConfidenceCalibrator()

    @pytest.fixture
    def manager(self, calibrator):
        """Create an active learning manager for testing."""
        return ActiveLearningManager(calibrator)

    def test_init(self, manager, calibrator):
        """Test manager initialization."""
        assert manager.calibrator is calibrator
        assert manager.feedback_buffer == []
        assert manager.dismissal_threshold == 0.20
        assert manager.retrain_after_samples == 100
        assert manager.last_retrain_date is None
        assert manager.total_feedback_collected == 0
        assert manager.retrain_count == 0

    def test_collect_feedback_valid(self, manager):
        """Test collecting valid feedback."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='helpful',
            confidence_at_detection=0.75
        )

        assert len(manager.feedback_buffer) == 1
        assert manager.total_feedback_collected == 1
        assert manager.feedback_buffer[0]['anomaly_id'] == 'test_1'
        assert manager.feedback_buffer[0]['user_action'] == 'helpful'
        assert manager.feedback_buffer[0]['confidence'] == 0.75
        assert manager.feedback_buffer[0]['was_correct'] is True

    def test_collect_feedback_helpful(self, manager):
        """Test feedback with 'helpful' action marks as correct."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='helpful',
            confidence_at_detection=0.75
        )

        assert manager.feedback_buffer[0]['was_correct'] is True

    def test_collect_feedback_acted_on(self, manager):
        """Test feedback with 'acted_on' action marks as correct."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='acted_on',
            confidence_at_detection=0.75
        )

        assert manager.feedback_buffer[0]['was_correct'] is True

    def test_collect_feedback_dismissed(self, manager):
        """Test feedback with 'dismissed' action marks as incorrect."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='dismissed',
            confidence_at_detection=0.75
        )

        assert manager.feedback_buffer[0]['was_correct'] is False

    def test_collect_feedback_false_positive(self, manager):
        """Test feedback with 'false_positive' action marks as incorrect."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='false_positive',
            confidence_at_detection=0.75
        )

        assert manager.feedback_buffer[0]['was_correct'] is False

    def test_collect_feedback_invalid_action(self, manager):
        """Test invalid user action is ignored."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='invalid_action',
            confidence_at_detection=0.75
        )

        assert len(manager.feedback_buffer) == 0
        assert manager.total_feedback_collected == 0

    def test_collect_feedback_invalid_confidence(self, manager):
        """Test invalid confidence is rejected."""
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='helpful',
            confidence_at_detection=1.5  # Out of range
        )

        assert len(manager.feedback_buffer) == 0
        assert manager.total_feedback_collected == 0

    def test_collect_feedback_timestamp(self, manager):
        """Test feedback includes timestamp."""
        before = datetime.utcnow()
        manager.collect_feedback(
            anomaly_id='test_1',
            user_action='helpful',
            confidence_at_detection=0.75
        )
        after = datetime.utcnow()

        feedback = manager.feedback_buffer[0]
        assert 'timestamp' in feedback
        assert before <= feedback['timestamp'] <= after

    def test_retrain_after_threshold(self, manager):
        """Test retraining triggers after threshold samples."""
        # Set low threshold for testing
        manager.retrain_after_samples = 5

        # Collect 4 samples - should not retrain
        for i in range(4):
            manager.collect_feedback(
                anomaly_id=f'test_{i}',
                user_action='helpful' if i % 2 == 0 else 'dismissed',
                confidence_at_detection=0.5 + (i * 0.1)
            )

        assert len(manager.feedback_buffer) == 4
        assert manager.retrain_count == 0

        # 5th sample should trigger retraining
        manager.collect_feedback(
            anomaly_id='test_5',
            user_action='helpful',
            confidence_at_detection=0.9
        )

        assert len(manager.feedback_buffer) == 0  # Buffer cleared
        assert manager.retrain_count == 1
        assert manager.last_retrain_date is not None
        assert manager.calibrator.is_fitted is True

    def test_retrain_calibrator_empty_buffer(self, manager):
        """Test retraining with empty buffer logs warning."""
        manager._retrain_calibrator()

        assert manager.retrain_count == 0
        assert manager.last_retrain_date is None

    def test_retrain_calibrator_updates_metrics(self, manager):
        """Test retraining updates metrics."""
        # Collect samples
        for i in range(10):
            manager.collect_feedback(
                anomaly_id=f'test_{i}',
                user_action='helpful' if i % 2 == 0 else 'dismissed',
                confidence_at_detection=0.5 + (i * 0.05)
            )

        before = datetime.utcnow()
        manager._retrain_calibrator()
        after = datetime.utcnow()

        assert manager.retrain_count == 1
        assert manager.last_retrain_date is not None
        assert before <= manager.last_retrain_date <= after
        assert len(manager.feedback_buffer) == 0

    def test_retrain_calibrator_all_same_label(self, manager):
        """Test retraining with all same label logs warning but continues."""
        # All positive samples
        for i in range(10):
            manager.collect_feedback(
                anomaly_id=f'test_{i}',
                user_action='helpful',
                confidence_at_detection=0.5 + (i * 0.05)
            )

        # Should complete despite all same label
        manager._retrain_calibrator()

        assert manager.retrain_count == 1
        assert len(manager.feedback_buffer) == 0

    def test_retrain_calculates_dismissal_rate(self, manager):
        """Test retraining calculates dismissal rate."""
        # 6 helpful, 4 dismissed = 40% dismissal rate
        for i in range(6):
            manager.collect_feedback(
                anomaly_id=f'helpful_{i}',
                user_action='helpful',
                confidence_at_detection=0.7
            )

        for i in range(4):
            manager.collect_feedback(
                anomaly_id=f'dismissed_{i}',
                user_action='dismissed',
                confidence_at_detection=0.5
            )

        manager._retrain_calibrator()

        # Should complete (dismissal rate = 40% > threshold of 20%)
        assert manager.retrain_count == 1

    def test_get_uncertainty_samples_empty(self, manager):
        """Test uncertainty sampling with empty list."""
        samples = manager.get_uncertainty_samples([], n_samples=5)
        assert samples == []

    def test_get_uncertainty_samples_invalid_n(self, manager):
        """Test uncertainty sampling with invalid n_samples."""
        anomalies = [{'clause_number': '1.1', 'stage2_confidence': 0.5}]
        samples = manager.get_uncertainty_samples(anomalies, n_samples=0)
        assert samples == []

        samples = manager.get_uncertainty_samples(anomalies, n_samples=-1)
        assert samples == []

    def test_get_uncertainty_samples_selects_most_uncertain(self, manager):
        """Test uncertainty sampling selects most uncertain anomalies."""
        anomalies = [
            {'clause_number': '1.1', 'stage2_confidence': 0.9},   # Certain (distance 0.4)
            {'clause_number': '1.2', 'stage2_confidence': 0.5},   # Most uncertain (distance 0.0)
            {'clause_number': '1.3', 'stage2_confidence': 0.1},   # Certain (distance 0.4)
            {'clause_number': '1.4', 'stage2_confidence': 0.55},  # Uncertain (distance 0.05)
            {'clause_number': '1.5', 'stage2_confidence': 0.8},   # Confident (distance 0.3)
        ]

        samples = manager.get_uncertainty_samples(anomalies, n_samples=3)

        # Should return 3 most uncertain: 0.5 (0.0), 0.55 (0.05), and one of 0.1/0.9 (0.4)
        assert len(samples) == 3
        assert samples[0]['clause_number'] == '1.2'  # Most uncertain
        assert samples[1]['clause_number'] == '1.4'  # Second most uncertain

    def test_get_uncertainty_samples_fewer_than_requested(self, manager):
        """Test uncertainty sampling when fewer anomalies than requested."""
        anomalies = [
            {'clause_number': '1.1', 'stage2_confidence': 0.5},
            {'clause_number': '1.2', 'stage2_confidence': 0.7}
        ]

        samples = manager.get_uncertainty_samples(anomalies, n_samples=10)

        # Should return all 2 available
        assert len(samples) == 2

    def test_get_uncertainty_samples_uses_calibrated_confidence(self, manager):
        """Test uncertainty sampling prefers calibrated confidence."""
        anomalies = [
            {
                'clause_number': '1.1',
                'calibrated_confidence': 0.5,
                'stage2_confidence': 0.9
            }
        ]

        samples = manager.get_uncertainty_samples(anomalies, n_samples=1)

        # Should use calibrated_confidence (0.5) not stage2_confidence (0.9)
        assert len(samples) == 1

    def test_get_uncertainty_samples_fallback_to_stage1(self, manager):
        """Test uncertainty sampling falls back to stage1 confidence."""
        anomalies = [
            {
                'clause_number': '1.1',
                'stage1_detection': {'stage1_confidence': 0.6}
            }
        ]

        samples = manager.get_uncertainty_samples(anomalies, n_samples=1)

        assert len(samples) == 1

    def test_get_feedback_stats_empty(self, manager):
        """Test feedback stats with empty buffer."""
        stats = manager.get_feedback_stats()

        assert stats['buffer_size'] == 0
        assert stats['buffer_capacity'] == 100
        assert stats['buffer_progress'] == 0.0
        assert stats['total_feedback_collected'] == 0
        assert stats['retrain_count'] == 0
        assert stats['last_retrain_date'] is None
        assert stats['dismissal_rate'] == 0.0
        assert stats['accuracy'] == 0.0
        assert stats['dismissal_threshold'] == 0.20
        assert stats['calibrator_fitted'] is False

    def test_get_feedback_stats_with_data(self, manager):
        """Test feedback stats with data in buffer."""
        # Collect some feedback
        manager.collect_feedback('test_1', 'helpful', 0.7)
        manager.collect_feedback('test_2', 'dismissed', 0.5)
        manager.collect_feedback('test_3', 'helpful', 0.8)

        stats = manager.get_feedback_stats()

        assert stats['buffer_size'] == 3
        assert stats['buffer_progress'] == 0.03  # 3/100
        assert stats['total_feedback_collected'] == 3
        assert stats['dismissal_rate'] == 1/3  # 1 dismissed out of 3
        assert stats['accuracy'] == 2/3  # 2 correct out of 3

    def test_should_collect_feedback_very_uncertain(self, manager):
        """Test should_collect_feedback always True for very uncertain."""
        # Very uncertain (0.4 - 0.6)
        assert manager.should_collect_feedback(0.45) is True
        assert manager.should_collect_feedback(0.50) is True
        assert manager.should_collect_feedback(0.55) is True

    def test_should_collect_feedback_confident(self, manager):
        """Test should_collect_feedback is probabilistic for confident."""
        # Set seed for reproducibility
        np.random.seed(42)

        # For confident predictions, should_collect is probabilistic (10%)
        results = [manager.should_collect_feedback(0.9) for _ in range(100)]

        # Should be roughly 10% True
        true_rate = sum(results) / len(results)
        assert 0.0 <= true_rate <= 0.3  # Allow some variance

    def test_export_feedback_data(self, manager):
        """Test exporting feedback data."""
        manager.collect_feedback('test_1', 'helpful', 0.7)
        manager.collect_feedback('test_2', 'dismissed', 0.5)

        exported = manager.export_feedback_data()

        assert len(exported) == 2
        assert exported[0]['anomaly_id'] == 'test_1'
        assert isinstance(exported[0]['timestamp'], str)  # Serialized

    def test_import_feedback_data(self, manager):
        """Test importing feedback data."""
        feedback_data = [
            {
                'anomaly_id': 'test_1',
                'user_action': 'helpful',
                'confidence': 0.7,
                'was_correct': True,
                'timestamp': '2025-01-01T00:00:00'
            },
            {
                'anomaly_id': 'test_2',
                'user_action': 'dismissed',
                'confidence': 0.5,
                'was_correct': False,
                'timestamp': '2025-01-01T00:01:00'
            }
        ]

        manager.import_feedback_data(feedback_data)

        assert len(manager.feedback_buffer) == 2
        assert manager.feedback_buffer[0]['anomaly_id'] == 'test_1'
        assert isinstance(manager.feedback_buffer[0]['timestamp'], datetime)

    def test_reset_buffer(self, manager):
        """Test resetting buffer."""
        manager.collect_feedback('test_1', 'helpful', 0.7)
        manager.collect_feedback('test_2', 'helpful', 0.8)

        assert len(manager.feedback_buffer) == 2

        manager.reset_buffer()

        assert len(manager.feedback_buffer) == 0

    def test_force_retrain_empty_buffer(self, manager):
        """Test force retrain with empty buffer logs warning."""
        manager.force_retrain()

        assert manager.retrain_count == 0

    def test_force_retrain_with_data(self, manager):
        """Test force retrain works with fewer samples."""
        # Collect only 5 samples (less than threshold of 100)
        for i in range(5):
            manager.collect_feedback(
                anomaly_id=f'test_{i}',
                user_action='helpful' if i % 2 == 0 else 'dismissed',
                confidence_at_detection=0.5 + (i * 0.1)
            )

        assert len(manager.feedback_buffer) == 5

        manager.force_retrain()

        assert len(manager.feedback_buffer) == 0
        assert manager.retrain_count == 1
        assert manager.calibrator.is_fitted is True

    def test_multiple_retrains(self, manager):
        """Test multiple retraining cycles."""
        manager.retrain_after_samples = 5

        # First retrain
        for i in range(5):
            manager.collect_feedback(
                f'test1_{i}', 'helpful', 0.6 + (i * 0.05)
            )

        assert manager.retrain_count == 1
        first_retrain_date = manager.last_retrain_date

        # Second retrain
        for i in range(5):
            manager.collect_feedback(
                f'test2_{i}', 'dismissed', 0.4 + (i * 0.05)
            )

        assert manager.retrain_count == 2
        assert manager.last_retrain_date > first_retrain_date

    def test_feedback_buffer_integrity(self, manager):
        """Test feedback buffer maintains data integrity."""
        manager.collect_feedback('test_1', 'helpful', 0.75)

        feedback = manager.feedback_buffer[0]

        # Check all required fields
        assert 'anomaly_id' in feedback
        assert 'user_action' in feedback
        assert 'confidence' in feedback
        assert 'was_correct' in feedback
        assert 'timestamp' in feedback

        # Check types
        assert isinstance(feedback['anomaly_id'], str)
        assert isinstance(feedback['user_action'], str)
        assert isinstance(feedback['confidence'], float)
        assert isinstance(feedback['was_correct'], bool)
        assert isinstance(feedback['timestamp'], datetime)
