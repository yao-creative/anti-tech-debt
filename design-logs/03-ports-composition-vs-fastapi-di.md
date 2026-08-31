Yes. I would make a distinction between **architectural DI** and **framework DI**.

### Best-practice model

Think of the system as having three separate concerns:

$$
\boxed{\text{Port}}
\neq
\boxed{\text{Adapter}}
\neq
\boxed{\text{Dependency Injection}}
$$

* **Port** = the contract the application speaks.
* **Adapter** = a concrete implementation/translation to an external mechanism.
* **DI/composition** = the process that chooses and connects concrete implementations to ports.

For your FastAPI application, I would use this structure:

```text
app/
├── domain/
├── application/
│   ├── ports/
│   │   ├── model_client.py
│   │   ├── event_sink.py
│   │   └── memory.py
│   └── services/
│
├── adapters/
│   ├── openai.py
│   ├── postgres.py
│   └── ...
│
├── bootstrap/
│   ├── config.py
│   └── composition.py
│
└── api/
    ├── routes.py
    └── dependencies.py
```

Then the dependency graph is:

$$
\text{API}
\rightarrow
\text{Application}
\rightarrow
\text{Ports}
\leftarrow
\text{Adapters}
$$

while:

$$
\text{Bootstrap}
\rightarrow
\text{constructs and connects everything}
$$

---

## 1. The port should be defined where the application needs it

For example:

```python
# application/ports/model_client.py

from typing import Protocol

class ModelClient(Protocol):
    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        ...
```

Your application depends on this:

```python
class AgentService:
    def __init__(self, model: ModelClient):
        self._model = model
```

Notice there is no FastAPI here.

No:

```python
Depends(...)
```

No:

```python
OpenAI(...)
```

No environment-variable lookup.

The application is just parameterized over the port.

Set-theoretically, if

$$
P = \text{ModelClient}
$$

then:

$$
AgentService : P \rightarrow Behavior
$$

It doesn't care which particular inhabitant of $P$ it receives.

---

# 2. The adapter implements the port

```python
# adapters/openai.py

class OpenAIModelClient:
    def __init__(self, api_key: str):
        self._client = ...

    async def generate(self, request):
        ...
```

Structurally:

$$
OpenAIModelClient \in ModelClient
$$

in the sense that it satisfies the protocol.

The adapter knows about:

* OpenAI's SDK
* HTTP
* authentication
* external request/response schemas
* provider-specific errors

The application doesn't.

---

# 3. The composition root connects them

This is the important piece:

```python
# bootstrap/composition.py

def build_application(config: Config) -> Application:
    model: ModelClient = OpenAIModelClient(
        api_key=config.openai.api_key,
    )

    return Application(
        model=model,
    )
```

This is **dependency injection**.

More precisely, it is **constructor injection performed by the composition root**.

You are manually constructing:

$$
OpenAIModelClient
\hookrightarrow
ModelClient
\rightarrow
Application
$$

There is no need for a DI framework to accomplish this.

---

# 4. Then FastAPI gets the already-composed application

Your FastAPI integration can be extremely thin:

```python
app = FastAPI()

@app.on_event("startup")
async def startup():
    config = load_config()
    app.state.application = build_application(config)
```

Then:

```python
def get_application(request: Request) -> Application:
    return request.app.state.application
```

and:

```python
@app.post("/messages")
async def send_message(
    message: Message,
    application: Application = Depends(get_application),
):
    return await application.send_message(message)
```

Now `Depends()` isn't really performing your architectural composition.

It is just doing:

$$
Request
\rightarrow
Application
$$

The important construction already happened:

$$
Config
\rightarrow
CompositionRoot
\rightarrow
Application[ModelClient=OpenAIAdapter]
$$

This is the pattern I would recommend for your architecture.

---

# 5. Why not just do this?

You *can*:

```python
def get_model_client() -> ModelClient:
    return OpenAIModelClient(...)
```

and:

```python
def get_application(
    model: ModelClient = Depends(get_model_client),
):
    return Application(model)
```

It's not inherently wrong.

The problem appears when the entire application graph becomes encoded as:

$$
Depends(Depends(Depends(...)))
$$

Then your architectural composition becomes coupled to FastAPI.

For example, suddenly your application construction is conceptually:

