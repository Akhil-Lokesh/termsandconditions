"""
GPT-5 Two-Stage Analysis Orchestrator.

Coordinates the two-stage cascade analysis:
- Stage 1: Fast GPT-5-Nano classification ($0.0006/doc)
- Stage 2: Deep GPT-5 analysis ($0.015/doc) - only if confidence < 0.55

Target blended cost: $0.0039/doc (assuming ~24% escalation rate)
73% cost savings vs single-stage GPT-4 analysis.
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.services.gpt5_stage1_classifier import GPT5Stage1Classifier
from app.services.gpt5_stage2_analyzer import GPT5Stage2Analyzer
from app.services.analysis_cache_manager import AnalysisCacheManager, SmartCacheStrategy
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class AnalysisResult:
    """Result from two-stage analysis."""

    document_id: str
    overall_risk: str  # low, medium, high
    confidence: float  # 0.0-1.0
    stage: int  # 1 or 2
    clauses: List[Dict[str, Any]]
    summary: str
    cost: float  # USD
    processing_time: float  # seconds
    stage1_result: Optional[Dict[str, Any]] = None
    stage2_result: Optional[Dict[str, Any]] = None
    escalated: bool = False
    timestamp: str = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "document_id": self.document_id,
            "overall_risk": self.overall_risk,
            "confidence": self.confidence,
            "stage": self.stage,
            "clauses": self.clauses,
            "summary": self.summary,
            "cost": self.cost,
            "processing_time": self.processing_time,
            "escalated": self.escalated,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
            "metadata": {
                "stage1_confidence": (
                    self.stage1_result.get("confidence") if self.stage1_result else None
                ),
                "stage2_validated": self.stage2_result is not None,
            },
        }


class GPT5TwoStageOrchestrator:
    """
    Orchestrates two-stage T&C analysis.

    Routing logic:
    1. Always run Stage 1 first (fast & cheap)
    2. If confidence >= 0.55: Return Stage 1 result
    3. If confidence < 0.55: Escalate to Stage 2
    4. Return final result with cost tracking
    """

    # Confidence threshold for Stage 1 → Stage 2 escalation
    ESCALATION_THRESHOLD = 0.55

    # Target metrics
    TARGET_ESCALATION_RATE = 0.24  # 24% of documents escalate to Stage 2
    TARGET_BLENDED_COST = 0.0039  # $0.0039 per document average

    def __init__(self, enable_cache: bool = True):
        """
        Initialize orchestrator with both stage services.

        Args:
            enable_cache: Enable result caching (default: True)
        """
        self.stage1 = GPT5Stage1Classifier()
        self.stage2 = GPT5Stage2Analyzer()
        self.cache = AnalysisCacheManager() if enable_cache else None

        # Metrics tracking
        self.total_documents = 0
        self.total_escalations = 0
        self.total_cost = 0.0
        self.cache_enabled = enable_cache

        logger.info(
            f"Initialized GPT5TwoStageOrchestrator (cache={'enabled' if enable_cache else 'disabled'})"
        )

    async def analyze_document(
        self,
        document_text: str,
        document_id: str,
        company_name: str = "Unknown",
        industry: str = "general",
    ) -> AnalysisResult:
        """
        Analyze a T&C document using two-stage cascade.

        Args:
            document_text: Full text of T&C document
            document_id: Unique document identifier
            company_name: Name of company
            industry: Industry category

        Returns:
            AnalysisResult with final classification and cost tracking

        Raises:
            ValueError: If document is invalid
        """
        start_time = time.time()
        escalated = False

        logger.info(f"Starting two-stage analysis for document {document_id}")

        # ===================================================================
        # CACHE CHECK: Return cached result if available
        # ===================================================================
        if self.cache:
            cached_result = await self.cache.get_cached_analysis(document_text)
            if cached_result:
                logger.info(f"[{document_id}] Returning cached result (cost: $0.00)")

                # Convert cached dict to AnalysisResult
                return AnalysisResult(
                    document_id=document_id,
                    overall_risk=cached_result["overall_risk"],
                    confidence=cached_result["confidence"],
                    stage=cached_result["stage"],
                    clauses=cached_result["clauses"],
                    summary=cached_result["summary"],
                    cost=0.0,  # Cache hit = $0 cost
                    processing_time=round(time.time() - start_time, 2),
                    stage1_result=cached_result.get("stage1_result"),
                    stage2_result=cached_result.get("stage2_result"),
                    escalated=cached_result.get("escalated", False),
                    timestamp=cached_result.get("timestamp"),
                )

        # ===================================================================
        # STAGE 1: Fast Classification
        # ===================================================================
        logger.info(f"[{document_id}] Running Stage 1 (GPT-5-Nano)...")

        try:
            stage1_result = await self.stage1.classify_document(
                document_text=document_text,
                document_id=document_id,
                company_name=company_name,
            )

            logger.info(
                f"[{document_id}] Stage 1 complete: "
                f"risk={stage1_result['overall_risk']}, "
                f"confidence={stage1_result['confidence']:.2f}, "
                f"cost=${stage1_result['cost']:.6f}"
            )

        except Exception as e:
            logger.error(f"[{document_id}] Stage 1 failed: {e}", exc_info=True)
            raise

        # ===================================================================
        # ROUTING DECISION: Should we escalate to Stage 2?
        # ===================================================================
        should_escalate = (
            stage1_result.get("confidence", 0.0) < self.ESCALATION_THRESHOLD
        )

        logger.info(
            f"[{document_id}] Routing decision: "
            f"confidence={stage1_result['confidence']:.2f}, "
            f"threshold={self.ESCALATION_THRESHOLD}, "
            f"escalate={should_escalate}"
        )

        stage2_result = None

        if should_escalate:
            # ===============================================================
            # STAGE 2: Deep Legal Analysis
            # ===============================================================
            logger.info(f"[{document_id}] Escalating to Stage 2 (GPT-5)...")
            escalated = True

            try:
                stage2_result = await self.stage2.deep_analyze(
                    document_text=document_text,
                    document_id=document_id,
                    stage1_result=stage1_result,
                    company_name=company_name,
                    industry=industry,
                )

                logger.info(
                    f"[{document_id}] Stage 2 complete: "
                    f"risk={stage2_result['overall_risk']}, "
                    f"confidence={stage2_result['confidence']:.2f}, "
                    f"cost=${stage2_result['cost']:.6f}"
                )

            except Exception as e:
                logger.error(f"[{document_id}] Stage 2 failed: {e}", exc_info=True)
                # If Stage 2 fails, fall back to Stage 1 result
                logger.warning(f"[{document_id}] Falling back to Stage 1 result")
                stage2_result = None

        # ===================================================================
        # BUILD FINAL RESULT
        # ===================================================================
        processing_time = time.time() - start_time

        # Use Stage 2 result if available, otherwise Stage 1
        final_result = stage2_result if stage2_result else stage1_result

        # Calculate total cost
        total_cost = stage1_result["cost"]
        if stage2_result:
            total_cost += stage2_result["cost"]

        # Build analysis result
        result = AnalysisResult(
            document_id=document_id,
            overall_risk=final_result["overall_risk"],
            confidence=final_result["confidence"],
            stage=2 if stage2_result else 1,
            clauses=final_result.get("clauses", []),
            summary=final_result.get("summary", ""),
            cost=total_cost,
            processing_time=round(processing_time, 2),
            stage1_result=stage1_result,
            stage2_result=stage2_result,
            escalated=escalated,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Update metrics
        self._update_metrics(total_cost, escalated)

        # Log final result
        logger.info(
            f"[{document_id}] Analysis complete: "
            f"final_stage={result.stage}, "
            f"risk={result.overall_risk}, "
            f"confidence={result.confidence:.2f}, "
            f"cost=${result.cost:.6f}, "
            f"time={result.processing_time:.2f}s"
        )

        # Log cost efficiency
        savings = self._calculate_savings(result.cost)
        logger.info(
            f"[{document_id}] Cost efficiency: "
            f"${result.cost:.6f} (vs ${0.015:.6f} single-stage = ${savings:.6f} saved)"
        )

        # ===================================================================
        # CACHE RESULT: Store for future use
        # ===================================================================
        if self.cache and SmartCacheStrategy.should_cache(
            document_text, result.to_dict()
        ):
            try:
                await self.cache.cache_analysis_result(document_text, result.to_dict())
                logger.info(f"[{document_id}] Result cached for future requests")
            except Exception as e:
                logger.warning(f"[{document_id}] Failed to cache result: {e}")

        return result

    async def analyze_batch(
        self, documents: List[Dict[str, str]], batch_id: str = None
    ) -> List[AnalysisResult]:
        """
        Analyze multiple documents in batch.

        Optimizes for throughput while tracking cost metrics.

        Args:
            documents: List of dicts with 'text', 'id', 'company', 'industry' keys
            batch_id: Optional batch identifier

        Returns:
            List of AnalysisResult objects
        """
        batch_id = batch_id or f"batch_{int(time.time())}"
        logger.info(f"Starting batch analysis: {batch_id} ({len(documents)} documents)")

        results = []
        batch_start_time = time.time()

        for idx, doc in enumerate(documents):
            try:
                result = await self.analyze_document(
                    document_text=doc["text"],
                    document_id=doc["id"],
                    company_name=doc.get("company", "Unknown"),
                    industry=doc.get("industry", "general"),
                )

                results.append(result)

                logger.info(
                    f"[{batch_id}] Progress: {idx + 1}/{len(documents)} "
                    f"(${result.cost:.6f}, stage {result.stage})"
                )

            except Exception as e:
                logger.error(
                    f"[{batch_id}] Failed to analyze document {doc['id']}: {e}"
                )
                # Continue with next document
                continue

        # Batch statistics
        batch_time = time.time() - batch_start_time
        total_cost = sum(r.cost for r in results)
        avg_cost = total_cost / len(results) if results else 0
        escalation_rate = (
            sum(1 for r in results if r.escalated) / len(results) if results else 0
        )

        logger.info(
            f"[{batch_id}] Batch complete: "
            f"{len(results)} documents, "
            f"${total_cost:.4f} total cost, "
            f"${avg_cost:.6f} avg/doc, "
            f"{escalation_rate*100:.1f}% escalation rate, "
            f"{batch_time:.2f}s total time"
        )

        # Compare to targets
        cost_vs_target = (
            (avg_cost - self.TARGET_BLENDED_COST) / self.TARGET_BLENDED_COST
        ) * 100
        escalation_vs_target = (
            (escalation_rate - self.TARGET_ESCALATION_RATE)
            / self.TARGET_ESCALATION_RATE
        ) * 100

        logger.info(
            f"[{batch_id}] Metrics vs targets: "
            f"cost {cost_vs_target:+.1f}% (target ${self.TARGET_BLENDED_COST:.6f}), "
            f"escalation {escalation_vs_target:+.1f}% (target {self.TARGET_ESCALATION_RATE*100:.1f}%)"
        )

        return results

    def _update_metrics(self, cost: float, escalated: bool):
        """Update running metrics."""
        self.total_documents += 1
        self.total_cost += cost
        if escalated:
            self.total_escalations += 1

    def _calculate_savings(self, actual_cost: float) -> float:
        """
        Calculate savings vs single-stage GPT-4.

        Single-stage GPT-4 cost: ~$0.015 per document
        """
        SINGLE_STAGE_COST = 0.015
        return SINGLE_STAGE_COST - actual_cost

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current orchestrator metrics.

        Returns:
            Dict with cost and escalation statistics
        """
        if self.total_documents == 0:
            return {
                "total_documents": 0,
                "total_cost": 0.0,
                "average_cost_per_document": 0.0,
                "escalation_rate": 0.0,
                "total_savings": 0.0,
            }

        avg_cost = self.total_cost / self.total_documents
        escalation_rate = self.total_escalations / self.total_documents
        total_savings = self._calculate_savings(avg_cost) * self.total_documents

        return {
            "total_documents": self.total_documents,
            "total_escalations": self.total_escalations,
            "escalation_rate": round(escalation_rate, 3),
            "total_cost": round(self.total_cost, 4),
            "average_cost_per_document": round(avg_cost, 6),
            "target_cost": self.TARGET_BLENDED_COST,
            "cost_vs_target": round(
                ((avg_cost - self.TARGET_BLENDED_COST) / self.TARGET_BLENDED_COST)
                * 100,
                1,
            ),
            "total_savings_vs_single_stage": round(total_savings, 4),
            "percent_savings": round((1 - (avg_cost / 0.015)) * 100, 1),
        }

    def reset_metrics(self):
        """Reset metrics tracking (useful for testing or periodic resets)."""
        self.total_documents = 0
        self.total_escalations = 0
        self.total_cost = 0.0
        logger.info("Metrics reset")
