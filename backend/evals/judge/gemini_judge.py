"""Gemini Flash labeler — independent second-rater for inter-annotator agreement.

Unlike the existing per-prediction verdict judges (which validate a
prediction with yes/no verdicts), this module asks Gemini Flash to LABEL
clauses independently with severity + risk_category. The orchestrator
then computes Cohen's kappa between Claude's production labels and
Gemini's labels — a true inter-annotator agreement study.

Design choices (intentional):
- REST API via ``httpx`` (already a project dep). No ``google-generativeai``
  SDK dependency. Easier to verify "no search grounding" config and to
  reproduce in environments without the SDK.
- Hard cap: 5 clauses per request (Gemini Flash handles this well at
  temperature 0 without truncation).
- Temperature 0 + ``responseMimeType: application/json`` for stable parsing.
- No ``tools`` array in the request → search grounding cannot fire.
- Exponential backoff on 429 / 503, honoring ``Retry-After`` if present.
- Skip-safe: missing ``GEMINI_API_KEY`` raises ``GeminiNotConfigured``;
  callers should catch and exit 0.

Free-tier safety (Gemini 1.5/2.0 Flash):
- 15 requests / minute, 1,500 requests / day default.
- 30 clauses at batch=5 = 6 requests (well within both limits).
- The ``RPM_PACING_SECONDS`` constant throttles to one request every
  ~4.5s by default to stay under 15 RPM even with concurrent callers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

import httpx

logger = logging.getLogger(__name__)

# --- Public constants ------------------------------------------------------ #

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_BATCH_SIZE = 5
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_BACKOFF = 1.0  # seconds
DEFAULT_MAX_BACKOFF = 60.0
# 6.5s/request = ~9 RPM, safely under Gemini 2.5 Flash's 10 RPM free limit
# (also safe for 2.0 Flash's 15 RPM). RPD cap on 2.5 Flash is 250/day, so a
# 30-clause run at batch=5 (6 requests) consumes ~2.4% of daily budget.
RPM_PACING_SECONDS = 6.5
REQUEST_TIMEOUT_SECONDS = 60.0

# Severity vocabulary — must match LLMClauseDetector + EvalClause schema.
SEVERITIES = ("critical", "high", "medium", "low")
# Categories — must match the 11 values in evals/datasets/schema.py.
RISK_CATEGORIES = (
    "liability", "payment", "privacy", "arbitration", "modification",
    "termination", "content", "data", "rights", "surveillance", "other",
)

GEMINI_ENDPOINT_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


# --- System & user prompt builders ---------------------------------------- #

SYSTEM_PROMPT = """You are a legal-document risk analyst evaluating clauses from \
Terms of Service and Privacy Policy documents. For each clause you receive, \
assign one severity and one risk_category.

Severity rubric:
- critical: clear material harm to a typical consumer (forced arbitration \
combined with class-action waiver; broad liability cap of $0 or fees-paid; \
perpetual/irrevocable license to user content with sublicense rights; sale \
of personal data to unnamed third parties; unilateral termination with \
prepaid-credit forfeiture; jury-trial waiver with venue restriction).
- high: significant one-sided risk (one-sided indemnification; auto-renewal \
hard-to-cancel; broad data sharing with affiliates / advertisers; sole-\
discretion termination of accounts; sole-discretion content removal; broad \
license to user-generated content).
- medium: notable but standard industry practice (limitation of liability \
without extreme caps; unilateral terms-change via continued use; mandatory \
venue / forum selection; warranty disclaimers).
- low: boilerplate / routine (severability; notice provisions; headings; \
governing-law clauses with reasonable jurisdiction).

Categories (pick exactly one): liability, payment, privacy, arbitration, \
modification, termination, content, data, rights, surveillance, other.

