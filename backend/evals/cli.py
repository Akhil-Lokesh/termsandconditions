"""Unified eval CLI.

A single entrypoint that wraps the four eval workflows:

    python -m evals.cli stats     --dataset all
    python -m evals.cli baseline  --dataset all --n 200
    python -m evals.cli judge     --dataset seed --sample 50
    python -m evals.cli ci-check  --current results.json --baseline evals/baseline.json

Each sub-command imports its dependencies LAZILY so:

  * ``python -m evals.cli --help`` is instant.
  * A missing optional library (e.g. ``openai`` for the judge) only
    surfaces when you actually try to run that sub-command, not when
    you ask the CLI to list its commands.
  * ``stats`` works even without ANY API keys — useful for quick
    dataset sanity checks in a fresh checkout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional


def _cmd_stats(args: argparse.Namespace) -> int:
    """Print dataset stats (counts per severity + per category)."""
    # Lazy import — only pulls in evals.datasets when actually needed.
    from evals.datasets.loader import dataset_stats

    out = dataset_stats(args.dataset)
    print(json.dumps(out, indent=2))
    return 0


def _cmd_baseline(args: argparse.Namespace) -> int:
    """Run the baseline kappa report (skips cleanly without API key)."""
    from evals.baseline_runner import main as baseline_main

    forwarded: List[str] = [
        "--dataset",
        args.dataset,
        "--n",
        str(args.n),
    ]
    if args.seed is not None:
        forwarded += ["--seed", str(args.seed)]
    if args.out:
        forwarded += ["--out", str(args.out)]
    return baseline_main(forwarded)


def _cmd_judge(args: argparse.Namespace) -> int:
    """Run the LLM-as-judge harness."""
    from evals.judge.runner import main as judge_main

    forwarded: List[str] = [
        "--dataset",
        args.dataset,
        "--sample",
        str(args.sample),
        "--cross-sample",
        str(args.cross_sample),
        "--concurrency",
        str(args.concurrency),
    ]
    if args.judge_model:
        forwarded += ["--judge-model", args.judge_model]
    if args.cross_model:
        forwarded += ["--cross-model", args.cross_model]
    if args.no_cross:
        forwarded += ["--no-cross"]
    if args.use_stub_predictions:
        forwarded += ["--use-stub-predictions"]
    if args.out:
        forwarded += ["--out", str(args.out)]
    return judge_main(forwarded)


def _cmd_ci_check(args: argparse.Namespace) -> int:
    from evals.ci_gate import main as gate_main

    forwarded: List[str] = [
        "--current",
        str(args.current),
        "--baseline",
        str(args.baseline),
        "--max-regression",
        str(args.max_regression),
    ]
    if args.strict:
        forwarded += ["--strict"]
    if args.out:
        forwarded += ["--out", str(args.out)]
    return gate_main(forwarded)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evals.cli",
        description="T&C eval CLI — stats, baseline, judge, CI gate.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ---- stats ---- #
    p_stats = sub.add_parser(
        "stats",
        help="Print labeled-dataset statistics (counts per severity/category).",
    )
    p_stats.add_argument(
        "--dataset",
        default="all",
        choices=("seed", "unfair_tos", "opp115", "all"),
    )
    p_stats.set_defaults(func=_cmd_stats)

    # ---- baseline ---- #
    p_base = sub.add_parser(
        "baseline",
        help="Run the LLM detector on a dataset and compute the kappa baseline.",
    )
    p_base.add_argument(
        "--dataset",
        default="all",
        choices=("seed", "unfair_tos", "opp115", "all"),
    )
    p_base.add_argument("--n", type=int, default=200)
    p_base.add_argument("--seed", type=int, default=42)
    p_base.add_argument(
        "--out",
        type=Path,
        default=None,
        help="JSON output path (default: evals/baseline.json).",
    )
    p_base.set_defaults(func=_cmd_baseline)

    # ---- judge ---- #
    p_judge = sub.add_parser(
        "judge",
        help="Run the LLM-as-judge harness (Claude primary + GPT-4o cross-check).",
    )
    p_judge.add_argument(
        "--dataset",
        default="seed",
        choices=("seed", "unfair_tos", "opp115", "all"),
    )
    p_judge.add_argument("--sample", type=int, default=50)
    p_judge.add_argument("--judge-model", default="claude-opus-4-5")
    p_judge.add_argument("--cross-model", default="gpt-4o")
    p_judge.add_argument("--cross-sample", type=float, default=0.15)
    p_judge.add_argument("--no-cross", action="store_true")
    p_judge.add_argument("--concurrency", type=int, default=5)
    p_judge.add_argument("--use-stub-predictions", action="store_true")
    p_judge.add_argument("--out", type=Path, default=None)
    p_judge.set_defaults(func=_cmd_judge)

    # ---- ci-check ---- #
    p_ci = sub.add_parser(
        "ci-check",
        help="Compare a current eval result against the committed baseline.",
    )
    p_ci.add_argument("--current", type=Path, required=True)
    p_ci.add_argument("--baseline", type=Path, required=True)
    p_ci.add_argument("--max-regression", type=float, default=0.03)
    p_ci.add_argument("--strict", action="store_true")
    p_ci.add_argument("--out", type=Path, default=None)
    p_ci.set_defaults(func=_cmd_ci_check)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
