"""
Tests for AnomalyDetectionMonitor.

Tests daily monitoring, weekly trends, calibration quality assessment,
and scheduled task setup.
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import numpy as np

from app.core.anomaly_detection_monitor import AnomalyDetectionMonitor, setup_monitoring_scheduler


class TestAnomalyDetectionMonitor:
    """Test suite for AnomalyDetectionMonitor."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        return db

    @pytest.fixture
    def mock_detector(self):
        """Create mock anomaly detector."""
        detector = Mock()

        # Mock confidence calibrator
        calibrator = Mock()
        calibrator.is_fitted = True
        calibrator.last_ece = 0.03
        calibrator.brier_score_before = 0.25
        calibrator.brier_score_after = 0.15
        detector.confidence_calibrator = calibrator

        # Mock active learning manager
        active_learning = Mock()
        active_learning.get_feedback_stats.return_value = {
            'buffer_size': 50,
            'total_feedback_collected': 200,
            'retrain_count': 2,
            'last_retrain_date': '2025-01-10',
            'dismissal_rate': 0.15,
            'accuracy': 0.85,
            'calibrator_fitted': True
        }
        active_learning.feedback_buffer = [
            {'user_action': 'helpful', 'confidence': 0.8},
            {'user_action': 'dismissed', 'confidence': 0.6},
            {'user_action': 'acted_on', 'confidence': 0.9},
            {'user_action': 'false_positive', 'confidence': 0.5},
        ] * 50  # 200 total feedback items
        detector.active_learning = active_learning

        return detector

    @pytest.fixture
    def monitor(self, mock_db, mock_detector):
        """Create monitor instance with mocks."""
        with patch('app.core.anomaly_detection_monitor.AnomalyDetector', return_value=mock_detector):
            monitor = AnomalyDetectionMonitor(mock_db)
            return monitor

    def test_initialization(self, mock_db, mock_detector):
        """Test monitor initialization."""
        with patch('app.core.anomaly_detection_monitor.AnomalyDetector', return_value=mock_detector):
            monitor = AnomalyDetectionMonitor(mock_db)

            assert monitor.db == mock_db
            assert monitor.detector == mock_detector
            assert monitor.PERFORMANCE_THRESHOLDS['false_positive_rate'] == 0.20
            assert monitor.PERFORMANCE_THRESHOLDS['dismissal_rate'] == 0.20
            assert monitor.PERFORMANCE_THRESHOLDS['ece'] == 0.05
            assert monitor.PERFORMANCE_THRESHOLDS['avg_alerts_per_doc'] == 5.0
            assert monitor.PERFORMANCE_THRESHOLDS['processing_time_p95'] == 30.0

    def test_monitor_daily_metrics_healthy(self, monitor, mock_db):
        """Test daily monitoring with healthy metrics."""
        target_date = date(2025, 1, 15)

        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.scalar.side_effect = [
            100,  # total_detections
            10,   # documents_analyzed
        ]
        mock_db.query.return_value = mock_query

        # Mock p95 calculation
        with patch.object(monitor, '_calculate_p95_processing_time', return_value=5.0):
            # Mock calibration quality
            with patch.object(monitor, 'get_calibration_quality', return_value={
                'expected_calibration_error': 0.03
            }):
                results = monitor.monitor_daily_metrics(target_date)

        # Verify results structure
        assert results['date'] == '2025-01-15'
        assert results['total_detections'] == 100
        assert results['documents_analyzed'] == 10
        assert results['avg_alerts_per_doc'] == 10.0
        assert results['p95_processing_time'] == 5.0
        assert results['status'] == 'HEALTHY'
        assert len(results['alerts']) == 0

    def test_monitor_daily_metrics_degraded_dismissal_rate(self, monitor, mock_db):
        """Test daily monitoring with high dismissal rate."""
        target_date = date(2025, 1, 15)

        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.scalar.side_effect = [
            100,  # total_detections
            10,   # documents_analyzed
        ]
        mock_db.query.return_value = mock_query

        # Mock high dismissal rate
        monitor.detector.active_learning.get_feedback_stats.return_value = {
            'buffer_size': 50,
            'total_feedback_collected': 200,
            'retrain_count': 2,
            'last_retrain_date': '2025-01-10',
            'dismissal_rate': 0.35,  # Above threshold
            'accuracy': 0.65,
            'calibrator_fitted': True
        }

        # Mock p95 calculation
        with patch.object(monitor, '_calculate_p95_processing_time', return_value=5.0):
            # Mock calibration quality
            with patch.object(monitor, 'get_calibration_quality', return_value={
                'expected_calibration_error': 0.03
            }):
                results = monitor.monitor_daily_metrics(target_date)

        # Should be degraded due to high dismissal rate
        assert results['status'] == 'DEGRADED'
        assert len(results['alerts']) > 0

        # Find dismissal rate alert
        dismissal_alert = next(
            (a for a in results['alerts'] if a['metric'] == 'dismissal_rate'),
            None
        )
        assert dismissal_alert is not None
        assert dismissal_alert['severity'] == 'MEDIUM'
        assert dismissal_alert['value'] == 0.35

    def test_monitor_daily_metrics_high_ece(self, monitor, mock_db):
        """Test daily monitoring with high ECE."""
        target_date = date(2025, 1, 15)

        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.scalar.side_effect = [
            100,  # total_detections
            10,   # documents_analyzed
        ]
        mock_db.query.return_value = mock_query

        # Mock p95 calculation
        with patch.object(monitor, '_calculate_p95_processing_time', return_value=5.0):
            # Mock high ECE
            with patch.object(monitor, 'get_calibration_quality', return_value={
                'expected_calibration_error': 0.08  # Above threshold
            }):
                results = monitor.monitor_daily_metrics(target_date)

        # Should be degraded due to high ECE
        assert results['status'] == 'DEGRADED'

        # Find ECE alert
        ece_alert = next(
            (a for a in results['alerts'] if a['metric'] == 'expected_calibration_error'),
            None
        )
        assert ece_alert is not None
        assert ece_alert['severity'] == 'MEDIUM'

    def test_monitor_daily_metrics_high_processing_time(self, monitor, mock_db):
        """Test daily monitoring with high processing time."""
        target_date = date(2025, 1, 15)

        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.scalar.side_effect = [
            100,  # total_detections
            10,   # documents_analyzed
        ]
        mock_db.query.return_value = mock_query

        # Mock high p95 processing time
        with patch.object(monitor, '_calculate_p95_processing_time', return_value=45.0):
            # Mock calibration quality
            with patch.object(monitor, 'get_calibration_quality', return_value={
                'expected_calibration_error': 0.03
            }):
                results = monitor.monitor_daily_metrics(target_date)

        # Find processing time alert
        time_alert = next(
            (a for a in results['alerts'] if a['metric'] == 'processing_time_p95'),
            None
        )
        assert time_alert is not None
        assert time_alert['severity'] == 'LOW'
        assert time_alert['value'] == 45.0

    def test_monitor_daily_metrics_default_date(self, monitor, mock_db):
        """Test daily monitoring defaults to today."""
        # Mock database queries
        mock_query = Mock()
        mock_query.filter.return_value.scalar.side_effect = [
            50,   # total_detections
            10,   # documents_analyzed
        ]
        mock_db.query.return_value = mock_query

        # Mock dependencies
        with patch.object(monitor, '_calculate_p95_processing_time', return_value=5.0):
            with patch.object(monitor, 'get_calibration_quality', return_value={
                'expected_calibration_error': 0.03
            }):
                results = monitor.monitor_daily_metrics()

        # Should use today's date
        assert results['date'] == date.today().isoformat()

    def test_get_weekly_trends(self, monitor, mock_db):
        """Test weekly trend analysis."""
        # Mock database queries for 4 weeks
        total_detections = [80, 90, 100, 110]
        documents_analyzed = [20, 22, 25, 28]

        call_count = [0]
        def mock_scalar():
            result = total_detections[call_count[0] // 2] if call_count[0] % 2 == 0 else documents_analyzed[call_count[0] // 2]
            call_count[0] += 1
            return result

        mock_query = Mock()
        mock_query.filter.return_value.scalar = mock_scalar
        mock_db.query.return_value = mock_query

        results = monitor.get_weekly_trends(weeks=4)

        # Verify structure
        assert 'start_date' in results
        assert 'end_date' in results
        assert results['weeks_analyzed'] == 4
        assert len(results['weekly_data']) == 4

        # Verify weekly data
        for week_data in results['weekly_data']:
            assert 'week_start' in week_data
            assert 'week_end' in week_data
            assert 'total_detections' in week_data
            assert 'documents_analyzed' in week_data
            assert 'avg_alerts_per_doc' in week_data

        # Verify trends
        assert 'trends' in results
        assert 'overall_trend' in results['trends']

        # Verify recommendations
        assert 'recommendations' in results
        assert isinstance(results['recommendations'], list)
        assert len(results['recommendations']) > 0

    def test_get_weekly_trends_increasing(self, monitor, mock_db):
        """Test trend detection for increasing alerts."""
        # Mock increasing detections
        total_detections = [50, 100, 150, 200]
        documents_analyzed = [10, 10, 10, 10]

        call_count = [0]
        def mock_scalar():
            result = total_detections[call_count[0] // 2] if call_count[0] % 2 == 0 else documents_analyzed[call_count[0] // 2]
            call_count[0] += 1
            return result

        mock_query = Mock()
        mock_query.filter.return_value.scalar = mock_scalar
        mock_db.query.return_value = mock_query

        results = monitor.get_weekly_trends(weeks=4)

        # Should detect increasing trend
        assert results['trends']['avg_alerts_trend'] == 'INCREASING'

    def test_get_calibration_quality_fitted(self, monitor):
        """Test calibration quality assessment when fitted."""
        results = monitor.get_calibration_quality()

        assert results['is_fitted'] is True
        assert results['expected_calibration_error'] == 0.03
        assert results['brier_score_before'] == 0.25
        assert results['brier_score_after'] == 0.15
        assert results['brier_improvement'] == 40.0  # (0.25 - 0.15) / 0.25 * 100
        assert results['total_feedback_samples'] == 200
        assert results['retrain_count'] == 2
        assert results['last_retrain_date'] == '2025-01-10'
        assert results['calibration_status'] == 'GOOD'

    def test_get_calibration_quality_not_fitted(self, monitor):
        """Test calibration quality when calibrator not fitted."""
        # Mock unfitted calibrator
        monitor.detector.confidence_calibrator.is_fitted = False

        results = monitor.get_calibration_quality()

        assert results['is_fitted'] is False
        assert results['expected_calibration_error'] is None
        assert results['brier_score_before'] is None
        assert results['brier_score_after'] is None
        assert results['brier_improvement'] is None
        assert results['calibration_status'] == 'NOT_FITTED'

    def test_get_calibration_quality_needs_attention(self, monitor):
        """Test calibration quality with high ECE."""
        # Mock high ECE
        monitor.detector.confidence_calibrator.last_ece = 0.08

        results = monitor.get_calibration_quality()

        assert results['calibration_status'] == 'NEEDS_ATTENTION'

    def test_calculate_p95_processing_time(self, monitor):
        """Test P95 processing time calculation."""
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 2)

        # Currently returns placeholder
        result = monitor._calculate_p95_processing_time(start, end)

        assert isinstance(result, float)
        assert result >= 0

    def test_analyze_trends_increasing(self, monitor):
        """Test trend analysis for increasing values."""
        weekly_data = [
            {'avg_alerts_per_doc': 3.0, 'total_detections': 100},
            {'avg_alerts_per_doc': 4.0, 'total_detections': 110},
            {'avg_alerts_per_doc': 5.0, 'total_detections': 120},
            {'avg_alerts_per_doc': 6.0, 'total_detections': 130},
        ]

        trends = monitor._analyze_trends(weekly_data)

        assert trends['avg_alerts_trend'] == 'INCREASING'
        assert trends['overall_trend'] == 'DEGRADING'

    def test_analyze_trends_decreasing(self, monitor):
        """Test trend analysis for decreasing values."""
        weekly_data = [
            {'avg_alerts_per_doc': 6.0, 'total_detections': 100},
            {'avg_alerts_per_doc': 5.0, 'total_detections': 100},
            {'avg_alerts_per_doc': 4.0, 'total_detections': 100},
            {'avg_alerts_per_doc': 3.0, 'total_detections': 100},
        ]

        trends = monitor._analyze_trends(weekly_data)

        assert trends['avg_alerts_trend'] == 'DECREASING'
        assert trends['overall_trend'] == 'IMPROVING'

    def test_analyze_trends_stable(self, monitor):
        """Test trend analysis for stable values."""
        weekly_data = [
            {'avg_alerts_per_doc': 5.0, 'total_detections': 100},
            {'avg_alerts_per_doc': 5.1, 'total_detections': 102},
            {'avg_alerts_per_doc': 4.9, 'total_detections': 98},
            {'avg_alerts_per_doc': 5.0, 'total_detections': 100},
        ]

        trends = monitor._analyze_trends(weekly_data)

        assert trends['avg_alerts_trend'] == 'STABLE'
        assert trends['overall_trend'] == 'STABLE'

    def test_analyze_trends_insufficient_data(self, monitor):
        """Test trend analysis with insufficient data."""
        weekly_data = [
            {'avg_alerts_per_doc': 5.0, 'total_detections': 100},
        ]

        trends = monitor._analyze_trends(weekly_data)

        assert trends['overall_trend'] == 'INSUFFICIENT_DATA'

    def test_generate_recommendations_degrading(self, monitor):
        """Test recommendations for degrading performance."""
        trends = {
            'overall_trend': 'DEGRADING',
            'avg_alerts_trend': 'INCREASING'
        }

        recommendations = monitor._generate_recommendations(trends)

        assert len(recommendations) > 0
        assert any('degrading' in r.lower() for r in recommendations)
        assert any('retraining' in r.lower() or 'retrain' in r.lower() for r in recommendations)
        assert any('increasing' in r.lower() for r in recommendations)

    def test_generate_recommendations_improving(self, monitor):
        """Test recommendations for improving performance."""
        trends = {
            'overall_trend': 'IMPROVING',
            'avg_alerts_trend': 'STABLE'
        }

        recommendations = monitor._generate_recommendations(trends)

        assert len(recommendations) > 0
        assert any('improving' in r.lower() for r in recommendations)

    def test_generate_recommendations_stable(self, monitor):
        """Test recommendations for stable performance."""
        trends = {
            'overall_trend': 'STABLE',
            'avg_alerts_trend': 'STABLE'
        }

        recommendations = monitor._generate_recommendations(trends)

        assert len(recommendations) > 0
        assert any('stable' in r.lower() for r in recommendations)

    def test_performance_thresholds_values(self):
        """Test performance threshold values are reasonable."""
        thresholds = AnomalyDetectionMonitor.PERFORMANCE_THRESHOLDS

        assert 0 < thresholds['false_positive_rate'] <= 1.0
        assert 0 < thresholds['dismissal_rate'] <= 1.0
        assert 0 < thresholds['ece'] <= 1.0
        assert thresholds['avg_alerts_per_doc'] > 0
        assert thresholds['processing_time_p95'] > 0


class TestScheduledMonitoring:
    """Test suite for scheduled monitoring tasks."""

    def test_setup_monitoring_scheduler(self):
        """Test scheduler setup."""
        mock_db_factory = Mock()

        with patch('app.core.anomaly_detection_monitor.BackgroundScheduler') as MockScheduler:
            mock_scheduler = Mock()
            MockScheduler.return_value = mock_scheduler

            scheduler = setup_monitoring_scheduler(mock_db_factory)

            # Verify scheduler was created
            MockScheduler.assert_called_once()

            # Verify job was added
            mock_scheduler.add_job.assert_called_once()

            # Verify job configuration
            call_args = mock_scheduler.add_job.call_args
            assert call_args[1]['id'] == 'daily_monitoring'
            assert call_args[1]['name'] == 'Daily Anomaly Detection Monitoring'
            assert call_args[1]['replace_existing'] is True

    def test_scheduled_task_runs(self):
        """Test scheduled monitoring task execution."""
        mock_db_factory = Mock()
        mock_db = Mock()
        mock_db_factory.return_value = mock_db

        with patch('app.core.anomaly_detection_monitor.BackgroundScheduler') as MockScheduler:
            with patch('app.core.anomaly_detection_monitor.AnomalyDetectionMonitor') as MockMonitor:
                mock_scheduler = Mock()
                MockScheduler.return_value = mock_scheduler

                mock_monitor = Mock()
                mock_monitor.monitor_daily_metrics.return_value = {
                    'status': 'HEALTHY',
                    'alerts': [],
                    'total_detections': 100,
                    'dismissal_rate': 0.10
                }
                MockMonitor.return_value = mock_monitor

                # Setup scheduler
                scheduler = setup_monitoring_scheduler(mock_db_factory)

                # Get the scheduled function
                scheduled_func = mock_scheduler.add_job.call_args[0][0]

                # Run it
                scheduled_func()

                # Verify monitor was created and called
                MockMonitor.assert_called_once_with(mock_db)
                mock_monitor.monitor_daily_metrics.assert_called_once()
                mock_db.close.assert_called_once()

    def test_scheduled_task_handles_errors(self):
        """Test scheduled task error handling."""
        mock_db_factory = Mock()
        mock_db = Mock()
        mock_db_factory.return_value = mock_db

        with patch('app.core.anomaly_detection_monitor.BackgroundScheduler') as MockScheduler:
            with patch('app.core.anomaly_detection_monitor.AnomalyDetectionMonitor') as MockMonitor:
                mock_scheduler = Mock()
                MockScheduler.return_value = mock_scheduler

                # Make monitor raise exception
                MockMonitor.side_effect = Exception("Database error")

                # Setup scheduler
                scheduler = setup_monitoring_scheduler(mock_db_factory)

                # Get the scheduled function
                scheduled_func = mock_scheduler.add_job.call_args[0][0]

                # Run it - should not raise exception
                try:
                    scheduled_func()
                except Exception:
                    pytest.fail("Scheduled task should handle exceptions gracefully")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
