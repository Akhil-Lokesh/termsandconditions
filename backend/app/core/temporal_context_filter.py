"""
Temporal Context Filter for Stage 2 Anomaly Detection.

Applies temporal adjustments to risk scores based on when terms were last changed.
Recent changes receive heightened scrutiny with decay over time.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TemporalContextFilter:
    """
    Applies temporal context filtering to anomaly detection.

    Recent changes to terms and conditions receive heightened scrutiny
    with a decay model that reduces the modifier over time.
    """

    # Temporal decay model
    TEMPORAL_DECAY_TIERS = [
        {
            'days_min': 0,
            'days_max': 30,
            'modifier': 3.0,
            'label': 'Recent change, heightened scrutiny'
        },
        {
            'days_min': 31,
            'days_max': 60,
            'modifier': 2.0,
            'label': 'Recent change, elevated scrutiny'
        },
        {
            'days_min': 61,
            'days_max': 90,
            'modifier': 1.5,
            'label': 'Recent change, increased scrutiny'
        },
        {
            'days_min': 91,
            'days_max': None,  # No upper limit
            'modifier': 1.0,
            'label': 'Standard scrutiny'
        }
    ]

    # Threshold for considering a policy "very old"
    VERY_OLD_THRESHOLD_DAYS = 365 * 5  # 5 years

    def __init__(self):
        """Initialize the temporal context filter."""
        logger.info("TemporalContextFilter initialized")
        logger.info(f"Decay model: {len(self.TEMPORAL_DECAY_TIERS)} tiers")

    def apply_temporal_adjustment(
        self,
        risk_score: float,
        effective_date: Optional[datetime] = None,
        last_modified: Optional[datetime] = None,
        is_change: bool = False
    ) -> Dict[str, Any]:
        """
        Apply temporal adjustment to risk score.

        Args:
            risk_score: Base risk score (0-10)
            effective_date: Date when the current version became effective
            last_modified: Date when the terms were last modified
            is_change: Whether this represents a change from a previous version

        Returns:
            Dict containing:
                - temporal_modifier (float): Multiplier based on recency (1.0-3.0)
                - adjusted_score (float): risk_score * temporal_modifier
                - days_since_change (int): Days since last modification
                - reason (str): Explanation for the adjustment
                - is_very_old (bool): Whether policy is >5 years old
                - scrutiny_level (str): Label for scrutiny level
        """
        try:
            current_date = datetime.now()

            # Handle edge cases with dates
            edge_case_warnings = []

            # Use last_modified if available, otherwise effective_date
            reference_date = last_modified if last_modified else effective_date

            # Edge case 1: Missing dates
            if reference_date is None:
                logger.warning("No effective_date or last_modified provided, using current date")
                reference_date = current_date
                edge_case_warnings.append("No date provided, using current date")
                is_change = False  # Treat as non-change if we don't know the date

            # Edge case 2: Future dates
            if reference_date > current_date:
                logger.warning(
                    f"Reference date {reference_date} is in the future, using 1.0 modifier"
                )
                edge_case_warnings.append(
                    f"Future date detected ({reference_date.strftime('%Y-%m-%d')}), "
                    "using standard scrutiny"
                )
                return {
                    'temporal_modifier': 1.0,
                    'adjusted_score': risk_score * 1.0,
                    'days_since_change': 0,
                    'reason': (
                        'Future date detected. Using standard scrutiny. '
                        'Please verify the effective date is correct.'
                    ),
                    'is_very_old': False,
                    'scrutiny_level': 'Standard (future date)',
                    'warnings': edge_case_warnings
                }

            # Calculate days since change
            days_since_change = (current_date - reference_date).days

            # Edge case 3: Very old policies (>5 years)
            is_very_old = days_since_change > self.VERY_OLD_THRESHOLD_DAYS
            if is_very_old:
                years_old = days_since_change // 365
                edge_case_warnings.append(
                    f"Policy is {years_old} years old and may be outdated"
                )
                logger.info(f"Policy is very old: {days_since_change} days ({years_old} years)")

            # For non-changes (existing policies), use standard modifier
            if not is_change:
                reason = (
                    f'Existing policy (last modified {days_since_change} days ago). '
                    f'Using standard scrutiny.'
                )

                if is_very_old:
                    years_old = days_since_change // 365
                    reason += (
                        f' Note: Policy is {years_old} years old and may be outdated.'
                    )

                return {
                    'temporal_modifier': 1.0,
                    'adjusted_score': risk_score * 1.0,
                    'days_since_change': days_since_change,
                    'reason': reason,
                    'is_very_old': is_very_old,
                    'scrutiny_level': 'Standard (no change)',
                    'warnings': edge_case_warnings if edge_case_warnings else None
                }

            # For changes, apply decay model
            modifier, scrutiny_label = self._get_temporal_modifier(days_since_change)

            # Calculate adjusted score
            adjusted_score = risk_score * modifier

            # Build reason string
            reason = self._build_reason(
                days_since_change=days_since_change,
                modifier=modifier,
                scrutiny_label=scrutiny_label,
                is_very_old=is_very_old,
                reference_date=reference_date
            )

            result = {
                'temporal_modifier': modifier,
                'adjusted_score': adjusted_score,
                'days_since_change': days_since_change,
                'reason': reason,
                'is_very_old': is_very_old,
                'scrutiny_level': scrutiny_label,
                'reference_date': reference_date.strftime('%Y-%m-%d'),
                'warnings': edge_case_warnings if edge_case_warnings else None
            }

            logger.debug(
                f"Temporal adjustment applied: {days_since_change} days, "
                f"modifier={modifier}, score {risk_score} -> {adjusted_score}"
            )

            return result

        except Exception as e:
            logger.error(f"Error applying temporal adjustment: {str(e)}", exc_info=True)
            # On error, return neutral modifier to be safe
            return {
                'temporal_modifier': 1.0,
                'adjusted_score': risk_score * 1.0,
                'days_since_change': 0,
                'reason': f'Error during temporal adjustment: {str(e)}',
                'is_very_old': False,
                'scrutiny_level': 'Standard (error)',
                'error': str(e)
            }

    def _get_temporal_modifier(self, days_since_change: int) -> tuple[float, str]:
        """
        Get temporal modifier based on days since change.

        Args:
            days_since_change: Number of days since the change

        Returns:
            Tuple of (modifier, label)
        """
        for tier in self.TEMPORAL_DECAY_TIERS:
            days_min = tier['days_min']
            days_max = tier['days_max']

            # Check if days_since_change falls in this tier
            if days_max is None:
                # Last tier with no upper limit
                if days_since_change >= days_min:
                    return tier['modifier'], tier['label']
            else:
                # Tier with upper limit
                if days_min <= days_since_change <= days_max:
                    return tier['modifier'], tier['label']

        # Fallback (should never reach here with proper tier configuration)
        logger.warning(f"No tier found for {days_since_change} days, using 1.0 modifier")
        return 1.0, 'Standard scrutiny'

    def _build_reason(
        self,
        days_since_change: int,
        modifier: float,
        scrutiny_label: str,
        is_very_old: bool,
        reference_date: datetime
    ) -> str:
        """
        Build a comprehensive reason string for the temporal adjustment.

        Args:
            days_since_change: Number of days since change
            modifier: The temporal modifier applied
            scrutiny_label: Label describing the scrutiny level
            is_very_old: Whether the policy is very old
            reference_date: The reference date used for calculation

        Returns:
            Detailed reason string
        """
        # Format reference date
        date_str = reference_date.strftime('%Y-%m-%d')

        # Build main reason
        reason_parts = []

        # Part 1: Timeline
        if days_since_change == 0:
            reason_parts.append(f'Changed today ({date_str}).')
        elif days_since_change == 1:
            reason_parts.append(f'Changed yesterday ({date_str}).')
        elif days_since_change < 7:
            reason_parts.append(f'Changed {days_since_change} days ago ({date_str}).')
        elif days_since_change < 30:
            weeks = days_since_change // 7
            reason_parts.append(f'Changed {weeks} week{"s" if weeks > 1 else ""} ago ({date_str}).')
        elif days_since_change < 365:
            months = days_since_change // 30
            reason_parts.append(
                f'Changed {months} month{"s" if months > 1 else ""} ago ({date_str}).'
            )
        else:
            years = days_since_change // 365
            remaining_months = (days_since_change % 365) // 30
            if remaining_months > 0:
                reason_parts.append(
                    f'Changed {years} year{"s" if years > 1 else ""} and '
                    f'{remaining_months} month{"s" if remaining_months > 1 else ""} ago ({date_str}).'
                )
            else:
                reason_parts.append(
                    f'Changed {years} year{"s" if years > 1 else ""} ago ({date_str}).'
                )

        # Part 2: Scrutiny level and modifier
        reason_parts.append(
            f'{scrutiny_label}. Applying {modifier}x weight to risk score.'
        )

        # Part 3: Very old policy warning
        if is_very_old:
            years_old = days_since_change // 365
            reason_parts.append(
                f'Note: Policy is {years_old} year{"s" if years_old > 1 else ""} old '
                f'and may be outdated or non-compliant with current regulations.'
            )

        return ' '.join(reason_parts)

    def get_decay_tier_info(self, days_since_change: int) -> Dict[str, Any]:
        """
        Get information about which decay tier applies for given days.

        Args:
            days_since_change: Number of days since change

        Returns:
            Dict with tier information
        """
        modifier, label = self._get_temporal_modifier(days_since_change)

        # Find the matching tier
        for tier in self.TEMPORAL_DECAY_TIERS:
            days_min = tier['days_min']
            days_max = tier['days_max']

            if days_max is None:
                if days_since_change >= days_min:
                    return {
                        'days_since_change': days_since_change,
                        'tier_range': f'{days_min}+ days',
                        'modifier': modifier,
                        'label': label,
                        'tier': tier
                    }
            else:
                if days_min <= days_since_change <= days_max:
                    return {
                        'days_since_change': days_since_change,
                        'tier_range': f'{days_min}-{days_max} days',
                        'modifier': modifier,
                        'label': label,
                        'tier': tier
                    }

        # Fallback
        return {
            'days_since_change': days_since_change,
            'tier_range': 'Unknown',
            'modifier': 1.0,
            'label': 'Standard scrutiny'
        }

    def get_all_decay_tiers(self) -> list[Dict[str, Any]]:
        """
        Get information about all decay tiers.

        Returns:
            List of tier information dicts
        """
        return [
            {
                'days_min': tier['days_min'],
                'days_max': tier['days_max'],
                'days_range': (
                    f"{tier['days_min']}-{tier['days_max']} days"
                    if tier['days_max'] is not None
                    else f"{tier['days_min']}+ days"
                ),
                'modifier': tier['modifier'],
                'label': tier['label']
            }
            for tier in self.TEMPORAL_DECAY_TIERS
        ]

    def is_policy_very_old(self, effective_date: Optional[datetime] = None) -> bool:
        """
        Check if a policy is very old (>5 years).

        Args:
            effective_date: Date when the policy became effective

        Returns:
            True if policy is very old, False otherwise
        """
        if effective_date is None:
            return False

        current_date = datetime.now()
        days_old = (current_date - effective_date).days

        return days_old > self.VERY_OLD_THRESHOLD_DAYS

    def calculate_expected_decay(
        self,
        initial_score: float,
        days_progression: list[int]
    ) -> list[Dict[str, Any]]:
        """
        Calculate expected score decay over time for a given initial score.

        Useful for understanding how a risk score will decay as time passes.

        Args:
            initial_score: Initial risk score
            days_progression: List of days to calculate scores for

        Returns:
            List of dicts with days, modifier, adjusted_score
        """
        decay_progression = []

        for days in days_progression:
            modifier, label = self._get_temporal_modifier(days)
            adjusted_score = initial_score * modifier

            decay_progression.append({
                'days_since_change': days,
                'temporal_modifier': modifier,
                'adjusted_score': adjusted_score,
                'scrutiny_level': label
            })

        return decay_progression

    def suggest_review_priority(
        self,
        days_since_change: int,
        base_risk_score: float
    ) -> Dict[str, Any]:
        """
        Suggest review priority based on temporal context and risk score.

        Args:
            days_since_change: Days since last change
            base_risk_score: Base risk score (0-10)

        Returns:
            Dict with priority level and reasoning
        """
        modifier, label = self._get_temporal_modifier(days_since_change)
        adjusted_score = base_risk_score * modifier

        # Determine priority level
        if adjusted_score >= 8.0:
            priority = 'CRITICAL'
            priority_reason = (
                f'High risk score ({base_risk_score:.1f}) with {modifier}x temporal weight '
                f'= {adjusted_score:.1f}. Immediate review required.'
            )
        elif adjusted_score >= 6.0:
            priority = 'HIGH'
            priority_reason = (
                f'Elevated risk score ({base_risk_score:.1f}) with {modifier}x temporal weight '
                f'= {adjusted_score:.1f}. Review soon.'
            )
        elif adjusted_score >= 4.0:
            priority = 'MEDIUM'
            priority_reason = (
                f'Moderate risk score ({base_risk_score:.1f}) with {modifier}x temporal weight '
                f'= {adjusted_score:.1f}. Review when possible.'
            )
        else:
            priority = 'LOW'
            priority_reason = (
                f'Low risk score ({base_risk_score:.1f}) with {modifier}x temporal weight '
                f'= {adjusted_score:.1f}. Standard review process.'
            )

        return {
            'priority': priority,
            'base_risk_score': base_risk_score,
            'temporal_modifier': modifier,
            'adjusted_score': adjusted_score,
            'days_since_change': days_since_change,
            'scrutiny_level': label,
            'reason': priority_reason
        }
