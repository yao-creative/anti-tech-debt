Exactly. **Intent: dependency composition / runtime wiring.**

The **composition root** is precisely where the abstract port gets bound to a concrete adapter.

Conceptually:

$$
\text{Config}
\rightarrow
\text{Composition Root}
\rightarrow
\text{Concrete Adapter}
\rightarrow
\text{Port}
\rightarrow
\text{Application}
$$

For example:

```rust
trait EventSink {
    fn append(&self, event: Event) -> Result<(), Error>;
}

struct PostgresEventSink {
    // ...
}

impl EventSink for PostgresEventSink {
    // ...
}
```

Then your composition root might do:

```rust
fn build_runtime(config: Config) -> ApplicationRuntime {
    let event_sink: Box<dyn EventSink> =
        match config.event_store {
            EventStore::Postgres => {
                Box::new(PostgresEventSink::new(config.postgres))
            }

            EventStore::InMemory => {
                Box::new(InMemoryEventSink::new())
            }
        };

    ApplicationRuntime::new(event_sink)
}
```

The important thing is that **the match belongs outside the application**.

Your runtime sees only:

```rust
struct ApplicationRuntime {
    event_sink: Box<dyn EventSink>,
}
```

It does **not** do:

```rust
match config.event_store {
    EventStore::Postgres => ...
}
```

because then your application becomes aware of infrastructure selection.

---

### There are two distinct concepts here

**1. Port**

The type-level contract:

```rust
trait EventSink {
    fn append(&self, event: Event) -> Result<(), Error>;
}
```

**2. Composition**

The runtime value-level choice:

```rust
let sink: Box<dyn EventSink> =
    Box::new(PostgresEventSink::new(...));
```

So mathematically, if:

$$
P = \texttt{EventSink}
$$

and

$$
I = \{\texttt{PostgresEventSink},\texttt{SqliteEventSink},\texttt{MemoryEventSink}\}
$$

then composition chooses an element:

$$
c : Config \rightarrow I
$$

and injects that implementation into the application:

$$
I \hookrightarrow P
$$

giving:

$$
Config
\xrightarrow{c}
I
\hookrightarrow
P
\rightarrow
ApplicationRuntime
$$

The **port is static structure**; the **adapter selection is runtime configuration**.

---

### And you don't necessarily need a DI container

This is an important distinction.

You can have explicit composition:

```rust
fn build(config: Config) -> ApplicationRuntime {
    let sink = build_event_sink(&config);

    ApplicationRuntime::new(sink)
}
```

where:

```rust
fn build_event_sink(config: &Config) -> Box<dyn EventSink> {
    match config.event_store {
        EventStore::Postgres => {
            Box::new(PostgresEventSink::new(&config.postgres))
        }
        EventStore::Sqlite => {
            Box::new(SqliteEventSink::new(&config.sqlite))
        }
    }
}
```

Or a DI/container abstraction can perform that resolution:

```rust
let sink = container.resolve::<dyn EventSink>()?;
```

But **DI is an implementation technique; composition root is the architectural concept**.

For the architecture you've been developing, I'd actually prefer the explicit version initially:

$$
\boxed{
\text{Config} \rightarrow \text{Builder/Composition Root} \rightarrow \text{Runtime}
}
$$

with the runtime receiving already-constructed ports.

That gives you a very clean invariant:

> **After bootstrap, the application runtime should not need to know how its ports were resolved.**

So `ApplicationRuntime` is effectively parameterized by its environment:

$$
ApplicationRuntime[P_1,P_2,\ldots,P_n]
$$

and bootstrap instantiates that parameterization:

$$
ApplicationRuntime[
EventSink = Postgres,
ModelClient = Anthropic,
MemoryBackend = SQLite
]
$$

while the application code itself continues to operate only against:

$$
EventSink,\ ModelClient,\ MemoryBackend.
$$

That's the precise relationship between **hexagonal ports, adapters, configuration, and the composition root**.
