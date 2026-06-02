"""Quick TikTok-ToS pipeline runner.

Reads data/baseline_corpus/social/tiktok_tos.txt, splits into clause-sized
chunks, runs the LLMClauseDetector directly, and prints the breakdown by
severity. No DB, no auth, no HTTP — just the detector against real text.

Useful when comparing UI behaviour ("I see N anomalies for this doc") to
what the detector returns at the source.

Usage:
    cd backend
    python scripts/test_tiktok_pipeline.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from collections import Counter
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Tame the noise from sqlalchemy / passlib so the detector output is readable.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
for noisy in ("sqlalchemy.engine.Engine", "passlib.utils.compat",
              "passlib.registry", "httpx", "httpcore"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from app.core.llm_clause_detector import LLMClauseDetector  # noqa: E402
from app.services.claude_service import ClaudeService  # noqa: E402

TIKTOK_TXT = _BACKEND_DIR.parent / "data" / "baseline_corpus" / "social" / "tiktok_tos.txt"


def split_into_clauses(text: str) -> list[dict]:
    """Approximate clause split for a single-line TikTok ToS.

    Splits on numbered sections (1. ... 2. ... 4.1 ... 4.2 ...) and the
    'In short:' anchors TikTok uses heavily. Each chunk becomes a clause.
    """
    # Section headers like "1. Who your contract is with", "4.5 What you can't do"
    section_pat = re.compile(r"(\d{1,2}(?:\.\d{1,2})?\s+[A-Z][^.]{5,80}?)(?=[A-Z]|\.)")
    pieces = section_pat.split(text)
    clauses: list[dict] = []
    current_section = "Preamble"
    buf: list[str] = []
    for piece in pieces:
        p = piece.strip()
        if not p:
            continue
        # Detect a header by leading digit
        if re.match(r"^\d{1,2}(\.\d{1,2})?\s+[A-Z]", p):
            # flush prior section into clauses
            if buf:
                body = " ".join(buf).strip()
                for chunk in _chunk_text(body, min_chars=120, max_chars=800):
                    clauses.append({
                        "clause_number": f"{len(clauses)+1}",
                        "section": current_section[:80],
                        "text": chunk,
                    })
                buf = []
            current_section = p
        else:
            buf.append(p)
    if buf:
        body = " ".join(buf).strip()
        for chunk in _chunk_text(body, min_chars=120, max_chars=800):
            clauses.append({
                "clause_number": f"{len(clauses)+1}",
                "section": current_section[:80],
                "text": chunk,
            })
    return clauses


def _chunk_text(text: str, min_chars: int, max_chars: int) -> list[str]:
    """Greedy sentence-aware chunking that respects min/max length."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out, buf = [], ""
    for s in sentences:
        if not s.strip():
            continue
        if len(buf) + len(s) + 1 <= max_chars:
            buf = (buf + " " + s).strip()
        else:
            if len(buf) >= min_chars:
                out.append(buf)
                buf = s
            else:
                buf = (buf + " " + s).strip()
    if buf:
        if len(buf) < min_chars and out:
            out[-1] = out[-1] + " " + buf
        else:
            out.append(buf)
    return out


async def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        # Load from backend/.env if not already exported.
        env = _BACKEND_DIR / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
                    break
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY missing — exiting.")
        return 1

    if not TIKTOK_TXT.exists():
        print(f"missing: {TIKTOK_TXT}")
        return 1

    raw = TIKTOK_TXT.read_text(encoding="utf-8").strip()
    clauses = split_into_clauses(raw)
    print(f"\nSplit TikTok ToS into {len(clauses)} clauses")
    print(f"(first clause preview: {clauses[0]['section']} — {clauses[0]['text'][:120]}…)\n")

    detector = LLMClauseDetector(ClaudeService())
    findings = await detector.detect_risky_clauses(
        clauses,
        company_name="TikTok",
        service_type="social_media",
        document_type="terms_of_service",
    )

    print(f"\n=== Detector returned {len(findings)} risky findings ===\n")
    sev = Counter(f.get("severity") for f in findings)
    cat = Counter(f.get("risk_category") for f in findings)
    print(f"severities: {dict(sev)}")
    print(f"categories: {dict(cat)}\n")

    for i, f in enumerate(findings, 1):
        sev = f.get("severity", "?")
        cat = f.get("risk_category", "?")
        section = f.get("section", "?")[:60]
        clause_text = (f.get("clause_text") or "")[:120].replace("\n", " ")
        print(f"  {i:>2}. [{sev:<8}] [{cat:<14}] {section}")
        print(f"      \"{clause_text}…\"")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
