"""Minimal LLM client for OpenRouter (OpenAI-compatible chat completions).

If no API key is configured, `generate` returns None so callers can fall back to
a deterministic rule-based narrative.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(settings.OPENROUTER_API_KEY)


def generate(prompt: str, system: str | None = None) -> str | None:
    """Return the model's text, or None if disabled or the call fails."""
    if not enabled():
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = httpx.post(
            settings.LLM_BASE_URL.rstrip("/") + "/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.LLM_MODEL,
                "messages": messages,
                "max_tokens": settings.LLM_MAX_TOKENS,
                "temperature": 0.3,
            },
            timeout=settings.LLM_TIMEOUT,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return content.strip() or None
    except Exception as exc:  # noqa: BLE001 - never let an LLM failure break the API
        log.warning("LLM request failed: %s", exc)
        return None
