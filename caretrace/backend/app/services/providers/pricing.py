"""Deterministic, local cost estimation for provider calls.

Pricing is a static, inspectable table in USD per token. Local models (e.g.
Ollama) are treated as free. Unknown models or missing token counts yield a
cost of 0.0 rather than guessing.
"""

from __future__ import annotations

# USD per token, by model.
_PRICING_PER_TOKEN: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {
        "input": 0.15 / 1_000_000,
        "output": 0.60 / 1_000_000,
    },
}


def estimate_cost(
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float:
    """Estimate the USD cost of a call from token usage.

    Returns 0.0 when pricing is unknown (e.g. local models) or token counts are
    unavailable.
    """
    pricing = _PRICING_PER_TOKEN.get(model)
    if pricing is None or prompt_tokens is None or completion_tokens is None:
        return 0.0
    cost = prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]
    return round(cost, 8)
