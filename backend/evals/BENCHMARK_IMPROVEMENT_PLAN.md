# Benchmark Improvement Plan

A prioritized, concrete plan to make the evaluation of this ToS/Privacy risk
detector fairer, more credible, and (where benchmark scores are genuinely
depressed by detector behavior) better. This is an analysis deliverable — it
proposes changes and names the exact files/functions to touch, but does **not**
implement detector or prompt edits.

Grounded in a read of: `evals/datasets/loader.py`, `evals/metrics/kappa.py`,
`evals/metrics/severity.py`, `evals/baseline_runner.py`,
`evals/run_unfair_tos_benchmark.py`, `evals/run_gemini_agreement.py`,
`evals/datasets/ingest_unfair_tos.py`, `app/core/llm_clause_detector.py`,
`app/core/risk_patterns.py`, and `evals/unfair_tos_benchmark.json`.

---

## The single most important finding (read first)

The headline "severity Cohen's kappa +0.072 (slight)" is **not** primarily a
detector failure — it is partly a **label-construction artifact**, and the
metric itself is the wrong tool. Three independent facts converge:

1. **The benchmark's own HIGH labels are a coarse heuristic, not graded
   consumer-harm.** `ingest_unfair_tos.py` (`LABEL_MAPPING`, lines 69–78)
   assigns severity *by unfairness category, not by clause wording*: every
   `Limitation of liability` and `Arbitration` clause is hard-coded `high`; all
   six other unfairness types are hard-coded `medium`. So "gold-HIGH" literally
   means "this sentence is a liability or arbitration clause," regardless of how
   mild. The detector reading the actual text and calling a weak liability
   clause `medium` may be **more correct than the gold label**, not less.

2. **The metric collapses on a 2-class base rate.** In
   `unfair_tos_benchmark.json` the sample has only `high` (14) and `medium` (26)
   gold tiers and the detector also concentrates on `medium`. Unweighted Cohen's
   kappa (`metrics/kappa.py::cohens_kappa`) divides out chance agreement, which
   is huge when both raters pile on one class — hence +0.072 at 55% raw match.

3. **The off-by-one pattern is real but small-magnitude.** The confusion matrix
   shows gold-HIGH → high 3 / medium 10 / low 1. That is a genuine
   under-rating tendency, but it is mostly a **±1 tier** disagreement against a
   label that was itself assigned by category, not severity.

Conclusion: the plan must (A) replace/augment the metric, (B) disentangle
taxonomy mismatch from true miscalibration, and only then (C) consider detector
nudges. Reporting +0.072 as "our accuracy" is self-sabotage; it is mostly
measuring the wrong thing.

---

## A) Benchmark methodology improvements

### A1. Fairer severity metric — fix the kappa base-rate paradox  · effort: S
**Problem.** `metrics/kappa.py::cohens_kappa` is unweighted and treats a
HIGH→MEDIUM error identically to a HIGH→LOW error, then deflates to +0.072
because both distributions are medium-heavy. It is the headline number and it is
misleading.

**Concrete change.** Add to `evals/metrics/severity.py`:
- `quadratic_weighted_kappa(predictions, labels)` — ordinal QWK over the tier
  scale `low<medium<high<critical` (reuse the `_TIER` map already defined in
  `run_unfair_tos_benchmark.py:46`, hoist it into `severity.py` as the single
  source of truth). QWK is the standard metric for ordered categories and is the
  honest "severity agreement" number.
- `severity_mae(predictions, labels)` — mean absolute tier distance; intuitive
  ("off by 0.7 tiers on average").
- Keep raw exact-match and per-class F1 (already in
  `precision_recall_by_severity`).

Then in `baseline_runner.py::_build_report` add `severity_qwk` and
`severity_mae` alongside the existing `severity_kappa`, and update
`run_unfair_tos_benchmark.py::main` print block to surface QWK as the primary
severity figure with raw kappa shown as a secondary "(unweighted, base-rate
sensitive)" line. Update `ci_gate.py` to gate on QWK regression too, not only
unweighted kappa (which can move on pure base-rate shifts).

