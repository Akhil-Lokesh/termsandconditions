"""Interactive terminal labeler for the gold holdout.

Reads ``gold_holdout_queue.jsonl`` stubs, prompts per-clause for severity
+ category + optional notes, and appends validated rows to
``gold_holdout.jsonl``. Resumable — re-run any time; clauses already in
the output file are skipped automatically.

Usage:
    cd backend
    python -m evals.datasets.label_gold_holdout
"""

from __future__ import annotations

import json
import sys
import textwrap
from collections import Counter
from pathlib import Path

from evals.datasets.schema import RISK_CATEGORY_VALUES, EvalClause

HERE = Path(__file__).parent
QUEUE_PATH = HERE / "gold_holdout_queue.jsonl"
OUTPUT_PATH = HERE / "gold_holdout.jsonl"

TARGETS = {"critical": 20, "high": 40, "medium": 50, "low": 30}
TOTAL_TARGET = sum(TARGETS.values())

SEVERITY_MAP = {"1": "critical", "2": "high", "3": "medium", "4": "low"}
CATEGORY_MAP = {str(i + 1): c for i, c in enumerate(RISK_CATEGORY_VALUES)}


def load_done_ids() -> set[str]:
    if not OUTPUT_PATH.exists():
        return set()
    done = set()
    with OUTPUT_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            done.add(json.loads(line)["clause_id"])
    return done


def load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        sys.exit(
            f"queue not found at {QUEUE_PATH}\n"
            "run: python -m evals.datasets.sample_for_labeling"
        )
    with QUEUE_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def current_dist() -> Counter:
    c: Counter = Counter()
    if not OUTPUT_PATH.exists():
        return c
    with OUTPUT_PATH.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            c[json.loads(line)["expected_severity"]] += 1
    return c


def show_clause(rec: dict, idx: int, total: int, done_count: int) -> None:
    print("\n" + "=" * 72)
    print(f"  LABELING  {done_count + 1}/{TOTAL_TARGET} target   "
          f"(queue position {idx}/{total})")
    print("=" * 72)
    print(f"clause_id:        {rec['clause_id']}")
    print(f"source dataset:   {rec.get('_hint_source_dataset', '?')}")
    print(f"section:          {rec.get('section', '?')}")
    print(f"hint category:    {rec.get('_hint_category', '(none)')}  "
          "[upstream guess — you decide]")
    print()
    print("text:")
    print("-" * 72)
    print(textwrap.fill(
        rec["text"], width=72, initial_indent="  ", subsequent_indent="  "
    ))
    print("-" * 72)


def ask_severity() -> str | None:
    print("\nseverity:  1)critical  2)high  3)medium  4)low   "
          "s)skip  b)back  q)quit")
    while True:
        ans = input("> ").strip().lower()
        if ans in ("q", "s", "b"):
            return ans
        if ans in SEVERITY_MAP:
            return SEVERITY_MAP[ans]
        print("invalid — pick 1/2/3/4 or s/b/q")


def ask_category() -> str | None:
    print("\ncategory:")
    items = list(CATEGORY_MAP.items())
    half = (len(items) + 1) // 2
    left, right = items[:half], items[half:]
    for i in range(half):
        l_k, l_v = left[i]
        if i < len(right):
            r_k, r_v = right[i]
            print(f"  {l_k:>2}) {l_v:<16}   {r_k:>2}) {r_v}")
        else:
            print(f"  {l_k:>2}) {l_v}")
    print("  s) skip   q) quit")
    while True:
        ans = input("> ").strip().lower()
        if ans in ("q", "s"):
            return ans
        if ans in CATEGORY_MAP:
            return CATEGORY_MAP[ans]
        print(f"invalid — pick 1-{len(CATEGORY_MAP)} or s/q")


def show_progress() -> None:
    dist = current_dist()
    parts = [
        f"{tier[0].upper()}:{dist[tier]:>2}/{tgt}"
        for tier, tgt in TARGETS.items()
    ]
    total = sum(dist.values())
    print(f"\nprogress:  {'  '.join(parts)}   total {total}/{TOTAL_TARGET}")


def main() -> None:
    queue = load_queue()
    done = load_done_ids()

    show_progress()
    remaining = len(queue) - len(done)
    print(f"\n{len(done)} labeled · {remaining} clauses left in queue")
    print(f"output: {OUTPUT_PATH}")
    print("\npress Enter to begin (Ctrl-C to exit)")
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        return

    prev_id: str | None = None
    quit_flag = False
    for idx, rec in enumerate(queue, 1):
        if quit_flag:
            break
        if rec["clause_id"] in done:
            continue

        while True:
            show_clause(rec, idx, len(queue), len(done))
            sev = ask_severity()
            if sev == "q":
                quit_flag = True
                break
            if sev == "s":
                break
            if sev == "b":
                if prev_id is None:
                    print("nothing to go back to.")
                    continue
                _remove_last_record(prev_id)
                done.discard(prev_id)
                print(f"removed {prev_id}; re-run to re-label it.")
                prev_id = None
                show_progress()
                break

            cat = ask_category()
            if cat == "q":
                quit_flag = True
                break
            if cat == "s":
                break

            try:
                notes = input("\nnotes (Enter to skip):\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                quit_flag = True
                break

            labeled = {
                "clause_id": rec["clause_id"],
                "section": rec.get("section", "Unknown") or "Unknown",
                "text": rec["text"],
                "expected_severity": sev,
                "expected_risk_category": cat,
                "notes": notes,
                "source": "hand-labeled (gold)",
            }
            try:
                EvalClause(**labeled)
            except Exception as e:
                print(f"validation failed: {e}\nnot saved — try again")
                continue

            with OUTPUT_PATH.open("a") as f:
                f.write(json.dumps(labeled) + "\n")
            done.add(rec["clause_id"])
            prev_id = rec["clause_id"]
            print(f"\n[saved] {rec['clause_id']}  ->  {sev} / {cat}")
            show_progress()
            break

    print("\n" + "=" * 72)
    print("session ended.")
    show_progress()
    print(f"output: {OUTPUT_PATH}")


def _remove_last_record(clause_id: str) -> None:
    if not OUTPUT_PATH.exists():
        return
    with OUTPUT_PATH.open() as f:
        rows = [
            line for line in f
            if line.strip() and json.loads(line)["clause_id"] != clause_id
        ]
    with OUTPUT_PATH.open("w") as f:
        f.writelines(rows)


if __name__ == "__main__":
    main()
