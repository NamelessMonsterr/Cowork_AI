"""
Cowork AI Assistant - FastAPI Backend (PRODUCTION WIRED).

Provides REST API and WebSocket for the Electron frontend.
Now connected to REAL Computer and LLM components.
"""

import asyncio
import time
import logging
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Real Components
from assistant.agent.planner import Planner
from assistant.voice.stt import STT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== Models ====================

class ActionRequest(BaseModel):
    action: str
    target: Optional[str] = None
    value: Optional[str] = None


class PlanStep(BaseModel):
    id: str
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    status: str = "pending"


class PlanRequest(BaseModel):
    task: str
    steps: Optional[List[PlanStep]] = None


# ==================== State ====================

class AppState:
    def __init__(self):
        self.session_active = False
        self.current_task: Optional[str] = None
        self.current_plan: List[Dict] = []
        self.takeover_active = False
        self.voice_enabled = True
        self.websocket_clients: List[WebSocket] = []
        
        # The AI Brain & Ears
        self.planner = None 
        self.stt = None
    
    async def broadcast(self, event: str, data: dict):
        for ws in self.websocket_clients[:]:
            try:
                await ws.send_json({"event": event, "data": data, "timestamp": time.time()})
            except:
                if ws in self.websocket_clients:
                    self.websocket_clients.remove(ws)


state = AppState()


# ==================== App ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Cowork Assistant initializing real components...")
    
    # Initialize the Planner (Computer + LLM)
    try:
        state.planner = Planner()
        state.stt = STT()
        logger.info("Planner & STT initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
    
    yield
    logger.info("Cowork Assistant stopping...")


app = FastAPI(
    title="Flash AI Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Routes ====================

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "production"}


@app.post("/voice/listen")
async def voice_listen():
    """
    Record audio, transcribe, and start planning.
    This is the main entry point for Voice Mode.
    """
    if not state.stt:
        raise HTTPException(503, "STT not initialized")
    
    # Notify UI we are listening
    await state.broadcast("voice_listening", {})
    
    # Run in thread to avoid blocking loop during recording
    text = await asyncio.to_thread(state.stt.listen_and_transcribe, duration=5)
    
    if not text:
        await state.broadcast("voice_error", {"message": "No speech detected"})
        return {"success": False, "message": "No speech detected"}

    await state.broadcast("voice_transcribed", {"text": text})
    
    # Automatically start planning with the transcribed text
    try:
        request = PlanRequest(task=text)
        await plan_preview(request)
        
        # AUTO-EXECUTE: Approve and run the plan immediately
        if state.current_plan:
            await plan_approve()
    except HTTPException as e:
        logger.error(f"Voice flow planning failed: {e.detail}")
        await state.broadcast("voice_error", {"message": f"Planning failed: {e.detail}"})
        return {"success": False, "message": f"Planning failed: {e.detail}"}
    except Exception as e:
        logger.error(f"Voice flow error: {e}")
        await state.broadcast("voice_error", {"message": str(e)})
        return {"success": False, "message": str(e)}
    
    return {"success": True, "text": text}


@app.get("/voice/status")
async def voice_status():
    return {"enabled": state.voice_enabled}


@app.get("/status")
async def status():
    return {
        "session_active": state.session_active,
        "current_task": state.current_task,
        "takeover_active": state.takeover_active,
        "has_brain": state.planner is not None,
        "connected_clients": len(state.websocket_clients),
    }


@app.post("/session/start")
async def session_start():
    state.session_active = True
    await state.broadcast("session_started", {})
    return {"success": True}


@app.post("/session/stop")
async def session_stop():
    state.session_active = False
    state.current_task = None
    state.current_plan = []
    await state.broadcast("session_stopped", {})
    return {"success": True}


@app.post("/plan/preview")
async def plan_preview(request: PlanRequest):
    """
    Generate a REAL plan using the LLM.
    """
    if not state.planner:
        raise HTTPException(503, "Planner not initialized (check API Key)")
        
    state.current_task = request.task
    await state.broadcast("plan_generating", {"task": request.task})
    
    # Call the Brain
    try:
        plan_data = await state.planner.create_plan(request.task)
        state.current_plan = plan_data
        
        # Convert to Display Steps
        display_steps = []
        for i, step in enumerate(plan_data):
            display_steps.append(PlanStep(
                id=str(i),
                action=step.get("action", "unknown"),
                target=step.get("target", ""),
                value=step.get("value", "")
            ))

        await state.broadcast("plan_preview", {
            "task": request.task,
            "steps": [s.model_dump() for s in display_steps],
        })
        return {"success": True, "steps": len(display_steps)}
        
    except Exception as e:
        logger.error(f"Planning failed: {e}")
        raise HTTPException(500, f"Planning failed: {str(e)}")


@app.post("/plan/approve")
async def plan_approve():
    """Execute the generated plan."""
    if not state.current_plan:
        raise HTTPException(400, "No plan to approve")
    
    # Auto-start session when plan is approved (fixes execution blocking bug)
    state.session_active = True
        
    await state.broadcast("plan_approved", {"task": state.current_task})
    
    # Execute asynchronously
    asyncio.create_task(run_plan_execution())
    return {"success": True}


async def run_plan_execution():
    """Background task to execute steps."""
    for step in state.current_plan:
        if not state.session_active or state.takeover_active:
            break
            
        # Notify UI
        await state.broadcast("action_executing", step)
        
        # Broadcast speak event for frontend TTS
        if step.get("action") == "speak":
            await state.broadcast("voice_speak", {"text": step.get("value")})
        
        # Real Execution
        try:
            if state.planner:
                await state.planner.execute_step(step)
            else:
                await asyncio.sleep(1) # Fallback for testing
                
            await state.broadcast("action_completed", {"success": True})
        except Exception as e:
            await state.broadcast("action_failed", {"error": str(e)})
            break
    
    # Auto-cleanup: Reset session after execution completes
    state.session_active = False
    state.current_plan = []
    await state.broadcast("execution_finished", {"task": state.current_task})


@app.post("/takeover/request")
async def takeover_request():
    state.takeover_active = True
    await state.broadcast("takeover_requested", {"reason": "User requested"})
    return {"success": True}


@app.post("/takeover/complete")
async def takeover_complete():
    state.takeover_active = False
    await state.broadcast("takeover_completed", {})
    return {"success": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.websocket_clients.append(websocket)
    try:
        while True:
            await websocket.receive_json()
    except WebSocketDisconnect:
        state.websocket_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
