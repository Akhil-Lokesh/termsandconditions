# T&C Anomaly Detection — Operational Runbook

## 1. Overview

This runbook covers on-call operations for the T&C anomaly detection
eval pipeline: how to inspect the active-learning feedback loop, run the
LLM-as-judge evaluation suite, manage feature flags, and triage common
incidents. The pipeline runs Claude-based clause detection followed by
context filtering, clustering, compound-risk synthesis, confidence
calibration, and alert ranking (6 stages). Evals run Claude Opus 4.7
as the primary judge with GPT-4o cross-checking 15% of decisions for
family-bias detection. The Cohen's kappa baseline is the deploy gate.

---

## 2. Daily / weekly tasks

**Inspect feedback persistence** (daily, takes ~5s):

```bash
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM feedback_events WHERE processed_at IS NULL;"
psql "$DATABASE_URL" -c "SELECT user_action, COUNT(*) FROM feedback_events \
    WHERE created_at > NOW() - INTERVAL '7 days' GROUP BY user_action;"
```

A growing `processed_at IS NULL` backlog (>500 rows) means the calibrator
isn't draining the buffer — check the ALM hydration log on startup.

**Manually trigger calibrator retraining** (when buffer is full or feedback
distribution shifts):

```bash
python -c "from app.core.active_learning_manager import ActiveLearningManager; \
    alm = ActiveLearningManager(); alm.retrain_calibrator(force=True)"
```

**Review judge disagreements** (weekly, ~10 min): open
`backend/evals/judge_disagreements.jsonl` and scan for patterns. If
GPT-4o and Claude disagree on >20% of a single severity tier or
risk_category, the prompt may have drifted.

```bash
jq -s 'group_by(.severity) | map({severity: .[0].severity, n: length})' \
    backend/evals/judge_disagreements.jsonl
```

---

## 3. Running the eval pipeline

Typical local workflow:

```bash
# 1. Dataset sanity check — verify all sources load with expected counts.
python -m evals.cli stats --dataset all

# 2. Run baseline (200 samples is the standard size for kappa).
#    Cost: ~$1.50–$2.50 with Opus 4.7 judge at 200 samples,
#          +$0.30 for GPT-4o cross-check on 15% sample.
ANTHROPIC_API_KEY=sk-ant-... \
OPENAI_API_KEY=sk-... \
    python -m evals.baseline_runner \
        --dataset all \
        --n 200 \
        --out evals/baseline.json

# 3. Run the current detector and compare against the baseline.
python -m evals.runner --out results.json
python -m evals.cli ci-check \
    --current results.json \
    --baseline evals/baseline.json
```

**Cost estimate per full run (200 samples):**

| Component                       | Approx cost |
| ------------------------------- | ----------- |
| Detector (Claude batch)         | $0.40       |
| Claude judge (Opus 4.7)         | $1.80       |
| GPT-4o cross-checker (15%)      | $0.30       |
| **Total**                       | **~$2.50**  |

CI runs the same with `--n 100` (~$1.25/run) on every PR touching
`app/core/llm_clause_detector.py` or `evals/`.

---

## 4. Feature flags reference

| Flag                          | Default | Effect |
| ----------------------------- | ------- | ------ |
| `ACTIVE_LEARNING_PERSIST`     | `false` | When `true`, `FeedbackEvent` rows are written through to the DB and hydrated into the ALM buffer on startup. When `false`, feedback stays in-memory and dies with the process. |
| `DOC_TYPE_DETECTION`          | `true`  | When `true`, `DocumentTypeDetector` classifies each upload as `terms_of_service` / `privacy_policy` / `other` and routes to the correct system prompt. Threshold for swapping the prompt is `confidence >= 0.7`; below that it falls back to the default T&C prompt and logs the low-confidence event. |
| `PRIVACY_PROMPT_VARIANT`      | `true`  | When `true` (and doc-type detection picks `privacy_policy` with confidence ≥ 0.7), the privacy-specific system prompt is used in `LLMClauseDetector._select_system_prompt()`. |
| `SELF_CONSISTENCY_CRITICAL`   | `false` | When `true`, every `severity=critical` finding gets a 3-call majority vote with a hard cap of 5 voted findings per document. Flip on only after the ablation report shows kappa lift > 0.02. |
| `MAX_LLM_USD_PER_DOC`         | `0.50`  | Per-document Claude cost ceiling. Pipeline aborts further LLM calls and falls back to keyword-only paths once a document crosses this budget. 80% triggers a warning log. |
| `HF_HUB_OFFLINE`              | (unset) | Local-dev macOS: set to `1` to prevent `sentence_transformers` from probing huggingface.co on startup (causes multi-minute hangs on flaky networks). |
| `HF_HUB_DISABLE_TELEMETRY`    | (unset) | Set to `1` to silence the HF telemetry ping that fires on first model load. |

