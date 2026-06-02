# Terms & Conditions Risk Analyzer — detection overhaul, eval harness, and benchmarks

Rebuilds the detection engine around a measured insight, deletes the legacy
multi-stage pipeline, and adds an evaluation harness rigorous enough to catch
(and correct) its own measurement bugs.

> Large PR: it folds the LLM migration, the simple-engineering refactor, the
> detection-quality fixes, and the evaluation/benchmark work into the current
> state of `feat/llm-detection-and-bug-fixes`.

## Architecture: detection = 2 LLM passes + 1 ranker

The old 6-stage pipeline was measured against a benchmark, shown to be
net-subtractive, and **deleted** (~17K LOC removed; `anomaly_detector.py` went
2,506 → 215 LOC). Detection is now three transparent steps:

1. **Risky-clause detection** — *checklist mode*: match the document against ~41
   curated patterns (`app/core/risk_patterns.py`). The key lesson: open-ended
   "find risky clauses" missed 5/6 critical clauses on a real ToS; reframing it
   as "is each of these N patterns present?" 8×'d HIGH-severity recall. **LLMs
   are reliable matchers, unreliable exhaustive searchers.**
2. **Missing-protection detection** (`app/core/expected_protections.py`) — flags
   absent consumer protections behind a relevance gate + a deterministic
   presence guard.
3. **Ranking** (`app/core/alert_ranker.py`) — recall-first budget; HIGH/MEDIUM
   findings are never silently dropped.

## Detection-quality fixes (this branch)

- **Recall root cause — clause-size cap.** Real ToS arrive as one unbroken
  ~8,000-word line; the structure extractor collapsed the whole document into a
  single clause, so the checklist had to exhaustively scan a wall of text and
  missed buried clauses. `MAX_CLAUSE_WORDS=200` sentence-splits oversized clauses
  (Apple ToS: 1 → 49 clauses), recovering law-enforcement, sole-remedy, and
  perpetual-license findings.
- **Same-clause deduplication.** Several catalog patterns matching one clause
  produced duplicate alerts; a second dedup pass collapses by clause location,
  keeping the highest severity.
- **Missing-protection inversion guard.** The missing-check flagged protections
  the document plainly grants (e.g. "30 days before changes"); a deterministic
  presence guard suppresses these false positives.
- **Severity calibration.** Behavioral advertising capped at MEDIUM (disclosed
  first-party ad targeting ≠ data sale, which stays critical); removed residual
  prevalence-based suppressors from the self-consistency vote prompts.
- **Anti-hallucination** evidence requirement added to the detection prompts.
- **Bug fixes:** invalid dotted Claude model IDs (`claude-sonnet-4.5-…` → 404);
  detector batch timeouts; integration-test auth fixtures (stale `/register`
  path; graceful skip when no live DB).

## Evaluation harness

- **Sealed gold holdout** — 149 hand-labeled clauses behind an import firewall +
  CI grep gate (production code physically cannot read it).
- **Public benchmark — UNFAIR-ToS (LexGLUE).** Mixed fair/unfair set (N=180, 95%
  bootstrap CIs): **84.1% recall [74.6–92.5] at a 4.3% false-positive rate
  [0.9–8.3]**; category recall 54%. Honest caveat (documented in
  `backend/evals/BENCHMARK.md`): this set's gold *severity* is a category proxy,
  so severity is not meaningfully measurable on it.
- **Cross-family agreement vs Gemini 2.5 Flash** — independent model, same
  rubric, aligned flag-or-decline task: severity κ **+0.419 (moderate)**,
  category κ +0.531, joint 60% (N=30). Auto-generated
  `backend/evals/COMPARATIVE_REPORT.md`.
- **Fair metrics:** quadratic-weighted kappa + MAE (the unweighted-kappa
  base-rate paradox is documented and retired as a headline); `false_positive_rate`
  on fair negatives; percentile bootstrap CIs; CI gate halts on κ / QWK drift.

**The rigor is the point:** the harness diagnosed its own measurement bugs (the
kappa paradox and category-proxy labels) and corrected the methodology rather
than quoting flattering-but-vacuous numbers.

## Test plan

- [x] Backend unit + integration suite green (integration skips cleanly without a
  live DB).
- [x] 95 eval-harness tests pass (`pytest backend/evals/tests -q`).
- [x] Gold-holdout firewall grep gate passes (no `gold_holdout` refs in `app/`).
- [x] Frontend (Vite) builds clean.
- [x] Benchmark + agreement runs executed against real APIs — numbers above are
  real, not synthetic; runs are skip-safe when keys are absent.

## Known follow-ups (not blocking; tracked in `backend/evals/BENCHMARK_IMPROVEMENT_PLAN.md`)

- **A3** — hand-adjudicated severity subset (separates real miscalibration from
  the LexGLUE taxonomy artifact; unblocks detector severity tuning).
- **A5** — document-level (end-to-end) evaluation through the real orchestrator.

## Security note

Rotate the Anthropic API key before/after merge — a key was exposed during
development. `app/core/config.py` previously hardcoded broken Claude model IDs as
defaults; grep deployed envs for `claude-*4.5-*` dotted IDs after merge.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
