#!/usr/bin/env python3
"""
Test anomaly detection using TikTok ToS clauses from the database.
This simulates what the upload pipeline does, but skips PDF extraction.
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')
# Set our app loggers to INFO
logging.getLogger('app.core.anomaly_detector').setLevel(logging.INFO)
logging.getLogger('app.core.llm_clause_detector').setLevel(logging.INFO)

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from app.core.anomaly_detector import AnomalyDetector
from app.core.config import settings
from app.services.claude_service import ClaudeService
from app.services.pinecone_service import PineconeService


async def main():
    # Load clauses from database
    engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT section, clause_number, text
            FROM clauses
            WHERE document_id::text LIKE '3b3371d4%%'
            ORDER BY section, clause_number
        """))
        rows = result.fetchall()

    print(f"Loaded {len(rows)} clauses from database")

    # Build sections structure (same format as StructureExtractor output)
    sections_map = {}
    for section_name, clause_number, clause_text in rows:
        if section_name not in sections_map:
            sections_map[section_name] = {
                "title": section_name,
                "number": str(len(sections_map) + 1),
                "content": "",
                "clauses": [],
            }
        sections_map[section_name]["clauses"].append({
            "clause_number": clause_number,
            "text": clause_text,
        })

    sections = list(sections_map.values())
    total_clauses = sum(len(s["clauses"]) for s in sections)
    print(f"Organized into {len(sections)} sections, {total_clauses} clauses")

    # Initialize detector
    claude_service = ClaudeService()
    pinecone_service = PineconeService()
    await pinecone_service.initialize()

    detector = AnomalyDetector(claude_service, pinecone_service, None)

    print("\nRunning anomaly detection with LLM batch + keyword detection...")
    print("=" * 60)

    report = await detector.detect_anomalies(
        document_id="test-tiktok-rerun",
        sections=sections,
        company_name="TikTok",
        service_type="social_media",
    )

    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    high = report.get("high_severity_alerts", report.get("high_severity", []))
    medium = report.get("medium_severity_alerts", report.get("medium_severity", []))
    low = report.get("low_severity_alerts", report.get("low_severity", []))
    risk_score = report.get("overall_risk_score", "N/A")

    print(f"\nRisk Score: {risk_score}/10")
    print(f"CRITICAL/HIGH: {len(high)}, MEDIUM: {len(medium)}, LOW: {len(low)}")
    print(f"Total: {len(high) + len(medium) + len(low)}")

    all_anomalies = []
    for sev_label, anomalies in [("HIGH", high), ("MEDIUM", medium), ("LOW", low)]:
        for a in anomalies:
            severity = a.get("severity", "unknown").upper()
            all_anomalies.append((severity, a))

    print(f"\n--- All Anomalies ---")
    for i, (severity, a) in enumerate(all_anomalies, 1):
        section = a.get("section", "Unknown")
        clause_num = a.get("clause_number", "?")
        category = a.get("risk_category", "other")
        explanation = a.get("explanation", "")[:120]
        print(f"\n{i}. [{severity}] {section} / {clause_num}")
        print(f"   Category: {category}")
        print(f"   Explanation: {explanation}...")

    # Expected clause check
    print(f"\n{'=' * 60}")
    print("EXPECTED CLAUSE CHECK")
    print("=" * 60)

    all_texts = " ".join(
        a.get("clause_text", "").lower() + " " + a.get("explanation", "").lower()
        for _, a in all_anomalies
    )

    expected = [
        ("moral rights", "Waiver of moral rights"),
        ("user-to-user", "User-to-user content license"),
        ("likeness", "Name/image/voice/likeness license"),
        ("statute of limitation", "Shortened statute of limitations"),
        ("indemnif", "Indemnification"),
        ("arbitration", "Forced arbitration"),
        ("class action", "Class action waiver"),
        ("terminat", "Account termination"),
        ("automat", "Automated content analysis"),
        ("revenue", "Revenue exclusion"),
        ("modif", "Unilateral modification"),
        ("warrant", "Warranty disclaimer"),
        ("liabilit", "Liability limitation"),
        ("sublicens", "Content sublicensing"),
        ("irrevocab", "Irrevocable rights"),
    ]

    found_count = 0
    for term, desc in expected:
        found = term.lower() in all_texts
        status = "FOUND" if found else "MISSED"
        if found:
            found_count += 1
        print(f"  [{status}] {desc} ({term})")

    print(f"\nDetection rate: {found_count}/{len(expected)} ({found_count/len(expected)*100:.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
