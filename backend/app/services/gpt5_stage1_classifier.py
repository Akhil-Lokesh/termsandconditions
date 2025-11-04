"""
GPT-5-Nano Stage 1 Fast Classification Service.

Fast, cheap classification of T&C documents using GPT-5-Nano.
Classifies clauses as STANDARD/FLAGGED/ANOMALY with confidence scores.
Cost: ~$0.0006 per document (vs $0.015 for GPT-4).

Stage 1 returns results immediately if confidence >= 0.55.
Low confidence cases (< 0.55) escalate to Stage 2 for deep analysis.
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


class GPT5Stage1Classifier:
    """
    Fast T&C classification using GPT-5-Nano.

    Designed for rapid triage:
    - Identifies obviously standard clauses
    - Flags potential anomalies for Stage 2 review
    - Returns high-confidence results immediately
    - Escalates uncertain cases to deep analysis
    """

    # Cost per 1M tokens (GPT-5-Nano pricing)
    COST_PER_1M_INPUT_TOKENS = 0.15  # $0.15 per 1M input tokens
    COST_PER_1M_OUTPUT_TOKENS = 0.60  # $0.60 per 1M output tokens

    # Confidence threshold for returning Stage 1 results
    CONFIDENCE_THRESHOLD = 0.55

    # Model configuration
    MODEL_NAME = "gpt-5-nano"  # Fast reasoning model for classification
    TEMPERATURE = 1.0  # GPT-5-Nano MUST use temperature=1.0 (required by OpenAI)
    MAX_TOKENS = 2000  # Sufficient for classification output

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize Stage 1 classifier.

        Args:
            openai_service: Optional OpenAI service instance
        """
        self.openai = openai_service or OpenAIService()
        self.model_name = self.MODEL_NAME

        logger.info(f"Initialized GPT5Stage1Classifier with model: {self.model_name}")

    async def classify_document(
        self, document_text: str, document_id: str, company_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Fast classification of T&C document.

        Uses GPT-5-Nano for rapid triage classification.
        Returns classification with confidence score.

        Args:
            document_text: Full text of T&C document
            document_id: Unique document identifier
            company_name: Name of company (for context)

        Returns:
            Dict with:
            - overall_risk: low/medium/high
            - confidence: 0.0-1.0 (confidence in classification)
            - clauses: List of classified clauses
            - summary: Brief risk summary
            - requires_escalation: True if confidence < 0.55
            - cost: Processing cost in USD
            - processing_time: Time in seconds
            - stage: 1 (Stage 1 classification)

        Raises:
            ValueError: If document is empty or invalid
        """
        start_time = time.time()

        # Validate input
        if not document_text or len(document_text.strip()) < 100:
            raise ValueError("Document text is too short or empty")

        logger.info(f"Starting Stage 1 classification for document {document_id}")
        logger.info(
            f"Document length: {len(document_text)} chars, Company: {company_name}"
        )

        # Build classification prompt
        prompt = self._build_classification_prompt(document_text, company_name)

        # Call GPT-5-Nano
        # Note: GPT-5-Nano doesn't use temperature parameter (reasoning model)
        try:
            response = await self.openai.create_structured_completion(
                prompt=prompt,
                model=self.model_name,
                temperature=0.0,  # Will be ignored for reasoning models by OpenAI service
            )

            # Parse JSON response
            result = self._parse_classification_response(response)

            # Calculate cost
            # Note: OpenAI API response should include usage data
            # For now, estimate based on typical token counts
            input_tokens = len(document_text.split()) * 1.3  # Rough estimate
            output_tokens = len(response.split()) * 1.3
            cost = self._calculate_cost(input_tokens, output_tokens)

            # Add metadata
            processing_time = time.time() - start_time
            result["cost"] = cost
            result["processing_time"] = round(processing_time, 2)
            result["stage"] = 1
            result["document_id"] = document_id
            result["timestamp"] = datetime.utcnow().isoformat()

            # Determine if escalation needed
            confidence = result.get("confidence", 0.0)
            result["requires_escalation"] = confidence < self.CONFIDENCE_THRESHOLD

            logger.info(
                f"Stage 1 complete: risk={result['overall_risk']}, "
                f"confidence={confidence:.2f}, "
                f"escalation={result['requires_escalation']}, "
                f"cost=${cost:.6f}, "
                f"time={processing_time:.2f}s"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            # Attempt fallback parsing
            return self._fallback_parse(response, document_id, start_time)

        except Exception as e:
            logger.error(f"Stage 1 classification failed: {e}", exc_info=True)
            raise

    def _build_classification_prompt(
        self, document_text: str, company_name: str
    ) -> str:
        """
        Build the classification prompt for GPT-5-Nano.

        Designed to be clear, concise, and focused on rapid triage.
        """
        # Truncate document if too long (Stage 1 is meant to be fast)
        max_chars = 15000  # ~4000 tokens
        if len(document_text) > max_chars:
            document_text = (
                document_text[:max_chars]
                + "\n\n[Document truncated for Stage 1 analysis]"
            )
            logger.debug(f"Truncated document to {max_chars} chars for Stage 1")

        prompt = f"""You are a T&C analyst specializing in rapid document classification for Terms & Conditions documents.

YOUR TASK:
Analyze the provided Terms & Conditions document and classify each clause as one of:
- STANDARD: Common boilerplate language found in 70%+ of similar T&Cs
- FLAGGED: Unusual or noteworthy but not necessarily problematic
- ANOMALY: Clear deviation from market standards, potentially risky

COMPANY: {company_name}

DOCUMENT TEXT:
{document_text}

PROVIDE:
1. Classification for main sections/clauses
2. Confidence score for your classification (0.0 to 1.0, where 1.0 = high confidence)
3. Brief reasoning for each anomaly flagged
4. Overall document risk assessment (low/medium/high)

CONFIDENCE SCORING:
- 0.0-0.33: Low confidence - escalate to Stage 2
- 0.34-0.54: Medium-low confidence - escalate to Stage 2
- 0.55-0.75: Medium-high confidence - can return Stage 1 result
- 0.76-1.0: High confidence - return Stage 1 result

CLAUSES TO FOCUS ON:
1. Cancellation/Termination policies
2. Payment terms and auto-renewal
3. Liability limitations and disclaimers
4. Arbitration requirements
5. Data privacy and user rights
6. Intellectual property assignments
7. Warranty disclaimers
8. Class action waivers
9. Indemnification clauses
10. Modification rights for company

OUTPUT FORMAT:
Return ONLY a valid JSON object (no markdown, no explanations) with this structure:
{{
  "overall_risk": "low|medium|high",
  "confidence": 0.0-1.0,
  "clauses": [
    {{
      "section": "Section name",
      "clause_id": "1.1",
      "classification": "STANDARD|FLAGGED|ANOMALY",
      "reason": "Brief explanation",
      "risk_level": "low|medium|high"
    }}
  ],
  "summary": "One sentence summary of overall T&C risk profile",
  "requires_escalation": true|false
}}

CRITICAL RULES:
- Be decisive. Don't over-flag. Standard clauses should be STANDARD even if slightly unusual.
- Only flag ANOMALY if it's genuinely different from industry norms.
- Confidence score reflects your certainty, not the document's risk level.
- If you find multiple serious issues, confidence should be high (0.8+) but overall_risk "high".
- Prefer escalation when uncertain - Stage 2 will do deeper analysis.

JSON Response:"""

        return prompt

    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """
        Parse GPT-5-Nano classification response.

        Expects strict JSON format. Validates required fields.
        """
        try:
            result = json.loads(response)

            # Validate required fields
            required_fields = ["overall_risk", "confidence", "clauses", "summary"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # Validate types
            if not isinstance(result["confidence"], (int, float)):
                raise ValueError("Confidence must be numeric")

            if result["confidence"] < 0.0 or result["confidence"] > 1.0:
                logger.warning(
                    f"Confidence {result['confidence']} out of range, clamping to 0-1"
                )
                result["confidence"] = max(0.0, min(1.0, result["confidence"]))

            if result["overall_risk"] not in ["low", "medium", "high"]:
                raise ValueError(f"Invalid overall_risk: {result['overall_risk']}")

            if not isinstance(result["clauses"], list):
                raise ValueError("Clauses must be a list")

            logger.debug(
                f"Parsed {len(result['clauses'])} clauses from Stage 1 response"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise

    def _fallback_parse(
        self, response: str, document_id: str, start_time: float
    ) -> Dict[str, Any]:
        """
        Fallback parsing when JSON parsing fails.

        Attempts to extract key information using regex.
        Returns conservative result requiring escalation.
        """
        logger.warning("Attempting fallback parsing of Stage 1 response")

        # Try to extract confidence score
        confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', response)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.3

        # Try to extract overall_risk
        risk_match = re.search(r'"overall_risk"\s*:\s*"(low|medium|high)"', response)
        overall_risk = risk_match.group(1) if risk_match else "medium"

        # Conservative fallback result
        fallback_result = {
            "overall_risk": overall_risk,
            "confidence": confidence,
            "clauses": [],
            "summary": "Stage 1 parsing failed - escalated to Stage 2 for detailed analysis",
            "requires_escalation": True,  # Always escalate if parsing failed
            "cost": 0.0006,  # Estimated
            "processing_time": round(time.time() - start_time, 2),
            "stage": 1,
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "parsing_error": True,
        }

        logger.warning(f"Fallback result: {fallback_result}")
        return fallback_result

    def _calculate_cost(self, input_tokens: float, output_tokens: float) -> float:
        """
        Calculate API call cost.

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
            f"Cost calculation: {input_tokens:.0f} input tokens, "
            f"{output_tokens:.0f} output tokens = ${total_cost:.6f}"
        )

        return round(total_cost, 6)

    async def classify_batch(
        self, documents: List[Dict[str, str]], batch_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple documents in batch.

        Processes documents sequentially (no parallel API calls to avoid rate limits).

        Args:
            documents: List of dicts with 'text', 'id', 'company' keys
            batch_id: Optional batch identifier for logging

        Returns:
            List of classification results
        """
        batch_id = batch_id or f"batch_{int(time.time())}"
        logger.info(
            f"Starting batch classification: {batch_id} ({len(documents)} documents)"
        )

        results = []
        total_cost = 0.0
        escalation_count = 0

        for idx, doc in enumerate(documents):
            try:
                result = await self.classify_document(
                    document_text=doc["text"],
                    document_id=doc["id"],
                    company_name=doc.get("company", "Unknown"),
                )

                results.append(result)
                total_cost += result["cost"]

                if result["requires_escalation"]:
                    escalation_count += 1

                logger.info(f"Batch progress: {idx + 1}/{len(documents)} complete")

            except Exception as e:
                logger.error(f"Failed to classify document {doc['id']}: {e}")
                # Continue with next document
                results.append(
                    {
                        "document_id": doc["id"],
                        "error": str(e),
                        "requires_escalation": True,
                        "stage": 1,
                    }
                )

        escalation_rate = (escalation_count / len(documents)) * 100 if documents else 0

        logger.info(
            f"Batch {batch_id} complete: {len(results)} results, "
            f"${total_cost:.4f} total cost, "
            f"{escalation_rate:.1f}% escalation rate"
        )

        return results
