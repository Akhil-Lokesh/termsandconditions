"""
Active learning manager for continuous model improvement.

Collects user feedback on anomaly detections and retrains the confidence
calibrator to improve accuracy over time. Implements uncertainty sampling
for targeted feedback collection.

Stage 5 of the anomaly detection pipeline: Active Learning & Feedback Loop

Persistence:
    When the ACTIVE_LEARNING_PERSIST env var is set to "true" and a
    ``db_session_factory`` is passed to ``__init__``, each call to
    ``collect_feedback`` write-throughs to the ``feedback_events`` table
    BEFORE appending to the in-memory buffer. At startup, ``hydrate_from_db``
    pulls unprocessed rows back into the buffer. This guarantees feedback
    survives server restarts.
"""

import os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone
import numpy as np
from sqlalchemy.orm import Session
from app.core.confidence_calibrator import ConfidenceCalibrator
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def _persist_enabled() -> bool:
    """Return True iff feedback persistence is feature-flag enabled."""
    return os.getenv('ACTIVE_LEARNING_PERSIST', 'false').lower() == 'true'


# Maps internal action names (used by the in-memory buffer and ConfidenceCalibrator)
# to the persisted-vocabulary action names stored in feedback_events.user_action.
_INTERNAL_TO_PERSISTED_ACTION = {
    'helpful': 'agree',
    'acted_on': 'agree',
    'dismissed': 'dismiss',
    'false_positive': 'disagree',
}

# Inverse: rows loaded from DB must be re-projected back to an internal action so
# the in-memory `was_correct` semantics stay consistent. "dismiss" / "disagree" /
# "wrong_severity" / "wrong_category" all imply the prediction was unhelpful.
_PERSISTED_TO_INTERNAL_ACTION = {
    'agree': 'helpful',
    'disagree': 'false_positive',
    'dismiss': 'dismissed',
    'wrong_severity': 'dismissed',
    'wrong_category': 'dismissed',
}


def _map_action_to_persisted(internal_action: str) -> str:
    """Translate internal action to persisted-vocabulary action, with passthrough."""
    return _INTERNAL_TO_PERSISTED_ACTION.get(internal_action, internal_action)


def _map_action_to_internal(persisted_action: str) -> str:
    """Translate persisted action back to internal action, with passthrough."""
    return _PERSISTED_TO_INTERNAL_ACTION.get(persisted_action, persisted_action)


