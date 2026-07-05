# Runtime Vs Platform State Stability

This note identifies which parts of the current design are stable platform contracts versus unstable runtime implementation details, and why that distinction matters.

## Short Answer

The unstable part is not the existence of state. The unstable part is **where state lives, who is allowed to mutate it, and whether that state is a contract or just a local runtime convenience**.

In the current scaffold:

- the **platform-shaped contracts** are relatively stable
- the **runtime-owned state topology** is still unstable

That is a reasonable trade-off for a local-first v1, but it means the runtime should be treated as implementation territory, not as the long-term platform surface.

## Stable Platform Contracts

These look stable because other implementations could preserve them while replacing most of the runtime internals:

- `TurnOp` in [src/anti_tech_debt_app/contracts/commands.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/contracts/commands.py:7)
- `RuntimeEvent` and `RuntimeState` in [src/anti_tech_debt_app/contracts/events.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/contracts/events.py:9)
- `TurnState`, `ThreadState`, and `TurnContext` in [src/anti_tech_debt_app/contracts/models.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/contracts/models.py:10)
- `ProviderAdapter` and `ProviderEvent` in [src/anti_tech_debt_app/providers/base.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/providers/base.py:10)
- `ToolCall`, `ToolResult`, and the `Tool` protocol in [src/anti_tech_debt_app/tools/registry.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/tools/registry.py:7)

Why these are platform-like:

- They describe the vocabulary of the system, not one particular in-process execution strategy.
- They are already narrow enough to survive a future server split, alternate provider, or alternate UI.
- They let the rest of the code communicate without exposing storage layout or queue internals.

## Unstable Runtime State Design

These parts currently carry state in ways that are useful but not yet architecturally settled.

### 1. `TurnLoop` is both orchestrator and state mutator

`TurnLoop` loads history, appends messages, drives provider streaming, executes tools, runs subagents, emits events, and updates runtime status in one place: [src/anti_tech_debt_app/runtime/turn_loop.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/runtime/turn_loop.py:14)

Why this is unstable:

- It mixes platform behavior with one concrete execution strategy.
- Any change to persistence, approval flow, cancellation, retries, or streaming semantics lands in the same unit.
- It makes it hard to say whether the authoritative state is:
  - persisted messages
  - event log
  - last emitted status
  - local coroutine progress

This is the biggest runtime/platform blur in the repo.

### 2. `EventBus` mixes read model and transport

`EventBus` is both:

- an event fanout channel
- a last-known status cache

See [src/anti_tech_debt_app/runtime/event_bus.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/runtime/event_bus.py:8).

Why this is unstable:

- subscriber transport and state snapshotting evolve for different reasons
- a future remote client likely wants replay, subscription cursors, and durable status projection rather than one in-memory cell
- the current `status` value is operationally useful, but it is not clearly the system of record

This is runtime convenience state, not yet platform-grade state.

### 3. `ThreadRuntime` owns lifecycle and queue execution policy together

`ThreadRuntime` publishes startup/shutdown status, owns the inbound queue, and runs the loop that drains operations into `TurnLoop`: [src/anti_tech_debt_app/runtime/thread.py](/Users/yao/projects/yao-job-search/src/anti_tech_debt_app/runtime/thread.py:15)

Why this is unstable:

- queue topology is likely to change if the runtime becomes multi-thread, remote, cancellable, or parallel
- start/stop lifecycle policy is currently tied to one process and one worker loop
- the queue depth that appears in `RuntimeState` is a local execution metric, not a durable business concept

This is a classic runtime concern that should stay replaceable.

### 4. Runtime states exist, but transitions are not the primary source of truth

The enums in `TurnState` and `ThreadState` are good stable vocabulary. But the transitions are not modeled as pure reducers or explicit transition rules. They are embedded in imperative control flow across `ThreadRuntime`, `TurnLoop`, `ToolRouter`, and `SubagentRuntime`.

Why this is unstable:

- correctness depends on control-flow discipline rather than one explicit transition model
- replay and auditing are weaker because the transition function is implicit
- alternate runtimes must copy behavior from code paths instead of from one canonical state model

The names are stable. The transition architecture is not.

### 5. Durable state is split across three authorities

Today the system has at least three meaningful state holders:

- `SQLiteStore` for thread/message durability
- `EventLog` for append-only event history
- `EventBus` for latest in-memory runtime status

That split is pragmatic, but unstable at the design level because the repo does not yet define which one is authoritative for which question.

Examples:

- "What is the conversation history?" -> `SQLiteStore`
- "What happened during execution?" -> `EventLog`
- "What is happening right now?" -> `EventBus`

This is fine operationally, but it is still a runtime design choice rather than a finalized platform model.

## Runtime Vs Platform: The Real Trade-Off

The main trade-off is this:

- **runtime-first design** optimizes for shipping a working system quickly
- **platform-first design** optimizes for replacement, extension, and correctness under change

### If you keep state in the runtime

Pros:

- faster to build
- easier to trace end-to-end locally
- fewer abstractions for a single-process happy path
- simpler debugging when one engineer is reading one code path

Cons:

- state ownership drifts across classes
- invariants are enforced socially rather than structurally
- server split or multi-client support becomes a refactor instead of an adapter
- it becomes harder to tell which states are API promises versus implementation accidents

### If you move more state into platform contracts

Pros:

- clearer authority over thread, turn, tool, and approval state
- easier replay, testing, and alternate runtimes
- better compatibility with remote execution, durable queues, and richer UIs
- fewer hidden coupling points between orchestration and persistence

Cons:

- more ceremony early
- more reducers, commands, and projections to maintain
- more indirection for a codebase that is still proving its shape
- effect-heavy features like streaming and subprocesses still need imperative interpreters anyway

## What Is Actually Stable Enough To Standardize Now

These are good candidates for platform stabilization now:

- command types entering the system
- event types leaving the core runtime
- provider and tool interfaces
- the meaning of `ThreadState` and `TurnState`
- the durable schema for threads/messages

These should remain explicitly runtime-owned for now:

- in-memory queue topology
- exact fanout mechanism
- whether status is cached in-memory or projected elsewhere
- whether one `TurnLoop` or several actors execute a turn
- the exact placement of approval and delegation steps in the interpreter

## Recommended Boundary

A practical boundary for the next iteration is:

- **Platform owns**
  - command/event contracts
  - domain state vocabulary
  - reducer-like transition rules for turn progression
  - durable persistence schema and replay semantics

- **Runtime owns**
  - task scheduling
  - async queue plumbing
  - provider streaming orchestration
  - tool/subagent execution
  - event fanout to UI clients

That keeps the runtime flexible while preventing platform semantics from being encoded only in coroutine control flow.

## Bottom Line

What is not stable today is the **state design at the runtime layer**, not the basic domain vocabulary.

The current codebase already has decent platform seeds, but the authoritative model of execution state is still spread across:

- imperative turn orchestration
- multiple storage locations
- in-memory status caching

That is the right trade-off for a v1 runtime. It is not the right trade-off if the goal is to treat the current runtime shape as the permanent platform contract.
