#!/usr/bin/env python3
"""
Diagnostic script to test the anomaly detection pipeline directly.
This bypasses the API to identify exactly where detection is failing.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Sample risky clauses from Apple T&C
TEST_CLAUSES = [
    {
        "section": "Termination",
        "text": "Apple reserves the right to modify, suspend, or discontinue the Services (or any part or content thereof) at any time with or without notice to you, and Apple will not be liable to you or to any third party should it exercise such rights."
    },
    {
        "section": "Data Collection",
        "text": "We may collect and use your personal information, including your location, browsing history, and usage data, to personalize content and advertisements. This information may be shared with third-party partners for marketing purposes."
    },
    {
        "section": "Liability",
        "text": "IN NO EVENT SHALL APPLE BE LIABLE FOR ANY DIRECT, SPECIAL, INDIRECT, OR CONSEQUENTIAL DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, BUSINESS, OR GOODWILL, ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT."
    },
    {
        "section": "Dispute Resolution",
        "text": "You agree that any dispute relating to this agreement shall be resolved through binding arbitration, and you waive your right to participate in any class action lawsuit or class-wide arbitration."
    },
    {
        "section": "Changes",
        "text": "Apple may modify these Terms at any time without prior notice. Your continued use of the Services following any changes constitutes your acceptance of the new Terms."
    },
    {
        "section": "Indemnification",
        "text": "You agree to indemnify, defend, and hold harmless Apple and its officers, directors, employees, and agents from any claims, damages, losses, or expenses arising from your use of the Services or violation of these Terms."
    },
]


async def test_pattern_detection():
    """Test pattern-based detection."""
    print("\n" + "="*60)
    print("TESTING PATTERN-BASED DETECTION")
    print("="*60)
    
    from app.core.risk_indicators import RiskIndicatorDetector
    
    detector = RiskIndicatorDetector()
    
    for clause in TEST_CLAUSES:
        print(f"\n--- {clause['section']} ---")
        print(f"Text: {clause['text'][:100]}...")
        
        indicators = detector.detect_indicators(clause['text'], service_type="general")
        
        if indicators:
            print(f"✓ Found {len(indicators)} indicators:")
            for ind in indicators:
                print(f"  - {ind['indicator']} ({ind['severity']}): {ind['description'][:50]}...")
        else:
            print("✗ No indicators detected!")


async def test_semantic_detection():
    """Test semantic anomaly detection."""
    print("\n" + "="*60)
    print("TESTING SEMANTIC ANOMALY DETECTION")
    print("="*60)
    
    from app.core.semantic_anomaly_detector import SemanticAnomalyDetector
    
    detector = SemanticAnomalyDetector(similarity_threshold=0.45)
    
    print(f"Model available: {detector.is_available}")
    print(f"Similarity threshold: {detector.similarity_threshold}")
    
    if not detector.is_available:
        print("✗ Semantic detector NOT AVAILABLE - model failed to load!")
        return
    
    for clause in TEST_CLAUSES:
        print(f"\n--- {clause['section']} ---")
        print(f"Text: {clause['text'][:100]}...")
        
        result = detector.detect_semantic_anomalies(clause['text'])
        
        if result.get('is_anomalous'):
            print(f"✓ Semantic anomaly detected!")
            print(f"  Similarity: {result.get('similarity_score', 0):.3f}")
            print(f"  Category: {result.get('matched_category')}")
            print(f"  Pattern: {result.get('matched_pattern', '')[:50]}...")
            print(f"  Confidence: {result.get('confidence', 0):.2f}")
        else:
            print(f"✗ Not detected as anomaly")
            print(f"  Max similarity: {result.get('similarity_score', 0):.3f} (threshold: {detector.similarity_threshold})")
            if result.get('all_matches'):
                print(f"  Top match: {result['all_matches'][0]['category']} ({result['all_matches'][0]['similarity']:.3f})")


async def test_statistical_detection():
    """Test statistical outlier detection."""
    print("\n" + "="*60)
    print("TESTING STATISTICAL OUTLIER DETECTION")
    print("="*60)
    
    from app.core.statistical_outlier_detector import StatisticalOutlierDetector
    from app.core.constants import ModelConfig
    
    detector = StatisticalOutlierDetector(
        contamination=ModelConfig.STATISTICAL_CONTAMINATION,
        random_state=ModelConfig.STATISTICAL_RANDOM_STATE
    )
    
    # Try to load saved model
    model_path = Path(__file__).parent.parent / "app" / "core" / ".cache" / "statistical_detector.pkl"
    
    if model_path.exists():
        try:
            detector.load_model(str(model_path))
            print(f"✓ Model loaded from {model_path}")
        except Exception as e:
            print(f"✗ Failed to load model: {e}")
    else:
        print(f"✗ No model file found at {model_path}")
    
    print(f"Model fitted: {detector.is_fitted}")
    
    if not detector.is_fitted:
        print("✗ Statistical detector NOT FITTED - needs training!")
        return
    
    for clause in TEST_CLAUSES:
        print(f"\n--- {clause['section']} ---")
        
        clause_dict = {'text': clause['text'], 'section': clause['section']}
        result = detector.predict(clause_dict)
        
        if result.get('is_outlier'):
            print(f"✓ Statistical outlier detected!")
            print(f"  Anomaly score: {result.get('anomaly_score', 0):.3f}")
            print(f"  Confidence: {result.get('confidence', 0):.2f}")
        else:
            print(f"✗ Not detected as outlier")
            print(f"  Anomaly score: {result.get('anomaly_score', 0):.3f}")


async def test_multi_stage_detection():
    """Test the full multi-stage detection pipeline."""
    print("\n" + "="*60)
    print("TESTING MULTI-STAGE DETECTION PIPELINE")
    print("="*60)
    
    from app.services.claude_service import ClaudeService
    from app.services.pinecone_service import PineconeService
    from app.core.anomaly_detector import AnomalyDetector
    
    # Initialize services
    claude_service = ClaudeService()
    pinecone_service = PineconeService()
    await pinecone_service.initialize()
    
    # Initialize detector
    detector = AnomalyDetector(claude_service, pinecone_service, db=None)
    
    print(f"\nDetector status:")
    print(f"  Pattern detection: ✓ Available")
    print(f"  Semantic detection: {'✓' if detector.semantic_anomaly_detector and detector.semantic_anomaly_detector.is_available else '✗'} {'Available' if detector.semantic_anomaly_detector and detector.semantic_anomaly_detector.is_available else 'NOT Available'}")
    print(f"  Statistical detection: {'✓' if detector.statistical_detector and detector.statistical_detector.is_fitted else '✗'} {'Fitted' if detector.statistical_detector and detector.statistical_detector.is_fitted else 'NOT Fitted'}")
    
    # Test each clause
    for clause in TEST_CLAUSES:
        print(f"\n--- {clause['section']} ---")
        print(f"Text: {clause['text'][:80]}...")
        
        clause_dict = {'text': clause['text'], 'section': clause['section']}
        
        result = await detector._run_multi_stage_detection(
            clause_text=clause['text'],
            clause_dict=clause_dict,
            service_type="general"
        )
        
        print(f"\nResults:")
        print(f"  Stage 1 confidence: {result.get('stage1_confidence', 0):.2f}")
        print(f"  Proceed to Stage 2: {result.get('proceed_to_stage2', False)}")
        print(f"  Flags: pattern={result['flags']['pattern']}, semantic={result['flags']['semantic']}, statistical={result['flags']['statistical']}")
        
        # Show method confidences
        for method, conf in result.get('method_confidences', {}).items():
            print(f"  {method} confidence: {conf:.2f}")
        
        # Show adaptive weights
        if 'adaptive_weights' in result:
            print(f"  Adaptive weights: {result['adaptive_weights']}")


async def main():
    """Run all diagnostic tests."""
    print("="*60)
    print("ANOMALY DETECTION DIAGNOSTIC")
    print("="*60)
    
    # Test each component
    await test_pattern_detection()
    await test_semantic_detection()
    await test_statistical_detection()
    await test_multi_stage_detection()
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
