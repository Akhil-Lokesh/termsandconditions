"""
Industry Baseline Filter for Context-Aware Risk Adjustment.

Adjusts risk scores based on industry-specific baselines and expectations.
Stage 2 of the multi-stage anomaly detection pipeline.

Different industries have different norms and regulatory requirements:
- Children's apps: Extremely strict on privacy (COPPA)
- Health apps: Strict on data security (HIPAA)
- Financial apps: Strict on liability and security
- Dating apps: Strict on location tracking and data selling
- Social media: Moderate expectations
- Gaming: More lenient on virtual goods
- SaaS: Standard business expectations
- E-commerce: Consumer protection focused
- Streaming: Baseline (most lenient)
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from app.services.pinecone_service import PineconeService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class IndustryBaselineFilter:
    """
    Filters and adjusts risk scores based on industry-specific baselines.

    Uses industry-specific modifiers and baseline prevalence data to
    provide context-aware risk assessment.
    """

    # Industry-specific modifiers and rules
    INDUSTRY_MODIFIERS = {
        'children_apps': {
            'modifier': 3.0,
            'strict_categories': [
                'data_collection', 'data_selling', 'tracking', 'location_tracking',
                'biometric_data', 'contact_harvesting', 'keystroke_monitoring',
                'children_data_violation'
            ],
            'required_clauses': [
                'parental_consent', 'data_deletion', 'coppa_compliance'
            ],
            'prohibited_terms': [
                'sell children data', 'share with advertisers', 'location tracking',
                'biometric', 'behavioral tracking', 'third party marketing'
            ],
            'description': 'Children\'s apps (COPPA compliance required)'
        },
        'health_apps': {
            'modifier': 2.5,
            'strict_categories': [
                'data_selling', 'data_sharing', 'privacy', 'data_retention',
                'cross_border_data_transfer', 'liability_limitation'
            ],
            'required_clauses': [
                'hipaa_compliance', 'data_encryption', 'breach_notification'
            ],
            'prohibited_terms': [
                'sell health data', 'share medical information', 'no liability for breach',
                'transfer to foreign country'
            ],
            'description': 'Health apps (HIPAA compliance required)'
        },
        'financial_apps': {
            'modifier': 2.2,
            'strict_categories': [
                'liability_limitation', 'data_selling', 'auto_payment',
                'hidden_fees', 'rights_waiver', 'arbitration'
            ],
            'required_clauses': [
                'fraud_protection', 'dispute_resolution', 'fee_disclosure'
            ],
            'prohibited_terms': [
                'no liability for loss', 'automatic charges', 'waive fraud protection',
                'hidden fees', 'undisclosed charges'
            ],
            'description': 'Financial apps (strict liability and security)'
        },
        'dating_apps': {
            'modifier': 2.0,
            'strict_categories': [
                'location_tracking', 'data_selling', 'data_sharing',
                'biometric_data', 'privacy'
            ],
            'required_clauses': [
                'profile_deletion', 'location_control', 'blocking_features'
            ],
            'prohibited_terms': [
                'always track location', 'sell dating data', 'share with partners',
                'facial recognition without consent'
            ],
            'description': 'Dating apps (strict on location and privacy)'
        },
        'social_media': {
            'modifier': 1.8,
            'strict_categories': [
                'data_selling', 'content_ownership', 'monitoring',
                'biometric_data', 'children_data_violation'
            ],
            'required_clauses': [
                'data_portability', 'account_deletion', 'content_removal'
            ],
            'prohibited_terms': [
                'sell your content', 'perpetual ownership', 'facial recognition for ads'
            ],
            'description': 'Social media platforms'
        },
        'gaming': {
            'modifier': 1.5,
            'strict_categories': [
                'auto_payment', 'hidden_fees', 'children_data_violation',
                'virtual_goods_loss'
            ],
            'required_clauses': [
                'refund_policy', 'parental_controls'
            ],
            'prohibited_terms': [
                'all purchases final', 'no refunds on virtual goods without disclosure'
            ],
            'description': 'Gaming platforms and apps'
        },
        'saas': {
            'modifier': 1.3,
            'strict_categories': [
                'data_loss', 'liability_limitation', 'unilateral_changes',
                'auto_renewal'
            ],
            'required_clauses': [
                'sla', 'data_backup', 'termination_notice'
            ],
            'prohibited_terms': [
                'delete data without notice', 'change price anytime', 'no sla'
            ],
            'description': 'Software-as-a-Service platforms'
        },
        'ecommerce': {
            'modifier': 1.2,
            'strict_categories': [
                'no_refund', 'hidden_fees', 'auto_renewal',
                'liability_limitation'
            ],
            'required_clauses': [
                'return_policy', 'shipping_terms', 'payment_security'
            ],
            'prohibited_terms': [
                'all sales final', 'no refunds', 'surprise shipping fees'
            ],
            'description': 'E-commerce platforms'
        },
        'streaming': {
            'modifier': 1.0,
            'strict_categories': [],
            'required_clauses': [
                'cancellation_policy', 'content_availability'
            ],
            'prohibited_terms': [],
            'description': 'Streaming services (baseline)'
        }
    }

    def __init__(self, pinecone_service: Optional[PineconeService] = None):
        """
        Initialize the Industry Baseline Filter.

        Args:
            pinecone_service: Pinecone service for baseline queries
        """
        self.pinecone = pinecone_service
        self.similarity_threshold = 0.85  # For prevalence matching

        logger.info(f"IndustryBaselineFilter initialized with {len(self.INDUSTRY_MODIFIERS)} industries")

    def get_industry_info(self, industry: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an industry.

        Args:
            industry: Industry identifier

        Returns:
            Industry configuration dict or None if not found
        """
        return self.INDUSTRY_MODIFIERS.get(industry)

    def list_industries(self) -> List[str]:
        """
        Get list of all supported industries.

        Returns:
            List of industry identifiers
        """
        return list(self.INDUSTRY_MODIFIERS.keys())

    async def calculate_prevalence(
        self,
        clause_embedding: np.ndarray,
        industry: str,
        category: str,
        namespace: str = "baseline"
    ) -> Dict[str, Any]:
        """
        Calculate prevalence of a clause in industry baseline.

        Queries Pinecone baseline namespace to find similar clauses
        within the specified industry and category.

        Args:
            clause_embedding: Embedding vector of the clause
            industry: Industry identifier
            category: Risk category
            namespace: Pinecone namespace (default: "baseline")

        Returns:
            Dictionary containing:
                - prevalence (float): 0-1, percentage of baseline with similar clause
                - found_in_count (int): Number of documents with similar clause
                - total_baseline_count (int): Total documents in industry baseline
                - similar_clauses (list): List of similar clauses found
                - is_common (bool): True if prevalence >= 0.30
                - industry (str): Industry queried
                - category (str): Category queried
        """
        if self.pinecone is None:
            logger.warning("Pinecone service not available, returning default prevalence")
            return {
                'prevalence': 0.5,
                'found_in_count': 0,
                'total_baseline_count': 0,
                'similar_clauses': [],
                'is_common': True,
                'industry': industry,
                'category': category,
                'error': 'Pinecone not available'
            }

        try:
            # Query Pinecone for similar clauses in this industry + category
            query_filter = {
                'industry': industry,
                'category': category
            }

            logger.debug(f"Querying baseline: industry={industry}, category={category}")

            # Search for similar clauses
            similar_results = await self.pinecone.search(
                embedding=clause_embedding,
                namespace=namespace,
                filter=query_filter,
                top_k=100  # Get more results to count unique documents
            )

            # Filter by similarity threshold
            similar_clauses = [
                r for r in similar_results
                if r.get('score', 0) >= self.similarity_threshold
            ]

            # Count unique documents (not just clauses)
            unique_docs = set()
            for clause in similar_clauses:
                doc_id = clause.get('metadata', {}).get('document_id')
                if doc_id:
                    unique_docs.add(doc_id)

            found_in_count = len(unique_docs)

            # Get total baseline count for this industry
            # This would ideally come from metadata or a separate query
            # For now, we'll estimate based on typical corpus sizes
            baseline_counts = {
                'children_apps': 20,
                'health_apps': 15,
                'financial_apps': 20,
                'dating_apps': 10,
                'social_media': 15,
                'gaming': 15,
                'saas': 25,
                'ecommerce': 25,
                'streaming': 15
            }
            total_baseline_count = baseline_counts.get(industry, 20)

            # Calculate prevalence
            prevalence = found_in_count / total_baseline_count if total_baseline_count > 0 else 0.0

            # Determine if common
            is_common = prevalence >= 0.30

            logger.info(
                f"Prevalence for {industry}/{category}: {prevalence:.2%} "
                f"({found_in_count}/{total_baseline_count} documents)"
            )

            return {
                'prevalence': prevalence,
                'found_in_count': found_in_count,
                'total_baseline_count': total_baseline_count,
                'similar_clauses': similar_clauses[:10],  # Return top 10
                'is_common': is_common,
                'industry': industry,
                'category': category
            }

        except Exception as e:
            logger.error(f"Error calculating prevalence: {e}", exc_info=True)
            return {
                'prevalence': 0.5,  # Default to medium
                'found_in_count': 0,
                'total_baseline_count': 0,
                'similar_clauses': [],
                'is_common': True,
                'industry': industry,
                'category': category,
                'error': str(e)
            }

    def apply_industry_modifier(
        self,
        base_risk_score: float,
        industry: str,
        category: str,
        prevalence: float,
        clause_text: str = ""
    ) -> Dict[str, Any]:
        """
        Apply industry-specific modifier to risk score.

        Adjusts the base risk score based on:
        - Industry baseline expectations
        - Prevalence in industry
        - Category strictness
        - Prohibited terms

        Args:
            base_risk_score: Base risk score (0-10)
            industry: Industry identifier
            category: Risk category
            prevalence: Prevalence in industry baseline (0-1)
            clause_text: Optional clause text for prohibited term checking

        Returns:
            Dictionary containing:
                - base_score (float): Original score
                - industry_modifier (float): Calculated modifier
                - adjusted_score (float): Final adjusted score (capped at 10.0)
                - reasoning (str): Explanation of adjustment
                - adjustments (list): List of adjustment details
        """
        # Get industry config
        industry_config = self.INDUSTRY_MODIFIERS.get(industry)

        if not industry_config:
            logger.warning(f"Unknown industry: {industry}, using default modifier 1.0")
            industry_config = {
                'modifier': 1.0,
                'strict_categories': [],
                'prohibited_terms': [],
                'description': 'Unknown industry'
            }

        # Start with base industry modifier
        modifier = industry_config['modifier']
        adjustments = []
        reasoning_parts = []

        reasoning_parts.append(f"Industry: {industry_config['description']}")

        # Adjustment 1: Prevalence-based
        if prevalence >= 0.70:
            # Very common - reduce severity
            prevalence_factor = 0.5
            modifier *= prevalence_factor
            adjustments.append({
                'type': 'prevalence_high',
                'factor': prevalence_factor,
                'reason': f'Very common in {industry} (≥70%)'
            })
            reasoning_parts.append(
                f"Common practice in {industry} (found in {prevalence:.0%} of baseline) - reduced severity"
            )
        elif prevalence < 0.30:
            # Uncommon - increase severity
            prevalence_factor = 1.3
            modifier *= prevalence_factor
            adjustments.append({
                'type': 'prevalence_low',
                'factor': prevalence_factor,
                'reason': f'Uncommon in {industry} (<30%)'
            })
            reasoning_parts.append(
                f"Unusual for {industry} (found in only {prevalence:.0%} of baseline) - increased severity"
            )

        # Adjustment 2: Strict category check
        if category in industry_config['strict_categories']:
            strict_factor = 1.5
            modifier *= strict_factor
            adjustments.append({
                'type': 'strict_category',
                'factor': strict_factor,
                'reason': f'{category} requires heightened scrutiny in {industry}'
            })
            reasoning_parts.append(
                f"{category} is a high-priority concern for {industry}"
            )

        # Adjustment 3: Prohibited terms check
        if clause_text:
            clause_lower = clause_text.lower()
            found_prohibited = []

            for term in industry_config['prohibited_terms']:
                if term.lower() in clause_lower:
                    found_prohibited.append(term)

            if found_prohibited:
                prohibited_factor = 1.5
                modifier *= prohibited_factor
                adjustments.append({
                    'type': 'prohibited_terms',
                    'factor': prohibited_factor,
                    'reason': f'Contains prohibited terms: {found_prohibited[:3]}'
                })
                reasoning_parts.append(
                    f"Contains terms alarming for {industry}: {', '.join(found_prohibited[:3])}"
                )

        # Calculate adjusted score
        adjusted_score = base_risk_score * modifier

        # Cap at 10.0
        if adjusted_score > 10.0:
            reasoning_parts.append(f"Score capped at maximum (10.0)")
            adjusted_score = 10.0

        # Build final reasoning
        reasoning = ". ".join(reasoning_parts) + "."

        logger.debug(
            f"Industry adjustment: {base_risk_score:.2f} × {modifier:.2f} = {adjusted_score:.2f}"
        )

        return {
            'base_score': base_risk_score,
            'industry_modifier': modifier,
            'adjusted_score': round(adjusted_score, 2),
            'reasoning': reasoning,
            'adjustments': adjustments,
            'industry': industry,
            'category': category,
            'prevalence': prevalence
        }

    def check_required_clauses(
        self,
        document_clauses: List[str],
        industry: str
    ) -> Dict[str, Any]:
        """
        Check if document contains required protective clauses for industry.

        Args:
            document_clauses: List of clause texts from document
            industry: Industry identifier

        Returns:
            Dictionary containing:
                - missing_clauses (list): Required clauses not found
                - found_clauses (list): Required clauses found
                - compliance_score (float): 0-1, percentage of required clauses found
                - recommendations (list): Suggestions for missing clauses
        """
        industry_config = self.INDUSTRY_MODIFIERS.get(industry)

        if not industry_config:
            return {
                'missing_clauses': [],
                'found_clauses': [],
                'compliance_score': 1.0,
                'recommendations': []
            }

        required = industry_config.get('required_clauses', [])

        if not required:
            return {
                'missing_clauses': [],
                'found_clauses': [],
                'compliance_score': 1.0,
                'recommendations': []
            }

        # Simple keyword-based checking (could be enhanced with embeddings)
        found = []
        missing = []

        all_text = " ".join(document_clauses).lower()

        for required_clause in required:
            # Check if clause keyword is present
            if required_clause.replace('_', ' ') in all_text:
                found.append(required_clause)
            else:
                missing.append(required_clause)

        compliance_score = len(found) / len(required) if required else 1.0

        # Generate recommendations
        recommendations = []
        for clause in missing:
            recommendations.append(
                f"Consider adding {clause.replace('_', ' ')} clause for {industry} compliance"
            )

        logger.info(
            f"Required clauses check for {industry}: "
            f"{len(found)}/{len(required)} found ({compliance_score:.0%})"
        )

        return {
            'missing_clauses': missing,
            'found_clauses': found,
            'compliance_score': compliance_score,
            'recommendations': recommendations
        }

    def get_category_strictness(self, category: str, industry: str) -> float:
        """
        Get strictness level for a category within an industry.

        Args:
            category: Risk category
            industry: Industry identifier

        Returns:
            Strictness multiplier (1.0 = normal, >1.0 = stricter)
        """
        industry_config = self.INDUSTRY_MODIFIERS.get(industry, {})
        strict_categories = industry_config.get('strict_categories', [])

        if category in strict_categories:
            return 1.5
        else:
            return 1.0

    def explain_industry_expectations(self, industry: str) -> Dict[str, Any]:
        """
        Get detailed explanation of industry expectations.

        Args:
            industry: Industry identifier

        Returns:
            Dictionary with industry details and expectations
        """
        industry_config = self.INDUSTRY_MODIFIERS.get(industry)

        if not industry_config:
            return {
                'industry': industry,
                'found': False,
                'message': 'Unknown industry'
            }

        return {
            'industry': industry,
            'found': True,
            'description': industry_config['description'],
            'base_modifier': industry_config['modifier'],
            'strict_categories': industry_config['strict_categories'],
            'required_clauses': industry_config['required_clauses'],
            'prohibited_terms': industry_config['prohibited_terms'],
            'explanation': self._generate_industry_explanation(industry, industry_config)
        }

    def _generate_industry_explanation(
        self,
        industry: str,
        config: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable explanation of industry expectations.

        Args:
            industry: Industry identifier
            config: Industry configuration

        Returns:
            Explanation string
        """
        parts = [
            f"{config['description']} has a base risk modifier of {config['modifier']:.1f}x.",
        ]

        if config['strict_categories']:
            parts.append(
                f"Extra scrutiny is applied to: {', '.join(config['strict_categories'][:5])}."
            )

        if config['required_clauses']:
            parts.append(
                f"Expected protective clauses: {', '.join(config['required_clauses'])}."
            )

        if config['prohibited_terms']:
            parts.append(
                f"Terms that raise concerns: {', '.join(config['prohibited_terms'][:5])}."
            )

        return " ".join(parts)
