"""Multi-Provider LLM Client Abstraction.

Supports: NVIDIA NIMs, OpenAI, Anthropic Claude, Google Gemini, DeepSeek.
All providers follow a unified interface. Provider switching via config/env.
"""

from __future__ import annotations
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from src.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    NVIDIA = "nvidia"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    provider: LLMProvider = LLMProvider.NVIDIA
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls, provider: LLMProvider = LLMProvider.NVIDIA) -> "LLMConfig":
        """Load configuration from environment variables for a given provider."""
        prefix = provider.value.upper()
        return cls(
            provider=provider,
            api_key=os.getenv(f"{prefix}_API_KEY", ""),
            base_url=os.getenv(f"{prefix}_BASE_URL", _default_base_url(provider)),
            model=os.getenv(f"{prefix}_MODEL", _default_model(provider)),
        )


def _default_base_url(provider: LLMProvider) -> str:
    urls = {
        LLMProvider.NVIDIA: "https://integrate.api.nvidia.com/v1",
        LLMProvider.OPENAI: "https://api.openai.com/v1",
        LLMProvider.ANTHROPIC: "https://api.anthropic.com/v1",
        LLMProvider.GOOGLE: "https://generativelanguage.googleapis.com/v1",
        LLMProvider.DEEPSEEK: "https://api.deepseek.com/v1",
    }
    return urls.get(provider, urls[LLMProvider.NVIDIA])


def _default_model(provider: LLMProvider) -> str:
    models = {
        LLMProvider.NVIDIA: "meta/llama-3.1-70b-instruct",
        LLMProvider.OPENAI: "gpt-4o",
        LLMProvider.ANTHROPIC: "claude-3-opus-20240229",
        LLMProvider.GOOGLE: "gemini-1.5-pro",
        LLMProvider.DEEPSEEK: "deepseek-chat",
    }
    return models.get(provider, models[LLMProvider.NVIDIA])


# ─── Abstract Base ───────────────────────────────────────────────────────


