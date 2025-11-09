"""
Tests for AnomalyClusterer.

Tests the Stage 3 clustering and deduplication functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from app.core.anomaly_clusterer import AnomalyClusterer


class TestAnomalyClusterer:
    """Test suite for AnomalyClusterer."""

    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock SentenceTransformer."""
        mock = Mock()
        # Return embeddings with shape (n_samples, embedding_dim)
        mock.encode.return_value = np.random.rand(5, 384).astype(np.float32)
        return mock

    @pytest.fixture
    def mock_umap(self):
        """Mock UMAP reducer."""
        mock = Mock()
        # Return reduced embeddings with shape (n_samples, n_components)
        mock.fit_transform.return_value = np.random.rand(5, 5).astype(np.float32)
        return mock

    @pytest.fixture
    def mock_hdbscan(self):
        """Mock HDBSCAN clusterer."""
        mock = Mock()
        # Return cluster labels
        mock.fit_predict.return_value = np.array([0, 0, 1, 1, -1])
        return mock

    @pytest.fixture
    def clusterer_with_mocks(self, mock_sentence_transformer, mock_umap, mock_hdbscan):
        """Create clusterer with mocked dependencies."""
        with patch('app.core.anomaly_clusterer.SentenceTransformer') as mock_st_class, \
             patch('app.core.anomaly_clusterer.umap.UMAP') as mock_umap_class, \
             patch('app.core.anomaly_clusterer.hdbscan.HDBSCAN') as mock_hdbscan_class:

            mock_st_class.return_value = mock_sentence_transformer
            mock_umap_class.return_value = mock_umap
            mock_hdbscan_class.return_value = mock_hdbscan

            clusterer = AnomalyClusterer()
            return clusterer

    @pytest.fixture
    def sample_anomalies(self):
        """Create sample anomalies for testing."""
        return [
            {
                'clause_text': 'We may collect your personal data.',
                'section': 'Privacy',
                'clause_number': '1.1',
                'severity': 'high',
                'stage2_confidence': 0.9,
                'risk_category': 'data_collection'
            },
            {
                'clause_text': 'We may collect your personal information.',
                'section': 'Privacy',
                'clause_number': '1.2',
                'severity': 'high',
                'stage2_confidence': 0.85,
                'risk_category': 'data_collection'
            },
            {
                'clause_text': 'We can change terms at any time.',
                'section': 'Terms',
                'clause_number': '2.1',
                'severity': 'medium',
                'stage2_confidence': 0.75,
                'risk_category': 'unilateral_changes'
            },
            {
                'clause_text': 'You agree to binding arbitration.',
                'section': 'Disputes',
                'clause_number': '3.1',
                'severity': 'high',
                'stage2_confidence': 0.88,
                'risk_category': 'arbitration'
            },
            {
                'clause_text': 'We are not liable for any damages.',
                'section': 'Liability',
                'clause_number': '4.1',
                'severity': 'medium',
                'stage2_confidence': 0.70,
                'risk_category': 'liability'
            }
        ]

    def test_initialization_no_models(self):
        """Test initialization without models available."""
        with patch('app.core.anomaly_clusterer.SentenceTransformer', side_effect=ImportError):
            clusterer = AnomalyClusterer()
            assert clusterer.is_available == False

    def test_initialization_with_models(self, clusterer_with_mocks):
        """Test successful initialization with models."""
        assert clusterer_with_mocks.is_available == True
        assert clusterer_with_mocks.duplicate_threshold == 0.95

    def test_cluster_anomalies_empty_list(self, clusterer_with_mocks):
        """Test clustering with empty anomaly list."""
        result = clusterer_with_mocks.cluster_anomalies([])

        assert result['original_count'] == 0
        assert result['final_count'] == 0
        assert len(result['clusters']) == 0
        assert result['reduction_ratio'] == 0.0

    def test_cluster_anomalies_single_anomaly(self, sample_anomalies):
        """Test clustering with single anomaly."""
        # Use real clusterer (will use fallback if models not available)
        clusterer = AnomalyClusterer()

        result = clusterer.cluster_anomalies([sample_anomalies[0]])

        assert result['original_count'] == 1
        assert result['final_count'] == 1
        assert len(result['clusters']) == 1
        assert result['clusters'][0]['cluster_size'] == 1

    def test_cluster_anomalies_no_models_fallback(self, sample_anomalies):
        """Test fallback clustering when models not available."""
        # Force unavailable
        clusterer = AnomalyClusterer()
        clusterer.is_available = False

        result = clusterer.cluster_anomalies(sample_anomalies)

        assert result['fallback'] == True
        assert result['original_count'] == len(sample_anomalies)
        assert result['final_count'] == len(sample_anomalies)
        assert len(result['clusters']) == len(sample_anomalies)

    def test_generate_embeddings(self, clusterer_with_mocks, sample_anomalies):
        """Test embedding generation."""
        embeddings, anomalies_with_emb = clusterer_with_mocks._generate_embeddings(sample_anomalies)

        assert embeddings.shape[0] == len(sample_anomalies)
        assert len(anomalies_with_emb) == len(sample_anomalies)
        assert 'embedding' in anomalies_with_emb[0]

    def test_find_duplicates_no_duplicates(self, clusterer_with_mocks):
        """Test duplicate detection with no duplicates."""
        # Create embeddings that are dissimilar
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        anomalies = [{'id': i} for i in range(3)]

        duplicate_groups = clusterer_with_mocks._find_duplicates(embeddings, anomalies)

        assert len(duplicate_groups) == 0

    def test_find_duplicates_with_duplicates(self, clusterer_with_mocks):
        """Test duplicate detection with duplicates."""
        # Create embeddings with high similarity
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],  # Very similar to first
            [0.0, 0.0, 1.0]
        ])
        anomalies = [{'id': i} for i in range(3)]

        duplicate_groups = clusterer_with_mocks._find_duplicates(embeddings, anomalies)

        # Should find one duplicate group with indices 0 and 1
        assert len(duplicate_groups) >= 1
        # First group should contain first two anomalies
        assert 0 in duplicate_groups[0]
        assert 1 in duplicate_groups[0]

    def test_consolidate_duplicates_no_duplicates(self, clusterer_with_mocks, sample_anomalies):
        """Test consolidation with no duplicate groups."""
        duplicate_groups = []

        unique, mapping = clusterer_with_mocks._consolidate_duplicates(
            sample_anomalies,
            duplicate_groups
        )

        assert len(unique) == len(sample_anomalies)
        assert len(mapping) == len(sample_anomalies)

    def test_consolidate_duplicates_with_duplicates(self, clusterer_with_mocks, sample_anomalies):
        """Test consolidation with duplicate groups."""
        # Mark first two as duplicates
        duplicate_groups = [[0, 1]]

        unique, mapping = clusterer_with_mocks._consolidate_duplicates(
            sample_anomalies,
            duplicate_groups
        )

        # Should have 1 less anomaly (2 consolidated to 1)
        assert len(unique) == len(sample_anomalies) - 1

        # Check mapping
        assert len(mapping) == len(sample_anomalies)
        # Both 0 and 1 should map to same representative
        assert mapping[0] == mapping[1]

    def test_consolidate_duplicates_keeps_highest_confidence(self, clusterer_with_mocks):
        """Test that consolidation keeps highest confidence anomaly."""
        anomalies = [
            {'id': 0, 'stage2_confidence': 0.7, 'clause_text': 'text1'},
            {'id': 1, 'stage2_confidence': 0.9, 'clause_text': 'text2'},  # Highest
            {'id': 2, 'stage2_confidence': 0.8, 'clause_text': 'text3'}
        ]
        duplicate_groups = [[0, 1, 2]]

        unique, mapping = clusterer_with_mocks._consolidate_duplicates(
            anomalies,
            duplicate_groups
        )

        # Should keep anomaly with id=1 (highest confidence)
        assert len(unique) == 1
        assert unique[0]['id'] == 1
        assert unique[0]['stage2_confidence'] == 0.9

    def test_group_by_cluster(self, clusterer_with_mocks, sample_anomalies):
        """Test grouping anomalies by cluster labels."""
        labels = np.array([0, 0, 1, 1, -1])  # 2 clusters + 1 noise

        # Add embeddings to anomalies
        for anomaly in sample_anomalies:
            anomaly['embedding'] = np.random.rand(384)

        clusters, noise = clusterer_with_mocks._group_by_cluster(
            sample_anomalies,
            labels,
            {}
        )

        assert len(clusters) == 2  # 2 clusters
        assert len(noise) == 1  # 1 noise point
        assert clusters[0]['cluster_size'] == 2
        assert clusters[1]['cluster_size'] == 2

    def test_create_cluster_summary(self, clusterer_with_mocks, sample_anomalies):
        """Test cluster summary creation."""
        members = sample_anomalies[:2]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        assert summary['cluster_id'] == 'cluster_0'
        assert summary['cluster_size'] == 2
        assert 'representative_anomaly' in summary
        assert len(summary['member_anomalies']) == 2
        assert 'average_confidence' in summary
        assert 'overall_severity' in summary

    def test_create_cluster_summary_selects_highest_confidence(self, clusterer_with_mocks):
        """Test that cluster summary selects highest confidence as representative."""
        members = [
            {'id': 0, 'stage2_confidence': 0.7, 'clause_text': 'text1', 'severity': 'medium', 'risk_category': 'other', 'section': 'S1'},
            {'id': 1, 'stage2_confidence': 0.9, 'clause_text': 'text2', 'severity': 'high', 'risk_category': 'other', 'section': 'S2'},
            {'id': 2, 'stage2_confidence': 0.8, 'clause_text': 'text3', 'severity': 'medium', 'risk_category': 'other', 'section': 'S3'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        # Representative should be id=1 (highest confidence)
        assert summary['representative_anomaly']['id'] == 1

    def test_create_single_cluster_result(self, clusterer_with_mocks, sample_anomalies):
        """Test creating single cluster result."""
        unique = [sample_anomalies[0]]
        timing = {'total': 100.0}

        result = clusterer_with_mocks._create_single_cluster_result(
            unique,
            {},
            5,  # original_count
            timing
        )

        assert result['original_count'] == 5
        assert result['final_count'] == 1
        assert len(result['clusters']) == 1
        assert result['reduction_ratio'] == 0.8  # (5-1)/5

    def test_fallback_clustering(self, clusterer_with_mocks, sample_anomalies):
        """Test fallback clustering."""
        result = clusterer_with_mocks._fallback_clustering(sample_anomalies)

        assert result['fallback'] == True
        assert result['original_count'] == len(sample_anomalies)
        assert result['final_count'] == len(sample_anomalies)
        assert len(result['clusters']) == len(sample_anomalies)
        assert result['reduction_ratio'] == 0.0

    def test_get_cluster_statistics(self, clusterer_with_mocks):
        """Test getting cluster statistics."""
        clustering_result = {
            'clusters': [
                {'cluster_size': 3},
                {'cluster_size': 2},
                {'cluster_size': 1}
            ],
            'noise': [{'id': 1}, {'id': 2}],
            'reduction_ratio': 0.5
        }

        stats = clusterer_with_mocks.get_cluster_statistics(clustering_result)

        assert stats['n_clusters'] == 3
        assert stats['n_noise'] == 2
        assert stats['total_anomalies'] == 8  # 3+2+1+2
        assert stats['avg_cluster_size'] == 2.0  # (3+2+1)/3
        assert stats['max_cluster_size'] == 3
        assert stats['min_cluster_size'] == 1
        assert stats['reduction_ratio'] == 0.5

    def test_duplicate_threshold(self):
        """Test that duplicate threshold is configurable."""
        clusterer = AnomalyClusterer(duplicate_threshold=0.90)
        assert clusterer.duplicate_threshold == 0.90

    def test_umap_parameters(self):
        """Test that UMAP parameters are configurable."""
        clusterer = AnomalyClusterer(
            umap_n_neighbors=10,
            umap_n_components=3
        )
        assert clusterer.umap_n_neighbors == 10
        assert clusterer.umap_n_components == 3

    def test_hdbscan_parameters(self):
        """Test that HDBSCAN parameters are configurable."""
        clusterer = AnomalyClusterer(
            hdbscan_min_cluster_size=3,
            hdbscan_min_samples=2,
            hdbscan_cluster_selection_epsilon=0.3
        )
        assert clusterer.hdbscan_min_cluster_size == 3
        assert clusterer.hdbscan_min_samples == 2
        assert clusterer.hdbscan_cluster_selection_epsilon == 0.3

    def test_cluster_anomalies_timing(self, clusterer_with_mocks, sample_anomalies):
        """Test that clustering returns timing information."""
        # Mock embeddings to match sample size
        clusterer_with_mocks.sentence_transformer.encode.return_value = np.random.rand(len(sample_anomalies), 384)

        result = clusterer_with_mocks.cluster_anomalies(sample_anomalies)

        assert 'timing_ms' in result
        assert 'total' in result['timing_ms']
        assert result['timing_ms']['total'] > 0

    def test_consolidate_duplicates_marks_as_consolidated(self, clusterer_with_mocks, sample_anomalies):
        """Test that consolidated duplicates are marked."""
        duplicate_groups = [[0, 1]]

        unique, mapping = clusterer_with_mocks._consolidate_duplicates(
            sample_anomalies,
            duplicate_groups
        )

        # First unique anomaly should be marked as consolidated
        consolidated_anomaly = unique[0]
        assert consolidated_anomaly.get('is_consolidated') == True
        assert consolidated_anomaly.get('duplicate_count') == 2
        assert 'original_indices' in consolidated_anomaly

    def test_cluster_summary_includes_section_references(self, clusterer_with_mocks):
        """Test that cluster summary includes section references."""
        members = [
            {'section': 'Privacy', 'clause_text': 'text', 'stage2_confidence': 0.8, 'severity': 'high', 'risk_category': 'data'},
            {'section': 'Terms', 'clause_text': 'text2', 'stage2_confidence': 0.7, 'severity': 'medium', 'risk_category': 'other'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        assert 'section_references' in summary
        assert 'Privacy' in summary['section_references']
        assert 'Terms' in summary['section_references']

    def test_cluster_summary_includes_risk_categories(self, clusterer_with_mocks):
        """Test that cluster summary includes risk categories."""
        members = [
            {'risk_category': 'data_collection', 'clause_text': 'text', 'stage2_confidence': 0.8, 'severity': 'high', 'section': 'P'},
            {'risk_category': 'tracking', 'clause_text': 'text2', 'stage2_confidence': 0.7, 'severity': 'medium', 'section': 'T'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        assert 'risk_categories' in summary
        assert 'data_collection' in summary['risk_categories']
        assert 'tracking' in summary['risk_categories']

    def test_cluster_summary_overall_severity(self, clusterer_with_mocks):
        """Test that cluster summary selects highest severity."""
        members = [
            {'severity': 'low', 'clause_text': 'text', 'stage2_confidence': 0.8, 'risk_category': 'other', 'section': 'S'},
            {'severity': 'high', 'clause_text': 'text2', 'stage2_confidence': 0.7, 'risk_category': 'other', 'section': 'T'},
            {'severity': 'medium', 'clause_text': 'text3', 'stage2_confidence': 0.6, 'risk_category': 'other', 'section': 'U'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        assert summary['overall_severity'] == 'high'

    def test_reduction_ratio_calculation(self, clusterer_with_mocks, sample_anomalies):
        """Test reduction ratio calculation."""
        # Mock to return 2 clusters from 5 anomalies
        clusterer_with_mocks.sentence_transformer.encode.return_value = np.random.rand(5, 384)
        clusterer_with_mocks.hdbscan_clusterer.fit_predict.return_value = np.array([0, 0, 0, 1, 1])

        result = clusterer_with_mocks.cluster_anomalies(sample_anomalies)

        # Should reduce from 5 to 2 clusters = 60% reduction
        assert result['original_count'] == 5
        assert result['reduction_ratio'] > 0

    def test_empty_cluster_groups(self, clusterer_with_mocks):
        """Test handling of empty cluster groups."""
        anomalies = [
            {'id': 0, 'embedding': np.random.rand(384), 'stage2_confidence': 0.8, 'severity': 'high', 'risk_category': 'other', 'section': 'S', 'clause_text': 'text'}
        ]
        labels = np.array([-1])  # All noise

        clusters, noise = clusterer_with_mocks._group_by_cluster(anomalies, labels, {})

        assert len(clusters) == 0
        assert len(noise) == 1

    def test_cluster_anomalies_error_handling(self, clusterer_with_mocks, sample_anomalies):
        """Test error handling in cluster_anomalies."""
        # Force error by making encode fail
        clusterer_with_mocks.sentence_transformer.encode.side_effect = Exception("Encoding failed")

        result = clusterer_with_mocks.cluster_anomalies(sample_anomalies)

        # Should fall back to individual clusters
        assert result['fallback'] == True
        assert len(result['clusters']) == len(sample_anomalies)

    def test_consolidated_text_for_single_member(self, clusterer_with_mocks):
        """Test consolidated text for cluster with single member."""
        members = [
            {'clause_text': 'This is the clause text.', 'stage2_confidence': 0.8, 'severity': 'high', 'risk_category': 'other', 'section': 'Section 1'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        assert summary['consolidated_text'] == 'This is the clause text.'
        assert '[+' not in summary['consolidated_text']  # No additional members note

    def test_consolidated_text_for_multiple_members(self, clusterer_with_mocks):
        """Test consolidated text for cluster with multiple members."""
        members = [
            {'clause_text': 'Representative text.', 'stage2_confidence': 0.9, 'severity': 'high', 'risk_category': 'other', 'section': 'Section 1'},
            {'clause_text': 'Similar text.', 'stage2_confidence': 0.8, 'severity': 'medium', 'risk_category': 'other', 'section': 'Section 2'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        assert 'Representative text.' in summary['consolidated_text']
        assert '[+1 similar clause' in summary['consolidated_text']

    def test_average_confidence_calculation(self, clusterer_with_mocks):
        """Test average confidence calculation in cluster summary."""
        members = [
            {'stage2_confidence': 0.8, 'clause_text': 'text', 'severity': 'high', 'risk_category': 'other', 'section': 'S'},
            {'stage2_confidence': 0.6, 'clause_text': 'text2', 'severity': 'medium', 'risk_category': 'other', 'section': 'T'},
            {'stage2_confidence': 0.7, 'clause_text': 'text3', 'severity': 'low', 'risk_category': 'other', 'section': 'U'}
        ]

        summary = clusterer_with_mocks._create_cluster_summary(0, members)

        expected_avg = (0.8 + 0.6 + 0.7) / 3
        assert abs(summary['average_confidence'] - expected_avg) < 0.01

    def test_model_name_configuration(self):
        """Test that model name is configurable."""
        custom_model = 'custom-bert-model'
        clusterer = AnomalyClusterer(model_name=custom_model)
        assert clusterer.model_name == custom_model
