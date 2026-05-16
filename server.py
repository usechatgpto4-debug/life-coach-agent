"""
FastAPI Server — Agent Chat MVP
Serves static frontend and provides /api endpoints to interact with the ADK agent.
"""

import os
import uuid
import json
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

import db

# --- Load environment ---
load_dotenv(os.path.join(os.path.dirname(__file__), "life_coach_agent", ".env"))

# --- ADK Agent Setup ---
from life_coach_agent.agent import root_agent

APP_NAME = "life_coach_app"
USER_ID = "default_user"

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB on startup."""
    db.init_db()
    yield

app = FastAPI(title="Life Coach Agent MVP", lifespan=lifespan)


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    msg_type: str

class SessionCreate(BaseModel):
    title: str = "New Chat"


# --- API Endpoints ---

@app.post("/api/sessions")
async def api_create_session(body: SessionCreate):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    session_data = db.create_session(session_id, body.title)
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    return session_data


@app.get("/api/sessions")
async def api_list_sessions():
    """List all chat sessions."""
    return db.list_sessions()


@app.delete("/api/sessions/{session_id}")
async def api_delete_session(session_id: str):
    """Delete a chat session."""
    db.delete_session(session_id)
    return {"status": "deleted"}


@app.get("/api/sessions/{session_id}/messages")
async def api_get_messages(session_id: str):
    """Get all messages for a session."""
    return db.get_messages(session_id)


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(body: ChatRequest):
    """Send a message and get an agent response."""
    session_id = body.session_id
    user_message = body.message

    db.add_message(session_id, "user", user_message, "text")

    existing = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    if not existing:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
        )

    agent_reply = ""
    user_content = Content(parts=[Part(text=user_message)])

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=user_content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                agent_reply = event.content.parts[0].text or ""

    msg_type = "text"
    stripped = agent_reply.strip()

    if stripped.startswith("{") or stripped.startswith("```"):
        clean = stripped
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            parsed = json.loads(clean)
            if isinstance(parsed, dict) and parsed.get("type") == "mcq":
                msg_type = "mcq"
                agent_reply = clean
        except json.JSONDecodeError:
            pass

    db.add_message(session_id, "agent", agent_reply, msg_type)

    messages = db.get_messages(session_id)
    user_msgs = [m for m in messages if m["role"] == "user"]
    if len(user_msgs) == 1:
        title = user_message[:40] + ("..." if len(user_message) > 40 else "")
        db.update_session_title(session_id, title)

    return ChatResponse(
        session_id=session_id,
        reply=agent_reply,
        msg_type=msg_type,
    )


# --- Serve Frontend ---
static_dir = os.path.join(os.path.dirname(__file__), "static")

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

app.mount("/static", StaticFiles(directory=static_dir), name="static")