class ActiveLearningManager:
    """
    Manages active learning and feedback collection for anomaly detection.

    Collects user feedback on detected anomalies, retrains the confidence
    calibrator when sufficient feedback is collected, and identifies
    uncertain predictions for targeted feedback collection.

    Attributes:
        calibrator: ConfidenceCalibrator instance to retrain
        feedback_buffer: List of feedback samples awaiting retraining
        dismissal_threshold: Alert threshold for dismissal rate
        retrain_after_samples: Number of samples before retraining
        last_retrain_date: Timestamp of last retraining
        total_feedback_collected: Total feedback samples collected
        retrain_count: Number of times calibrator has been retrained
    """

    def __init__(
        self,
        calibrator: ConfidenceCalibrator,
        db_session_factory: Optional[Callable[[], Session]] = None,
    ):
        """
        Initialize active learning manager.

        Args:
            calibrator: ConfidenceCalibrator instance to manage and retrain
            db_session_factory: Optional callable returning a context-manager
                SQLAlchemy Session (e.g. ``SessionLocal``). When provided AND
                ``ACTIVE_LEARNING_PERSIST=true``, ``collect_feedback`` writes
                each event to the ``feedback_events`` table before buffering
                it in memory; ``hydrate_from_db`` reloads unprocessed rows
                into the buffer at startup.
        """
        self.calibrator = calibrator
        self.feedback_buffer: List[Dict[str, Any]] = []
        self._db_session_factory = db_session_factory

        # Configuration
        self.dismissal_threshold = 0.20  # Alert if >20% dismissals
        self.retrain_after_samples = 100  # Retrain after 100 samples

        # Metrics
        self.last_retrain_date: Optional[datetime] = None
        self.total_feedback_collected = 0
        self.retrain_count = 0

        persist_flag = _persist_enabled()
        logger.info(
            f"Active learning manager initialized "
            f"(retrain_after={self.retrain_after_samples}, "
            f"dismissal_threshold={self.dismissal_threshold:.0%}, "
            f"persist={persist_flag and self._db_session_factory is not None})"
        )

    def collect_feedback(
        self,
        anomaly_id: str,
        user_action: str,
        confidence_at_detection: float,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        original_severity: Optional[str] = None,
        suggested_severity: Optional[str] = None,
    ) -> None:
        """
        Collect user feedback on an anomaly detection.

        Stores feedback in buffer and triggers retraining when sufficient
        samples are collected. When DB persistence is enabled (via the
        ``ACTIVE_LEARNING_PERSIST`` env var AND a ``db_session_factory`` was
        passed to ``__init__``), the event is also written to the
        ``feedback_events`` table.

        Args:
            anomaly_id: Unique identifier for the anomaly
            user_action: User action - 'helpful', 'acted_on', 'dismissed', 'false_positive'
            confidence_at_detection: Confidence score when anomaly was shown
            user_id: Optional ID of the user submitting the feedback. Required
                for DB persistence (skipped if missing — in-memory still works).
            document_id: Optional ID of the document the anomaly belongs to.
            original_severity: Optional severity that was originally shown.
            suggested_severity: Optional severity the user is suggesting.

        Valid user actions:
            - 'helpful': User found the anomaly helpful
            - 'acted_on': User took action based on the anomaly
            - 'dismissed': User dismissed the anomaly as not important
            - 'false_positive': User marked as false positive
        """
        # Validate inputs
        valid_actions = ['helpful', 'acted_on', 'dismissed', 'false_positive']
        if user_action not in valid_actions:
            logger.warning(
                f"Invalid user action '{user_action}', expected one of {valid_actions}"
            )
            return

        if not 0 <= confidence_at_detection <= 1:
            logger.warning(
                f"Invalid confidence {confidence_at_detection}, must be in [0, 1]"
            )
            return

        # Determine if prediction was correct
        # Correct if user found it helpful or acted on it
        was_correct = user_action in ['helpful', 'acted_on']

        # Create feedback entry
        feedback = {
            'anomaly_id': anomaly_id,
            'user_action': user_action,
            'confidence': confidence_at_detection,
            'was_correct': was_correct,
            'timestamp': datetime.now(timezone.utc)
        }

        # Write-through to DB BEFORE in-memory append so a crash between the
        # two doesn't lose the event. Feature-flagged via ACTIVE_LEARNING_PERSIST.
        # We need a user_id (FK NOT NULL) to persist; skip the DB write if
        # missing and log so callers can wire it up. On DB failure we log and
        # continue — never silently drop the event.
        if (
            self._db_session_factory is not None
            and _persist_enabled()
            and user_id is not None
        ):
            try:
                # Lazy import to avoid a circular import via app.db.base / models
                from app.models.feedback_event import FeedbackEvent
                with self._db_session_factory() as db:
                    db.add(FeedbackEvent(
                        user_id=user_id,
                        anomaly_id=anomaly_id,
                        document_id=document_id,
                        # Internal action names map to the persisted vocabulary
                        # ("dismissed" -> "dismiss", "false_positive" -> "disagree",
                        # "helpful"/"acted_on" -> "agree"). The DB column is
                        # capped at 20 chars; we keep the persisted value short.
                        user_action=_map_action_to_persisted(user_action),
                        original_severity=original_severity,
                        suggested_severity=suggested_severity,
                        confidence_score=confidence_at_detection,
                    ))
                    db.commit()
            except Exception as e:
                logger.error(
                    f"Failed to persist feedback to DB: {e}", exc_info=True
                )
                # Continue with in-memory append — don't lose the event
        elif (
            self._db_session_factory is not None
            and _persist_enabled()
            and user_id is None
        ):
            logger.debug(
                "Skipping DB persist: user_id not provided to collect_feedback "
                "(in-memory buffer still updated)"
            )

        # Add to buffer
        self.feedback_buffer.append(feedback)
        self.total_feedback_collected += 1

        logger.info(
            f"Feedback collected: anomaly={anomaly_id}, action={user_action}, "
            f"confidence={confidence_at_detection:.3f}, correct={was_correct}, "
            f"buffer_size={len(self.feedback_buffer)}/{self.retrain_after_samples}"
        )

        # Check if we should retrain
        if len(self.feedback_buffer) >= self.retrain_after_samples:
            logger.info(
                f"Feedback buffer full ({len(self.feedback_buffer)} samples), "
                f"triggering retraining..."
            )
            self._retrain_calibrator()

    def hydrate_from_db(self, max_rows: int = 1000) -> int:
        """
        Reload unprocessed feedback events from the DB into the in-memory buffer.

        Intended to run once at app startup (or first AnomalyDetector use) so
        feedback collected before a restart isn't lost. Each loaded row is
        stamped with ``processed_at = now()`` and committed so subsequent
        restarts skip it.

        Feature-flagged via ``ACTIVE_LEARNING_PERSIST``. Returns 0 silently if
        disabled or no session factory was supplied.

        Args:
            max_rows: Maximum rows to load on this call (caps OOM risk on
                first hydrate of a large backlog). Defaults to 1000.

        Returns:
            Number of rows hydrated into the buffer.
        """
        if not _persist_enabled():
            logger.debug(
                "hydrate_from_db: skipped (ACTIVE_LEARNING_PERSIST not enabled)"
            )
            return 0
        if self._db_session_factory is None:
            logger.debug(
                "hydrate_from_db: skipped (no db_session_factory provided)"
            )
            return 0

        try:
            # Lazy import to avoid circular imports during module load
            from app.models.feedback_event import FeedbackEvent
        except Exception as e:
            logger.error(f"hydrate_from_db: model import failed: {e}")
            return 0

        hydrated = 0
        try:
            with self._db_session_factory() as db:
                rows = (
                    db.query(FeedbackEvent)
                    .filter(FeedbackEvent.processed_at.is_(None))
                    .order_by(FeedbackEvent.created_at.desc())
                    .limit(max_rows)
                    .all()
                )

                now = datetime.now(timezone.utc)
                for row in rows:
                    internal_action = _map_action_to_internal(row.user_action)
                    was_correct = internal_action in ['helpful', 'acted_on']
                    confidence = row.confidence_score if row.confidence_score is not None else 0.5

                    self.feedback_buffer.append({
                        'anomaly_id': row.anomaly_id,
                        'user_action': internal_action,
                        'confidence': confidence,
                        'was_correct': was_correct,
                        'timestamp': row.created_at or now,
                    })
                    row.processed_at = now
                    hydrated += 1
                    self.total_feedback_collected += 1

                if hydrated:
                    db.commit()

            logger.info(
                f"Active learning hydrated {hydrated} feedback events from DB "
                f"(buffer_size now {len(self.feedback_buffer)}/"
                f"{self.retrain_after_samples})"
            )
        except Exception as e:
            logger.error(f"hydrate_from_db failed: {e}", exc_info=True)

        return hydrated

    def _retrain_calibrator(self) -> None:
        """
        Retrain the confidence calibrator using collected feedback.

        Extracts predictions and labels from feedback buffer, retrains
        the calibrator, calculates metrics, and clears the buffer.
        """
        if len(self.feedback_buffer) == 0:
            logger.warning("Cannot retrain: feedback buffer is empty")
            return

        logger.info(f"Starting calibrator retraining with {len(self.feedback_buffer)} samples")

        try:
            # Extract predictions and labels
            predictions = np.array([
                fb['confidence'] for fb in self.feedback_buffer
            ])
            labels = np.array([
                1 if fb['was_correct'] else 0 for fb in self.feedback_buffer
            ])

            # Check for edge case: all same action
            if len(np.unique(labels)) == 1:
                logger.warning(
                    f"All feedback samples have same label ({labels[0]}), "
                    f"retraining may not be effective"
                )
                # Continue anyway, but log warning

            # Calculate dismissal rate
            dismissal_count = sum(
                1 for fb in self.feedback_buffer
                if fb['user_action'] in ['dismissed', 'false_positive']
            )
            dismissal_rate = dismissal_count / len(self.feedback_buffer)

            # Alert if dismissal rate is high
            if dismissal_rate > self.dismissal_threshold:
                logger.warning(
                    f"High dismissal rate detected: {dismissal_rate:.1%} "
                    f"(threshold: {self.dismissal_threshold:.0%}). "
                    f"Consider adjusting detection sensitivity."
                )

            # Calculate accuracy before retraining
            accuracy_before = np.mean(labels)

            # Retrain calibrator
            logger.info("Fitting calibrator on feedback data...")
            self.calibrator.fit(predictions, labels)

            # Update metrics
            self.retrain_count += 1
            self.last_retrain_date = datetime.now(timezone.utc)

            # Log retraining metrics
            logger.info("=" * 60)
            logger.info("Active Learning Retraining Complete")
            logger.info("=" * 60)
            logger.info(f"Training samples: {len(self.feedback_buffer)}")
            logger.info(f"Positive samples (correct): {np.sum(labels)} ({np.mean(labels):.1%})")
            logger.info(f"Negative samples (incorrect): {len(labels) - np.sum(labels)} ({1 - np.mean(labels):.1%})")
            logger.info(f"Dismissal rate: {dismissal_rate:.1%}")
            logger.info(f"Accuracy (before retraining): {accuracy_before:.1%}")
            logger.info(f"Retrain count: {self.retrain_count}")
            logger.info(f"Total feedback collected: {self.total_feedback_collected}")
            logger.info("=" * 60)

            # Clear buffer
            buffer_size_before = len(self.feedback_buffer)
            self.feedback_buffer.clear()

            logger.info(
                f"Retraining successful, cleared {buffer_size_before} samples from buffer"
            )

        except Exception as e:
            logger.error(f"Retraining failed: {e}", exc_info=True)
            logger.warning("Feedback buffer NOT cleared due to error")
            # Don't clear buffer so we can retry later

    def get_uncertainty_samples(
        self,
        anomalies: List[Dict[str, Any]],
        n_samples: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get most uncertain anomalies for active learning.

        Identifies anomalies with confidence scores closest to 0.5
        (maximum uncertainty). These are ideal candidates for user
        feedback to improve model calibration.

        Args:
            anomalies: List of detected anomalies with confidence scores
            n_samples: Number of uncertain samples to return

        Returns:
            List of n_samples most uncertain anomalies
        """
        if not anomalies:
            logger.warning("No anomalies provided for uncertainty sampling")
            return []

        if n_samples <= 0:
            logger.warning(f"Invalid n_samples={n_samples}, must be > 0")
            return []

        # Limit n_samples to available anomalies
        n_samples = min(n_samples, len(anomalies))

        logger.info(
            f"Selecting {n_samples} most uncertain samples from "
            f"{len(anomalies)} anomalies"
        )

        # Calculate uncertainty for each anomaly
        # Uncertainty = distance from 0.5 (maximum uncertainty point)
        anomalies_with_uncertainty = []
        for anomaly in anomalies:
            # Try to get calibrated confidence first, fall back to raw
            confidence = anomaly.get('calibrated_confidence') or \
                        anomaly.get('stage2_confidence') or \
                        anomaly.get('stage1_detection', {}).get('stage1_confidence', 0.5)

            # Calculate uncertainty as distance from 0.5
            uncertainty = abs(confidence - 0.5)

            anomalies_with_uncertainty.append({
                'anomaly': anomaly,
                'confidence': confidence,
                'uncertainty': uncertainty
            })

        # Sort by uncertainty (ascending - smallest distance = most uncertain)
        sorted_by_uncertainty = sorted(
            anomalies_with_uncertainty,
            key=lambda x: x['uncertainty']
        )

        # Take top n_samples
        most_uncertain = sorted_by_uncertainty[:n_samples]

        # Extract anomalies
        uncertain_anomalies = [item['anomaly'] for item in most_uncertain]

        # Log uncertainty info
        logger.info("Most uncertain samples selected:")
        for i, item in enumerate(most_uncertain, 1):
            logger.info(
                f"  {i}. Confidence: {item['confidence']:.3f}, "
                f"Uncertainty: {item['uncertainty']:.3f}, "
                f"Clause: {item['anomaly'].get('clause_number', 'unknown')}"
            )

        return uncertain_anomalies

    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get feedback collection statistics.

        Returns:
            Dictionary containing feedback metrics and status
        """
        if not self.feedback_buffer:
            dismissal_rate = 0.0
            accuracy = 0.0
        else:
            dismissal_count = sum(
                1 for fb in self.feedback_buffer
                if fb['user_action'] in ['dismissed', 'false_positive']
            )
            dismissal_rate = dismissal_count / len(self.feedback_buffer)

            correct_count = sum(1 for fb in self.feedback_buffer if fb['was_correct'])
            accuracy = correct_count / len(self.feedback_buffer)

        return {
            'buffer_size': len(self.feedback_buffer),
            'buffer_capacity': self.retrain_after_samples,
            'buffer_progress': len(self.feedback_buffer) / self.retrain_after_samples,
            'total_feedback_collected': self.total_feedback_collected,
            'retrain_count': self.retrain_count,
            'last_retrain_date': self.last_retrain_date.isoformat() if self.last_retrain_date else None,
            'dismissal_rate': dismissal_rate,
            'accuracy': accuracy,
            'dismissal_threshold': self.dismissal_threshold,
            'calibrator_fitted': self.calibrator.is_fitted
        }

    def should_collect_feedback(self, confidence: float) -> bool:
        """
        Determine if feedback should be collected for this anomaly.

        Prioritizes uncertain predictions (near 0.5) for feedback collection.

        Args:
            confidence: Confidence score of the anomaly

        Returns:
            True if feedback should be collected, False otherwise
        """
        # Always collect feedback for uncertain predictions (0.4 - 0.6)
        uncertainty = abs(confidence - 0.5)

        if uncertainty < 0.1:  # Very uncertain (0.4 - 0.6)
            return True
        elif uncertainty < 0.2:  # Somewhat uncertain (0.3 - 0.7)
            # Collect 50% of the time
            return np.random.random() < 0.5
        else:  # Confident predictions
            # Collect 10% of the time
            return np.random.random() < 0.1

    def export_feedback_data(self) -> List[Dict[str, Any]]:
        """
        Export feedback buffer for persistence or analysis.

        Returns:
            List of feedback entries with serializable timestamps
        """
        return [
            {
                **fb,
                'timestamp': fb['timestamp'].isoformat()
            }
            for fb in self.feedback_buffer
        ]

    def import_feedback_data(self, feedback_data: List[Dict[str, Any]]) -> None:
        """
        Import feedback data from persistence layer.

        Args:
            feedback_data: List of feedback entries to import
        """
        for fb in feedback_data:
            # Convert timestamp back to datetime if it's a string
            if isinstance(fb['timestamp'], str):
                fb['timestamp'] = datetime.fromisoformat(fb['timestamp'])

            self.feedback_buffer.append(fb)

        logger.info(f"Imported {len(feedback_data)} feedback samples")

    def reset_buffer(self) -> None:
        """
        Reset feedback buffer without retraining.

        Useful for testing or manual intervention.
        """
        buffer_size = len(self.feedback_buffer)
        self.feedback_buffer.clear()
        logger.info(f"Feedback buffer reset, cleared {buffer_size} samples")

    def force_retrain(self) -> None:
        """
        Force retraining even if buffer is not full.

        Useful for manual retraining or testing.
        """
        if len(self.feedback_buffer) == 0:
            logger.warning("Cannot force retrain: feedback buffer is empty")
            return

        logger.info(
            f"Forcing retraining with {len(self.feedback_buffer)} samples "
            f"(normal threshold: {self.retrain_after_samples})"
        )
        self._retrain_calibrator()
