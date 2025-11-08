"""
Anomaly detector for identifying risky clauses.

Universal anomaly detection that works for ANY Terms & Conditions document
from ANY company. Automatically identifies unusual, risky, or consumer-unfriendly
clauses without being told what to look for.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.pinecone_service import PineconeService
from app.services.openai_service import OpenAIService
from app.core.prevalence_calculator import PrevalenceCalculator
from app.core.risk_assessor import RiskAssessor
from app.core.risk_indicators import RiskIndicators
from app.core.semantic_risk_detector import SemanticRiskDetector  # Fix #5
from app.core.compound_risk_detector import CompoundRiskDetector  # Fix #6
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnomalyDetector:
    """Detects anomalies and risky clauses in T&C documents."""

    def __init__(
        self,
        openai_service: Optional[OpenAIService] = None,
        pinecone_service: Optional[PineconeService] = None,
        db: Optional[Session] = None,
    ):
        """
        Initialize anomaly detector.

        Args:
            openai_service: Optional OpenAI service instance
            pinecone_service: Optional Pinecone service instance
            db: Optional database session
        """
        self.openai = openai_service or OpenAIService()
        self.pinecone = pinecone_service or PineconeService()
        self.db = db
        self.prevalence_calc = PrevalenceCalculator(self.openai, self.pinecone, self.db)
        self.risk_assessor = RiskAssessor(self.openai, use_gpt5=True, db=self.db)
        self.risk_indicators = RiskIndicators()
        self.semantic_detector = SemanticRiskDetector(self.openai)  # Fix #5
        self.compound_detector = CompoundRiskDetector()  # Fix #6
        self._semantic_initialized = False

    async def detect_anomalies(
        self,
        document_id: str,
        sections: List[Dict[str, Any]],
        company_name: str = "Unknown",
        service_type: str = "general",
    ) -> List[Dict[str, Any]]:
        """
        Detect all anomalies in a document.

        Universal detection that works for ANY T&C document from ANY company.
        Identifies unusual, risky, or consumer-unfriendly clauses automatically.

        Args:
            document_id: Document identifier
            sections: List of parsed sections with clauses
            company_name: Name of the company (optional)
            service_type: Type of service for context-dependent analysis

        Returns:
            List of detected anomalies with full details
        """
        logger.info(f"Starting anomaly detection for document {document_id}")
        logger.info(f"Company: {company_name}, Service Type: {service_type}")
        logger.info(f"Total sections to analyze: {len(sections)}")

        all_anomalies = []
        total_clauses = 0

        for section in sections:
            section_name = section.get("section_name", "Unknown Section")
            clauses = section.get("clauses", [])
            total_clauses += len(clauses)

            logger.info(
                f"Analyzing section '{section_name}' with {len(clauses)} clauses"
            )

            for clause_idx, clause in enumerate(clauses):
                clause_text = clause.get("text", "")
                clause_number = clause.get(
                    "clause_number", f"{section_name}.{clause_idx}"
                )

                if not clause_text or len(clause_text.strip()) < 20:
                    continue  # Skip only empty or very short clauses (< 20 chars)

                logger.debug(
                    f"Analyzing clause {clause_number}: {clause_text[:100]}..."
                )

                # STEP 1: Detect universal risk indicators (keyword-based)
                detected_indicators = self.risk_indicators.detect_indicators(
                    clause_text=clause_text, service_type=service_type
                )

                logger.debug(
                    f"Clause {clause_number}: Found {len(detected_indicators)} keyword indicators"
                )

                # STEP 1.5: Augment with semantic detection (Fix #5)
                # Initialize semantic detector on first use (lazy initialization)
                if not self._semantic_initialized:
                    try:
                        await self.semantic_detector.initialize()
                        self._semantic_initialized = True
                    except Exception as e:
                        logger.warning(f"Semantic detector initialization failed: {e}")

                # Add semantic detection if initialized
                if self._semantic_initialized:
                    try:
                        detected_indicators = (
                            await self.semantic_detector.augment_indicators(
                                clause_text=clause_text,
                                keyword_indicators=detected_indicators,
                            )
                        )
                        logger.debug(
                            f"Clause {clause_number}: Total indicators after semantic detection: "
                            f"{len(detected_indicators)}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Semantic detection failed for clause {clause_number}: {e}"
                        )
                        # Continue with keyword indicators only

                # STEP 2: Calculate prevalence in baseline corpus
                try:
                    prevalence = await self.prevalence_calc.calculate_prevalence(
                        clause_text=clause_text, clause_type=section_name
                    )
                    logger.debug(
                        f"Clause {clause_number}: Prevalence = {prevalence:.2%}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Prevalence calculation failed for clause {clause_number}: {e}"
                    )
                    # Default to 10% (Fix #2 - unusual/rare when unknown)
                    prevalence = 0.1  # Unknown but probably unusual

                # STEP 3: Determine if clause is suspicious (AGGRESSIVE DETECTION)
                is_unusual = prevalence < 0.30  # Rare clause
                has_high_risk = any(
                    ind["severity"] == "high" for ind in detected_indicators
                )
                has_medium_risk = any(
                    ind["severity"] == "medium" for ind in detected_indicators
                )

                # NEW: More aggressive detection - flag if ANY of these are true:
                is_suspicious = (
                    is_unusual or  # Rare in baseline corpus
                    has_high_risk or  # Contains high-risk patterns
                    has_medium_risk or  # Contains medium-risk patterns
                    len(detected_indicators) > 0  # Contains ANY risk indicator
                )

                # Additionally: Flag long clauses with vague language
                if len(clause_text) > 500:
                    vague_terms = ["may", "might", "could", "at our discretion", "as we see fit", "in our sole discretion"]
                    has_vague = any(term in clause_text.lower() for term in vague_terms)
                    if has_vague:
                        is_suspicious = True

                logger.debug(
                    f"Clause {clause_number}: Unusual={is_unusual}, "
                    f"HighRisk={has_high_risk}, MediumRisk={has_medium_risk}, "
                    f"Suspicious={is_suspicious}, Indicators={len(detected_indicators)}"
                )

                if is_suspicious:
                    # STEP 4: Determine severity from INDICATORS (Fix #4 - Remove GPT-4 gate)
                    # Severity is based on detected patterns, not GPT-4 opinion
                    if has_high_risk:
                        severity = "high"
                    elif has_medium_risk:
                        severity = "medium"
                    elif is_unusual:
                        severity = "low"
                    else:
                        severity = "medium"  # Default for suspicious clauses

                    # STEP 5: Get GPT-4 for explanation/context (NOT for gating)
                    try:
                        risk_assessment = await self.risk_assessor.assess_risk(
                            clause_text=clause_text,
                            section=section_name,
                            clause_number=clause_number,
                            prevalence=prevalence,
                            detected_indicators=detected_indicators,
                            company_name=company_name,
                        )

                        logger.info(
                            f"Clause {clause_number}: GPT-4 details = {risk_assessment.get('risk_level', 'unknown')}"
                        )

                        # Use GPT-4 explanation but keep indicator-based severity
                        explanation = risk_assessment.get("explanation", "")
                        consumer_impact = risk_assessment.get("consumer_impact", "")
                        recommendation = risk_assessment.get("recommendation", "")
                        risk_category = risk_assessment.get("risk_category", "other")

                    except Exception as e:
                        logger.warning(
                            f"GPT-4 assessment failed for clause {clause_number}: {e}"
                        )
                        # Fallback: Generate basic explanation from indicators
                        explanation = self._generate_fallback_explanation(
                            detected_indicators, prevalence
                        )
                        consumer_impact = "This clause may negatively impact consumers."
                        recommendation = (
                            "Review this clause carefully before accepting."
                        )
                        risk_category = (
                            detected_indicators[0]["indicator"]
                            if detected_indicators
                            else "other"
                        )

                    # ALWAYS flag suspicious clauses (Fix #4 - No GPT-4 gate)
                    anomaly = {
                        "document_id": document_id,
                        "section": section_name,
                        "clause_number": clause_number,
                        "clause_text": clause_text,
                        "severity": severity,  # From indicators, not GPT-4
                        "explanation": explanation,
                        "consumer_impact": consumer_impact,
                        "recommendation": recommendation,
                        "risk_category": risk_category,
                        "prevalence": prevalence,
                        "prevalence_display": f"{prevalence*100:.0f}%",
                        "detected_indicators": [
                            {
                                "name": ind["indicator"],
                                "description": ind["description"],
                                "severity": ind["severity"],
                            }
                            for ind in detected_indicators
                        ],
                        "comparison": (
                            f"Found in only {prevalence*100:.0f}% of similar services"
                            if prevalence < 0.30
                            else f"Found in {prevalence*100:.0f}% of similar services"
                        ),
                    }

                    all_anomalies.append(anomaly)
                    logger.info(
                        f"✓ Anomaly detected: {clause_number} ({severity} risk - {len(detected_indicators)} indicators)"
                    )

        logger.info(
            f"Anomaly detection complete: {len(all_anomalies)} anomalies found out of {total_clauses} clauses"
        )

        # STEP 6: Detect compound risks (Fix #6)
        compound_risks = self.compound_detector.detect_compound_risks(all_anomalies)

        if compound_risks:
            logger.info(f"Detected {len(compound_risks)} compound risk patterns")

            # Add compound risks to each related anomaly for context
            for compound_risk in compound_risks:
                pattern_name = compound_risk["compound_risk_type"]

                # Find anomalies involved in this compound risk
                for anomaly in all_anomalies:
                    anomaly_indicators = {
                        ind["name"] for ind in anomaly.get("detected_indicators", [])
                    }

                    required_indicators = set(compound_risk["required_indicators"])
                    optional_indicators = set(
                        compound_risk.get("matched_optional_indicators", [])
                    )
                    all_relevant = required_indicators.union(optional_indicators)

                    if anomaly_indicators.intersection(all_relevant):
                        # This anomaly is part of the compound risk
                        if "compound_risks" not in anomaly:
                            anomaly["compound_risks"] = []

                        anomaly["compound_risks"].append(
                            {
                                "pattern": pattern_name,
                                "severity": compound_risk["severity"],
                                "description": compound_risk["description"],
                                "confidence": compound_risk["confidence"],
                            }
                        )

        # Store compound risks for document-level reporting
        # (Can be accessed separately via document.compound_risks)
        for anomaly in all_anomalies:
            if not hasattr(anomaly, "_compound_risks_summary"):
                anomaly["_compound_risks_summary"] = compound_risks

        return all_anomalies

    def _generate_fallback_explanation(
        self, detected_indicators: List[Dict], prevalence: float
    ) -> str:
        """
        Generate basic explanation when GPT-4 fails (Fix #4 - Fallback).

        Args:
            detected_indicators: List of detected risk indicators
            prevalence: Prevalence score (0-1)

        Returns:
            Basic explanation string
        """
        if not detected_indicators:
            return f"This clause is unusual (found in only {prevalence*100:.0f}% of similar services)."

        # Build explanation from indicators
        indicator_names = [
            ind["description"] for ind in detected_indicators[:3]
        ]  # Top 3

        if len(indicator_names) == 1:
            explanation = (
                f"This clause contains a concerning pattern: {indicator_names[0]}."
            )
        elif len(indicator_names) == 2:
            explanation = f"This clause contains concerning patterns: {indicator_names[0]} and {indicator_names[1]}."
        else:
            explanation = f"This clause contains multiple concerning patterns including: {indicator_names[0]}, {indicator_names[1]}, and {indicator_names[2]}."

        if prevalence < 0.30:
            explanation += f" Additionally, this clause is rare (found in only {prevalence*100:.0f}% of similar services)."

        return explanation

    def calculate_document_risk_score(
        self, anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate overall risk score for the document.

        Universal risk scoring formula that works for any T&C document:
        - Considers anomaly count, severity distribution, and category diversity
        - Returns score from 1-10 and risk level (Low/Medium/High)

        Args:
            anomalies: List of detected anomalies

        Returns:
            Dictionary with risk_score (1-10), risk_level, and breakdown
        """
        if not anomalies:
            return {
                "risk_score": 1.0,
                "risk_level": "Low",
                "risk_label": "Low Risk",
                "explanation": "No significant anomalies detected. This document appears to have standard terms.",
                "breakdown": {
                    "anomaly_count": 0,
                    "high_severity": 0,
                    "medium_severity": 0,
                    "low_severity": 0,
                },
            }

        # Count by severity
        high_count = sum(1 for a in anomalies if a["severity"] == "high")
        medium_count = sum(1 for a in anomalies if a["severity"] == "medium")
        low_count = sum(1 for a in anomalies if a["severity"] == "low")
        total_count = len(anomalies)

        # Count unique risk categories
        categories = set(a.get("risk_category", "other") for a in anomalies)
        category_diversity = len(categories)

        # SCORING FORMULA (1-10 scale):
        # Base score from anomaly count
        count_score = min(
            total_count / 2.0, 4.0
        )  # Max 4 points (1-8 anomalies = 0.5-4 pts)

        # Severity weighting
        severity_score = (
            (high_count * 0.75) + (medium_count * 0.35) + (low_count * 0.15)
        )
        severity_score = min(severity_score, 4.0)  # Max 4 points

        # Category diversity (more categories = more systemic issues)
        diversity_score = min(category_diversity * 0.5, 2.0)  # Max 2 points

        # Total score (1-10)
        raw_score = count_score + severity_score + diversity_score
        risk_score = max(1.0, min(raw_score, 10.0))  # Clamp between 1-10

        # Determine risk level
        if risk_score >= 7.0:
            risk_level = "High"
            risk_label = "High Risk"
            explanation = f"This document contains {total_count} concerning clauses with {high_count} high-severity issues. Multiple problematic areas detected across {category_diversity} different categories. Exercise extreme caution."
        elif risk_score >= 4.0:
            risk_level = "Medium"
            risk_label = "Medium Risk"
            explanation = f"This document contains {total_count} concerning clauses. While not extremely aggressive, there are {high_count + medium_count} issues worth reviewing carefully before accepting."
        else:
            risk_level = "Low"
            risk_label = "Low to Medium Risk"
            explanation = f"This document contains {total_count} minor issues. Most terms appear standard, but review the flagged clauses for your specific situation."

        logger.info(f"Document risk score: {risk_score:.1f}/10 ({risk_level})")
        logger.info(
            f"Breakdown: {total_count} anomalies ({high_count} high, {medium_count} medium, {low_count} low)"
        )

        return {
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "risk_label": risk_label,
            "explanation": explanation,
            "breakdown": {
                "anomaly_count": total_count,
                "high_severity": high_count,
                "medium_severity": medium_count,
                "low_severity": low_count,
                "category_diversity": category_diversity,
                "categories": list(categories),
            },
            "scoring_details": {
                "count_contribution": round(count_score, 2),
                "severity_contribution": round(severity_score, 2),
                "diversity_contribution": round(diversity_score, 2),
            },
        }

    async def generate_report(
        self, document_id: str, anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate complete anomaly report for document.

        Args:
            document_id: Document identifier
            anomalies: List of detected anomalies

        Returns:
            Comprehensive report with risk score and categorized anomalies
        """
        logger.info(f"Generating report for document {document_id}")

        # Categorize anomalies by severity
        high_risk = [a for a in anomalies if a["severity"] == "high"]
        medium_risk = [a for a in anomalies if a["severity"] == "medium"]
        low_risk = [a for a in anomalies if a["severity"] == "low"]

        # Calculate overall risk score
        risk_assessment = self.calculate_document_risk_score(anomalies)

        # Group by category
        by_category = {}
        for anomaly in anomalies:
            category = anomaly.get("risk_category", "other")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(anomaly)

        report = {
            "document_id": document_id,
            "overall_risk": risk_assessment,
            "total_anomalies": len(anomalies),
            "high_risk_count": len(high_risk),
            "medium_risk_count": len(medium_risk),
            "low_risk_count": len(low_risk),
            "high_risk_anomalies": high_risk,
            "medium_risk_anomalies": medium_risk,
            "low_risk_anomalies": low_risk,
            "by_category": by_category,
            "top_concerns": (
                high_risk[:3] if high_risk else medium_risk[:3]
            ),  # Top 3 most critical
        }

        logger.info(
            f"Report generated: {len(anomalies)} anomalies, Risk Score: {risk_assessment['risk_score']}/10"
        )

        return report
