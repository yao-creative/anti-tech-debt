# anti-tech-debt-app


Observations:

Finding good signals of what good code/ maths is very hard. Everyone has intrinsic epistemic bias and agreement over what is right and the why to best practice are always weakly defined. By cleaning for strong signals, I can boost my learning rate and this learning rate is the second order derivative on the diffeq of output productivity. More quality learn = less busy work + more pay = more happiness :D.

For me strong proxy signals are: Turing / Fields medal papers, Popular Research fields, github repos of frameworks which have existed for 10+ years and still inuse in the frontier serving millions of people. Textbooks which have been repeatedly edited with 5- 20 editions over the past 20 years.  Or work/ interview questions from labs/ companies which repetitively drive results or that my smartest friends want to work in. And second order book recommendations/ repository recommendations from people who work there, from their blogs. 

But then I'm responsible for piecing them together and figuring out what's true.

## Structure

Local-first Python scaffold for a Codex/Omnigent-style agent runtime with a REPL/TUI, typed queues, SQLite thread persistence, and a mock-first happy path.

## Commands

```bash
uv sync
uv run anti-tech-debt-app
uv run pytest
```

## Design:

1. Single User owned Thread/ session.

2. Agent is a state machine interacting with queues.

