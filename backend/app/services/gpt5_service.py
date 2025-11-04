"""
GPT-5 Service - Correct Implementation for Responses API.

GPT-5 models (gpt-5-mini, gpt-5-nano) use the RESPONSES API, not Chat Completions.
Key differences:
- Use client.responses.create() NOT client.chat.completions.create()
- Use max_completion_tokens NOT max_tokens
- Access output via response.output_text NOT response.choices[0].message.content
- Set reasoning_effort for better quality
- Temperature is IGNORED (reasoning models have fixed temperature)
"""

import json
import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class GPT5Service:
    """
    Correct GPT-5 API implementation using Responses API.

    Works with:
    - gpt-5-mini (cheaper, faster)
    - gpt-5-nano (cheapest, fastest)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GPT-5 service.

        Args:
            api_key: OpenAI API key (uses settings.OPENAI_API_KEY if not provided)
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    async def create_response(
        self,
        prompt: str,
        model: str = "gpt-5-nano",
        reasoning_effort: str = "medium",
        max_completion_tokens: int = 2000,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Create response using GPT-5 Responses API.

        Args:
            prompt: The user prompt/question
            model: "gpt-5-nano" or "gpt-5-mini"
            reasoning_effort: "low" | "medium" | "high" (affects quality and cost)
            max_completion_tokens: Max tokens for output (NOT max_tokens!)
            response_format: Optional {"type": "json_object"} for JSON output

        Returns:
            Response text (or JSON if response_format specified)

        Raises:
            Exception: If API call fails
        """
        try:
            logger.debug(f"Creating GPT-5 response with model={model}, effort={reasoning_effort}")

            # CORRECT: Use responses.create() for GPT-5
            response = await self.client.responses.create(
                model=model,
                input_text=prompt,  # Use input_text for Responses API

                # CRITICAL PARAMETERS:
                max_completion_tokens=max_completion_tokens,  # NOT max_tokens!
                reasoning_effort=reasoning_effort,  # "low" | "medium" | "high"

                # Optional JSON formatting
                response_format=response_format,

                # Temperature is IGNORED for reasoning models (fixed by OpenAI)
                # Don't include: temperature, top_p, frequency_penalty, presence_penalty
            )

            # CORRECT: Access output_text for GPT-5 Responses API
            output_text = response.output_text

            if not output_text:
                logger.warning("GPT-5 returned empty output_text")
                raise ValueError("Empty response from GPT-5")

            logger.debug(f"GPT-5 response: {len(output_text)} chars")
            return output_text

        except Exception as e:
            logger.error(f"GPT-5 API error: {e}", exc_info=True)
            raise

    async def create_json_response(
        self,
        prompt: str,
        model: str = "gpt-5-nano",
        reasoning_effort: str = "medium",
        max_completion_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Create JSON response using GPT-5.

        Args:
            prompt: The prompt (should ask for JSON output)
            model: "gpt-5-nano" or "gpt-5-mini"
            reasoning_effort: "low" | "medium" | "high"
            max_completion_tokens: Max tokens for output

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        try:
            # Force JSON output format
            output_text = await self.create_response(
                prompt=prompt,
                model=model,
                reasoning_effort=reasoning_effort,
                max_completion_tokens=max_completion_tokens,
                response_format={"type": "json_object"}
            )

            # Parse JSON
            result = json.loads(output_text)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse GPT-5 JSON response: {e}")
            logger.error(f"Raw output: {output_text}")
            raise

    async def analyze_clause(
        self,
        clause_text: str,
        indicators: List[Dict],
        prevalence: float,
        severity_guess: str
    ) -> Dict[str, Any]:
        """
        Analyze T&C clause using GPT-5-nano for anomaly detection.

        This is the method to use in your anomaly detector.

        Args:
            clause_text: The clause to analyze
            indicators: Detected risk indicators
            prevalence: How common this clause is (0.0-1.0)
            severity_guess: Severity from indicators ("high"/"medium"/"low")

        Returns:
            Analysis dict with explanation, confirmation, confidence
        """
        prompt = f"""You are a consumer protection legal analyst. Assess this Terms & Conditions clause.

CLAUSE:
{clause_text}

DETECTED INDICATORS:
{', '.join([ind.get('indicator', ind.get('name', 'unknown')) for ind in indicators])}

PREVALENCE: Found in {prevalence*100:.0f}% of similar services

OUR ASSESSMENT: This appears to be {severity_guess.upper()} risk

YOUR TASK:
1. Confirm if {severity_guess} severity is correct
2. Explain why this clause is concerning for consumers
3. Rate your confidence (0.0 to 1.0)

RESPOND IN JSON FORMAT:
{{
  "explanation": "Why this clause matters to users (2-3 sentences)",
  "why_risky": "Specific risk to consumer",
  "confirm_severity": "HIGH or MEDIUM or LOW",
  "confidence": 0.85,
  "consumer_impact": "What this means for everyday users"
}}
"""

        try:
            result = await self.create_json_response(
                prompt=prompt,
                model="gpt-5-nano",  # Fastest, cheapest
                reasoning_effort="medium",  # Good balance
                max_completion_tokens=1000
            )

            return result

        except Exception as e:
            logger.error(f"GPT-5 clause analysis failed: {e}")

            # Fallback response
            return {
                "explanation": f"Detected {len(indicators)} risk indicators: {', '.join([ind.get('description', '') for ind in indicators[:3]])}",
                "why_risky": "Pattern matching detected concerning language",
                "confirm_severity": severity_guess.upper(),
                "confidence": 0.7,
                "consumer_impact": "Review this clause carefully"
            }


# ============================================================================
# ALTERNATIVE: Chat Completions API (if Responses API doesn't work)
# ============================================================================

class GPT5ChatFallback:
    """
    Fallback using Chat Completions API if Responses API unavailable.

    NOTE: This may not work with GPT-5 models if they require Responses API.
    Use this only if you get errors about Responses API not being available.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    async def create_response(
        self,
        prompt: str,
        model: str = "gpt-5-nano",
        max_tokens: int = 2000
    ) -> str:
        """
        Fallback using Chat Completions API.

        NOTE: May not work if GPT-5 requires Responses API.
        """
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                # Don't use temperature for reasoning models
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Chat Completions fallback failed: {e}")
            raise


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

async def example_basic_usage():
    """Example: Basic GPT-5 usage"""
    gpt5 = GPT5Service()

    response = await gpt5.create_response(
        prompt="Explain what arbitration clauses mean for consumers",
        model="gpt-5-nano",
        reasoning_effort="medium",
        max_completion_tokens=500
    )

    print(response)


async def example_json_usage():
    """Example: Get JSON response"""
    gpt5 = GPT5Service()

    result = await gpt5.create_json_response(
        prompt="""Analyze this clause and return JSON:

        "We may terminate your account at any time for any reason."

        Return: {"risk": "high/medium/low", "reason": "explanation"}
        """,
        model="gpt-5-nano",
        reasoning_effort="medium"
    )

    print(result)  # {'risk': 'high', 'reason': '...'}


async def example_anomaly_detection():
    """Example: Use in anomaly detection"""
    gpt5 = GPT5Service()

    indicators = [
        {"indicator": "unilateral_termination", "description": "Can terminate without cause"}
    ]

    analysis = await gpt5.analyze_clause(
        clause_text="We reserve the right to terminate your access at any time.",
        indicators=indicators,
        prevalence=0.25,
        severity_guess="high"
    )

    print(analysis)
    # {
    #   "explanation": "This clause allows arbitrary termination...",
    #   "confirm_severity": "HIGH",
    #   "confidence": 0.92
    # }
