**Intent: dependency-injection semantics and architectural composition.**

The cleanest answer is: **use both, but at different levels**.

## 1. FastAPI DI

Suppose you have:

```python
from typing import Protocol
from fastapi import Depends, FastAPI


class EventSink(Protocol):
    async def append(self, event: Event) -> None: ...


class EventService:
    def __init__(self, sink: EventSink):
        self.sink = sink

    async def record(self, event: Event):
        await self.sink.append(event)
```

You can make FastAPI construct it:

```python
def get_event_sink() -> EventSink:
    return PostgresEventSink(...)


def get_event_service(
    sink: EventSink = Depends(get_event_sink),
) -> EventService:
    return EventService(sink)


@app.post("/events")
async def append_event(
    event: Event,
    service: EventService = Depends(get_event_service),
):
    await service.record(event)
```

The dependency relation is:

$$
Endpoint
\rightarrow
EventService
\rightarrow
EventSink
\rightarrow
PostgresEventSink
$$

FastAPI recursively resolves this graph **per request**.

This is perfectly legitimate DI.

---

# 2. Composition-root DI

Instead, construct the graph once:

```python
def build_application(config: Config) -> Application:
    sink = PostgresEventSink(
        dsn=config.database.dsn,
    )

    service = EventService(
        sink=sink,
    )

    return Application(
        events=service,
    )
```

Then at startup:

```python
application = build_application(config)
```

and your endpoint just receives that object:

```python
def get_application(request: Request) -> Application:
    return request.app.state.application


@app.post("/events")
async def append_event(
    event: Event,
    application: Application = Depends(get_application),
):
    await application.events.record(event)
```

Now the dependency graph is:

$$
Config
\rightarrow
CompositionRoot
\rightarrow
\begin{cases}
PostgresEventSink\\
EventService\\
Application
\end{cases}
$$

and request handling is merely:

$$
HTTPRequest
\rightarrow
Application
$$

This is what I'd call **application-level dependency injection**.

---

# 3. So when do you use them together?

This is where the distinction becomes really useful.

Use **composition-root DI for long-lived application dependencies**:

$$
\boxed{
\text{Application lifetime}
}
$$

Examples:

* database pools
* HTTP clients
* model clients
* event sinks
* repositories
* caches
* application services
* circuit breakers
* rate limiters
* telemetry clients

Use **FastAPI DI for request/context dependencies**:

$$
\boxed{
\text{Request lifetime}
}
$$

Examples:

* authenticated user
* request ID
* current request
* transaction/session scoped to request
* parsed request context
* authorization context

So you can have:

$$
\text{FastAPI DI}
\rightarrow
\boxed{\text{already-composed Application}}
$$

and then:

$$
\text{Application}
\rightarrow
\boxed{\text{ports}}
$$

---

# 4. A concrete example

Imagine your application has:

```python
class ModelClient(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse:
        ...
```

and:

```python
class AgentService:
    def __init__(self, model: ModelClient):
        self.model = model
```

Your adapters:

```python
class OpenAIModelClient:
    ...
```

Your resilience wrappers:

```python
class RateLimitedModelClient:
    ...

class CircuitBrokenModelClient:
    ...

class RetryingModelClient:
    ...
```

Then the **composition root** owns the assembly:

```python
def build_model_client(config: Config) -> ModelClient:
    client = OpenAIModelClient(
        api_key=config.openai.api_key,
    )

    client = RetryingModelClient(
        inner=client,
        policy=config.openai.retry,
    )

    client = CircuitBrokenModelClient(
        inner=client,
        policy=config.openai.circuit_breaker,
    )

    client = RateLimitedModelClient(
        inner=client,
        policy=config.openai.rate_limit,
    )

    return client
```

Then:

```python
def build_application(config: Config) -> Application:
    model = build_model_client(config)

    agent = AgentService(
        model=model,
    )

    return Application(
        agent=agent,
    )
```

And startup:

```python
@app.on_event("startup")
async def startup():
    config = load_config()
    app.state.application = build_application(config)
```

Finally FastAPI:

