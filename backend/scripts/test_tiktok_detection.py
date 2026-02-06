#!/usr/bin/env python3
"""
Test anomaly detection on TikTok ToS text file.
Runs the full detection pipeline including LLM batch detection.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.anomaly_detector import AnomalyDetector
from app.core.structure_extractor import StructureExtractor
from app.services.claude_service import ClaudeService
from app.services.pinecone_service import PineconeService


async def main():
    # Load TikTok ToS text
    tos_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "baseline_corpus", "social", "tiktok_tos.txt"
    )

    if not os.path.exists(tos_path):
        # Try alternate location
        tos_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "baseline_corpus", "social", "tiktok_tos.txt"
        )

    if not os.path.exists(tos_path):
        print(f"ERROR: TikTok ToS file not found at {tos_path}")
        return

    with open(tos_path, "r") as f:
        text = f.read()

    print(f"Loaded TikTok ToS: {len(text)} chars")

    # Pre-process: add line breaks before numbered sections if text has no newlines
    # (baseline corpus files from web scraping often lack proper formatting)
    import re
    if text.count("\n") < 10:
        print("Text has few newlines — adding line breaks before section headers...")
        # Add newlines before "1. Title", "2. Title" etc. and "4.1 ", "4.2 " etc.
        text = re.sub(r'(?<=[.!?])\s*(\d+\.\s+[A-Z])', r'\n\n\1', text)
        text = re.sub(r'(?<=[.!?])\s*(\d+\.\d+\s+[A-Z])', r'\n\n\1', text)
        # Add newlines before "In short:" summaries
        text = re.sub(r'(?<=[.!?])\s*(In short:)', r'\n\n\1', text)
        # Add newlines after "In short: ..." blocks (before the next paragraph)
        text = re.sub(r'(In short:[^.]+\.)\s*(?=[A-Z])', r'\1\n\n', text)
        print(f"After pre-processing: {text.count(chr(10))} newlines")

    # Step 1: Parse structure
    print("\n" + "="*60)
    print("STEP 1: PARSING DOCUMENT STRUCTURE")
    print("="*60)

    extractor = StructureExtractor()
    structure = await extractor.extract_structure(text)
    sections = structure["sections"]
    num_clauses = structure["num_clauses"]
    print(f"Found {num_clauses} clauses in {len(sections)} sections")

    # Step 2: Run anomaly detection
    print("\n" + "="*60)
    print("STEP 2: RUNNING ANOMALY DETECTION (with LLM batch)")
    print("="*60)

    claude_service = ClaudeService()
    pinecone_service = PineconeService()
    await pinecone_service.initialize()

    detector = AnomalyDetector(claude_service, pinecone_service, None)

    report = await detector.detect_anomalies(
        document_id="test-tiktok",
        sections=sections,
        company_name="TikTok",
        service_type="social_media",
    )

    # Step 3: Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    high = report.get("high_severity_alerts", report.get("high_severity", []))
    medium = report.get("medium_severity_alerts", report.get("medium_severity", []))
    low = report.get("low_severity_alerts", report.get("low_severity", []))
    risk_score = report.get("overall_risk_score", "N/A")

    print(f"\nRisk Score: {risk_score}/10")
    print(f"HIGH: {len(high)}, MEDIUM: {len(medium)}, LOW: {len(low)}")
    print(f"Total: {len(high) + len(medium) + len(low)}")

    all_anomalies = []
    for sev_label, anomalies in [("CRITICAL/HIGH", high), ("MEDIUM", medium), ("LOW", low)]:
        for a in anomalies:
            severity = a.get("severity", "unknown").upper()
            all_anomalies.append((severity, a))

    print(f"\n--- All Anomalies ---")
    for i, (severity, a) in enumerate(all_anomalies, 1):
        section = a.get("section", "Unknown")
        clause_num = a.get("clause_number", "?")
        category = a.get("risk_category", "other")
        explanation = a.get("explanation", "")[:120]
        print(f"\n{i}. [{severity}] {section} (clause {clause_num})")
        print(f"   Category: {category}")
        print(f"   Explanation: {explanation}...")

    # Check for expected clauses
    print(f"\n{'='*60}")
    print("EXPECTED CLAUSE CHECK")
    print("="*60)

    expected = [
        "moral rights",
        "user-to-user",
        "name/image/voice",
        "name, image",
        "likeness",
        "statute of limitation",
        "indemnif",
        "arbitration",
        "class action",
        "termination",
        "automated",
        "content analysis",
        "revenue",
        "modification",
        "warranty",
        "liability",
    ]

    all_texts = " ".join(
        a.get("clause_text", "").lower() + " " + a.get("explanation", "").lower()
        for _, a in all_anomalies
    )

    for term in expected:
        found = term.lower() in all_texts
        status = "FOUND" if found else "MISSED"
        print(f"  [{status}] {term}")


if __name__ == "__main__":
    asyncio.run(main())
