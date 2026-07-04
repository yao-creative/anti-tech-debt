from __future__ import annotations

from prompt_toolkit import PromptSession


class Composer:
    """Prompt-toolkit backed source of user input lines.

    Owns:
        One interactive prompt session.

    Mutates:
        Prompt-toolkit internal editing state.

    Observes:
        Terminal keystrokes.

    Functional framing:
        An effectful source of strings.

    Category-theoretic framing:
        A producer object whose arrows yield terminal-input values in the IO
        category.
    """

    def __init__(self) -> None:
        self.session = PromptSession("> ")

    async def prompt_async(self) -> str:
        return await self.session.prompt_async()
