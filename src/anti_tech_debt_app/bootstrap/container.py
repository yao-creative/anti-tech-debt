from __future__ import annotations

from anti_tech_debt_app.config import AppConfig
from anti_tech_debt_app.contracts.commands import TurnOp
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.persistence.event_log import EventLog
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore
from anti_tech_debt_app.providers.mock_provider import MockProvider
from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.session import SessionRuntime
from anti_tech_debt_app.runtime.subagent_runtime import SubagentRuntime
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.runtime.turn_loop import TurnLoop
from anti_tech_debt_app.tools.planner import PlannerTool
from anti_tech_debt_app.tools.registry import ToolRegistry


class Container:
    """Composition root for the local application runtime.

    Owns:
        The concrete wiring of persistence, queues, provider, tooling, and
        runtime coordinators for one process.

    Mutates:
        No meaningful runtime state after construction; it materializes the
        object graph and exposes references to stateful collaborators.

    Observes:
        AppConfig only.

    Functional framing:
        A pure-ish constructor from configuration to a runnable runtime
        algebra, modulo object allocation effects.

    Category-theoretic framing:
        A concrete interpreter that instantiates the abstract architecture by
        selecting specific morphisms for storage, provider, and tool routing.
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.store = SQLiteStore(self.config.database_path)
        self.event_log = EventLog(self.config.event_log_path)
        self.event_bus = EventBus()
        self.turn_input_queue: TypedQueue[TurnOp] = TypedQueue("turn_input", maxsize=self.config.queue_capacity)
        self.tool_registry = ToolRegistry({"planner": PlannerTool()})
        self.approvals = ApprovalRuntime(auto_approve=True)
        self.tool_router = ToolRouter(self.tool_registry, self.approvals, self.event_bus)
        self.subagent_runtime = SubagentRuntime(self.event_bus)
        self.turn_loop = TurnLoop(
            self.store,
            self.event_log,
            self.event_bus,
            MockProvider(),
            self.tool_router,
            self.subagent_runtime,
            self.config.default_model,
        )
        self.session_runtime = SessionRuntime(
            self.store,
            self.event_bus,
            self.turn_loop,
            self.turn_input_queue,
        )
        self.session_manager = self.session_runtime
        self.turn_runner = self.turn_loop
