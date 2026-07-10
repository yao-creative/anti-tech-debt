# Runtime System Map

This document captures the current local-runtime model after centralizing `RuntimeState` ownership in `ThreadRuntime`.

## Core Hierarchies

```mermaid
flowchart TD
    Container[Container<br/>composition root]
    ThreadRuntime[ThreadRuntime<br/>runtime aggregate root]
    TurnLoop[TurnLoop<br/>turn interpreter]
    ToolRouter[ToolRouter]
    SubagentRuntime[SubagentRuntime]
    Provider[ProviderAdapter]
    Store[SQLiteStore]
    EventLog[EventLog]
    EventBus[EventBus]
    TUI[StatusBar / TuiFormatter / REPL]

    Container --> ThreadRuntime
    Container --> TurnLoop
    Container --> ToolRouter
    Container --> SubagentRuntime
    Container --> Provider
    Container --> Store
    Container --> EventLog
    Container --> EventBus

    ThreadRuntime --> TurnLoop
    ThreadRuntime --> EventBus
    ThreadRuntime --> Store
    ThreadRuntime -->|TurnOp queue| ThreadRuntime
    TurnLoop --> Provider
    TurnLoop --> ToolRouter
    TurnLoop --> SubagentRuntime
    TurnLoop --> Store
    TurnLoop --> EventLog
    TurnLoop --> EventBus
    TUI --> EventBus
```

- `Container` wires concrete implementations only; it is not a state owner.
- `ThreadRuntime` is the runtime aggregate root for live execution state: active thread, worker lifecycle, queue draining, and the authoritative `RuntimeState` snapshot.
- `TurnLoop` is an interpreter for one turn. It owns sequencing and persistence side effects, but no longer owns the live status snapshot.
- `ToolRouter` and `SubagentRuntime` are subordinate effectors that emit runtime events but do not mutate status directly.
- `SQLiteStore`, `EventLog`, and `EventBus` are three distinct stores with different authority.

## Aggregates And Authorities

```mermaid
flowchart LR
    ThreadAggregate[ThreadRuntime aggregate]
    ConversationAggregate[Conversation aggregate<br/>SQLiteStore threads + messages]
    AuditLog[Execution audit<br/>EventLog]
    LiveProjection[Live runtime read model<br/>EventBus.status]
    Fanout[Transient event fanout<br/>EventBus queues]

    ThreadAggregate --> LiveProjection
    ThreadAggregate --> Fanout
    ThreadAggregate --> ConversationAggregate
    ThreadAggregate --> AuditLog
```

- `ThreadRuntime` is the only writer of `RuntimeState`.
- `SQLiteStore` is the durable source of truth for threads and messages.
- `EventLog` is a durable audit trail for coarse turn lifecycle events: `turn.started`, `turn.completed`, `turn.failed`.
- `EventBus.status` is a live in-memory projection for UI/runtime observers, not event sourcing and not an outbox.
- `EventBus` subscriber queues are transient transport only.

## States And Transitions

```mermaid
stateDiagram-v2
    [*] --> Idle: start/new_thread/resume_latest_thread
    Idle --> Running: submit_turn
    Running --> WaitingTool: provider emits tool_call
    WaitingTool --> Running: tool finishes
    Running --> WaitingSubagent: provider emits delegate
    WaitingSubagent --> Running: subagent finishes
    Running --> Completed: provider emits final
    Running --> Failed: turn exception
    WaitingTool --> Failed: tool path raises
    WaitingSubagent --> Failed: subagent path raises
    Running --> Cancelled: runtime stopped mid-turn
    WaitingTool --> Cancelled: runtime stopped mid-turn
    WaitingSubagent --> Cancelled: runtime stopped mid-turn
```

`TurnState` now has one explicit meaning: progress of the current or most recent turn for the active thread.

`ThreadState` is orthogonal to that:

```mermaid
stateDiagram-v2
    [*] --> Active: runtime start
    Active --> Stopped: runtime stop
```

- `ACTIVE + IDLE` means the runtime is running but not executing a turn.
- `ACTIVE + RUNNING|WAITING_*` means the worker is live and the active thread is mid-turn.
- `STOPPED + COMPLETED|FAILED|CANCELLED` preserves the terminal outcome of the last turn after shutdown.
- `STOPPED + IDLE` means the runtime stopped without an in-flight or completed turn.

