"""Candidate suggester for manual gold-holdout adjudication — READ-ONLY.

Scans ``gold_holdout.jsonl`` for medium/high rows whose text matches
critical-tier patterns (forced arbitration + class waiver, jury-trial
waiver, broad liability caps, perpetual licenses, sale of personal data,
unilateral termination with forfeit) and PRINTS them as candidates for a
human to review.

INTEGRITY NOTE: this tool never writes to the holdout. Auto-relabeling the
sealed gold standard with the detector's own regex heuristics would make the
"independent" labels circular — the benchmark would just reward the detector
for matching its own patterns. Gold severities are hand-adjudicated only; use
this list as a worklist for that manual review, not as an automated rewrite.

Usage:
    cd backend
    python -m evals.datasets.auto_promote_critical            # print candidates
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
HOLDOUT_PATH = HERE / "gold_holdout.jsonl"


# Each pattern: (name, compiled regex, optional secondary regex that must
# ALSO match, description). Patterns are intentionally narrow — we'd rather
# miss a real critical than promote a false one.
PATTERNS: list[tuple[str, re.Pattern, re.Pattern | None, str]] = [
    (
        "arbitration_class_waiver",
        re.compile(r"\barbitrat\w+", re.IGNORECASE),
        re.compile(r"\b(class[\s-]?action|class[\s-]?wide|class\s+(claim|relief)|"
                   r"collective\s+action|representative\s+action)\b", re.IGNORECASE),
        "forced arbitration combined with class-action waiver",
    ),
    (
        "jury_trial_waiver",
        re.compile(r"\b(waiv\w+|relinquish\w*|give\s+up|forgo)\b", re.IGNORECASE),
        re.compile(r"\bjury\s+trial\b|\btrial\s+by\s+jury\b", re.IGNORECASE),
        "explicit waiver of jury trial right",
    ),
    (
        "broad_liability_cap",
        re.compile(r"\b(maximum|aggregate|total|entire)\s+liab\w+", re.IGNORECASE),
        re.compile(r"\$\s?(0|\d{1,3})\b|fees?\s+(you\s+)?paid|amount\s+(you\s+)?paid|"
                   r"hundred\s+dollars|us\s?\$\s?\d{1,4}\b", re.IGNORECASE),
        "broad liability cap (fees-paid or $0/small fixed amount)",
    ),
    (
        "perpetual_content_license",
        re.compile(r"\b(perpetual|irrevocable)\b", re.IGNORECASE),
        re.compile(r"\b(licen[sc]e|sublicens\w*|royalty[\s-]?free)\b", re.IGNORECASE),
        "perpetual or irrevocable license to user content",
    ),
    (
        "sale_personal_data",
        re.compile(r"\b(sell|sale\s+of|transfer|share)\b", re.IGNORECASE),
        re.compile(r"\b(personal\s+(information|data|details)|user\s+data|"
                   r"your\s+information)\b.*?\b(third[\s-]?part\w+|advertiser|"
                   r"marketing\s+partner|affiliate)\b", re.IGNORECASE | re.DOTALL),
        "sale or sharing of personal data with unnamed third parties",
    ),
    (
        "unilateral_termination_forfeit",
        re.compile(r"\bterminat\w+|suspend\w*\s+(your\s+)?(account|access)", re.IGNORECASE),
        re.compile(r"\b(no\s+refund|non[\s-]?refund\w*|forfeit\w*|without\s+(any\s+)?"
                   r"(notice|liability|refund))\b", re.IGNORECASE),
        "unilateral termination with prepaid forfeiture / no refund",
    ),
    (
        "unilateral_terms_change_binding",
        re.compile(r"(change|modify|amend|update|revise).*?(terms|agreement|policy)",
                   re.IGNORECASE | re.DOTALL),
        re.compile(r"\b(continued\s+use|by\s+continuing|deemed\s+to\s+have\s+accepted|"
                   r"binding\s+on\s+you)\b", re.IGNORECASE),
        "unilateral binding terms changes by continued-use mechanism",
    ),
]


def load_rows() -> list[dict]:
    if not HOLDOUT_PATH.exists():
        sys.exit(f"{HOLDOUT_PATH} not found")
    return [json.loads(l) for l in HOLDOUT_PATH.open() if l.strip()]


def match_patterns(text: str) -> list[tuple[str, str]]:
    """Return list of (pattern_name, description) that match the text."""
    hits = []
    for name, primary, secondary, desc in PATTERNS:
        if not primary.search(text):
            continue
        if secondary is not None and not secondary.search(text):
            continue
        hits.append((name, desc))
    return hits


def show_dist(rows: list[dict], label: str) -> None:
    c = Counter(r["expected_severity"] for r in rows)
    print(f"\n{label}:")
    print(f"  critical: {c.get('critical', 0):>3}")
    print(f"  high:     {c.get('high', 0):>3}")
    print(f"  medium:   {c.get('medium', 0):>3}")
    print(f"  low:      {c.get('low', 0):>3}")
    print(f"  TOTAL:    {sum(c.values()):>3}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--include-low", action="store_true",
                    help="also scan low-severity rows for candidates")
    args = ap.parse_args()

    rows = load_rows()
    show_dist(rows, "BEFORE")

    eligible_severities = {"medium", "high"}
    if args.include_low:
        eligible_severities.add("low")

    proposals: list[tuple[int, dict, list[tuple[str, str]]]] = []
    for i, rec in enumerate(rows):
        if rec["expected_severity"] not in eligible_severities:
            continue
        if rec["expected_severity"] == "critical":
            continue
        hits = match_patterns(rec["text"])
        if hits:
            proposals.append((i, rec, hits))

    if not proposals:
        print("\nno candidates matched. holdout calibration unchanged.")
        return

    print(f"\n{'=' * 72}")
    print(f"PROPOSED PROMOTIONS: {len(proposals)} rows -> critical")
    print(f"{'=' * 72}")
    for i, rec, hits in proposals:
        pat_names = ", ".join(n for n, _ in hits)
        print(f"\n  [{rec['clause_id']}]  current={rec['expected_severity']:<6}"
              f"  cat={rec['expected_risk_category']}")
        print(f"  matched: {pat_names}")
        snippet = textwrap.fill(
            rec["text"][:280] + ("…" if len(rec["text"]) > 280 else ""),
            width=72, initial_indent="    ", subsequent_indent="    ",
        )
        print(snippet)

    # Project what the distribution WOULD look like if a human promoted these —
    # informational only; nothing is written.
    projected = [dict(r) for r in rows]
    for i, _rec, _hits in proposals:
        projected[i]["expected_severity"] = "critical"
    show_dist(projected, "PROJECTED IF MANUALLY PROMOTED")

    print(f"\n{'=' * 72}")
    print("READ-ONLY — no changes written (gold labels are hand-adjudicated).")
    print("Use the list above as a worklist for manual review.")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()
