**Intent: architectural formalization — specifically, what a hexagonal “port” is as a mathematical/programming boundary.**

The cleanest way to think about a **port** is:

> A port is an abstract interface describing a capability that the application requires or exposes, independent of any particular implementation.

The key is that a port is **not a component** and **not an adapter**. It is a **contract at a boundary**.

---

## 1. Start with the dependency direction

Suppose your application needs persistence.

You don't want:

$$
\text{Application} \rightarrow \text{Postgres}
$$

because then the application is structurally coupled to Postgres.

Instead:

$$
\text{Application} \rightarrow \boxed{\text{Persistence Port}}
$$

and externally:

$$
\text{Postgres Adapter} \rightarrow \boxed{\text{Persistence Port}}
$$

So both sides depend on the same abstraction.

In Rust:

```rust
trait EventSink {
    fn append(&self, event: Event) -> Result<(), SinkError>;
}
```

Then:

```rust
struct PostgresEventSink {
    // ...
}

impl EventSink for PostgresEventSink {
    fn append(&self, event: Event) -> Result<(), SinkError> {
        // PostgreSQL-specific implementation
    }
}
```

The important thing is:

```text
Application knows EventSink.
Application does not know PostgresEventSink.
```

---

# 2. Set-theoretically

Let:

$$
A = \text{set of application behaviors}
$$

and let:

$$
E = \text{set of external implementations}
$$

For example:

$$
E =
\{
\text{Postgres},
\text{SQLite},
\text{DuckDB},
\text{InMemory}
\}
$$

The application doesn't actually need to know which element of $E$ it is talking to.

It only needs a **required capability**:

$$
P : A \rightarrow \text{Behavior}
$$

Conceptually, the port defines a set of operations:

$$
P = \{\text{append},\text{flush},\text{read},...\}
$$

An adapter is then an implementation of that operation set:

$$
\text{PostgresAdapter} \models P
$$

$$
\text{SQLiteAdapter} \models P
$$

$$
\text{InMemoryAdapter} \models P
$$

So:

$$
\boxed{
\text{Port} = \text{abstract behavioral contract}
}
$$

while:

$$
\boxed{
\text{Adapter} = \text{concrete realization of that contract}
}
$$

---

# 3. The category-theoretic view

This is particularly useful for the architecture you've been building.

Treat the application as one object:

$$
\mathcal A
$$

and external systems as objects:

$$
\mathcal E_1,\mathcal E_2,\ldots
$$

You don't want arbitrary morphisms:

$$
\mathcal A \rightarrow \mathcal E_{\text{Postgres}}
$$

because that makes the application depend on one particular external object.

Instead introduce an interface/object representing the required structure:

$$
\mathcal P
$$

Then:

$$
\mathcal A \rightarrow \mathcal P
$$

and implementations provide:

$$
\mathcal E_i \rightarrow \mathcal P
$$

The port therefore acts as the **stable abstraction through which the application participates in the larger category**.

In programming terms:

```rust
trait EventSink {
    fn append(&self, event: Event) -> Result<(), Error>;
}
```

is the $\mathcal P$.

Then:

```rust
struct SupabaseEventSink;
struct SqliteEventSink;
struct MemoryEventSink;
```

are objects satisfying that interface.

---

# 4. There are actually two kinds of ports

This distinction is extremely important in Hexagonal Architecture.

## Inbound port

An **inbound port** describes what the application allows the outside world to ask it to do.

For example:

```rust
trait SendMessage {
    fn send(&mut self, message: Message) -> Result<Response, Error>;
}
```

The outside world can invoke this.

Adapters:

```text
CLI adapter
HTTP adapter
TUI adapter
WebSocket adapter
```

all translate their external representation into:

$$
\text{SendMessage}
$$

So:

$$
\text{CLI} \rightarrow \boxed{\text{SendMessage}} \rightarrow \text{Application}
$$

---

## Outbound port

An **outbound port** describes something the application needs from the outside world.

For example:

```rust
trait ModelClient {
    async fn generate(
        &self,
        request: ModelRequest,
    ) -> Result<ModelResponse, ModelError>;
}
```

The application invokes this.

Adapters implement it:

```text
OpenAI adapter
Anthropic adapter
Local vLLM adapter
Mock adapter
```

So:

$$
\text{Application} \rightarrow
\boxed{\text{ModelClient}}
\leftarrow
\text{AnthropicAdapter}
$$

This is the dependency inversion.

---

# 5. The really important distinction: port ≠ interface merely because it is a trait

Not every trait is a port.

Suppose you have:

```rust
trait TokenCounter {
    fn count(&self, text: &str) -> usize;
}
```

That could just be an **internal abstraction**.

A port exists when the abstraction represents a **boundary between the application and an independently replaceable actor/system**.

For example:

```rust
trait ModelClient { ... }
trait EventSink { ... }
trait MemoryBackend { ... }
trait Tool { ... }
```

are natural ports because implementations may live outside the core application.

But something like:

```rust
trait Planner {
    fn plan(...);
}
```

might simply be an internal domain abstraction.

So a useful test is:

> **If I replace the thing on the other side of this interface without changing the application/domain, is this interface the contract that makes that replacement possible?**

If yes → likely a port.

---

# 6. Port vs adapter algebraically

You can think of it as a factorization.

Without hexagonal architecture:

$$
A \xrightarrow{f} E
$$

where $A$ is application code and $E$ is some external technology.

With hexagonal architecture:

$$
A \xrightarrow{p} P
$$

and an adapter realizes:

$$
E \xrightarrow{a} P
$$

The concrete implementation satisfies the port:

$$
a \models P
$$

So the application is parameterized by the port:

$$
A[P]
$$

rather than by the concrete technology:

$$
A[\text{Postgres}]
$$

That's the fundamental architectural move.

---

# 7. Applied to your runtime

For your agent system, I'd classify things roughly like this:

| Boundary          | Port                              | Adapters                      |
| ----------------- | --------------------------------- | ----------------------------- |
| Model inference   | `ModelClient`                     | OpenAI, Anthropic, vLLM       |
| Event persistence | `EventSink`                       | SQLite, Postgres, Supabase    |
| Memory            | `MemoryBackend`                   | SQLite, vector DB, in-memory  |
| Tools             | `Tool`                            | filesystem, HTTP, shell, etc. |
| User input        | `InputPort` / application command | TUI, CLI, HTTP                |
| Output            | `OutputPort`                      | terminal, WebSocket, UI       |

And your core aggregates:

```text
ApplicationRuntime
Conversation
AgentRuntime
Planner
```

should generally **not know which adapter is being used**.

They know only the ports.

---

## 8. The deepest formulation

A port is therefore best understood as a **boundary specification of admissible interaction**.

Formally, if an application requires some capability $C$, define a port:

$$
P_C = \text{the interface specifying how } C \text{ can be interacted with}
$$

Then an adapter is a realization:

$$
\operatorname{Adapter}(X) : X \to P_C
$$

where $X$ is some external technology or mechanism.

Thus:

$$
\boxed{
\text{Port} = \text{what interaction means}
}
$$

$$
\boxed{
\text{Adapter} = \text{how that interaction is realized}
}
$$

And **Hexagonal Architecture is essentially organizing your dependency graph so that application/domain behavior depends on ports, while technology-specific adapters depend on those ports.**

That is why the "hexagon" itself isn't really the important part. **The important structure is the factorization of dependencies through stable behavioral boundaries.**
