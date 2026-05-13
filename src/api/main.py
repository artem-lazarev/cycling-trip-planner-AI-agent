from fastapi import FastAPI
from pydantic import BaseModel
from agent import AIAgent
import asyncio
from fastapi.concurrency import run_in_threadpool

app = FastAPI()

sessions = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.session_id not in sessions:
        sessions[request.session_id] = AIAgent(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    agent = sessions[request.session_id]
    response = await run_in_threadpool(agent.chat, request.message)
    return ChatResponse(response=response)