All flags are read from environment variables in
`backend/app/core/config.py`. Default-off flags must stay off in production
until they ship with monitoring evidence (this is the cardinal rule of the
upgrade plan — see `nxt.md`).

---

## 5. Common incidents + remediation

**Incident: Cohen's kappa dropped suddenly (CI gate failing)**

Checklist, in order:
1. Did the dataset change? `git log -- evals/datasets/` — any new ingester runs?
2. Did the detector prompt change? `git log -- backend/app/core/llm_clause_detector.py`
3. Did the Claude model change? Check `app/services/claude_service.py` for model ID.
4. Run the ablation: `python -m evals.experiments.vote_ablation` — compare with/without `SELF_CONSISTENCY_CRITICAL`.
5. If none of the above, run with `--n 500` to rule out small-sample noise (kappa has ~±0.04 jitter at n=200).

**Incident: Cost spiked (per-doc spend > $0.50)**

1. Check the latest `vote_ablation_report.json` — did vote rate explode on a specific document type?
2. Was `SELF_CONSISTENCY_CRITICAL` flipped on? Roll it back if not gated by ablation evidence.
3. Look for documents producing >5 critical findings (the vote cap should catch this — log a warning if hit).
4. Confirm `MAX_LLM_USD_PER_DOC` is loaded: `python -c "from app.core.config import settings; print(settings.MAX_LLM_USD_PER_DOC)"`

**Incident: Feedback not persisting (user feedback disappears on restart)**

1. Check the env var: `printenv ACTIVE_LEARNING_PERSIST` — must be `true`.
2. Check the table exists: `psql "$DATABASE_URL" -c "\d feedback_events"`.
3. On startup, look for the ALM hydration log line: `ActiveLearningManager: hydrated N events from DB`. If `N=0` when you expect events, check `processed_at IS NOT NULL` filter logic.
4. Verify the alembic migration ran: `alembic current` should show `d2a4b5...` or later.

**Incident: DocumentTypeDetector misroutes (privacy doc routed to T&C prompt or vice versa)**

1. Tail the upload background task log; look for `document_type_confidence=` log line.
2. If `confidence < 0.7`, the system *correctly* falls back to the T&C prompt — this is by design.
3. If `confidence >= 0.7` but the wrong type was picked, add the document to `evals/fixtures/doctype_misroutes.jsonl` and re-train / re-prompt the detector.
4. Force-route via document context override (single-doc workaround):
   ```python
   document_context['document_type_override'] = 'privacy_policy'
   ```

**Incident: App stuck on startup**

Almost always `sentence_transformers` hanging on huggingface.co probe.

```bash
export HF_HUB_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1
```

Add both to your `.env`. If still hanging, run `python -c "import sentence_transformers"` to confirm — clean output = problem is elsewhere.

---

## 6. Critical files quick reference

| File | Purpose |
| ---- | ------- |
| `app/core/llm_clause_detector.py` | Primary detector — Claude batch call, prompt selection, majority-vote logic for critical findings |
| `app/core/active_learning_manager.py` | Feedback buffer + DB write-through + calibrator retraining + startup hydration |
| `app/core/document_type_detector.py` | Type detection (terms_of_service / privacy_policy / other); called from `document_pipeline.py` |
| `app/core/anomaly_detector.py` | 6-stage pipeline orchestrator |
| `evals/runner.py` | Single-run eval driver |
| `evals/cli.py` | `stats`, `ci-check`, `compare` sub-commands |
| `evals/baseline_runner.py` | Generates `baseline.json` |
| `evals/judge/claude_judge.py` | Primary Opus 4.7 judge |
| `evals/judge/openai_judge.py` | GPT-4o cross-checker; **must NOT import `app/services/claude_service.py`** (import-linter rule) |
| `evals/datasets/firewall.py` | Blocks `app/core/**` from reading the gold holdout |
| `evals/metrics/kappa.py` | Cohen's kappa + agreement metrics |
| `app/models/feedback_event.py` | `FeedbackEvent` SQLAlchemy model |

---

## 7. Escalation thresholds

**Halt deploy** if any of these are true:
- Cohen's kappa drops > 0.03 vs `evals/baseline.json` on a 200-sample run
- Per-doc cost p95 > $0.75 (50% over the soft cap)
- Critical-severity false-positive rate > 25% on the gold holdout
- Any test in `tests/test_feedback_persistence.py` or `tests/test_doc_type_routing.py` fails

**Proceed with caution** (flag for follow-up, but ship):
- Cohen's kappa drops 0.01–0.03 — investigate within 48 hours
- Per-doc cost p95 between $0.50 and $0.75 — file a tracking ticket
- GPT-4o disagrees with Claude on > 20% of a single category — review prompt
- Feedback buffer size > 80% capacity without auto-retrain firing — bump retrain cadence

**Escalation path**: kappa drop > 0.05 or any production-affecting incident →
ping the on-call channel and link the failing eval run + `vote_ablation_report.json`.
