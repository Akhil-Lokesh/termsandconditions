"""
GPT-5 Stage 2 Deep Legal Analysis Service.

Comprehensive legal analysis of T&C documents using GPT-5.
Only called when Stage 1 confidence < 0.55 (uncertain cases).
Cost: ~$0.015 per document (25x more expensive than Stage 1).

Provides detailed legal reasoning, case law references, and specific
consumer protection concerns that Stage 1 cannot reliably assess.
"""

import json
import re
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.services.openai_service import OpenAIService
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class GPT5Stage2Analyzer:
    """
    Deep legal analysis using GPT-5.

    Provides comprehensive analysis for cases where Stage 1 is uncertain.
    Uses advanced reasoning capabilities of GPT-5 for nuanced legal assessment.
    """

    # Cost per 1M tokens (GPT-5 pricing)
    COST_PER_1M_INPUT_TOKENS = 2.50  # $2.50 per 1M input tokens
    COST_PER_1M_OUTPUT_TOKENS = 10.00  # $10.00 per 1M output tokens

    # Model configuration
    MODEL_NAME = "gpt-5"  # Full GPT-5 model for deep analysis
    TEMPERATURE = 0.6  # Temperature setting for GPT-5 (0.6 = more focused analysis)
    MAX_TOKENS = 4000  # More tokens for detailed analysis

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize Stage 2 analyzer.

        Args:
            openai_service: Optional OpenAI service instance
        """
        self.openai = openai_service or OpenAIService()
        self.model_name = self.MODEL_NAME

        logger.info(f"Initialized GPT5Stage2Analyzer with model: {self.model_name}")

    async def deep_analyze(
        self,
        document_text: str,
        document_id: str,
        stage1_result: Optional[Dict[str, Any]] = None,
        company_name: str = "Unknown",
        industry: str = "general"
    ) -> Dict[str, Any]:
        """
        Perform deep legal analysis of T&C document.

        Uses GPT-5's advanced reasoning for comprehensive assessment.
        Considers Stage 1 flagged items for focused analysis.

        Args:
            document_text: Full text of T&C document
            document_id: Unique document identifier
            stage1_result: Optional Stage 1 classification result (for context)
            company_name: Name of company
            industry: Industry category (tech, finance, healthcare, etc.)

        Returns:
            Dict with:
            - overall_risk: low/medium/high
            - confidence: 0.8-1.0 (Stage 2 is always high confidence)
            - clauses: List of analyzed clauses with detailed reasoning
            - summary: Comprehensive risk summary
            - legal_concerns: Specific legal issues identified
            - consumer_impact: How clauses affect consumers
            - recommendations: Specific recommendations
            - stage1_validation: How Stage 2 validates/contradicts Stage 1
            - cost: Processing cost in USD
            - processing_time: Time in seconds
            - stage: 2 (Stage 2 analysis)

        Raises:
            ValueError: If document is empty or invalid
        """
        start_time = time.time()

        # Validate input
        if not document_text or len(document_text.strip()) < 100:
            raise ValueError("Document text is too short or empty")

        logger.info(f"Starting Stage 2 deep analysis for document {document_id}")
        logger.info(
            f"Document length: {len(document_text)} chars, "
            f"Company: {company_name}, Industry: {industry}"
        )

        if stage1_result:
            logger.info(
                f"Stage 1 context: risk={stage1_result.get('overall_risk')}, "
                f"confidence={stage1_result.get('confidence', 0):.2f}, "
                f"flagged={len([c for c in stage1_result.get('clauses', []) if c.get('classification') == 'ANOMALY'])}"
            )

        # Build deep analysis prompt
        prompt = self._build_deep_analysis_prompt(
            document_text,
            company_name,
            industry,
            stage1_result
        )

        # Call GPT-5
        try:
            response = await self.openai.create_structured_completion(
                prompt=prompt,
                model=self.model_name,
                temperature=self.TEMPERATURE
            )

            # Parse JSON response
            result = self._parse_analysis_response(response)

            # Calculate cost
            input_tokens = len(document_text.split()) * 1.3 + 500  # Prompt overhead
            output_tokens = len(response.split()) * 1.3
            cost = self._calculate_cost(input_tokens, output_tokens)

            # Add metadata
            processing_time = time.time() - start_time
            result["cost"] = cost
            result["processing_time"] = round(processing_time, 2)
            result["stage"] = 2
            result["document_id"] = document_id
            result["timestamp"] = datetime.utcnow().isoformat()
            result["requires_escalation"] = False  # Stage 2 is final

            # Validate Stage 1 if provided
            if stage1_result:
                result["stage1_validation"] = self._validate_stage1(
                    stage1_result,
                    result
                )

            logger.info(
                f"Stage 2 complete: risk={result['overall_risk']}, "
                f"confidence={result.get('confidence', 0):.2f}, "
                f"legal_concerns={len(result.get('legal_concerns', []))}, "
                f"cost=${cost:.6f}, "
                f"time={processing_time:.2f}s"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return self._fallback_parse(response, document_id, start_time)

        except Exception as e:
            logger.error(f"Stage 2 analysis failed: {e}", exc_info=True)
            raise

    def _build_deep_analysis_prompt(
        self,
        document_text: str,
        company_name: str,
        industry: str,
        stage1_result: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build comprehensive analysis prompt for GPT-5.

        Incorporates Stage 1 findings for focused deep dive.
        """
        # Build context from Stage 1
        stage1_context = ""
        if stage1_result:
            anomalies = [
                c for c in stage1_result.get("clauses", [])
                if c.get("classification") == "ANOMALY"
            ]
            if anomalies:
                stage1_context = "\n\nSTAGE 1 FLAGGED ITEMS (pay special attention):\n"
                for anomaly in anomalies[:5]:  # Top 5 anomalies
                    stage1_context += f"- {anomaly.get('section', 'Unknown')}: {anomaly.get('reason', '')}\n"

        prompt = f"""You are a senior legal analyst specializing in consumer protection law and Terms & Conditions review.

YOUR TASK:
Perform comprehensive legal analysis of this Terms & Conditions document. Provide detailed assessment
of legal risks, consumer protection concerns, and regulatory compliance issues.

COMPANY: {company_name}
INDUSTRY: {industry}
{stage1_context}

DOCUMENT TEXT:
{document_text}

ANALYSIS REQUIREMENTS:

1. **Clause-by-Clause Analysis**:
   - Identify all material clauses (not just obvious problems)
   - Classify each as STANDARD, UNUSUAL, or PROBLEMATIC
   - Provide specific legal reasoning for problematic clauses
   - Reference relevant consumer protection laws where applicable

2. **Legal Concerns**:
   - Contract enforceability issues
   - Consumer protection violations (FTC Act, state laws)
   - Unconscionability factors
   - Ambiguous or deceptive language
   - Missing standard protections

3. **Industry Context**:
   - Compare to {industry} industry standards
   - Identify deviations from best practices
   - Note clauses that are acceptable in some industries but not others

4. **Consumer Impact Assessment**:
   - How each problematic clause affects typical users
   - Potential financial impact
   - Rights being waived
   - Practical enforceability

5. **Risk Prioritization**:
   - High risk: Legal issues, likely harm, deceptive practices
   - Medium risk: Unusual but possibly defensible
   - Low risk: Slight variations from standard language

6. **Specific Recommendations**:
   - What users should know before accepting
   - Red flags requiring legal review
   - Negotiation points for business users

OUTPUT FORMAT:
Return ONLY a valid JSON object with this structure:

{{
  "overall_risk": "low|medium|high",
  "confidence": 0.8-1.0,
  "summary": "2-3 sentence executive summary of legal risks",

  "clauses": [
    {{
      "section": "Section name",
      "clause_id": "1.1",
      "classification": "STANDARD|UNUSUAL|PROBLEMATIC",
      "risk_level": "low|medium|high",
      "legal_reasoning": "Detailed legal analysis with specific concerns",
      "consumer_impact": "How this affects users in practice",
      "relevant_law": "Applicable laws or regulations (if any)",
      "recommendation": "Specific action or awareness needed"
    }}
  ],

  "legal_concerns": [
    {{
      "issue": "Brief issue title",
      "severity": "low|medium|high",
      "description": "Detailed explanation of legal concern",
      "affected_clauses": ["1.1", "2.3"],
      "legal_basis": "Why this is concerning under law"
    }}
  ],

  "consumer_impact": {{
    "financial_risk": "low|medium|high",
    "rights_waived": ["List of rights consumers give up"],
    "hidden_obligations": ["Obligations not clearly disclosed"],
    "enforceability_concerns": ["Clauses that may not be enforceable"]
  }},

  "recommendations": [
    "Specific recommendation 1",
    "Specific recommendation 2",
    ...
  ],

  "industry_comparison": "How this compares to typical {industry} T&Cs",
  "overall_assessment": "Comprehensive final assessment"
}}

CRITICAL INSTRUCTIONS:
- Be thorough but precise. Every claim must be defensible.
- Reference specific legal principles when identifying issues.
- Distinguish between "unusual" and "illegal/unenforceable".
- Consider jurisdiction (assume US consumer protection law if not specified).
- Stage 2 should have high confidence (0.8-1.0) - you have full context and reasoning power.
- Return ONLY the JSON object, no markdown formatting.

JSON Response:"""

        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        Parse GPT-5 deep analysis response.

        Validates comprehensive analysis structure.
        """
        try:
            result = json.loads(response)

            # Validate required fields
            required_fields = [
                "overall_risk",
                "confidence",
                "summary",
                "clauses",
                "legal_concerns",
                "recommendations"
            ]

            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # Validate confidence (Stage 2 should be high)
            confidence = result["confidence"]
            if not isinstance(confidence, (int, float)):
                raise ValueError("Confidence must be numeric")

            if confidence < 0.8 or confidence > 1.0:
                logger.warning(f"Stage 2 confidence {confidence} unusual, clamping to 0.8-1.0")
                result["confidence"] = max(0.8, min(1.0, confidence))

            # Validate overall_risk
            if result["overall_risk"] not in ["low", "medium", "high"]:
                raise ValueError(f"Invalid overall_risk: {result['overall_risk']}")

            # Validate structure
            if not isinstance(result["clauses"], list):
                raise ValueError("Clauses must be a list")

            if not isinstance(result["legal_concerns"], list):
                raise ValueError("Legal concerns must be a list")

            logger.debug(
                f"Parsed Stage 2 response: {len(result['clauses'])} clauses, "
                f"{len(result['legal_concerns'])} legal concerns"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise

    def _fallback_parse(
        self,
        response: str,
        document_id: str,
        start_time: float
    ) -> Dict[str, Any]:
        """
        Fallback parsing when JSON parsing fails.

        More sophisticated than Stage 1 fallback since Stage 2 is expensive.
        """
        logger.warning("Attempting fallback parsing of Stage 2 response")

        # Try to extract key information
        confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', response)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.85

        risk_match = re.search(r'"overall_risk"\s*:\s*"(low|medium|high)"', response)
        overall_risk = risk_match.group(1) if risk_match else "medium"

        # Extract summary if possible
        summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', response)
        summary = summary_match.group(1) if summary_match else (
            "Stage 2 analysis completed but response parsing failed. "
            "Manual review recommended."
        )

        fallback_result = {
            "overall_risk": overall_risk,
            "confidence": confidence,
            "summary": summary,
            "clauses": [],
            "legal_concerns": [{
                "issue": "Response Parsing Error",
                "severity": "medium",
                "description": "Stage 2 analysis completed but structured data extraction failed",
                "affected_clauses": [],
                "legal_basis": "Manual review required"
            }],
            "consumer_impact": {
                "financial_risk": "unknown",
                "rights_waived": [],
                "hidden_obligations": [],
                "enforceability_concerns": []
            },
            "recommendations": [
                "Manual legal review recommended due to parsing error",
                "Full GPT-5 analysis was performed but structured extraction failed"
            ],
            "industry_comparison": "Unable to extract from malformed response",
            "overall_assessment": summary,
            "cost": 0.015,  # Estimated
            "processing_time": round(time.time() - start_time, 2),
            "stage": 2,
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "requires_escalation": False,
            "parsing_error": True
        }

        logger.warning(f"Stage 2 fallback result: {fallback_result['overall_risk']}")
        return fallback_result

    def _validate_stage1(
        self,
        stage1_result: Dict[str, Any],
        stage2_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate Stage 1 classification against Stage 2 findings.

        Helps measure Stage 1 accuracy and refine confidence thresholds.
        """
        stage1_risk = stage1_result.get("overall_risk", "unknown")
        stage2_risk = stage2_result.get("overall_risk", "unknown")

        agreement = stage1_risk == stage2_risk

        # Count anomalies flagged in each stage
        stage1_anomalies = len([
            c for c in stage1_result.get("clauses", [])
            if c.get("classification") in ["ANOMALY", "FLAGGED"]
        ])

        stage2_problems = len([
            c for c in stage2_result.get("clauses", [])
            if c.get("classification") in ["PROBLEMATIC", "UNUSUAL"]
        ])

        validation = {
            "agreement": agreement,
            "stage1_risk": stage1_risk,
            "stage2_risk": stage2_risk,
            "stage1_anomaly_count": stage1_anomalies,
            "stage2_problem_count": stage2_problems,
            "stage1_confidence": stage1_result.get("confidence", 0),
            "assessment": "confirmed" if agreement else "refined"
        }

        if not agreement:
            logger.info(
                f"Stage 2 refined Stage 1 assessment: "
                f"{stage1_risk} → {stage2_risk} "
                f"(Stage 1 confidence was {stage1_result.get('confidence', 0):.2f})"
            )
        else:
            logger.info(
                f"Stage 2 confirmed Stage 1 assessment: {stage1_risk} "
                f"(Stage 1 was correct despite low confidence)"
            )

        return validation

    def _calculate_cost(self, input_tokens: float, output_tokens: float) -> float:
        """
        Calculate API call cost for GPT-5.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT_TOKENS
        output_cost = (output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT_TOKENS
        total_cost = input_cost + output_cost

        logger.debug(
            f"Stage 2 cost: {input_tokens:.0f} input tokens, "
            f"{output_tokens:.0f} output tokens = ${total_cost:.6f}"
        )

        return round(total_cost, 6)
