from __future__ import annotations

import asyncio

from bootstrap.wiring import build_container
from tui.repl import ReplApp


def main() -> None:
    asyncio.run(ReplApp(build_container()).run())

if __name__ == "__main__":
    main()