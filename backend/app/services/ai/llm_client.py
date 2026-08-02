"""
Thin wrapper around the Anthropic API shared by all AI agents.

If no ANTHROPIC_API_KEY is configured, `is_available` is False and
callers fall back to their deterministic/rule-based paths. This keeps
the whole app runnable and testable without any external credentials,
while still being "real" when a key is supplied.
"""
from __future__ import annotations

from app.core.config import get_settings

settings = get_settings()


class LLMClient:
    def __init__(self):
        self._client = None
        if settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            except Exception:
                self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def complete(self, system: str, user: str, max_tokens: int = 800) -> str:
        if not self.is_available:
            raise RuntimeError("LLM client not configured (no ANTHROPIC_API_KEY set).")
        response = self._client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
