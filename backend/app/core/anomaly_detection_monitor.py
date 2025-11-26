"""
Anomaly Detection Performance Monitor.

Monitors system performance metrics, tracks trends, and alerts on threshold violations.
Provides daily monitoring, weekly trend analysis, and calibration quality assessment.

Key Features:
- Daily performance monitoring with threshold violation alerts
- Weekly trend analysis for performance degradation detection
- Calibration quality monitoring (ECE, Brier score)
- Database-driven metrics calculation
- Scheduled monitoring tasks with APScheduler
- Comprehensive logging and alerting
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.anomaly_detector import AnomalyDetector

logger = logging.getLogger(__name__)


class AnomalyDetectionMonitor:
    """
    Performance monitor for anomaly detection system.

    Tracks daily metrics, weekly trends, and calibration quality.
    Generates alerts when performance degrades below thresholds.
    """

    # Performance thresholds for alerting
    PERFORMANCE_THRESHOLDS = {
        'false_positive_rate': 0.20,    # Max 20% false positives
        'dismissal_rate': 0.20,          # Max 20% dismissals
        'ece': 0.05,                     # Max 5% calibration error
        'avg_alerts_per_doc': 5.0,       # Target ~5 alerts per document
        'processing_time_p95': 30.0      # 95th percentile < 30 seconds
    }

    def __init__(self, db: Session):
        """
        Initialize monitor with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.detector = AnomalyDetector()
        logger.info("AnomalyDetectionMonitor initialized")

    def monitor_daily_metrics(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Monitor daily performance metrics and check against thresholds.

        Calculates key performance indicators for the specified date,
        compares against thresholds, and generates alerts for violations.

        Args:
            target_date: Date to analyze (defaults to today)

        Returns:
            Dictionary containing:
            - date: Target date
            - total_detections: Total anomalies detected
            - shown_to_users: Anomalies shown (not suppressed)
            - dismissed_count: Number dismissed by users
            - helpful_count: Number marked helpful
            - dismissal_rate: Dismissal rate (0.0-1.0)
            - helpful_rate: Helpful rate (0.0-1.0)
            - avg_alerts_per_doc: Average alerts per document
            - p95_processing_time: 95th percentile processing time (seconds)
            - alerts: List of threshold violation alerts
            - status: "HEALTHY" or "DEGRADED"
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Monitoring daily metrics for date: {target_date}")

        # Import models here to avoid circular imports
        from app.models.anomaly import Anomaly
        from app.models.document import Document

        # Query anomalies created on target date
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())

        total_detections = (
            self.db.query(func.count(Anomaly.id))
            .filter(
                Anomaly.created_at >= start_datetime,
                Anomaly.created_at <= end_datetime
            )
            .scalar() or 0
        )

        # Count shown anomalies (not in suppressed metadata)
        # For simplicity, assume all stored anomalies were shown
        # In production, track suppressed_count separately
        shown_to_users = total_detections

        # Get feedback stats from active learning manager
        feedback_stats = self.detector.active_learning.get_feedback_stats()

        # Calculate feedback metrics
        dismissed_count = 0
        helpful_count = 0
        false_positive_count = 0
        acted_on_count = 0

        # Iterate through feedback buffer to count actions
        for feedback in self.detector.active_learning.feedback_buffer:
            action = feedback.get('user_action', '')
            if action == 'dismissed':
                dismissed_count += 1
            elif action == 'helpful':
                helpful_count += 1
            elif action == 'false_positive':
                false_positive_count += 1
            elif action == 'acted_on':
                acted_on_count += 1

        # Calculate rates
        total_feedback = feedback_stats['total_feedback_collected']
        dismissal_rate = feedback_stats['dismissal_rate']
        helpful_rate = (
            (helpful_count + acted_on_count) / total_feedback
            if total_feedback > 0 else 0.0
        )
        false_positive_rate = (
            false_positive_count / total_feedback
            if total_feedback > 0 else 0.0
        )

        # Get documents analyzed today
        documents_analyzed = (
            self.db.query(func.count(Document.id))
            .filter(
                Document.created_at >= start_datetime,
                Document.created_at <= end_datetime
            )
            .scalar() or 0
        )

        # Calculate average alerts per document
        avg_alerts_per_doc = (
            total_detections / documents_analyzed
            if documents_analyzed > 0 else 0.0
        )

        # Calculate 95th percentile processing time
        # For now, use placeholder - in production, track in metrics table
        p95_processing_time = self._calculate_p95_processing_time(
            start_datetime, end_datetime
        )

        # Get calibration quality
        calibration_quality = self.get_calibration_quality()
        ece = calibration_quality.get('expected_calibration_error')

        # Check thresholds and generate alerts
        alerts = []
        status = "HEALTHY"

        if false_positive_rate > self.PERFORMANCE_THRESHOLDS['false_positive_rate']:
            alert = {
                'severity': 'HIGH',
                'metric': 'false_positive_rate',
                'value': false_positive_rate,
                'threshold': self.PERFORMANCE_THRESHOLDS['false_positive_rate'],
                'message': (
                    f"False positive rate ({false_positive_rate:.1%}) exceeds "
                    f"threshold ({self.PERFORMANCE_THRESHOLDS['false_positive_rate']:.1%})"
                )
            }
            alerts.append(alert)
            status = "DEGRADED"
            logger.warning(alert['message'])

        if dismissal_rate > self.PERFORMANCE_THRESHOLDS['dismissal_rate']:
            alert = {
                'severity': 'MEDIUM',
                'metric': 'dismissal_rate',
                'value': dismissal_rate,
                'threshold': self.PERFORMANCE_THRESHOLDS['dismissal_rate'],
                'message': (
                    f"Dismissal rate ({dismissal_rate:.1%}) exceeds "
                    f"threshold ({self.PERFORMANCE_THRESHOLDS['dismissal_rate']:.1%})"
                )
            }
            alerts.append(alert)
            status = "DEGRADED"
            logger.warning(alert['message'])

        if ece and ece > self.PERFORMANCE_THRESHOLDS['ece']:
            alert = {
                'severity': 'MEDIUM',
                'metric': 'expected_calibration_error',
                'value': ece,
                'threshold': self.PERFORMANCE_THRESHOLDS['ece'],
                'message': (
                    f"Expected Calibration Error ({ece:.3f}) exceeds "
                    f"threshold ({self.PERFORMANCE_THRESHOLDS['ece']:.3f})"
                )
            }
            alerts.append(alert)
            status = "DEGRADED"
            logger.warning(alert['message'])

        if avg_alerts_per_doc > self.PERFORMANCE_THRESHOLDS['avg_alerts_per_doc'] * 2:
            # Alert if more than 2x target (10 alerts per doc)
            alert = {
                'severity': 'LOW',
                'metric': 'avg_alerts_per_doc',
                'value': avg_alerts_per_doc,
                'threshold': self.PERFORMANCE_THRESHOLDS['avg_alerts_per_doc'] * 2,
                'message': (
                    f"Average alerts per document ({avg_alerts_per_doc:.1f}) "
                    f"is significantly above target ({self.PERFORMANCE_THRESHOLDS['avg_alerts_per_doc']:.1f})"
                )
            }
            alerts.append(alert)
            logger.warning(alert['message'])

        if p95_processing_time > self.PERFORMANCE_THRESHOLDS['processing_time_p95']:
            alert = {
                'severity': 'LOW',
                'metric': 'processing_time_p95',
                'value': p95_processing_time,
                'threshold': self.PERFORMANCE_THRESHOLDS['processing_time_p95'],
                'message': (
                    f"P95 processing time ({p95_processing_time:.1f}s) exceeds "
                    f"threshold ({self.PERFORMANCE_THRESHOLDS['processing_time_p95']:.1f}s)"
                )
            }
            alerts.append(alert)
            logger.warning(alert['message'])

        # Build results
        results = {
            'date': target_date.isoformat(),
            'total_detections': total_detections,
            'shown_to_users': shown_to_users,
            'documents_analyzed': documents_analyzed,
            'dismissed_count': dismissed_count,
            'helpful_count': helpful_count + acted_on_count,
            'false_positive_count': false_positive_count,
            'dismissal_rate': dismissal_rate,
            'helpful_rate': helpful_rate,
            'false_positive_rate': false_positive_rate,
            'avg_alerts_per_doc': round(avg_alerts_per_doc, 2),
            'p95_processing_time': round(p95_processing_time, 2),
            'expected_calibration_error': ece,
            'alerts': alerts,
            'status': status
        }

        logger.info(
            f"Daily metrics for {target_date}: "
            f"{total_detections} detections, "
            f"{dismissal_rate:.1%} dismissal rate, "
            f"{helpful_rate:.1%} helpful rate, "
            f"status: {status}"
        )

        return results

    def get_weekly_trends(self, weeks: int = 4) -> Dict[str, Any]:
        """
        Analyze performance trends over multiple weeks.

        Calculates weekly aggregates and identifies trends in key metrics
        to detect performance degradation or improvement over time.

        Args:
            weeks: Number of weeks to analyze (default: 4)

        Returns:
            Dictionary containing:
            - start_date: Analysis start date
            - end_date: Analysis end date
            - weekly_data: List of weekly metric snapshots
            - trends: Trend analysis (improving/degrading/stable)
            - recommendations: Suggested actions based on trends
        """
        logger.info(f"Analyzing weekly trends for past {weeks} weeks")

        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)

        # Import models
        from app.models.anomaly import Anomaly
        from app.models.document import Document

        weekly_data = []

        # Analyze each week
        for week_offset in range(weeks):
            week_end = end_date - timedelta(weeks=week_offset)
            week_start = week_end - timedelta(days=7)

            week_start_dt = datetime.combine(week_start, datetime.min.time())
            week_end_dt = datetime.combine(week_end, datetime.max.time())

            # Query weekly metrics
            total_detections = (
                self.db.query(func.count(Anomaly.id))
                .filter(
                    Anomaly.created_at >= week_start_dt,
                    Anomaly.created_at <= week_end_dt
                )
                .scalar() or 0
            )

            documents_analyzed = (
                self.db.query(func.count(Document.id))
                .filter(
                    Document.created_at >= week_start_dt,
                    Document.created_at <= week_end_dt
                )
                .scalar() or 0
            )

            avg_alerts = (
                total_detections / documents_analyzed
                if documents_analyzed > 0 else 0.0
            )

            weekly_data.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'total_detections': total_detections,
                'documents_analyzed': documents_analyzed,
                'avg_alerts_per_doc': round(avg_alerts, 2)
            })

        # Reverse to chronological order
        weekly_data.reverse()

        # Analyze trends
        trends = self._analyze_trends(weekly_data)
        recommendations = self._generate_recommendations(trends)

        results = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'weeks_analyzed': weeks,
            'weekly_data': weekly_data,
            'trends': trends,
            'recommendations': recommendations
        }

        logger.info(
            f"Weekly trends analyzed: {weeks} weeks, "
            f"trend status: {trends.get('overall_trend', 'unknown')}"
        )

        return results

    def get_calibration_quality(self) -> Dict[str, Any]:
        """
        Assess confidence calibration quality.

        Evaluates how well the confidence calibrator is performing
        by analyzing ECE, Brier score, and calibration curve.

        Returns:
            Dictionary containing:
            - is_fitted: Whether calibrator is trained
            - expected_calibration_error: ECE score (if available)
            - brier_score_before: Brier score before calibration
            - brier_score_after: Brier score after calibration
            - brier_improvement: Improvement percentage
            - total_feedback_samples: Number of feedback samples
            - retrain_count: Number of retraining iterations
            - last_retrain_date: Last retraining date
            - calibration_status: "GOOD" | "NEEDS_ATTENTION" | "NOT_FITTED"
        """
        logger.info("Assessing calibration quality")

        calibrator = self.detector.confidence_calibrator
        feedback_stats = self.detector.active_learning.get_feedback_stats()

        if not calibrator.is_fitted:
            logger.warning("Calibrator not fitted yet")
            return {
                'is_fitted': False,
                'expected_calibration_error': None,
                'brier_score_before': None,
                'brier_score_after': None,
                'brier_improvement': None,
                'total_feedback_samples': feedback_stats['total_feedback_collected'],
                'retrain_count': feedback_stats['retrain_count'],
                'last_retrain_date': feedback_stats['last_retrain_date'],
                'calibration_status': 'NOT_FITTED'
            }

        # Get ECE from calibrator metrics
        # Note: Need to add getter method to ConfidenceCalibrator
        # For now, use None as placeholder
        ece = getattr(calibrator, 'last_ece', None)
        brier_before = getattr(calibrator, 'brier_score_before', None)
        brier_after = getattr(calibrator, 'brier_score_after', None)

        # Calculate improvement if both scores available
        brier_improvement = None
        if brier_before and brier_after:
            brier_improvement = (
                ((brier_before - brier_after) / brier_before) * 100
                if brier_before > 0 else 0.0
            )

        # Determine calibration status
        calibration_status = "GOOD"
        if ece and ece > self.PERFORMANCE_THRESHOLDS['ece']:
            calibration_status = "NEEDS_ATTENTION"

        results = {
            'is_fitted': True,
            'expected_calibration_error': round(ece, 4) if ece else None,
            'brier_score_before': round(brier_before, 4) if brier_before else None,
            'brier_score_after': round(brier_after, 4) if brier_after else None,
            'brier_improvement': round(brier_improvement, 2) if brier_improvement else None,
            'total_feedback_samples': feedback_stats['total_feedback_collected'],
            'retrain_count': feedback_stats['retrain_count'],
            'last_retrain_date': feedback_stats['last_retrain_date'],
            'calibration_status': calibration_status
        }

        logger.info(
            f"Calibration quality: status={calibration_status}, "
            f"ECE={ece:.4f if ece else 'N/A'}, "
            f"samples={feedback_stats['total_feedback_collected']}"
        )

        return results

    def _calculate_p95_processing_time(
        self,
        start_datetime: datetime,
        end_datetime: datetime
    ) -> float:
        """
        Calculate 95th percentile processing time for date range.

        In production, this would query a metrics table tracking
        processing times. For now, returns a placeholder value.

        Args:
            start_datetime: Start of date range
            end_datetime: End of date range

        Returns:
            95th percentile processing time in seconds
        """
        # TODO: Implement actual processing time tracking in database
        # For now, return a reasonable placeholder
        # In production, query: SELECT processing_time_ms FROM metrics
        # WHERE created_at BETWEEN start AND end
        # Then calculate: np.percentile(times, 95) / 1000

        return 5.0  # Placeholder: 5 seconds

    def _analyze_trends(self, weekly_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze trends in weekly data.

        Uses simple linear regression to detect improving or degrading trends.

        Args:
            weekly_data: List of weekly metric snapshots

        Returns:
            Dictionary with trend analysis for key metrics
        """
        if len(weekly_data) < 2:
            return {'overall_trend': 'INSUFFICIENT_DATA'}

        # Extract time series
        avg_alerts = [w['avg_alerts_per_doc'] for w in weekly_data]
        detections = [w['total_detections'] for w in weekly_data]

        # Calculate simple trends (increasing/decreasing/stable)
        def trend_direction(values: List[float]) -> str:
            if len(values) < 2:
                return 'STABLE'

            # Compare first half to second half
            mid = len(values) // 2
            first_half = np.mean(values[:mid]) if mid > 0 else values[0]
            second_half = np.mean(values[mid:])

            change_pct = ((second_half - first_half) / first_half * 100
                         if first_half > 0 else 0)

            if abs(change_pct) < 10:
                return 'STABLE'
            elif change_pct > 0:
                return 'INCREASING'
            else:
                return 'DECREASING'

        alerts_trend = trend_direction(avg_alerts)
        detections_trend = trend_direction(detections)

        # Determine overall trend
        overall_trend = 'STABLE'
        if alerts_trend == 'INCREASING':
            overall_trend = 'DEGRADING'  # More alerts = potential issue
        elif alerts_trend == 'DECREASING' and detections_trend == 'STABLE':
            overall_trend = 'IMPROVING'  # Fewer alerts, stable detections = better quality

        return {
            'overall_trend': overall_trend,
            'avg_alerts_trend': alerts_trend,
            'detections_trend': detections_trend,
            'weeks_analyzed': len(weekly_data)
        }

    def _generate_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on trend analysis.

        Args:
            trends: Trend analysis results

        Returns:
            List of recommended actions
        """
        recommendations = []

        overall_trend = trends.get('overall_trend', 'STABLE')

        if overall_trend == 'DEGRADING':
            recommendations.append(
                "Performance is degrading. Review recent changes to detection rules."
            )
            recommendations.append(
                "Consider retraining confidence calibrator with recent feedback."
            )
            recommendations.append(
                "Check for changes in document types or industries being analyzed."
            )

        elif overall_trend == 'IMPROVING':
            recommendations.append(
                "Performance is improving. Continue current approach."
            )
            recommendations.append(
                "Consider documenting successful practices for future reference."
            )

        else:  # STABLE or INSUFFICIENT_DATA
            recommendations.append(
                "Performance is stable. Continue monitoring."
            )

        alerts_trend = trends.get('avg_alerts_trend')
        if alerts_trend == 'INCREASING':
            recommendations.append(
                "Alert volume is increasing. Review alert ranking thresholds."
            )

        return recommendations


# === Scheduled Monitoring Tasks ===

def setup_monitoring_scheduler(db_session_factory):
    """
    Setup APScheduler to run monitoring tasks.

    Schedules daily performance monitoring at 1 AM UTC.

    Args:
        db_session_factory: Factory function to create DB sessions

    Returns:
        Configured scheduler instance
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = BackgroundScheduler()

    def run_daily_monitoring():
        """Run daily monitoring task."""
        try:
            logger.info("Starting scheduled daily monitoring")
            db = db_session_factory()
            monitor = AnomalyDetectionMonitor(db)

            # Run daily metrics
            results = monitor.monitor_daily_metrics()

            # Log results
            if results['status'] == 'DEGRADED':
                logger.error(
                    f"Daily monitoring: DEGRADED status with {len(results['alerts'])} alerts"
                )
                for alert in results['alerts']:
                    logger.error(f"  - {alert['message']}")
            else:
                logger.info(
                    f"Daily monitoring: HEALTHY status, "
                    f"{results['total_detections']} detections, "
                    f"{results['dismissal_rate']:.1%} dismissal rate"
                )

            db.close()

        except Exception as e:
            logger.error(f"Error in scheduled daily monitoring: {e}", exc_info=True)

    # Schedule daily at 1 AM UTC
    scheduler.add_job(
        run_daily_monitoring,
        trigger=CronTrigger(hour=1, minute=0),
        id='daily_monitoring',
        name='Daily Anomaly Detection Monitoring',
        replace_existing=True
    )

    logger.info("Monitoring scheduler configured (runs daily at 1 AM UTC)")

    return scheduler
