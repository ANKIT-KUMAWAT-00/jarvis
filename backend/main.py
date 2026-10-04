"""
JARVIS Main Application Server
FastAPI backend providing REST endpoints, WebSockets for live telemetry,
and static frontend serving.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import config, PROJECT_ROOT, FRONTEND_DIR, DATA_DIR, LOGS_DIR
from backend.security import PermissionEngine, ActionLevel, ConfirmationToken, Sanitizer
from backend.memory import MemoryStore, MemoryItem, MemoryRetriever, KnowledgeGraphBuilder
from backend.tools import (
    ToolRegistry, FilesystemTool, TerminalTool, ProcessTool,
    GitTool, ScreenVisionTool, BrowserTool, SystemInfoTool,
    AppControlTool, MeetingSchedulerTool, CommunicationTool
)
from backend.providers import LLMProvider, GeminiProvider, MockProvider
from backend.agent import JarvisAgent
from backend.tasks import TaskScheduler
from skills.base import SkillRegistry
from skills.coding.skill import CodingSkill
from skills.filesystem.skill import FilesystemSkill
from skills.browser.skill import BrowserSkill
from skills.vision.skill import VisionSkill
from skills.reminders.skill import RemindersSkill
from skills.custom.skill import CustomSkill


# Global singletons
permission_engine = PermissionEngine()
memory_store = MemoryStore(config.db_path)
graph_builder = KnowledgeGraphBuilder(config.notes_dir, memory_store)
task_scheduler = TaskScheduler(memory_store)

# Initialize Tools
tool_registry = ToolRegistry(permission_engine, memory_store)
tool_registry.register(FilesystemTool(config.workspace_root))
tool_registry.register(TerminalTool(config.workspace_root))
tool_registry.register(ProcessTool(LOGS_DIR))
tool_registry.register(GitTool(config.workspace_root))
tool_registry.register(ScreenVisionTool(DATA_DIR / "scratch"))
tool_registry.register(BrowserTool())
tool_registry.register(SystemInfoTool())
tool_registry.register(AppControlTool())
tool_registry.register(MeetingSchedulerTool(DATA_DIR, task_scheduler))
tool_registry.register(CommunicationTool())


# Initialize Skills
skill_registry = SkillRegistry()
skill_registry.register(CodingSkill(config.workspace_root))
skill_registry.register(FilesystemSkill(config.workspace_root))
skill_registry.register(BrowserSkill())
skill_registry.register(VisionSkill(DATA_DIR / "scratch"))
skill_registry.register(RemindersSkill(task_scheduler))
skill_registry.register(CustomSkill())

# Initialize LLM Provider: Prefer Gemini if configured, fallback gracefully to Mock
if config.all_gemini_keys:
    active_provider: LLMProvider = GeminiProvider(
        api_keys=config.all_gemini_keys,
        model_name=config.gemini_model
    )
else:
    active_provider = MockProvider(model_name="mock-jarvis-v1 (Free/Offline)")

def check_and_refresh_provider() -> LLMProvider:
    """Check if Gemini keys were added or modified in .env, and switch dynamically."""
    global active_provider
    config.reload()
    keys = config.all_gemini_keys
    
    if keys:
        if not isinstance(active_provider, GeminiProvider) or active_provider.api_keys != keys:
            active_provider = GeminiProvider(api_keys=keys, model_name=config.gemini_model)
            agent.set_provider(active_provider)
    elif not keys and not isinstance(active_provider, MockProvider):
        active_provider = MockProvider(model_name="mock-jarvis-v1 (Free/Offline)")
        agent.set_provider(active_provider)
        
    return active_provider

# Initialize Agent
agent = JarvisAgent(
    config=config,
    provider=active_provider,
    tool_registry=tool_registry,
    memory_store=memory_store
)


# Active WebSocket connections
active_connections: List[WebSocket] = []


async def broadcast_ws_event(event: Dict[str, Any]):
    """Broadcast an agent event to all connected UI clients."""
    if not active_connections:
        return
    message_str = json.dumps(event)
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_text(message_str)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in active_connections:
            active_connections.remove(ws)


# Hook agent events to WebSocket broadcaster
agent.register_event_subscriber(broadcast_ws_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await task_scheduler.start()
    yield
    # Shutdown
    await task_scheduler.stop()


app = FastAPI(
    title="JARVIS Personal Autonomous AI Agent",
    description="Local-first, security-gated, verified AI operating layer for macOS.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS: Allow local development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Models
class ChatRequest(BaseModel):
    prompt: str
    token_id: Optional[str] = None


class RememberRequest(BaseModel):
    fact: str
    category: str = "preference"


class ConfirmRequest(BaseModel):
    token_id: str
    confirmed: bool


class TaskCreateRequest(BaseModel):
    title: str
    description: str = ""
    delay_seconds: Optional[float] = None


class ConfigKeyRequest(BaseModel):
    api_key: str


# --- Endpoints ---

@app.get("/api/health")
async def health_check():
    """System health check and environmental status."""
    check_and_refresh_provider()
    sys_tool = tool_registry.get_tool("system_info")
    sys_res = await sys_tool.execute({}) if sys_tool else None
    
    return {
        "status": "online",
        "agent_name": config.jarvis_name,
        "environment": config.app_env,
        "active_model": active_provider.get_model_name(),
        "is_gemini_configured": active_provider.is_configured() and isinstance(active_provider, GeminiProvider),
        "key_pool_size": len(active_provider.api_keys) if isinstance(active_provider, GeminiProvider) else 0,
        "active_key_index": (active_provider.current_key_index + 1) if isinstance(active_provider, GeminiProvider) else 0,
        "total_memories": memory_store.count_memories(),
        "available_tools": [t["name"] for t in tool_registry.list_tools()],
        "available_skills": [s["name"] for s in skill_registry.list_skills()],
        "workspace_root": str(config.workspace_root),
        "system_info": sys_res.output if sys_res else {}
    }


@app.post("/api/config/key")
async def update_gemini_api_key(req: ConfigKeyRequest):
    """Update and persist GEMINI_API_KEY, validate it, and immediately hot-swap provider."""
    clean_key = req.api_key.strip()
    if not clean_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    
    test_provider = GeminiProvider(api_key=clean_key, model_name=config.gemini_model)
    valid, message = await test_provider.validate_connection()
    if not valid:
        raise HTTPException(status_code=400, detail=f"Gemini API verification failed: {message}")
    
    # Persist key to .env
    config.persist_api_key(clean_key)
    config.gemini_api_key = clean_key
    global active_provider
    active_provider = test_provider
    agent.set_provider(active_provider)

    await broadcast_ws_event({
        "type": "SYSTEM_READY",
        "name": config.jarvis_name,
        "model": active_provider.get_model_name(),
        "workspace": str(config.workspace_root)
    })
    return {"status": "success", "model": active_provider.get_model_name(), "message": message}


@app.post("/api/chat")
async def handle_chat(req: ChatRequest):
    """Primary conversational & task execution entrypoint."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    
    check_and_refresh_provider()
    result = await agent.run(user_input=req.prompt, confirmation_token_id=req.token_id)
    return result