**Payoff.** A defensible single severity number that rewards being close. Likely
moves the reported severity figure from "slight (+0.07)" to a respectable
ordinal score on the *same* predictions — without touching the detector.

### A2. Add precision / false-positive measurement with FAIR negatives  · effort: M
**Problem.** UNFAIR-ToS as ingested is **positives-only**: `ingest_unfair_tos.py`
explicitly skips all-zero (fair) rows (lines 208–210, and the module docstring
says so). So `recall_flagged = 100%` is structurally guaranteed-ish and
**precision/FP rate on public data is entirely unmeasured.** A detector that
flags *everything* would also score 100% recall here. The `low`/`critical`
precision cells in the current report are 0/blank because the dataset has no
such labels — the P/R/F1 machinery exists but has nothing to bite on.

**Concrete change.**
- New ingester `evals/datasets/ingest_unfair_tos_negatives.py` (or add a
  `--include-fair` flag to the existing one): keep the all-zero "fair" sentences
  with `expected_severity = "none"`, `expected_risk_category = None`, written to
  `unfair_tos_mixed.jsonl`. Register `"unfair_tos_mixed"` in
  `loader.py::_VALID_NAMES` and the `load_dataset` dispatch.
- Add `false_positive_rate(predictions, labels)` to `severity.py`: of the
  gold-`none` clauses, fraction the detector flagged. This is the
  precision-first detector's most important and currently-missing number.
- The detector returns *nothing* for non-risky clauses; the alignment in
  `baseline_runner.py::_align_predictions` already maps a missing finding to
  `severity=None`, so gold-`none` + pred-`None` = true negative works with no
  detector change.

**Payoff.** The first honest precision/FP number on a public, licensed set.
Converts "100% recall" (vacuous) into "X% recall at Y% FP rate" (credible). This
is the single biggest credibility gap in the current eval.

### A3. Disentangle taxonomy mismatch from genuine miscalibration  · effort: M
**Problem.** LexGLUE "unfairness" ≠ this tool's "consumer-harm severity," and
(per the top finding) the HIGH/MEDIUM split in `LABEL_MAPPING` is assigned by
category, not by reading the clause. Some of the HIGH→MEDIUM "errors" are the
detector being *right* about a mild liability clause.

**Concrete change.**
- Treat LexGLUE severity as **weak/heuristic** and report category metrics as
  the primary LexGLUE result (category recall 75%, category kappa +0.697 is
  already substantial and is the metric LexGLUE labels actually support well).
  Demote LexGLUE *severity* numbers to "calibration signal, weak labels."
- Build a small **adjudicated severity subset**: sample ~40 of the HIGH→MEDIUM
  disagreement clauses (the `run_unfair_tos_benchmark.py` confusion already
  isolates them; emit them to a JSONL like `gemini_disagreements.jsonl` does)
  and hand-grade them against *this tool's* rubric. Store as a sealed slice or
  fold into `gold_holdout.jsonl`. Re-measuring severity on hand-graded labels
  is the only way to separate "miscalibrated" from "label taxonomy differs."
- For the cross-family check, the Gemini harness
  (`run_gemini_agreement.py`) already grades on *this* rubric via
  `gemini_judge.py`, so its severity kappa (+0.419 moderate) is a *cleaner*
  severity signal than LexGLUE's and should be reported as such.

**Payoff.** Stops attributing definitional disagreement to detector error.
Likely reveals the true miscalibration is smaller than the +0.072 implies.

### A4. Larger N + confidence intervals  · effort: S
**Problem.** N=30–40 with point estimates only; the per-class kappa swings
(critical=1.0 on zero support, high=0.16) are noise-dominated.

**Concrete change.**
- Raise default N: `run_unfair_tos_benchmark.py` already chunks sequentially to
  beat the timeout — bump `--n` to 150–300 for the reported run. (Cost is the
  constraint, not architecture.)
- Add `evals/metrics/bootstrap.py::bootstrap_ci(metric_fn, predictions, labels,
  n_resamples=2000, alpha=0.05)` — resample clause indices with replacement,
  recompute the metric, return `(point, lo, hi)`. Wrap QWK, MAE, recall, and FP
  rate. Surface `[lo, hi]` in the report JSON and the printed summary.
