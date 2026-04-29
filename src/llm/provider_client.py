"""Provider-aware LLM client for Anthropic and OpenAI backends."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Literal, Type, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

from src.logging_config import get_logger

try:
    from anthropic import Anthropic, APIConnectionError as AnthropicAPIConnectionError
    from anthropic import APIStatusError as AnthropicAPIStatusError
    from anthropic import APITimeoutError as AnthropicAPITimeoutError
except ImportError:  # pragma: no cover - optional until dependency is installed
    Anthropic = None  # type: ignore[assignment]
    AnthropicAPIStatusError = AnthropicAPIConnectionError = AnthropicAPITimeoutError = ()  # type: ignore[assignment]

try:
    from openai import APIConnectionError as OpenAIAPIConnectionError
    from openai import APIStatusError as OpenAIAPIStatusError
    from openai import APITimeoutError as OpenAIAPITimeoutError
    from openai import BadRequestError as OpenAIBadRequestError
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional until dependency is installed
    OpenAI = None  # type: ignore[assignment]
    OpenAIAPIStatusError = OpenAIAPIConnectionError = OpenAIAPITimeoutError = ()  # type: ignore[assignment]
    OpenAIBadRequestError = ()  # type: ignore[assignment]

T = TypeVar("T", bound=BaseModel)
LLMProvider = Literal["anthropic", "openai", "deepseek"]
LLMMode = Literal["api-key", "setup-token"]

load_dotenv()

logger = get_logger("llm.provider_client")

_MODEL_FAMILY_MAX_TOKENS: list[tuple[str, int]] = [
    ("claude-opus", 32000),
    ("claude-sonnet", 16000),
    ("claude-haiku", 8192),
    # Keep DeepSeek conservative by default; users can opt in to higher budgets via LLM_MAX_TOKENS.
    ("deepseek-", 8192),
    ("gpt-5", 8192),
    ("gpt-4.1", 8192),
    ("gpt-4o", 8192),
    ("o1", 8192),
    ("o3", 8192),
    ("o4", 8192),
]
_DEFAULT_MAX_TOKENS = 8192
_OPENAI_MODEL_PREFIXES = (
    "gpt-",
    "o1",
    "o3",
    "o4",
    "codex-",
    "computer-use-preview",
)
_DEEPSEEK_MODEL_PREFIXES = ("deepseek-",)
_DEEPSEEK_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


def _resolve_int_env(name: str, default: int) -> int:
    """Read an integer from an environment variable, falling back to *default*."""
    val = os.environ.get(name, "").strip()
    if val:
        try:
            return int(val)
        except ValueError:
            logger.warning("Invalid %s=%r, using default %d", name, val, default)
    return default


def _resolve_max_tokens(model: str) -> int:
    """Return max output tokens from env var, or fall back to a heuristic."""
    env_val = os.environ.get("LLM_MAX_TOKENS", "").strip()
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            logger.warning("Invalid LLM_MAX_TOKENS=%r, ignoring", env_val)
    for prefix, limit in _MODEL_FAMILY_MAX_TOKENS:
        if model.startswith(prefix):
            return limit
    return _DEFAULT_MAX_TOKENS


def _is_openai_model(model: str) -> bool:
    """Best-effort detection for OpenAI model names."""
    return model.startswith(_OPENAI_MODEL_PREFIXES)


def _is_deepseek_model(model: str) -> bool:
    """Best-effort detection for DeepSeek model names."""
    return model.startswith(_DEEPSEEK_MODEL_PREFIXES)


def resolve_llm_mode() -> LLMMode:
    """Resolve the configured LLM connection mode."""
    raw_mode = os.environ.get("LLM_MODE", "api-key").strip().lower()
    if raw_mode not in ("api-key", "setup-token"):
        logger.warning("Unknown LLM_MODE=%r, defaulting to api-key", raw_mode)
        return "api-key"
    return raw_mode  # type: ignore[return-value]


def resolve_llm_provider(
    model: str | None = None,
    provider: str | None = None,
) -> LLMProvider:
    """Resolve provider from explicit config, env, or model naming."""
    raw_provider = (provider or os.environ.get("LLM_PROVIDER", "")).strip().lower()
    if raw_provider in ("anthropic", "openai", "deepseek"):
        return raw_provider  # type: ignore[return-value]

    candidate_model = (model or os.environ.get("LLM_MODEL", "")).strip().lower()
    if candidate_model and _is_deepseek_model(candidate_model):
        return "deepseek"
    if candidate_model and _is_openai_model(candidate_model):
        return "openai"
    return "anthropic"


def _resolve_key_env_name(provider: LLMProvider) -> str:
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "deepseek":
        return "DEEPSEEK_API_KEY"
    return "ANTHROPIC_API_KEY"


def resolve_llm_api_key(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    mode: str | None = None,
) -> str:
    """Resolve the API key for the active provider."""
    resolved_provider = resolve_llm_provider(model=model, provider=provider)
    resolved_mode = resolve_llm_mode() if mode is None else mode.strip().lower()

    if resolved_mode == "setup-token":
        return "setup-token-placeholder"
    if api_key:
        return api_key
    return os.environ.get(_resolve_key_env_name(resolved_provider), "")


def _normalize_openai_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def resolve_llm_base_url(
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    mode: str | None = None,
) -> str | None:
    """Resolve the base URL for the active provider and mode."""
    resolved_provider = resolve_llm_provider(model=model, provider=provider)
    resolved_mode = resolve_llm_mode() if mode is None else mode.strip().lower()

    if base_url:
        return (
            _normalize_openai_base_url(base_url)
            if resolved_provider in ("openai", "deepseek")
            else base_url
        )

    if resolved_mode == "setup-token":
        if resolved_provider == "deepseek":
            return None
        proxy_url = os.environ.get("LLM_PROXY_URL", "http://localhost:8317")
        return (
            _normalize_openai_base_url(proxy_url)
            if resolved_provider == "openai"
            else proxy_url
        )

    if resolved_provider == "openai":
        configured = os.environ.get("OPENAI_BASE_URL", "").strip()
        return _normalize_openai_base_url(configured) if configured else None
    if resolved_provider == "deepseek":
        configured = os.environ.get("DEEPSEEK_BASE_URL", "").strip()
        return _normalize_openai_base_url(configured) if configured else _DEEPSEEK_DEFAULT_BASE_URL

    return None


def is_llm_ready(
    provider: str | None = None,
    model: str | None = None,
    mode: str | None = None,
) -> bool:
    """Return whether the configured LLM backend is ready to serve requests."""
    resolved_mode = resolve_llm_mode() if mode is None else mode.strip().lower()
    if resolved_mode == "setup-token":
        return resolve_llm_provider(model=model, provider=provider) != "deepseek"

    env_name = _resolve_key_env_name(resolve_llm_provider(model=model, provider=provider))
    return bool(os.environ.get(env_name))


class LLMClient:
    """Provider-aware wrapper for structured LLM interactions."""

    _STRUCTURED_MAX_RETRIES = 2
    _STREAM_MAX_RETRIES = 3
    _STREAM_RETRY_BASE_DELAY = 2.0
    _ANTHROPIC_TRANSIENT_ERRORS = tuple(
        exc
        for exc in (
            AnthropicAPIStatusError,
            AnthropicAPIConnectionError,
            AnthropicAPITimeoutError,
        )
        if exc
    )
    _OPENAI_TRANSIENT_ERRORS = tuple(
        exc
        for exc in (
            OpenAIAPIStatusError,
            OpenAIAPIConnectionError,
            OpenAIAPITimeoutError,
        )
        if exc
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int | None = None,
        base_url: str | None = None,
        provider: str | None = None,
    ):
        self.model = model
        self.provider = resolve_llm_provider(model=model, provider=provider)
        self.mode = resolve_llm_mode()
        self.max_tokens = max_tokens or _resolve_max_tokens(model)
        self.max_continuations = _resolve_int_env("LLM_MAX_CONTINUATIONS", 3)
        self.api_key = resolve_llm_api_key(
            provider=self.provider,
            model=model,
            api_key=api_key,
            mode=self.mode,
        )
        self.base_url = resolve_llm_base_url(
            provider=self.provider,
            model=model,
            base_url=base_url,
            mode=self.mode,
        )
        self._client: Any | None = None

        has_key = bool(self.api_key and self.api_key.startswith("sk-"))
        logger.info(
            "LLMClient init: provider=%s, mode=%s, has_key=%s, base_url=%s, model=%s",
            self.provider,
            self.mode,
            has_key,
            self.base_url or "default",
            model,
        )

    @property
    def client(self) -> Any:
        if self._client is None:
            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url

            if self.provider == "anthropic":
                if Anthropic is None:
                    raise RuntimeError(
                        "anthropic package is not installed; install dependencies before using Anthropic models."
                    )
                self._client = Anthropic(**kwargs)
            else:
                if OpenAI is None:
                    raise RuntimeError(
                        "openai package is not installed; install dependencies before using OpenAI models."
                    )
                self._client = OpenAI(**kwargs)

            logger.debug(
                "LLM provider client created: provider=%s, base_url=%s",
                self.provider,
                self.base_url or "default",
            )
        return self._client

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from a prompt."""
        tokens = max_tokens or self.max_tokens
        prompt_preview = prompt[:120].replace("\n", " ")
        logger.info(
            "LLM request: provider=%s, model=%s, max_tokens=%d, temp=%.1f, prompt=%s...",
            self.provider,
            self.model,
            tokens,
            temperature,
            prompt_preview,
        )

        messages = [{"role": "user", "content": prompt}]
        t0 = time.perf_counter()
        try:
            text, stop_reason, in_tok, out_tok = self._stream_collect(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=tokens,
            )
            elapsed = time.perf_counter() - t0
            logger.info(
                "LLM response: %.1fs, input_tokens=%d, output_tokens=%d, stop=%s",
                elapsed,
                in_tok,
                out_tok,
                stop_reason,
            )
            return text
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            logger.error("LLM request failed after %.1fs: %s", elapsed, exc)
            raise

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Generate JSON output from a prompt."""
        json_system = (system + "\n\n" if system else "") + (
            "You must respond with valid JSON only. No markdown fences, no explanations, "
            "just the JSON object/array."
        )
        return self.generate(
            prompt,
            system=json_system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def generate_structured(
        self,
        prompt: str,
        model_class: Type[T],
        system: str = "",
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> T:
        """Generate a structured response validated against a Pydantic model."""
        tokens = max_tokens or self.max_tokens
        prompt_preview = prompt[:120].replace("\n", " ")
        logger.info(
            "LLM structured request: provider=%s, model=%s, schema=%s, max_tokens=%d, temp=%.1f, prompt=%s...",
            self.provider,
            self.model,
            model_class.__name__,
            tokens,
            temperature,
            prompt_preview,
        )

        for attempt in range(1 + self._STRUCTURED_MAX_RETRIES):
            try:
                return self._generate_json_with_continuation(
                    prompt,
                    model_class,
                    system,
                    temperature,
                    tokens,
                )
            except Exception as exc:
                if attempt < self._STRUCTURED_MAX_RETRIES:
                    logger.warning(
                        "Structured generation failed (attempt %d/%d), retrying: %s",
                        attempt + 1,
                        1 + self._STRUCTURED_MAX_RETRIES,
                        exc,
                    )
                else:
                    raise

    def _stream_collect(
        self,
        messages: list[dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str, int, int]:
        if self.provider in ("openai", "deepseek"):
            return self._openai_collect(
                messages=messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        return self._anthropic_stream_collect(
            messages=messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _anthropic_stream_collect(
        self,
        messages: list[dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str, int, int]:
        """Anthropic streaming helper with retry/backoff."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        last_exc: Exception | None = None
        for attempt in range(self._STREAM_MAX_RETRIES):
            try:
                chunks: list[str] = []
                with self.client.messages.stream(**kwargs) as stream:
                    for text in stream.text_stream:
                        chunks.append(text)
                    msg = stream.get_final_message()
                return (
                    "".join(chunks),
                    str(msg.stop_reason),
                    msg.usage.input_tokens,
                    msg.usage.output_tokens,
                )
            except self._ANTHROPIC_TRANSIENT_ERRORS as exc:
                last_exc = exc
                if isinstance(exc, AnthropicAPIStatusError) and 400 <= exc.status_code < 500:
                    raise
                delay = self._STREAM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Transient Anthropic API error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    self._STREAM_MAX_RETRIES,
                    delay,
                    exc,
                )
                time.sleep(delay)

        raise last_exc or RuntimeError("Anthropic request failed without an exception")

    def _build_openai_messages(
        self,
        messages: list[dict[str, str]],
        system: str,
    ) -> list[dict[str, str]]:
        if not system:
            return messages
        return [{"role": "system", "content": system}, *messages]

    def _openai_supports_max_completion_tokens(self, exc: Exception) -> bool:
        message = str(exc).lower()
        unsupported_markers = (
            "max_completion_tokens",
            "unrecognized request argument",
            "unknown parameter",
            "extra inputs are not permitted",
        )
        return not any(marker in message for marker in unsupported_markers)

    def _normalize_openai_stop_reason(self, stop_reason: str | None) -> str:
        if stop_reason == "length":
            return "max_tokens"
        return stop_reason or "unknown"

    def _openai_create_completion(
        self,
        messages: list[dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> Any:
        request_messages = self._build_openai_messages(messages, system)
        base_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": request_messages,
            "temperature": temperature,
        }
        if self.provider == "deepseek":
            return self.client.chat.completions.create(
                **base_kwargs,
                max_tokens=max_tokens,
            )

        try:
            return self.client.chat.completions.create(
                **base_kwargs,
                max_completion_tokens=max_tokens,
            )
        except OpenAIBadRequestError as exc:
            if self._openai_supports_max_completion_tokens(exc):
                raise
            logger.info("Retrying OpenAI request with legacy max_tokens parameter")
            return self.client.chat.completions.create(
                **base_kwargs,
                max_tokens=max_tokens,
            )

    def _openai_collect(
        self,
        messages: list[dict[str, str]],
        system: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str, int, int]:
        """OpenAI helper with retry/backoff."""
        last_exc: Exception | None = None
        for attempt in range(self._STREAM_MAX_RETRIES):
            try:
                response = self._openai_create_completion(
                    messages=messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                choice = response.choices[0]
                usage = response.usage
                content = choice.message.content or ""
                if isinstance(content, list):
                    text = "".join(
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict)
                    )
                else:
                    text = content
                return (
                    text,
                    self._normalize_openai_stop_reason(choice.finish_reason),
                    getattr(usage, "prompt_tokens", 0) or 0,
                    getattr(usage, "completion_tokens", 0) or 0,
                )
            except self._OPENAI_TRANSIENT_ERRORS as exc:
                last_exc = exc
                if isinstance(exc, OpenAIAPIStatusError) and 400 <= exc.status_code < 500:
                    raise
                delay = self._STREAM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Transient OpenAI API error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1,
                    self._STREAM_MAX_RETRIES,
                    delay,
                    exc,
                )
                time.sleep(delay)

        raise last_exc or RuntimeError("OpenAI request failed without an exception")

    def _generate_json_with_continuation(
        self,
        prompt: str,
        model_class: Type[T],
        system: str,
        temperature: float,
        max_tokens: int,
        max_continuations: int | None = None,
    ) -> T:
        """Generate JSON with automatic multi-turn continuation on truncation."""
        if max_continuations is None:
            max_continuations = self.max_continuations
        from src.utils.json_repair import repair_json

        json_system = (system + "\n\n" if system else "") + (
            "You must respond with valid JSON only. No markdown fences, no explanations, "
            "just the JSON object/array."
        )

        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
        accumulated = ""
        t0 = time.perf_counter()

        for attempt in range(1 + max_continuations):
            chunk_text, stop_reason, in_tok, out_tok = self._stream_collect(
                messages=messages,
                system=json_system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            accumulated += chunk_text

            elapsed = time.perf_counter() - t0
            logger.info(
                "LLM JSON continuation #%d: provider=%s, %.1fs, in=%d, out=%d, stop=%s, total_len=%d",
                attempt,
                self.provider,
                elapsed,
                in_tok,
                out_tok,
                stop_reason,
                len(accumulated),
            )

            if stop_reason != "max_tokens":
                data = repair_json(accumulated)
                return model_class.model_validate(data)

            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": accumulated},
                {
                    "role": "user",
                    "content": (
                        "Your JSON output was truncated. Continue writing the JSON "
                        "from EXACTLY where you stopped. Do NOT repeat any text - "
                        "just output the remaining characters to complete the JSON."
                    ),
                },
            ]
            logger.info("Output truncated, requesting continuation #%d...", attempt + 1)

        logger.warning(
            "Exhausted %d continuations (total %d chars), attempting partial parse",
            max_continuations,
            len(accumulated),
        )
        data = repair_json(accumulated)
        return model_class.model_validate(data)

    def generate_with_template(
        self,
        template_name: str,
        variables: dict,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Generate using a prompt template from the prompts directory."""
        template_path = Path(__file__).parent / "prompts" / "v1" / f"{template_name}.txt"
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")

        template = template_path.read_text(encoding="utf-8")
        prompt = template.format(**variables)
        return self.generate(prompt, system=system, temperature=temperature)
