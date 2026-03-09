"""LLM client wrapper for Anthropic API."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


class LLMClient:
    """Wrapper around Anthropic API for structured LLM interactions."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        base_url: str | None = None,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self._client: Anthropic | None = None

        # Determine mode from env
        llm_mode = os.environ.get("LLM_MODE", "api-key").strip().lower()

        if llm_mode == "setup-token":
            # Route through CLIProxyAPI — api_key is ignored by proxy
            self.api_key = "setup-token-placeholder"
            self.base_url = base_url or os.environ.get(
                "LLM_PROXY_URL", "http://localhost:8317"
            )
        else:
            # Direct API key mode
            self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            self.base_url = base_url

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            kwargs: dict = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = Anthropic(**kwargs)
        return self._client

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from a prompt."""
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.2,
    ) -> str:
        """Generate JSON output from a prompt.

        Adds instruction to return valid JSON.
        """
        json_system = (system + "\n\n" if system else "") + (
            "You must respond with valid JSON only. No markdown fences, no explanations, "
            "just the JSON object/array."
        )
        return self.generate(prompt, system=json_system, temperature=temperature)

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
