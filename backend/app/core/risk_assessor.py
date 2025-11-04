"""
Risk assessor using GPT-5-Nano (or GPT-4o-mini fallback) for evaluating clause risk.

Acts as a CONSUMER ADVOCATE, not a company lawyer.
Identifies clauses that would surprise or harm the average consumer.
"""

import json
from typing import Dict, Any, List, Optional

from app.services.openai_service import OpenAIService
from app.services.gpt5_service import GPT5Service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RiskAssessor:
    """Assesses risk level of clauses using GPT-5-Nano (with GPT-4o-mini fallback) as a consumer protection tool."""

    def __init__(self, openai_service: Optional[OpenAIService] = None, use_gpt5: bool = True):
        """
        Initialize risk assessor.

        Args:
            openai_service: Optional OpenAI service instance
            use_gpt5: If True, try GPT-5-Nano first (fallback to GPT-4o-mini on error)
        """
        self.openai = openai_service or OpenAIService()
        self.use_gpt5 = use_gpt5
        self.gpt5_service = None

        # Initialize GPT-5 service if requested
        if use_gpt5:
            try:
                self.gpt5_service = GPT5Service()
                logger.info("GPT-5 service initialized for risk assessment")
            except Exception as e:
                logger.warning(f"GPT-5 service initialization failed, will use GPT-4o-mini: {e}")
                self.use_gpt5 = False

    async def assess_risk(
        self,
        clause_text: str,
        section: str,
        clause_number: str,
        prevalence: float,
        detected_indicators: List[Dict[str, Any]],
        company_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Assess risk level of a clause from a consumer protection perspective.

        Think like a CONSUMER ADVOCATE who helps everyday people understand
        what they're agreeing to. Be skeptical of company-friendly language.

        Args:
            clause_text: The clause text to analyze
            section: Section name
            clause_number: Clause identifier
            prevalence: How common this clause is (0.0-1.0)
            detected_indicators: List of detected risk indicators
            company_name: Name of the company

        Returns:
            Risk assessment with level, explanation, and recommendations
        """

        # Build indicator summary
        indicator_summary = "None detected"
        if detected_indicators:
            high_indicators = [ind for ind in detected_indicators if ind["severity"] == "high"]
            medium_indicators = [ind for ind in detected_indicators if ind["severity"] == "medium"]

            parts = []
            if high_indicators:
                parts.append(f"HIGH RISK: {', '.join([ind['description'] for ind in high_indicators])}")
            if medium_indicators:
                parts.append(f"MEDIUM RISK: {', '.join([ind['description'] for ind in medium_indicators])}")

            indicator_summary = "; ".join(parts) if parts else "Minor concerns detected"

        # Create consumer-focused prompt
        # Determine prevalence message
        if prevalence < 0.30:
            prevalence_msg = "(This is UNUSUAL - most companies don't have this)"
        elif prevalence < 0.70:
            prevalence_msg = "(This is fairly common in T&Cs)"
        else:
            prevalence_msg = "(This is very standard)"
        
        prompt = f"""You are a CONSUMER PROTECTION ADVOCATE analyzing Terms & Conditions for everyday people.

Your job: Help consumers understand what they're really agreeing to and identify unfair clauses.

Think like a skeptical consumer advocate, NOT a company lawyer. If a clause would surprise or disadvantage the average person who just wants to use a service, flag it.

CLAUSE TO ANALYZE:
Company: {company_name}
Section: {section} (Clause {clause_number})
Text: "{clause_text}"

CONTEXT:
- Prevalence: Found in {prevalence*100:.0f}% of similar standard T&Cs
  {prevalence_msg}
- Detected Risk Indicators: {indicator_summary}

CONSUMER PROTECTION ANALYSIS:
Ask yourself from a consumer's perspective:

1. SURPRISE FACTOR: Would this surprise a reasonable person reading quickly?
2. FAIRNESS: Is this balanced, or heavily favor the company?
3. RIGHTS: Does this waive important consumer rights (refunds, legal recourse, data privacy)?
4. HIDDEN COSTS: Are there hidden fees, automatic renewals, or surprise charges?
5. ESCAPE CLAUSES: Can the company change rules/prices without notice? Can they terminate you arbitrarily?
6. ONE-SIDEDNESS: Are obligations entirely on the consumer with no company accountability?

SEVERITY GUIDELINES:
- **HIGH RISK**: Severely unfair, dangerous for consumers, waives critical rights, hidden costs, one-sided termination, forced arbitration, unusual liability
  Examples: "We can terminate you anytime for any reason", "You waive all rights to sue", "Prices can increase without notice"

- **MEDIUM RISK**: Concerning but common in some industries, may be unfair but not egregiously so, reduces consumer protections
  Examples: Auto-renewal without clear notice, broad data sharing, no refunds, terms can change anytime

- **LOW RISK**: Standard protective language, reasonable terms, common in industry, doesn't significantly disadvantage consumers
  Examples: Standard warranty disclaimers, reasonable usage limits, normal legal protections for company

RESPOND IN JSON:
{{
  "risk_level": "high" | "medium" | "low",
  "risk_category": "liability" | "payment" | "privacy" | "arbitration" | "modification" | "termination" | "content" | "data" | "other",
  "explanation": "2-3 sentences explaining why this is risky for consumers (or why it's okay). Be specific about the consumer harm.",
  "consumer_impact": "One sentence: How does this practically affect someone using the service?",
  "recommendation": "What should consumers know or do about this clause?"
}}

Be CRITICAL but FAIR. If it's genuinely risky for consumers, say so clearly. If it's standard protection, say that too.

JSON Response:"""

        try:
            # Try GPT-5-Nano first (if available), fallback to GPT-4o-mini
            if self.use_gpt5 and self.gpt5_service:
                try:
                    logger.debug(f"Using GPT-5-Nano for risk assessment of clause {clause_number}")

                    # Use GPT-5 Responses API with correct parameters
                    result = await self.gpt5_service.create_json_response(
                        prompt=prompt,
                        model="gpt-5-nano",
                        reasoning_effort="medium"  # Balanced quality/cost for anomaly detection
                    )

                    logger.debug(
                        f"GPT-5-Nano assessment for clause {clause_number}: "
                        f"{result.get('risk_level', 'unknown')} - {result.get('explanation', '')[:100]}"
                    )

                    return result

                except Exception as e:
                    logger.warning(f"GPT-5-Nano failed for clause {clause_number}, falling back to GPT-4o-mini: {e}")
                    # Continue to GPT-4o-mini fallback below

            # Fallback: Use GPT-4o-mini (reliable, working)
            logger.debug(f"Using GPT-4o-mini for risk assessment of clause {clause_number}")
            result = await self.openai.create_structured_completion(
                prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.3
            )

            logger.debug(
                f"GPT-4o-mini assessment for clause {clause_number}: "
                f"{result.get('risk_level', 'unknown')} - {result.get('explanation', '')[:100]}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-4 response as JSON: {e}")
            logger.error(f"Result was: {result}")

            # Fallback based on indicators
            if any(ind["severity"] == "high" for ind in detected_indicators):
                fallback_level = "high"
            elif detected_indicators:
                fallback_level = "medium"
            else:
                fallback_level = "low"

            return {
                "risk_level": fallback_level,
                "risk_category": "other",
                "explanation": "Risk assessment based on detected indicators (GPT-4 parsing failed).",
                "consumer_impact": f"Detected {len(detected_indicators)} potential issues.",
                "recommendation": "Review this clause carefully."
            }

        except Exception as e:
            logger.error(f"Risk assessment failed: {e}", exc_info=True)
            # Safe fallback
            return {
                "risk_level": "medium",
                "risk_category": "other",
                "explanation": "Unable to complete full risk assessment due to technical error.",
                "consumer_impact": "This clause requires manual review.",
                "recommendation": "Consult the full Terms & Conditions or seek legal advice."
            }
