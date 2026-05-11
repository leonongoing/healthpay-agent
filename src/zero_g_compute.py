"""
Multi-Provider LLM Integration Module.

Provides OpenAI-compatible LLM interface with automatic fallback chain:
    Gemma 4 (Google AI Studio) → 0G Compute → OpenAI

Priority order is configurable via HEALTHPAY_LLM_PROVIDER environment variable.

Environment variables:
    GEMINI_API_KEY:          Google AI Studio API key (for Gemma 4)
    ZG_COMPUTE_PRIVATE_KEY:  Ethereum private key for 0G Compute
    OPENAI_API_KEY:          OpenAI API key for fallback
    HEALTHPAY_LLM_PROVIDER:  Provider priority (gemma4 | 0g | openai)
"""

import logging
import os
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)

# Default models for each provider
GEMMA4_MODEL = "gemma-4-27b-it"
ZG_MODEL = "Qwen/Qwen2.5-7B-Instruct"
OPENAI_MODEL = "gpt-4o-mini"


class ZeroGComputeError(Exception):
    """Raised when all LLM providers fail."""
    pass


def _get_provider_priority() -> list[str]:
    """Get LLM provider priority from config."""
    priority = os.environ.get("HEALTHPAY_LLM_PROVIDER", "gemma4").lower()
    
    # Build fallback chain based on priority
    if priority == "gemma4":
        return ["gemma4", "0g", "openai"]
    elif priority == "0g":
        return ["0g", "gemma4", "openai"]
    elif priority == "openai":
        return ["openai", "gemma4", "0g"]
    else:
        logger.warning("Unknown LLM provider: %s, defaulting to gemma4", priority)
        return ["gemma4", "0g", "openai"]


class ZeroGLLM:
    """
    Multi-provider LLM client with automatic fallback.

    Tries providers in order: Gemma 4 → 0G Compute → OpenAI

    Usage:
        llm = ZeroGLLM()
        response = await llm.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            stream=False
        )
    """

    def __init__(self, model: Optional[str] = None):
        """
        Initialize multi-provider LLM client.

        Args:
            model: Model name (provider-specific, optional)
        """
        self.model = model
        self.provider_priority = _get_provider_priority()
        
        # Initialize clients lazily
        self._gemma4_client = None
        self._a0g_client = None
        self._openai_client = None
        self._active_provider = None

        logger.info("LLM client initialized with fallback chain: %s", " → ".join(self.provider_priority))

    def _init_gemma4(self):
        """Initialize Gemma 4 client."""
        if self._gemma4_client is not None:
            return
        
        try:
            from gemma4_client import Gemma4LLM
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                self._gemma4_client = Gemma4LLM(model=self.model or GEMMA4_MODEL, api_key=api_key)
                if self._gemma4_client.is_available():
                    logger.info("Gemma 4 client ready")
                else:
                    self._gemma4_client = None
            else:
                logger.debug("GEMINI_API_KEY not set, skipping Gemma 4")
        except Exception as e:
            logger.warning("Failed to initialize Gemma 4: %s", e)
            self._gemma4_client = None

    def _init_0g(self):
        """Initialize 0G Compute client."""
        if self._a0g_client is not None:
            return
        
        try:
            from a0g import A0G
            private_key = os.environ.get("ZG_COMPUTE_PRIVATE_KEY")
            if private_key:
                network = os.environ.get("ZG_COMPUTE_NETWORK", "testnet")
                client = A0G(private_key=private_key, network=network)
                
                # Discover providers
                services = client.get_all_services()
                if services:
                    self._a0g_client = client
                    self._a0g_provider = services[0].provider
                    logger.info("0G Compute client ready (provider: %s)", self._a0g_provider)
                else:
                    logger.debug("No 0G Compute providers found")
            else:
                logger.debug("ZG_COMPUTE_PRIVATE_KEY not set, skipping 0G")
        except ImportError:
            logger.debug("python-0g not installed, skipping 0G")
        except Exception as e:
            logger.warning("Failed to initialize 0G Compute: %s", e)
            self._a0g_client = None

    def _init_openai(self):
        """Initialize OpenAI client."""
        if self._openai_client is not None:
            return
        
        try:
            from openai import AsyncOpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self._openai_client = AsyncOpenAI(api_key=api_key)
                logger.info("OpenAI client ready")
            else:
                logger.debug("OPENAI_API_KEY not set, skipping OpenAI")
        except ImportError:
            logger.debug("openai package not installed, skipping OpenAI")
        except Exception as e:
            logger.warning("Failed to initialize OpenAI: %s", e)
            self._openai_client = None

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        Generate chat completion with automatic provider fallback.

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Response object (OpenAI-compatible format)

        Raises:
            ZeroGComputeError: If all providers fail
        """
        errors = []

        for provider in self.provider_priority:
            try:
                if provider == "gemma4":
                    self._init_gemma4()
                    if self._gemma4_client:
                        logger.debug("Trying Gemma 4...")
                        response = await self._gemma4_client.chat_completion(
                            messages=messages,
                            stream=stream,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        self._active_provider = "gemma4"
                        logger.info("✓ Using Gemma 4")
                        return response

                elif provider == "0g":
                    self._init_0g()
                    if self._a0g_client:
                        logger.debug("Trying 0G Compute...")
                        response = await self._0g_chat_completion(
                            messages=messages,
                            stream=stream,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        self._active_provider = "0g"
                        logger.info("✓ Using 0G Compute")
                        return response

                elif provider == "openai":
                    self._init_openai()
                    if self._openai_client:
                        logger.debug("Trying OpenAI...")
                        response = await self._openai_chat_completion(
                            messages=messages,
                            stream=stream,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        self._active_provider = "openai"
                        logger.info("✓ Using OpenAI")
                        return response

            except Exception as e:
                error_msg = f"{provider} failed: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                continue

        # All providers failed
        raise ZeroGComputeError(
            f"All LLM providers failed. Errors: {'; '.join(errors)}\n"
            "Configure at least one: GEMINI_API_KEY, ZG_COMPUTE_PRIVATE_KEY, or OPENAI_API_KEY"
        )

    async def _0g_chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
    ) -> Any:
        """Call 0G Compute API."""
        client = self._a0g_client.get_openai_async_client(provider=self._a0g_provider)
        
        params = {
            "model": self.model or ZG_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens

        return await client.chat.completions.create(**params)

    async def _openai_chat_completion(
        self,
        messages: list[dict[str, str]],
        stream: bool,
        temperature: float,
        max_tokens: Optional[int],
    ) -> Any:
        """Call OpenAI API."""
        params = {
            "model": self.model or OPENAI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens

        return await self._openai_client.chat.completions.create(**params)

    async def stream_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat completion tokens.

        Yields:
            Content chunks as strings
        """
        response = await self.chat_completion(
            messages=messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        async for chunk in response:
            if hasattr(chunk, "choices") and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content

    def is_using_0g(self) -> bool:
        """Check if currently using 0G Compute."""
        return self._active_provider == "0g"

    def is_using_gemma4(self) -> bool:
        """Check if currently using Gemma 4."""
        return self._active_provider == "gemma4"

    def get_active_provider(self) -> Optional[str]:
        """Get the currently active provider name."""
        return self._active_provider

    async def close(self):
        """Close client connections."""
        if self._openai_client:
            await self._openai_client.close()


# Convenience function for quick usage
async def chat(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Quick chat completion helper.

    Returns:
        Response content as string
    """
    llm = ZeroGLLM(model=model)
    try:
        response = await llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    finally:
        await llm.close()
