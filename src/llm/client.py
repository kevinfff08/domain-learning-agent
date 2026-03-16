"""LLM client wrapper for Anthropic API."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Type, TypeVar

from dotenv import load_dotenv
from anthropic import Anthropic, APIStatusError, APIConnectionError, APITimeoutError
from pydantic import BaseModel

from src.logging_config import get_logger

T = TypeVar("T", bound=BaseModel)

load_dotenv()

logger = get_logger("llm.client")

# Max output tokens by model family (prefix match, order matters)
_MODEL_FAMILY_MAX_TOKENS: list[tuple[str, int]] = [
    ("claude-opus", 32000),
    ("claude-sonnet", 16000),
    ("claude-haiku", 8192),
]
_DEFAULT_MAX_TOKENS = 8192


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
    """Return max output tokens from env var, or fall back to model maximum."""
    env_val = os.environ.get("LLM_MAX_TOKENS", "").strip()
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            logger.warning("Invalid LLM_MAX_TOKENS=%r, ignoring", env_val)
    # No env override → match model family by prefix
    for prefix, limit in _MODEL_FAMILY_MAX_TOKENS:
        if model.startswith(prefix):
            return limit
    return _DEFAULT_MAX_TOKENS


class LLMClient:
    """Wrapper around Anthropic API for structured LLM interactions."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int | None = None,
        base_url: str | None = None,
    ):
        self.model = model
        self.max_tokens = max_tokens or _resolve_max_tokens(model)
        self.max_continuations = _resolve_int_env("LLM_MAX_CONTINUATIONS", 3)
        self._client: Anthropic | None = None

        # Determine mode from env
        llm_mode = os.environ.get("LLM_MODE", "api-key").strip().lower()

        if llm_mode == "setup-token":
            # Route through CLIProxyAPI — api_key is ignored by proxy
            self.api_key = "setup-token-placeholder"
            self.base_url = base_url or os.environ.get(
                "LLM_PROXY_URL", "http://localhost:8317"
            )
            logger.info("LLMClient init: mode=setup-token, proxy=%s, model=%s", self.base_url, model)
        else:
            # Direct API key mode
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self.base_url = base_url
            has_key = bool(self.api_key and self.api_key.startswith("sk-"))
            logger.info("LLMClient init: mode=api-key, has_key=%s, model=%s", has_key, model)

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            kwargs: dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = Anthropic(**kwargs)
            logger.debug("Anthropic client created (base_url=%s)", self.base_url or "default")
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
        logger.info("LLM request: model=%s, max_tokens=%d, temp=%.1f, prompt=%s...", self.model, tokens, temperature, prompt_preview)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        t0 = time.perf_counter()
        try:
            text, stop_reason, in_tok, out_tok = self._stream_collect(kwargs)
            elapsed = time.perf_counter() - t0
            logger.info(
                "LLM response: %.1fs, input_tokens=%d, output_tokens=%d, stop=%s",
                elapsed, in_tok, out_tok, stop_reason,
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
        """Generate JSON output from a prompt.

        Adds instruction to return valid JSON.  Uses instance default
        max_tokens (model maximum) unless explicitly overridden.
        """
        json_system = (system + "\n\n" if system else "") + (
            "You must respond with valid JSON only. No markdown fences, no explanations, "
            "just the JSON object/array."
        )
        return self.generate(
            prompt, system=json_system, temperature=temperature,
            max_tokens=max_tokens,
        )

    _STRUCTURED_MAX_RETRIES = 2  # retry on JSON parse / validation failures

    def generate_structured(
        self,
        prompt: str,
        model_class: Type[T],
        system: str = "",
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> T:
        """Generate a structured response validated against a Pydantic model.

        Uses raw JSON mode with multi-turn continuation on truncation.
        Retries up to _STRUCTURED_MAX_RETRIES times on JSON parse or
        validation failures (LLM sometimes returns malformed JSON).
        """
        tokens = max_tokens or self.max_tokens
        prompt_preview = prompt[:120].replace("\n", " ")
        logger.info(
            "LLM structured request: model=%s, schema=%s, max_tokens=%d, temp=%.1f, prompt=%s...",
            self.model, model_class.__name__, tokens, temperature, prompt_preview,
        )
        last_exc: Exception | None = None
        for attempt in range(1 + self._STRUCTURED_MAX_RETRIES):
            try:
                return self._generate_json_with_continuation(
                    prompt, model_class, system, temperature, tokens,
                )
            except (ValueError, Exception) as exc:
                # ValueError from repair_json, ValidationError from pydantic
                last_exc = exc
                if attempt < self._STRUCTURED_MAX_RETRIES:
                    logger.warning(
                        "Structured generation failed (attempt %d/%d), retrying: %s",
                        attempt + 1, 1 + self._STRUCTURED_MAX_RETRIES, exc,
                    )
                else:
                    raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _TRANSIENT_ERRORS = (APIStatusError, APIConnectionError, APITimeoutError)
    _STREAM_MAX_RETRIES = 3
    _STREAM_RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry

    def _stream_collect(self, kwargs: dict) -> tuple[str, str, int, int]:
        """Stream an API call and return (text, stop_reason, input_tokens, output_tokens).

        Retries automatically on transient API errors (connection drops,
        unexpected EOF, timeouts) with exponential backoff.
        """
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
                    msg.stop_reason,
                    msg.usage.input_tokens,
                    msg.usage.output_tokens,
                )
            except self._TRANSIENT_ERRORS as exc:
                last_exc = exc
                # Don't retry on 4xx client errors (bad request, auth, etc.)
                if isinstance(exc, APIStatusError) and 400 <= exc.status_code < 500:
                    raise
                delay = self._STREAM_RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Transient API error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, self._STREAM_MAX_RETRIES, delay, exc,
                )
                time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    def _generate_json_with_continuation(
        self,
        prompt: str,
        model_class: Type[T],
        system: str,
        temperature: float,
        max_tokens: int,
        max_continuations: int | None = None,
    ) -> T:
        """Generate JSON with automatic multi-turn continuation on truncation.

        Uses raw JSON mode (no output_config).  If the model hits max_tokens,
        feeds the partial output back as an assistant turn and asks the model
        to continue, up to *max_continuations* times (default from LLM_MAX_CONTINUATIONS env).
        """
        if max_continuations is None:
            max_continuations = self.max_continuations
        from src.utils.json_repair import repair_json

        json_system = (system + "\n\n" if system else "") + (
            "You must respond with valid JSON only. No markdown fences, no explanations, "
            "just the JSON object/array."
        )

        messages: list[dict] = [{"role": "user", "content": prompt}]
        accumulated = ""
        total_in = 0
        total_out = 0
        t0 = time.perf_counter()

        for attempt in range(1 + max_continuations):
            kwargs: dict = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": temperature,
            }
            if json_system:
                kwargs["system"] = json_system

            chunk_text, stop_reason, in_tok, out_tok = self._stream_collect(kwargs)
            accumulated += chunk_text
            total_in += in_tok
            total_out += out_tok

            elapsed = time.perf_counter() - t0
            logger.info(
                "LLM JSON continuation #%d: %.1fs, in=%d, out=%d, stop=%s, total_len=%d",
                attempt, elapsed, in_tok, out_tok, stop_reason, len(accumulated),
            )

            if stop_reason != "max_tokens":
                # Completed — parse and return
                data = repair_json(accumulated)
                return model_class.model_validate(data)

            # Not done yet — set up continuation turn
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": accumulated},
                {
                    "role": "user",
                    "content": (
                        "Your JSON output was truncated. Continue writing the JSON "
                        "from EXACTLY where you stopped. Do NOT repeat any text — "
                        "just output the remaining characters to complete the JSON."
                    ),
                },
            ]
            logger.info("Output truncated, requesting continuation #%d...", attempt + 1)

        # Exhausted all continuations — try to parse what we have
        logger.warning(
            "Exhausted %d continuations (total %d chars), attempting partial parse",
            max_continuations, len(accumulated),
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
