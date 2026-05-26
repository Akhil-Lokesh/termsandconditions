#!/usr/bin/env python3
"""
Test anomaly detection directly without authentication.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.anomaly_detector import AnomalyDetector
from app.core.risk_indicators import RiskIndicators
from app.core.semantic_anomaly_detector import SemanticAnomalyDetector
from app.core.constants import ModelConfig
from app.services.claude_service import ClaudeService
from app.services.pinecone_service import PineconeService


# Test clauses - known risky clauses
TEST_CLAUSES = [
    "We may terminate your account at any time without notice for any reason.",
    "We reserve the right to share your personal information with third parties for marketing purposes.",
    "By using this service, you waive all rights to participate in class action lawsuits.",
    "We may modify these terms at any time without prior notice to you.",
    "We are not liable for any damages arising from the use of this service.",
    "Your data may be sold to advertisers and data brokers.",
    "You agree to indemnify and hold us harmless from any claims.",
    "We collect information about your browsing habits and share it with partners.",
]


async def test_pattern_detection():
    """Test pattern-based detection."""
    print("\n" + "="*60)
    print("TESTING PATTERN-BASED DETECTION")
    print("="*60)
    
    detector = RiskIndicators()
    
    for i, clause in enumerate(TEST_CLAUSES, 1):
        print(f"\n--- Clause {i} ---")
        print(f"Text: {clause[:80]}...")
        
        indicators = detector.detect_indicators(clause, "general")
        
        print(f"Indicators found: {len(indicators)}")
        for ind in indicators:
            print(f"  - {ind['indicator']} ({ind['severity']}): {ind['description'][:50]}...")


async def test_semantic_detection():
    """Test semantic anomaly detection."""
    print("\n" + "="*60)
    print("TESTING SEMANTIC ANOMALY DETECTION")
    print("="*60)
    
    detector = SemanticAnomalyDetector(
        model_name=ModelConfig.SEMANTIC_MODEL,
        similarity_threshold=ModelConfig.SEMANTIC_SIMILARITY_THRESHOLD
    )
    
    print(f"Model: {detector.model_name}")
    print(f"Threshold: {detector.similarity_threshold}")
    print(f"Is Available: {detector.is_available}")
    
    if not detector.is_available:
        print("WARNING: Semantic detector not available!")
        return
    
    for i, clause in enumerate(TEST_CLAUSES, 1):
        print(f"\n--- Clause {i} ---")
        print(f"Text: {clause[:80]}...")
        
        result = detector.detect_semantic_anomalies(clause)
        
        print(f"Is Anomalous: {result['is_anomalous']}")
        print(f"Similarity Score: {result['similarity_score']:.3f}")
        print(f"Confidence: {result['confidence']:.3f}")
        if result['matched_pattern']:
            print(f"Matched Pattern: {result['matched_pattern'][:50]}...")
            print(f"Matched Category: {result['matched_category']}")


async def test_full_detection():
    """Test full multi-stage detection."""
    print("\n" + "="*60)
    print("TESTING FULL MULTI-STAGE DETECTION")
    print("="*60)
    
    # Initialize services
    claude_service = ClaudeService()
    pinecone_service = PineconeService()
    await pinecone_service.initialize()
    
    detector = AnomalyDetector(claude_service, pinecone_service, None)
    
    print(f"Statistical detector fitted: {detector.statistical_detector.is_fitted if detector.statistical_detector else False}")
    print(f"Semantic detector available: {detector.semantic_anomaly_detector.is_available if detector.semantic_anomaly_detector else False}")
    
    flagged_count = 0
    
    for i, clause in enumerate(TEST_CLAUSES, 1):
        print(f"\n--- Clause {i} ---")
        print(f"Text: {clause[:80]}...")
        
        result = await detector._run_multi_stage_detection(
            clause_text=clause,
            clause_dict={'text': clause, 'section': 'Test'},
            service_type="general"
        )
        
        print(f"Stage 1 Confidence: {result['stage1_confidence']:.3f}")
        print(f"Proceed to Stage 2: {result['proceed_to_stage2']}")
        print(f"Flags: pattern={result['flags']['pattern']}, semantic={result['flags']['semantic']}, statistical={result['flags']['statistical']}")
        
        # Show method confidences
        print(f"Method confidences: {result['method_confidences']}")
        
        if result['proceed_to_stage2']:
            flagged_count += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {flagged_count}/{len(TEST_CLAUSES)} clauses flagged")
    print(f"{'='*60}")


async def main():
    """Run all tests."""
    print("="*60)
    print("ANOMALY DETECTION DIAGNOSTIC TEST")
    print("="*60)
    
    await test_pattern_detection()
    await test_semantic_detection()
    await test_full_detection()


if __name__ == "__main__":
    asyncio.run(main())
