# anti-tech-debt-app Architecture

This document describes the architecture that is actually implemented in `src/anti_tech_debt_app/`.

## Core Actors

```mermaid
flowchart LR
    User[User]
    Repl[ReplApp]
    Composer[Composer]
    Formatter[TuiFormatter]
    SessionManager[SessionManager]
    TurnRunner[TurnRunner]
    AgentRuntime[AgentRuntime]
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
    Repl --> SessionManager
    Repl --> EventBus

    SessionManager --> TurnRunner
    SessionManager --> SQLiteStore
    SessionManager --> EventBus

    TurnRunner --> SQLiteStore
    TurnRunner --> EventLog
    TurnRunner --> EventBus
    TurnRunner --> AgentRuntime

    AgentRuntime --> MockProvider
    AgentRuntime --> ToolRouter
    AgentRuntime --> SubagentRuntime

    ToolRouter --> ApprovalRuntime
    ToolRouter --> ToolRegistry
    ToolRegistry --> PlannerTool

    SubagentRuntime --> EventBus
```

## Core Queues And Event Channels

Only two explicit typed queues are implemented today. Other interactions are direct async calls or pub-sub over `EventBus`.

```mermaid
flowchart TD
    User[User Input]
    Repl[ReplApp]
    SubmissionQ[[submission_queue<br/>TypedQueue[StartTurn]<br/>bounded]]
    SessionManager[SessionManager]
    TurnRunner[TurnRunner]
    AgentRuntime[AgentRuntime]
    ToolRouter[ToolRouter]
    EventBridge[[event_bridge<br/>TypedQueue[Event]<br/>bounded]]
    EventBus[EventBus]
    SubscriberQ[(asyncio.Queue[Event]<br/>per subscriber)]
    Printer[_print_events loop]
    Console[Rich Console]

    User --> Repl
    Repl --> SubmissionQ
    SubmissionQ --> SessionManager
    SessionManager --> TurnRunner
    TurnRunner --> AgentRuntime
    AgentRuntime --> ToolRouter
    AgentRuntime --> EventBridge
    EventBridge --> SessionManager
    SessionManager --> EventBus
    ToolRouter --> EventBus
    TurnRunner --> EventBus
    EventBus --> SubscriberQ
    SubscriberQ --> Printer
    Printer --> Console
```

### Queue Semantics

```mermaid
classDiagram
    class TypedQueue~T~ {
      +name: str
      +put(payload: T)
      +get() T
      +get_nowait() T
      +task_done()
      +qsize() int
    }

    class QueueEnvelope~T~ {
      +name: str
      +payload: T
    }

    class StartTurn {
      +session_id: str
      +user_input: str
    }

    class Event {
      +session_id: str
      +type: str
      +payload: dict[str, Any]
      +created_at: str
    }

    TypedQueue --> QueueEnvelope
    TypedQueue --> StartTurn
    TypedQueue --> Event
```

## Core Entities

```mermaid
classDiagram
    class SessionRecord {
      +session_id: str
      +title: str
      +created_at: str
    }

    class MessageRecord {
      +session_id: str
      +role: str
      +content: str
      +created_at: str
    }

    class TurnContext {
      +session_id: str
      +user_input: str
      +history: list[MessageRecord]
      +allow_delegate: bool
    }

    class Event {
      +session_id: str
      +type: str
      +payload: dict[str, Any]
      +created_at: str
    }

    class StatusSnapshot {
      +session_id: str
      +turn_state: TurnState
      +model: str
      +queue_depths: dict[str, int]
    }

    class ToolCall {
      +name: str
      +arguments: dict[str, str]
    }

    class ToolResult {
      +name: str
      +output: str
    }

    class ProviderEvent {
      +type: str
      +payload: dict[str, str]
    }

    SessionRecord --> MessageRecord : owns
    TurnContext --> MessageRecord : includes history
    Event --> SessionRecord : references by session_id
    StatusSnapshot --> SessionRecord : references by session_id
    ToolResult --> ToolCall : resolves
```

## Happy Path

This is the current end-to-end flow implemented by `MockProvider`, `PlannerTool`, and `SubagentRuntime`.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Repl as ReplApp
    participant SM as SessionManager
    participant SQ as submission_queue
    participant TR as TurnRunner
    participant DB as SQLiteStore
    participant Log as EventLog
    participant Agent as AgentRuntime
    participant Provider as MockProvider
    participant Router as ToolRouter
    participant Approval as ApprovalRuntime
    participant Planner as PlannerTool
    participant Sub as SubagentRuntime
    participant Bridge as event_bridge
    participant Bus as EventBus

    User->>Repl: Enter prompt
    Repl->>SM: submit_turn(session_id, user_input)
    SM->>SQ: put(StartTurn)
    SM->>SQ: get()
    SM->>TR: run(session_id, user_input)
    TR->>DB: list_messages(session_id)
    TR->>DB: append user MessageRecord
    TR->>Log: append turn.started
    TR->>Bus: publish turn.started
    TR->>Agent: run(TurnContext)
    Agent->>Provider: stream(turn_context)
    Provider-->>Agent: text_delta
    Agent->>Bridge: put assistant.delta
    Provider-->>Agent: tool_call(planner)
    Agent->>Router: execute(ToolCall)
    Router->>Approval: review(call)
    Approval-->>Router: approved
    Router->>Bus: publish tool.approval
    Router->>Planner: execute(call)
    Planner-->>Router: ToolResult
    Router->>Bus: publish tool.result
    Provider-->>Agent: delegate(task)
    Agent->>Sub: run(task)
    Sub->>Bridge: put subagent.started
    Sub->>Bridge: put subagent.completed
    Sub-->>Agent: result
    Agent->>Bridge: put assistant.note
    Provider-->>Agent: final
    Agent-->>TR: final_text
    TR->>DB: append assistant MessageRecord
    TR->>Log: append turn.completed
    TR->>Bus: publish turn.completed
    Bridge->>SM: bridged Event
    SM->>Bus: publish bridged Event
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
        text session_id PK
        text title
        text created_at
    }

    MESSAGES {
        text session_id FK
        text role
        text content
        text created_at
    }

    SESSIONS ||--o{ MESSAGES : contains
```

## Persistence Model

SQLite is the source of truth for sessions and messages. The JSONL event log is append-only debug and replay support.

```mermaid
flowchart LR
    TurnRunner[TurnRunner]
    SQLite[(SQLiteStore)]
    Sessions[(sessions table)]
    Messages[(messages table)]
    EventLog[(events.jsonl)]

    TurnRunner --> SQLite
    SQLite --> Sessions
    SQLite --> Messages
    TurnRunner --> EventLog
```

## Actual Database Tables

```sql
create table if not exists sessions (
  session_id text primary key,
  title text,
  created_at text
);

create table if not exists messages (
  session_id text,
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
