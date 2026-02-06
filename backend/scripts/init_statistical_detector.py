#!/usr/bin/env python3
"""
Initialize and train the Statistical Outlier Detector from baseline corpus.

This script:
1. Loads clauses from the baseline corpus in Pinecone
2. Trains the Statistical Outlier Detector (Isolation Forest)
3. Saves the trained model for use in anomaly detection

Run this script after populating the baseline corpus to enable
statistical anomaly detection.

Usage:
    python scripts/init_statistical_detector.py
"""

import asyncio
import os
import sys
import pickle
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.pinecone_service import PineconeService
from app.core.statistical_outlier_detector import StatisticalOutlierDetector
from app.core.config import settings
from app.core.constants import ModelConfig


# Model save path
MODEL_SAVE_PATH = Path(__file__).parent.parent / "app" / "core" / ".cache" / "statistical_detector.pkl"


async def fetch_baseline_clauses(pinecone_service: PineconeService, limit: int = 1000) -> list:
    """
    Fetch clauses from the baseline corpus in Pinecone.

    Args:
        pinecone_service: Initialized Pinecone service
        limit: Maximum number of clauses to fetch

    Returns:
        List of clause dictionaries with text and metadata
    """
    print(f"Fetching up to {limit} clauses from baseline corpus...")

    # Query baseline namespace with a dummy vector to get all vectors
    # We'll use list operation instead if available
    try:
        # Get index stats first
        stats = pinecone_service.index.describe_index_stats()
        baseline_namespace = settings.PINECONE_BASELINE_NAMESPACE

        if baseline_namespace not in stats.namespaces:
            print(f"Warning: Baseline namespace '{baseline_namespace}' not found in Pinecone")
            print(f"Available namespaces: {list(stats.namespaces.keys())}")
            return []

        total_vectors = stats.namespaces[baseline_namespace].vector_count
        print(f"Found {total_vectors} vectors in baseline namespace")

        if total_vectors == 0:
            print("No vectors in baseline corpus. Run index_baseline_corpus.py first.")
            return []

        # Fetch vectors using list operation (more efficient)
        # Note: Pinecone list() returns IDs, then we fetch them
        clauses = []

        # Use a sample query to get vectors with metadata
        # Create a zero vector with the correct dimension
        dimension = 1536  # OpenAI embedding dimension
        zero_vector = [0.0] * dimension

        # Query with large top_k to get many results
        results = pinecone_service.index.query(
            vector=zero_vector,
            top_k=min(limit, total_vectors),
            namespace=baseline_namespace,
            include_metadata=True
        )

        for match in results.matches:
            metadata = match.metadata or {}
            clause = {
                'id': match.id,
                'text': metadata.get('text', ''),
                'section': metadata.get('section', 'Unknown'),
                'company': metadata.get('company', 'Unknown'),
                'industry': metadata.get('industry', 'Unknown'),
            }
            if clause['text']:
                clauses.append(clause)

        print(f"Fetched {len(clauses)} clauses from baseline corpus")
        return clauses

    except Exception as e:
        print(f"Error fetching baseline clauses: {e}")
        return []


def train_detector(clauses: list) -> StatisticalOutlierDetector:
    """
    Train the statistical outlier detector on baseline clauses.

    Args:
        clauses: List of clause dictionaries

    Returns:
        Trained StatisticalOutlierDetector
    """
    print(f"Training statistical outlier detector on {len(clauses)} clauses...")

    # Initialize detector with config values
    detector = StatisticalOutlierDetector(
        contamination=ModelConfig.STATISTICAL_CONTAMINATION,
        random_state=ModelConfig.STATISTICAL_RANDOM_STATE
    )

    # Train on baseline clauses
    detector.fit(clauses)

    print(f"Detector trained successfully!")
    print(f"  - Is fitted: {detector.is_fitted}")

    return detector


def save_detector(detector: StatisticalOutlierDetector, path: Path) -> None:
    """
    Save trained detector to disk.

    Args:
        detector: Trained detector
        path: Path to save the model
    """
    # Create cache directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use the detector's save_model method to ensure proper format
    detector.save_model(str(path))

    print(f"Detector saved to: {path}")


def load_detector(path: Path) -> StatisticalOutlierDetector:
    """
    Load a trained detector from disk.

    Args:
        path: Path to the saved model

    Returns:
        Loaded StatisticalOutlierDetector
    """
    with open(path, 'rb') as f:
        detector = pickle.load(f)

    print(f"Detector loaded from: {path}")
    print(f"  - Is fitted: {detector.is_fitted}")

    return detector


async def main():
    """Main function to initialize and train the statistical detector."""
    print("=" * 60)
    print("Statistical Outlier Detector Initialization")
    print("=" * 60)

    # Initialize Pinecone service
    print("\nInitializing Pinecone service...")
    pinecone_service = PineconeService()
    await pinecone_service.initialize()
    print("Pinecone service initialized")

    # Fetch baseline clauses
    clauses = await fetch_baseline_clauses(pinecone_service, limit=1000)

    if not clauses:
        print("\nNo clauses found in baseline corpus.")
        print("Please run index_baseline_corpus.py first to populate the baseline.")
        return

    # Train detector
    detector = train_detector(clauses)

    # Test the detector on a sample clause
    if clauses:
        print("\nTesting detector on sample clause...")
        sample = clauses[0]
        result = detector.predict(sample)
        print(f"  - Sample text: {sample['text'][:100]}...")
        print(f"  - Is outlier: {result['is_outlier']}")
        print(f"  - Anomaly score: {result['anomaly_score']:.4f}")
        print(f"  - Confidence: {result['confidence']:.4f}")

    # Save detector
    save_detector(detector, MODEL_SAVE_PATH)

    print("\n" + "=" * 60)
    print("Statistical detector initialized successfully!")
    print("=" * 60)
    print(f"\nThe detector will be automatically loaded on application startup.")
    print(f"Model saved to: {MODEL_SAVE_PATH}")

    # Cleanup
    await pinecone_service.close()


if __name__ == "__main__":
    asyncio.run(main())
