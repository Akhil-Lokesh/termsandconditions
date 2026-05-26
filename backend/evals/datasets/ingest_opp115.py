"""OPP-115 ingester.

Source: Wilson et al. "The Creation and Analysis of a Website Privacy
Policy Corpus" (OPP-115), distributed by Carnegie Mellon's Usable
Privacy Policy Project.

  Download URL: https://usableprivacy.org/static/data/OPP-115_v1_0.zip
  License:      CC-BY-NC (research / teaching). Commercial use requires
                permission from CMU. See evals/datasets/README.md for
                attribution details (other agent will write that).

The corpus is 115 privacy policies, each segmented and annotated by
multiple annotators across 10 data-practice categories. We:

    1. Download the ZIP into `_raw/opp115.zip` if not already present.
    2. Extract annotation CSVs from `OPP-115_v1_0/annotations/*.csv`.
    3. Pull segment text from `OPP-115_v1_0/sanitized_policies/*.html`.
    4. Majority-vote across annotators per (policy_id, segment_id).
    5. Map the source category to our (risk_category, severity).
    6. Write one JSONL line per voted-on segment to `opp115.jsonl`.

Defensive: any download/extraction failure produces an empty output
file and a clear log message; the ingester does not crash.

Run from `backend/`:
    venv/bin/python -m evals.datasets.ingest_opp115
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import urllib.request
import warnings
import zipfile
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore", message=".*OpenSSL.*", category=Warning)

_THIS_DIR = Path(__file__).resolve().parent
_RAW_DIR = _THIS_DIR / "_raw"
_ZIP_PATH = _RAW_DIR / "opp115.zip"
_EXTRACT_DIR = _RAW_DIR / "opp115_extracted"
OUTPUT_PATH = _THIS_DIR / "opp115.jsonl"

DOWNLOAD_URL = "https://usableprivacy.org/static/data/OPP-115_v1_0.zip"

# Map OPP-115 source category names to our (risk_category, severity).
# Severities are conservative defaults — privacy is generally medium,
# bumped to "high" for third-party sharing (the canonical "do they sell
# my data?" question), and demoted to "low" for purely defensive or
# administrative practices (data security, policy change, "other").
CATEGORY_MAPPING: Dict[str, Dict[str, str]] = {
    "First Party Collection/Use": {"category": "data", "severity": "medium"},
    "Third Party Sharing/Collection": {"category": "data", "severity": "high"},
    "User Choice/Control": {"category": "rights", "severity": "medium"},
    "User Access, Edit and Deletion": {"category": "rights", "severity": "medium"},
    # Slight name variations seen across releases — keep both.
    "User Access, Edit, and Deletion": {"category": "rights", "severity": "medium"},
    "Data Retention": {"category": "data", "severity": "medium"},
    "Data Security": {"category": "data", "severity": "low"},
    "Policy Change": {"category": "modification", "severity": "low"},
    "International and Specific Audiences": {"category": "data", "severity": "medium"},
    "Do Not Track": {"category": "surveillance", "severity": "medium"},
    "Other": {"category": "other", "severity": "low"},
    # Sub-category variations sometimes show up too.
    "Practice Not Covered": {"category": "other", "severity": "low"},
    "Privacy contact information": {"category": "other", "severity": "low"},
    "Introductory/Generic": {"category": "other", "severity": "low"},
}


class _HTMLStripper(HTMLParser):
    """Tiny stdlib-only HTML->text converter to avoid adding bs4 as a
    dep just for this script. Concatenates text data, collapses
    whitespace at the end."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        joined = "".join(self.parts)
        # Collapse runs of whitespace; OPP-115 HTML has lots of newlines.
        return re.sub(r"\s+", " ", joined).strip()


def _strip_html(html: str) -> str:
    parser = _HTMLStripper()
    try:
        parser.feed(html)
    except Exception:
        # Malformed markup — return whatever we've extracted so far.
        pass
    return parser.get_text()


