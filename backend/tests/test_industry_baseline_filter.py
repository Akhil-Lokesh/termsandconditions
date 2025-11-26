"""
Tests for IndustryBaselineFilter.

Tests the Stage 2 industry-specific baseline filtering functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from app.core.industry_baseline_filter import IndustryBaselineFilter


class TestIndustryBaselineFilter:
    """Test suite for IndustryBaselineFilter."""

    @pytest.fixture
    def filter(self):
        """Create a filter instance with mocked Pinecone."""
        mock_pinecone = Mock()
        return IndustryBaselineFilter(pinecone_index=mock_pinecone)

    @pytest.fixture
    def sample_embedding(self):
        """Create a sample embedding vector."""
        return np.random.rand(384).tolist()

    def test_initialization(self, filter):
        """Test filter initialization."""
        assert filter.pinecone_index is not None
        assert len(filter.INDUSTRY_MODIFIERS) == 9
        assert 'children_apps' in filter.INDUSTRY_MODIFIERS
        assert 'streaming' in filter.INDUSTRY_MODIFIERS

    def test_industry_modifiers_structure(self, filter):
        """Test that industry modifiers have correct structure."""
        required_keys = ['modifier', 'strict_categories', 'required_clauses', 'prohibited_terms']

        for industry, config in filter.INDUSTRY_MODIFIERS.items():
            for key in required_keys:
                assert key in config, f"Industry {industry} missing key: {key}"

            # Check modifier is a valid number
            assert isinstance(config['modifier'], (int, float))
            assert 1.0 <= config['modifier'] <= 3.0

            # Check lists are actually lists
            assert isinstance(config['strict_categories'], list)
            assert isinstance(config['required_clauses'], list)
            assert isinstance(config['prohibited_terms'], list)

    def test_industry_modifier_values(self, filter):
        """Test that industry modifiers are in expected range."""
        modifiers = filter.INDUSTRY_MODIFIERS

        # Children apps should have highest modifier
        assert modifiers['children_apps']['modifier'] == 3.0

        # Streaming should have lowest modifier
        assert modifiers['streaming']['modifier'] == 1.0

        # Health should be high
        assert modifiers['health_apps']['modifier'] >= 2.0

        # Financial should be high
        assert modifiers['financial_apps']['modifier'] >= 2.0

    def test_strict_categories_present(self, filter):
        """Test that strict categories are defined for high-risk industries."""
        # Children apps should have multiple strict categories
        children_config = filter.INDUSTRY_MODIFIERS['children_apps']
        assert len(children_config['strict_categories']) >= 5
        assert 'data_collection' in children_config['strict_categories']
        assert 'data_selling' in children_config['strict_categories']

        # Health apps should have strict categories
        health_config = filter.INDUSTRY_MODIFIERS['health_apps']
        assert len(health_config['strict_categories']) >= 4
        assert 'data_selling' in health_config['strict_categories']

    def test_required_clauses_present(self, filter):
        """Test that required clauses are defined for regulated industries."""
        # Children apps should have required clauses
        children_config = filter.INDUSTRY_MODIFIERS['children_apps']
        assert len(children_config['required_clauses']) > 0

        # Health apps should have HIPAA-related requirements
        health_config = filter.INDUSTRY_MODIFIERS['health_apps']
        assert len(health_config['required_clauses']) > 0

    def test_prohibited_terms_present(self, filter):
        """Test that prohibited terms are defined."""
        # Children apps should have prohibited terms
        children_config = filter.INDUSTRY_MODIFIERS['children_apps']
        assert len(children_config['prohibited_terms']) > 0

        # Dating apps should have prohibited terms
        dating_config = filter.INDUSTRY_MODIFIERS['dating_apps']
        assert len(dating_config['prohibited_terms']) > 0

    @pytest.mark.asyncio
    async def test_calculate_prevalence_common_clause(self, filter, sample_embedding):
        """Test prevalence calculation for common clause."""
        # Mock Pinecone query to return many similar clauses
        mock_matches = [
            Mock(id=f"doc{i}_clause{j}", score=0.90, metadata={'document_id': f'doc{i}'})
            for i in range(1, 11)  # 10 documents
            for j in range(1, 4)   # 3 clauses each
        ]

        filter.pinecone_index.query = AsyncMock(return_value=Mock(matches=mock_matches))

        result = await filter.calculate_prevalence(
            clause_embedding=sample_embedding,
            industry='saas',
            category='termination'
        )

        assert isinstance(result, dict)
        assert 'prevalence' in result
        assert 'found_in_count' in result
        assert 'total_baseline_count' in result
        assert 'is_common' in result

        # Should be common (found in 10 documents out of 15 baseline)
        assert result['is_common'] == True
        assert result['found_in_count'] == 10

    @pytest.mark.asyncio
    async def test_calculate_prevalence_rare_clause(self, filter, sample_embedding):
        """Test prevalence calculation for rare clause."""
        # Mock Pinecone query to return few similar clauses
        mock_matches = [
            Mock(id=f"doc{i}_clause1", score=0.90, metadata={'document_id': f'doc{i}'})
            for i in range(1, 3)  # Only 2 documents
        ]

        filter.pinecone_index.query = AsyncMock(return_value=Mock(matches=mock_matches))

        result = await filter.calculate_prevalence(
            clause_embedding=sample_embedding,
            industry='children_apps',
            category='data_selling'
        )

        # Should be rare (found in only 2 documents)
        assert result['is_common'] == False
        assert result['found_in_count'] == 2
        assert result['prevalence'] < 0.30

    @pytest.mark.asyncio
    async def test_calculate_prevalence_no_matches(self, filter, sample_embedding):
        """Test prevalence calculation with no matches."""
        # Mock Pinecone query to return no matches above threshold
        mock_matches = [
            Mock(id="doc1_clause1", score=0.50, metadata={'document_id': 'doc1'}),  # Below 0.85
            Mock(id="doc2_clause1", score=0.60, metadata={'document_id': 'doc2'})   # Below 0.85
        ]

        filter.pinecone_index.query = AsyncMock(return_value=Mock(matches=mock_matches))

        result = await filter.calculate_prevalence(
            clause_embedding=sample_embedding,
            industry='gaming',
            category='liability'
        )

        # Should find zero matches above threshold
        assert result['found_in_count'] == 0
        assert result['prevalence'] == 0.0
        assert result['is_common'] == False

    @pytest.mark.asyncio
    async def test_calculate_prevalence_error_handling(self, filter, sample_embedding):
        """Test prevalence calculation error handling."""
        # Mock Pinecone query to raise exception
        filter.pinecone_index.query = AsyncMock(side_effect=Exception("Pinecone error"))

        result = await filter.calculate_prevalence(
            clause_embedding=sample_embedding,
            industry='saas',
            category='termination'
        )

        # Should return default values on error
        assert result['prevalence'] == 0.0
        assert result['found_in_count'] == 0
        assert 'error' in result

    def test_apply_industry_modifier_common_clause(self, filter):
        """Test industry modifier for common clause."""
        result = filter.apply_industry_modifier(
            base_risk_score=0.8,
            industry='streaming',
            category='termination',
            prevalence=0.75,  # Common
            clause_text='You may cancel your subscription at any time.'
        )

        assert isinstance(result, dict)
        assert 'base_score' in result
        assert 'industry_modifier' in result
        assert 'adjusted_score' in result
        assert 'reasoning' in result

        # Common clause in streaming (low modifier) should have reduced score
        assert result['adjusted_score'] < result['base_score']
        assert result['industry_modifier'] < 1.0

    def test_apply_industry_modifier_rare_strict_category(self, filter):
        """Test industry modifier for rare clause in strict category."""
        result = filter.apply_industry_modifier(
            base_risk_score=0.8,
            industry='children_apps',
            category='data_selling',  # Strict category for children apps
            prevalence=0.15,  # Rare
            clause_text='We may share data with partners.'
        )

        # Rare clause in strict category for children apps should have increased score
        assert result['adjusted_score'] > result['base_score']
        assert result['industry_modifier'] > 3.0  # Base 3.0 + prevalence 1.3x + strict 1.5x

    def test_apply_industry_modifier_prohibited_terms(self, filter):
        """Test industry modifier with prohibited terms."""
        result = filter.apply_industry_modifier(
            base_risk_score=0.7,
            industry='children_apps',
            category='tracking',
            prevalence=0.50,
            clause_text='We track your child location and sell children data to advertisers.'
        )

        # Should detect prohibited terms and increase modifier
        assert result['adjusted_score'] > result['base_score']
        # Should mention prohibited terms in reasoning
        assert 'prohibited terms' in result['reasoning'].lower()

    def test_apply_industry_modifier_invalid_industry(self, filter):
        """Test industry modifier with invalid industry."""
        result = filter.apply_industry_modifier(
            base_risk_score=0.8,
            industry='invalid_industry',
            category='termination',
            prevalence=0.50,
            clause_text='Standard termination clause.'
        )

        # Should fall back to 1.0 modifier for unknown industry
        assert result['industry_modifier'] >= 1.0
        assert 'unknown industry' in result['reasoning'].lower()

    def test_apply_industry_modifier_score_capping(self, filter):
        """Test that adjusted score is capped at 10.0."""
        result = filter.apply_industry_modifier(
            base_risk_score=9.5,
            industry='children_apps',
            category='data_selling',
            prevalence=0.05,  # Very rare
            clause_text='We sell children data and track location without consent.'
        )

        # Should be capped at 10.0
        assert result['adjusted_score'] <= 10.0

    def test_apply_industry_modifier_medium_prevalence(self, filter):
        """Test industry modifier with medium prevalence (30-70%)."""
        result = filter.apply_industry_modifier(
            base_risk_score=0.7,
            industry='saas',
            category='auto_renewal',
            prevalence=0.50,  # Medium
            clause_text='Subscription automatically renews.'
        )

        # Medium prevalence should use base industry modifier (1.3x for SaaS)
        assert 1.2 <= result['industry_modifier'] <= 1.5

    def test_check_required_clauses(self, filter):
        """Test checking for required clauses."""
        # Test with children apps
        result = filter.check_required_clauses(
            industry='children_apps',
            document_clauses=['privacy policy', 'parental consent required', 'data deletion']
        )

        assert isinstance(result, dict)
        assert 'missing_clauses' in result
        assert 'has_all_required' in result

    def test_get_category_strictness(self, filter):
        """Test getting category strictness level."""
        # Strict category for children apps
        strictness = filter.get_category_strictness('children_apps', 'data_selling')
        assert strictness == 'strict'

        # Non-strict category
        strictness = filter.get_category_strictness('streaming', 'termination')
        assert strictness == 'normal'

        # Invalid industry
        strictness = filter.get_category_strictness('invalid', 'data_selling')
        assert strictness == 'normal'

    def test_explain_industry_expectations(self, filter):
        """Test explaining industry expectations."""
        explanation = filter.explain_industry_expectations('children_apps')

        assert isinstance(explanation, dict)
        assert 'industry' in explanation
        assert 'base_modifier' in explanation
        assert 'strict_categories' in explanation
        assert 'required_clauses' in explanation
        assert 'prohibited_terms' in explanation

        assert explanation['industry'] == 'children_apps'
        assert explanation['base_modifier'] == 3.0

    def test_explain_industry_expectations_invalid(self, filter):
        """Test explaining expectations for invalid industry."""
        explanation = filter.explain_industry_expectations('invalid_industry')

        # Should return default/empty explanation
        assert explanation['industry'] == 'invalid_industry'
        assert 'error' in explanation or explanation['base_modifier'] == 1.0

    def test_all_industries_have_complete_config(self, filter):
        """Test that all industries have complete configuration."""
        for industry in ['children_apps', 'health_apps', 'financial_apps',
                        'dating_apps', 'social_media', 'gaming',
                        'saas', 'ecommerce', 'streaming']:
            config = filter.INDUSTRY_MODIFIERS[industry]

            # All should have valid modifier
            assert 1.0 <= config['modifier'] <= 3.0

            # All should have lists (even if empty)
            assert isinstance(config['strict_categories'], list)
            assert isinstance(config['required_clauses'], list)
            assert isinstance(config['prohibited_terms'], list)

    @pytest.mark.asyncio
    async def test_calculate_prevalence_unique_documents(self, filter, sample_embedding):
        """Test that prevalence counts unique documents, not total clauses."""
        # Mock Pinecone to return multiple clauses from same documents
        mock_matches = [
            Mock(id="doc1_clause1", score=0.90, metadata={'document_id': 'doc1'}),
            Mock(id="doc1_clause2", score=0.88, metadata={'document_id': 'doc1'}),
            Mock(id="doc1_clause3", score=0.87, metadata={'document_id': 'doc1'}),
            Mock(id="doc2_clause1", score=0.91, metadata={'document_id': 'doc2'}),
            Mock(id="doc2_clause2", score=0.89, metadata={'document_id': 'doc2'}),
        ]

        filter.pinecone_index.query = AsyncMock(return_value=Mock(matches=mock_matches))

        result = await filter.calculate_prevalence(
            clause_embedding=sample_embedding,
            industry='saas',
            category='termination'
        )

        # Should count only 2 unique documents, not 5 clauses
        assert result['found_in_count'] == 2

    def test_apply_industry_modifier_reasoning_detail(self, filter):
        """Test that reasoning provides detailed explanation."""
        result = filter.apply_industry_modifier(
            base_risk_score=0.8,
            industry='health_apps',
            category='data_selling',
            prevalence=0.20,  # Rare
            clause_text='Patient data may be sold to research companies.'
        )

        reasoning = result['reasoning'].lower()

        # Should mention industry
        assert 'health' in reasoning

        # Should mention prevalence adjustment
        assert 'rare' in reasoning or 'prevalence' in reasoning

        # Should mention strict category if applicable
        if 'data_selling' in filter.INDUSTRY_MODIFIERS['health_apps']['strict_categories']:
            assert 'strict' in reasoning

    def test_prevalence_threshold_boundary(self, filter):
        """Test prevalence threshold boundaries (30% and 70%)."""
        # Just below common threshold (70%)
        result1 = filter.apply_industry_modifier(
            base_risk_score=0.7,
            industry='saas',
            category='termination',
            prevalence=0.69,
            clause_text='Standard clause.'
        )

        # Just above common threshold (70%)
        result2 = filter.apply_industry_modifier(
            base_risk_score=0.7,
            industry='saas',
            category='termination',
            prevalence=0.71,
            clause_text='Standard clause.'
        )

        # Common clause should have lower score
        assert result2['adjusted_score'] < result1['adjusted_score']

    @pytest.mark.asyncio
    async def test_calculate_prevalence_filter_parameters(self, filter, sample_embedding):
        """Test that prevalence calculation uses correct filter parameters."""
        mock_query = AsyncMock(return_value=Mock(matches=[]))
        filter.pinecone_index.query = mock_query

        await filter.calculate_prevalence(
            clause_embedding=sample_embedding,
            industry='gaming',
            category='liability'
        )

        # Verify query was called with correct parameters
        call_args = mock_query.call_args
        assert call_args is not None

        # Check that filter includes industry and category
        if 'filter' in call_args.kwargs:
            filter_dict = call_args.kwargs['filter']
            assert 'industry' in str(filter_dict).lower() or 'category' in str(filter_dict).lower()
