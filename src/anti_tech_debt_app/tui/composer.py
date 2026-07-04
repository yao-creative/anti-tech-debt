from __future__ import annotations

from prompt_toolkit import PromptSession


class Composer:
    def __init__(self) -> None:
        self.session = PromptSession("> ")

    async def prompt_async(self) -> str:
        return await self.session.prompt_async()