def _download_zip() -> bool:
    """Download the OPP-115 ZIP into `_raw/opp115.zip`. Returns True on
    success (file present and non-empty), False otherwise."""
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    if _ZIP_PATH.exists() and _ZIP_PATH.stat().st_size > 1_000_000:
        print(f"  using cached {_ZIP_PATH} ({_ZIP_PATH.stat().st_size:,} bytes)")
        return True
    print(f"  downloading {DOWNLOAD_URL} -> {_ZIP_PATH} ...")
    try:
        req = urllib.request.Request(
            DOWNLOAD_URL,
            headers={"User-Agent": "Mozilla/5.0 (evals-ingester)"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp, _ZIP_PATH.open(
            "wb"
        ) as f_out:
            while True:
                chunk = resp.read(1024 * 64)
                if not chunk:
                    break
                f_out.write(chunk)
    except Exception as e:
        print(f"ERROR: download failed: {e}")
        if _ZIP_PATH.exists():
            try:
                _ZIP_PATH.unlink()
            except OSError:
                pass
        return False
    size = _ZIP_PATH.stat().st_size if _ZIP_PATH.exists() else 0
    print(f"  downloaded {size:,} bytes")
    return size > 1_000_000


def _open_zip() -> Optional[zipfile.ZipFile]:
    """Open the ZIP, returning None on any structural problem."""
    if not _ZIP_PATH.exists():
        return None
    try:
        return zipfile.ZipFile(_ZIP_PATH, "r")
    except zipfile.BadZipFile as e:
        print(f"ERROR: ZIP file is corrupt ({e})")
        try:
            _ZIP_PATH.unlink()
        except OSError:
            pass
        return None


def _classify_files(zf: zipfile.ZipFile) -> Tuple[List[str], List[str]]:
    """Return (annotation_csv_paths, policy_html_paths) inside the ZIP."""
    annotations: List[str] = []
    policies: List[str] = []
    for name in zf.namelist():
        lower = name.lower()
        if "/annotations/" in lower and lower.endswith(".csv"):
            annotations.append(name)
        elif "/sanitized_policies/" in lower and (
            lower.endswith(".html") or lower.endswith(".htm")
        ):
            policies.append(name)
    return annotations, policies


def _policy_key_from_path(path: str) -> str:
    """Extract the policy filename stem (e.g. 'aol.com') from a ZIP path."""
    return Path(path).stem


def _extract_policy_segments(
    zf: zipfile.ZipFile, html_path: str
) -> Dict[str, str]:
    """Return {segment_id: text} for one policy HTML file.

    OPP-115's `sanitized_policies/*.html` files are single-line HTML
    strings with segments delimited by the literal token `|||`. The
    `segment_id` column in the annotations CSV is the zero-indexed
    position of that segment in the `|||`-split list.

    We strip HTML tags inline per segment so downstream callers get
    clean prose.
    """
    try:
        raw = zf.read(html_path).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ! could not read {html_path}: {e}")
        return {}

    segments: Dict[str, str] = {}
    for idx, chunk in enumerate(raw.split("|||")):
        text = _strip_html(chunk)
        if text:
            segments[str(idx)] = text
    return segments


def _read_annotation_rows(zf: zipfile.ZipFile, csv_path: str) -> List[Dict[str, str]]:
    """Read one OPP-115 annotation CSV, returning a list of dict rows.

    The CSV format is the OPP-115 release format:
      annotation_id, batch_id, annotator_id, policy_id, segment_id,
      category_name, attribute-value-pairs, date, policy_url

    Some releases ship without a header row, in which case we fall back
    to positional columns.
    """
    try:
        data = zf.read(csv_path).decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ! could not read {csv_path}: {e}")
        return []

    # Sniff for a header.
    reader = csv.reader(io.StringIO(data))
    rows = list(reader)
    if not rows:
        return []

    header_keywords = {"annotation_id", "policy_id", "segment_id", "category_name"}
    first = [c.strip().lower() for c in rows[0]]
    has_header = any(k in first for k in header_keywords)

    if has_header:
        keys = [c.strip() for c in rows[0]]
        body = rows[1:]
    else:
        # Positional fallback per the canonical OPP-115 layout. Some
        # releases include `attribute_value_pairs` as a single JSON-ish
        # field at index 6.
        keys = [
            "annotation_id",
            "batch_id",
            "annotator_id",
            "policy_id",
            "segment_id",
            "category_name",
            "attribute_value_pairs",
            "date",
            "policy_url",
        ]
        body = rows

    out: List[Dict[str, str]] = []
    for r in body:
        if not r:
            continue
        # Tolerate extra trailing fields without crashing.
        rec = {}
        for i, key in enumerate(keys):
            rec[key] = r[i] if i < len(r) else ""
        out.append(rec)
    return out


def ingest() -> int:
    """Run OPP-115 ingestion. Returns rows written.

    Always writes a (possibly empty) output file so downstream callers
    can rely on its presence.
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Pre-truncate so a partial run doesn't leave stale rows.
    OUTPUT_PATH.write_text("", encoding="utf-8")

    if not _download_zip():
        print("OPP-115 ingestion: download failed; wrote empty output file.")
        return 0

    zf = _open_zip()
    if zf is None:
        print("OPP-115 ingestion: ZIP unreadable; wrote empty output file.")
        return 0

    try:
        annotation_paths, policy_html_paths = _classify_files(zf)
        print(
            f"  found {len(annotation_paths)} annotation CSV(s), "
            f"{len(policy_html_paths)} policy HTML file(s) in ZIP"
        )

        if not annotation_paths or not policy_html_paths:
            print("ERROR: ZIP layout unexpected — no annotations or policies found.")
            return 0

        # Build {policy_key: {segment_id: text}}.
        print("  parsing policy HTML for segment text ...")
        segments_by_policy: Dict[str, Dict[str, str]] = {}
        for html_path in policy_html_paths:
            key = _policy_key_from_path(html_path)
            # OPP-115 file naming convention is `<policy_id>_<domain>.html`
            # e.g. `1_aol.com.html`. Split on first underscore to get the
            # numeric policy_id used in the annotation CSVs.
            policy_id_prefix = key.split("_", 1)[0]
            segs = _extract_policy_segments(zf, html_path)
            segments_by_policy[policy_id_prefix] = segs
            segments_by_policy[key] = segs  # also index by full key

        # Aggregate annotations: {(policy_key, segment_id): Counter(category)}
        print("  reading annotation CSVs ...")
        votes: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
        unmapped_categories: Counter = Counter()
        for csv_path in annotation_paths:
            rows = _read_annotation_rows(zf, csv_path)
            csv_key = Path(csv_path).stem  # e.g. "1_aol.com"
            csv_policy_id = csv_key.split("_", 1)[0]
            for r in rows:
                policy_id = r.get("policy_id", "").strip() or csv_policy_id
                segment_id = r.get("segment_id", "").strip()
                category = r.get("category_name", "").strip()
                if not segment_id or not category:
                    continue
                # The category column in many OPP-115 dumps already uses
                # canonical English names. Strip surrounding quotes etc.
                category = category.strip("\"' ")
                if category not in CATEGORY_MAPPING:
                    unmapped_categories[category] += 1
                # Key the votes by the CSV's policy stem so segment text
                # lookup works downstream.
                votes[(csv_key, segment_id)][category] += 1

        if unmapped_categories:
            print("  note: unmapped categories (top 5):")
            for cat, n in unmapped_categories.most_common(5):
                print(f"    {cat!r}: {n}")

        # Pick the majority category per segment and emit a row.
        rows_written = 0
        severity_counts: Counter = Counter()
        category_counts: Counter = Counter()
        skipped_no_text = 0
        skipped_no_mapping = 0

        with OUTPUT_PATH.open("w", encoding="utf-8") as f_out:
            for (policy_key, segment_id), vote_counter in votes.items():
                # Majority vote across annotators.
                top_category, top_count = vote_counter.most_common(1)[0]
                if top_category not in CATEGORY_MAPPING:
                    skipped_no_mapping += 1
                    continue

                # Resolve segment text. Try the full key first, then the
                # numeric prefix.
                segs = segments_by_policy.get(policy_key) or segments_by_policy.get(
                    policy_key.split("_", 1)[0], {}
                )
                text = segs.get(segment_id, "").strip()
                if not text or len(text) < 4:
                    skipped_no_text += 1
                    continue

                mapping = CATEGORY_MAPPING[top_category]
                notes_parts = [
                    f"{cat}={count}" for cat, count in vote_counter.most_common()
                ]
                record = {
                    "clause_id": f"opp115_{policy_key}_{segment_id}",
                    "section": top_category,
                    "text": text,
                    "expected_severity": mapping["severity"],
                    "expected_risk_category": mapping["category"],
                    "notes": "votes: " + ", ".join(notes_parts),
                    "source": "OPP-115 (CMU Usable Privacy)",
                }
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                rows_written += 1
                severity_counts[mapping["severity"]] += 1
                category_counts[mapping["category"]] += 1

        print()
        print("=" * 60)
        print(f"OPP-115 ingestion complete: {rows_written} rows -> {OUTPUT_PATH}")
        print("=" * 60)
        print(f"  skipped (no text):    {skipped_no_text}")
        print(f"  skipped (no mapping): {skipped_no_mapping}")
        print("by severity:")
        for sev in ("critical", "high", "medium", "low"):
            print(f"  {sev:<10} {severity_counts.get(sev, 0):>6}")
        print("by category (mapped):")
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat:<14} {count:>6}")
        return rows_written
    finally:
        zf.close()


if __name__ == "__main__":
    n = ingest()
    # Exit 0 even on zero rows — the script "succeeded" structurally
    # even if the download didn't. The output file's presence is the
    # contract.
    sys.exit(0 if n >= 0 else 1)
