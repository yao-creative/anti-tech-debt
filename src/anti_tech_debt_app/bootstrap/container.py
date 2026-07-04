from __future__ import annotations

from anti_tech_debt_app.config import AppConfig
from anti_tech_debt_app.contracts.commands import StartTurn
from anti_tech_debt_app.contracts.events import Event
from anti_tech_debt_app.contracts.queues import TypedQueue
from anti_tech_debt_app.persistence.event_log import EventLog
from anti_tech_debt_app.persistence.sqlite_store import SQLiteStore
from anti_tech_debt_app.providers.mock_provider import MockProvider
from anti_tech_debt_app.runtime.agent_runtime import AgentRuntime
from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.runtime.event_bus import EventBus
from anti_tech_debt_app.runtime.session_manager import SessionManager
from anti_tech_debt_app.runtime.subagent_runtime import SubagentRuntime
from anti_tech_debt_app.runtime.tool_router import ToolRouter
from anti_tech_debt_app.runtime.turn_runner import TurnRunner
from anti_tech_debt_app.tools.planner import PlannerTool
from anti_tech_debt_app.tools.registry import ToolRegistry


class Container:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.store = SQLiteStore(self.config.database_path)
        self.event_log = EventLog(self.config.event_log_path)
        self.event_bus = EventBus()
        self.submission_queue: TypedQueue[StartTurn] = TypedQueue("submission", maxsize=self.config.queue_capacity)
        self.event_bridge: TypedQueue[Event] = TypedQueue("event_bridge", maxsize=self.config.queue_capacity)
        self.tool_registry = ToolRegistry({"planner": PlannerTool()})
        self.approvals = ApprovalRuntime(auto_approve=True)
        self.tool_router = ToolRouter(self.tool_registry, self.approvals, self.event_bus)
        self.subagent_runtime = SubagentRuntime(self.event_bridge)
        self.agent_runtime = AgentRuntime(MockProvider(), self.tool_router, self.subagent_runtime, self.event_bridge)
        self.turn_runner = TurnRunner(
            self.store,
            self.event_log,
            self.event_bus,
            self.agent_runtime,
            self.config.default_model,
        )
        self.session_manager = SessionManager(
            self.store,
            self.event_bus,
            self.turn_runner,
            self.submission_queue,
            self.event_bridge,
        )
