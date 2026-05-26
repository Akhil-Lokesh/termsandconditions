"""Re-grade existing gold holdout rows.

Walks through rows in ``gold_holdout.jsonl`` matching a chosen tier filter,
shows the current label, and lets you change severity, change category,
keep as-is, or delete the row. Rewrites the file in place atomically after
every confirmed change.

Default filter is ``medium`` + ``high`` — that's where most upgrades to
``critical`` will come from. Use ``--tier all`` to walk every row, or
``--tier critical`` to review just the already-criticals.

Usage:
    cd backend
    python -m evals.datasets.regrade_gold_holdout
    python -m evals.datasets.regrade_gold_holdout --tier all
    python -m evals.datasets.regrade_gold_holdout --tier high
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

from evals.datasets.schema import RISK_CATEGORY_VALUES, EvalClause

HERE = Path(__file__).parent
OUTPUT_PATH = HERE / "gold_holdout.jsonl"

TARGETS = {"critical": 20, "high": 40, "medium": 50, "low": 30}
SEVERITY_MAP = {"1": "critical", "2": "high", "3": "medium", "4": "low"}
CATEGORY_MAP = {str(i + 1): c for i, c in enumerate(RISK_CATEGORY_VALUES)}
TIER_FILTERS = ("all", "critical", "high", "medium", "low", "default")


def load_rows() -> list[dict]:
    if not OUTPUT_PATH.exists():
        sys.exit(f"{OUTPUT_PATH} not found — run the labeler first")
    rows = []
    with OUTPUT_PATH.open() as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def atomic_rewrite(rows: list[dict]) -> None:
    """Atomic write — temp file + rename. No half-written state on crash."""
    fd, tmp_name = tempfile.mkstemp(
        dir=OUTPUT_PATH.parent, prefix=".gold_holdout.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        os.replace(tmp_name, OUTPUT_PATH)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def dist(rows: list[dict]) -> Counter:
    return Counter(r["expected_severity"] for r in rows)


def show_progress(rows: list[dict]) -> None:
    d = dist(rows)
    parts = [
        f"{tier[0].upper()}:{d[tier]:>2}/{tgt}"
        for tier, tgt in TARGETS.items()
    ]
    print(f"\nprogress:  {'  '.join(parts)}   total {sum(d.values())}/140")


def show_row(rec: dict, idx: int, total: int) -> None:
    print("\n" + "=" * 72)
    print(f"  REGRADING  {idx}/{total}")
    print("=" * 72)
    print(f"clause_id:        {rec['clause_id']}")
    print(f"section:          {rec.get('section', '?')}")
    print(f"current label:    {rec['expected_severity']} / "
          f"{rec['expected_risk_category']}")
    if rec.get("notes"):
        print(f"notes:            {rec['notes']}")
    print()
    print("text:")
    print("-" * 72)
    print(textwrap.fill(
        rec["text"], width=72, initial_indent="  ", subsequent_indent="  "
    ))
    print("-" * 72)


def ask_severity() -> str | None:
    print("\nnew severity:  1)critical  2)high  3)medium  4)low   x)cancel")
    while True:
        ans = input("> ").strip().lower()
        if ans == "x":
            return None
        if ans in SEVERITY_MAP:
            return SEVERITY_MAP[ans]
        print("invalid — pick 1/2/3/4 or x")


def ask_category() -> str | None:
    print("\nnew category:")
    items = list(CATEGORY_MAP.items())
    half = (len(items) + 1) // 2
    for i in range(half):
        l_k, l_v = items[i]
        if i + half < len(items):
            r_k, r_v = items[i + half]
            print(f"  {l_k:>2}) {l_v:<16}   {r_k:>2}) {r_v}")
        else:
            print(f"  {l_k:>2}) {l_v}")
    print("  x) cancel")
    while True:
        ans = input("> ").strip().lower()
        if ans == "x":
            return None
        if ans in CATEGORY_MAP:
            return CATEGORY_MAP[ans]
        print(f"invalid — pick 1-{len(CATEGORY_MAP)} or x")


def filter_rows(rows: list[dict], tier: str) -> list[int]:
    """Return indices (into rows) matching the chosen tier filter."""
    if tier == "all":
        return list(range(len(rows)))
    if tier == "default":
        return [
            i for i, r in enumerate(rows)
            if r["expected_severity"] in ("medium", "high")
        ]
    return [i for i, r in enumerate(rows) if r["expected_severity"] == tier]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier", choices=TIER_FILTERS, default="default",
                    help="which severity bucket to walk (default: medium+high)")
    args = ap.parse_args()

    rows = load_rows()
    indices = filter_rows(rows, args.tier)
    if not indices:
        print(f"no rows match tier filter '{args.tier}'.")
        return

    print(f"loaded {len(rows)} rows · regrading {len(indices)} "
          f"in tier filter '{args.tier}'")
    show_progress(rows)
    print("\npress Enter to begin (Ctrl-C to exit)")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        return

    history: list[int] = []  # stack of visited indices for 'back'
    pos = 0
    while pos < len(indices):
        i = indices[pos]
        rec = rows[i]
        show_row(rec, pos + 1, len(indices))
        print("\noptions:")
        print("  s) change severity     c) change category     k) keep as-is")
        print("  d) delete this row     b) back                q) quit & save")
        try:
            ans = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if ans == "q":
            break
        if ans == "k":
            history.append(pos)
            pos += 1
            continue
        if ans == "b":
            if not history:
                print("nothing to go back to.")
                continue
            pos = history.pop()
            continue
        if ans == "d":
            confirm = input(f"delete {rec['clause_id']}? [y/N] ").strip().lower()
            if confirm == "y":
                deleted_id = rec["clause_id"]
                del rows[i]
                indices = filter_rows(rows, args.tier)
                atomic_rewrite(rows)
                print(f"[deleted] {deleted_id}")
                show_progress(rows)
                if pos >= len(indices):
                    break
            continue
        if ans == "s":
            new_sev = ask_severity()
            if new_sev is None:
                continue
            old_sev = rec["expected_severity"]
            rec["expected_severity"] = new_sev
            try:
                EvalClause(**{k: v for k, v in rec.items()
                              if not k.startswith("_")})
            except Exception as e:
                rec["expected_severity"] = old_sev
                print(f"validation failed: {e} — reverted")
                continue
            atomic_rewrite(rows)
            print(f"[updated] {rec['clause_id']}  {old_sev} -> {new_sev}")
            show_progress(rows)
            indices = filter_rows(rows, args.tier)
            history.append(pos)
            pos += 1
            continue
        if ans == "c":
            new_cat = ask_category()
            if new_cat is None:
                continue
            old_cat = rec["expected_risk_category"]
            rec["expected_risk_category"] = new_cat
            try:
                EvalClause(**{k: v for k, v in rec.items()
                              if not k.startswith("_")})
            except Exception as e:
                rec["expected_risk_category"] = old_cat
                print(f"validation failed: {e} — reverted")
                continue
            atomic_rewrite(rows)
            print(f"[updated] {rec['clause_id']}  cat {old_cat} -> {new_cat}")
            continue

        print("unknown choice — pick s/c/k/d/b/q")

    print("\n" + "=" * 72)
    print("session ended.")
    show_progress(rows)
    print(f"output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
