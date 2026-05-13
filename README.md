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

**Tool loop.** `AIAgent.chat` loops: send messages → mirror the assistant response into history → execute any `tool_use` blocks → append the `tool_result`s as a user-role message → repeat until the model returns text with no tool calls. Lets the model chain steps (route → elevation → weather → accommodation) instead of firing everything at once.

**Tool pattern.** One module per tool in `src/tools/`. Each exports `DEFINITION` (the Anthropic schema) and `execute(input) -> str`. The agent picks them up from `ALL_TOOLS` in `src/tools/__init__.py`. Adding a tool: write the module, append to the list. No decorators, no registry.

**Input validation.** Every tool validates its input with a Pydantic model before running. Bad input returns a readable error string to the model rather than throwing — the model can read the error and retry with the right shape.

**Mock data.** Hardcoded routes, elevations, weather, and accommodation for four European corridors (Amsterdam↔Copenhagen, Amsterdam↔Berlin, Paris↔Amsterdam, London↔Paris). Unknown routes and unverified towns return an explicit "no data" message so the model doesn't fabricate cities. Architecture is what's being tested, not API plumbing.

**Session storage.** In-process `dict[session_id, AIAgent]`. Each `AIAgent` instance owns its own message history (including `tool_use` and `tool_result` blocks), so mid-conversation preference changes ("actually make it 80km/day") update only the affected parts instead of re-planning from scratch. Server generates a `session_id` if the client doesn't send one. Redis or a DB would replace this in prod.

**Scratchpad.** The system prompt tells the model to reason inside `<scratch>...</scratch>` tags. The agent strips those (including unclosed tags from `max_tokens` truncation) before returning. Gives the model room to plan tool order and reconcile day-vs-segment counts without leaking it to the user.

**System prompt.** Short and prescriptive (`src/agent/prompts.py`): when to ask vs. just plan, which tools to batch in parallel, how to reconcile day count vs. segment count, how to react to preference changes, what to say when a tool returns no data.

## What I'd build with more time

- **Real APIs**: Apple WeatherKit for weather, GraphHopper for routing, PJAMM for climb data, Google Maps for places. 
- **The three bonus tools**: `get_points_of_interest`, `check_visa_requirements`, `estimate_budget` — each fits the same `DEFINITION`/`execute` pattern.
- **System Prompt**: Keep evolving the system prompt.
- **Persistent session storage**: SQLite instead of the in-process dict, so sessions survive restarts and scale beyond one process.
- **Streaming responses**: stream the model's output so the user sees the plan being built instead of waiting for the full turn.
- **Structured itinerary output**: alongside the prose reply, return a typed Pydantic `Itinerary` object (days, distances, accommodation, weather) so a frontend can render the plan as a real UI rather than parsing text.
- **Frontend**: Deploy the app with a frontend (Vercel + Render.com)
- **Eval harness**: a small set of scripted conversations to regression-test tool selection and multi-step reasoning when prompts or models change.
