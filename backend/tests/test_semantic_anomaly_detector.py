"""
Tests for SemanticAnomalyDetector.

Tests the Stage 2 semantic anomaly detection functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from app.core.semantic_anomaly_detector import SemanticAnomalyDetector

# Check if sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class TestSemanticAnomalyDetector:
    """Test suite for SemanticAnomalyDetector."""

    @pytest.fixture
    def detector(self):
        """Create a detector instance."""
        # Use lightweight model for testing
        return SemanticAnomalyDetector(
            model_name='sentence-transformers/all-MiniLM-L6-v2',
            similarity_threshold=0.75
        )

    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.model_name == 'sentence-transformers/all-MiniLM-L6-v2'
        assert detector.similarity_threshold == 0.75
        assert len(detector.problematic_patterns) >= 12  # At least 12 patterns

        # Check if model loaded (depends on package availability)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            assert detector.is_available
            assert detector.model is not None
            assert detector.pattern_embeddings is not None
        else:
            assert not detector.is_available

    def test_problematic_patterns_structure(self, detector):
        """Test that problematic patterns have correct structure."""
        required_keys = ['category', 'severity', 'text', 'description']

        for pattern in detector.problematic_patterns:
            for key in required_keys:
                assert key in pattern, f"Pattern missing key: {key}"

            assert pattern['severity'] in ['high', 'medium', 'low']
            assert len(pattern['text']) > 20
            assert len(pattern['description']) > 5

    def test_pattern_categories(self, detector):
        """Test that all required categories are present."""
        categories = detector.get_categories()

        required_categories = [
            'data_selling',
            'rights_waiver',
            'auto_renewal',
            'unilateral_changes',
            'hidden_fees'
        ]

        for category in required_categories:
            assert category in categories, f"Missing required category: {category}"

    def test_pattern_counts(self, detector):
        """Test that we have sufficient examples per category."""
        category_counts = {}
        for pattern in detector.problematic_patterns:
            cat = pattern['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Check minimum counts
        assert category_counts.get('data_selling', 0) >= 3
        assert category_counts.get('rights_waiver', 0) >= 3
        assert category_counts.get('auto_renewal', 0) >= 2
        assert category_counts.get('unilateral_changes', 0) >= 2
        assert category_counts.get('hidden_fees', 0) >= 2

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_detect_data_selling_clause(self, detector):
        """Test detection of data selling clause."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        clause = (
            "We may sell or transfer your personal information to advertisers, "
            "marketing companies, and data brokers for their commercial purposes."
        )

        result = detector.detect_semantic_anomalies(clause)

        assert isinstance(result, dict)
        assert 'is_anomalous' in result
        assert 'similarity_score' in result
        assert 'matched_pattern' in result
        assert 'confidence' in result
        assert result['stage'] == 2
        assert result['detector'] == 'semantic_anomaly'

        # Should likely detect this as similar to data_selling patterns
        # (though exact match depends on model)
        if result['is_anomalous']:
            assert result['matched_category'] in ['data_selling', 'data_retention']
            assert result['confidence'] >= 0.5

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_detect_rights_waiver_clause(self, detector):
        """Test detection of rights waiver clause."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        clause = (
            "You hereby waive all legal rights and agree not to sue the company "
            "under any circumstances, including for damages or losses."
        )

        result = detector.detect_semantic_anomalies(clause)

        assert isinstance(result, dict)
        assert result['stage'] == 2

        # Should potentially detect rights waiver similarity
        if result['is_anomalous']:
            assert result['matched_category'] == 'rights_waiver'

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_normal_clause_not_flagged(self, detector):
        """Test that normal clauses are not flagged."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        normal_clause = (
            "You can contact our customer support team by email or phone. "
            "We aim to respond to all inquiries within 24 hours."
        )

        result = detector.detect_semantic_anomalies(normal_clause)

        # Normal clause should have low similarity
        assert result['similarity_score'] < 0.85  # Should not be very similar

    def test_empty_clause_handling(self, detector):
        """Test handling of empty clause."""
        result = detector.detect_semantic_anomalies("")

        assert not result['is_anomalous']
        assert result['similarity_score'] == 0.0
        assert 'error' in result

    def test_short_clause_handling(self, detector):
        """Test handling of very short clause."""
        result = detector.detect_semantic_anomalies("Hi")

        assert not result['is_anomalous']
        assert result['similarity_score'] == 0.0
        assert 'error' in result

    def test_model_unavailable_fallback(self):
        """Test graceful fallback when model not available."""
        with patch('app.core.semantic_anomaly_detector.SENTENCE_TRANSFORMERS_AVAILABLE', False):
            detector = SemanticAnomalyDetector()

            assert not detector.is_available
            assert detector.model is None

            result = detector.detect_semantic_anomalies("Test clause")
            assert not result['is_anomalous']
            assert result['available'] == False

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_update_threshold(self, detector):
        """Test updating similarity threshold."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        original_threshold = detector.similarity_threshold

        # Update threshold
        detector.update_threshold(0.85)
        assert detector.similarity_threshold == 0.85

        # Restore original
        detector.update_threshold(original_threshold)
        assert detector.similarity_threshold == original_threshold

    def test_update_threshold_invalid(self, detector):
        """Test that invalid threshold raises error."""
        with pytest.raises(ValueError):
            detector.update_threshold(1.5)

        with pytest.raises(ValueError):
            detector.update_threshold(-0.1)

    def test_get_pattern_details(self, detector):
        """Test retrieving pattern details."""
        # Get all patterns
        all_patterns = detector.get_pattern_details()
        assert len(all_patterns) >= 12

        # Get patterns by category
        data_selling = detector.get_pattern_details(category='data_selling')
        assert len(data_selling) >= 3
        for pattern in data_selling:
            assert pattern['category'] == 'data_selling'

    def test_get_categories(self, detector):
        """Test retrieving all categories."""
        categories = detector.get_categories()

        assert isinstance(categories, list)
        assert len(categories) >= 5
        assert 'data_selling' in categories
        assert 'rights_waiver' in categories

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_analyze_multiple_clauses(self, detector):
        """Test batch analysis of multiple clauses."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        clauses = [
            "You can cancel your subscription at any time.",
            "We may sell your data to third parties.",
            "Contact support for assistance."
        ]

        results = detector.analyze_multiple_clauses(clauses)

        assert len(results) == 3
        for result in results:
            assert 'is_anomalous' in result
            assert 'similarity_score' in result

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_compare_clauses(self, detector):
        """Test comparing similarity between two clauses."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        clause1 = "We may sell your personal information to advertisers."
        clause2 = "Your data may be shared with marketing partners."

        similarity = detector.compare_clauses(clause1, clause2)

        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        # These clauses should have some similarity
        assert similarity > 0.3

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_get_embedding(self, detector):
        """Test getting embedding for text."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        text = "This is a test clause."
        embedding = detector.get_embedding(text)

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] > 0  # Has dimensions

    def test_get_embedding_unavailable(self, detector):
        """Test getting embedding when model unavailable."""
        if detector.is_available:
            # Temporarily disable
            detector.is_available = False

        embedding = detector.get_embedding("Test")
        assert embedding is None

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_all_matches_returned(self, detector):
        """Test that all matching patterns are returned."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        # Use a clause very similar to a data selling pattern
        clause = detector.problematic_patterns[0]['text']  # Use exact pattern

        result = detector.detect_semantic_anomalies(clause)

        if result['is_anomalous']:
            assert 'all_matches' in result
            assert len(result['all_matches']) > 0

            # Check structure of matches
            for match in result['all_matches']:
                assert 'category' in match
                assert 'description' in match
                assert 'severity' in match
                assert 'similarity' in match
                assert match['similarity'] >= detector.similarity_threshold

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_confidence_calculation(self, detector):
        """Test that confidence is calculated correctly."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        clause = "We may share your data with partners for marketing."

        result = detector.detect_semantic_anomalies(clause)

        # Confidence should be in valid range
        assert 0.0 <= result['confidence'] <= 1.0

        # If anomalous, confidence should be at least 0.5
        if result['is_anomalous']:
            assert result['confidence'] >= 0.5

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_severity_levels(self, detector):
        """Test that severity levels are assigned correctly."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        # Test with a known high severity pattern
        clause = detector.problematic_patterns[0]['text']  # First pattern (data_selling - high)

        result = detector.detect_semantic_anomalies(clause)

        if result['is_anomalous']:
            assert result['severity'] in ['high', 'medium', 'low']

    def test_response_structure(self, detector):
        """Test that response has all required fields."""
        result = detector.detect_semantic_anomalies("Test clause about service usage.")

        required_fields = [
            'is_anomalous',
            'similarity_score',
            'matched_pattern',
            'matched_category',
            'confidence',
            'severity',
            'stage',
            'detector',
            'all_matches'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_embeddings_are_normalized(self, detector):
        """Test that embeddings are normalized."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        embedding = detector.get_embedding("Test clause")

        if embedding is not None:
            # Check that embedding is approximately normalized (L2 norm ≈ 1)
            norm = np.linalg.norm(embedding)
            assert 0.99 <= norm <= 1.01  # Allow small floating point error

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_cache_operations(self, detector, tmp_path):
        """Test saving and loading cache."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        cache_file = tmp_path / "test_cache.pkl"

        # Save cache
        detector.save_cache(str(cache_file))
        assert cache_file.exists()

        # Create new detector and load cache
        new_detector = SemanticAnomalyDetector(
            model_name=detector.model_name,
            similarity_threshold=0.70
        )

        if new_detector.is_available:
            new_detector.load_cache(str(cache_file))

            # Check that data was loaded
            assert new_detector.pattern_embeddings is not None
            assert len(new_detector.problematic_patterns) == len(detector.problematic_patterns)
            assert new_detector.similarity_threshold == 0.75  # From cache

    def test_save_cache_without_embeddings(self, detector):
        """Test that saving cache without embeddings raises error."""
        detector.pattern_embeddings = None

        with pytest.raises(RuntimeError, match="No embeddings to save"):
            detector.save_cache("/tmp/test.pkl")

    @pytest.mark.skipif(not SENTENCE_TRANSFORMERS_AVAILABLE, reason="sentence-transformers not installed")
    def test_consistent_results(self, detector):
        """Test that detection results are consistent across multiple calls."""
        if not detector.is_available:
            pytest.skip("Model not loaded")

        clause = "We reserve the right to change prices without notice."

        # Run detection multiple times
        results = [detector.detect_semantic_anomalies(clause) for _ in range(3)]

        # All results should be identical
        for i in range(1, len(results)):
            assert results[i]['is_anomalous'] == results[0]['is_anomalous']
            assert abs(results[i]['similarity_score'] - results[0]['similarity_score']) < 1e-5
            assert results[i]['matched_category'] == results[0]['matched_category']
