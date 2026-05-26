"""Anthropic Claude judge for the LLM-as-judge harness.

This is the PRIMARY judge in the cross-family pair. It uses the Anthropic
``AsyncAnthropic`` client directly (no wrapping through
``app.services.claude_service``) so we keep the evaluation code path
independent of the production detector path — easier to audit, easier to
stub in tests.

Public surface:

    class ClaudeJudge:
        async judge_clause(clause: dict, prediction: dict) -> dict
        async judge_batch(clauses: list, predictions: list,
                          concurrency: int = 5) -> list[dict]

Each verdict returned has the shape::

    {
        "severity_verdict": "yes" | "partial" | "no",
        "category_verdict": "yes" | "no",
        "rationale": "...",
    }

The judge intentionally returns simple verdict labels rather than its own
severity prediction — its job is to AUDIT the predictor, not replace it.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Shared judge rubric. ClaudeJudge and OpenAIJudge MUST use the same prompt
# wording — "cross-family" means a different VENDOR, not a different
# rubric. If the prompts diverge, agreement metrics conflate prompt drift
# with model disagreement and the cross-check loses meaning.
JUDGE_SYSTEM_PROMPT = """You are a SENIOR LEGAL ANALYST auditing the output of an automated clause-risk classifier.

You will be shown:
  1. A clause from a Terms & Conditions or Privacy Policy document.
  2. The classifier's prediction: a severity (critical/high/medium/low) and a risk_category.
  3. (Optional) The dataset's expected severity and expected risk_category for reference.

YOUR JOB is to decide, strictly and consistently, whether the prediction is correct.

SEVERITY VERDICT — answer one of:
  "yes"     — the predicted severity is correct for this clause.
  "partial" — adjacent severity (e.g. predicted "high" when "critical" is justified, or vice-versa).
  "no"      — the predicted severity is wrong (e.g. flagged "critical" when the clause is industry-standard,
              or flagged "low" when the clause waives a fundamental right).

Be STRICT about over-calibration: if the clause describes a practice common in >50% of major
tech / social-media ToS (broad content license, warranty disclaimers, unilateral modification,
limitation of liability, indemnification, standard cookies, "legitimate interests" language),
flagging it "critical" is INCORRECT — verdict = "no". Reserve "critical" for clauses that waive
fundamental legal rights, contain potentially illegal provisions, or cause extreme harm with no
recourse.

CATEGORY VERDICT — answer one of:
  "yes" — risk_category matches what a careful reviewer would assign.
  "no"  — wrong category (e.g. predicted "privacy" but the clause is about arbitration).

Valid risk categories (T&C):
  liability, payment, privacy, arbitration, modification, termination,
  content, data, rights, surveillance, other

Valid risk categories (privacy policy):
  data_collection, data_sharing, data_retention, tracking, legal_basis,
  consent, data_rights, third_parties, international_transfers, children_data, other

RATIONALE — exactly one sentence explaining your verdict.

OUTPUT FORMAT — respond with ONLY valid JSON, no markdown fences, no prose outside the JSON:
{
  "severity_verdict": "yes" | "partial" | "no",
  "category_verdict": "yes" | "no",
  "rationale": "one sentence"
}"""


_JUDGE_USER_TEMPLATE = """CLAUSE:
\"\"\"
{clause_text}
\"\"\"

SECTION: {section}

DATASET EXPECTED (for reference, may be noisy):
  expected_severity: {expected_severity}
  expected_risk_category: {expected_risk_category}

CLASSIFIER PREDICTION:
  severity: {pred_severity}
  risk_category: {pred_risk_category}

Return the JSON verdict now."""


# Default judge model. The brief specifies "claude-opus-4-5" as the
# stable id; if "claude-opus-4-7" becomes available the caller can pass
# it explicitly via the constructor.
DEFAULT_JUDGE_MODEL = "claude-opus-4-5"


def _truncate(s: Any, n: int = 2000) -> str:
    """Defensive truncation so a long clause can't blow the prompt budget."""
    if s is None:
        return ""
    s = str(s)
    if len(s) <= n:
        return s
    return s[:n] + "... [truncated]"


def _parse_verdict_text(text: str) -> Dict[str, Any]:
    """Extract a verdict dict from the model's reply.

    The system prompt asks for raw JSON only, but be tolerant: also accept
    a JSON object embedded in surrounding prose / code-fences.
    """
    if not text:
        return {
            "severity_verdict": "no",
            "category_verdict": "no",
            "rationale": "empty model response",
        }

    # Strip fenced code blocks if present.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Drop opening fence (with optional language tag) and trailing fence.
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    # Try the whole thing first.
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back: grab the first {...} block.
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return {
                "severity_verdict": "no",
                "category_verdict": "no",
                "rationale": f"unparseable response: {text[:160]!r}",
            }
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            return {
                "severity_verdict": "no",
                "category_verdict": "no",
                "rationale": f"json decode failed: {exc}",
            }

    sev = str(parsed.get("severity_verdict", "no")).lower().strip()
    if sev not in {"yes", "partial", "no"}:
        sev = "no"
    cat = str(parsed.get("category_verdict", "no")).lower().strip()
    if cat not in {"yes", "no"}:
        cat = "no"
    rationale = str(parsed.get("rationale", ""))[:500]

    return {
        "severity_verdict": sev,
        "category_verdict": cat,
        "rationale": rationale,
    }


