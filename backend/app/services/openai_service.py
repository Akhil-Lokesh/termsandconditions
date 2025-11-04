"""
OpenAI API service wrapper.

Provides methods for:
- Embedding generation (text-embedding-3-small)
- Chat completions (GPT-4, GPT-3.5-turbo)
- Batch operations
- Retry logic
- Error handling
"""

import logging
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI, OpenAIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.utils.exceptions import EmbeddingError, LLMCompletionError

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API client with retry logic and error handling."""

    def __init__(self, cache_service=None):
        """
        Initialize OpenAI service.

        Args:
            cache_service: Optional Redis cache service for caching results
        """
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.cache = cache_service
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.gpt4_model = settings.OPENAI_MODEL_GPT4
        self.gpt35_model = settings.OPENAI_MODEL_GPT35

    @retry(
        stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OpenAIError, TimeoutError)),
    )
    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text with caching.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            # Check cache first
            if self.cache:
                cache_key = f"embedding:{hash(text)}"
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for embedding: {cache_key[:20]}...")
                    return cached

            # Call OpenAI API
            logger.debug(f"Generating embedding for text ({len(text)} chars)")
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )

            embedding = response.data[0].embedding

            # Cache result (24 hour TTL)
            if self.cache:
                await self.cache.set(cache_key, embedding, ttl=86400)

            logger.debug(f"Generated embedding with dimension {len(embedding)}")
            return embedding

        except OpenAIError as e:
            logger.error(f"OpenAI API error during embedding: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during embedding: {e}", exc_info=True)
            raise EmbeddingError(f"Unexpected error: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OpenAIError, TimeoutError)),
    )
    async def batch_create_embeddings(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings in batches for efficiency.

        Args:
            texts: List of input texts
            batch_size: Number of texts per batch (max 100 for OpenAI)

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If batch embedding generation fails
        """
        try:
            all_embeddings = []

            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                logger.debug(
                    f"Generating embeddings for batch {i // batch_size + 1} "
                    f"({len(batch)} texts)"
                )

                response = await self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch,
                )

                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            logger.info(f"Generated {len(all_embeddings)} embeddings in total")
            return all_embeddings

        except OpenAIError as e:
            logger.error(f"OpenAI API error during batch embedding: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"Unexpected error during batch embedding: {e}", exc_info=True
            )
            raise EmbeddingError(f"Unexpected error: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(settings.OPENAI_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OpenAIError, TimeoutError)),
    )
    async def create_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        system_message: Optional[str] = None,
    ) -> str:
        """
        Generate chat completion using GPT-4 or GPT-3.5-turbo.

        Args:
            prompt: User prompt/question
            model: Model to use (defaults to GPT-4)
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum tokens in response
            system_message: Optional system message for context

        Returns:
            Generated completion text

        Raises:
            LLMCompletionError: If completion generation fails
        """
        try:
            model = model or self.gpt4_model

            # Build messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            logger.debug(
                f"Generating completion with {model} "
                f"(temp={temperature}, max_tokens={max_tokens})"
            )

            # Handle different model types:
            # - GPT-5-Nano (reasoning model): No temperature parameter, uses max_completion_tokens
            # - GPT-5 (full model): Supports temperature=1.0, uses max_completion_tokens
            # - O1 models (reasoning): No temperature parameter, uses max_completion_tokens
            # - GPT-4/3.5: Supports temperature, uses max_tokens

            if "gpt-5-nano" in model.lower():
                # GPT-5-Nano: MUST use temperature=1.0 and max_completion_tokens
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=1.0,  # Required for GPT-5-Nano
                    max_completion_tokens=max_tokens,
                    timeout=settings.OPENAI_TIMEOUT,
                )
            elif "o1-mini" in model.lower():
                # O1-mini reasoning model: No temperature parameter
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    timeout=settings.OPENAI_TIMEOUT,
                )
            elif "gpt-5" in model.lower() or "o1-preview" in model.lower():
                # GPT-5 full model: Supports temperature=1.0
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,  # Use provided temperature (typically 1.0 for GPT-5)
                    max_completion_tokens=max_tokens,
                    timeout=settings.OPENAI_TIMEOUT,
                )
            else:
                # GPT-4, GPT-3.5: Standard temperature and max_tokens
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=settings.OPENAI_TIMEOUT,
                )

            completion = response.choices[0].message.content

            logger.debug(f"Generated completion ({len(completion)} chars)")
            return completion

        except OpenAIError as e:
            logger.error(f"OpenAI API error during completion: {e}")
            raise LLMCompletionError(f"Failed to generate completion: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during completion: {e}", exc_info=True)
            raise LLMCompletionError(f"Unexpected error: {str(e)}") from e

    async def create_structured_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Generate completion expecting JSON response.

        Args:
            prompt: User prompt (should instruct to return JSON)
            model: Model to use (defaults to GPT-4)
            temperature: Sampling temperature

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
                max_tokens=2000,
            )

            # Parse JSON response
            import json

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
            logger.error(f"Failed to parse JSON from completion: {e}")
            logger.error(f"Raw completion: {completion}")
            raise LLMCompletionError(f"Invalid JSON response: {str(e)}") from e

    async def close(self):
        """Close the OpenAI client connection."""
        await self.client.close()
        logger.info("OpenAI service closed")