- Suppress or flag zero-support cells (critical/low) instead of printing
  `kappa=1.0` / `f1=0.0`, which currently look like real results in
  `unfair_tos_benchmark.json`.

**Payoff.** Every headline number gets an honest ± band; removes the "1.0 on
zero support" foot-guns from the artifact.

### A5. Document-level evaluation (task-match)  · effort: L
**Problem.** The detector is tuned for **whole-document checklist matching**
(`risk_patterns.py`, the checklist prompt at `llm_clause_detector.py:253+`), but
both benchmarks feed **isolated single clauses**. `baseline_runner.py::_detect`
sends each EvalClause as its own `clause_number` with `service_type="general"`,
so the checklist prompt runs without document context — a real task mismatch
that *handicaps* the detector (no cross-clause context, e.g. an arbitration
clause whose opt-out lives in another section).

**Concrete change.**
- Assemble a handful of **full documents** with per-clause gold labels (the
  TikTok doc referenced in MEMORY is an obvious seed; LexGLUE rows carry a
  source doc id that could be regrouped). Add a `load_documents()` path and a
  `run_document_benchmark.py` that feeds whole docs through
  `anomaly_detector.py` (the real orchestrator incl. `_dedupe_findings`), then
  aligns findings back to clauses by `clause_number`.
- Report document-level **set metrics**: did we surface each gold-risky clause
  anywhere in the alert budget (recall after `alert_ranker.py` bucketing), and
  how many spurious alerts (precision). This matches the product's actual
  contract better than isolated-clause grading.

**Payoff.** Measures the system as shipped (parsing → detect → rank), not just
the detector in an unnatural single-clause mode. Strongest portfolio story
("evaluated end-to-end at the document level"), but highest effort.

### A6. Leakage / rigor concerns  · effort: S
- **Fixed-seed subsample drift.** `loader.py::load_dataset` subsamples with
  `random.Random(42)` over the *current file contents*; if a JSONL is
  regenerated, "N=40, seed=42" silently selects different rows. Record the
  selected `clause_id`s in the report JSON so a run is reproducible/auditable.
- **Gold-holdout firewall holds, but watch auto-promotion.**
  `datasets/auto_promote_high.py` / `auto_promote_critical.py` move detector
  outputs into the labeling queue — ensure promoted-from-detector rows are
  re-adjudicated by a human before they enter `gold_holdout.jsonl`, or the
  baseline starts grading the detector against its own past predictions
  (circularity). Add a provenance field check to `regrade_gold_holdout.py`.
- **Gemini self-consistency confound.** The production detector runs with
  `SELF_CONSISTENCY_CRITICAL` on (vote-only-demotes). When comparing to Gemini,
  hold the flag fixed and record its state in the report so agreement deltas
  aren't conflated with flag flips.

---

## B) Detector improvements that would raise benchmark scores

> Do **not** implement these here — they are testable hypotheses. Each should be
> A/B'd against the QWK / FP metrics from section A before adoption.

### B1. The HIGH under-rating: catalog default-severity skew  · effort: S to test
**Evidence.** `risk_patterns.py` defaults: 3 critical / 17 high / 18 medium / 3
low. The checklist prompt (`llm_clause_detector.py:255–257`,
"SEVERITY HANDLING ... USE THE CATALOG'S DEFAULT unless the SPECIFIC wording
... warrants a different tier") anchors hard on catalog defaults. Confusion shows
gold-HIGH (liability + arbitration in LexGLUE terms) → predicted medium 10×.
LexGLUE's "high" categories are exactly `Limitation of liability` (cat
`liability`) and `Arbitration`. Cross-reference: several liability/arbitration
patterns in the catalog carry `medium` defaults (e.g. lines 219–227, 303–323
region). So when the doc matches a *medium-default* liability/arbitration
pattern, the detector emits medium — and the (heuristic) gold says high.

**Concrete, testable change.** Audit the `liability`- and `arbitration`-category
patterns in `risk_patterns.py`; for those whose wording is genuinely severe (full
liability waiver, forced arbitration + class waiver with no opt-out), confirm the
default is `high`/`critical`. *But only after A3* — because the gold "high" is a
weak label, raising defaults to chase it could hurt the hand-graded subset and
the Gemini agreement. This is why B1 is gated behind the adjudicated subset.

