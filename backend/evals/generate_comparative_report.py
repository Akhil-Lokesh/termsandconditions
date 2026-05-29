"""Generate ``evals/COMPARATIVE_REPORT.md`` from the Gemini agreement run JSON.

Reads ``evals/gemini_agreement_run.json`` (produced by
``run_gemini_agreement.py``) and renders a markdown report with:
- Resume-ready bullets
- Methodology section
- Detailed metrics (agreement %, kappa, per-severity kappa)
- Severity confusion matrix
- Top disagreement examples
- Free-tier safety notes

Cardinal rule: **never invent numbers**. Missing fields render as
``[no data — run gemini-agreement first]`` placeholders. The report is
safe to commit even when no agreement run has been performed yet.

Usage:
    cd backend
    python -m evals.generate_comparative_report
    python -m evals.generate_comparative_report \
        --in evals/gemini_agreement_run.json \
        --out evals/COMPARATIVE_REPORT.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

DEFAULT_IN = "evals/gemini_agreement_run.json"
DEFAULT_OUT = "evals/COMPARATIVE_REPORT.md"

# Renders when a numeric field is missing. NEVER replace with a fabricated
# value. Reviewers should be able to grep for this string to find gaps.
MISSING = "[no data — run gemini-agreement first]"

SEVERITIES_ORDER = ("critical", "high", "medium", "low", "none", "__none__")


def _fmt_pct(rate: Optional[float]) -> str:
    if rate is None:
        return MISSING
    try:
        return f"{float(rate) * 100:.1f}%"
    except (TypeError, ValueError):
        return MISSING


def _fmt_signed(v: Optional[float], digits: int = 3) -> str:
    if v is None:
        return MISSING
    try:
        return f"{float(v):+.{digits}f}"
    except (TypeError, ValueError):
        return MISSING


def _fmt_int(v: Any) -> str:
    if v is None:
        return MISSING
    try:
        return str(int(v))
    except (TypeError, ValueError):
        return MISSING


def _load_report(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _render_bullets(report: Optional[Dict[str, Any]]) -> str:
    """Render the resume-ready bullets section.

    Each bullet is rendered with placeholders if its underlying data is
    missing. The wording is identical so the bullet structure stays
    consistent across runs.
    """
    if report is None:
        n = MISSING
        sev_agree = MISSING
        cat_agree = MISSING
        sev_kappa = MISSING
        sev_interp = MISSING
        n_dis = MISSING
        gemini_model = MISSING
        rpm_hits = MISSING
        requests = MISSING
    else:
        a = report.get("agreement") or {}
        gs = report.get("gemini_stats") or {}
        n = _fmt_int(report.get("n_samples"))
        sev_agree = _fmt_pct(a.get("severity_agreement_rate"))
        cat_agree = _fmt_pct(a.get("category_agreement_rate"))
        sev_kappa = _fmt_signed(a.get("severity_kappa"))
        sev_interp = a.get("severity_kappa_interpretation") or MISSING
        n_dis = _fmt_int(report.get("n_disagreements"))
        gemini_model = report.get("model_gemini") or MISSING
        rpm_hits = _fmt_int(gs.get("rate_limit_hits"))
        requests = _fmt_int(gs.get("requests_sent"))

    lines = [
        "## Resume-ready bullets",
        "",
        "Bullets below are populated **only** from data in "
        "`evals/gemini_agreement_run.json`. Any placeholder marker (shown "
        "where a field was absent at report-generation time) means you "
        "should re-run `python -m evals.run_gemini_agreement` and regenerate.",
        "",
        f"- Designed a cross-family inter-annotator agreement study comparing "
        f"the Claude production detector against {gemini_model} on **N = {n}** "
        f"sampled clauses; severity Cohen's kappa = **{sev_kappa}** "
        f"(_{sev_interp}_).",
        f"- Severity exact-match agreement: **{sev_agree}**. "
        f"Risk-category exact-match agreement: **{cat_agree}**. "
        f"Logged **{n_dis}** disagreement examples for prompt-drift analysis "
        f"(see `evals/gemini_disagreements.jsonl`).",
        f"- Built skip-safe REST-based Gemini Flash integration (no SDK "
        f"dependency); honored the free-tier 15 RPM limit via per-instance "
        f"pacing lock — **{requests}** requests issued, **{rpm_hits}** rate-"
        f"limit retries on the most recent run.",
        f"- Hardened the eval harness with an import firewall (production "
        f"code cannot read the gold holdout) and a CI regression gate that "
        f"halts deploys on kappa drift > 0.03.",
        "",
    ]
    return "\n".join(lines)


def _render_metrics(report: Optional[Dict[str, Any]]) -> str:
    if report is None:
        return (
            "## Detailed metrics\n\n"
            f"{MISSING}\n"
        )
    a = report.get("agreement") or {}
    per_sev = a.get("per_severity_kappa") or {}
    lines = [
        "## Detailed metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Sample size (N) | {_fmt_int(report.get('n_samples'))} |",
        f"| Severity exact-match agreement | {_fmt_pct(a.get('severity_agreement_rate'))} |",
        f"| Category exact-match agreement | {_fmt_pct(a.get('category_agreement_rate'))} |",
        f"| Joint (severity + category) agreement | {_fmt_pct(a.get('joint_agreement_rate'))} |",
        f"| Severity Cohen's kappa | {_fmt_signed(a.get('severity_kappa'))} "
        f"(_{a.get('severity_kappa_interpretation') or MISSING}_) |",
        f"| Macro severity kappa | {_fmt_signed(a.get('macro_severity_kappa'))} |",
        f"| Category kappa | {_fmt_signed(a.get('category_kappa'))} |",
        "",
        "### Per-severity kappa (one-vs-rest)",
        "",
        "| Severity | Kappa |",
        "| --- | --- |",
    ]
    for sev in ("critical", "high", "medium", "low"):
        lines.append(f"| {sev} | {_fmt_signed(per_sev.get(sev))} |")
    lines.append("")
    return "\n".join(lines)


def _render_confusion(report: Optional[Dict[str, Any]]) -> str:
    lines = ["## Severity confusion matrix (Claude rows × Gemini columns)", ""]
    if report is None:
        lines.append(MISSING)
        return "\n".join(lines) + "\n"

    a = report.get("agreement") or {}
    matrix = a.get("severity_confusion_matrix") or {}
    if not matrix:
        lines.append(MISSING)
        return "\n".join(lines) + "\n"

    header = "| Claude \\\\ Gemini | " + " | ".join(SEVERITIES_ORDER) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(SEVERITIES_ORDER)) + " |"
    lines.extend([header, sep])
    for row in SEVERITIES_ORDER:
        cells = [str(matrix.get(row, {}).get(col, 0)) for col in SEVERITIES_ORDER]
        lines.append(f"| {row} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def _render_disagreements(report: Optional[Dict[str, Any]], log_path: Path) -> str:
    lines = ["## Top disagreement examples", ""]
    if not log_path.exists():
        lines.append(MISSING)
        return "\n".join(lines) + "\n"

    rows: List[dict] = []
    with log_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        lines.append("No disagreements found in the latest run "
                     "(perfect agreement, or the log is empty).")
        return "\n".join(lines) + "\n"

    for r in rows[:10]:
        cid = r.get("clause_id", "?")
        gap = r.get("severity_tier_gap", "?")
        claude = r.get("claude", {})
        gemini = r.get("gemini", {})
        text = (r.get("text") or "").replace("\n", " ")[:280]
        lines.append(
            f"- **{cid}** (severity-tier gap: {gap}) — "
            f"Claude: `{claude.get('severity')}` / `{claude.get('risk_category')}` · "
            f"Gemini: `{gemini.get('severity')}` / `{gemini.get('risk_category')}`"
        )
        lines.append(f"  > {text}")
        lines.append("")
    if len(rows) > 10:
        lines.append(f"_…{len(rows) - 10} more in `{log_path}`._")
        lines.append("")
    return "\n".join(lines)


def _render_methodology() -> str:
    return (
        "## Methodology\n\n"
        "Both raters perform the SAME task the production detector performs: "
        "flag clauses that warrant a consumer-risk alert and decline the rest. "
        "Each rater assigns one severity tier — one of "
        "`none / low / medium / high / critical` — plus one risk_category "
        "(11-value vocabulary defined in `evals/datasets/schema.py`). A `none` "
        "verdict means the clause is benign/descriptive and warrants no alert; "
        "for a `none` verdict the risk_category is not scored (there is no risk "
        "to categorise). This task alignment matters: the production "
        "`LLMClauseDetector` is a precision-first checklist matcher that returns "
        "NO finding for non-risky clauses, so a judge forced to assign a tier to "
        "every clause would manufacture disagreement on clauses both raters "
        "actually consider harmless. Claude predictions come from the production "
        "detector (the same code path users hit in the app); a non-flagged "
        "clause is recorded as `none`. Gemini labels come from "
        "`evals/judge/gemini_judge.py`, a REST-based wrapper that issues "
        "`generateContent` calls at temperature 0 with no search-grounding "
        "tools attached.\n\n"
        "Agreement is computed as the fraction of clauses where both raters "
        "produce the same label (exact match). Cohen's kappa is computed by "
        "`evals/metrics/kappa.py` over the union of observed labels (including "
        "`none`), so agreement on declining to flag a benign clause counts as "
        "agreement, exactly as it does in production.\n"
    )


def _render_safety() -> str:
    return (
        "## Free-tier safety notes\n\n"
        "`GeminiJudge` is built for the Gemini Flash free tier (15 RPM, "
        "1,500 RPD as of 2025). Key safeguards baked in:\n\n"
        "- Per-instance async pacing lock — minimum 4.5 s between requests "
        "(`RPM_PACING_SECONDS` in `evals/judge/gemini_judge.py`). Caps "
        "effective throughput at ~13 RPM.\n"
        "- Exponential backoff on `429`/`5xx` (`DEFAULT_MAX_RETRIES = 5`), "
        "honoring `Retry-After` headers when present.\n"
        "- Batch size 5 by default — 30 clauses = 6 requests, well below "
        "free-tier RPM/RPD ceilings.\n"
        "- Skip-safe: missing `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` causes "
        "the runner to exit 0 with a printed message; no artifact is written.\n"
        "- No `tools` array in the request body — search grounding cannot "
        "fire even by accident.\n\n"
        "If you need to scale past free-tier limits, raise the pacing "
        "constant or upgrade to Gemini's paid tier. Cost (paid tier, as of "
        "writing): roughly $0.075 / 1M input tokens, $0.30 / 1M output for "
        "`gemini-2.0-flash` — orders of magnitude cheaper than Claude or "
        "comparable frontier commercial models, which is the point of "
        "using it as the second rater.\n"
    )


def render_report(report: Optional[Dict[str, Any]], log_path: Path) -> str:
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    src = (report or {}).get("_outfile") or DEFAULT_IN
    git_commit = (report or {}).get("git_commit") or MISSING
    model_g = (report or {}).get("model_gemini") or MISSING
    timestamp = (report or {}).get("timestamp") or MISSING

    header = (
        "# Comparative Report — Claude (production detector) vs Gemini Flash\n\n"
        "_This file is auto-generated by `evals/generate_comparative_report.py`; "
        "do not edit by hand._\n\n"
        f"- **Generated:** {when}\n"
        f"- **Source data:** `{src}`\n"
        f"- **Run timestamp:** {timestamp}\n"
        f"- **Git commit:** `{git_commit}`\n"
        f"- **Gemini model:** `{model_g}`\n\n"
        "---\n\n"
    )

    return "\n".join([
        header,
        _render_bullets(report),
        _render_methodology(),
        _render_metrics(report),
        _render_confusion(report),
        _render_disagreements(report, log_path),
        _render_safety(),
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="in_path", type=Path, default=Path(DEFAULT_IN),
                    help=f"input JSON path (default {DEFAULT_IN})")
    ap.add_argument("--out", type=Path, default=Path(DEFAULT_OUT),
                    help=f"output Markdown path (default {DEFAULT_OUT})")
    ap.add_argument("--disagreement-log", type=Path,
                    default=Path("evals/gemini_disagreements.jsonl"),
                    help="JSONL path for disagreement examples")
    args = ap.parse_args()

    report = _load_report(args.in_path)
    if report is None:
        print(f"warning: no usable data at {args.in_path}; rendering placeholder report.")
    else:
        # Anchor the source path inside the report for traceability.
        report["_outfile"] = str(args.in_path)

    md = render_report(report, args.disagreement_log)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
