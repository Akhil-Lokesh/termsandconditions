"""Anomaly detector — thin orchestrator over the LLM checklist pipeline.

Simple-engineering refactor (2026-05-27): retired the 6-stage pipeline after
the user's before/after dashboard showed Stages 2-5 were subtractive on top
of the new checklist detector. Final flow:

  1. ``LLMClauseDetector.detect_risky_clauses`` runs the production checklist
     prompt against the document. Optionally a second LLM pass runs
     ``detect_missing_protections`` to flag absent consumer protections.
  2. ``AlertRanker`` buckets the merged findings into high / medium / low
     and enforces the per-document alert budget.
  3. The orchestrator assembles the report dict the upload pipeline expects.

Public surface preserved for callers in ``app/api/v1/``:
- ``AnomalyDetector(embedding_service, pinecone_service, db, claude_service)``
- ``async detect_anomalies(document_id, sections, company_name, service_type, document_context)``
- ``calculate_document_risk_score(...)`` (deprecated but kept for one external script)
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.alert_ranker import AlertRanker
from app.core.llm_clause_detector import LLMClauseDetector
from app.services.claude_service import ClaudeService
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


# Severity-tier weights used by the risk-score calculator. Tuned so a single
# critical or a couple of highs land a document around 7/10 ("High Risk").
_SEVERITY_WEIGHTS = {"critical": 4.0, "high": 2.0, "medium": 0.7, "low": 0.2}
_RISK_SCORE_CAP = 30.0

# Ordinal ranking for keeping the most severe instance when collapsing duplicates.
_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


class AnomalyDetector:
    """Detects anomalies and risky clauses in T&C / privacy documents."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        pinecone_service: Optional[PineconeService] = None,
        db: Optional[Session] = None,
        claude_service: Optional[ClaudeService] = None,
    ) -> None:
        # The embedding + pinecone services are kept on the instance only so
        # external callers (debug endpoints, scripts) can grab them via the
        # detector without re-wiring DI. The detection flow itself does not
        # depend on them anymore — Stage 1 is pure LLM.
        self.embedding = embedding_service or EmbeddingService()
        self.claude = claude_service or ClaudeService()
        self.pinecone = pinecone_service or PineconeService()
        self.db = db

        self.llm_detector = LLMClauseDetector(self.claude)
        self.alert_ranker = AlertRanker()

    # ---- Main entrypoint -------------------------------------------------- #

    async def detect_anomalies(
        self,
        document_id: str,
        sections: List[Dict[str, Any]],
        company_name: str = "Unknown",
        service_type: str = "general",
        document_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the checklist detector + optional missing-protections pass.

        Returns a report dict matching the schema the upload pipeline
        consumes (high/medium/low severity alerts + overall risk score).
        """
        pipeline_start = time.time()
        document_context = document_context or {}
        document_type = document_context.get("document_type", "terms_of_service")

        logger.info(
            f"[anomaly_detector] document={document_id} company={company_name!r} "
            f"type={document_type} sections={len(sections)}"
        )

        # Flatten sections into a deterministic clause list for the LLM.
        clauses = _flatten_sections(sections)
        if not clauses:
            logger.warning(f"document {document_id}: no clauses extracted; returning empty report")
            return _empty_report(document_id, company_name, pipeline_start)

        # ---- Pass 1: risky-clause detection ------------------------------ #
        findings = await self.llm_detector.detect_risky_clauses(
            clauses,
            company_name=company_name,
            service_type=service_type,
            document_type=document_type,
        )
        logger.info(f"[detect] checklist pass returned {len(findings)} findings")

        # ---- Pass 2: missing protections (feature-flagged) --------------- #
        if os.getenv("MISSING_PROTECTIONS_CHECK", "true").lower() == "true":
            try:
                full_text = "\n\n".join(c["text"] for c in clauses if c.get("text"))
                if len(full_text.strip()) >= 200:
                    missing = await self.llm_detector.detect_missing_protections(
                        document_text=full_text,
                        company_name=company_name,
                    )
                    if missing:
                        logger.info(f"[detect] missing-protections pass added {len(missing)}")
                        findings = findings + missing
            except Exception as exc:
                logger.warning(f"[detect] missing-protections check failed (non-fatal): {exc}")

        # ---- Collapse duplicate findings --------------------------------- #
        # The LLM emits one finding per clause, so a risk that appears in several
        # clauses (e.g. "termination on suspicion" in 4 sections) surfaces as N
        # near-identical alerts. Collapse by risk title so each distinct risk is
        # one finding — matching how a human reviewer / benchmark counts them.
        pre_dedup = len(findings)
        findings = _dedupe_findings(findings)
        if len(findings) != pre_dedup:
            logger.info(f"[detect] dedup collapsed {pre_dedup} -> {len(findings)} findings")

        # ---- Rank + bucket ------------------------------------------------ #
        ranked = self.alert_ranker.rank_and_filter(
            calibrated_anomalies=findings,
            document_context=document_context,
        )
        high = ranked.get("high_severity", [])
        medium = ranked.get("medium_severity", [])
        low = ranked.get("low_severity", [])
        suppressed = ranked.get("suppressed", [])

        overall_risk_score = _calculate_risk_score(high, medium, low)
        duration_ms = round((time.time() - pipeline_start) * 1000, 2)

        logger.info(
            f"[anomaly_detector] complete document={document_id} "
            f"H={len(high)} M={len(medium)} L={len(low)} "
            f"risk={overall_risk_score:.1f}/10 elapsed={duration_ms}ms"
        )

        return {
            "document_id": document_id,
            "company_name": company_name,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "overall_risk_score": round(overall_risk_score, 1),
            "high_severity_alerts": high,
            "medium_severity_alerts": medium,
            "low_severity_alerts": low,
            "suppressed_alerts_count": len(suppressed),
            "total_anomalies_detected": ranked.get("total_detected", len(findings)),
            "total_alerts_shown": ranked.get("total_shown", len(high) + len(medium) + len(low)),
            "ranking_metadata": ranked.get("ranking_metadata", {}),
            "pipeline_performance": {
                "checklist_findings": len(findings),
                "ranked_high": len(high),
                "ranked_medium": len(medium),
                "ranked_low": len(low),
                "total_processing_time_ms": duration_ms,
            },
        }

    # ---- Legacy compat helpers (kept for external callers) --------------- #

    @staticmethod
    def calculate_document_risk_score(
        high_severity: List[Dict[str, Any]],
        medium_severity: List[Dict[str, Any]],
        low_severity: List[Dict[str, Any]],
    ) -> float:
        """Compute the same risk score the orchestrator uses, as a static helper."""
        return _calculate_risk_score(high_severity, medium_severity, low_severity)


# ---- Module-level helpers ------------------------------------------------- #


def _flatten_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sections → flat clause list with sequential clause_numbers."""
    clauses: List[Dict[str, Any]] = []
    seq = 0
    for section in sections or []:
        section_name = section.get("title") or section.get("section_name") or "Unknown"
        for c in (section.get("clauses", []) if isinstance(section, dict) else []):
            text = (c.get("text") or "").strip()
            if not text or len(text) < 20:
                continue
            seq += 1
            clauses.append({
                "text": text,
                "section": section_name[:200],
                "clause_number": str(seq),
            })
    return clauses


def _dedupe_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse findings that represent the SAME risk into one.

    Two passes, each keeping the highest-severity instance and preserving order:

    1. **Same risk identity.** A pattern matched in several clauses produces
       near-identical findings. Catalog findings are keyed by pattern_id (stable
       even when the LLM rephrases the title); "novel"/off-catalog findings by a
       normalised title (so distinct novel risks are preserved).

    2. **Same clause location.** Several DISTINCT catalog patterns can match the
       same clause (e.g. on the Apple ToS, ``termination_with_prepaid_forfeit``
       and ``sole_discretion_account_termination`` both fire on the one
       termination clause; ``perpetual_content_license`` and
       ``sole_discretion_content_removal`` both fire on the submissions clause).
       The benchmark counts one risk per clause, so these surface as duplicate
       alerts ("M x3", "M+L") that pass 1 cannot catch (different pattern_ids).
       Collapse findings sharing a real clause_number to the strongest one.
       Findings with no clause_number (e.g. missing-protection findings) are
       NEVER merged here — they are not tied to a document location.
    """

    def _stronger(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """True if `a` should replace `b` (higher severity)."""
        return _SEVERITY_RANK.get(a.get("severity", "low"), 0) > _SEVERITY_RANK.get(
            b.get("severity", "low"), 0
        )

    # ---- Pass 1: collapse identical risks (pattern_id / title / explanation) --
    best: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for f in findings:
        pid = (f.get("pattern_id") or "").strip().lower()
        # Normalise title: lowercase, drop punctuation, collapse whitespace.
        title = re.sub(r"[^a-z0-9 ]", "", (f.get("risk_title") or "").lower())
        title = re.sub(r"\s+", " ", title).strip()
        if pid and pid not in ("novel", "none"):
            key = "pattern:" + pid
        elif title:
            key = "title:" + title
        else:
            key = "expl:" + (f.get("explanation") or "").strip().lower()[:80]

        cur = best.get(key)
        if cur is None:
            best[key] = f
            order.append(key)
        elif _stronger(f, cur):
            best[key] = f
    collapsed = [best[k] for k in order]

    # ---- Pass 2: collapse multiple patterns hitting the SAME clause location --
    by_clause: Dict[str, Dict[str, Any]] = {}
    clause_order: List[str] = []
    result: List[Dict[str, Any]] = []
    for f in collapsed:
        clause = str(f.get("clause_number") or "").strip()
        if not clause:
            # No document location (e.g. missing-protection finding) — keep as-is.
            result.append(f)
            continue
        cur = by_clause.get(clause)
        if cur is None:
            by_clause[clause] = f
            clause_order.append(clause)
            result.append(f)
        elif _stronger(f, cur):
            # Replace the weaker finding already emitted for this clause.
            result[result.index(cur)] = f
            by_clause[clause] = f
    return result


def _calculate_risk_score(
    high: List[Dict[str, Any]],
    medium: List[Dict[str, Any]],
    low: List[Dict[str, Any]],
) -> float:
    """Weighted severity score capped at 30, then scaled to /10."""
    crit_count = sum(1 for a in high if a.get("severity") == "critical")
    high_count = sum(1 for a in high if a.get("severity") == "high")
    weighted = (
        crit_count * _SEVERITY_WEIGHTS["critical"]
        + high_count * _SEVERITY_WEIGHTS["high"]
        + len(medium) * _SEVERITY_WEIGHTS["medium"]
        + len(low) * _SEVERITY_WEIGHTS["low"]
    )
    weighted = min(weighted, _RISK_SCORE_CAP)
    return (weighted / _RISK_SCORE_CAP) * 10.0


def _empty_report(document_id: str, company_name: str, pipeline_start: float) -> Dict[str, Any]:
    return {
        "document_id": document_id,
        "company_name": company_name,
        "analysis_date": datetime.now(timezone.utc).isoformat(),
        "overall_risk_score": 0.0,
        "high_severity_alerts": [],
        "medium_severity_alerts": [],
        "low_severity_alerts": [],
        "suppressed_alerts_count": 0,
        "total_anomalies_detected": 0,
        "total_alerts_shown": 0,
        "ranking_metadata": {},
        "pipeline_performance": {
            "checklist_findings": 0,
            "ranked_high": 0,
            "ranked_medium": 0,
            "ranked_low": 0,
            "total_processing_time_ms": round((time.time() - pipeline_start) * 1000, 2),
        },
    }
