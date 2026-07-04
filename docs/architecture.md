# anti-tech-debt-app Architecture

This document describes the architecture that is actually implemented in `src/anti_tech_debt_app/`.

## Core Actors

```mermaid
flowchart LR
    User[User]
    Repl[ReplApp]
    Composer[Composer]
    Formatter[TuiFormatter]
    ThreadRuntime[ThreadRuntime]
    TurnLoop[TurnLoop]
    MockProvider[MockProvider]
    ToolRouter[ToolRouter]
    ApprovalRuntime[ApprovalRuntime]
    ToolRegistry[ToolRegistry]
    PlannerTool[PlannerTool]
    SubagentRuntime[SubagentRuntime]
    EventBus[EventBus]
    SQLiteStore[SQLiteStore]
    EventLog[EventLog]

    User --> Repl
    Repl --> Composer
    Repl --> Formatter
    Repl --> ThreadRuntime
    Repl --> EventBus

    ThreadRuntime --> TurnLoop
    ThreadRuntime --> SQLiteStore
    ThreadRuntime --> EventBus

    TurnLoop --> SQLiteStore
    TurnLoop --> EventLog
    TurnLoop --> EventBus
    TurnLoop --> MockProvider
    TurnLoop --> ToolRouter
    TurnLoop --> SubagentRuntime

    ToolRouter --> ApprovalRuntime
    ToolRouter --> ToolRegistry
    ToolRegistry --> PlannerTool

    SubagentRuntime --> EventBus
```

## Formal Class Comments

Here is the compressed markdown table organizing your components by their ownership, mutations, observations, and theoretical framings.

| Component | Owns | Mutates | Observes | Functional Framing | Category-Theoretic Framing |
| --- | --- | --- | --- | --- | --- |
| **ReplApp** | Interactive control flow for one local terminal surface; references to Composer, TuiFormatter, SlashCommands, StatusBar, and Container. | Starts and stops `ThreadRuntime` background tasks; no REPL-local thread selection remains. | EventBus subscriber stream, prompt input, slash commands, and latest runtime state. | An interpreter from user intent into runtime commands; operationally a stateful shell over an effectful stream. | A boundary morphism from terminal interactions to the internal runtime category; preserves ordering but not purity because it sequences side effects. |
| **Composer** | prompt-toolkit prompt session. | prompt-toolkit internal line-editing state only. | Raw user keystrokes and terminal input. | An effectful source of String values. | A producer object whose arrows yield user-input values in the IO category. |
| **TuiFormatter** | Rendering policy for welcome text, events, and status lines. | Console output only. | Event values and RuntimeState values. | Mostly a renderer from domain events to presentation artifacts. | A presentation functor from runtime-event structure to terminal-render structure; intentionally non-faithful because formatting drops internal detail. |
| **ThreadRuntime** | Thread lifecycle entrypoints, active-thread ownership, and the inbound turn queue loop. | Active thread selection, queue consumption progress, and background task registry. | Turn operations from the inbound queue and persisted thread rows. | A coordinator that composes user operations with turn execution. | A mediator object that composes arrows from command space into turn-execution space. |
| **TurnLoop** | One turn transaction boundary plus the canonical local runtime loop. | Persisted messages, event log entries, tool/subagent state transitions, and latest runtime state. | Prior message history, current user input, provider events, tool results, and subagent results. | A single effectful interpreter for turn execution. | A Kleisli arrow $TurnOp \to \text{Effect } TurnResult$, where effects include persistence and event emission. |
| **MockProvider** | Deterministic happy-path provider script. | Nothing outside its local coroutine progression. | TurnContext. | A pure scenario generator wrapped in async iteration. | A coalgebra for unfolding a finite stream of ProviderEvent values from one TurnContext seed. |
| **ToolRouter** | Tool dispatch policy and approval gate composition. | Published tool approval/result events. | ToolCall values, ApprovalRuntime decisions, and ToolRegistry results. | An effectful dispatcher $ToolCall \to ToolResult$. | A composition of two arrows, review and execute, with event emission as an attached writer-like effect. |
| **ApprovalRuntime** | Approval rule for whether a tool call is allowed. | No shared state in the current implementation. | ToolCall. | A predicate lifted into async form. | A boolean-valued morphism from tool-call objects into a two-point approval object. |
| **ToolRegistry** | Name-to-tool mapping. | No runtime state after construction in the current implementation. | `ToolCall.name` and tool-specific arguments. | A dictionary-backed dispatcher. | A small indexed family of morphisms selected by tool name. |
| **PlannerTool** | Planner behavior for the single built-in tool. | Nothing. | ToolCall arguments. | A total function from planner input to a ToolResult payload. | A pure morphism in the domain layer, merely lifted into async for uniformity. |
| **SubagentRuntime** | Delegated-task execution semantics for the scaffold. | `event_bridge` by publishing subagent lifecycle events. | Delegated task string and thread identifier. | A worker that returns a derived result while emitting progress events. | A product arrow $Task \to (\text{Event}^*, Result)$, approximated operationally with streamed events plus a returned value. |
| **EventBus** | Subscriber list and latest runtime state. | Subscriber registry and current runtime-state cache. | Event publications and RuntimeState publications from upstream actors. | In-memory pub-sub plus a last-value runtime-state cell. | A broadcast natural transformation from single event production into a family of subscriber queues. |
| **SQLiteStore** | Threads and messages persistence in SQLite. | `threads` table and `messages` table. | ThreadRecord and MessageRecord values passed in by higher layers. | Repository algebra for thread/message storage. | A persistence interpreter from domain records to durable relations. |
| **EventLog** | Append-only JSONL event history. | `events.jsonl`. | Event values. | A writer sink for replayable event history. | A Writer-like accumulator externalized as a file. |


