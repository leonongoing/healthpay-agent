"""
Gemma 4 LLM Client via Google AI Studio (Gemini API).

Provides OpenAI-compatible interface for Gemma 4 models with automatic
retry logic and error handling. Designed as a drop-in replacement for
ZeroGLLM in the HealthPay Agent.

Supported models:
    - gemma-4-27b-it (27B, recommended for production)
    - gemma-4-31b-it (31B, highest quality)
    - gemma-4-26b-a4b-it (26B MoE, best cost/performance)
    - gemma-4-12b-it (12B, lightweight)

Environment variables:
    GEMINI_API_KEY:      Google AI Studio API key
    GEMMA4_MODEL:        Model name (default: gemma-4-27b-it)
    GEMMA4_TEMPERATURE:  Sampling temperature (default: 0.3)
    GEMMA4_MAX_TOKENS:   Max output tokens (default: 4096)
"""

import asyncio
import logging
import os
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)

# Default model for Gemma 4 (27B recommended for HealthPay)
DEFAULT_MODEL = "gemma-4-27b-it"
DEFAULT_TEMPERATURE = 0.3  # Low temperature for medical accuracy
DEFAULT_MAX_TOKENS = 4096

# Rate limit retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds


class Gemma4Error(Exception):
    """Raised when Gemma 4 API operations fail."""
    pass


def _is_gemma4_available() -> bool:
    """Check if google-genai package is installed."""
    try:
        from google import genai
        return True
    except ImportError:
        return False


def _get_config() -> dict[str, Any]:
    """Read Gemma 4 configuration from environment variables."""
    return {
        "api_key": os.environ.get("GEMINI_API_KEY", ""),
        "model": os.environ.get("GEMMA4_MODEL", DEFAULT_MODEL),
        "temperature": float(os.environ.get("GEMMA4_TEMPERATURE", str(DEFAULT_TEMPERATURE))),
        "max_tokens": int(os.environ.get("GEMMA4_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
    }


class Gemma4LLM:
    """
    OpenAI-compatible LLM client for Gemma 4 via Google AI Studio.

    Usage:
        llm = Gemma4LLM()
        response = await llm.chat_completion(
            messages=[{"role": "user", "content": "Analyze this claim..."}],
            stream=False
        )
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Gemma4LLM client.

        Args:
            model: Model name (default: gemma-4-27b-it)
            api_key: Google AI Studio API key (default: from env)
        """
        self.config = _get_config()
        self.model = model or self.config["model"]
        self.api_key = api_key or self.config["api_key"]
        self._client = None

        if not self.api_key:
            logger.warning(
                "GEMINI_API_KEY not set. Gemma 4 client will not be available. "
                "Get your key at: https://aistudio.google.com/apikey"
            )
            return

        if not _is_gemma4_available():
            logger.warning(
                "google-genai package not installed. Install with: pip install google-genai"
            )
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            logger.info("Gemma 4 client initialized (model: %s)", self.model)
        except Exception as e:
            logger.error("Failed to initialize Gemma 4 client: %s", e)
            self._client = None

    def is_available(self) -> bool:
        """Check if Gemma 4 client is available."""
        return self._client is not None

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        Generate chat completion using Gemma 4.

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Response object (OpenAI-compatible format)

        Raises:
            Gemma4Error: If API call fails after retries
        """
        if not self.is_available():
            raise Gemma4Error(
                "Gemma 4 client not available. Check GEMINI_API_KEY and google-genai installation."
            )

        # Convert OpenAI message format to Gemini format
        contents = self._convert_messages(messages)

        # Build config
        config = {
            "temperature": temperature if temperature is not None else self.config["temperature"],
            "max_output_tokens": max_tokens if max_tokens is not None else self.config["max_tokens"],
        }

        # Retry logic with model fallback for transient 500/503 errors
        fallback_models = [self.model]
        for alt in ["gemma-4-31b-it", "gemma-4-26b-a4b-it"]:
            if alt != self.model:
                fallback_models.append(alt)

        last_error = None
        for model_attempt, current_model in enumerate(fallback_models):
            for attempt in range(MAX_RETRIES):
                try:
                    response = self._client.models.generate_content(
                        model=current_model,
                        contents=contents,
                        config=config,
                    )
                    if model_attempt > 0 or attempt > 0:
                        logger.info("Succeeded with model=%s attempt=%d", current_model, attempt + 1)
                    return self._to_openai_format(response, stream=stream)

                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    is_transient = (
                        "rate limit" in error_msg or "quota" in error_msg
                        or "500" in error_msg or "internal" in error_msg
                        or "503" in error_msg or "unavailable" in error_msg
                    )
                    if is_transient and attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        logger.warning(
                            "Transient error model=%s, retry %.1fs (%d/%d): %s",
                            current_model, wait_time, attempt + 1, MAX_RETRIES, str(e)[:80]
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    logger.warning("Model %s failed: %s", current_model, str(e)[:80])
                    break  # try next fallback model

        raise Gemma4Error(f"Gemma 4 API call failed after all models/retries: {last_error}")

    def _convert_messages(self, messages: list[dict[str, str]]) -> str:
        """
        Convert OpenAI message format to Gemini content format.

        OpenAI format:
            [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

        Gemini format:
            Single string with role prefixes (system message merged into user prompt)
        """
        # Merge system messages into user context
        system_parts = []
        user_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_parts.append(content)
            elif role == "user":
                user_parts.append(content)
            elif role == "assistant":
                # For multi-turn conversations, include assistant responses
                user_parts.append(f"[Previous response]: {content}")

        # Build final prompt
        prompt_parts = []
        if system_parts:
            prompt_parts.append("System instructions:\n" + "\n".join(system_parts))
        if user_parts:
            prompt_parts.append("\n".join(user_parts))

        return "\n\n".join(prompt_parts)

    def _to_openai_format(self, response: Any, stream: bool = False) -> Any:
        """
        Convert Gemini response to OpenAI-compatible format.

        OpenAI format:
            {
                "choices": [{"message": {"role": "assistant", "content": "..."}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
            }
        """
        # Extract text from Gemini response
        try:
            content = response.text
        except Exception:
            content = str(response)

        # Build OpenAI-compatible response
        class OpenAIResponse:
            def __init__(self, content: str):
                self.choices = [
                    type('Choice', (), {
                        'message': type('Message', (), {
                            'role': 'assistant',
                            'content': content
                        })(),
                        'finish_reason': 'stop'
                    })()
                ]
                self.usage = type('Usage', (), {
                    'prompt_tokens': 0,  # Gemini doesn't provide token counts
                    'completion_tokens': 0,
                    'total_tokens': 0
                })()

        return OpenAIResponse(content)

    async def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat completion tokens.

        Note: Gemini API doesn't support streaming in the same way as OpenAI.
        This method returns the full response as a single chunk.

        Yields:
            Content chunks as strings
        """
        response = await self.chat_completion(
            messages=messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Yield full content as single chunk
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
            if content:
                yield content


# Convenience function for quick usage
async def chat(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Quick chat completion helper.

    Returns:
        Response content as string
    """
    llm = Gemma4LLM(model=model)
    response = await llm.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
