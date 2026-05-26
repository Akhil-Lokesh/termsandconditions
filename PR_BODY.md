## Summary

Closes out the 5-layer upgrade plan documented in `nxt.md`:

- **Layer 1** — eliminated ~2,555 LOC of dead code (13 unused files + 4 unused methods in `anomaly_detector.py`)
- **Layer 2** — wired up feedback persistence (`FeedbackEvent` model + Alembic migration + write-through), DocumentTypeDetector → LLMClauseDetector routing, privacy-policy prompt variant
- **Layer 3** — ingested UNFAIR-ToS (1,032 sentences) + OPP-115 (3,792 clauses); hand-labeled 149-clause gold holdout sealed behind import firewall + static grep gate; license attribution README
- **Layer 4** — Claude Opus 4.7 judge + GPT-4o cross-checker (15% sample); Cohen's kappa metrics; SQLite verdict cache; CI regression gate that halts deploys on kappa drift > 0.03
- **Layer 5** — 3-call self-consistency vote on critical findings (behind feature flag); per-doc cost cap (`MAX_LLM_USD_PER_DOC`); ablation harness; frontend feedback UI; 189-line operational runbook

**Bonus (Layer 4-adjacent):** Cross-family Gemini Flash agreement harness — REST-based, no SDK dependency, free-tier safe (~9 RPM pacing), skip-safe when keys are missing, never-invents-numbers report generator.

**Bug fix:** `app/core/config.py` had invalid Claude model IDs (`claude-sonnet-4.5-20250514` with dot syntax that the Anthropic API rejects). Production detector was silently 404'ing for anyone who didn't override `CLAUDE_MODEL` in `.env`.

## Eval evidence

Cross-family inter-annotator agreement (Claude production detector vs Gemini 2.5 Flash, N=30, free tier):

| Metric | Value |
| --- | --- |
| Severity exact-match agreement | **60.0%** |
| Risk-category exact-match agreement | **63.3%** |
| Joint (severity + category) agreement | **36.7%** |
| Severity Cohen's kappa | **+0.381** (_fair_, Landis-Koch) |
| Category Cohen's kappa | **+0.495** |
| Disagreements logged | **12** (see `backend/evals/gemini_disagreements.jsonl`) |
| Gemini requests issued | **7** (0 rate-limited) |

Full report at `backend/evals/COMPARATIVE_REPORT.md` (auto-generated, regenerates on each agreement run).

## Test plan

- [x] `pytest backend/tests/test_llm_clause_detector.py backend/evals/tests/test_metrics.py backend/evals/tests/test_kappa.py backend/evals/tests/test_judges.py backend/evals/tests/test_ci_gate.py backend/tests/test_firewall.py backend/evals/tests/test_gemini_judge.py backend/evals/tests/test_gemini_agreement.py backend/evals/tests/test_comparative_report.py --noconftest -q` → **119 passed, 1 skipped**
- [x] `bash backend/scripts/check_holdout_firewall.sh` → static grep gate passes (no `gold_holdout` references in `app/`)
- [x] Gemini agreement run executed against real APIs (Claude Sonnet 4.5 + Gemini 2.5 Flash) — numbers above are real, not synthetic
- [x] Skip-safe: `python -m evals.run_gemini_agreement` without `GEMINI_API_KEY` → exits 0 cleanly, no artifact written
- [x] No OpenAI/GPT references in any new Gemini-related file (verified via grep)
- [ ] **CI eval-gate workflow** — first PR run will establish the actual CI behavior on this branch

## Known follow-ups (not blocking this PR)

- `backend/evals/baseline.json` — the Cohen's kappa baseline against the gold holdout. Requires a paid Claude + OpenAI judge run (~$2.50). Once generated, the CI regression gate becomes meaningfully comparative.
- `backend/evals/vote_ablation_report.json` — required before flipping `SELF_CONSISTENCY_CRITICAL=true` in production. Requires ~$5 in Claude API budget. Decision criterion: kappa lift > 0.02.
- Gold holdout distribution: currently C:10 H:9 M:70 L:60 (target was 20/40/50/30). Each tier has ≥9 samples so per-tier kappa is computable; expanding criticals to 20 is a 15-minute follow-up via `python -m evals.datasets.regrade_gold_holdout`.

## Security note

`app/core/config.py` previously hardcoded broken Claude model IDs as defaults. Anyone who deployed without setting `CLAUDE_MODEL` in `.env` had a non-functional production detector. This PR fixes that — but worth grepping any deployed envs for the bad IDs after merge.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
