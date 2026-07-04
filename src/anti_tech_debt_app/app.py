from __future__ import annotations

import asyncio

from anti_tech_debt_app.bootstrap.wiring import build_container
from anti_tech_debt_app.tui.repl import ReplApp


def main() -> None:
    asyncio.run(ReplApp(build_container()).run())
