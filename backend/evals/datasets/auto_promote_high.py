"""Heuristic auto-promoter for the gold holdout — high tier.

Sibling of ``auto_promote_critical.py``. Scans medium-severity rows for
patterns characteristic of HIGH-tier risk (one-sided indemnification,
auto-renewal, broad data sharing, sole-discretion termination/content
removal, liability caps, mandatory venue, broad content licenses,
class-action waiver alone). Promotes matches medium -> high.

Defaults to dry-run; pass ``--apply`` to write atomically. Only touches
rows currently at ``medium`` — won't downgrade critical/high, won't
promote low.

Usage:
    cd backend
    python -m evals.datasets.auto_promote_high           # dry run
    python -m evals.datasets.auto_promote_high --apply   # write
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
HOLDOUT_PATH = HERE / "gold_holdout.jsonl"


PATTERNS: list[tuple[str, re.Pattern, re.Pattern | None, str]] = [
    (
        "one_sided_indemnification",
        re.compile(r"\byou\s+(agree\s+to\s+)?(indemnify|hold\s+\w+\s+harmless|"
                   r"defend)\b", re.IGNORECASE),
        None,
        "user indemnifies company (often without reciprocity)",
    ),
    (
        "auto_renewal",
        re.compile(r"\bauto[\s-]?renew\w*|automatic\w*\s+renew\w*|"
                   r"renew\s+automatically\b", re.IGNORECASE),
        None,
        "auto-renewing subscription",
    ),
    (
        "broad_data_sharing",
        re.compile(r"\b(share|disclose|provide)\b", re.IGNORECASE),
        re.compile(r"\b(personal\s+(information|data)|your\s+information|user\s+data)\b.*"
                   r"\b(third[\s-]?part\w+|affiliate|partner|advertiser|service\s+provider)",
                   re.IGNORECASE | re.DOTALL),
        "sharing personal data with third parties / affiliates / partners",
    ),
    (
        "sole_discretion_termination",
        re.compile(r"\bsole\s+discretion\b", re.IGNORECASE),
        re.compile(r"\b(terminat\w+|suspend\w*|disable\w*|cancel\w*|"
                   r"remove\w*)\b.*\b(account|access|service|user)\b",
                   re.IGNORECASE | re.DOTALL),
        "sole-discretion account/service termination",
    ),
    (
        "sole_discretion_content_removal",
        re.compile(r"\bsole\s+discretion\b", re.IGNORECASE),
        re.compile(r"\b(remove|delete|take\s+down|reject)\b.*\b(content|post|"
                   r"submission|material)\b", re.IGNORECASE | re.DOTALL),
        "sole-discretion content removal",
    ),
    (
        "liability_limitation",
        re.compile(r"\b(limit\w*\s+of\s+)?liab\w+|liab\w+\s+(shall\s+be\s+)?limit\w+",
                   re.IGNORECASE),
        re.compile(r"\b(no\s+event|in\s+no\s+case|under\s+no\s+circumstances|"
                   r"not\s+(be\s+)?liable|disclaim|exclude\w*)\b", re.IGNORECASE),
        "broad liability disclaimer / limitation",
    ),
    (
        "mandatory_venue",
        re.compile(r"\b(exclusive\s+(jurisdiction|venue)|venue\s+shall\s+be|"
                   r"submit\s+to\s+the\s+(exclusive\s+)?jurisdiction)\b",
                   re.IGNORECASE),
        None,
        "mandatory forum / venue selection",
    ),
    (
        "broad_content_license",
        re.compile(r"\b(licen[sc]e|right)\b.*\bto\s+(use|copy|modify|adapt|translate|"
                   r"distribute|display|publish|reproduce|prepare\s+derivative)",
                   re.IGNORECASE | re.DOTALL),
        re.compile(r"\b(your\s+content|user\s+content|submission|post|materials?)\b",
                   re.IGNORECASE),
        "broad license to user-generated content",
    ),
    (
        "class_action_waiver_alone",
        re.compile(r"\b(class[\s-]?action|class[\s-]?wide|representative\s+action)\s+"
                   r"(waiver|prohibit|preclu)\w*", re.IGNORECASE),
        None,
        "class-action waiver (standalone)",
    ),
    (
        "unilateral_terms_change_continued_use",
        re.compile(r"(change|modify|amend|update)\w*\s+(these\s+)?(terms|agreement|policy)",
                   re.IGNORECASE),
        re.compile(r"\b(continued\s+use|by\s+continuing|deemed\s+(to\s+)?(have\s+)?"
                   r"accept\w+|posting)\b", re.IGNORECASE),
        "unilateral terms change with continued-use acceptance",
    ),
    (
        "warranty_disclaimer",
        re.compile(r"\b(as[\s-]?is|as\s+available)\b|\bdisclaim\w*\s+(all\s+)?"
                   r"warrant\w+|without\s+warrant\w+", re.IGNORECASE),
        None,
        "blanket warranty disclaimer (as-is / no implied warranties)",
    ),
]


def load_rows() -> list[dict]:
    if not HOLDOUT_PATH.exists():
        sys.exit(f"{HOLDOUT_PATH} not found")
    return [json.loads(l) for l in HOLDOUT_PATH.open() if l.strip()]


def atomic_rewrite(rows: list[dict]) -> None:
    fd, tmp = tempfile.mkstemp(dir=HOLDOUT_PATH.parent,
                                prefix=".gold_holdout.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        os.replace(tmp, HOLDOUT_PATH)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def match_patterns(text: str) -> list[tuple[str, str]]:
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
    ap.add_argument("--apply", action="store_true",
                    help="actually write changes (default: dry run)")
    ap.add_argument("--max", type=int, default=None,
                    help="cap number of promotions (priority: most pattern hits first)")
    args = ap.parse_args()

    rows = load_rows()
    show_dist(rows, "BEFORE")

    proposals: list[tuple[int, dict, list[tuple[str, str]]]] = []
    for i, rec in enumerate(rows):
        if rec["expected_severity"] != "medium":
            continue
        hits = match_patterns(rec["text"])
        if hits:
            proposals.append((i, rec, hits))

    # Sort by number of pattern hits desc — strongest signals first.
    proposals.sort(key=lambda t: -len(t[2]))

    if args.max is not None:
        proposals = proposals[:args.max]

    if not proposals:
        print("\nno candidates matched.")
        return

    print(f"\n{'=' * 72}")
    print(f"PROPOSED PROMOTIONS: {len(proposals)} rows  medium -> high")
    print(f"{'=' * 72}")
    for i, rec, hits in proposals:
        pat_names = ", ".join(n for n, _ in hits)
        print(f"\n  [{rec['clause_id']}]  cat={rec['expected_risk_category']}  "
              f"({len(hits)} pattern{'s' if len(hits) > 1 else ''})")
        print(f"  matched: {pat_names}")
        snippet = textwrap.fill(
            rec["text"][:240] + ("…" if len(rec["text"]) > 240 else ""),
            width=72, initial_indent="    ", subsequent_indent="    ",
        )
        print(snippet)

    projected = [dict(r) for r in rows]
    for i, _rec, _hits in proposals:
        projected[i]["expected_severity"] = "high"
    show_dist(projected, "PROJECTED AFTER")

    if not args.apply:
        print(f"\n{'=' * 72}")
        print("DRY RUN — no changes written.")
        print("Re-run with --apply to commit. Use --max N to cap volume.")
        print(f"{'=' * 72}")
        return

    for i, _rec, _hits in proposals:
        rows[i]["expected_severity"] = "high"
    atomic_rewrite(rows)
    show_dist(rows, "AFTER (written)")
    print(f"\nwrote {HOLDOUT_PATH}")


if __name__ == "__main__":
    main()