Output requirements:
- Return ONLY a JSON array, one object per clause, in INPUT ORDER.
- Each object has exactly: clause_id (string), severity (one of \
critical/high/medium/low), risk_category (one of the 11 values above).
- No prose, no markdown fences, no chain-of-thought, no other keys.
"""


def build_user_prompt(clauses: Iterable[dict]) -> str:
    """Render a batch of clauses into the user-turn payload."""
    parts = ["Label each of the following clauses. Respond with a JSON array.\n"]
    for i, c in enumerate(clauses, 1):
        cid = str(c.get("clause_id", f"_unset_{i}"))
        section = str(c.get("section", "Unknown"))[:200]
        text = str(c.get("text", ""))[:2000]
        parts.append(f"--- clause {i} ---")
        parts.append(f"clause_id: {cid}")
        parts.append(f"section: {section}")
        parts.append(f"text: {text}")
        parts.append("")
    return "\n".join(parts)


# --- Exceptions ----------------------------------------------------------- #

class GeminiNotConfigured(RuntimeError):
    """Raised when ``GEMINI_API_KEY`` is missing. Callers should exit 0."""


class GeminiAPIError(RuntimeError):
    """Raised after retries are exhausted on a transient API error."""


# --- Result types --------------------------------------------------------- #

@dataclass
class GeminiLabel:
    """One labeled clause from Gemini."""
    clause_id: str
    severity: Optional[str]  # may be None if parsing failed
    risk_category: Optional[str]
    raw_response: str = ""

    def to_dict(self) -> dict:
        return {
            "clause_id": self.clause_id,
            "severity": self.severity,
            "risk_category": self.risk_category,
            "raw_response": self.raw_response,
        }


@dataclass
class GeminiBatchStats:
    """Per-run statistics — exposed for the runbook + free-tier safety logs."""
    requests_sent: int = 0
    requests_retried: int = 0
    rate_limit_hits: int = 0
    total_clauses_labeled: int = 0
    parse_failures: int = 0
    elapsed_seconds: float = 0.0


# --- Parser --------------------------------------------------------------- #

def _strip_fences(text: str) -> str:
    """Best-effort markdown fence removal."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


def parse_gemini_response(
    raw_text: str, expected_clause_ids: List[str]
) -> List[GeminiLabel]:
    """Parse a Gemini reply into ``GeminiLabel`` list aligned by clause_id.

    Tolerant of:
    - Markdown code fences around the JSON.
    - Trailing commentary after the array.
    - Extra/missing fields per object (defaults to None).
    - Out-of-order results (aligned by clause_id, not position).

    Returns one label per expected_clause_id. Missing IDs get severity=None
    and risk_category=None so downstream metrics handle them as misses.
    """
    cleaned = _strip_fences(raw_text or "")
    items: List[dict] = []
    if cleaned:
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                items = [x for x in parsed if isinstance(x, dict)]
            elif isinstance(parsed, dict):
                items = [parsed]
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, list):
                        items = [x for x in parsed if isinstance(x, dict)]
                except json.JSONDecodeError:
                    pass

    by_id: dict[str, dict] = {}
    for it in items:
        cid = str(it.get("clause_id", "")).strip()
        if cid:
            by_id[cid] = it

    out: List[GeminiLabel] = []
    for cid in expected_clause_ids:
        item = by_id.get(cid, {})
        sev = item.get("severity")
        cat = item.get("risk_category")
        if isinstance(sev, str):
            sev = sev.strip().lower()
            if sev not in SEVERITIES:
                sev = None
        else:
            sev = None
        if isinstance(cat, str):
            cat = cat.strip().lower()
            if cat not in RISK_CATEGORIES:
                cat = None
        else:
            cat = None
        out.append(GeminiLabel(
            clause_id=cid,
            severity=sev,
            risk_category=cat,
            raw_response=(raw_text or "")[:500],
        ))
    return out


# --- HTTP transport (overridable for tests) ------------------------------- #