## Boundaries And Contracts

```mermaid
flowchart TD
    UI[UI boundary]
    Runtime[Runtime orchestration boundary]
    Domain[Durable conversation boundary]
    ProviderBoundary[Provider boundary]
    ToolBoundary[Tool boundary]

    UI -->|subscribe/read status| Runtime
    Runtime -->|append/list messages| Domain
    Runtime -->|stream ProviderEvent| ProviderBoundary
    Runtime -->|ToolCall -> ToolResult| ToolBoundary
```

### Contract Summary

- `ThreadRuntime`
  - Owns active-thread lifecycle, worker task lifecycle, queue draining, and `RuntimeState` publication.
  - Contract: any live status visible to UI must have been published through `ThreadRuntime`.
- `TurnLoop`
  - Owns one-turn sequencing, message persistence, event-log append, and transient event publication.
  - Contract: it may request turn-state changes through a callback, but it does not write `EventBus.status`.
- `EventBus`
  - Owns subscriber queues and the latest cached runtime snapshot.
  - Contract: transient in-process fanout plus cached latest status; not authoritative durable history.
- `EventLog`
  - Owns append-only durable lifecycle records.
  - Contract: replayable audit of turn lifecycle, not a complete event stream.
- `SQLiteStore`
  - Owns durable conversation state.
  - Contract: authoritative source for threads and messages.

## Happy Path

```mermaid
sequenceDiagram
    participant UI as REPL/TUI
    participant TR as ThreadRuntime
    participant TL as TurnLoop
    participant P as Provider
    participant Tool as ToolRouter
    participant Sub as SubagentRuntime
    participant DB as SQLiteStore
    participant Log as EventLog
    participant Bus as EventBus

    UI->>TR: submit_turn("Fix duplicate abstractions")
    TR->>Bus: status ACTIVE/RUNNING
    TR->>TL: run(turn op, status callback)
    TL->>DB: append user message
    TL->>Log: append turn.started
    TL->>Bus: publish turn.started
    TL->>P: stream(turn context)
    P-->>TL: text_delta
    TL->>Bus: publish assistant.delta
    P-->>TL: tool_call
    TL->>TR: status callback WAITING_TOOL
    TR->>Bus: status ACTIVE/WAITING_TOOL
    TL->>Tool: execute(tool call)
    Tool->>Bus: publish tool.approval
    Tool->>Bus: publish tool.result
    TL->>TR: status callback RUNNING
    TR->>Bus: status ACTIVE/RUNNING
    P-->>TL: delegate
    TL->>TR: status callback WAITING_SUBAGENT
    TR->>Bus: status ACTIVE/WAITING_SUBAGENT
    TL->>Sub: run(task)
    Sub->>Bus: publish subagent.started
    Sub->>Bus: publish subagent.completed
    TL->>Bus: publish assistant.note
    TL->>TR: status callback RUNNING
    TR->>Bus: status ACTIVE/RUNNING
    P-->>TL: final
    TL->>DB: append assistant message
    TL->>Log: append turn.completed
    TL->>Bus: publish turn.completed
    TL->>TR: status callback COMPLETED
    TR->>Bus: status ACTIVE/COMPLETED
    UI->>TR: stop()
    TR->>Bus: status STOPPED/COMPLETED
```

### Happy Path Narrative

- The user-facing runtime enters through `ThreadRuntime`.
- `TurnLoop` performs all effectful turn work but reports turn-phase transitions upward instead of owning status.
- The UI receives two streams of information:
  - transient events through `EventBus.subscribe()`
  - the latest snapshot through `EventBus.status`
- Shutdown changes only `ThreadState` and preserves the most recent terminal `TurnState`.

## Current Gaps

- `EventBus` still combines transient transport and cached latest snapshot. The write boundary is now clean, but the storage roles are still co-located.
- There is no unsubscribe path on `EventBus`, so long-lived UIs can accumulate stale subscriber queues.
- `EventLog` only records coarse lifecycle events, not every transient event published on the bus.
- Cancellation is runtime-local: stopping the worker marks the turn `CANCELLED`, but there is no richer cancellation handshake with provider/tool/subagent components.
