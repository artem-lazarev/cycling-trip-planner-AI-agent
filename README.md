# Cycling Trip Planner Agent

A conversational AI agent that helps cyclists plan multi-day bike trips. Built with FastAPI and the Anthropic Claude API.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your `ANTHROPIC_API_KEY` to `.env`.

## Run

```bash
PYTHONPATH=src:src/agent uvicorn api.main:app --reload
```

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
PYTHONPATH=src pytest tests/
```

## Architecture decisions

**Tool-calling loop.** `AIAgent.chat` (in `src/agent/agent.py`) runs a single loop: send messages to Claude, mirror the response into the conversation history, run any requested tool calls, feed results back, and repeat until Claude produces a final text reply. This is the minimal shape that lets the model plan across multiple steps (route → elevation → weather → accommodation → itinerary) rather than firing every tool at once.

**Tool pattern.** Each tool is its own module under `src/tools/` exporting two things:
- `DEFINITION` — the Anthropic tool-use schema (name, description, input_schema)
- `execute(tool_input) -> str` — runs the tool and returns a plain string

The agent discovers tools through `ALL_TOOLS` in `src/tools/__init__.py`. Adding a new tool is two steps: drop a file in `src/tools/` and append it to `ALL_TOOLS`. No registration glue, no decorators.

**Mock data.** Per the spec, tools return hardcoded mock data for a handful of well-known European cycling corridors with sensible fallbacks for anything else. The architecture is what's being tested, not API integration.

**Session storage.** Sessions live in a plain in-process `dict` keyed by `session_id`. The server auto-generates one if the client doesn't supply it. Fine for a case study — a real deployment would swap this for Redis or a database.

**Conversation state.** The full message history (including tool_use and tool_result blocks) is kept per-session, so the agent has the context it needs to adapt when the user changes preferences ("actually make it 80km/day") instead of re-planning from scratch.

**System prompt.** Lives in `src/agent/prompts.py` and steers the agent's behavior: ask before assuming, call tools step by step, present a day-by-day itinerary, adapt when preferences change. Kept short and prescriptive.

## What I'd build with more time

- **Real APIs**: Apple WeatherKit for weather, GraphHopper for routing, PJAMM for climb data, Google Maps for places. 
- **The three bonus tools**: `get_points_of_interest`, `check_visa_requirements`, `estimate_budget` — each fits the same `DEFINITION`/`execute` pattern.
- **System Prompt**: Keep evolving the system prompt.
- **Persistent session storage**: SQLite instead of the in-process dict, so sessions survive restarts and scale beyond one process.
- **Streaming responses**: stream the model's output so the user sees the plan being built instead of waiting for the full turn.
- **Structured itinerary output**: alongside the prose reply, return a typed Pydantic `Itinerary` object (days, distances, accommodation, weather) so a frontend can render the plan as a real UI rather than parsing text.
- **Frontend**: Deploy the app with a frontend (Vercel + Render.com)
- **Eval harness**: a small set of scripted conversations to regression-test tool selection and multi-step reasoning when prompts or models change.