```python
def get_application(request: Request) -> Application:
    return request.app.state.application


@app.post("/chat")
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    application: Application = Depends(get_application),
):
    return await application.chat(
        user=user.id,
        message=request.message,
    )
```

Now notice the division of responsibility:

| Concern                       | Owner                |
| ----------------------------- | -------------------- |
| What is `ModelClient`?        | Application          |
| How does OpenAI implement it? | Adapter              |
| Retry policy?                 | Resilience component |
| Circuit-breaker policy?       | Resilience component |
| Rate-limit policy?            | Resilience component |
| Which provider/config?        | Composition root     |
| Construct `Application`?      | Composition root     |
| Current user?                 | FastAPI DI           |
| Current request?              | FastAPI DI           |
| Invoke application?           | HTTP adapter         |

That's a very clean architecture.

---

# 5. Formalize it as lifetimes

This is probably the most useful way to reason about it.

Let:

$$
D = \{d_1,d_2,\ldots,d_n\}
$$

be your dependency graph.

Each dependency has a **lifetime**:

$$
\lambda : D \rightarrow
\{
Process,
Application,
Request,
Operation
\}
$$

For example:

$$
\lambda(\text{PostgresPool}) = Application
$$

$$
\lambda(\text{ModelClient}) = Application
$$

$$
\lambda(\text{CircuitBreaker}) = Application
$$

$$
\lambda(\text{CurrentUser}) = Request
$$

$$
\lambda(\text{Request}) = Request
$$

The composition root should construct dependencies whose lifetime is at or above the application boundary.

FastAPI DI is particularly useful for dependencies whose lifetime is determined by the request graph.

---

# 6. There's another important category: operation-scoped dependencies

Suppose your application does:

```python
async def process_message(...):
    async with db.transaction() as tx:
        ...
```

You might deliberately create:

$$
Transaction : Operation
$$

rather than putting one transaction in the composition root.

Then:

$$
Application
\rightarrow
TransactionFactory
\rightarrow
Transaction
$$

The application can have a port such as:

```python
class TransactionManager(Protocol):
    def transaction(self) -> AsyncContextManager[Transaction]:
        ...
```

and the concrete implementation is constructed at the composition root.

This is another nice example of why **"DI = FastAPI Depends" is too narrow**.

---

# 7. The category-theoretic view

You can think of your application as parameterized over a collection of ports.

Let:

$$
P =
P_{Model}
\times
P_{EventSink}
\times
P_{Memory}
\times
P_{Tool}
$$

Then:

$$
Application : P \rightarrow Behavior
$$

The composition root selects an implementation:

$$
c : Config \rightarrow I
$$

where $I$ is a tuple of concrete implementations.

Then it maps those implementations into the required port structure:

$$
I \rightarrow P
$$

giving:

$$
Config
\rightarrow
I
\rightarrow
P
\rightarrow
Application
$$

FastAPI's DI then doesn't need to solve this architectural problem. It can simply provide:

$$
Request \rightarrow Application
$$

and request-scoped values:

$$
Request \rightarrow User
$$

So you have two different resolution functions:

$$
\boxed{
R_{startup}: Config \rightarrow Application
}
$$

and:

$$
\boxed{
R_{request}: Request \rightarrow Context
}
$$

That is the clean separation I would aim for.

---

## Practical rule

If you ask:

> **"Who decides what implementation my application uses?"**

Answer:

**Composition root.**

If you ask:

> **"Who gives this HTTP handler the current user/request/transaction context?"**

Answer:

**FastAPI DI.**

If you ask:

> **"What does the application depend upon?"**

Answer:

**Ports.**

If you ask:

> **"What talks to OpenAI/Postgres/Redis?"**

Answer:

**Adapters.**

And therefore your ideal dependency chain is:

$$
\boxed{
Config
\rightarrow
CompositionRoot
\rightarrow
Adapters + Policies
\rightarrow
Ports
\rightarrow
Application
}
$$

with the framework sitting at the edge:

$$
HTTP
\rightarrow
FastAPI
\rightarrow
Application
$$

rather than FastAPI becoming the thing that *defines and owns your entire application dependency graph*.
