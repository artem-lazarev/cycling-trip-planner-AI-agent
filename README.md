# Cycling Trip Planner Agent

A conversational AI agent that helps cyclists plan multi-day bike trips. Built with FastAPI and Anthropic Claude API.

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
uvicorn src.api.main:app --reload
```

Then send a request to `http://localhost:8000/chat`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to cycle from Amsterdam to Copenhagen, 100km/day, camping mostly, in June"}'
```

The response includes a `session_id`. Reuse it in later requests to continue the same trip-planning conversation.