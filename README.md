# Cycling Trip Planner Agent

A conversational AI agent that helps cyclists plan multi-day bike trips. Built with FastAPI and the Anthropic Claude API.

## Setup

```bash
git clone https://github.com/artem-lazarev/cycling-trip-planner-AI-agent.git
cd cycling-trip-planner-AI-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your `ANTHROPIC_API_KEY` to `.env`.

## Run

```bash
PYTHONPATH=src:src/agent python -m uvicorn api.main:app --reload
```

> Use `python -m uvicorn` (not bare `uvicorn`). If you have Homebrew's `uvicorn` installed, the bare command resolves to that binary, which runs its own bundled Python and won't see the packages installed in your venv — you'll get `ModuleNotFoundError: No module named 'fastapi'`. Running it via `python -m` forces the venv's interpreter.

Then send a request to `http://localhost:8000/chat`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to cycle from Amsterdam to Copenhagen, 100km/day, camping mostly with a hostel every 4th night, in June"}'
```

The response includes a `session_id`. Pass it back on the next request to continue the same trip-planning conversation:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<id from previous response>", "message": "Actually make it 80km/day"}'
```

## Tests

```bash
PYTHONPATH=src python -m pytest tests/
```

## Architecture decisions

- **Deliberately minimal codebase** — An AI agent is just an LLM running in a loop with access to tools, stopping when it decides it's done. That's it. I kept the implementation as small and the code as verbose as I could so that this idea is conveyed.
- **No frameworks, no orchestrators, no graphs** — just the loop
- **Verbose by design** — every step explicit, nothing hidden in abstractions

---

**Tool-calling loop.** `AIAgent.chat` (in `src/agent/agent.py`) is where the whole thing lives. It sends messages to Claude, mirrors the response into the conversation history, runs any requested tool calls, feeds results back, and repeats — until Claude returns a plain text reply with no more tool calls. That's the complete agent.

**Batching within a turn.** A single Claude response can carry many `tool_use` blocks. The system prompt tells the model to batch independent calls — elevation for every segment, accommodation for every stop — into one turn, and to start a new turn only when later tools depend on earlier results (e.g. `find_accommodation` needs waypoints from `get_route`). LLM round-trips dominate latency, so fewer turns matter; tool execution itself doesn't.

**Sequential tool execution.** The runner executes a turn's `tool_use` blocks one at a time in a `for` loop (`agent.py:87-95`). Fine here — every tool is a dict lookup. If any tool became real I/O, this is where `asyncio.gather` would go.

**Tool pattern.** Each tool is its own module under `src/tools/` and exports two things:
- `DEFINITION` — the Anthropic tool-use schema (name, description, input_schema)
- `execute(tool_input) -> str` — runs the tool and returns a plain string

The agent discovers tools through `ALL_TOOLS` in `src/tools/__init__.py`. Adding a new tool is two steps: drop a file in `src/tools/`, append it to `ALL_TOOLS`. No registration glue, no decorators. Inputs are validated with a Pydantic model at the top of `execute`; bad input returns a readable error string to the model rather than throwing.

**Session storage.** Sessions are a plain `dict` mapping `session_id` to an `AIAgent` instance. The message history lives directly on the instance as `self.messages` — there's no separate state store. The server auto-generates a `session_id` if the client doesn't supply one. Fine for a case study — a real deployment would swap this for SQLite or Redis.

**Conversation state.** Because history is stored on the instance itself, the agent always has full context and can adapt mid-conversation when the user changes preferences ("actually make it 80km/day").

**System prompt.** Lives in `src/agent/prompts.py`. Short and prescriptive: ask before assuming, call tools step by step, present a day-by-day itinerary, adapt when preferences change. It also tells the model to reason inside `<scratch>...</scratch>` tags, which the agent strips before returning the reply.

**Mock data.** Tools return hardcoded mock data for a handful of well-known European cycling corridors, with sensible fallbacks for anything else. The architecture is what's being tested here, not API integration.

## What I'd build with more time

- **Real APIs**: Apple WeatherKit for weather, GraphHopper for routing, PJAMM for climb data, Google Maps for places. 
- **System Prompt**: Keep evolving the system prompt.
- **More tools**: `get_points_of_interest`, `check_visa_requirements`, `estimate_budget` — each fits the same `DEFINITION`/`execute` pattern.
- **Persistent session storage**: SQLite instead of the in-process dict, so sessions survive restarts and scale beyond one process.
- **Streaming responses**: stream the model's output so the user sees the plan being built instead of waiting for the full turn.
- **Structured itinerary output**: alongside the prose reply, return a typed Pydantic `Itinerary` object (days, distances, accommodation, weather) so a frontend can render the plan as a real UI rather than parsing text.
- **Frontend**: Deploy the app with a frontend (Vercel + Render.com)
- **Eval harness**: a small set of scripted conversations to regression-test tool selection and multi-step reasoning when prompts or models change.
