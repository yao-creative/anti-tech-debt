from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from contracts.models import TurnContext
from contracts.ports import ProviderAdapter, ProviderEvent


class MockProvider(ProviderAdapter):
    """Deterministic provider that unfolds the scaffold happy path.

    Owns:
        The scripted event progression for one demo turn.

    Mutates:
        No shared state; only local coroutine progress.

    Observes:
        TurnContext input.

    Functional framing:
        A deterministic stream generator from one turn context.

    Category-theoretic framing:
        A coalgebra that unfolds a finite ProviderEvent stream from a single
        seed value.
    """

    async def stream(self, turn_context: TurnContext) -> AsyncIterator[ProviderEvent]:
        prompt = turn_context.user_input.strip()
        yield ProviderEvent("text_delta", {"text": "Analyzing tech debt scope...\n"})
        await asyncio.sleep(0)
        yield ProviderEvent("tool_call", {"tool": "planner", "input": prompt})
        await asyncio.sleep(0)
        if turn_context.allow_delegate:
            yield ProviderEvent("delegate", {"task": f"Audit one hotspot from: {prompt}"})
            await asyncio.sleep(0)
        yield ProviderEvent(
            "final",
            {"text": f"Happy path complete for request: {prompt}"},
        )
