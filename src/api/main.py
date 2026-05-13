import os
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from dotenv import load_dotenv

from agent import AIAgent

load_dotenv()

app = FastAPI(title="Cycling Trip Planner")

# In-memory session store: session_id -> AIAgent. Fine for a case study;
# a real deployment would use Redis or a DB.
sessions: dict[str, AIAgent] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    session_id = request.session_id or uuid.uuid4().hex
    if session_id not in sessions:
        sessions[session_id] = AIAgent(api_key=api_key)

    agent = sessions[session_id]
    response = await run_in_threadpool(agent.chat, request.message)
    return ChatResponse(response=response, session_id=session_id)