class _HttpTransport:
    """Thin wrapper around httpx.AsyncClient.post — swap in tests."""

    def __init__(self, timeout: float = REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    async def post(self, url: str, params: dict, json_body: dict) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(url, params=params, json=json_body)


# --- Main judge class ----------------------------------------------------- #

class GeminiJudge:
    """Asynchronous Gemini Flash labeler with batching + retry/backoff.

    Usage:
        judge = GeminiJudge()  # reads GEMINI_API_KEY
        labels = await judge.label_batch(clauses)
        # labels: List[GeminiLabel], one per input clause, same order

    Cross-family rule:
    This module MUST NOT import from ``app/services/claude_service.py``,
    ``anthropic``, or any other rater's client SDK. The agreement study is
    only honest if the second rater has zero coupling to the first.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rpm_pacing_seconds: float = RPM_PACING_SECONDS,
        transport: Optional[_HttpTransport] = None,
    ) -> None:
        self.model = model
        self.batch_size = max(1, int(batch_size))
        self.max_retries = max(0, int(max_retries))
        self.rpm_pacing_seconds = max(0.0, float(rpm_pacing_seconds))
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self._transport = transport or _HttpTransport()
        # Lazy lock — Python 3.9 binds asyncio.Lock to an event loop at
        # construction time; deferring creation lets us instantiate the
        # judge outside a running loop (e.g. in synchronous test setup).
        self._pacing_lock: Optional[asyncio.Lock] = None
        self._last_request_at: float = 0.0
        self.stats = GeminiBatchStats()

    @property
    def name(self) -> str:
        return f"gemini:{self.model}"

    def _require_key(self) -> str:
        if not self._api_key:
            raise GeminiNotConfigured(
                "GEMINI_API_KEY not set; the Gemini agreement run is skipped."
            )
        return self._api_key

    async def _pace(self) -> None:
        """Enforce a global minimum interval between requests (per judge instance)."""
        if self.rpm_pacing_seconds <= 0:
            return
        if self._pacing_lock is None:
            self._pacing_lock = asyncio.Lock()
        async with self._pacing_lock:
            now = time.monotonic()
            wait = (self._last_request_at + self.rpm_pacing_seconds) - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    def _build_request_body(self, clauses: List[dict]) -> dict:
        """Construct the generateContent body — no tools, no grounding."""
        return {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": build_user_prompt(clauses)}],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "topP": 1,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json",
            },
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_NONE"}
                for c in (
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                )
            ],
            # NOTE: intentionally no "tools" key — disables grounding.
        }

    @staticmethod
    def _extract_text(response_json: dict) -> str:
        try:
            candidates = response_json.get("candidates") or []
            if not candidates:
                return ""
            parts = candidates[0].get("content", {}).get("parts", []) or []
            return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        except (AttributeError, IndexError, KeyError, TypeError):
            return ""

    async def _post_with_retry(self, body: dict) -> str:
        """POST to Gemini with exponential backoff. Returns response text."""
        api_key = self._require_key()
        url = GEMINI_ENDPOINT_TEMPLATE.format(model=self.model)
        params = {"key": api_key}

        attempt = 0
        while True:
            attempt += 1
            await self._pace()
            self.stats.requests_sent += 1
            try:
                resp = await self._transport.post(url, params=params, json_body=body)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                if attempt > self.max_retries:
                    raise GeminiAPIError(
                        f"network error after {attempt} attempts: {exc}"
                    ) from exc
                self.stats.requests_retried += 1
                await asyncio.sleep(self._backoff_seconds(attempt, retry_after=None))
                continue

            status = resp.status_code
            if status == 200:
                try:
                    return self._extract_text(resp.json())
                except (ValueError, json.JSONDecodeError) as exc:
                    raise GeminiAPIError(f"non-JSON response: {exc}") from exc

            if status in (429, 500, 502, 503, 504):
                if attempt > self.max_retries:
                    raise GeminiAPIError(
                        f"status {status} after {attempt} attempts: "
                        f"{(resp.text or '')[:300]}"
                    )
                if status == 429:
                    self.stats.rate_limit_hits += 1
                retry_after_header = resp.headers.get("Retry-After")
                ra: Optional[float] = None
                if retry_after_header:
                    try:
                        ra = float(retry_after_header)
                    except (TypeError, ValueError):
                        ra = None
                self.stats.requests_retried += 1
                await asyncio.sleep(self._backoff_seconds(attempt, retry_after=ra))
                continue

            # Non-retryable 4xx
            raise GeminiAPIError(
                f"unrecoverable status {status}: {(resp.text or '')[:300]}"
            )

    @staticmethod
    def _backoff_seconds(attempt: int, retry_after: Optional[float]) -> float:
        if retry_after is not None and retry_after > 0:
            return min(retry_after, DEFAULT_MAX_BACKOFF)
        base = DEFAULT_BASE_BACKOFF * (2 ** (attempt - 1))
        jitter = random.uniform(0, base * 0.25)
        return min(base + jitter, DEFAULT_MAX_BACKOFF)

    async def label_batch(self, clauses: List[dict]) -> List[GeminiLabel]:
        """Label a sequence of clauses, batching into the configured size.

        Returns one GeminiLabel per input clause, preserving input order.
        Parse failures yield a label with severity=None / risk_category=None
        but never raise — callers can compute coverage from stats.
        """
        start = time.monotonic()
        out: List[GeminiLabel] = []

        for batch_start in range(0, len(clauses), self.batch_size):
            batch = clauses[batch_start:batch_start + self.batch_size]
            expected_ids = [str(c.get("clause_id", f"_unset_{batch_start + i}"))
                             for i, c in enumerate(batch)]
            body = self._build_request_body(batch)
            try:
                raw_text = await self._post_with_retry(body)
            except GeminiAPIError:
                logger.exception("gemini batch failed after retries")
                # Emit empty labels for the batch so alignment stays sound.
                self.stats.parse_failures += len(batch)
                out.extend(
                    GeminiLabel(clause_id=cid, severity=None,
                                risk_category=None, raw_response="")
                    for cid in expected_ids
                )
                continue

            labels = parse_gemini_response(raw_text, expected_ids)
            for lbl in labels:
                if lbl.severity is None or lbl.risk_category is None:
                    self.stats.parse_failures += 1
            self.stats.total_clauses_labeled += len(labels)
            out.extend(labels)

        self.stats.elapsed_seconds = round(time.monotonic() - start, 2)
        return out

    async def label_clause(self, clause: dict) -> GeminiLabel:
        """Convenience single-clause wrapper."""
        labels = await self.label_batch([clause])
        return labels[0]
