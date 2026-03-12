"""LLM client wrapper for Anthropic API."""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

from src.logging_config import get_logger

load_dotenv()

logger = get_logger("llm.client")

# Max output tokens by model family (prefix match, order matters)
_MODEL_FAMILY_MAX_TOKENS: list[tuple[str, int]] = [
    ("claude-opus", 32000),
    ("claude-sonnet", 16000),
    ("claude-haiku", 8192),
]
_DEFAULT_MAX_TOKENS = 8192


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
            # Use streaming to avoid SDK non-streaming timeout for large max_tokens
            chunks: list[str] = []
            input_tokens = 0
            output_tokens = 0
            stop_reason = ""
            with self.client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    chunks.append(text)
                msg = stream.get_final_message()
                input_tokens = msg.usage.input_tokens
                output_tokens = msg.usage.output_tokens
                stop_reason = msg.stop_reason

            elapsed = time.perf_counter() - t0
            logger.info(
                "LLM response: %.1fs, input_tokens=%d, output_tokens=%d, stop=%s",
                elapsed, input_tokens, output_tokens, stop_reason,
            )
            return "".join(chunks)
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
