# Design Philosophy, State Separation, And Codex Comparison

This note captures the design rationale behind the local `anti-tech-debt-app` scaffold and compares it to a stricter state-machine-first architecture and to Codex-style runtime design.

## Design Philosophy Used In The Scaffold

The scaffold does **not** fully separate immutable state, pure transition logic, and orchestration. It is intentionally a pragmatic v1.

The main design philosophies used were:

- **Thin happy path first**: get one complete local loop working before introducing a server split, richer policies, or additional queue machinery.
- **Explicit boundaries over hidden coupling**: provider, tool routing, persistence, TUI, and session coordination are split into separate classes with narrow responsibilities.
- **Typed message flow where it matters**: `StartTurn`, `Event`, `TurnContext`, `ToolCall`, and `ToolResult` make orchestration legible.
- **Local-first, server-ready seams**: the runtime is one process now, but `SessionManager`, `TurnRunner`, `AgentRuntime`, and `ProviderAdapter` are shaped so they can later sit behind an API.
- **Effects pushed to edges where practical**: storage, logging, tool execution, console rendering, and provider streaming are kept separate from the basic domain records.

## Did The Scaffold Fully Separate State From Functions And Orchestrators?

No. The separation is partial.

### What Is Separated

- **Durable state** lives in `SQLiteStore`.
- **Event history** lives in `EventLog`.
- **Transient status** lives in `EventBus`.
- **Domain records** live in `contracts/models.py`.
- **Behavior families** are partially separated into `PlannerTool`, `ApprovalRuntime`, `MockProvider`, and `ToolRouter`.
- **Orchestrators** are explicit:
  - `ReplApp`
  - `SessionManager`
  - `TurnRunner`
  - `AgentRuntime`

### What Is Not Fully Separated

- `TurnRunner` both orchestrates and mutates persistent state.
- `AgentRuntime` both interprets provider events and emits side effects directly to `event_bridge`.
- `SessionManager` is both lifecycle manager and queue consumer.
- `EventBus` mixes pub-sub with status caching.
- There is no single immutable `SessionState` or `TurnState` reduced by pure functions.
- There is no strict split between:
  - pure transition function
  - effect description
  - effect interpreter

### Best Description Of The Current Shape

The current scaffold is best described as:

- domain records
- effectful service objects
- orchestrator classes
- light queue boundaries

It is **not** best described as:

- pure state machines
- reducers
- interpreters over immutable state

## What The Stronger Separation Would Look Like

To move toward a stricter state-machine-first design:

1. Introduce explicit immutable state models:
   - `SessionState`
   - `TurnState`
   - `SubagentState`
2. Move logic into pure reducers:
   - `reduce_turn(state, event) -> state`
   - `decide_effects(state) -> list[Command]`
3. Make orchestrators thin interpreters:
   - run commands
   - persist state
   - publish events
   - call provider and tools
4. Separate command types from event types more strictly:
   - commands = intent to do work
   - events = facts that happened
   - state = fold of events

## Trade-Offs Of Making It Fully State-Machine-First

If the runtime is redesigned that way, the trade-offs are:

### Pros

- Easier correctness reasoning because state changes become explicit and auditable.
- Better testing because pure reducers are easy to unit test.
- Better replay/debugging because state can be rebuilt from events.
- Cleaner multi-actor orchestration because commands, events, and transitions stay separate.
- Easier future server split because orchestrators become transport adapters around the same core.

### Cons

- More code up front: more types, reducers, command enums, event enums, and interpreter layers.
- Slower iteration early: simple features touch state models, reducers, interpreters, and tests.
- More indirection: the design can feel ceremonious for a small local-first v1.
- Harder onboarding if contributors are not already comfortable with event-sourced or FP-style architecture.
- Some effects remain awkward anyway: streaming, cancellation, subprocesses, queues, and terminal rendering are inherently effect-heavy.

### Practical Summary

- **Current style**: faster to ship, easier to read locally, looser semantics.
- **Full separation**: slower to build, stronger invariants, easier to scale and evolve.

## Does Codex Do That?

Codex appears to do this **partially**, but not in the strongest pure-functional sense.

From the local Codex materials in this repository, Codex clearly has:

- explicit runtime states
- queue and channel boundaries
- a turn lifecycle and state-machine mindset
- separation between UI, session runtime, turn loop, tool runtime, and model stream

But Codex is not best understood as:

- everything is immutable state
- every transition is a pure reducer
- all effects are interpreted from a purely declarative core

It is better understood as:

- well-structured stateful orchestration
- explicit state machine
- explicit event flow
- explicit runtime/service boundaries

That is typically the right trade-off for an agent runtime because tool execution, streaming, approvals, subprocesses, and UI updates are deeply effect-heavy.

## Recommended Direction

For this scaffold, the practical next step is incremental strengthening rather than a full rewrite:

1. define explicit command and event enums
2. introduce explicit `SessionState` and `TurnState`
3. add pure reducers for turn progression
4. keep provider, tool, persistence, and TUI code as interpreters at the edge

That captures most of the value of stronger state separation without forcing the entire system into a fully academic architecture prematurely.
