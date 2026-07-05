# Repository Guidance

## Interfaces

- Do not add interfaces everywhere by default.
- Add `Protocol`-based interfaces only at volatile boundaries where implementations are likely to vary, such as providers, tool execution, approvals, persistence, or delegated execution.
- Keep orchestration types concrete when they primarily coordinate repo-specific behavior rather than model a reusable boundary.
- Keep the composition root responsible for wiring concrete implementations to those interfaces.
- When refactoring, prefer extracting one high-leverage seam at a time instead of introducing broad interface layers across stable code.
