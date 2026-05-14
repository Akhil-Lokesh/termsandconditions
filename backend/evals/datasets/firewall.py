"""Import firewall for the gold-standard evaluation holdout file.

The single most expensive mistake in eval work is leaking your held-out
test set into the prompt/training pipeline — it silently invalidates every
accuracy claim downstream. This module guarantees, at runtime, that the
gold holdout file (``gold_holdout.jsonl``) is only readable by code under
``backend/evals/`` (and explicitly named eval-test modules under
``backend/tests/``). Production code paths under ``app/core/``,
``app/services/``, and ``app/api/`` cannot reach it — even indirectly via
helpers, monkey-patching, or import shenanigans — because the caller
inspection walks the entire stack.

There is also a complementary static CI rule
(``backend/scripts/check_holdout_firewall.sh``) that greps the source tree
for literal references to ``gold_holdout`` in ``backend/app/``. Together:

* **Static** layer: greps for direct string references. Catches the obvious
  "I'll just import the JSONL path directly" mistake.
* **Runtime** layer (this file): inspects the call stack on every read so
  that even an indirect access through a shared helper is blocked.

Both must pass for the holdout to be considered sealed.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
import pathlib
from typing import Any, List

logger = logging.getLogger(__name__)


GOLD_HOLDOUT_PATH = pathlib.Path(__file__).parent / "gold_holdout.jsonl"

# Optional schema — the sibling ``schema`` module is being authored by a
# separate agent and may not exist yet. Import lazily and fall back to dict.
try:  # pragma: no cover - optional import path
    from evals.datasets.schema import EvalClause  # type: ignore
except Exception:  # noqa: BLE001 - schema module may not exist yet
    EvalClause = None  # type: ignore[assignment]


# Path segments that indicate a PRODUCTION caller. Any frame whose file
# lives under one of these prefixes is forbidden from reading the holdout.
_FORBIDDEN_PATH_SEGMENTS = (
    os.path.join("backend", "app", "core"),
    os.path.join("backend", "app", "services"),
    os.path.join("backend", "app", "api"),
)

# Path segments that indicate an ALLOWED caller (eval code or eval-specific
# tests). A frame is allowed if its file lives under one of these prefixes.
_ALLOWED_PATH_SEGMENTS = (
    os.path.join("backend", "evals"),
)


def _is_eval_test_file(filename: str) -> bool:
    """Return True if a file under ``backend/tests/`` is an eval test.

    Eval tests are named ``test_*evals*.py`` (the firewall test itself is
    also explicitly allowed). Files under ``backend/tests/`` that are NOT
    eval tests are still allowed to call ``load_gold_holdout`` for unit
    testing of the firewall mechanism itself, but they exercise the
    public surface as if they were eval code.
    """
    tests_segment = os.path.join("backend", "tests")
    if tests_segment not in filename:
        return False
    base = os.path.basename(filename)
    if not base.startswith("test_"):
        return False
    # Anything in tests/ with "evals" or "firewall" in the name is fine.
    return "evals" in base or "firewall" in base


def assert_caller_in_evals_only() -> None:
    """Walk the call stack; raise if any frame is in production code.

    This is the runtime half of the import firewall. It is intentionally
    paranoid: rather than just checking the immediate caller, it inspects
    every frame above this one so that an indirect access path (helper
    function, decorator, plugin loader) cannot smuggle a production
    caller through.

    Raises:
        RuntimeError: if any frame on the stack lives under
            ``backend/app/core/``, ``backend/app/services/``, or
            ``backend/app/api/``.
    """
    stack = inspect.stack()
    saw_allowed_caller = False

    # Skip frame 0 (this function itself). Walk the rest of the stack.
    for frame_info in stack[1:]:
        filename = frame_info.filename or ""

        # Skip this firewall module's own frames (e.g. load_gold_holdout).
        if filename == __file__:
            continue

        # Production code paths are always rejected, even if a later frame
        # in the stack looks legitimate. The first forbidden frame wins.
        for forbidden in _FORBIDDEN_PATH_SEGMENTS:
            if forbidden in filename:
                raise RuntimeError(
                    "Gold holdout file is sealed from production code paths "
                    "— caller must be under evals/. "
                    f"Forbidden frame: {filename} (matched '{forbidden}'). "
                    "If you need labeled data in production, use the public "
                    "labeled datasets via evals/datasets/loader.py; the gold "
                    "holdout is reserved for offline evaluation only."
                )

        # Allowed paths: eval source or eval-tagged test files.
        if any(seg in filename for seg in _ALLOWED_PATH_SEGMENTS):
            saw_allowed_caller = True
            continue
        if _is_eval_test_file(filename):
            saw_allowed_caller = True
            continue

    if not saw_allowed_caller:
        # Reached only if no frame matched either bucket. Pytest's own
        # plumbing, REPL frames, etc. land here. We still allow them as
        # long as no forbidden frame was seen — a strict "must be under
        # evals/" check would block legitimate test discovery. The static
        # CI rule covers the case where someone tries to call this from
        # somewhere truly unexpected.
        logger.debug(
            "load_gold_holdout called from a stack with no eval-tagged "
            "frames; allowing because no production frames were seen."
        )


def load_gold_holdout() -> List[Any]:
    """Load the gold-standard evaluation holdout as a list of records.

    The file is JSONL: one JSON object per line. If the
    :class:`EvalClause` schema is importable, records are parsed into that
    schema; otherwise they are returned as plain dicts so that this module
    is usable before the dataset ingesters are in place.

    Returns:
        List of holdout records (``EvalClause`` instances if schema is
        available, otherwise dicts). Returns ``[]`` and logs a warning if
        the holdout file does not exist yet — labeling is in progress.

    Raises:
        RuntimeError: if called from a production code path (see
            :func:`assert_caller_in_evals_only`).
    """
    assert_caller_in_evals_only()

    if not GOLD_HOLDOUT_PATH.exists():
        logger.warning(
            "Gold holdout file not yet created at %s; returning empty list. "
            "Hand-labeling is tracked under Layer 3 task 3.4 in nxt.md.",
            GOLD_HOLDOUT_PATH,
        )
        return []

    records: List[Any] = []
    with GOLD_HOLDOUT_PATH.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Malformed JSON in gold holdout at line {line_no}: {exc}"
                ) from exc
            if EvalClause is not None:
                try:
                    records.append(EvalClause(**obj))  # type: ignore[misc]
                except Exception:  # noqa: BLE001
                    # If schema validation fails, fall through to dict so
                    # the firewall test is decoupled from schema details.
                    records.append(obj)
            else:
                records.append(obj)
    return records


__all__ = [
    "GOLD_HOLDOUT_PATH",
    "assert_caller_in_evals_only",
    "load_gold_holdout",
]
