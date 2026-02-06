"""
Competitive Analyzer for T&C Analysis.

Compares a document's risk profile against industry competitors to provide
context like "This T&C is worse than 75% of streaming services" and
suggests better alternatives.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .constants import INDUSTRY_COMPETITORS

logger = logging.getLogger(__name__)


@dataclass
class CompetitorComparison:
    """Result of competitive comparison."""
    company_name: str
    avg_risk_score: float
    notable_issues: List[str]
    is_better: bool  # True if this competitor is better than analyzed doc


class CompetitiveAnalyzer:
    """
    Analyzes a document's risk profile against industry competitors.

    Provides:
    - Percentile ranking (how this doc compares to peers)
    - Better/worse alternatives
    - Unique risks vs peers
    - Actionable recommendations
    """

    def __init__(self):
        """Initialize with industry competitor data."""
        self.competitors = INDUSTRY_COMPETITORS
        logger.info(f"CompetitiveAnalyzer initialized with {len(self.competitors)} industries")

    def analyze(
        self,
        document_risk_score: float,
        industry: str,
        company_name: Optional[str] = None,
        detected_risk_categories: Optional[List[str]] = None,
        high_severity_count: int = 0,
        medium_severity_count: int = 0
    ) -> Dict[str, Any]:
        """
        Analyze document against industry competitors.

        Args:
            document_risk_score: Overall risk score (1-10) of the document
            industry: Industry identifier (streaming, social_media, etc.)
            company_name: Optional company name to exclude from comparison
            detected_risk_categories: List of risk categories found in document
            high_severity_count: Number of high severity alerts
            medium_severity_count: Number of medium severity alerts

        Returns:
            Dict with competitive benchmark data matching CompetitiveBenchmark schema
        """
        detected_risk_categories = detected_risk_categories or []

        # Handle None industry
        if not industry:
            logger.warning("No industry provided for competitive analysis, using 'general'")
            industry = 'general'

        # Normalize industry name
        industry_normalized = self._normalize_industry(industry)

        # Get competitors for this industry
        industry_competitors = self.competitors.get(industry_normalized, {})

        if not industry_competitors:
            logger.warning(f"No competitor data for industry: {industry_normalized}")
            return self._generate_default_benchmark(document_risk_score, industry)

        # Filter out the same company if provided
        if company_name:
            company_key = self._normalize_company_name(company_name)
            industry_competitors = {
                k: v for k, v in industry_competitors.items()
                if k != company_key
            }

        # Calculate industry statistics
        risk_scores = [c['avg_risk_score'] for c in industry_competitors.values()]
        industry_avg = sum(risk_scores) / len(risk_scores) if risk_scores else 5.0

        # Calculate percentile (0 = best, 100 = worst)
        better_count = sum(1 for score in risk_scores if score < document_risk_score)
        percentile = int((better_count / len(risk_scores)) * 100) if risk_scores else 50

        # Determine comparison category
        if document_risk_score < industry_avg - 1.0:
            risk_comparison = "better"
        elif document_risk_score > industry_avg + 1.0:
            risk_comparison = "worse"
        else:
            risk_comparison = "similar"

        # Find better and worse alternatives
        better_alternatives = []
        worse_alternatives = []

        for key, competitor in industry_competitors.items():
            comp_info = {
                'company_name': competitor['company_name'],
                'avg_risk_score': competitor['avg_risk_score'],
                'notable_issues': competitor.get('notable_issues', [])
            }

            if competitor['avg_risk_score'] < document_risk_score - 0.5:
                better_alternatives.append(comp_info)
            elif competitor['avg_risk_score'] > document_risk_score + 0.5:
                worse_alternatives.append(comp_info)

        # Sort alternatives
        better_alternatives.sort(key=lambda x: x['avg_risk_score'])
        worse_alternatives.sort(key=lambda x: x['avg_risk_score'], reverse=True)

        # Identify unique risks (risks not common in better alternatives)
        unique_risks = self._identify_unique_risks(
            detected_risk_categories,
            better_alternatives
        )

        # Identify missing protections
        missing_protections = self._identify_missing_protections(
            detected_risk_categories,
            industry_normalized,
            document_risk_score
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            document_risk_score,
            industry_avg,
            risk_comparison,
            better_alternatives,
            unique_risks,
            high_severity_count,
            medium_severity_count
        )

        # Generate summary
        summary = self._generate_summary(
            document_risk_score,
            industry_avg,
            percentile,
            industry_normalized,
            len(industry_competitors),
            company_name
        )

        return {
            'industry': industry_normalized,
            'industry_average_risk': round(industry_avg, 1),
            'percentile_rank': percentile,
            'risk_comparison': risk_comparison,
            'peer_count': len(industry_competitors),
            'better_alternatives': better_alternatives[:3],  # Top 3
            'worse_alternatives': worse_alternatives[:2],    # Top 2
            'unique_risks': unique_risks[:5],
            'missing_protections': missing_protections[:5],
            'recommendations': recommendations[:5],
            'summary': summary
        }

    def _normalize_industry(self, industry: str) -> str:
        """Normalize industry name to match our data."""
        if not industry:
            return 'general'
        industry_lower = industry.lower().strip()

        # Common mappings
        mappings = {
            'saas': 'cloud_saas',
            'software': 'cloud_saas',
            'cloud': 'cloud_saas',
            'music': 'streaming',
            'video': 'streaming',
            'media': 'streaming',
            'entertainment': 'streaming',
            'social': 'social_media',
            'finance': 'financial',
            'fintech': 'financial',
            'banking': 'financial',
            'payment': 'financial',
            'payments': 'financial',
            'rideshare': 'gig_economy',
            'delivery': 'gig_economy',
            'gig': 'gig_economy',
            'shopping': 'ecommerce',
            'retail': 'ecommerce',
        }

        return mappings.get(industry_lower, industry_lower)

    def _normalize_company_name(self, company_name: str) -> str:
        """Normalize company name to match our keys."""
        # Remove common suffixes and convert to lowercase
        name = company_name.lower().strip()
        for suffix in [' inc', ' inc.', ' llc', ' corp', ' corporation', ' ltd']:
            name = name.replace(suffix, '')
        return name.replace(' ', '_').replace('-', '_')

    def _identify_unique_risks(
        self,
        detected_risks: List[str],
        better_alternatives: List[Dict]
    ) -> List[str]:
        """Identify risks that better competitors don't have."""
        if not better_alternatives:
            return []

        # Collect issues from better alternatives
        common_issues = set()
        for alt in better_alternatives:
            for issue in alt.get('notable_issues', []):
                common_issues.add(issue.lower())

        # Find risks in our document not common in better alternatives
        unique = []
        risk_descriptions = {
            'data_selling': 'Sells user data to third parties',
            'biometric': 'Collects biometric data',
            'perpetual_license': 'Claims perpetual rights to your content',
            'forced_arbitration': 'Forces arbitration, no class actions',
            'unilateral_termination': 'Can terminate your account without cause',
            'auto_renewal': 'Auto-renews with difficult cancellation',
            'fund_holds': 'Can hold your funds indefinitely',
            'liability_limitation': 'Extensive liability limitations',
        }

        for risk in detected_risks:
            risk_lower = risk.lower().replace('_', ' ')
            # Check if this risk appears in better alternatives
            is_common = any(risk_lower in issue for issue in common_issues)
            if not is_common and risk in risk_descriptions:
                unique.append(risk_descriptions[risk])

        return unique

    def _identify_missing_protections(
        self,
        detected_risks: List[str],
        industry: str,
        risk_score: float
    ) -> List[str]:
        """Identify consumer protections this document lacks."""
        missing = []

        # Standard protections that high-risk documents often lack
        if risk_score > 6.0:
            if 'forced_arbitration' in detected_risks or 'class_action_waiver' in detected_risks:
                missing.append('Right to participate in class action lawsuits')
            if 'data_selling' in detected_risks:
                missing.append('Opt-out from data selling')
            if 'auto_renewal' in detected_risks:
                missing.append('Easy cancellation without penalty')
            if 'unilateral_termination' in detected_risks:
                missing.append('Account termination appeal process')

        if risk_score > 5.0:
            missing.append('Clear data deletion upon account closure')
            if industry in ['streaming', 'social_media']:
                missing.append('Content portability/export options')

        return missing

    def _generate_recommendations(
        self,
        risk_score: float,
        industry_avg: float,
        comparison: str,
        better_alternatives: List[Dict],
        unique_risks: List[str],
        high_count: int,
        medium_count: int
    ) -> List[str]:
        """Generate actionable recommendations based on comparison."""
        recommendations = []

        if comparison == "worse":
            recommendations.append(
                f"Consider alternatives: This service has higher risk ({risk_score:.1f}) "
                f"than industry average ({industry_avg:.1f})"
            )

            if better_alternatives:
                best = better_alternatives[0]
                recommendations.append(
                    f"Better alternative: {best['company_name']} "
                    f"(risk score: {best['avg_risk_score']:.1f})"
                )

        if high_count > 3:
            recommendations.append(
                f"High alert: {high_count} critical/high severity issues found - "
                "review carefully before agreeing"
            )

        if unique_risks:
            recommendations.append(
                f"Unique concerns: This T&C has {len(unique_risks)} issues "
                "not typical for this industry"
            )

        # Generic safety recommendations
        if risk_score > 5.0:
            recommendations.append(
                "Set calendar reminder to review terms periodically for changes"
            )
            recommendations.append(
                "Consider using privacy-focused payment methods (virtual cards)"
            )

        if not recommendations:
            recommendations.append(
                "This T&C is relatively consumer-friendly for its industry"
            )

        return recommendations

    def _generate_summary(
        self,
        risk_score: float,
        industry_avg: float,
        percentile: int,
        industry: str,
        peer_count: int,
        company_name: Optional[str]
    ) -> str:
        """Generate one-sentence summary."""
        company_text = company_name or "This service"
        industry_text = industry.replace('_', ' ').title()

        if percentile <= 25:
            return (
                f"{company_text}'s terms are better than {100-percentile}% of "
                f"{industry_text} services (risk: {risk_score:.1f}/10, "
                f"industry avg: {industry_avg:.1f}/10)"
            )
        elif percentile <= 50:
            return (
                f"{company_text}'s terms are about average for {industry_text} "
                f"(risk: {risk_score:.1f}/10, industry avg: {industry_avg:.1f}/10)"
            )
        elif percentile <= 75:
            return (
                f"{company_text}'s terms are worse than {percentile}% of "
                f"{industry_text} services - consider alternatives "
                f"(risk: {risk_score:.1f}/10)"
            )
        else:
            return (
                f"Warning: {company_text}'s terms are among the worst in "
                f"{industry_text} ({percentile}th percentile, risk: {risk_score:.1f}/10) - "
                "strongly consider alternatives"
            )

    def _generate_default_benchmark(
        self,
        risk_score: float,
        industry: str
    ) -> Dict[str, Any]:
        """Generate default benchmark when no competitor data available."""
        return {
            'industry': industry,
            'industry_average_risk': 5.5,  # Assume average
            'percentile_rank': 50,
            'risk_comparison': 'unknown',
            'peer_count': 0,
            'better_alternatives': [],
            'worse_alternatives': [],
            'unique_risks': [],
            'missing_protections': [],
            'recommendations': [
                'No competitor data available for detailed comparison',
                f'Document risk score: {risk_score:.1f}/10'
            ],
            'summary': (
                f"Unable to compare - no competitor data for {industry} industry. "
                f"Risk score: {risk_score:.1f}/10"
            )
        }

    def get_supported_industries(self) -> List[str]:
        """Get list of industries with competitor data."""
        return list(self.competitors.keys())

    def get_competitors_for_industry(self, industry: str) -> List[Dict[str, Any]]:
        """Get competitor list for an industry."""
        industry_normalized = self._normalize_industry(industry)
        competitors = self.competitors.get(industry_normalized, {})

        return [
            {
                'key': key,
                'company_name': data['company_name'],
                'avg_risk_score': data['avg_risk_score'],
                'notable_issues': data.get('notable_issues', [])
            }
            for key, data in competitors.items()
        ]