## Core Queues And Event Channels

The runtime now has one explicit inbound typed queue. Tool execution and subagent execution are direct effects inside the canonical turn loop, and UI fanout happens through `EventBus`.

```mermaid
flowchart TD
    User[User Input]
    Repl[ReplApp]
    TurnInputQ[[turn_input_queue<br/>typed turn queue<br/>bounded]]
    ThreadRuntime[ThreadRuntime]
    TurnLoop[TurnLoop]
    ToolRouter[ToolRouter]
    EventBus[EventBus]
    SubscriberQ[(subscriber event queue<br/>per subscriber)]
    Printer[_print_events loop]
    Console[Rich Console]

    User --> Repl
    Repl --> TurnInputQ
    TurnInputQ --> ThreadRuntime
    ThreadRuntime --> TurnLoop
    TurnLoop --> ToolRouter
    TurnLoop --> EventBus
    ToolRouter --> EventBus
    EventBus --> SubscriberQ
    SubscriberQ --> Printer
    Printer --> Console
```

### Queue Semantics

```mermaid
classDiagram
    class TypedQueue {
      +name: str
      +put(payload)
      +get()
      +get_nowait()
      +task_done()
      +qsize() int
    }

    class QueueEnvelope {
      +name: str
      +payload: object
    }

    class StartTurn {
      +thread_id: str
      +user_input: str
    }

    class Event {
      +thread_id: str
      +type: str
      +payload: object
      +created_at: str
    }

    TypedQueue --> QueueEnvelope
    TypedQueue --> StartTurn
    TypedQueue --> Event
```

## Core Entities

```mermaid
classDiagram
    class ThreadRecord {
      +thread_id: str
      +title: str
      +created_at: str
    }

    class MessageRecord {
      +thread_id: str
      +role: str
      +content: str
      +created_at: str
    }

    class TurnContext {
      +thread_id: str
      +user_input: str
      +history: message collection
      +allow_delegate: bool
    }

    class Event {
      +thread_id: str
      +type: str
      +payload: object
      +created_at: str
    }

    class RuntimeState {
      +thread_id: str
      +thread_state: ThreadState
      +turn_state: TurnState
      +model: str
      +queue_depths: object
    }

    class ToolCall {
      +name: str
      +arguments: object
    }

    class ToolResult {
      +name: str
      +output: str
    }

    class ProviderEvent {
      +type: str
      +payload: object
    }

    ThreadRecord --> MessageRecord : owns
    TurnContext --> MessageRecord : includes history
    Event --> ThreadRecord : references by thread_id
    RuntimeState --> ThreadRecord : references by thread_id
    ToolResult --> ToolCall : resolves
```