@app.post("/api/remember")
async def handle_remember(req: RememberRequest):
    """Directly persist a memory item."""
    if not req.fact.strip():
        raise HTTPException(status_code=400, detail="Fact cannot be empty.")
    
    item = MemoryItem(
        category=req.category,
        content=req.fact.strip(),
        source="user",
        confidence="explicit"
    )
    mem_id = memory_store.add_memory(item)
    await broadcast_ws_event({"type": "MEMORY_UPDATED", "id": mem_id, "content": req.fact, "category": req.category})
    return {"status": "persisted", "id": mem_id, "content": req.fact}


@app.get("/api/memory")
async def get_memories(category: Optional[str] = None, limit: int = 50):
    """Retrieve memories, optionally filtered by category."""
    memories = memory_store.get_memories(category=category, limit=limit)
    return [m.model_dump() for m in memories]


@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    """Generate node-link graph data for 2D/3D visualization."""
    return graph_builder.build_graph()


@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None):
    """List scheduled and active tasks."""
    return [t.model_dump() for t in task_scheduler.list_tasks(status=status)]


@app.post("/api/tasks")
async def create_task(req: TaskCreateRequest):
    """Create a new persistent task or reminder."""
    task = task_scheduler.create_task(
        title=req.title,
        description=req.description,
        scheduled_delay_seconds=req.delay_seconds
    )
    return task.model_dump()


@app.post("/api/confirm")
async def confirm_action(req: ConfirmRequest):
    """Authorize or reject a pending Level 2/3 confirmation token."""
    if req.confirmed:
        success = permission_engine.confirm_token(req.token_id)
        if not success:
            raise HTTPException(status_code=400, detail="Token not found or expired.")
        token = permission_engine.get_pending_token(req.token_id)
        return {"status": "confirmed", "token_id": req.token_id}
    else:
        permission_engine.reject_token(req.token_id)
        return {"status": "rejected", "token_id": req.token_id}


@app.post("/api/screen")
async def capture_screen():
    """Trigger instantaneous macOS screen capture and vision telemetry."""
    return await agent.run("What am I looking at on my screen?")


@app.get("/api/activity")
async def get_recent_activity(limit: int = 30):
    """Fetch recent audit activity receipts."""
    return memory_store.get_recent_activity(limit=limit)


@app.get("/api/skills")
async def get_skills():
    """List registered modular skills."""
    return skill_registry.list_skills()


@app.post("/api/interrupt")
async def interrupt_execution():
    """Stop active agent loops immediately."""
    agent.interrupt()
    await broadcast_ws_event({"type": "IDLE", "message": "Interrupted by user command."})
    return {"status": "interrupted"}


# --- WebSocket Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send initial system status
        await websocket.send_text(json.dumps({
            "type": "SYSTEM_READY",
            "name": config.jarvis_name,
            "model": active_provider.get_model_name(),
            "workspace": str(config.workspace_root)
        }))

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action", "chat")
                if action == "chat":
                    prompt = payload.get("prompt", "")
                    token_id = payload.get("token_id")
                    if prompt:
                        asyncio.create_task(agent.run(prompt, confirmation_token_id=token_id))
                elif action == "interrupt":
                    agent.interrupt()
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)


# Mount Static Files for Frontend
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