class ClaudeJudge:
    """LLM-as-judge backed by Anthropic Claude.

    Args:
        model: Claude model id. Defaults to ``"claude-opus-4-5"`` — one
            tier above the production detector (Sonnet). If a newer Opus
            tier (e.g. 4-7) becomes available the caller can pass it
            explicitly; we don't auto-discover.
        api_key: Anthropic API key. Reads ``ANTHROPIC_API_KEY`` from env
            when omitted. The judge can be instantiated without a key for
            testing (the client is created lazily); calls will fail at
            request time with a clear error.
    """

    def __init__(
        self,
        model: str = DEFAULT_JUDGE_MODEL,
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or None
        self._client = None  # lazy

    @property
    def name(self) -> str:
        return f"claude:{self.model}"

    def _get_client(self):
        """Lazily construct the AsyncAnthropic client.

        Imported inside the method so test code can monkeypatch
        ``ClaudeJudge._client`` without ever importing ``anthropic``.
        """
        if self._client is not None:
            return self._client
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "anthropic library not installed — cannot construct ClaudeJudge"
            ) from exc
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set; ClaudeJudge cannot call the API. "
                "Pass api_key explicitly or set the environment variable."
            )
        self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def judge_clause(
        self,
        clause: Dict[str, Any],
        prediction: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Audit one (clause, prediction) pair.

        Args:
            clause: Dict with at least ``text``. Optional keys recognised:
                ``section``, ``expected_severity``, ``expected_risk_category``.
            prediction: Dict with at least ``severity`` and
                ``risk_category``.

        Returns:
            Verdict dict: ``{severity_verdict, category_verdict, rationale}``.
            Never raises for an upstream API error — converts to a
            "no" verdict with the error message in rationale so the
            orchestrator can still aggregate.
        """
        user_prompt = _JUDGE_USER_TEMPLATE.format(
            clause_text=_truncate(clause.get("text", ""), 2000),
            section=_truncate(clause.get("section", "Unknown"), 200),
            expected_severity=clause.get("expected_severity", "n/a"),
            expected_risk_category=clause.get("expected_risk_category", "n/a"),
            pred_severity=prediction.get("severity", "n/a"),
            pred_risk_category=prediction.get("risk_category", "n/a"),
        )

        try:
            client = self._get_client()
            response = await client.messages.create(
                model=self.model,
                max_tokens=400,
                temperature=0.0,
                system=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            # The Anthropic SDK returns content as a list of blocks.
            text_blocks: List[str] = []
            for block in getattr(response, "content", []) or []:
                # Either a TextBlock SDK object or a plain dict.
                if hasattr(block, "text"):
                    text_blocks.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    text_blocks.append(block["text"])
            raw_text = "\n".join(text_blocks).strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ClaudeJudge.judge_clause failed for clause_id=%s: %s",
                clause.get("clause_id"),
                exc,
            )
            return {
                "severity_verdict": "no",
                "category_verdict": "no",
                "rationale": f"judge error: {type(exc).__name__}: {exc}",
            }

        verdict = _parse_verdict_text(raw_text)
        verdict["_raw"] = raw_text[:500]
        verdict["_judge"] = self.name
        return verdict

    async def judge_batch(
        self,
        clauses: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """Concurrent batch judging with a fixed-size semaphore.

        Args:
            clauses: aligned with ``predictions`` by index.
            predictions: same length as ``clauses``.
            concurrency: max simultaneous in-flight requests.

        Returns:
            List of verdicts in the same order as the inputs.
        """
        if len(clauses) != len(predictions):
            raise ValueError(
                f"clauses ({len(clauses)}) and predictions "
                f"({len(predictions)}) must be aligned and equal length"
            )
        if not clauses:
            return []

        sem = asyncio.Semaphore(max(1, concurrency))

        async def _run(idx: int, c: Dict[str, Any], p: Dict[str, Any]):
            async with sem:
                v = await self.judge_clause(c, p)
                return idx, v

        tasks = [
            asyncio.create_task(_run(i, c, p))
            for i, (c, p) in enumerate(zip(clauses, predictions))
        ]
        results: List[Optional[Dict[str, Any]]] = [None] * len(clauses)
        for fut in asyncio.as_completed(tasks):
            idx, verdict = await fut
            results[idx] = verdict
        # mypy: by construction every slot is filled.
        return [r for r in results if r is not None]


__all__ = [
    "ClaudeJudge",
    "JUDGE_SYSTEM_PROMPT",
    "DEFAULT_JUDGE_MODEL",
]
