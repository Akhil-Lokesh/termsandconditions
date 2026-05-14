"""Orchestrator for the LLM-as-judge harness.

Wraps the primary and (optional) cross-family judges with:

  * A SQLite verdict cache so re-runs on the same (clause, prediction)
    pair are free. The cache key includes the judge model id so swapping
    judges does not blindly reuse stale verdicts.
  * Stratified random sampling of the cross-family checker (default 15%
    of pairs, deterministic via Random(seed=42)).
  * A disagreement log (JSONL) written for every primary-vs-cross
    mismatch — the most important artifact for debugging calibration drift.
  * A graceful "skipped — no API key" exit path so CI can call this
    unconditionally.

CLI:

    python -m evals.judge.runner --dataset seed --sample 50
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Make `backend/` importable when invoked as `python -m evals.judge.runner`.
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


DEFAULT_CACHE_PATH = _THIS_DIR / "cache.db"
DEFAULT_DISAGREEMENT_LOG = _THIS_DIR / "judge_disagreements.jsonl"


# --------------------------------------------------------------------------- #
# SQLite cache                                                                #
# --------------------------------------------------------------------------- #


class VerdictCache:
    """Tiny synchronous SQLite cache for judge verdicts.

    Schema::

        CREATE TABLE verdicts (
            cache_key   TEXT PRIMARY KEY,
            judge_model TEXT NOT NULL,
            verdict_json TEXT NOT NULL,
            created_at  TIMESTAMP NOT NULL
        )

    The cache_key is sha256(clause_id || prediction_json || judge_model).
    Synchronous inside an async runner is fine — these writes are
    microseconds and the alternative (aiosqlite) is a heavier dep.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verdicts (
                cache_key TEXT PRIMARY KEY,
                judge_model TEXT NOT NULL,
                verdict_json TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """
        )
        self._conn.commit()

    @staticmethod
    def make_key(
        clause_id: str, prediction: Dict[str, Any], judge_model: str
    ) -> str:
        # sort_keys=True so identical predictions hash identically across runs.
        payload = json.dumps(prediction, sort_keys=True, default=str)
        digest = hashlib.sha256(
            f"{clause_id}|{payload}|{judge_model}".encode("utf-8")
        ).hexdigest()
        return digest

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT verdict_json FROM verdicts WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return None

    def put(
        self, cache_key: str, judge_model: str, verdict: Dict[str, Any]
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO verdicts
            (cache_key, judge_model, verdict_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                cache_key,
                judge_model,
                json.dumps(verdict, default=str),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# Sampling                                                                    #
# --------------------------------------------------------------------------- #


def _stratified_sample_indices(
    clauses: List[Dict[str, Any]],
    fraction: float,
    seed: int = 42,
) -> List[int]:
    """Pick a stratified random sample of indices, grouped by expected_severity.

    The cross-family check uses this to make sure every severity stratum
    is represented in the cross-checked sample (uniform random sampling
    would leave "critical" — the rarest class — under-represented).
    """
    fraction = max(0.0, min(1.0, fraction))
    if fraction == 0.0 or not clauses:
        return []

    buckets: Dict[str, List[int]] = {}
    for i, c in enumerate(clauses):
        sev = str(c.get("expected_severity", "unlabeled")).lower()
        buckets.setdefault(sev, []).append(i)

    rng = random.Random(seed)
    chosen: List[int] = []
    for sev, idxs in buckets.items():
        rng.shuffle(idxs)
        k = max(1, int(round(len(idxs) * fraction))) if idxs else 0
        chosen.extend(idxs[:k])
    chosen.sort()
    return chosen


# --------------------------------------------------------------------------- #
# Orchestrator                                                                #
# --------------------------------------------------------------------------- #


class JudgeRunner:
    """Run primary + (optional) cross-family judges with caching.

    Args:
        primary_judge: object with ``judge_batch(clauses, predictions, concurrency)``.
            Typically a ``ClaudeJudge`` instance.
        cross_judge: optional cross-family judge (typically ``OpenAIJudge``).
        cache_path: path to the SQLite verdict cache. Defaults to
            ``backend/evals/judge/cache.db``.
        disagreement_log: JSONL path where primary-vs-cross disagreements
            are appended.
    """

    def __init__(
        self,
        primary_judge: Any,
        cross_judge: Optional[Any] = None,
        cache_path: Path = DEFAULT_CACHE_PATH,
        disagreement_log: Path = DEFAULT_DISAGREEMENT_LOG,
    ) -> None:
        self.primary = primary_judge
        self.cross = cross_judge
        self.cache = VerdictCache(cache_path)
        self.disagreement_log = Path(disagreement_log)
        self.disagreement_log.parent.mkdir(parents=True, exist_ok=True)

    async def _judge_with_cache(
        self,
        judge: Any,
        clauses: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        concurrency: int = 5,
    ) -> List[Dict[str, Any]]:
        """Call ``judge.judge_batch`` but return cached verdicts when possible."""
        model_name = getattr(judge, "name", None) or getattr(judge, "model", "judge")

        # Resolve every pair against the cache.
        verdicts: List[Optional[Dict[str, Any]]] = [None] * len(clauses)
        miss_indices: List[int] = []
        keys: List[str] = []
        for i, (c, p) in enumerate(zip(clauses, predictions)):
            key = self.cache.make_key(
                str(c.get("clause_id", f"idx{i}")),
                p,
                model_name,
            )
            keys.append(key)
            hit = self.cache.get(key)
            if hit is not None:
                verdicts[i] = hit
            else:
                miss_indices.append(i)

        if miss_indices:
            miss_clauses = [clauses[i] for i in miss_indices]
            miss_preds = [predictions[i] for i in miss_indices]
            fresh = await judge.judge_batch(
                miss_clauses, miss_preds, concurrency=concurrency
            )
            for slot, v in zip(miss_indices, fresh):
                verdicts[slot] = v
                self.cache.put(keys[slot], model_name, v)

        return [v if v is not None else {
            "severity_verdict": "no",
            "category_verdict": "no",
            "rationale": "missing verdict",
        } for v in verdicts]

    def _record_disagreements(
        self,
        clauses: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        primary_verdicts: List[Dict[str, Any]],
        cross_verdicts: List[Dict[str, Any]],
        sample_indices: List[int],
    ) -> int:
        """Append a JSONL line per disagreement; return count."""
        disagreements = 0
        with self.disagreement_log.open("a", encoding="utf-8") as fh:
            for j, orig_idx in enumerate(sample_indices):
                p = primary_verdicts[orig_idx]
                x = cross_verdicts[j]
                sev_match = p["severity_verdict"] == x["severity_verdict"]
                cat_match = p["category_verdict"] == x["category_verdict"]
                if sev_match and cat_match:
                    continue
                disagreements += 1
                fh.write(
                    json.dumps(
                        {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "clause_id": clauses[orig_idx].get("clause_id"),
                            "clause_text": str(
                                clauses[orig_idx].get("text", "")
                            )[:400],
                            "prediction": predictions[orig_idx],
                            "primary": {
                                "judge": p.get("_judge"),
                                "severity_verdict": p["severity_verdict"],
                                "category_verdict": p["category_verdict"],
                                "rationale": p.get("rationale", ""),
                            },
                            "cross": {
                                "judge": x.get("_judge"),
                                "severity_verdict": x["severity_verdict"],
                                "category_verdict": x["category_verdict"],
                                "rationale": x.get("rationale", ""),
                            },
                            "severity_match": sev_match,
                            "category_match": cat_match,
                        },
                        default=str,
                    )
                    + "\n"
                )
        return disagreements

    @staticmethod
    def _aggregate(
        verdicts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute the simple "yes" rate per axis."""
        if not verdicts:
            return {
                "severity_yes_rate": 0.0,
                "severity_partial_rate": 0.0,
                "severity_no_rate": 0.0,
                "category_yes_rate": 0.0,
                "n": 0,
            }
        n = len(verdicts)
        sev_yes = sum(1 for v in verdicts if v["severity_verdict"] == "yes")
        sev_partial = sum(
            1 for v in verdicts if v["severity_verdict"] == "partial"
        )
        sev_no = sum(1 for v in verdicts if v["severity_verdict"] == "no")
        cat_yes = sum(1 for v in verdicts if v["category_verdict"] == "yes")
        return {
            "severity_yes_rate": sev_yes / n,
            "severity_partial_rate": sev_partial / n,
            "severity_no_rate": sev_no / n,
            "category_yes_rate": cat_yes / n,
            "n": n,
        }

    @staticmethod
    def _agreement(
        primary: List[Dict[str, Any]],
        cross: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Per-axis exact-match agreement between primary and cross."""
        if not primary or not cross or len(primary) != len(cross):
            return {
                "severity_agreement_rate": 0.0,
                "category_agreement_rate": 0.0,
                "overall_agreement_rate": 0.0,
            }
        n = len(primary)
        sev = sum(
            1
            for p, x in zip(primary, cross)
            if p["severity_verdict"] == x["severity_verdict"]
        )
        cat = sum(
            1
            for p, x in zip(primary, cross)
            if p["category_verdict"] == x["category_verdict"]
        )
        both = sum(
            1
            for p, x in zip(primary, cross)
            if p["severity_verdict"] == x["severity_verdict"]
            and p["category_verdict"] == x["category_verdict"]
        )
        return {
            "severity_agreement_rate": sev / n,
            "category_agreement_rate": cat / n,
            "overall_agreement_rate": both / n,
        }

    async def run(
        self,
        clauses: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
        cross_check_sample: float = 0.15,
        concurrency: int = 5,
    ) -> Dict[str, Any]:
        """Run primary judge on all pairs, cross judge on a sample.

        Args:
            clauses: list of clause dicts (must include ``clause_id`` &
                ``text``).
            predictions: aligned 1:1 with clauses.
            cross_check_sample: 0.0–1.0 fraction of pairs to also send to
                ``self.cross``. Zero (or no cross judge) skips the cross
                step. Stratified by ``expected_severity`` for a fair mix.
            concurrency: max in-flight requests per judge.

        Returns:
            Aggregate stats dict — see docstring at module top.
        """
        if len(clauses) != len(predictions):
            raise ValueError(
                f"clauses ({len(clauses)}) and predictions "
                f"({len(predictions)}) must be aligned and equal length"
            )

        # --- Primary judge over the whole input -------------------------- #
        primary_verdicts = await self._judge_with_cache(
            self.primary, clauses, predictions, concurrency=concurrency
        )

        # --- Cross-family checker on a stratified sample ----------------- #
        cross_verdicts: List[Dict[str, Any]] = []
        sample_indices: List[int] = []
        agreement = {
            "severity_agreement_rate": 0.0,
            "category_agreement_rate": 0.0,
            "overall_agreement_rate": 0.0,
        }
        n_disagree = 0
        if self.cross is not None and cross_check_sample > 0.0:
            sample_indices = _stratified_sample_indices(
                clauses, cross_check_sample, seed=42
            )
            if sample_indices:
                sample_clauses = [clauses[i] for i in sample_indices]
                sample_preds = [predictions[i] for i in sample_indices]
                cross_verdicts = await self._judge_with_cache(
                    self.cross,
                    sample_clauses,
                    sample_preds,
                    concurrency=concurrency,
                )
                # Build aligned primary slice for fair agreement calc.
                primary_slice = [primary_verdicts[i] for i in sample_indices]
                agreement = self._agreement(primary_slice, cross_verdicts)
                n_disagree = self._record_disagreements(
                    clauses,
                    predictions,
                    primary_verdicts,
                    cross_verdicts,
                    sample_indices,
                )

        primary_agg = self._aggregate(primary_verdicts)
        cross_agg = self._aggregate(cross_verdicts)

        return {
            "primary_judge": getattr(self.primary, "name", "primary"),
            "cross_judge": (
                getattr(self.cross, "name", None) if self.cross else None
            ),
            "n_judged": len(clauses),
            "n_cross_checked": len(cross_verdicts),
            "cross_check_sample_fraction": cross_check_sample,
            "primary_aggregate": primary_agg,
            "cross_aggregate": cross_agg,
            "agreement_rate": agreement["overall_agreement_rate"],
            "severity_agreement_rate": agreement["severity_agreement_rate"],
            "category_agreement_rate": agreement["category_agreement_rate"],
            "n_disagreements": n_disagree,
            "disagreement_log": str(self.disagreement_log),
            "severity_yes_rate": primary_agg["severity_yes_rate"],
            "category_yes_rate": primary_agg["category_yes_rate"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def close(self) -> None:
        self.cache.close()


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def _missing_api_key_skip(reason: str) -> int:
    print(f"judge runner skipped — {reason}")
    return 0


async def _cli_main(args: argparse.Namespace) -> int:
    # Lazy imports so a missing optional library doesn't break --help.
    from evals.datasets.loader import load_dataset

    eval_clauses = load_dataset(args.dataset, max_rows=args.sample)
    if not eval_clauses:
        print(f"No clauses loaded for dataset={args.dataset!r}; nothing to do.")
        return 0

    # Build (clauses, predictions). For an unconditional CLI run we need a
    # detector pass; reuse the project detector if Anthropic key is set,
    # otherwise create stub predictions equal to expected labels so the
    # judge call shape still exercises end-to-end.
    clause_dicts = [
        {
            "clause_id": c.clause_id,
            "section": c.section,
            "text": c.text,
            "expected_severity": c.expected_severity,
            "expected_risk_category": c.expected_risk_category,
        }
        for c in eval_clauses
    ]

    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not has_anthropic:
        return _missing_api_key_skip(
            "ANTHROPIC_API_KEY not set (judge requires Claude key)."
        )

    if args.use_stub_predictions:
        predictions = [
            {
                "severity": c.expected_severity,
                "risk_category": c.expected_risk_category,
            }
            for c in eval_clauses
        ]
    else:
        # Use the production detector to generate predictions for judging.
        from app.core.llm_clause_detector import LLMClauseDetector
        from app.services.claude_service import ClaudeService

        detector = LLMClauseDetector(ClaudeService())
        detector_input = [
            {
                "clause_number": c.clause_id,
                "section": c.section,
                "text": c.text,
            }
            for c in eval_clauses
        ]
        findings = await detector.detect_risky_clauses(
            detector_input, company_name="EvalHarness", service_type="general"
        )
        by_id = {str(f["clause_number"]): f for f in findings}
        predictions = []
        for c in eval_clauses:
            f = by_id.get(str(c.clause_id), {})
            predictions.append(
                {
                    "severity": f.get("severity"),
                    "risk_category": f.get("risk_category"),
                }
            )

    from evals.judge.claude_judge import ClaudeJudge

    primary = ClaudeJudge(model=args.judge_model)
    cross = None
    if os.environ.get("OPENAI_API_KEY") and not args.no_cross:
        try:
            from evals.judge.openai_judge import OpenAIJudge

            cross = OpenAIJudge(model=args.cross_model)
        except Exception as exc:  # noqa: BLE001
            print(f"cross judge disabled: {exc}")

    runner = JudgeRunner(
        primary_judge=primary,
        cross_judge=cross,
        cache_path=Path(args.cache),
        disagreement_log=Path(args.disagreements),
    )
    try:
        report = await runner.run(
            clause_dicts,
            predictions,
            cross_check_sample=args.cross_sample,
            concurrency=args.concurrency,
        )
    finally:
        runner.close()

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"wrote {out_path}")
    print(json.dumps(report, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the LLM-as-judge harness on an eval dataset."
    )
    parser.add_argument(
        "--dataset",
        default="seed",
        choices=("seed", "unfair_tos", "opp115", "all"),
        help="Which labeled dataset to load (default: seed).",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=50,
        help="Max number of clauses to sample (default: 50).",
    )
    parser.add_argument(
        "--judge-model",
        default="claude-opus-4-5",
        help="Anthropic model id for the primary judge.",
    )
    parser.add_argument(
        "--cross-model",
        default="gpt-4o",
        help="OpenAI model id for the cross-family judge.",
    )
    parser.add_argument(
        "--cross-sample",
        type=float,
        default=0.15,
        help="Fraction of pairs to also run through the cross judge.",
    )
    parser.add_argument(
        "--no-cross",
        action="store_true",
        help="Disable the cross-family check even if OPENAI_API_KEY is set.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max simultaneous in-flight judge requests.",
    )
    parser.add_argument(
        "--cache",
        default=str(DEFAULT_CACHE_PATH),
        help="SQLite cache path (default: backend/evals/judge/cache.db).",
    )
    parser.add_argument(
        "--disagreements",
        default=str(DEFAULT_DISAGREEMENT_LOG),
        help="JSONL path for disagreement records.",
    )
    parser.add_argument(
        "--use-stub-predictions",
        action="store_true",
        help=(
            "Use dataset gold labels as predictions (skips detector). "
            "Useful for smoke-testing the judge pipeline without burning "
            "detector quota."
        ),
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional path to write the JSON report.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        return asyncio.run(_cli_main(args))
    except KeyboardInterrupt:
        print("interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "JudgeRunner",
    "VerdictCache",
    "DEFAULT_CACHE_PATH",
    "DEFAULT_DISAGREEMENT_LOG",
]
