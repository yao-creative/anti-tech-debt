from __future__ import annotations

from anti_tech_debt_app.runtime.approval_runtime import ApprovalRuntime
from anti_tech_debt_app.tools.registry import ToolCall


async def test_approval_runtime_denies_shell_when_auto_approve_disabled() -> None:
    runtime = ApprovalRuntime(auto_approve=False)
    approved = await runtime.review(ToolCall(name="shell", arguments={"input": "echo hi"}))
    assert approved is False
