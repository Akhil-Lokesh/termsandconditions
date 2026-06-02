"""OpenAI GPT-4o judge — the CROSS-FAMILY checker.

ARCHITECTURAL RULE — DO NOT VIOLATE
===================================
This module exists ONLY to provide a SECOND, INDEPENDENT vendor opinion in
the LLM-as-judge harness. The cross-family check loses ALL meaning if both
judges talk to the same vendor (Claude grading Claude is not an
independent audit, it's an echo chamber). For that reason:

  * This file imports the ``openai`` library.
  * This file MUST NEVER import anything from the production backend
    package — no detector wrappers, no shared retry helpers, no config
    objects. If you find yourself reaching for production code from this
    module, duplicate it locally instead.

There is a static CI check enforcing this rule (a literal grep against
this filename); please don't try to work around it.

The class signature MUST mirror ``ClaudeJudge`` so the orchestrator can
swap them. Reuse the exact same ``JUDGE_SYSTEM_PROMPT`` content as
``claude_judge.py``: cross-family means a different MODEL not a different
PROMPT.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# COPIED VERBATIM from claude_judge.JUDGE_SYSTEM_PROMPT — kept as a local
# string so this file does not import ``claude_judge`` (mirroring the
# constraint that production code must not import here either; we keep
# this module dependency-light by design).
#
# If you update the rubric, update BOTH files in lockstep. Equality is enforced
# by a unit test — evals/tests/test_judges.py::test_judge_prompts_in_lockstep —
# which asserts the two JUDGE_SYSTEM_PROMPT strings are byte-identical (there is
# no runtime check, since this module intentionally does not import claude_judge).
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


DEFAULT_JUDGE_MODEL = "gpt-4o"


def _truncate(s: Any, n: int = 2000) -> str:
    if s is None:
        return ""
    s = str(s)
    if len(s) <= n:
        return s
    return s[:n] + "... [truncated]"


def _parse_verdict_text(text: str) -> Dict[str, Any]:
    """Same shape parser as ``claude_judge._parse_verdict_text``.

    Intentionally duplicated rather than imported to keep this file
    decoupled — see module docstring.
    """
    if not text:
        return {
            "severity_verdict": "no",
            "category_verdict": "no",
            "rationale": "empty model response",
        }
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
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


class OpenAIJudge:
    """LLM-as-judge backed by OpenAI GPT-4o.

    Args:
        model: OpenAI chat model id. Defaults to ``"gpt-4o"``.
        api_key: OpenAI API key. Reads ``OPENAI_API_KEY`` from env when
            omitted. The constructor will RAISE if neither the
            environment variable nor an explicit api_key is supplied,
            because the cross-family check is the WHOLE POINT of this
            module — running it without an OpenAI key is almost always a
            bug. (Module-level imports do NOT raise — a missing openai
            library only surfaces at instantiation, by design.)
    """

    def __init__(
        self,
        model: str = DEFAULT_JUDGE_MODEL,
        api_key: Optional[str] = None,
    ) -> None:
        # Validate openai library is importable now, not at module load.
        try:
            from openai import AsyncOpenAI  # noqa: F401  (presence check)
        except ImportError as exc:
            raise RuntimeError(
                "openai library not installed. Add 'openai>=1.0.0' to "
                "requirements.txt and reinstall the venv to use OpenAIJudge."
            ) from exc

        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or None
        self._client = None  # lazy; lets tests monkeypatch without an env var

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover (covered above)
            raise RuntimeError(
                "openai library not installed — cannot construct OpenAIJudge"
            ) from exc
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set; OpenAIJudge cannot call the API. "
                "Pass api_key explicitly or set the environment variable."
            )
        self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def judge_clause(
        self,
        clause: Dict[str, Any],
        prediction: Dict[str, Any],
    ) -> Dict[str, Any]:
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
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=400,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            # OpenAI SDK shape: response.choices[0].message.content
            raw_text = ""
            choices = getattr(response, "choices", None) or []
            if choices:
                message = getattr(choices[0], "message", None)
                if message is not None:
                    raw_text = getattr(message, "content", "") or ""
            raw_text = (raw_text or "").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "OpenAIJudge.judge_clause failed for clause_id=%s: %s",
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
        return [r for r in results if r is not None]


__all__ = [
    "OpenAIJudge",
    "JUDGE_SYSTEM_PROMPT",
    "DEFAULT_JUDGE_MODEL",
]