### B2. The vote-only-demotes asymmetry  · effort: S to test
**Evidence.** `_run_critical_self_consistency` / `_majority_vote_critical`
(`llm_clause_detector.py:516+`) only re-vote `severity=='critical'` and the
comment at 522–523 says the vote can only **demote**. MEMORY also records the
calibration-suppressor that lived in vote prompts. Net effect: the system has a
structural downward pressure on severity and no upward correction path. A clause
the first pass under-calls as `high` (when it is critical) is never promoted.

**Concrete, testable change.** Consider a symmetric vote (allow promote *and*
demote) on `high` findings too, or at minimum measure how often the vote moves
mass downward on the benchmark. Test against QWK + FP — promotion risks raising
the FP/over-rating rate, so this must be measured, not assumed.

### B3. Single-clause context starvation  · effort: M to test
**Evidence.** Section A5: isolated-clause grading strips document context the
checklist prompt expects. This *depresses* benchmark scores without any detector
defect. Confirm by comparing isolated-clause vs document-level recall on the same
clauses (A5 infra). If document-level scores are materially higher, the
"miscalibration" is partly an evaluation artifact and the headline should cite
the document-level number.

---

## C) What to report for a portfolio (honest headline metrics)

**Lead with these (credible, defensible):**
1. **Category accuracy on a public benchmark (LexGLUE UNFAIR-ToS):** category
   recall **75%**, category Cohen's kappa **+0.697 (substantial)**. This is the
   metric the public labels actually support, and it is genuinely strong.
2. **Cross-family agreement vs an independent model (Gemini 2.5 Flash), same
   rubric, aligned flag-or-decline task:** severity **66.7% / kappa +0.419
   (moderate)**, category **70% / kappa +0.531**, joint **60%**. Frame as "two
   model families from different vendors agree at a moderate level on a hard,
   subjective task" — this is the strongest single signal that the tool isn't
   just memorizing one model's quirks.
3. **(After A2) Recall at a measured false-positive rate** on the mixed
   fair/unfair set — the precision-first claim made quantitative.
4. **(After A1) Ordinal severity QWK / MAE** instead of unweighted kappa.

**Reframe or retire these (currently misleading):**
- ❌ "Severity Cohen's kappa +0.072 (slight)" as a headline. It is base-rate
  collapse against weak category-derived labels. Report it only with the
  caveat + QWK alongside, or drop it for LexGLUE severity entirely.
- ❌ "Recall 100% (40/40)" as an accuracy claim. On an all-positives set this is
  near-vacuous; always pair with the FP rate (A2) or it reads as cherry-picked.
- ⚠️ Per-class cells with zero support (critical kappa=1.0, low f1=0.0 in
  `unfair_tos_benchmark.json`) — suppress; they look like results but are noise.
- ⚠️ Always state N and show CIs (A4). "N=40, point estimate" is not portfolio-
  grade for a subjective grading task.

**Meta-point worth surfacing in the portfolio writeup:** the most impressive
thing here is not any single score — it's that the eval harness *diagnosed its
own measurement bug* (the kappa paradox + weak labels) and corrected the
methodology. That narrative (measurement rigor) is more valuable to a hiring
manager than a high number.

---

## Top 3 highest-leverage actions

1. **A2 — Add fair negatives + a false-positive rate.** Until precision is
   measured on public data, the headline "100% recall" is unfalsifiable and the
   whole eval understates its own credibility. Highest payoff, medium effort.
2. **A1 — Replace the unweighted-kappa headline with quadratic-weighted kappa +
   MAE.** Fixes the misleading +0.072 with zero detector changes; one S-effort
   metric function. Do this before quoting any severity number anywhere.
3. **A3 — Build a small hand-adjudicated severity subset (this tool's rubric).**
   It's the only way to know whether the HIGH under-rating is real
   miscalibration (then do B1/B2) or a LexGLUE taxonomy artifact — and it
   unblocks honest reporting of every severity claim.