## Happy Path

This is the current end-to-end flow implemented by `ThreadRuntime`, `TurnLoop`, `MockProvider`, `PlannerTool`, and `SubagentRuntime`.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Repl as ReplApp
    participant TR as ThreadRuntime
    participant SQ as turn_input_queue
    participant TL as TurnLoop
    participant DB as SQLiteStore
    participant Log as EventLog
    participant Provider as MockProvider
    participant Router as ToolRouter
    participant Approval as ApprovalRuntime
    participant Planner as PlannerTool
    participant Sub as SubagentRuntime
    participant Bus as EventBus

    User->>Repl: Enter prompt
    Repl->>TR: submit_turn(user_input)
    TR->>SQ: put(TurnOp(thread_id))
    TR->>SQ: get()
    TR->>TL: run(op)
    TL->>DB: list_messages(thread_id)
    TL->>DB: append user MessageRecord
    TL->>Log: append turn.started
    TL->>Bus: publish turn.started
    TL->>Provider: stream(turn_context)
    Provider-->>TL: text_delta
    TL->>Bus: publish assistant.delta
    Provider-->>TL: tool_call(planner)
    TL->>Router: execute(ToolCall)
    Router->>Approval: review(call)
    Approval-->>Router: approved
    Router->>Bus: publish tool.approval
    Router->>Planner: execute(call)
    Planner-->>Router: ToolResult
    Router->>Bus: publish tool.result
    Provider-->>TL: delegate(task)
    TL->>Sub: run(task)
    Sub->>Bus: publish subagent.started
    Sub->>Bus: publish subagent.completed
    Sub-->>TL: result
    TL->>Bus: publish assistant.note
    Provider-->>TL: final
    TL-->>TR: final_text
    TL->>DB: append assistant MessageRecord
    TL->>Log: append turn.completed
    TL->>Bus: publish turn.completed
    Bus-->>Repl: subscriber events
```

## Runtime State Path

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Running: submit_turn
    Running --> Streaming: MockProvider emits text_delta
    Streaming --> ToolExecution: tool_call
    ToolExecution --> Streaming: tool.result published
    Streaming --> Delegation: delegate
    Delegation --> Streaming: subagent.completed
    Streaming --> Completed: final + turn.completed
    Completed --> Idle
```

## Database Model

The implemented SQLite schema is intentionally minimal.

```mermaid
erDiagram
    SESSIONS {
        text thread_id PK
        text title
        text created_at
    }

    MESSAGES {
        text thread_id FK
        text role
        text content
        text created_at
    }

    THREADS ||--o{ MESSAGES : contains
```

## Persistence Model

SQLite is the source of truth for threads and messages. The JSONL event log is append-only debug and replay support.

```mermaid
flowchart LR
    TurnRunner[TurnRunner]
    SQLite[(SQLiteStore)]
    Threads[(threads table)]
    Messages[(messages table)]
    EventLog[(events.jsonl)]

    TurnRunner --> SQLite
    SQLite --> Threads
    SQLite --> Messages
    TurnRunner --> EventLog
```

## Actual Database Tables

```sql
create table if not exists threads (
  thread_id text primary key,
  title text,
  created_at text
);

create table if not exists messages (
  thread_id text,
  role text,
  content text,
  created_at text
);
```

## Notes On What Is Not Implemented Yet

- There is no HTTP or WebSocket server.
- There is no dedicated tool queue, approval queue, or subagent task queue yet.
- `EventBus` is in-memory pub-sub, not durable messaging.
- Only `planner` is wired into `ToolRegistry` in the default container.
- `OpenAICompatibleProvider` is a stub seam, not a working provider.
