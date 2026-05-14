"""
Anomaly detector for identifying risky clauses.

Universal anomaly detection that works for ANY Terms & Conditions document
from ANY company. Automatically identifies unusual, risky, or consumer-unfriendly
clauses without being told what to look for.

Multi-Stage Detection Pipeline:
- Stage 1: Multi-Method Detection (Pattern 40%, Semantic 35%, Statistical 25%)
- Stage 2: Context Filtering (Industry, Service Type, Temporal)
- Stage 3: Clustering & Deduplication (ML-powered with legal-BERT)
- Stage 4: Compound Risk Detection (6 systemic patterns)
- Stage 5: Confidence Calibration (Isotonic regression with active learning)
- Stage 6: Alert Ranking & Budget (MAX_ALERTS=10, prevents alert fatigue)
"""

import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.llm_clause_detector import LLMClauseDetector
from app.core.rag_anomaly_detector import ContextTag

from app.services.pinecone_service import PineconeService
from app.services.claude_service import ClaudeService
from app.services.embedding_service import EmbeddingService
from app.core.prevalence_calculator import PrevalenceCalculator
from app.core.risk_indicators import RiskIndicators
from app.core.semantic_risk_detector import SemanticRiskDetector  # Legacy - will be replaced
from app.core.compound_risk_detector import CompoundRiskDetector
from app.core.statistical_outlier_detector import StatisticalOutlierDetector  # Stage 1: Statistical
from app.core.semantic_anomaly_detector import SemanticAnomalyDetector  # Stage 1: Semantic
from app.core.industry_baseline_filter import IndustryBaselineFilter  # Stage 2: Industry Context
from app.core.service_type_context_filter import ServiceTypeContextFilter  # Stage 2: Service Type
from app.core.temporal_context_filter import TemporalContextFilter  # Stage 2: Temporal Context
from app.core.anomaly_clusterer import AnomalyClusterer  # Stage 3: Clustering & Deduplication
from app.core.confidence_calibrator import ConfidenceCalibrator  # Stage 5: Confidence Calibration
from app.core.active_learning_manager import ActiveLearningManager  # Stage 5: Active Learning
from app.core.alert_ranker import AlertRanker  # Stage 6: Alert Ranking & Budget
from app.core.context_aware_layer import ContextAwareLayer  # NEW: Context-Aware Layer
from app.core.competitive_analyzer import CompetitiveAnalyzer  # NEW: Competitive Benchmarking
from app.core.inverted_funnel import InvertedFunnelDetector, DetectedAnomaly  # NEW: Inverted Funnel System
from app.core.rag_anomaly_detector import RAGAnomalyDetector  # NEW: RAG-based detection
from app.core.constants import (
    ThreatLevel,
    CommonnessLevel,
    DisplayCategory,
    PATTERN_THREAT_LEVELS,
    CommonnessThresholds,
    get_display_category,
    get_threat_level_from_score,
    CATEGORY_PREVALENCE_ESTIMATES,
    INDUSTRY_PREVALENCE_MODIFIERS,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyDetector:
    """Detects anomalies and risky clauses in T&C documents."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        pinecone_service: Optional[PineconeService] = None,
        db: Optional[Session] = None,
        claude_service: Optional[ClaudeService] = None,
        enable_statistical_detection: bool = True,
        enable_semantic_detection: bool = True,
    ):
        """
        Initialize anomaly detector with multi-stage detection pipeline.

        Args:
            embedding_service: Optional Embedding service instance for semantic detection
            pinecone_service: Optional Pinecone service instance
            db: Optional database session
            claude_service: Optional Claude service instance
            enable_statistical_detection: Enable Stage 1 statistical detection
            enable_semantic_detection: Enable Stage 1 semantic detection
        """
        self.embedding = embedding_service or EmbeddingService()
        self.claude = claude_service or ClaudeService()
        self.pinecone = pinecone_service or PineconeService()
        self.db = db

        # Legacy detectors (maintained for backward compatibility)
        self.prevalence_calc = PrevalenceCalculator(self.embedding, self.pinecone, self.db)
        self.risk_indicators = RiskIndicators()
        self.semantic_detector = SemanticRiskDetector(self.embedding)  # FIXED: Use EmbeddingService
        self.compound_detector = CompoundRiskDetector()
        self._semantic_initialized = False

        # NEW: Stage 1 Multi-Method Detection
        self.enable_statistical = enable_statistical_detection
        self.enable_semantic = enable_semantic_detection

        # Initialize Statistical Outlier Detector (Stage 1)
        if self.enable_statistical:
            try:
                self.statistical_detector = StatisticalOutlierDetector(
                    contamination=0.1,
                    random_state=42
                )
                logger.info("Statistical outlier detector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize statistical detector: {e}")
                self.statistical_detector = None
        else:
            self.statistical_detector = None

        # Initialize Semantic Anomaly Detector (Stage 1)
        if self.enable_semantic:
            try:
                self.semantic_anomaly_detector = SemanticAnomalyDetector(
                    model_name='sentence-transformers/all-MiniLM-L6-v2',  # Lightweight model
                    similarity_threshold=0.75
                )
                logger.info(f"Semantic anomaly detector initialized (available: {self.semantic_anomaly_detector.is_available})")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic anomaly detector: {e}")
                self.semantic_anomaly_detector = None
        else:
            self.semantic_anomaly_detector = None

        # Detection method weights for Stage 1 confidence calculation
        self.method_weights = {
            'pattern_based': 0.40,  # 40% weight
            'semantic': 0.35,        # 35% weight
            'statistical': 0.25      # 25% weight
        }

        # NEW: Stage 2 Context Filters
        try:
            self.industry_filter = IndustryBaselineFilter(pinecone_service=self.pinecone)
            logger.info("Industry baseline filter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize industry filter: {e}")
            self.industry_filter = None

        try:
            self.service_type_filter = ServiceTypeContextFilter()
            logger.info("Service type context filter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize service type filter: {e}")
            self.service_type_filter = None

        try:
            self.temporal_filter = TemporalContextFilter()
            logger.info("Temporal context filter initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize temporal filter: {e}")
            self.temporal_filter = None

        # NEW: Stage 3 Clusterer
        try:
            self.anomaly_clusterer = AnomalyClusterer(
                model_name='nlpaueb/legal-bert-base-uncased',
                duplicate_threshold=0.95
            )
            logger.info(f"Anomaly clusterer initialized (available: {self.anomaly_clusterer.is_available})")
        except Exception as e:
            logger.warning(f"Failed to initialize anomaly clusterer: {e}")
            self.anomaly_clusterer = None

        # NEW: Stage 5 Confidence Calibration & Active Learning
        try:
            self.confidence_calibrator = ConfidenceCalibrator()
            self.active_learning = ActiveLearningManager(self.confidence_calibrator)
            logger.info("Confidence calibrator and active learning manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Stage 5 components: {e}")
            self.confidence_calibrator = None
            self.active_learning = None

        # NEW: Stage 6 Alert Ranking & Budget Management
        try:
            # user_preferences can be set later via set_user_preferences()
            self.alert_ranker = AlertRanker()
            logger.info("Alert ranker initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize alert ranker: {e}")
            self.alert_ranker = None

        # NEW: Context-Aware Layer (reduces false positives)
        try:
            self.context_aware_layer = ContextAwareLayer()
            logger.info("Context-aware layer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize context-aware layer: {e}")
            self.context_aware_layer = None

        # NEW: Inverted Funnel Detector (4-layer system for better UX)
        try:
            self.inverted_funnel = InvertedFunnelDetector(
                risk_indicators=self.risk_indicators,
                semantic_detector=self.semantic_anomaly_detector,
                statistical_detector=self.statistical_detector,
                prevalence_calculator=self.prevalence_calc,
            )
            logger.info("Inverted funnel detector initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize inverted funnel detector: {e}")
            self.inverted_funnel = None

        # NEW: RAG-based Anomaly Detector (true retrieval-augmented detection)
        # Uses baseline corpus comparison for accurate prevalence calculation
        try:
            self.rag_detector = RAGAnomalyDetector(
                embedding_service=self.embedding,
                pinecone_service=self.pinecone,
                baseline_namespace="baseline",
                similarity_threshold=0.75,
            )
            logger.info("RAG anomaly detector initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG detector: {e}")
            self.rag_detector = None

    async def _run_multi_stage_detection(
        self,
        clause_text: str,
        clause_dict: Dict[str, Any],
        service_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Run multi-stage detection on a single clause.

        Combines pattern-based, semantic, and statistical detection methods.

        Args:
            clause_text: The clause text to analyze
            clause_dict: Clause dictionary for statistical detector
            service_type: Type of service for context

        Returns:
            Dictionary containing detection results from all methods
        """
        detections = []
        method_confidences = {}

        # METHOD 1: Pattern-Based Detection (Keyword matching)
        pattern_start = time.time()
        try:
            detected_indicators = self.risk_indicators.detect_indicators(
                clause_text=clause_text,
                service_type=service_type
            )

            # Calculate pattern-based confidence
            if detected_indicators:
                # Higher confidence if more high-severity indicators
                high_severity = sum(1 for ind in detected_indicators if ind['severity'] == 'high')
                medium_severity = sum(1 for ind in detected_indicators if ind['severity'] == 'medium')

                # Confidence: 0.5 base + (0.2 per high) + (0.1 per medium), capped at 1.0
                pattern_confidence = min(1.0, 0.5 + (high_severity * 0.2) + (medium_severity * 0.1))
            else:
                pattern_confidence = 0.0

            method_confidences['pattern_based'] = pattern_confidence

            detections.append({
                'method': 'pattern_based',
                'indicators': detected_indicators,
                'count': len(detected_indicators),
                'has_high_risk': any(ind['severity'] == 'high' for ind in detected_indicators),
                'has_medium_risk': any(ind['severity'] == 'medium' for ind in detected_indicators),
                'confidence': pattern_confidence,
                'timing_ms': (time.time() - pattern_start) * 1000
            })

            logger.debug(f"Pattern detection: {len(detected_indicators)} indicators, confidence={pattern_confidence:.2f}")

        except Exception as e:
            logger.error(f"Pattern-based detection failed: {e}")
            detections.append({
                'method': 'pattern_based',
                'error': str(e),
                'confidence': 0.0
            })
            method_confidences['pattern_based'] = 0.0

        # METHOD 2: Semantic Anomaly Detection (Embeddings)
        semantic_start = time.time()
        try:
            if self.semantic_anomaly_detector and self.semantic_anomaly_detector.is_available:
                semantic_result = self.semantic_anomaly_detector.detect_semantic_anomalies(clause_text)

                method_confidences['semantic'] = semantic_result.get('confidence', 0.0)

                detections.append({
                    'method': 'semantic',
                    'is_anomalous': semantic_result.get('is_anomalous', False),
                    'similarity_score': semantic_result.get('similarity_score', 0.0),
                    'matched_pattern': semantic_result.get('matched_pattern'),
                    'matched_category': semantic_result.get('matched_category'),
                    'severity': semantic_result.get('severity', 'unknown'),
                    'confidence': semantic_result.get('confidence', 0.0),
                    'all_matches': semantic_result.get('all_matches', []),
                    'timing_ms': (time.time() - semantic_start) * 1000
                })

                logger.debug(
                    f"Semantic detection: anomalous={semantic_result.get('is_anomalous')}, "
                    f"similarity={semantic_result.get('similarity_score', 0):.3f}, "
                    f"confidence={semantic_result.get('confidence', 0):.2f}"
                )
            else:
                # Semantic detector not available
                detections.append({
                    'method': 'semantic',
                    'available': False,
                    'confidence': 0.0
                })
                method_confidences['semantic'] = 0.0
                logger.debug("Semantic detection: not available")

        except Exception as e:
            logger.error(f"Semantic detection failed: {e}")
            detections.append({
                'method': 'semantic',
                'error': str(e),
                'confidence': 0.0
            })
            method_confidences['semantic'] = 0.0

        # METHOD 3: Statistical Outlier Detection (Isolation Forest)
        statistical_start = time.time()
        try:
            if self.statistical_detector and self.statistical_detector.is_fitted:
                statistical_result = self.statistical_detector.predict(clause_dict)

                method_confidences['statistical'] = statistical_result.get('confidence', 0.0)

                detections.append({
                    'method': 'statistical',
                    'is_outlier': statistical_result.get('is_outlier', False),
                    'anomaly_score': statistical_result.get('anomaly_score', 0.0),
                    'confidence': statistical_result.get('confidence', 0.0),
                    'features': statistical_result.get('features', {}),
                    'timing_ms': (time.time() - statistical_start) * 1000
                })

                logger.debug(
                    f"Statistical detection: outlier={statistical_result.get('is_outlier')}, "
                    f"score={statistical_result.get('anomaly_score', 0):.3f}, "
                    f"confidence={statistical_result.get('confidence', 0):.2f}"
                )
            else:
                # Statistical detector not fitted
                detections.append({
                    'method': 'statistical',
                    'fitted': False,
                    'confidence': 0.0
                })
                method_confidences['statistical'] = 0.0
                logger.debug("Statistical detection: not fitted (baseline corpus required)")

        except Exception as e:
            logger.error(f"Statistical detection failed: {e}")
            detections.append({
                'method': 'statistical',
                'error': str(e),
                'confidence': 0.0
            })
            method_confidences['statistical'] = 0.0

        # Calculate weighted Stage 1 confidence
        stage1_confidence = (
            method_confidences.get('pattern_based', 0.0) * self.method_weights['pattern_based'] +
            method_confidences.get('semantic', 0.0) * self.method_weights['semantic'] +
            method_confidences.get('statistical', 0.0) * self.method_weights['statistical']
        )

        # Determine if should proceed to Stage 2
        # Proceed if ANY method flags the clause
        pattern_flagged = any(d.get('method') == 'pattern_based' and d.get('count', 0) > 0 for d in detections)
        semantic_flagged = any(d.get('method') == 'semantic' and d.get('is_anomalous', False) for d in detections)
        statistical_flagged = any(d.get('method') == 'statistical' and d.get('is_outlier', False) for d in detections)

        proceed_to_stage2 = pattern_flagged or semantic_flagged or statistical_flagged

        return {
            'detections': detections,
            'method_confidences': method_confidences,
            'stage1_confidence': stage1_confidence,
            'proceed_to_stage2': proceed_to_stage2,
            'flags': {
                'pattern': pattern_flagged,
                'semantic': semantic_flagged,
                'statistical': statistical_flagged
            }
        }

    def run_stage1(
        self,
        clauses: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run Stage 1 multi-method detection on a list of clauses.

        Uses pattern-based keyword detection on each clause.
        Returns dict with 'anomalies' list for downstream stages.
        """
        service_type = context.get('service_type', 'general')
        anomalies = []

        for clause in clauses:
            clause_text = clause.get('text', '')
            clause_number = clause.get('clause_number', 'unknown')

            if not clause_text or len(clause_text.strip()) < 10:
                continue

            # Pattern-based detection
            detected_indicators = self.risk_indicators.detect_indicators(
                clause_text=clause_text,
                service_type=service_type,
            )

            if detected_indicators:
                high_severity = sum(1 for ind in detected_indicators if ind.get('severity') == 'high')
                medium_severity = sum(1 for ind in detected_indicators if ind.get('severity') == 'medium')
                pattern_confidence = min(1.0, 0.5 + (high_severity * 0.2) + (medium_severity * 0.1))

                severity = 'high' if high_severity > 0 else 'medium' if medium_severity > 0 else 'low'

                anomalies.append({
                    'clause_number': clause_number,
                    'clause_text': clause_text,
                    'severity': severity,
                    'risk_category': detected_indicators[0].get('category', 'other'),
                    'detected_indicators': detected_indicators,
                    'stage1_detection': {
                        'stage1_confidence': pattern_confidence,
                        'methods': {'pattern': True, 'semantic': False, 'statistical': False},
                    },
                })

        return {'anomalies': anomalies}

    async def run_stage2(
        self,
        stage1_results: List[Dict[str, Any]],
        document_context: Dict[str, Any],
        document_text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Run Stage 2 context filtering on Stage 1 anomalies.

        NEW: Starts with Context-Aware Layer to reduce false positives by
        understanding document context (industry, user profile, power dynamics).

        Then applies industry-specific baselines, service type context,
        and temporal adjustments to refine anomaly detection.

        Args:
            stage1_results: List of anomalies from Stage 1
            document_context: Context about the document including:
                - industry: Industry type (e.g., 'children_apps', 'health_apps')
                - service_type: Service type (e.g., 'subscription', 'freemium')
                - effective_date: When T&C became effective
                - last_modified: When T&C were last modified
                - is_change: Whether this is a change from previous version
            document_text: Full document text for context detection

        Returns:
            List of anomalies with Stage 2 metadata and filtering applied
        """
        logger.info(f"Starting Stage 2 filtering on {len(stage1_results)} anomalies")

        # =====================================================================
        # NEW: Context-Aware Layer (reduces false positives)
        # Auto-detects industry, user profile, power dynamics from document text
        # Suppresses expected patterns, amplifies red flags
        # =====================================================================
        if self.context_aware_layer and document_text:
            try:
                context_result = self.context_aware_layer.analyze_with_context(
                    anomalies=stage1_results,
                    document_text=document_text,
                    metadata=document_context.get('metadata', {})
                )

                # Update document context with detected industry
                document_context['detected_industry'] = context_result.context.industry
                document_context['industry_confidence'] = context_result.context.industry_confidence
                document_context['user_profile'] = context_result.context.user_profile
                document_context['power_dynamics'] = context_result.context.power_dynamics
                document_context['data_sensitivity'] = context_result.context.data_sensitivity

                # Use auto-detected industry if not manually specified
                if document_context.get('industry') in [None, 'general', 'saas']:
                    if context_result.context.industry_confidence > 0.3:
                        document_context['industry'] = context_result.context.industry

                # Use adjusted anomalies (suppressed patterns removed, severities adjusted)
                stage1_results = context_result.adjusted_anomalies

                logger.info(
                    f"Context-Aware Layer: industry={context_result.context.industry} "
                    f"(confidence={context_result.context.industry_confidence:.2f}), "
                    f"suppressed={context_result.suppressed_count}, "
                    f"reduced={context_result.reduced_count}, "
                    f"amplified={context_result.amplified_count}"
                )

                # Log suppressed patterns for debugging
                if context_result.suppressed_anomalies:
                    suppressed_patterns = [
                        a.get('risk_category', 'unknown')
                        for a in context_result.suppressed_anomalies[:5]
                    ]
                    logger.info(f"  Suppressed patterns: {suppressed_patterns}")

            except Exception as e:
                logger.warning(f"Context-aware analysis failed: {e}")
                # Continue with original anomalies if context-aware fails
        else:
            if not self.context_aware_layer:
                logger.debug("Context-aware layer not available")
            if not document_text:
                logger.debug("No document text provided for context detection")
        stage2_start = time.time()

        # Extract document context with defaults
        industry = document_context.get('industry', 'saas')  # Default to SaaS
        service_type = document_context.get('service_type', 'subscription')  # Default to subscription
        effective_date = document_context.get('effective_date')
        last_modified = document_context.get('last_modified')
        is_change = document_context.get('is_change', False)

        logger.info(
            f"Document context: industry={industry}, service_type={service_type}, "
            f"is_change={is_change}"
        )

        stage2_results = []
        filtered_out_count = 0

        # Batch-embed all clause texts upfront (much faster than per-clause calls)
        clause_embeddings_map = {}
        if self.embedding and self.industry_filter:
            try:
                clause_texts = [a.get('clause_text', '') for a in stage1_results]
                clause_keys = [a.get('clause_number', f'unknown_{i}') for i, a in enumerate(stage1_results)]
                embeddings = await self.embedding.batch_create_embeddings(clause_texts)
                clause_embeddings_map = dict(zip(clause_keys, embeddings))
                logger.info(f"Batch-embedded {len(embeddings)} clauses for Stage 2")
            except Exception as e:
                logger.warning(f"Batch embedding failed, falling back to category estimates: {e}")

        for anomaly in stage1_results:
            try:
                # Extract anomaly data
                clause_text = anomaly.get('clause_text', '')
                clause_number = anomaly.get('clause_number', 'unknown')
                category = anomaly.get('risk_category', 'other')
                stage1_confidence = anomaly.get('stage1_detection', {}).get('stage1_confidence', 0.5)

                # Get base risk score (use severity as proxy: high=8, medium=5, low=3)
                severity = anomaly.get('severity', 'medium')
                base_risk_score = {'high': 8.0, 'medium': 5.0, 'low': 3.0}.get(severity, 5.0)

                logger.debug(
                    f"Processing clause {clause_number}: base_risk={base_risk_score}, "
                    f"stage1_confidence={stage1_confidence:.2f}"
                )

                # STEP 1: Calculate prevalence and apply industry modifier
                prevalence_result = None
                industry_adjustment = None

                # Get estimated prevalence based on category (fallback when baseline unavailable)
                estimated_prevalence = CATEGORY_PREVALENCE_ESTIMATES.get(category, 0.50)

                if self.industry_filter:
                    try:
                        # Use pre-computed batch embedding
                        clause_embedding = clause_embeddings_map.get(clause_number)

                        if clause_embedding:
                            # Calculate prevalence from baseline
                            prevalence_result = await self.industry_filter.calculate_prevalence(
                                clause_embedding=clause_embedding,
                                industry=industry,
                                category=category
                            )

                            # If baseline returned 0 (empty), use category estimate
                            if prevalence_result.get('prevalence', 0.0) == 0.0:
                                prevalence_result['prevalence'] = estimated_prevalence
                                prevalence_result['source'] = 'category_estimate'

                            # Apply industry modifier
                            industry_adjustment = self.industry_filter.apply_industry_modifier(
                                base_risk_score=base_risk_score,
                                industry=industry,
                                category=category,
                                prevalence=prevalence_result.get('prevalence', estimated_prevalence),
                                clause_text=clause_text
                            )

                            logger.debug(
                                f"Clause {clause_number}: prevalence={prevalence_result.get('prevalence', 0):.2%}, "
                                f"industry_modifier={industry_adjustment.get('industry_modifier', 1.0):.2f}"
                            )
                        else:
                            # No embedding - use category estimate
                            logger.warning(f"No embedding for clause {clause_number}, using category estimate")
                            prevalence_result = {'prevalence': estimated_prevalence, 'source': 'category_estimate'}
                            industry_adjustment = self.industry_filter.apply_industry_modifier(
                                base_risk_score=base_risk_score,
                                industry=industry,
                                category=category,
                                prevalence=estimated_prevalence,
                                clause_text=clause_text
                            )

                    except Exception as e:
                        logger.error(f"Industry filtering failed for clause {clause_number}: {e}")
                        prevalence_result = {'prevalence': estimated_prevalence, 'source': 'category_estimate', 'error': str(e)}
                        industry_adjustment = {
                            'base_score': base_risk_score,
                            'industry_modifier': 1.0,
                            'adjusted_score': base_risk_score,
                            'reasoning': f'Using category estimate due to error'
                        }
                else:
                    # No industry filter - use category estimate
                    prevalence_result = {'prevalence': estimated_prevalence, 'source': 'category_estimate'}
                    industry_adjustment = {
                        'base_score': base_risk_score,
                        'industry_modifier': 1.0,
                        'adjusted_score': base_risk_score,
                        'reasoning': 'Using category-based prevalence estimate'
                    }

                # Use industry-adjusted score for further processing
                current_risk_score = industry_adjustment.get('adjusted_score', base_risk_score)

                # STEP 2: Apply service type context filter
                service_type_result = None

                if self.service_type_filter:
                    try:
                        # Prepare clause metadata for disclosure quality check
                        clause_metadata = {
                            'text': clause_text,
                            'position': anomaly.get('position', 0.5),  # Position in document (0-1)
                            'readability_score': anomaly.get('readability_score'),
                            'has_specific_details': anomaly.get('has_specific_details')
                        }

                        # Create detection dict for service type filter
                        detection = {
                            'category': category,
                            'confidence': stage1_confidence,
                            'severity': severity
                        }

                        service_type_result = self.service_type_filter.filter_by_service_context(
                            detection=detection,
                            service_type=service_type,
                            clause_metadata=clause_metadata
                        )

                        logger.debug(
                            f"Clause {clause_number}: keep_anomaly={service_type_result.get('keep_anomaly')}, "
                            f"context_score={service_type_result.get('context_score', 0.5):.2f}"
                        )

                    except Exception as e:
                        logger.error(f"Service type filtering failed for clause {clause_number}: {e}")
                        service_type_result = {
                            'keep_anomaly': True,
                            'reason': f'Error: {str(e)}',
                            'context_score': 0.5,
                            'error': str(e)
                        }
                else:
                    # No service type filter available
                    service_type_result = {
                        'keep_anomaly': True,
                        'reason': 'Service type filter not initialized',
                        'context_score': 0.5
                    }

                # STEP 3: Apply temporal adjustment
                temporal_adjustment = None

                if self.temporal_filter:
                    try:
                        temporal_adjustment = self.temporal_filter.apply_temporal_adjustment(
                            risk_score=current_risk_score,
                            effective_date=effective_date,
                            last_modified=last_modified,
                            is_change=is_change
                        )

                        # Update risk score with temporal adjustment
                        current_risk_score = temporal_adjustment.get('adjusted_score', current_risk_score)

                        logger.debug(
                            f"Clause {clause_number}: temporal_modifier={temporal_adjustment.get('temporal_modifier', 1.0):.2f}, "
                            f"final_score={current_risk_score:.2f}"
                        )

                    except Exception as e:
                        logger.error(f"Temporal adjustment failed for clause {clause_number}: {e}")
                        temporal_adjustment = {
                            'temporal_modifier': 1.0,
                            'adjusted_score': current_risk_score,
                            'reason': f'Error: {str(e)}',
                            'error': str(e)
                        }
                else:
                    # No temporal filter available
                    temporal_adjustment = {
                        'temporal_modifier': 1.0,
                        'adjusted_score': current_risk_score,
                        'reason': 'Temporal filter not initialized'
                    }

                # STEP 4: Calculate Stage 2 confidence
                # Combine Stage 1 confidence with context scores
                context_score = service_type_result.get('context_score', 0.5)

                # Stage 2 confidence = weighted average of Stage 1 confidence and context factors
                # Lower context_score means more concerning (alarming), so invert it for confidence
                context_confidence = 1.0 - context_score  # Alarming (0.1) becomes 0.9 confidence

                # Weight: 70% Stage 1, 30% context
                stage2_confidence = (stage1_confidence * 0.7) + (context_confidence * 0.3)

                # STEP 5: Determine if should proceed to Stage 3
                keep_anomaly = service_type_result.get('keep_anomaly', True)
                final_score = current_risk_score
                calibrated_confidence = stage2_confidence

                # Get prevalence value for filtering
                prevalence_value = prevalence_result.get('prevalence', 0.5) if isinstance(prevalence_result, dict) else 0.5

                # Import critical patterns to bypass prevalence filter
                from app.core.constants import CriticalPatterns, PrevalenceThresholds

                # Normalize category for comparison
                category_normalized = (category or '').lower().replace('-', '_').replace(' ', '_')

                # Check if this is a critical pattern that should never be suppressed
                is_critical_pattern = category_normalized in CriticalPatterns.ALWAYS_CRITICAL

                # Proceed to Stage 3 with stricter filtering:
                # 1. Service type filter says keep AND
                # 2. (Adjusted score >= 4.0 OR calibrated confidence >= 0.50) AND
                # 3. Prevalence < 85% (suppress only very common clauses) OR is critical pattern OR is high severity
                #
                # SEVERITY OVERRIDE: Never suppress high/critical severity anomalies by prevalence alone
                # Just because something is common doesn't mean it's not harmful
                severity = anomaly.get('severity', 'medium')
                is_high_severity = severity in ['critical', 'high']

                proceed_to_stage3 = (
                    keep_anomaly and
                    (final_score >= 4.0 or calibrated_confidence >= 0.50) and  # Raised thresholds
                    (
                        prevalence_value < PrevalenceThresholds.SUPPRESS_ABOVE or
                        is_critical_pattern or
                        is_high_severity  # NEW: Never suppress high/critical severity
                    )
                )

                # Log filtering decision
                if not keep_anomaly:
                    logger.info(
                        f"Clause {clause_number} filtered out by service type context: "
                        f"{service_type_result.get('reason', 'Unknown reason')}"
                    )
                    filtered_out_count += 1
                elif prevalence_value >= PrevalenceThresholds.SUPPRESS_ABOVE and not is_critical_pattern and not is_high_severity:
                    logger.info(
                        f"Clause {clause_number} filtered out - common clause: "
                        f"prevalence={prevalence_value:.0%} (>= 85% threshold)"
                    )
                    filtered_out_count += 1
                elif not proceed_to_stage3:
                    logger.info(
                        f"Clause {clause_number} filtered out by score/confidence thresholds: "
                        f"score={final_score:.2f}, confidence={calibrated_confidence:.2f}"
                    )
                    filtered_out_count += 1
                else:
                    logger.debug(
                        f"Clause {clause_number} proceeding to Stage 3: "
                        f"score={final_score:.2f}, confidence={calibrated_confidence:.2f}, prevalence={prevalence_value:.0%}"
                    )

                # STEP 6: Update anomaly with Stage 2 metadata
                stage2_anomaly = {
                    **anomaly,  # Include all Stage 1 fields
                    'prevalence': prevalence_value,  # Use float, not dict
                    'industry_adjustment': industry_adjustment,
                    'service_type_filter': service_type_result,
                    'temporal_adjustment': temporal_adjustment,
                    'stage2_confidence': stage2_confidence,
                    'final_risk_score': final_score,
                    'calibrated_confidence': calibrated_confidence,
                    'proceed_to_stage3': proceed_to_stage3,
                    'filtered_reason': None if proceed_to_stage3 else service_type_result.get('reason')
                }

                stage2_results.append(stage2_anomaly)

            except Exception as e:
                logger.error(f"Stage 2 processing failed for anomaly: {e}", exc_info=True)
                # Include anomaly with error info
                stage2_results.append({
                    **anomaly,
                    'stage2_error': str(e),
                    'proceed_to_stage3': True  # Keep on error to be safe
                })

        # Performance metrics
        stage2_duration = (time.time() - stage2_start) * 1000
        logger.info(
            f"Stage 2 complete: {len(stage2_results)} anomalies processed, "
            f"{filtered_out_count} filtered out, "
            f"{sum(1 for a in stage2_results if a.get('proceed_to_stage3', False))} proceeding to Stage 3, "
            f"took {stage2_duration:.2f}ms"
        )

        return stage2_results

    def run_stage3(self, stage2_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run Stage 3 clustering and deduplication.

        Groups similar anomalies together and removes duplicates to reduce noise
        and improve readability of the final report.

        Args:
            stage2_results: List of anomalies from Stage 2

        Returns:
            Dict containing:
                - clusters: List of representative anomalies with cluster metadata
                - noise: Individual anomalies that didn't cluster
                - reduction_ratio: Percentage reduction from clustering
                - original_count: Original number of anomalies
                - final_count: Final number after clustering
                - timing_ms: Performance metrics
        """
        logger.info(f"Starting Stage 3 clustering on {len(stage2_results)} anomalies")
        stage3_start = time.time()

        # Filter to only anomalies that should proceed to Stage 3
        anomalies_for_clustering = [
            a for a in stage2_results if a.get('proceed_to_stage3', True)
        ]

        logger.info(
            f"Stage 3 input: {len(anomalies_for_clustering)} anomalies "
            f"(filtered from {len(stage2_results)})"
        )

        # Check if clusterer is available
        if not self.anomaly_clusterer or not self.anomaly_clusterer.is_available:
            logger.warning("Anomaly clusterer not available, proceeding without clustering")
            return {
                'clusters': [
                    {
                        'cluster_id': f'no_clustering_{i}',
                        'representative_anomaly': anomaly,
                        'member_anomalies': [anomaly],
                        'cluster_size': 1,
                        'is_noise': True
                    }
                    for i, anomaly in enumerate(anomalies_for_clustering)
                ],
                'noise': [],
                'reduction_ratio': 0.0,
                'original_count': len(anomalies_for_clustering),
                'final_count': len(anomalies_for_clustering),
                'timing_ms': {'total': (time.time() - stage3_start) * 1000},
                'clusterer_available': False
            }

        try:
            # Run clustering
            clustering_result = self.anomaly_clusterer.cluster_anomalies(
                anomalies_for_clustering
            )

            # Transform clusters into final format
            clusters = []
            for cluster in clustering_result['clusters']:
                representative = cluster['representative_anomaly']

                # Add cluster metadata to representative
                representative_with_cluster = {
                    **representative,
                    'cluster_metadata': {
                        'cluster_id': cluster['cluster_id'],
                        'cluster_size': cluster['cluster_size'],
                        'section_references': cluster['section_references'],
                        'consolidated_text': cluster['consolidated_text'],
                        'average_confidence': cluster.get('average_confidence', 0.0),
                        'overall_severity': cluster.get('overall_severity', representative.get('severity', 'medium')),
                        'risk_categories': cluster.get('risk_categories', [representative.get('risk_category', 'other')]),
                        'member_clause_numbers': [
                            m.get('clause_number', 'unknown') for m in cluster['member_anomalies']
                        ]
                    },
                    'is_cluster_representative': True
                }

                clusters.append({
                    'cluster_id': cluster['cluster_id'],
                    'representative_anomaly': representative_with_cluster,
                    'member_anomalies': cluster['member_anomalies'],
                    'cluster_size': cluster['cluster_size']
                })

            # Process noise
            noise = clustering_result['noise']

            # Mark noise anomalies
            for anomaly in noise:
                anomaly['is_noise'] = True
                anomaly['cluster_metadata'] = None

            # Calculate metrics
            original_count = clustering_result['original_count']
            final_count = clustering_result['final_count']
            reduction_ratio = clustering_result['reduction_ratio']

            stage3_duration = (time.time() - stage3_start) * 1000

            logger.info(
                f"Stage 3 complete: Reduced {original_count} anomalies to {final_count} "
                f"({len(clusters)} clusters + {len(noise)} noise) - "
                f"{reduction_ratio:.1%} reduction in {stage3_duration:.2f}ms"
            )

            # Log cluster details
            if clusters:
                for cluster in clusters[:5]:  # Log first 5 clusters
                    logger.info(
                        f"  Cluster {cluster['cluster_id']}: {cluster['cluster_size']} members, "
                        f"severity={cluster['representative_anomaly']['cluster_metadata']['overall_severity']}"
                    )

            return {
                'clusters': clusters,
                'noise': noise,
                'reduction_ratio': reduction_ratio,
                'original_count': original_count,
                'final_count': final_count,
                'n_clusters': len(clusters),
                'n_noise': len(noise),
                'timing_ms': clustering_result.get('timing_ms', {}),
                'clusterer_available': True,
                'proceed_to_stage4': True
            }

        except Exception as e:
            logger.error(f"Stage 3 clustering failed: {e}", exc_info=True)

            # Graceful fallback: treat all anomalies as noise
            logger.warning("Falling back to no clustering due to error")

            return {
                'clusters': [],
                'noise': anomalies_for_clustering,
                'reduction_ratio': 0.0,
                'original_count': len(anomalies_for_clustering),
                'final_count': len(anomalies_for_clustering),
                'timing_ms': {'total': (time.time() - stage3_start) * 1000},
                'clusterer_available': False,
                'error': str(e),
                'proceed_to_stage4': True
            }

    def run_stage4(
        self,
        stage3_results: List[Dict[str, Any]],
        full_clauses: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Run Stage 4 compound risk detection.

        Identifies systemic risks that arise from combinations of individual anomalies.
        These compound patterns create risks that are worse than the sum of their parts.

        Args:
            stage3_results: List of anomalies from Stage 3 (clustered)
            full_clauses: Optional list of all document clauses for additional context

        Returns:
            Dict containing:
                - compound_risks: List of detected compound risk patterns
                - compound_risk_score: Overall compound risk score
                - patterns_detected: List of pattern names
                - timing_ms: Performance metrics
        """
        logger.info(f"Starting Stage 4 compound risk detection on {len(stage3_results)} anomalies")
        stage4_start = time.time()

        try:
            # Detect compound risks using existing detector
            compound_risks = self.compound_detector.detect_compound_risks(
                anomalies=stage3_results,
                full_clauses=full_clauses
            )

            # NEW: Also detect pattern clusters using RiskIndicators
            # Collect all detected pattern names from anomalies
            all_detected_patterns = set()
            for anomaly in stage3_results:
                for indicator in anomaly.get("detected_indicators", []):
                    all_detected_patterns.add(indicator["name"])

            # Use new pattern cluster detection
            if all_detected_patterns:
                pattern_clusters = self.risk_indicators.detect_pattern_clusters(
                    list(all_detected_patterns)
                )

                # Convert pattern clusters to compound risk format
                for cluster in pattern_clusters:
                    # Avoid duplicate entries by checking if similar pattern exists
                    cluster_key = cluster['cluster']
                    existing_names = {r.get('compound_risk_type', '') for r in compound_risks}

                    if cluster_key not in existing_names:
                        compound_risks.append({
                            'compound_risk_type': cluster['cluster'],
                            'name': cluster['cluster'].replace('_', ' ').title(),
                            'description': cluster['description'],
                            'compound_severity': cluster['severity'],
                            'base_severity': 'high',
                            'risk_multiplier': 1.5 if cluster['severity'] == 'critical' else 1.2,
                            'confidence': cluster['coverage_ratio'],
                            'combined_score': 8.0 if cluster['severity'] == 'critical' else 6.0,
                            'required_components': cluster['patterns_possible'],
                            'matched_required': cluster['patterns_found'],
                            'matched_optional': [],
                            'source': 'pattern_cluster'
                        })

                        logger.info(
                            f"Pattern cluster detected: {cluster['cluster']} "
                            f"({cluster['coverage']} patterns matched)"
                        )

            if compound_risks:
                logger.info(
                    f"Detected {len(compound_risks)} compound risk patterns: "
                    f"{[r['name'] for r in compound_risks]}"
                )

                # Add compound risks to each related anomaly for context
                for compound_risk in compound_risks:
                    # Get component indicators for this pattern
                    required_components = set(compound_risk.get("required_components", []))
                    matched_required = set(compound_risk.get("matched_required", []))
                    matched_optional = set(compound_risk.get("matched_optional", []))
                    all_matched = matched_required.union(matched_optional)

                    # Find anomalies involved in this compound risk
                    for anomaly in stage3_results:
                        anomaly_indicators = {
                            ind["name"] for ind in anomaly.get("detected_indicators", [])
                        }

                        if anomaly_indicators.intersection(all_matched):
                            # This anomaly is part of the compound risk
                            if "compound_risks" not in anomaly:
                                anomaly["compound_risks"] = []

                            anomaly["compound_risks"].append({
                                "pattern": compound_risk["compound_risk_type"],
                                "name": compound_risk["name"],
                                "compound_severity": compound_risk["compound_severity"],
                                "base_severity": compound_risk["base_severity"],
                                "risk_multiplier": compound_risk["risk_multiplier"],
                                "description": compound_risk["description"],
                                "confidence": compound_risk["confidence"],
                                "combined_score": compound_risk["combined_score"]
                            })

                            logger.debug(
                                f"Added compound risk '{compound_risk['name']}' to "
                                f"anomaly {anomaly.get('clause_number')}"
                            )
            else:
                logger.info("No compound risk patterns detected")

            # Calculate overall compound risk score
            compound_risk_assessment = self.compound_detector.calculate_compound_risk_score(
                compound_risks
            )

            stage4_duration = (time.time() - stage4_start) * 1000

            logger.info(
                f"Stage 4 complete: {len(compound_risks)} patterns detected, "
                f"compound risk score: {compound_risk_assessment['compound_risk_score']:.1f}/10 "
                f"({compound_risk_assessment['compound_risk_level']}), "
                f"took {stage4_duration:.2f}ms"
            )

            return {
                'compound_risks': compound_risks,
                'compound_risk_assessment': compound_risk_assessment,
                'patterns_detected': [r["compound_risk_type"] for r in compound_risks],
                'timing_ms': {'total': stage4_duration},
                'stage4_complete': True
            }

        except Exception as e:
            logger.error(f"Stage 4 compound risk detection failed: {e}", exc_info=True)

            # Graceful fallback
            return {
                'compound_risks': [],
                'compound_risk_assessment': {
                    'compound_risk_score': 0.0,
                    'compound_risk_level': 'None',
                    'compound_risk_count': 0
                },
                'patterns_detected': [],
                'timing_ms': {'total': (time.time() - stage4_start) * 1000},
                'stage4_complete': False,
                'error': str(e)
            }

    def load_calibrator(self, training_data_path: Optional[str] = None) -> None:
        """
        Load and fit confidence calibrator with historical feedback data.

        This should be called during initialization or periodically to update
        the calibrator with accumulated user feedback.

        Args:
            training_data_path: Optional path to training data file
                              If None, loads from database
        """
        logger.info("Loading calibrator with historical feedback data")

        if not self.confidence_calibrator:
            logger.error("Confidence calibrator not initialized")
            return

        try:
            # Calibrator trains from feedback data; uses raw scores until feedback is collected
            if training_data_path is None:
                logger.info(
                    "No training data path provided. Calibrator will use raw scores "
                    "until feedback is collected."
                )
                return

            # Load training data (predictions and labels)
            # This would be implemented based on your database schema
            logger.info(f"Loading training data from {training_data_path}")

            # Placeholder for actual implementation
            import numpy as np
            # predicted_probs = np.load(f"{training_data_path}/predictions.npy")
            # actual_labels = np.load(f"{training_data_path}/labels.npy")

            # self.confidence_calibrator.fit(predicted_probs, actual_labels)

            logger.info("Calibrator loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load calibrator: {e}", exc_info=True)

    def run_stage5(
        self,
        stage4_anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run Stage 5 confidence calibration.

        Calibrates confidence scores for all anomalies using isotonic regression.
        Provides tier-based explanations and tracks calibration metrics.

        Args:
            stage4_anomalies: List of anomalies from Stage 4

        Returns:
            Dict containing:
                - anomalies_calibrated: Number of anomalies calibrated
                - calibrated_anomalies: List of anomalies with calibration data
                - calibration_summary: Calibration metrics
                - proceed_to_stage6: Boolean flag
                - timing_ms: Performance metrics
        """
        logger.info(f"Starting Stage 5 confidence calibration on {len(stage4_anomalies)} anomalies")
        stage5_start = time.time()

        # Check if calibrator is available
        if not self.confidence_calibrator:
            logger.warning("Confidence calibrator not available, skipping Stage 5")
            return {
                'anomalies_calibrated': 0,
                'calibrated_anomalies': stage4_anomalies,
                'calibration_summary': {},
                'proceed_to_stage6': True,
                'timing_ms': {'total': (time.time() - stage5_start) * 1000},
                'stage5_complete': False,
                'warning': 'Calibrator not initialized'
            }

        try:
            calibrated_anomalies = []
            calibration_adjustments = []
            tier_counts = {'HIGH': 0, 'MODERATE': 0, 'LOW': 0}

            for anomaly in stage4_anomalies:
                # Get raw confidence score (prefer stage2_confidence)
                raw_confidence = (
                    anomaly.get('stage2_confidence') or
                    anomaly.get('calibrated_confidence') or
                    anomaly.get('stage1_detection', {}).get('stage1_confidence', 0.5)
                )

                # Calibrate confidence
                calibration_result = self.confidence_calibrator.calibrate(raw_confidence)

                # Calculate adjustment
                adjustment = calibration_result['calibrated_confidence'] - raw_confidence
                calibration_adjustments.append(adjustment)

                # Count tiers
                tier = calibration_result['confidence_tier']
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

                # Add calibration data to anomaly
                calibrated_anomaly = {
                    **anomaly,
                    'confidence_calibration': {
                        'raw_confidence': calibration_result['raw_confidence'],
                        'calibrated_confidence': calibration_result['calibrated_confidence'],
                        'confidence_tier': calibration_result['confidence_tier'],
                        'tier_label': calibration_result['tier_label'],
                        'explanation': calibration_result['explanation'],
                        'adjustment': adjustment
                    }
                }

                # Log significant adjustments
                if abs(adjustment) > 0.1:
                    logger.debug(
                        f"Significant calibration adjustment for clause "
                        f"{anomaly.get('clause_number', 'unknown')}: "
                        f"{raw_confidence:.3f} → {calibration_result['calibrated_confidence']:.3f} "
                        f"({adjustment:+.3f})"
                    )

                calibrated_anomalies.append(calibrated_anomaly)

            # Calculate calibration summary
            import numpy as np
            avg_adjustment = np.mean(calibration_adjustments) if calibration_adjustments else 0.0
            std_adjustment = np.std(calibration_adjustments) if calibration_adjustments else 0.0

            calibration_summary = {
                'avg_adjustment': float(avg_adjustment),
                'std_adjustment': float(std_adjustment),
                'min_adjustment': float(min(calibration_adjustments)) if calibration_adjustments else 0.0,
                'max_adjustment': float(max(calibration_adjustments)) if calibration_adjustments else 0.0,
                'high_confidence_count': tier_counts.get('HIGH', 0),
                'moderate_confidence_count': tier_counts.get('MODERATE', 0),
                'low_confidence_count': tier_counts.get('LOW', 0),
                'calibrator_fitted': self.confidence_calibrator.is_fitted
            }

            stage5_duration = (time.time() - stage5_start) * 1000

            logger.info(
                f"Stage 5 complete: {len(calibrated_anomalies)} anomalies calibrated, "
                f"avg adjustment: {avg_adjustment:+.3f}, "
                f"tiers: HIGH={tier_counts.get('HIGH', 0)}, "
                f"MODERATE={tier_counts.get('MODERATE', 0)}, "
                f"LOW={tier_counts.get('LOW', 0)}, "
                f"took {stage5_duration:.2f}ms"
            )

            if not self.confidence_calibrator.is_fitted:
                logger.warning(
                    "Calibrator not fitted, using raw confidence scores. "
                    "Collect feedback to train calibrator."
                )

            return {
                'anomalies_calibrated': len(calibrated_anomalies),
                'calibrated_anomalies': calibrated_anomalies,
                'calibration_summary': calibration_summary,
                'proceed_to_stage6': True,
                'timing_ms': {'total': stage5_duration},
                'stage5_complete': True
            }

        except Exception as e:
            logger.error(f"Stage 5 calibration failed: {e}", exc_info=True)

            # Graceful fallback: return anomalies without calibration
            return {
                'anomalies_calibrated': 0,
                'calibrated_anomalies': stage4_anomalies,
                'calibration_summary': {},
                'proceed_to_stage6': True,
                'timing_ms': {'total': (time.time() - stage5_start) * 1000},
                'stage5_complete': False,
                'error': str(e)
            }

    def collect_user_feedback(
        self,
        anomaly_id: str,
        user_action: str,
        confidence_at_detection: float
    ) -> Dict[str, Any]:
        """
        Collect user feedback on an anomaly detection.

        This enables active learning by allowing the system to improve
        confidence calibration based on user feedback.

        Args:
            anomaly_id: Unique identifier for the anomaly
            user_action: User action - 'helpful', 'acted_on', 'dismissed', 'false_positive'
            confidence_at_detection: Confidence score shown to user

        Returns:
            Dict with feedback status and metadata
        """
        if not self.active_learning:
            logger.warning("Active learning manager not available")
            return {
                'success': False,
                'error': 'Active learning not initialized'
            }

        try:
            # Collect feedback
            self.active_learning.collect_feedback(
                anomaly_id=anomaly_id,
                user_action=user_action,
                confidence_at_detection=confidence_at_detection
            )

            # Get feedback stats
            stats = self.active_learning.get_feedback_stats()

            logger.info(
                f"Feedback collected for anomaly {anomaly_id}: {user_action}, "
                f"buffer: {stats['buffer_size']}/{stats['buffer_capacity']}"
            )

            return {
                'success': True,
                'feedback_stats': stats,
                'retrain_triggered': stats['buffer_progress'] >= 1.0
            }

        except Exception as e:
            logger.error(f"Failed to collect feedback: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def get_uncertainty_samples_for_feedback(
        self,
        anomalies: List[Dict[str, Any]],
        n_samples: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get most uncertain anomalies for targeted feedback collection.

        Uses active learning to identify anomalies where user feedback
        would be most valuable for improving the model.

        Args:
            anomalies: List of detected anomalies
            n_samples: Number of uncertain samples to return

        Returns:
            List of n_samples most uncertain anomalies
        """
        if not self.active_learning:
            logger.warning("Active learning manager not available")
            return []

        try:
            return self.active_learning.get_uncertainty_samples(
                anomalies=anomalies,
                n_samples=n_samples
            )
        except Exception as e:
            logger.error(f"Failed to get uncertainty samples: {e}")
            return []

    def set_user_preferences(self, user_preferences: Dict[str, Any]) -> None:
        """
        Set user preferences for alert ranking personalization.

        Args:
            user_preferences: Dict with user preferences
                Example:
                {
                    'priority_categories': ['data_collection', 'liability'],
                    'concern_level': 'high',  # 'low', 'medium', 'high'
                    'show_all': False
                }
        """
        if self.alert_ranker:
            self.alert_ranker.user_preferences = user_preferences
            logger.info(f"User preferences set: {user_preferences}")
        else:
            logger.warning("Alert ranker not initialized, cannot set preferences")

    def run_stage6(
        self,
        stage5_anomalies: List[Dict[str, Any]],
        compound_risks: Optional[List[Dict[str, Any]]] = None,
        document_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run Stage 6 alert ranking and budget management.

        Ranks anomalies by importance, enforces alert budget to prevent
        fatigue, and categorizes alerts for optimal user presentation.

        Args:
            stage5_anomalies: List of calibrated anomalies from Stage 5
            compound_risks: Optional list of compound risks from Stage 4
            document_context: Optional document context for industry-specific ranking

        Returns:
            Dict containing:
                - high_severity: List of high-priority alerts
                - medium_severity: List of medium-priority alerts
                - low_severity: List of low-priority alerts
                - suppressed: List of suppressed alerts
                - total_detected: Total anomalies detected
                - total_shown: Total alerts shown
                - ranking_metadata: Ranking statistics
                - timing_ms: Performance metrics
        """
        logger.info(f"Starting Stage 6 alert ranking on {len(stage5_anomalies)} anomalies")
        stage6_start = time.time()

        # Check if ranker is available
        if not self.alert_ranker:
            logger.warning("Alert ranker not available, distributing by severity field")
            high = [a for a in stage5_anomalies if a.get('severity', '').lower() in ('high', 'critical')]
            medium = [a for a in stage5_anomalies if a.get('severity', '').lower() == 'medium']
            low = [a for a in stage5_anomalies if a.get('severity', '').lower() == 'low']
            return {
                'high_severity': high,
                'medium_severity': medium,
                'low_severity': low,
                'suppressed': [],
                'total_detected': len(stage5_anomalies),
                'total_shown': len(stage5_anomalies),
                'ranking_metadata': {},
                'timing_ms': {'total': (time.time() - stage6_start) * 1000},
                'stage6_complete': False,
                'warning': 'Alert ranker not initialized'
            }

        try:
            # Run ranking and filtering
            ranking_result = self.alert_ranker.rank_and_filter(
                calibrated_anomalies=stage5_anomalies,
                compound_risks=compound_risks,
                document_context=document_context
            )

            stage6_duration = (time.time() - stage6_start) * 1000

            # Log suppression decisions
            if ranking_result['suppressed']:
                logger.info(
                    f"Suppressed {len(ranking_result['suppressed'])} low-priority alerts "
                    f"to enforce alert budget"
                )
                for suppressed in ranking_result['suppressed'][:3]:  # Log first 3
                    logger.debug(
                        f"  Suppressed: clause {suppressed.get('clause_number', 'unknown')}, "
                        f"score={suppressed.get('ranking_score', 0):.2f}"
                    )

            logger.info(
                f"Stage 6 complete: {ranking_result['total_shown']}/{ranking_result['total_detected']} "
                f"alerts shown ({len(ranking_result['high_severity'])} HIGH, "
                f"{len(ranking_result['medium_severity'])} MEDIUM, "
                f"{len(ranking_result['low_severity'])} LOW), "
                f"took {stage6_duration:.2f}ms"
            )

            return {
                **ranking_result,
                'timing_ms': {'total': stage6_duration},
                'stage6_complete': True
            }

        except Exception as e:
            logger.error(f"Stage 6 ranking failed: {e}", exc_info=True)

            # Graceful fallback: distribute by severity field
            high = [a for a in stage5_anomalies if a.get('severity', '').lower() in ('high', 'critical')]
            medium = [a for a in stage5_anomalies if a.get('severity', '').lower() == 'medium']
            low = [a for a in stage5_anomalies if a.get('severity', '').lower() == 'low']
            return {
                'high_severity': high,
                'medium_severity': medium,
                'low_severity': low,
                'suppressed': [],
                'total_detected': len(stage5_anomalies),
                'total_shown': len(stage5_anomalies),
                'ranking_metadata': {},
                'timing_ms': {'total': (time.time() - stage6_start) * 1000},
                'stage6_complete': False,
                'error': str(e)
            }

    def _calculate_overall_risk_score(
        self,
        high_severity: List[Dict[str, Any]],
        medium_severity: List[Dict[str, Any]],
        low_severity: List[Dict[str, Any]],
        compound_risks: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """
        Calculate overall document risk score on 1-10 scale.

        Factors:
        - Number of HIGH severity alerts (weight: 3.0)
        - Number of MEDIUM severity alerts (weight: 2.0)
        - Number of LOW severity alerts (weight: 1.0)
        - Number of compound risks (weight: 2.5)
        - Average calibrated confidence

        Args:
            high_severity: High severity alerts
            medium_severity: Medium severity alerts
            low_severity: Low severity alerts
            compound_risks: Optional compound risks

        Returns:
            Risk score between 1.0 and 10.0
        """
        # Count alerts by severity
        high_count = len(high_severity)
        medium_count = len(medium_severity)
        low_count = len(low_severity)
        compound_count = len(compound_risks) if compound_risks else 0

        # Weighted severity score
        severity_score = (
            (high_count * 3.0) +
            (medium_count * 2.0) +
            (low_count * 1.0) +
            (compound_count * 2.5)
        )

        # Cap at 30 for scaling
        severity_score = min(severity_score, 30.0)

        # Average confidence across all alerts
        all_alerts = high_severity + medium_severity + low_severity
        if all_alerts:
            confidences = [
                a.get('confidence_calibration', {}).get('calibrated_confidence', 0.5)
                for a in all_alerts
            ]
            avg_confidence = sum(confidences) / len(confidences)
        else:
            avg_confidence = 0.5

        # Base score from severity (0-10 scale)
        base_score = (severity_score / 30.0) * 10.0

        # Adjust by confidence (higher confidence = higher risk)
        confidence_adjustment = (avg_confidence - 0.5) * 2.0  # -1 to +1

        # Final score
        final_score = base_score + confidence_adjustment

        # Clamp to 1-10 range
        return max(1.0, min(final_score, 10.0))

    async def detect_anomalies(
        self,
        document_id: str,
        sections: List[Dict[str, Any]],
        company_name: str = "Unknown",
        service_type: str = "general",
        document_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Detect all anomalies in a document.

        Universal detection that works for ANY T&C document from ANY company.
        Identifies unusual, risky, or consumer-unfriendly clauses automatically.

        Multi-stage pipeline:
        - Stage 1: Multi-method detection (Pattern, Semantic, Statistical)
        - Stage 2: Context filtering (Industry, Service Type, Temporal)
        - Stage 3: Clustering and deduplication to reduce noise
        - Stage 4: Compound risk detection for systemic patterns
        - Stage 5: Confidence calibration with active learning
        - Stage 6: Alert ranking and budget management

        Args:
            document_id: Document identifier
            sections: List of parsed sections with clauses
            company_name: Name of the company (optional)
            service_type: Type of service for context-dependent analysis
            document_context: Optional context for Stage 2 filtering including:
                - industry: Industry type (e.g., 'children_apps', 'health_apps')
                - service_type: Service type (e.g., 'subscription', 'freemium')
                - effective_date: When T&C became effective
                - last_modified: When T&C were last modified
                - is_change: Whether this is a change from previous version

        Returns:
            Dict with complete anomaly analysis report including:
                - document_id: Document identifier
                - high_severity_alerts: High-priority alerts
                - medium_severity_alerts: Medium-priority alerts
                - low_severity_alerts: Low-priority alerts
                - overall_risk_score: Risk score (1-10)
                - compound_risks: Detected compound risks
                - pipeline_performance: Performance metrics for all stages
        """
        logger.info(f"Starting anomaly detection for document {document_id}")
        logger.info(f"Company: {company_name}, Service Type: {service_type}")
        logger.info(f"Total sections to analyze: {len(sections)}")

        # Track pipeline performance
        pipeline_start = time.time()

        all_anomalies = []
        total_clauses = 0
        full_clauses = []  # Collect all clauses for Stage 4
        document_text_parts = []  # Collect full document text for context detection

        # =====================================================================
        # LLM BATCH DETECTION: Send ALL clauses to Claude in 1-2 API calls
        # This catches risky clauses that keyword patterns miss entirely
        # =====================================================================
        llm_findings_map = {}
        try:
            llm_detector = LLMClauseDetector(self.claude)

            # Collect all clauses for batch analysis
            # Use simple sequential numeric IDs so Claude can return them exactly
            all_clause_list = []
            clause_id_counter = 0
            llm_id_map = {}  # (section_idx, clause_idx) -> sequential_id

            for section_idx, section in enumerate(sections):
                section_name = section.get("title", section.get("section_name", "Unknown Section"))
                for clause_idx, clause in enumerate(section.get("clauses", [])):
                    clause_text = clause.get("text", "")
                    clause_id_counter += 1
                    seq_id = str(clause_id_counter)
                    llm_id_map[(section_idx, clause_idx)] = seq_id
                    if clause_text and len(clause_text.strip()) >= 20:
                        all_clause_list.append({
                            "text": clause_text,
                            "section": section_name,
                            "clause_number": seq_id,
                        })

            logger.info(f"Running LLM batch detection on {len(all_clause_list)} clauses...")
            llm_findings = await llm_detector.detect_risky_clauses(
                clauses=all_clause_list,
                company_name=company_name,
                service_type=service_type,
            )

            # Index by clause_number for O(1) lookup
            llm_findings_map = {f["clause_number"]: f for f in llm_findings}
            logger.info(f"LLM batch detection complete: {len(llm_findings_map)} risky clauses identified")

        except Exception as e:
            logger.warning(f"LLM batch detection failed, continuing with keyword-only: {e}")
            llm_findings_map = {}

        for section_idx, section in enumerate(sections):
            section_name = section.get("title", section.get("section_name", "Unknown Section"))
            clauses = section.get("clauses", [])
            total_clauses += len(clauses)

            logger.info(
                f"Analyzing section '{section_name}' with {len(clauses)} clauses"
            )

            for clause_idx, clause in enumerate(clauses):
                clause_text = clause.get("text", "")
                clause_number = clause.get(
                    "clause_number", str(llm_id_map.get((section_idx, clause_idx), clause_idx))
                )
                # Use same sequential ID as LLM batch for consistent lookup
                llm_clause_id = llm_id_map.get((section_idx, clause_idx), "")

                # Collect text for context detection
                if clause_text:
                    document_text_parts.append(clause_text)

                if not clause_text or len(clause_text.strip()) < 20:
                    continue  # Skip only empty or very short clauses (< 20 chars)

                logger.info(
                    f"Analyzing clause {clause_number}: {clause_text[:100]}..."
                )

                # Check if LLM already flagged this clause (fast path)
                llm_finding_early = llm_findings_map.get(llm_clause_id)

                if llm_finding_early:
                    # FAST PATH: LLM already analyzed this clause — skip expensive multi-stage detection
                    # Just run lightweight keyword detection for indicator data
                    detected_indicators = self.risk_indicators.detect_indicators(
                        clause_text=clause_text,
                        service_type=service_type
                    )
                    # Compute confidence from indicators rather than hardcoding
                    indicator_confidence = min(0.9, 0.5 + len(detected_indicators) * 0.1)
                    multi_stage_results = {
                        'detections': [{'method': 'pattern_based', 'indicators': detected_indicators, 'count': len(detected_indicators)}],
                        'method_confidences': {'pattern_based': indicator_confidence if detected_indicators else 0.0},
                        'stage1_confidence': indicator_confidence,
                        'proceed_to_stage2': True,  # LLM flagged it, so always proceed
                        'flags': {'pattern': bool(detected_indicators), 'semantic': False, 'statistical': False}
                    }
                    logger.info(f"  LLM-flagged clause — fast path (skipped semantic/statistical/RAG detection)")
                else:
                    # FULL PATH: Run multi-stage detection (Pattern + Semantic + Statistical)
                    clause_dict = {'text': clause_text, 'section': section_name}
                    multi_stage_results = await self._run_multi_stage_detection(
                        clause_text=clause_text,
                        clause_dict=clause_dict,
                        service_type=service_type
                    )

                    # Extract pattern-based indicators for backward compatibility
                    pattern_detection = next(
                        (d for d in multi_stage_results['detections'] if d['method'] == 'pattern_based'),
                        {'indicators': [], 'count': 0}
                    )
                    detected_indicators = pattern_detection.get('indicators', [])

                # Collect full clauses for Stage 4 compound risk detection
                full_clauses.append({
                    'text': clause_text,
                    'section': section_name,
                    'clause_number': clause_number,
                    'stage1_results': multi_stage_results
                })

                logger.info(
                    f"Clause {clause_number}: Multi-stage detection complete - "
                    f"Stage1 confidence={multi_stage_results['stage1_confidence']:.2f}, "
                    f"Proceed to Stage2={multi_stage_results['proceed_to_stage2']}"
                )
                logger.info(
                    f"  Flags: pattern={multi_stage_results['flags']['pattern']}, "
                    f"semantic={multi_stage_results['flags']['semantic']}, "
                    f"statistical={multi_stage_results['flags']['statistical']}"
                )

                if detected_indicators:
                    indicator_summary = [
                        f"{ind['indicator']} ({ind['severity']})"
                        for ind in detected_indicators
                    ]
                    logger.info(f"  Pattern indicators: {indicator_summary}")

                # STEP 2: Determine if clause is suspicious FIRST (before expensive operations)
                has_high_risk = any(
                    ind["severity"] == "high" for ind in detected_indicators
                )
                has_medium_risk = any(
                    ind["severity"] == "medium" for ind in detected_indicators
                )

                # Use multi-stage detection OR LLM detection to decide if suspicious
                llm_finding = llm_finding_early  # Already looked up above
                is_suspicious = multi_stage_results['proceed_to_stage2'] or (llm_finding is not None)

                # STEP 2a: Augment with semantic detection ONLY for suspicious clauses
                # that weren't already flagged by LLM (LLM analysis is sufficient)
                if is_suspicious and not llm_finding_early:
                    if not self._semantic_initialized:
                        try:
                            await self.semantic_detector.initialize()
                            self._semantic_initialized = True
                        except Exception as e:
                            logger.warning(f"Semantic detector initialization failed: {e}")

                    if self._semantic_initialized:
                        try:
                            detected_indicators = (
                                await self.semantic_detector.augment_indicators(
                                    clause_text=clause_text,
                                    keyword_indicators=detected_indicators,
                                )
                            )
                            # Update risk flags after semantic augmentation
                            has_high_risk = any(
                                ind["severity"] == "high" for ind in detected_indicators
                            )
                            has_medium_risk = any(
                                ind["severity"] == "medium" for ind in detected_indicators
                            )
                            logger.debug(
                                f"Clause {clause_number}: Total indicators after semantic detection: "
                                f"{len(detected_indicators)}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Semantic detection failed for clause {clause_number}: {e}"
                            )
                            # Continue with keyword indicators only

                # STEP 2b: Run RAG for all suspicious clauses (including LLM-flagged)
                # to get prevalence data for severity calibration
                rag_result = None
                prevalence = 0.5  # Default: neutral prevalence

                if is_suspicious:
                    if self.rag_detector:
                        try:
                            rag_result = await self.rag_detector.analyze_clause(
                                clause_text=clause_text,
                                clause_number=clause_number,
                                section=section_name,
                                industry=service_type,
                                service_type=service_type,
                            )
                            prevalence = rag_result.corpus_prevalence
                            logger.info(
                                f"Clause {clause_number}: RAG Prevalence = {prevalence:.2%} "
                                f"(similar: {rag_result.similar_clauses_found}/{rag_result.total_corpus_docs})"
                            )
                            logger.info(
                                f"  RAG Context: {[t.value for t in rag_result.context_tags]}"
                            )
                            logger.info(
                                f"  RAG Risk: {rag_result.risk_score:.1f}/10 ({rag_result.risk_level})"
                            )
                        except Exception as e:
                            logger.warning(f"RAG detection failed for clause {clause_number}: {e}")
                            rag_result = None

                    # Fallback to legacy prevalence calculation if RAG failed
                    if rag_result is None:
                        try:
                            prevalence = await self.prevalence_calc.calculate_prevalence(
                                clause_text=clause_text, clause_type=section_name
                            )
                            logger.info(
                                f"Clause {clause_number}: Legacy Prevalence = {prevalence:.2%} (threshold: 30%)"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Prevalence calculation failed for clause {clause_number}: {e}"
                            )
                            prevalence = 0.1  # Unknown but probably unusual

                is_unusual = prevalence < 0.30

                logger.info(
                    f"Clause {clause_number}: Decision - is_suspicious={is_suspicious} "
                    f"(keywords: {multi_stage_results['proceed_to_stage2']}, llm: {llm_finding is not None})"
                )
                logger.info(
                    f"  Reasons: unusual={is_unusual}, high_risk={has_high_risk}, "
                    f"medium_risk={has_medium_risk}, any_indicators={len(detected_indicators) > 0}"
                )

                logger.debug(
                    f"Clause {clause_number}: Unusual={is_unusual}, "
                    f"HighRisk={has_high_risk}, MediumRisk={has_medium_risk}, "
                    f"Suspicious={is_suspicious}, Indicators={len(detected_indicators)}"
                )

                if is_suspicious:
                    # STEP 4: Determine severity from INDICATORS + LLM + RAG CONTEXT
                    # Check RAG context tags for severity adjustment
                    is_platform_required = False
                    is_industry_standard = False
                    is_user_triggered = False

                    if rag_result and rag_result.context_tags:
                        is_platform_required = ContextTag.REQUIRED_BY_PLATFORM in rag_result.context_tags
                        is_industry_standard = ContextTag.INDUSTRY_STANDARD in rag_result.context_tags
                        is_user_triggered = ContextTag.USER_TRIGGERED in rag_result.context_tags

                    # Base severity from keyword indicators
                    if has_high_risk:
                        keyword_severity = "high"
                    elif has_medium_risk:
                        keyword_severity = "medium"
                    elif is_unusual:
                        keyword_severity = "low"
                    else:
                        keyword_severity = "medium"

                    # Merge severity: LLM is primary (better calibrated), keyword only escalates critical
                    if llm_finding:
                        llm_severity = llm_finding.get("severity", "medium")
                        # Trust LLM severity, but let keywords escalate to critical
                        if keyword_severity == "critical" and llm_severity != "critical":
                            severity = "critical"
                            logger.info(f"  Keywords escalated to CRITICAL (LLM was: {llm_severity})")
                        else:
                            severity = llm_severity
                            logger.info(f"  Using LLM severity: {severity} (keyword was: {keyword_severity})")
                    else:
                        severity = keyword_severity
                        logger.info(f"  Using keyword severity: {severity} (no LLM finding)")

                    # RAG CONTEXT ADJUSTMENT: Reduce severity for standard clauses
                    # Never downgrade critical — those represent fundamental consumer harm
                    if is_platform_required and severity != "critical":
                        severity = "low"
                        logger.info(f"  RAG adjusted severity to LOW (platform-required)")
                    elif is_industry_standard and prevalence >= 0.50:
                        if severity == "high":
                            severity = "medium"
                            logger.info(f"  RAG adjusted severity HIGH→MEDIUM (industry standard, {prevalence:.0%} prevalence)")
                        elif severity == "medium":
                            severity = "low"
                            logger.info(f"  RAG adjusted severity MEDIUM→LOW (industry standard, {prevalence:.0%} prevalence)")
                    elif is_user_triggered and severity == "high":
                        severity = "medium"
                        logger.info(f"  RAG adjusted severity HIGH→MEDIUM (user-triggered liability)")
                    elif prevalence >= 0.70 and severity == "high":
                        severity = "medium"
                        logger.info(f"  Prevalence adjusted severity HIGH→MEDIUM ({prevalence:.0%} prevalence)")

                    # STEP 5: Get explanation — from LLM batch (preferred) or fallback
                    # NO per-clause Claude API calls — the LLM batch handles all explanations
                    if llm_finding and llm_finding.get("explanation"):
                        # LLM batch already provided explanation
                        explanation = llm_finding["explanation"]
                        consumer_impact = llm_finding.get("consumer_impact", "")
                        recommendation = llm_finding.get("recommendation", "")
                        risk_category = llm_finding.get("risk_category", "other")
                        logger.info(f"Clause {clause_number}: Using LLM batch explanation (saved API call)")
                    else:
                        # Keyword-only finding — use indicator-based explanation (no API call)
                        explanation = self._generate_fallback_explanation(
                            detected_indicators, prevalence
                        )
                        consumer_impact = "This clause may negatively impact consumers."
                        recommendation = (
                            "Review this clause carefully before accepting."
                        )
                        risk_category = (
                            detected_indicators[0]["indicator"]
                            if detected_indicators
                            else "other"
                        )
                        logger.info(f"Clause {clause_number}: Using keyword-based explanation (no API call)")

                    # ALWAYS flag suspicious clauses
                    anomaly = {
                        "document_id": document_id,
                        "section": section_name,
                        "clause_number": clause_number,
                        "clause_text": clause_text,
                        "severity": severity,
                        "severity_source": "llm" if llm_finding else "keyword",
                        "explanation": explanation,
                        "consumer_impact": consumer_impact,
                        "recommendation": recommendation,
                        "risk_category": risk_category,
                        "prevalence": prevalence,
                        "prevalence_display": f"{prevalence*100:.0f}%",
                        "detected_indicators": [
                            {
                                "name": ind["indicator"],
                                "description": ind["description"],
                                "severity": ind["severity"],
                            }
                            for ind in detected_indicators
                        ],
                        "comparison": (
                            f"Found in only {prevalence*100:.0f}% of similar services"
                            if prevalence < 0.30
                            else f"Found in {prevalence*100:.0f}% of similar services"
                        ),
                        # NEW: Multi-stage detection results
                        "stage1_detection": {
                            "detections": multi_stage_results['detections'],
                            "method_confidences": multi_stage_results['method_confidences'],
                            "stage1_confidence": multi_stage_results['stage1_confidence'],
                            "proceed_to_stage2": multi_stage_results['proceed_to_stage2'],
                            "flags": multi_stage_results['flags']
                        },
                        # NEW: RAG context data for accurate risk assessment
                        "rag_context": {
                            "context_tags": [t.value for t in rag_result.context_tags] if rag_result else [],
                            "context_explanation": rag_result.context_explanation if rag_result else "",
                            "harm_score": rag_result.harm_score if rag_result else 5.0,
                            "unusualness_score": rag_result.unusualness_score if rag_result else 5.0,
                            "enforceability_score": rag_result.enforceability_score if rag_result else 5.0,
                            "rag_risk_score": rag_result.risk_score if rag_result else None,
                            "rag_risk_level": rag_result.risk_level if rag_result else None,
                            "is_platform_required": is_platform_required,
                            "is_industry_standard": is_industry_standard,
                            "is_user_triggered": is_user_triggered,
                        } if rag_result else None
                    }

                    all_anomalies.append(anomaly)
                    logger.info(
                        f"✓ Anomaly detected: {clause_number} ({severity} risk - {len(detected_indicators)} indicators)"
                    )

        logger.info(
            f"Stage 1 complete: {len(all_anomalies)} anomalies found out of {total_clauses} clauses"
        )

        # STAGE 2: Apply context filtering
        if document_context is None:
            # Use defaults if no context provided
            document_context = {
                'industry': 'saas',
                'service_type': service_type,
                'is_change': False
            }

        # Build full document text for context detection
        full_document_text = "\n\n".join(document_text_parts)

        # Run Stage 2 filtering (with Context-Aware Layer)
        all_anomalies = await self.run_stage2(
            stage1_results=all_anomalies,
            document_context=document_context,
            document_text=full_document_text
        )

        # Capture Stage 2 metrics BEFORE Stage 3 clustering changes the list
        stage2_passed_count = sum(1 for a in all_anomalies if a.get('proceed_to_stage3', False))
        stage2_filtered_count = len(all_anomalies) - stage2_passed_count

        logger.info(
            f"Stage 2 complete: {stage2_passed_count} "
            f"anomalies proceeding to Stage 3, {stage2_filtered_count} filtered out"
        )

        # STAGE 3: Apply clustering and deduplication
        stage3_result = self.run_stage3(all_anomalies)

        # Flatten clusters and noise back into anomaly list for backward compatibility
        # Keep Stage 3 metadata attached to anomalies
        clustered_anomalies = []

        # Add representative anomalies from clusters
        for cluster in stage3_result['clusters']:
            clustered_anomalies.append(cluster['representative_anomaly'])

        # Add noise anomalies
        clustered_anomalies.extend(stage3_result['noise'])

        # Store Stage 3 results for document-level reporting
        for anomaly in clustered_anomalies:
            anomaly['_stage3_result'] = {
                'reduction_ratio': stage3_result['reduction_ratio'],
                'original_count': stage3_result['original_count'],
                'final_count': stage3_result['final_count'],
                'n_clusters': stage3_result.get('n_clusters', 0),
                'n_noise': stage3_result.get('n_noise', 0)
            }

        # Replace all_anomalies with clustered results
        all_anomalies = clustered_anomalies

        logger.info(
            f"Stage 3 complete: Reduced from {stage3_result['original_count']} to "
            f"{stage3_result['final_count']} anomalies ({stage3_result['reduction_ratio']:.1%} reduction)"
        )

        # STAGE 4: Detect compound risks using enhanced detector
        stage4_result = self.run_stage4(
            stage3_results=all_anomalies,
            full_clauses=full_clauses
        )

        # Store Stage 4 results for document-level reporting
        for anomaly in all_anomalies:
            anomaly['_stage4_result'] = {
                'compound_risk_score': stage4_result['compound_risk_assessment']['compound_risk_score'],
                'compound_risk_level': stage4_result['compound_risk_assessment']['compound_risk_level'],
                'patterns_detected': stage4_result['patterns_detected']
            }
            # Compound risks already added to individual anomalies by run_stage4()

        # Store compound risks summary for document-level reporting
        for anomaly in all_anomalies:
            if "_compound_risks_summary" not in anomaly:
                anomaly["_compound_risks_summary"] = stage4_result['compound_risks']

        logger.info(
            f"Stage 4 complete: {len(stage4_result['compound_risks'])} compound patterns detected, "
            f"risk level: {stage4_result['compound_risk_assessment']['compound_risk_level']}"
        )

        # STAGE 5: Confidence Calibration
        stage5_result = self.run_stage5(
            stage4_anomalies=all_anomalies
        )

        # Replace anomalies with calibrated versions
        all_anomalies = stage5_result['calibrated_anomalies']

        # Store Stage 5 results for document-level reporting
        for anomaly in all_anomalies:
            anomaly['_stage5_result'] = {
                'calibration_summary': stage5_result['calibration_summary'],
                'stage5_complete': stage5_result['stage5_complete']
            }

        logger.info(
            f"Stage 5 complete: {stage5_result['anomalies_calibrated']} anomalies calibrated"
        )

        if stage5_result.get('calibration_summary'):
            summary = stage5_result['calibration_summary']
            logger.info(
                f"  Calibration: avg_adjustment={summary.get('avg_adjustment', 0):+.3f}, "
                f"HIGH={summary.get('high_confidence_count', 0)}, "
                f"MODERATE={summary.get('moderate_confidence_count', 0)}, "
                f"LOW={summary.get('low_confidence_count', 0)}"
            )

        # STAGE 6: Alert Ranking & Budget Management
        stage6_result = self.run_stage6(
            stage5_anomalies=all_anomalies,
            compound_risks=stage4_result.get('compound_risks', []),
            document_context=document_context
        )

        # Calculate overall risk score
        overall_risk_score = self._calculate_overall_risk_score(
            high_severity=stage6_result['high_severity'],
            medium_severity=stage6_result['medium_severity'],
            low_severity=stage6_result['low_severity'],
            compound_risks=stage4_result.get('compound_risks', [])
        )

        logger.info(
            f"Stage 6 complete: Alert ranking finished, "
            f"overall risk score: {overall_risk_score:.1f}/10"
        )

        # Calculate total pipeline duration
        pipeline_end = time.time()
        total_pipeline_duration = (pipeline_end - pipeline_start) * 1000

        # Build comprehensive pipeline performance metrics
        # Calculate stage1_initial before filtering
        stage1_initial = sum(1 for a in all_anomalies if a.get('stage1_detection'))

        pipeline_performance = {
            'stage1_detections': stage1_initial,
            'stage2_passed': stage2_passed_count,
            'stage2_filtered_out': stage2_filtered_count,
            'stage3_clustered': stage3_result.get('final_count', 0),
            'stage4_compounds': len(stage4_result.get('compound_risks', [])),
            'stage5_calibrated': stage5_result.get('anomalies_calibrated', 0),
            'stage6_ranked': stage6_result.get('total_shown', 0),
            'total_clauses_analyzed': total_clauses,
            'total_processing_time_ms': round(total_pipeline_duration, 2)
        }

        # Run competitive analysis to benchmark against industry peers
        competitive_benchmark = None
        try:
            competitive_analyzer = CompetitiveAnalyzer()

            # Extract detected risk categories from anomalies
            detected_categories = list(set(
                a.get('risk_category', '') for a in all_anomalies
                if a.get('risk_category')
            ))

            # Get industry from context detection
            industry = document_context.get('industry', 'general') if document_context else 'general'

            competitive_benchmark = competitive_analyzer.analyze(
                document_risk_score=overall_risk_score,
                industry=industry,
                company_name=company_name,
                detected_risk_categories=detected_categories,
                high_severity_count=len(stage6_result['high_severity']),
                medium_severity_count=len(stage6_result['medium_severity'])
            )

            logger.info(
                f"Competitive analysis: {industry} industry, "
                f"percentile={competitive_benchmark.get('percentile_rank', 'N/A')}, "
                f"comparison={competitive_benchmark.get('risk_comparison', 'unknown')}"
            )
        except Exception as e:
            logger.warning(f"Competitive analysis failed: {e}")
            competitive_benchmark = None

        # INVERTED FUNNEL: Enrich anomalies with threat level and commonness
        inverted_funnel_data = self._enrich_with_inverted_funnel(
            _all_anomalies=all_anomalies,
            high_severity=stage6_result['high_severity'],
            medium_severity=stage6_result['medium_severity'],
            low_severity=stage6_result['low_severity'],
            _industry=document_context.get('industry', 'general') if document_context else 'general'
        )

        final_report = {
            'document_id': document_id,
            'company_name': company_name,
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'overall_risk_score': round(overall_risk_score, 1),
            'high_severity_alerts': stage6_result['high_severity'],
            'medium_severity_alerts': stage6_result['medium_severity'],
            'low_severity_alerts': stage6_result['low_severity'],
            'suppressed_alerts_count': len(stage6_result['suppressed']) + stage2_filtered_count,
            'total_anomalies_detected': stage6_result['total_detected'],
            'total_alerts_shown': stage6_result['total_shown'],
            'compound_risks': stage4_result.get('compound_risks', []),
            'ranking_metadata': stage6_result.get('ranking_metadata', {}),
            'pipeline_performance': pipeline_performance,
            'competitive_benchmark': competitive_benchmark,
            # NEW: Inverted Funnel categorization
            'inverted_funnel': inverted_funnel_data
        }

        # Log pipeline summary
        logger.info("=" * 60)
        logger.info("ANOMALY DETECTION PIPELINE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Document: {document_id}")
        logger.info(f"Overall Risk Score: {overall_risk_score:.1f}/10")
        logger.info(f"Alerts: {stage6_result['total_shown']}/{stage6_result['total_detected']} shown")
        logger.info(f"  HIGH: {len(stage6_result['high_severity'])}")
        logger.info(f"  MEDIUM: {len(stage6_result['medium_severity'])}")
        logger.info(f"  LOW: {len(stage6_result['low_severity'])}")
        logger.info(f"  SUPPRESSED: {len(stage6_result['suppressed'])}")
        logger.info(f"Compound Risks: {len(stage4_result.get('compound_risks', []))}")
        logger.info(f"Total Processing Time: {total_pipeline_duration:.2f}ms")
        logger.info("=" * 60)

        return final_report

    def _generate_fallback_explanation(
        self, detected_indicators: List[Dict], prevalence: float
    ) -> str:
        """
        Generate basic explanation when Claude fails (Fallback).

        Args:
            detected_indicators: List of detected risk indicators
            prevalence: Prevalence score (0-1)

        Returns:
            Basic explanation string
        """
        if not detected_indicators:
            return f"This clause is unusual (found in only {prevalence*100:.0f}% of similar services)."

        # Build explanation from indicators
        indicator_names = [
            ind["description"] for ind in detected_indicators[:3]
        ]  # Top 3

        if len(indicator_names) == 1:
            explanation = (
                f"This clause contains a concerning pattern: {indicator_names[0]}."
            )
        elif len(indicator_names) == 2:
            explanation = f"This clause contains concerning patterns: {indicator_names[0]} and {indicator_names[1]}."
        else:
            explanation = f"This clause contains multiple concerning patterns including: {indicator_names[0]}, {indicator_names[1]}, and {indicator_names[2]}."

        if prevalence < 0.30:
            explanation += f" Additionally, this clause is rare (found in only {prevalence*100:.0f}% of similar services)."

        return explanation

    def _enrich_with_inverted_funnel(
        self,
        _all_anomalies: List[Dict[str, Any]],
        high_severity: List[Dict[str, Any]],
        medium_severity: List[Dict[str, Any]],
        low_severity: List[Dict[str, Any]],
        _industry: str = "general",
    ) -> Dict[str, Any]:
        """
        Enrich anomalies with inverted funnel data (threat level + commonness).

        Takes the existing anomalies and adds:
        - threat_level: Based on consumer harm (CRITICAL/HIGH/MEDIUM/LOW/INFO)
        - commonness_level: How common the pattern is (UNIVERSAL to VERY_RARE)
        - display_category: Combined categorization for UI
        - user_importance_score: Ranking score for user relevance

        Args:
            all_anomalies: All detected anomalies
            high_severity: High severity alerts from Stage 6
            medium_severity: Medium severity alerts from Stage 6
            low_severity: Low severity alerts from Stage 6
            industry: Industry for commonness context

        Returns:
            Dictionary with inverted funnel categorized anomalies
        """
        from app.core.constants import (
            PATTERN_THREAT_LEVELS,
            CommonnessThresholds,
            UserImportanceConfig,
        )

        # Combine all alerts
        all_alerts = high_severity + medium_severity + low_severity

        # Categorize by display category
        unusual_dangerous = []
        common_dangerous = []
        unusual_minor = []
        standard_terms = []

        # Track distributions
        threat_distribution = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0
        }
        commonness_distribution = {
            'universal': 0,
            'very_common': 0,
            'common': 0,
            'uncommon': 0,
            'rare': 0,
            'very_rare': 0
        }

        # Pattern frequency
        pattern_counts = {}

        for alert in all_alerts:
            # Extract pattern/risk_category
            risk_category = alert.get('risk_category', 'other')
            detected_indicators = alert.get('detected_indicators', [])
            patterns = [ind.get('name', '') for ind in detected_indicators] if detected_indicators else [risk_category]

            # Get threat score (use highest from patterns)
            threat_score = 5.0  # Default medium
            for pattern in patterns:
                score = PATTERN_THREAT_LEVELS.get(pattern, 5.0)
                if score > threat_score:
                    threat_score = score

                # Count patterns
                if pattern:
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

            # Get commonness from prevalence
            prevalence = alert.get('prevalence', 0.30)
            commonness_level = CommonnessThresholds.get_level(prevalence)

            # NEW: Use RAG context to adjust threat score
            # This prevents overinflation of standard industry clauses
            rag_context = alert.get('rag_context')
            if rag_context:
                # Platform-required clauses (Apple, Google) = reduce threat significantly
                if rag_context.get('is_platform_required'):
                    threat_score = min(threat_score, 2.0)  # Cap at INFO level
                    logger.debug(f"RAG: Reduced threat score to {threat_score} (platform-required)")
                # Industry standard + high prevalence = reduce threat
                elif rag_context.get('is_industry_standard') and prevalence >= 0.70:
                    threat_score = min(threat_score, 4.0)  # Cap at LOW level
                    logger.debug(f"RAG: Reduced threat score to {threat_score} (industry standard)")
                # User-triggered liability = slightly reduce
                elif rag_context.get('is_user_triggered') and threat_score > 6.0:
                    threat_score = threat_score * 0.85  # 15% reduction
                    logger.debug(f"RAG: Reduced threat score to {threat_score} (user-triggered)")
                # Use RAG harm score if available and lower
                elif rag_context.get('rag_risk_score') and rag_context['rag_risk_score'] < threat_score:
                    # Blend RAG score with pattern score (60% RAG, 40% pattern)
                    threat_score = (rag_context['rag_risk_score'] * 0.6) + (threat_score * 0.4)
                    logger.debug(f"RAG: Blended threat score to {threat_score}")

            # Calculate threat level
            threat_level = get_threat_level_from_score(threat_score)

            # Calculate user importance score
            importance_score = UserImportanceConfig.calculate_importance(
                threat_score=threat_score,
                commonness=commonness_level
            )

            # Get display category
            display_category = get_display_category(threat_level, commonness_level)

            # Get human-readable threat description
            threat_descriptions = {
                ThreatLevel.CRITICAL: "This clause poses serious risk to consumers",
                ThreatLevel.HIGH: "This clause significantly impacts your rights",
                ThreatLevel.MEDIUM: "This clause is worth knowing about",
                ThreatLevel.LOW: "Standard clause with some consumer implications",
                ThreatLevel.INFO: "Standard legal boilerplate",
            }

            # Enrich the alert with inverted funnel data
            enriched_alert = {
                **alert,
                'threat_level': threat_level.value,
                'threat_score': threat_score,
                'commonness_level': commonness_level.value,
                'commonness_percentage': prevalence * 100,
                'display_category': display_category.value,
                'user_importance_score': importance_score,
                'why_threatening': threat_descriptions.get(threat_level, ""),
            }

            # Update distributions
            threat_distribution[threat_level.value] += 1
            commonness_distribution[commonness_level.value] += 1

            # Categorize into display buckets
            if display_category == DisplayCategory.UNUSUAL_DANGEROUS:
                unusual_dangerous.append(enriched_alert)
            elif display_category == DisplayCategory.COMMON_DANGEROUS:
                common_dangerous.append(enriched_alert)
            elif display_category == DisplayCategory.UNUSUAL_MINOR:
                unusual_minor.append(enriched_alert)
            else:
                standard_terms.append(enriched_alert)

        # Sort each category by importance score
        unusual_dangerous.sort(key=lambda x: x.get('user_importance_score', 0), reverse=True)
        common_dangerous.sort(key=lambda x: x.get('user_importance_score', 0), reverse=True)
        unusual_minor.sort(key=lambda x: x.get('user_importance_score', 0), reverse=True)
        standard_terms.sort(key=lambda x: x.get('user_importance_score', 0), reverse=True)

        # Top patterns
        top_patterns = sorted(
            [{'pattern': p, 'count': c} for p, c in pattern_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]

        logger.info(
            f"Inverted Funnel enrichment: "
            f"UNUSUAL_DANGEROUS={len(unusual_dangerous)}, "
            f"COMMON_DANGEROUS={len(common_dangerous)}, "
            f"UNUSUAL_MINOR={len(unusual_minor)}, "
            f"STANDARD_TERMS={len(standard_terms)}"
        )

        return {
            'unusual_dangerous': unusual_dangerous,
            'common_dangerous': common_dangerous,
            'unusual_minor': unusual_minor,
            'standard_terms': standard_terms,
            'category_summary': {
                'unusual_dangerous_count': len(unusual_dangerous),
                'common_dangerous_count': len(common_dangerous),
                'unusual_minor_count': len(unusual_minor),
                'standard_terms_count': len(standard_terms),
            },
            'threat_distribution': threat_distribution,
            'commonness_distribution': commonness_distribution,
            'top_patterns': top_patterns,
        }

    def calculate_document_risk_score(
        self, anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate overall risk score for the document.

        Universal risk scoring formula that works for any T&C document:
        - Considers anomaly count, severity distribution, and category diversity
        - Returns score from 1-10 and risk level (Low/Medium/High)

        Args:
            anomalies: List of detected anomalies

        Returns:
            Dictionary with risk_score (1-10), risk_level, and breakdown
        """
        if not anomalies:
            return {
                "risk_score": 1.0,
                "risk_level": "Low",
                "risk_label": "Low Risk",
                "explanation": "No significant anomalies detected. This document appears to have standard terms.",
                "breakdown": {
                    "anomaly_count": 0,
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                },
            }

        # Count by severity
        high_count = sum(1 for a in anomalies if a["severity"] == "high")
        medium_count = sum(1 for a in anomalies if a["severity"] == "medium")
        low_count = sum(1 for a in anomalies if a["severity"] == "low")
        total_count = len(anomalies)

        # Count unique risk categories
        categories = set(a.get("risk_category", "other") for a in anomalies)
        category_diversity = len(categories)

        # SCORING FORMULA (1-10 scale):
        # Base score from anomaly count
        count_score = min(
            total_count / 2.0, 4.0
        )  # Max 4 points (1-8 anomalies = 0.5-4 pts)

        # Severity weighting
        severity_score = (
            (high_count * 0.75) + (medium_count * 0.35) + (low_count * 0.15)
        )
        severity_score = min(severity_score, 4.0)  # Max 4 points

        # Category diversity (more categories = more systemic issues)
        diversity_score = min(category_diversity * 0.5, 2.0)  # Max 2 points

        # Total score (1-10)
        raw_score = count_score + severity_score + diversity_score
        risk_score = max(1.0, min(raw_score, 10.0))  # Clamp between 1-10

        # Determine risk level
        if risk_score >= 7.0:
            risk_level = "High"
            risk_label = "High Risk"
            explanation = f"This document contains {total_count} concerning clauses with {high_count} high-severity issues. Multiple problematic areas detected across {category_diversity} different categories. Exercise extreme caution."
        elif risk_score >= 4.0:
            risk_level = "Medium"
            risk_label = "Medium Risk"
            explanation = f"This document contains {total_count} concerning clauses. While not extremely aggressive, there are {high_count + medium_count} issues worth reviewing carefully before accepting."
        else:
            risk_level = "Low"
            risk_label = "Low to Medium Risk"
            explanation = f"This document contains {total_count} minor issues. Most terms appear standard, but review the flagged clauses for your specific situation."

        logger.info(f"Document risk score: {risk_score:.1f}/10 ({risk_level})")
        logger.info(
            f"Breakdown: {total_count} anomalies ({high_count} high, {medium_count} medium, {low_count} low)"
        )

        return {
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "risk_label": risk_label,
            "explanation": explanation,
            "breakdown": {
                "anomaly_count": total_count,
                "high_severity": high_count,
                "medium_severity": medium_count,
                "low_severity": low_count,
                "category_diversity": category_diversity,
                "categories": list(categories),
            },
            "scoring_details": {
                "count_contribution": round(count_score, 2),
                "severity_contribution": round(severity_score, 2),
                "diversity_contribution": round(diversity_score, 2),
            },
        }

    async def generate_report(
        self, document_id: str, anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate complete anomaly report for document.

        Args:
            document_id: Document identifier
            anomalies: List of detected anomalies

        Returns:
            Comprehensive report with risk score and categorized anomalies
        """
        logger.info(f"Generating report for document {document_id}")

        # Categorize anomalies by severity
        high_risk = [a for a in anomalies if a["severity"] == "high"]
        medium_risk = [a for a in anomalies if a["severity"] == "medium"]
        low_risk = [a for a in anomalies if a["severity"] == "low"]

        # Calculate overall risk score
        risk_assessment = self.calculate_document_risk_score(anomalies)

        # Group by category
        by_category = {}
        for anomaly in anomalies:
            category = anomaly.get("risk_category", "other")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(anomaly)

        report = {
            "document_id": document_id,
            "overall_risk": risk_assessment,
            "total_anomalies": len(anomalies),
            "high_risk_count": len(high_risk),
            "medium_risk_count": len(medium_risk),
            "low_risk_count": len(low_risk),
            "high_risk_anomalies": high_risk,
            "medium_risk_anomalies": medium_risk,
            "low_risk_anomalies": low_risk,
            "by_category": by_category,
            "top_concerns": (
                high_risk[:3] if high_risk else medium_risk[:3]
            ),  # Top 3 most critical
        }

        logger.info(
            f"Report generated: {len(anomalies)} anomalies, Risk Score: {risk_assessment['risk_score']}/10"
        )

        return report
