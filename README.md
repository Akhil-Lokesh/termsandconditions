# Terms & Conditions Risk Analyzer

Upload a Terms of Service or Privacy Policy and get back the clauses that
actually disadvantage you — each with a severity, a risk category, and a
plain-English explanation — plus the consumer protections the document is
*missing*.

The interesting part of this project isn't the app; it's the **detection
engineering and the evaluation harness that measures it**. Most "AI reads your
ToS" demos are a single open-ended prompt. This one is built around a measured
insight about where LLMs are reliable and where they aren't.

---

## The core insight: checklist beats open-ended

The first version asked the model an open-ended question — *"find the risky
clauses in this document."* On a real TikTok ToS it surfaced **1** HIGH-severity
clause and missed 5 of the 6 known-critical ones.

The fix was to reframe detection as **matching, not searching**. Instead of one
open-ended ask, the detector runs a *checklist*: "for each of these N curated
risk patterns, is it present in this document?" Same model, same document — but
recall on HIGH-severity clauses went from **1 → 8**.

> LLMs are reliable **matchers** and unreliable **exhaustive searchers.**

That single principle drives the whole architecture: a curated catalog of
patterns, a checklist pass, a separate pass for *missing* protections, and an
evaluation harness that keeps the system honest run-over-run.

A second corollary showed up repeatedly: **severity must track consumer *harm*,
not industry *prevalence*.** A "calibration rule" that quietly downgraded
common-but-severe clauses ("if >50% of major ToS do this, cap it at medium")
was the root cause of systematic under-flagging — and it hid in secondary
voting prompts long after it was removed from the main rubric.

---

## How detection works

Three stages, each deliberately simple and inspectable:

1. **Risky-clause detection** (`llm_clause_detector.py`, checklist mode) —
   matches the document against ~41 curated patterns in `risk_patterns.py`
   (perpetual content licenses, forced arbitration + class waivers,
   termination-on-suspicion, cascading family payments, …). Optional
   self-consistency voting (3 independent severity votes) stabilizes
   borderline calls.
2. **Missing-protection detection** (`expected_protections.py`) — flags
   protections a fair agreement *should* contain but doesn't (breach
   notification, advance-notice of changes, termination appeals, …), behind a
   **relevance gate** so it doesn't flag arbitration-opt-out on a document that
   has no arbitration in the first place.
3. **Ranking & bucketing** (`alert_ranker.py`) — scores findings, buckets into
   high / medium / low, and applies a recall-first alert budget (HIGH/MEDIUM
   are never silently dropped).

Before any of that, a **document pipeline** turns a raw upload into clauses:
text extraction → structure extraction → clause segmentation. Real-world ToS
are messy (one notorious document arrives as a single unbroken 8,000-word line),
so clause segmentation enforces a maximum clause size — the matcher only ever
sees digestible passages, never a wall of text.

---

## Evaluation harness

This is the part built for rigor, and the part worth reading the code for
(`backend/evals/`):

- **Sealed gold holdout** — 149 hand-labeled clauses behind an *import
  firewall* (production code physically cannot read the holdout) plus a CI grep
  gate, so quality numbers can't be gamed by leakage.
- **Cohen's κ regression gate** — CI fails the build if severity agreement
  drifts more than 0.03 against the last green baseline.
- **Cross-family agreement study** — the production Claude detector vs. an
  independent Gemini Flash rater (REST, temperature 0, no SDK dependency,
  free-tier rate-limit aware). On an N=30 sample: severity Cohen's
  κ = **+0.381** (fair), 60.0% severity exact-match, 63.3% category exact-match.
  Disagreements are logged for prompt-drift analysis.
- **Ablation studies** — e.g. self-consistency voting was kept because it
  delivered a **+0.06 κ** lift at **$0** cost delta, not on a hunch.

Every number above is produced by a script and regenerated from a JSON run
artifact — nothing in the reports is hand-typed. See
[`backend/evals/README.md`](backend/evals/README.md) and
[`backend/evals/COMPARATIVE_REPORT.md`](backend/evals/COMPARATIVE_REPORT.md).

---

## Tech stack

**Backend** — FastAPI · SQLAlchemy 2.0 · Pydantic v2 · PostgreSQL (Supabase) ·
Pinecone · Anthropic Claude API · pytest

**Frontend** — React + Vite · TanStack Query · React Hook Form · Radix UI ·
Tailwind CSS

---

## Getting started

### Prerequisites
- Python 3.9+ and Node 18+
- An Anthropic API key (required for detection)
- A PostgreSQL database (Supabase works out of the box)

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then fill in ANTHROPIC_API_KEY, DATABASE_URL, etc.

uvicorn app.main:app --reload --port 8000
# API docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

---

## Testing

```bash
cd backend
python -m pytest tests/                  # unit + integration
python -m pytest backend/evals/tests/    # eval metric unit tests (no API calls)
```

Integration tests that require a live database + auth skip cleanly when those
preconditions aren't available, so the suite runs green offline.

---

## Project structure

```
backend/
  app/
    api/v1/          # FastAPI routes (upload, anomalies, auth)
    core/            # detection + document pipeline (see below)
    services/        # Claude, embeddings, Pinecone, cache
  evals/             # evaluation harness, gold holdout, reports
  tests/             # unit + integration tests
frontend/
  src/               # React app (upload, results, dashboard)
data/
  baseline_corpus/   # reference ToS documents
```

Detection lives in `backend/app/core/`:
`llm_clause_detector.py` · `risk_patterns.py` · `expected_protections.py` ·
`alert_ranker.py` · `anomaly_detector.py` (orchestrator) ·
`structure_extractor.py` (clause segmentation).

---

## Design notes

A few decisions that are easy to miss from the code alone:

- **Deletion over abstraction.** An earlier 6-stage pipeline was measured
  against a benchmark, shown to be net-subtractive, and removed —
  `anomaly_detector.py` went from ~2,500 LOC to ~215.
- **Inverted-logic protections are excluded.** "Absence is good" protections
  (e.g. *moral rights preserved*) don't fit a present/absent model and were
  dropped after they fired as false positives on nearly every document.
- **Recall-first ranking.** Suppressed alerts aren't surfaced downstream, so
  the ranker never trims HIGH/MEDIUM findings — only LOW, and only over budget.