$$
Application
=
f(
Depends(Model),
Depends(Database),
Depends(Memory),
Depends(ToolRegistry),
...
)
$$

That makes the framework responsible for something I'd rather have your **bootstrap layer** own.

It also becomes awkward to instantiate the application outside HTTP:

```python
# CLI
# worker
# tests
# background job
# migration
```

You want all of those to be able to say:

```python
application = build_application(config)
```

without needing a running FastAPI application.

---

# 6. This gives you a useful three-layer distinction

### Application dependency

```python
class AgentService:
    def __init__(self, model: ModelClient):
        ...
```

**Meaning:**

> I require a `ModelClient`.

---

### Composition dependency

```python
def build_application(config):
    model = OpenAIModelClient(...)
    return Application(model)
```

**Meaning:**

> In this deployment, satisfy `ModelClient` with `OpenAIModelClient`.

---

### Framework dependency

```python
def get_application(request: Request):
    return request.app.state.application
```

**Meaning:**

> FastAPI, give this request access to the application I already constructed.

Those are three different responsibilities.

---

# 7. This also makes testing extremely clean

Production:

```python
application = build_application(prod_config)
```

Test:

```python
application = Application(
    model=FakeModelClient(),
    event_sink=InMemoryEventSink(),
)
```

No FastAPI.

No DI container.

No environment variables.

No monkeypatching.

This is one of the strongest reasons to prefer explicit composition.

---

# 8. Where does FastAPI's DI shine then?

I'd still use it for **request-level concerns**.

For example:

```python
async def get_current_user(...):
    ...

async def get_request_id(...):
    ...

async def get_application(...):
    ...
```

These are things whose lifetime/context is naturally associated with the HTTP request.

So I'd draw the boundary:

$$
\boxed{
\text{Composition Root}
=
\text{process/application dependencies}
}
$$

$$
\boxed{
\text{FastAPI DI}
=
\text{request/framework dependencies}
}
$$

That distinction is much more useful than "DI good/bad."

---

# 9. One refinement: don't make `Application` itself a giant dependency bag

You don't want:

```python
Application(
    model,
    db,
    redis,
    event_sink,
    memory,
    telemetry,
    limiter,
    breaker,
    ...
)
```

to become an indiscriminate service locator.

Instead, compose meaningful application components.

For example:

```python
agent = AgentService(
    model=model,
    memory=memory,
    tools=tools,
)

application = Application(
    agent=agent,
    events=events,
)
```

Then:

$$
Application
\rightarrow
AgentService
\rightarrow
\{
ModelClient,
MemoryBackend,
Tool
\}
$$

This preserves the dependency structure rather than hiding everything in one container.

---

## 10. And your resilience layers fit naturally into this

Suppose:

```python
raw_model = OpenAIModelClient(...)

model = RetryModelClient(raw_model, retry_policy)

model = CircuitBreakerModelClient(model, breaker)

model = RateLimitedModelClient(model, limiter)
```

All four can satisfy:

$$
ModelClient
$$

Then:

```python
agent = AgentService(model=model)
```

The composition root decides:

$$
\text{which adapter}
+
\text{which decorators}
+
\text{which policies}
$$

but the application sees only:

$$
\boxed{ModelClient}
$$

That's an especially nice use of ports because the resilience mechanisms themselves can be **port-preserving transformations**:

$$
R : Port \rightarrow Port
$$

$$
C : Port \rightarrow Port
$$

$$
L : Port \rightarrow Port
$$

So composition can construct:

$$
L(C(R(OpenAIAdapter)))
$$

and the entire expression still has type:

$$
ModelClient
$$

---

# My recommendation for your project

I would **not** introduce a general-purpose DI container yet.

Use:

```text
application/
    ports/

adapters/

bootstrap/
    composition.py

api/
    dependencies.py
```

with:

$$
\boxed{
\text{Ports define architectural contracts}
}
$$

$$
\boxed{
\text{Adapters implement external mechanisms}
}
$$

$$
\boxed{
\text{Composition root performs constructor injection}
}
$$

$$
\boxed{
\text{FastAPI Depends handles request/framework concerns}
}
$$

This gives you explicit dependency graphs, easy non-HTTP execution, straightforward tests, and a very clear hexagonal boundary without making FastAPI's DI system the thing that *defines* your architecture.
