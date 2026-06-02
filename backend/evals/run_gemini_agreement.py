"""Run a Claude (production detector) vs Gemini Flash (independent rater)
inter-annotator agreement study.

This is a Layer-4-adjacent eval. It compares the production
``LLMClauseDetector`` (Claude) to ``GeminiJudge`` (Gemini Flash) on the
same sampled clauses. Both raters output (severity, risk_category) and
we compute:
- Exact-match agreement % (severity, category, joint)
- Cohen's kappa (severity, category)
- 4-tier confusion matrix (Claude severity vs Gemini severity)
- Disagreement examples (top-N most informative mismatches, with text)

Skip-safe:
- Missing ``GEMINI_API_KEY`` => exit 0 with a printed message; no artifact is written.
- Missing ``ANTHROPIC_API_KEY`` (production detector) => exit 0 with a printed message.

Usage:
    cd backend
    python -m evals.run_gemini_agreement \
        --n 30 --dataset all \
        --out evals/gemini_agreement_run.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make `backend/` importable when launched from the project root.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from evals.datasets.loader import load_dataset  # noqa: E402
from evals.judge.gemini_judge import (  # noqa: E402
    DEFAULT_BATCH_SIZE,
    DEFAULT_MODEL as GEMINI_DEFAULT_MODEL,
    GeminiJudge,
    GeminiNotConfigured,
    SEVERITIES,
)
from evals.metrics.kappa import (  # noqa: E402
    category_kappa,
    confusion_with_kappa,
)

logger = logging.getLogger(__name__)

# --- Defaults ------------------------------------------------------------- #

DEFAULT_N = 30
DEFAULT_DATASET = "all"
DEFAULT_OUT = "evals/gemini_agreement_run.json"
DEFAULT_DISAGREEMENT_LOG = "evals/gemini_disagreements.jsonl"
DEFAULT_RAW_DUMP = "evals/_cache/gemini_raw.jsonl"
DEFAULT_SEED = 42
MAX_DISAGREEMENT_EXAMPLES = 20


# --- Production detector wrapper (imported lazily) ------------------------ #

async def _run_production_detector(eval_clauses: List[Any]) -> List[dict]:
    """Run the production Claude detector against the sampled clauses.

    Mirrors ``baseline_runner.py``. Returns one prediction dict per input,
    preserving order: ``{"clause_id", "severity", "risk_category"}``.
    Missing detector outputs (clause not flagged) get severity=None.
    """
    # Lazy import — keeps `--help` instant + lets us fail clean if anthropic
    # isn't installed in the eval environment.
    from app.core.llm_clause_detector import LLMClauseDetector
    from app.services.claude_service import ClaudeService

    detector = LLMClauseDetector(ClaudeService())
    detector_input = [
        {"clause_number": c.clause_id, "section": c.section, "text": c.text}
        for c in eval_clauses
    ]
    findings = await detector.detect_risky_clauses(
        detector_input,
        company_name="GeminiAgreement",
        service_type="general",
    )
    by_id = {str(f.get("clause_number")): f for f in (findings or [])}

    predictions: List[dict] = []
    for c in eval_clauses:
        f = by_id.get(str(c.clause_id), {})
        sev = f.get("severity")
        if isinstance(sev, str):
            sev = sev.strip().lower() or None
        # The detector returns NO finding for clauses it judges non-risky. That
        # is a deliberate "no alert" verdict, not missing data — represent it as
        # "none" so it aligns with the Gemini judge's "none" tier (both raters
        # perform the same flag-or-decline task). Without this, a precision-first
        # checklist detector looks like it "disagrees" with a judge that is
        # forced to assign a tier to every benign clause.
        if sev is None:
            sev = "none"
        cat = f.get("risk_category")
        if isinstance(cat, str):
            cat = cat.strip().lower() or None
        predictions.append({
            "clause_id": c.clause_id,
            "severity": sev,
            "risk_category": cat,
        })
    return predictions


# --- Agreement metrics ---------------------------------------------------- #

def compute_agreement_metrics(
    claude_preds: List[dict],
    gemini_labels: List[dict],
) -> Dict[str, Any]:
    """Compute exact-match agreement, joint agreement, and confusion data.

    Both inputs must be aligned by clause_id (same order, same length).
    """
    if len(claude_preds) != len(gemini_labels):
        raise ValueError(
            f"alignment broken: {len(claude_preds)} preds vs {len(gemini_labels)} labels"
        )

    n = len(claude_preds)
    sev_match = 0
    cat_match = 0
    joint_match = 0
    severity_confusion: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for cp, gl in zip(claude_preds, gemini_labels):
        if cp["clause_id"] != gl["clause_id"]:
            raise ValueError(
                f"clause_id misalignment: {cp['clause_id']} != {gl['clause_id']}"
            )
        c_sev = cp.get("severity")
        g_sev = gl.get("severity")
        c_cat = cp.get("risk_category")
        g_cat = gl.get("risk_category")

        if c_sev == g_sev:
            sev_match += 1
        if c_cat == g_cat:
            cat_match += 1
        if c_sev == g_sev and c_cat == g_cat:
            joint_match += 1

        # Confusion: rows = claude severity, cols = gemini severity
        # (None becomes the "__none__" bucket so missing predictions are visible)
        row_key = c_sev if c_sev in SEVERITIES else "__none__"
        col_key = g_sev if g_sev in SEVERITIES else "__none__"
        severity_confusion[row_key][col_key] += 1

    # Build kappa input shape expected by ``confusion_with_kappa``.
    # The function reads: prediction["severity"] vs label["expected_severity"].
    label_input = [
        {"clause_id": gl["clause_id"], "expected_severity": gl.get("severity"),
         "expected_risk_category": gl.get("risk_category")}
        for gl in gemini_labels
    ]
    severity_block = confusion_with_kappa(claude_preds, label_input)

    # Category kappa, separately.
    cat_kappa_value = category_kappa(claude_preds, label_input)

    # Frozen plain-dict confusion (defaultdicts don't serialize cleanly).
    severity_confusion_plain = {
        row: dict(cols) for row, cols in severity_confusion.items()
    }

    return {
        "n": n,
        "severity_agreement_rate": round(sev_match / n, 4) if n else 0.0,
        "category_agreement_rate": round(cat_match / n, 4) if n else 0.0,
        "joint_agreement_rate": round(joint_match / n, 4) if n else 0.0,
        "severity_kappa": severity_block["overall_kappa"],
        "severity_kappa_interpretation": severity_block["overall_kappa_interpretation"],
        "macro_severity_kappa": severity_block["macro_kappa"],
        "per_severity_kappa": severity_block["per_severity_kappa"],
        "category_kappa": cat_kappa_value,
        "severity_confusion_matrix": severity_confusion_plain,
    }


def select_disagreement_examples(
    eval_clauses: List[Any],
    claude_preds: List[dict],
    gemini_labels: List[dict],
    limit: int = MAX_DISAGREEMENT_EXAMPLES,
) -> List[dict]:
    """Pick up to `limit` rows where Claude and Gemini differ on severity.

    Prioritizes high-impact mismatches (where Claude says critical/high but
    Gemini says low/medium, or vice versa) over adjacent-tier swaps.
    """
    rank_value = {"critical": 4, "high": 3, "medium": 2, "low": 1, None: 0}
    out: List[Tuple[int, dict]] = []  # (priority, row)
    for c, cp, gl in zip(eval_clauses, claude_preds, gemini_labels):
        c_sev, g_sev = cp.get("severity"), gl.get("severity")
        if c_sev == g_sev:
            continue
        gap = abs(rank_value.get(c_sev, 0) - rank_value.get(g_sev, 0))
        out.append((gap, {
            "clause_id": c.clause_id,
            "section": c.section,
            "text": c.text[:600],
            "claude": {"severity": c_sev, "risk_category": cp.get("risk_category")},
            "gemini": {"severity": g_sev, "risk_category": gl.get("risk_category")},
            "severity_tier_gap": gap,
        }))
    out.sort(key=lambda t: -t[0])
    return [row for _, row in out[:limit]]


# --- I/O helpers ---------------------------------------------------------- #

def _git_commit() -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_BACKEND_DIR.parent,
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _write_disagreement_log(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _write_raw_dump(path: Path, gemini_labels_raw: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in gemini_labels_raw:
            f.write(json.dumps(r) + "\n")


def _exit_skip(reason: str) -> int:
    print(f"gemini-agreement skipped — {reason}")
    return 0


# --- Entrypoint ----------------------------------------------------------- #

async def run(
    n: int,
    dataset: str,
    out_path: Path,
    disagreement_log_path: Path,
    raw_dump_path: Path,
    model: str,
    batch_size: int,
    seed: int,
) -> Dict[str, Any]:
    """Run the agreement study. Returns the full report dict."""
    eval_clauses = load_dataset(dataset, max_rows=n)
    if not eval_clauses:
        raise RuntimeError(f"no clauses loaded for dataset={dataset!r}")
    # Deterministic shuffle (loader already samples deterministically, this
    # is a belt-and-suspenders for cross-run reproducibility).
    rng = random.Random(seed)
    rng.shuffle(eval_clauses)
    eval_clauses = eval_clauses[:n]

    judge = GeminiJudge(model=model, batch_size=batch_size)

    # 1. Claude predictions (production path).
    print(f"running production detector on {len(eval_clauses)} clauses…")
    claude_preds = await _run_production_detector(eval_clauses)

    # 2. Gemini labels (independent rater).
    print(f"running gemini ({model}) on {len(eval_clauses)} clauses…")
    judge_input = [
        {"clause_id": c.clause_id, "section": c.section, "text": c.text}
        for c in eval_clauses
    ]
    gemini_labels_obj = await judge.label_batch(judge_input)
    gemini_labels = [lbl.to_dict() for lbl in gemini_labels_obj]

    # A "none" severity means "no consumer-risk alert" — there is no meaningful
    # risk_category for a non-risk. Null the category on both sides so the
    # category-agreement metric is computed only where a category is defined
    # (i.e. a real flagged risk), instead of penalising agreed non-risks for
    # disagreeing on an irrelevant category label.
    for pred in claude_preds:
        if pred.get("severity") == "none":
            pred["risk_category"] = None
    for lbl in gemini_labels:
        if lbl.get("severity") == "none":
            lbl["risk_category"] = None

    # 3. Agreement metrics.
    metrics = compute_agreement_metrics(claude_preds, gemini_labels)

    # 4. Disagreement examples.
    disagreements = select_disagreement_examples(
        eval_clauses, claude_preds, gemini_labels
    )

    # 5. Persist raw + disagreements.
    _write_raw_dump(raw_dump_path, gemini_labels)
    _write_disagreement_log(disagreement_log_path, disagreements)

    # 6. Build the final report.
    report = {
        "model_claude": "production-detector",
        "model_gemini": judge.name,
        "dataset": dataset,
        "n_samples": len(eval_clauses),
        "batch_size": batch_size,
        "seed": seed,
        "gemini_stats": {
            "requests_sent": judge.stats.requests_sent,
            "requests_retried": judge.stats.requests_retried,
            "rate_limit_hits": judge.stats.rate_limit_hits,
            "parse_failures": judge.stats.parse_failures,
            "elapsed_seconds": judge.stats.elapsed_seconds,
        },
        "agreement": metrics,
        "n_disagreements": len(disagreements),
        "disagreement_log_path": str(disagreement_log_path),
        "gemini_raw_path": str(raw_dump_path),
        "claude_predictions": claude_preds,
        "gemini_labels": gemini_labels,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    return report


def _print_summary(report: Dict[str, Any]) -> None:
    a = report["agreement"]
    print()
    print(f"=== Claude vs Gemini Flash Agreement (N={report['n_samples']}) ===")
    print(f"  severity agreement %:   {a['severity_agreement_rate'] * 100:.1f}")
    print(f"  category agreement %:   {a['category_agreement_rate'] * 100:.1f}")
    print(f"  joint agreement %:      {a['joint_agreement_rate'] * 100:.1f}")
    print(f"  severity Cohen's kappa: {a['severity_kappa']:+.3f} "
          f"({a['severity_kappa_interpretation']})")
    print(f"  category Cohen's kappa: {a['category_kappa']:+.3f}")
    print(f"  disagreements:          {report['n_disagreements']}")
    print(f"  gemini requests:        {report['gemini_stats']['requests_sent']} "
          f"({report['gemini_stats']['rate_limit_hits']} rate-limited)")
    print(f"  saved:                  {report.get('_outfile', '(see --out)')}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=DEFAULT_N,
                    help=f"sample size (default {DEFAULT_N})")
    ap.add_argument("--dataset", type=str, default=DEFAULT_DATASET,
                    help="dataset name passed to evals.datasets.loader.load_dataset")
    ap.add_argument("--out", type=Path, default=Path(DEFAULT_OUT),
                    help=f"output JSON path (default {DEFAULT_OUT})")
    ap.add_argument("--disagreement-log", type=Path,
                    default=Path(DEFAULT_DISAGREEMENT_LOG),
                    help="JSONL path for disagreement examples")
    ap.add_argument("--raw", type=Path, default=Path(DEFAULT_RAW_DUMP),
                    help="JSONL path for raw Gemini labels")
    ap.add_argument("--model", type=str, default=GEMINI_DEFAULT_MODEL,
                    help=f"Gemini model id (default {GEMINI_DEFAULT_MODEL})")
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                    help=f"clauses per Gemini request (default {DEFAULT_BATCH_SIZE})")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help="random seed for sampling")
    args = ap.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        return _exit_skip("GEMINI_API_KEY not set")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _exit_skip("ANTHROPIC_API_KEY not set (production detector needs it)")

    try:
        report = asyncio.run(run(
            n=args.n,
            dataset=args.dataset,
            out_path=args.out,
            disagreement_log_path=args.disagreement_log,
            raw_dump_path=args.raw,
            model=args.model,
            batch_size=args.batch_size,
            seed=args.seed,
        ))
    except GeminiNotConfigured as exc:
        return _exit_skip(str(exc))

    report["_outfile"] = str(args.out)
    _print_summary(report)
    print(f"\nwrote {args.out}")
    print(f"wrote {args.disagreement_log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