class LLMClient(ABC):
    """Abstract base for all LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._setup_client()

    @abstractmethod
    def _setup_client(self):
        """Initialize the provider-specific client."""

    @abstractmethod
    def chat_completion(self, messages: list[dict], **kwargs) -> str:
        """Send a chat completion request. Returns response text."""

    @abstractmethod
    def _mock_response(self, messages: list[dict]) -> str:
        """Generate mock response for demo mode."""


# ─── NVIDIA NIMs (OpenAI-Compatible) ─────────────────────────────────────


class NvidiaClient(LLMClient):
    """NVIDIA NIMs via OpenAI-compatible endpoint."""

    def _setup_client(self):
        from openai import OpenAI
        import httpx
        if self.config.api_key:
            self._client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                http_client=httpx.Client(timeout=self.config.timeout_seconds),
            )
        else:
            self._client = None

    def chat_completion(self, messages: list[dict], **kwargs) -> str:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        import httpx

        if settings.demo_mode or not self._client:
            return self._mock_response(messages)

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.RemoteProtocolError)),
        )
        def _call():
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            return response.choices[0].message.content or ""

        return _call()

    def _mock_response(self, messages: list[dict]) -> str:
        """Delegate to existing mock system."""
        from src.core.nvidia_client import NVIDIAClient
        fallback = NVIDIAClient()
        return fallback._mock_response(messages)


# ─── OpenAI ──────────────────────────────────────────────────────────────


class OpenAIClient(LLMClient):
    """OpenAI API client."""

    def _setup_client(self):
        from openai import OpenAI
        import httpx
        if self.config.api_key:
            self._client = OpenAI(
                api_key=self.config.api_key,
                http_client=httpx.Client(timeout=self.config.timeout_seconds),
            )
        else:
            self._client = None

    def chat_completion(self, messages: list[dict], **kwargs) -> str:
        if settings.demo_mode or not self._client:
            return self._mock_response(messages)

        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )
        return response.choices[0].message.content or ""

    def _mock_response(self, messages: list[dict]) -> str:
        from src.core.nvidia_client import NVIDIAClient
        return NVIDIAClient()._mock_response(messages)


# ─── Anthropic Claude ────────────────────────────────────────────────────


class AnthropicClient(LLMClient):
    """Anthropic Claude API client."""

    def _setup_client(self):
        if self.config.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.config.api_key)
            except ImportError:
                logger.warning("anthropic package not installed. Run: pip install anthropic")
                self._client = None
        else:
            self._client = None

    def chat_completion(self, messages: list[dict], **kwargs) -> str:
        if settings.demo_mode or not self._client:
            return self._mock_response(messages)

        # Convert OpenAI-format messages to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                anthropic_messages.append({"role": m["role"], "content": m["content"]})

        message = self._client.messages.create(
            model=self.config.model,
            system=system_msg or None,
            messages=anthropic_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        return message.content[0].text if message.content else ""

    def _mock_response(self, messages: list[dict]) -> str:
        from src.core.nvidia_client import NVIDIAClient
        return NVIDIAClient()._mock_response(messages)


# ─── Google Gemini ───────────────────────────────────────────────────────


class GoogleClient(LLMClient):
    """Google Gemini API client."""

    def _setup_client(self):
        if self.config.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.config.api_key)
                self._genai = genai
                self._client = genai.GenerativeModel(self.config.model)
            except ImportError:
                logger.warning("google-generativeai package not installed. Run: pip install google-generativeai")
                self._client = None
                self._genai = None
        else:
            self._client = None
            self._genai = None

    def chat_completion(self, messages: list[dict], **kwargs) -> str:
        if settings.demo_mode or not self._client:
            return self._mock_response(messages)

        # Extract system prompt and convert to Gemini format
        system_text = ""
        chat_history = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            elif m["role"] == "user":
                chat_history.append({"role": "user", "parts": [m["content"]]})
            elif m["role"] == "assistant":
                chat_history.append({"role": "model", "parts": [m["content"]]})

        if system_text:
            self._client = self._genai.GenerativeModel(
                self.config.model,
                system_instruction=system_text,
            )

        response = self._client.generate_content(chat_history)
        return response.text if response else ""

    def _mock_response(self, messages: list[dict]) -> str:
        from src.core.nvidia_client import NVIDIAClient
        return NVIDIAClient()._mock_response(messages)


# ─── DeepSeek (OpenAI-Compatible) ────────────────────────────────────────


class DeepSeekClient(LLMClient):
    """DeepSeek API (OpenAI-compatible)."""

    def _setup_client(self):
        from openai import OpenAI
        import httpx
        if self.config.api_key:
            self._client = OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                http_client=httpx.Client(timeout=self.config.timeout_seconds),
            )
        else:
            self._client = None

    def chat_completion(self, messages: list[dict], **kwargs) -> str:
        if settings.demo_mode or not self._client:
            return self._mock_response(messages)

        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )
        return response.choices[0].message.content or ""

    def _mock_response(self, messages: list[dict]) -> str:
        from src.core.nvidia_client import NVIDIAClient
        return NVIDIAClient()._mock_response(messages)


# ─── Provider Factory ────────────────────────────────────────────────────

_PROVIDER_REGISTRY: dict[LLMProvider, type[LLMClient]] = {
    LLMProvider.NVIDIA: NvidiaClient,
    LLMProvider.OPENAI: OpenAIClient,
    LLMProvider.ANTHROPIC: AnthropicClient,
    LLMProvider.GOOGLE: GoogleClient,
    LLMProvider.DEEPSEEK: DeepSeekClient,
}


def create_llm_client(provider: Optional[LLMProvider] = None, config: Optional[LLMConfig] = None) -> LLMClient:
    """Factory: create an LLM client for the given provider.

    If provider is None, reads from env var LLM_PROVIDER (default: nvidia).
    If config is None, loads from environment variables.
    """
    if provider is None:
        provider_name = os.getenv("LLM_PROVIDER", "nvidia").lower()
        provider = LLMProvider(provider_name)

    if config is None:
        config = LLMConfig.from_env(provider)

    client_class = _PROVIDER_REGISTRY.get(provider)
    if not client_class:
        logger.warning(f"Unknown provider: {provider}. Falling back to NVIDIA.")
        client_class = NvidiaClient
        config = LLMConfig.from_env(LLMProvider.NVIDIA)

    logger.info(f"Created LLM client: {provider.value} ({config.model})")
    return client_class(config)


def register_provider(name: str, client_class: type[LLMClient]):
    """Register a custom provider (for extensibility)."""
    try:
        provider = LLMProvider(name)
        _PROVIDER_REGISTRY[provider] = client_class
    except ValueError:
        logger.warning(f"Cannot register unknown provider: {name}")
