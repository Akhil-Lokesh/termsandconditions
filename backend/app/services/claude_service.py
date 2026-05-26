"""
Anthropic Claude API service wrapper.

Provides methods for:
- Chat completions (Claude Sonnet 4)
- Structured JSON responses
- Retry logic
- Error handling

Note: Embeddings use local sentence-transformers model (no external API required).
"""

import json
import logging
from typing import List, Optional, Dict, Any
import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.utils.exceptions import LLMCompletionError

logger = logging.getLogger(__name__)


class ClaudeService:
    """Anthropic Claude API client with retry logic and error handling."""

    def __init__(self, cache_service=None):
        """
        Initialize Claude service.

        Args:
            cache_service: Optional Redis cache service for caching results
        """
        self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.cache = cache_service
        self.model = settings.CLAUDE_MODEL
        self.model_fast = settings.CLAUDE_MODEL_FAST

    @retry(
        stop=stop_after_attempt(settings.CLAUDE_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((anthropic.APIError, TimeoutError)),
    )
    async def create_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
        cache_system: bool = False,
    ) -> str:
        """
        Generate chat completion using Claude.

        Args:
            prompt: User prompt/question
            model: Model to use (defaults to claude-sonnet-4)
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum tokens in response
            system_message: Optional system message for context
            cache_system: If True, mark `system_message` as an ephemeral prompt-cache
                breakpoint (Anthropic prompt caching). The system block must be ≥1024
                tokens for caching to take effect on Sonnet 4.

        Returns:
            Generated completion text

        Raises:
            LLMCompletionError: If completion generation fails
        """
        try:
            model = model or self.model

            logger.debug(
                f"Generating completion with {model} "
                f"(temp={temperature}, max_tokens={max_tokens})"
            )

            # Build the request
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            # Add system message — as a content block when caching is requested
            if system_message:
                if cache_system:
                    request_params["system"] = [
                        {
                            "type": "text",
                            "text": system_message,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                else:
                    request_params["system"] = system_message

            response = await self.client.messages.create(**request_params)

            # Extract text from response
            completion = response.content[0].text

            cache_info = getattr(response, "usage", None)
            if cache_info is not None:
                cache_read = getattr(cache_info, "cache_read_input_tokens", 0) or 0
                cache_write = getattr(cache_info, "cache_creation_input_tokens", 0) or 0
                if cache_read or cache_write:
                    logger.info(
                        f"Claude cache stats — read: {cache_read} tokens, "
                        f"write: {cache_write} tokens"
                    )

            logger.debug(f"Generated completion ({len(completion)} chars)")
            return completion

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error during completion: {e}")
            raise LLMCompletionError(f"Failed to generate completion: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during completion: {e}", exc_info=True)
            raise LLMCompletionError(f"Unexpected error: {str(e)}") from e

    async def create_structured_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        system_message: Optional[str] = None,
        cache_system: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate completion expecting JSON response.

        Args:
            prompt: User prompt (should instruct to return JSON)
            model: Model to use (defaults to Claude Sonnet)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            system_message: Optional cacheable system instructions / rubric
            cache_system: Mark system block for prompt-cache reuse

        Returns:
            Parsed JSON response as dict

        Raises:
            LLMCompletionError: If completion or JSON parsing fails
        """
        try:
            completion = await self.create_completion(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_message=system_message,
                cache_system=cache_system,
            )

            # Parse JSON response
            # Try to extract JSON from markdown code blocks if present
            if "```json" in completion:
                json_start = completion.find("```json") + 7
                json_end = completion.find("```", json_start)
                completion = completion[json_start:json_end].strip()
            elif "```" in completion:
                json_start = completion.find("```") + 3
                json_end = completion.find("```", json_start)
                completion = completion[json_start:json_end].strip()

            result = json.loads(completion)
            return result

        except json.JSONDecodeError as e:
            # Attempt to repair truncated JSON (e.g., from max_tokens exhaustion)
            repaired = self._try_repair_truncated_json(completion)
            if repaired is not None:
                logger.warning(
                    f"JSON was truncated (likely max_tokens hit) — "
                    f"repaired by closing {len(completion)} char response"
                )
                return repaired
            logger.error(f"Failed to parse JSON from completion: {e}")
            logger.error(f"Raw completion (last 200 chars): ...{completion[-200:]}")
            raise LLMCompletionError(f"Invalid JSON response: {str(e)}") from e

    async def create_json_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        reasoning_effort: str = "medium",
    ) -> Dict[str, Any]:
        """
        Generate a JSON response (compatible with GPT-5 service interface).

        Args:
            prompt: User prompt
            model: Model to use
            reasoning_effort: Ignored for Claude (compatibility param)

        Returns:
            Parsed JSON response as dict
        """
        # Map reasoning effort to temperature
        temp_map = {"low": 0.3, "medium": 0.5, "high": 0.7}
        temperature = temp_map.get(reasoning_effort, 0.5)

        return await self.create_structured_completion(
            prompt=prompt,
            model=model,
            temperature=temperature,
        )

    @staticmethod
    def _count_unmatched_brackets(text: str) -> tuple:
        """Count unmatched braces/brackets, aware of JSON string boundaries."""
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape_next = False

        for ch in text:
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                open_braces += 1
            elif ch == '}':
                open_braces -= 1
            elif ch == '[':
                open_brackets += 1
            elif ch == ']':
                open_brackets -= 1

        return open_braces, open_brackets

    @staticmethod
    def _try_repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair JSON truncated by max_tokens exhaustion.

        Handles the common case where a JSON array of objects is cut off mid-entry.
        Returns parsed dict on success, None on failure.
        """
        text = text.strip()
        if not text:
            return None

        # Strip markdown fences if present
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
            last_fence = text.rfind("```")
            if last_fence > 0:
                text = text[:last_fence]
            text = text.strip()

        # Find the last complete JSON object in an array
        last_complete = text.rfind("}")
        if last_complete == -1:
            return None

        # Try progressively truncating from the end to find valid JSON
        # by closing any open brackets/braces (string-aware counting)
        for pos in range(len(text), max(len(text) - 1000, 0), -1):
            candidate = text[:pos].rstrip().rstrip(",")
            open_braces, open_brackets = ClaudeService._count_unmatched_brackets(candidate)
            if open_braces < 0 or open_brackets < 0:
                continue
            suffix = "}" * open_braces + "]" * open_brackets
            try:
                result = json.loads(candidate + suffix)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue

        return None

    async def close(self):
        """Close the Anthropic client connection."""
        await self.client.close()
        logger.info("Claude service closed")
