"""
Context-Aware Layer for T&C Analyzer.

Main orchestrator that combines:
- Document context detection (industry, user profile, power dynamics)
- Industry baselines (expected/outlier/red_flag patterns)
- Risk thresholds (acceptable risk by context)
- Harm severity calculation (context-adjusted multipliers)

Integrates at the start of Stage 2 in the anomaly detection pipeline
to reduce false positives and amplify real risks.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .document_context_detector import DocumentContextDetector, DocumentContext
from .context_aware_baselines import ContextAwareBaselines, IndustryBaseline
from .context_risk_thresholds import ContextRiskThresholds, ThresholdResult
from .harm_severity_calculator import HarmSeverityCalculator, HarmCalculationResult

logger = logging.getLogger(__name__)


@dataclass
class AnomalyAdjustment:
    """Adjustment made to a single anomaly."""

    original_severity: str
    adjusted_severity: str
    action: str  # 'suppressed', 'reduced', 'unchanged', 'amplified'
    pattern_classification: str  # 'expected', 'outlier', 'red_flag', 'neutral'
    multiplier: float
    reason: str


@dataclass
class ContextAwareAnalysisResult:
    """Result of context-aware analysis."""

    # Detected context
    context: DocumentContext

    # Industry baseline used
    industry_baseline: str
    industry_modifier: float

    # Adjusted anomalies
    adjusted_anomalies: List[Dict[str, Any]]

    # Suppressed anomalies (for debugging/logging)
    suppressed_anomalies: List[Dict[str, Any]]

    # Statistics
    total_anomalies: int
    suppressed_count: int
    reduced_count: int
    amplified_count: int
    unchanged_count: int

    # Adjustments made (for debugging/logging)
    adjustments: List[AnomalyAdjustment] = field(default_factory=list)

    # Processing metadata
    processing_time_ms: float = 0.0
    version: str = "1.0.0"


class ContextAwareLayer:
    """
    Main orchestrator for context-aware risk assessment.

    Reduces false positives by understanding document context and
    adjusting risk scores accordingly. Same patterns have different
    meanings in different industries.

    Usage:
        layer = ContextAwareLayer()
        result = layer.analyze_with_context(
            anomalies=stage1_results,
            document_text=document_text,
            metadata={'company_name': 'Apple Inc'}
        )
        # Use result.adjusted_anomalies in subsequent stages
    """

    def __init__(self):
        """Initialize context-aware layer with all components."""
        self.context_detector = DocumentContextDetector()
        self.baselines = ContextAwareBaselines()
        self.thresholds = ContextRiskThresholds()
        self.harm_calculator = HarmSeverityCalculator()

    def analyze_with_context(
        self,
        anomalies: List[Dict[str, Any]],
        document_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContextAwareAnalysisResult:
        """
        Analyze anomalies with context awareness.

        This is the main entry point. It:
        1. Auto-detects document context (industry, user profile, etc.)
        2. Classifies each anomaly against industry baseline
        3. Applies risk thresholds to suppress/reduce expected patterns
        4. Calculates context-adjusted harm severity
        5. Returns adjusted anomalies for further processing

        Args:
            anomalies: List of anomaly dicts from Stage 1
            document_text: Full document text for context detection
            metadata: Extracted metadata (company_name, document_type, etc.)

        Returns:
            ContextAwareAnalysisResult with adjusted anomalies and statistics
        """
        start_time = datetime.utcnow()
        metadata = metadata or {}

        # 1. Auto-detect context
        context = self.context_detector.detect_context(document_text, metadata)

        # 2. Get industry baseline
        baseline = self.baselines.get_baseline(context.industry)

        # 3. Process each anomaly
        adjusted_anomalies = []
        suppressed_anomalies = []
        adjustments = []

        reduced_count = 0
        amplified_count = 0
        unchanged_count = 0

        for anomaly in anomalies:
            adjustment = self._process_anomaly(anomaly, context, baseline)
            adjustments.append(adjustment)

            if adjustment.action == 'suppressed':
                # Add to suppressed list for debugging
                suppressed_copy = anomaly.copy()
                suppressed_copy['_suppression_reason'] = adjustment.reason
                suppressed_anomalies.append(suppressed_copy)
            else:
                # Update anomaly with adjusted severity
                adjusted_anomaly = anomaly.copy()

                if adjustment.adjusted_severity != adjustment.original_severity:
                    adjusted_anomaly['original_severity'] = adjustment.original_severity
                    adjusted_anomaly['severity'] = adjustment.adjusted_severity
                    adjusted_anomaly['context_adjustment'] = {
                        'action': adjustment.action,
                        'reason': adjustment.reason,
                        'multiplier': adjustment.multiplier,
                        'classification': adjustment.pattern_classification,
                    }

                adjusted_anomalies.append(adjusted_anomaly)

                # Track statistics
                if adjustment.action == 'reduced':
                    reduced_count += 1
                elif adjustment.action == 'amplified':
                    amplified_count += 1
                else:
                    unchanged_count += 1

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        result = ContextAwareAnalysisResult(
            context=context,
            industry_baseline=baseline.name,
            industry_modifier=baseline.base_modifier,
            adjusted_anomalies=adjusted_anomalies,
            suppressed_anomalies=suppressed_anomalies,
            total_anomalies=len(anomalies),
            suppressed_count=len(suppressed_anomalies),
            reduced_count=reduced_count,
            amplified_count=amplified_count,
            unchanged_count=unchanged_count,
            adjustments=adjustments,
            processing_time_ms=processing_time,
        )

        logger.info(
            f"Context-aware analysis complete: "
            f"industry={context.industry}, "
            f"total={result.total_anomalies}, "
            f"suppressed={result.suppressed_count}, "
            f"reduced={result.reduced_count}, "
            f"amplified={result.amplified_count}, "
            f"time={processing_time:.1f}ms"
        )

        return result

    def _process_anomaly(
        self,
        anomaly: Dict[str, Any],
        context: DocumentContext,
        baseline: IndustryBaseline
    ) -> AnomalyAdjustment:
        """
        Process a single anomaly and determine adjustment.

        Args:
            anomaly: Anomaly dict
            context: Detected document context
            baseline: Industry baseline

        Returns:
            AnomalyAdjustment describing what to do
        """
        # Get pattern identifier
        pattern = self._extract_pattern(anomaly)
        original_severity = anomaly.get('severity', 'medium')

        # 1. Classify against industry baseline
        classification = self.baselines.classify_pattern(pattern, context.industry)

        # 2. Evaluate threshold
        threshold_result = self.thresholds.evaluate_threshold(
            industry=context.industry,
            user_profile=context.user_profile,
            pattern=pattern,
            base_severity=original_severity
        )

        # 3. Calculate harm severity
        harm_result = self.harm_calculator.calculate_harm(
            pattern=pattern,
            base_severity=original_severity,
            industry=context.industry,
            user_profile=context.user_profile,
            power_dynamics=context.power_dynamics,
            data_sensitivity=context.data_sensitivity
        )

        # 4. Determine final action
        action, adjusted_severity, reason = self._determine_action(
            classification=classification,
            threshold_result=threshold_result,
            harm_result=harm_result,
            original_severity=original_severity,
            pattern=pattern,
            context=context,
            anomaly=anomaly  # Pass anomaly for prevalence check
        )

        return AnomalyAdjustment(
            original_severity=original_severity,
            adjusted_severity=adjusted_severity,
            action=action,
            pattern_classification=classification,
            multiplier=harm_result.final_multiplier,
            reason=reason
        )

    def _extract_pattern(self, anomaly: Dict[str, Any]) -> str:
        """
        Extract pattern identifier from anomaly.

        Tries multiple fields to find the most specific pattern name.
        """
        # Try different fields that might contain the pattern
        pattern = anomaly.get('risk_category')

        if not pattern:
            pattern = anomaly.get('pattern_type')

        if not pattern:
            pattern = anomaly.get('category')

        if not pattern:
            # Try to derive from title or description
            title = anomaly.get('title', '').lower()
            if 'arbitration' in title:
                pattern = 'forced_arbitration_class_waiver'
            elif 'liability' in title:
                pattern = 'broad_liability_disclaimer'
            elif 'termination' in title:
                pattern = 'unilateral_termination'
            elif 'license' in title and 'perpetual' in title:
                pattern = 'perpetual_irrevocable_license'
            elif 'ai' in title or 'training' in title:
                pattern = 'ai_training'
            elif 'data' in title and 'sell' in title:
                pattern = 'data_selling'
            else:
                pattern = 'unknown'

        return pattern

    def _determine_action(
        self,
        classification: str,
        threshold_result: ThresholdResult,
        harm_result: HarmCalculationResult,
        original_severity: str,
        pattern: str,
        context: DocumentContext,
        anomaly: Dict[str, Any] = None
    ) -> Tuple[str, str, str]:
        """
        Determine final action based on all factors.

        Priority:
        1. ALWAYS_CRITICAL patterns → force critical, never suppress
        2. High prevalence (>=70%) → suppress common clauses
        3. Red flags are NEVER suppressed, may be amplified
        4. Threshold 'accept' suppresses expected patterns
        5. Harm multiplier adjusts severity up or down
        6. Classification informs severity adjustments

        Returns:
            Tuple of (action, adjusted_severity, reason)
        """
        from .constants import CriticalPatterns, PrevalenceThresholds, BOILERPLATE_SECTIONS

        severity_levels = ['low', 'medium', 'high', 'critical']

        # Normalize pattern for comparison
        pattern_normalized = pattern.lower().replace('-', '_').replace(' ', '_') if pattern else ''

        # =================================================================
        # PRIORITY 1: ALWAYS_CRITICAL patterns - force critical severity
        # These patterns should NEVER be downgraded, always shown as critical
        # =================================================================
        if pattern_normalized in CriticalPatterns.ALWAYS_CRITICAL:
            return (
                'amplified',
                'critical',
                f"Critical consumer harm pattern: {pattern} - always flagged as critical"
            )

        # =================================================================
        # PRIORITY 1.5: BOILERPLATE SECTION DETECTION
        # Suppress non-critical patterns in standard legal sections
        # =================================================================
        if anomaly:
            section_name = anomaly.get('section', '') or anomaly.get('clause_section', '') or ''
            section_lower = section_name.lower().strip()

            # Check if this is a boilerplate section
            is_boilerplate = any(bp in section_lower for bp in BOILERPLATE_SECTIONS)

            if is_boilerplate and original_severity != 'critical':
                # Suppress non-critical findings in boilerplate sections
                return (
                    'suppressed',
                    original_severity,
                    f"Standard boilerplate section ({section_name}) - suppressed"
                )

        # =================================================================
        # PRIORITY 2: HIGH PREVALENCE - suppress common clauses
        # Patterns found in 70%+ of T&Cs are standard and should be hidden
        # =================================================================
        if anomaly:
            prevalence_data = anomaly.get('prevalence', {})
            prevalence = prevalence_data.get('prevalence', 0.5) if isinstance(prevalence_data, dict) else 0.5

            # Very common (85%+) - always suppress
            if prevalence >= PrevalenceThresholds.VERY_COMMON_THRESHOLD:
                return (
                    'suppressed',
                    original_severity,
                    f"Very common clause ({prevalence:.0%} prevalence) - standard T&C language"
                )

            # Common (70%+) expected patterns - suppress
            if prevalence >= PrevalenceThresholds.SUPPRESS_ABOVE and classification == 'expected':
                return (
                    'suppressed',
                    original_severity,
                    f"Common expected pattern ({prevalence:.0%} prevalence) in {context.industry}"
                )

        # =================================================================
        # PRIORITY 3: RED FLAGS - Never suppress, may amplify
        # Skip amplification for LLM-sourced severities (LLM already calibrated)
        # =================================================================
        # Check if severity was set by LLM
        severity_from_llm_early = anomaly.get('severity_source') == 'llm' if anomaly else False

        if classification == 'red_flag':
            if harm_result.final_multiplier > 1.5 and not severity_from_llm_early:
                # Amplify severity, but only escalate to 'critical' if base is 'high'
                current_idx = severity_levels.index(original_severity) if original_severity in severity_levels else 1
                # Only allow escalation to critical (index 3) if already high (index 2)
                max_idx = 3 if current_idx >= 2 else 2  # Cap at 'high' unless already 'high'
                new_idx = min(current_idx + 1, max_idx)
                adjusted = severity_levels[new_idx]
                return (
                    'amplified',
                    adjusted,
                    f"Red flag pattern in {context.industry} - amplified from {original_severity} to {adjusted}"
                )
            return (
                'unchanged',
                original_severity,
                f"Red flag pattern - maintaining {original_severity} severity"
            )

        # EXPECTED + ACCEPT: Suppress
        if classification == 'expected' and threshold_result.should_suppress:
            return (
                'suppressed',
                original_severity,
                f"Pattern '{pattern}' is expected in {context.industry} for {context.user_profile} users"
            )

        # EXPECTED + WARN: Reduce severity
        if classification == 'expected' and threshold_result.action == 'warn':
            current_idx = severity_levels.index(original_severity) if original_severity in severity_levels else 1
            new_idx = max(0, current_idx - 1)
            adjusted = severity_levels[new_idx]
            if adjusted != original_severity:
                return (
                    'reduced',
                    adjusted,
                    f"Common pattern in {context.industry} - reduced from {original_severity} to {adjusted}"
                )

        # Check if severity was set by LLM (already calibrated — don't amplify)
        severity_from_llm = anomaly.get('severity_source') == 'llm' if anomaly else False

        # OUTLIER: May amplify (but never to 'critical' - cap at 'high')
        # Skip amplification for LLM-sourced severities (LLM already calibrated)
        if classification == 'outlier' and not severity_from_llm:
            if harm_result.final_multiplier > 1.3:
                current_idx = severity_levels.index(original_severity) if original_severity in severity_levels else 1
                # Outliers cap at 'high' (index 2), never escalate to 'critical'
                new_idx = min(current_idx + 1, 2)  # Max index 2 = 'high'
                adjusted = severity_levels[new_idx]
                if adjusted != original_severity:
                    return (
                        'amplified',
                        adjusted,
                        f"Unusual pattern for {context.industry} - amplified from {original_severity} to {adjusted}"
                    )

        # USE HARM CALCULATION for all other cases
        # Skip amplification for LLM-sourced severities (LLM already calibrated)
        if harm_result.adjusted_severity != original_severity:
            adjusted_idx = severity_levels.index(harm_result.adjusted_severity) if harm_result.adjusted_severity in severity_levels else 1
            original_idx = severity_levels.index(original_severity) if original_severity in severity_levels else 1

            if adjusted_idx > original_idx and not severity_from_llm:
                # Cap amplification: only allow 'critical' if original was 'high'
                if harm_result.adjusted_severity == 'critical' and original_severity != 'high':
                    # Cap at 'high' instead
                    return (
                        'amplified',
                        'high',
                        harm_result.explanation + " (capped at high)"
                    )
                return (
                    'amplified',
                    harm_result.adjusted_severity,
                    harm_result.explanation
                )
            elif adjusted_idx < original_idx:
                # Downgrade is always allowed (even for LLM-sourced)
                return (
                    'reduced',
                    harm_result.adjusted_severity,
                    harm_result.explanation
                )

        # NO CHANGE
        return (
            'unchanged',
            original_severity,
            "Standard risk assessment applies"
        )

    def get_context_summary(self, context: DocumentContext) -> Dict[str, Any]:
        """
        Get a summary of detected context for logging/debugging.

        Args:
            context: Detected document context

        Returns:
            Dict with context summary
        """
        return {
            'industry': context.industry,
            'industry_confidence': context.industry_confidence,
            'industry_signals': context.industry_signals[:5],
            'user_profile': context.user_profile,
            'power_dynamics': context.power_dynamics,
            'data_sensitivity': context.data_sensitivity,
            'data_types': context.data_types_detected[:5],
            'company_name': context.company_name,
        }

    def get_baseline_summary(self, industry: str) -> Dict[str, Any]:
        """
        Get a summary of industry baseline for debugging.

        Args:
            industry: Industry identifier

        Returns:
            Dict with baseline summary
        """
        return self.baselines.get_industry_summary(industry)

    def get_supported_industries(self) -> List[str]:
        """Get list of supported industries."""
        return self.baselines.get_all_industries()


# Convenience function for quick analysis
def analyze_with_context(
    anomalies: List[Dict[str, Any]],
    document_text: str,
    metadata: Optional[Dict[str, Any]] = None
) -> ContextAwareAnalysisResult:
    """
    Convenience function for context-aware analysis.

    Usage:
        from app.core.context_aware_layer import analyze_with_context

        result = analyze_with_context(
            anomalies=stage1_results,
            document_text=document_text,
            metadata={'company_name': 'Apple Inc'}
        )
    """
    layer = ContextAwareLayer()
    return layer.analyze_with_context(anomalies, document_text, metadata)
