#!/usr/bin/env bash
# Fail if any file under backend/app/ references the gold holdout file.
#
# This is the STATIC half of the holdout firewall (the runtime half lives
# in backend/evals/datasets/firewall.py). It greps the production source
# tree for literal references to "gold_holdout" so a leak shows up at CI
# time even if the offender never actually executes the read.
#
# Intended to run from the repo root or from backend/. Both work because
# we anchor the path to "backend/app/" relative to the working directory.
set -euo pipefail

# Locate the search root: prefer ./backend/app, fall back to ./app for
# callers who cd into backend/ first.
if [ -d "backend/app" ]; then
    SEARCH_ROOT="backend/app"
elif [ -d "app" ]; then
    SEARCH_ROOT="app"
else
    echo "ERROR: could not locate backend/app/ from $(pwd)" >&2
    exit 2
fi

# grep -l prints filenames; -r recurses; -n is unnecessary here. We
# exclude __pycache__ via --exclude-dir so byte-compiled traces don't
# false-positive the rule.
if grep -rln \
        --exclude-dir=__pycache__ \
        --exclude-dir=".venv" \
        --exclude-dir="venv" \
        "gold_holdout" \
        "${SEARCH_ROOT}" 2>/dev/null
then
    echo "ERROR: ${SEARCH_ROOT}/ files reference gold_holdout — this leaks test set into production" >&2
    echo "Move the offending code under backend/evals/ or use the public loader in evals/datasets/loader.py." >&2
    exit 1
fi

echo "OK: no holdout references in ${SEARCH_ROOT}/"
