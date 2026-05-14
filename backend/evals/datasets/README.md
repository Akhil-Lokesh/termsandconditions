# `evals/datasets/` — Labeled corpora for anomaly-detection evaluation

## Purpose

This directory holds the labeled datasets used to evaluate the 6-stage
anomaly detection pipeline in `backend/app/core/anomaly_detector.py`. The
18-clause seed in `evals/fixtures/labeled_clauses.json` is supplemented
here by larger curated corpora (UNFAIR-ToS, OPP-115) and an expert-labeled
gold holdout used for the headline accuracy numbers. All loading goes
through `evals/datasets/loader.py` so callers see a uniform schema
regardless of which source the data came from.

---

## Datasets

### UNFAIR-ToS (LexGLUE) — `unfair_tos.jsonl`

- **Source**: `huggingface.co/datasets/coastalcph/lex_glue`, config `unfair_tos`
- **Size**: ~9,414 sentences drawn from 50 consumer Terms of Service
  documents, each annotated with one or more "unfair clause" categories
  (limitation of liability, unilateral change, unilateral termination,
  arbitration, choice of law, jurisdiction, content removal, contract by
  using).
- **License**: **CC-BY-4.0** — commercial use is permitted with
  attribution.
- **How to ingest**:
  ```bash
  python -m evals.datasets.ingest_unfair_tos
  ```
  This pulls the HuggingFace dataset, maps each label to our internal
  severity scale, and writes `unfair_tos.jsonl` next to this file.
- **Citation**:
  - Lippi, M., Pałka, P., Contissa, G., Lagioia, F., Micklitz, H.-W.,
    Sartor, G., & Torroni, P. (2019). *CLAUDETTE: an Automated Detector
    of Potentially Unfair Clauses in Online Terms of Service*. Artificial
    Intelligence and Law.
  - Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos,
    I., Katz, D. M., & Aletras, N. (2022). *LexGLUE: A Benchmark Dataset
    for Legal Language Understanding in English*. ACL.

### OPP-115 (Online Privacy Policies) — `opp115.jsonl`

- **Source**: `https://usableprivacy.org/static/data/OPP-115_v1_0.zip`
- **Size**: 115 website privacy policies, annotated at clause level by
  law students across 10 high-level data-practice categories (First Party
  Collection / Use, Third Party Sharing / Collection, User Choice /
  Control, User Access / Edit / Delete, Data Retention, Data Security,
  Policy Change, Do Not Track, International / Specific Audiences,
  Other).
- **License**: **CC-BY-NC** — research and teaching only. **For
  commercial use, a separate license must be obtained via the CMU
  Flintbox tech-transfer office.**
- **How to ingest**:
  ```bash
  python -m evals.datasets.ingest_opp115
  ```
  This downloads the zip, parses the annotator-merged labels, and writes
  `opp115.jsonl` next to this file.
- **Citation**:
  - Wilson, S., Schaub, F., Dara, A. A., Liu, F., Cherivirala, S.,
    Leon, P. G., Andersen, M. S., Zimmeck, S., Sathyendra, K. M.,
    Russell, N. C., Norton, T. B., Hovy, E., Reidenberg, J., &
    Sadeh, N. (2016). *The Creation and Analysis of a Website Privacy
    Policy Corpus*. ACL.
- **Warning**: OPP-115 carries a **non-commercial** clause. Any pipeline
  that ships a commercial product whose decisions rely on insights
  derived from this dataset must obtain a separate license from CMU
  before shipping. In practice this means: training-time use only,
  exclude OPP-115 from any production prompt examples, and keep its
  outputs out of any customer-visible report unless legal has cleared
  it.

### Seed (hand-labeled) — `../fixtures/labeled_clauses.json`

- **Size**: 18 hand-labeled clauses, curated for unit-style eval of the
  LLM detector. CUAD- and ContractEval-inspired.
- **License**: project-internal; do not redistribute.
- **How to ingest**:
  ```python
  from evals.datasets.loader import load_dataset
  clauses = load_dataset("seed")
  ```

---

## Gold holdout — `gold_holdout.jsonl`

The headline accuracy number for the pipeline is measured on this file.

- **Purpose**: held-out, expert-labeled evaluation set. **Never used for
  prompt tuning, in-context examples, or any feedback loop that touches
  the production model.** It exists exclusively for offline reporting.
- **Target size**: 100–150 clauses, stratified by severity so each tier
  has enough mass to compute per-severity precision/recall:
  - 20 `critical`
  - 40 `high`
  - 50 `medium`
  - 30 `low`
- **Access rules**: only code under `backend/evals/` may read this file.
  Two independent mechanisms enforce this:
  - **Runtime firewall** — `evals/datasets/firewall.py`. Every read calls
    `assert_caller_in_evals_only()`, which inspects the call stack and
    raises `RuntimeError` if any frame lives under `app/core/`,
    `app/services/`, or `app/api/`.
  - **Static CI rule** — `backend/scripts/check_holdout_firewall.sh`.
    Greps the production tree for the literal string `gold_holdout` and
    fails CI if a match is found, even if the code never actually
    executes.
  Both must pass; either alone is bypassable in principle, the
  combination is not.
- **Labeling instructions**: refer to the system prompt in
  `backend/app/core/llm_clause_detector.py` for canonical severity
  definitions (critical / high / medium / low) and the 11 risk
  categories. Each record needs the 7 `EvalClause` fields (clause text,
  source doc id, section, severity, risk_category, annotator notes,
  annotator id). Two-labeler agreement is strongly preferred; record
  disagreements so they can feed back into the labeling rubric.

---

## Loader usage

The unified loader takes a dataset name (or `"all"`) and returns a list
of records in the common `EvalClause` schema. The gold holdout is **not**
included in `"all"` — callers must request `"gold"` explicitly, and only
eval code is permitted to do so.

```python
from evals.datasets.loader import load_dataset

# Public corpora — fine for prompt tuning, ablations, baselines.
clauses = load_dataset("all")          # seed + unfair_tos + opp115
seed = load_dataset("seed")
ut = load_dataset("unfair_tos")
opp = load_dataset("opp115")

# Gold holdout — only from inside evals/, only for final reporting.
gold = load_dataset("gold")            # raises RuntimeError from app/*
```

---

## Compliance notes

- **UNFAIR-ToS** is CC-BY-4.0. Attribute Lippi et al. 2019 and
  Chalkidis et al. 2022 in any published metric, blog post, paper, or
  customer-facing document that reports numbers derived from this
  dataset.
- **OPP-115** is CC-BY-NC. **Must not be used in any commercial-output
  pipeline without a separate license obtained from CMU.** Treat its
  contents as research-only training data for the eval harness; do not
  pipe OPP-115 examples into prompts shipped to paying customers, and do
  not surface raw OPP-115 text in customer-visible reports.
- **Gold holdout** is project-internal. Do not publish, do not commit to
  any public mirror, do not paste into third-party tools that retain
  prompts. The whole point of holding it out is that no model — ours or
  anybody else's — has seen it. Leak it once and the kappa numbers it
  produces become meaningless forever.
