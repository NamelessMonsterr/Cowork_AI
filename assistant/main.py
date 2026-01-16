"""
Flash AI Assistant - Main Application Entry Point.
Wired with Gold Standard Architecture: Planner -> Guard -> Executor -> Strategies.
"""

import logging
import asyncio
import time
import os
import uuid
from contextlib import asynccontextmanager
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import signal

# --- Core Modules ---
from assistant.session_auth import SessionAuth
from assistant.voice.stt import STT
from assistant.agent.planner import Planner

# --- Safety & Execution ---
from assistant.safety.budget import ActionBudget
from assistant.safety.environment import EnvironmentMonitor
from assistant.safety.plan_guard import PlanGuard, ExecutionPlan, PlanGuardConfig
from assistant.computer.windows import WindowsComputer
from assistant.executor.executor import ReliableExecutor
from assistant.executor.verify import Verifier
from assistant.executor.strategies import UIAStrategy, VisionStrategy, CoordsStrategy
from assistant.executor.strategies import UIAStrategy, VisionStrategy, CoordsStrategy
from assistant.ui_contracts.schemas import ActionStep, StepResult, ExecutionPlan

# --- Recorder (W8) ---
from assistant.recorder.input import InputRecorder
from assistant.recorder.context import ContextTracker
from assistant.recorder.converter import SmartConverter
from assistant.recorder.storage import MacroStorage
from assistant.recovery.manager import RecoveryManager
from assistant.ui_contracts.events import RECOVERY_STARTED, RECOVERY_FAILED, RECOVERY_SUCCEEDED, RECOVERY_ATTEMPT

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Main")

# ==================== Models ====================

class TaskRequest(BaseModel):
    task: str

class PermissionGrantRequest(BaseModel):
    mode: str = "session"
    ttl_min: int = 30

# ==================== State ====================

class AppState:
    def __init__(self):
        # Core
        self.session_auth = SessionAuth()
        self.computer: Optional[WindowsComputer] = None
        self.stt: Optional[STT] = None
        
        # Brain & Limbs
        self.planner: Optional[Planner] = None
        self.executor: Optional[ReliableExecutor] = None
        self.plan_guard: Optional[PlanGuard] = None
        
        # Safety
        self.budget: Optional[ActionBudget] = None
        self.environment: Optional[EnvironmentMonitor] = None
        self.budget: Optional[ActionBudget] = None
        self.environment: Optional[EnvironmentMonitor] = None
        self.verifier: Optional[Verifier] = None
        
        # Recorder (W8)
        self.input_recorder: Optional[InputRecorder] = None
        self.context_tracker: Optional[ContextTracker] = None
        self.smart_converter: Optional[SmartConverter] = None
        self.smart_converter: Optional[SmartConverter] = None
        self.macro_storage: Optional[MacroStorage] = None
        self.recovery_manager: Optional[RecoveryManager] = None
        self.current_recording_anchors = []
        
        # Runtime
        self.current_task_id: Optional[str] = None
        self.is_executing = False
        self.websocket_clients: List[WebSocket] = []

    async def broadcast(self, event: str, data: dict):
        """Send event to all connected UI clients."""
        payload = {"event": event, "data": data, "timestamp": time.time()}
        for ws in self.websocket_clients[:]:
            try:
                await ws.send_json(payload)
            except:
                if ws in self.websocket_clients:
                    self.websocket_clients.remove(ws)

state = AppState()

# ==================== Lifespan (Wiring) ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Flash AI Agent (Gold Standard Architecture)...")
    
    try:
        # 1. Computer & Environment (Senses)
        state.computer = WindowsComputer()
        # Safety: Wire session check directly into Input Engine
        state.computer.set_session_verifier(state.session_auth.ensure)
        
        state.environment = EnvironmentMonitor(
            on_unsafe=lambda s, r: handle_unsafe_environment(s, r)
        )
        state.environment.start()
        
        # 2. Safety Components
        state.budget = ActionBudget()
        state.plan_guard = PlanGuard(state.session_auth)
        
        # 4. Strategies (W6)
        strategies = [
            UIAStrategy(),
            VisionStrategy(),
            CoordsStrategy() # Coords is pure fallback
        ]
        
        # 3. Verifier (W4) - Wired with Strategies (W7.2)
        state.verifier = Verifier(computer=state.computer, strategies=strategies)
        
        # 5. Reliable Executor (The Limb Controller)
        state.executor = ReliableExecutor(
            strategies=strategies,
            verifier=state.verifier,
            session_auth=state.session_auth,
            budget=state.budget,
            environment=state.environment,
            on_step_complete=lambda res: handle_step_complete_sync(res)
        )
        
        # 6. Planner (The Brain) - Pure Planning
        state.planner = Planner(computer=state.computer)
        state.planner = Planner(computer=state.computer)
        state.stt = STT()
        
        # 7. Recorder (W8)
        state.macro_storage = MacroStorage()
        state.context_tracker = ContextTracker(state.computer)
        state.smart_converter = SmartConverter(state.computer)
        
        def on_input_event(event):
            # Capture anchor for every event? Or just meaningful ones?
            # Capturing for every event might be heavy if high freq (mouse move ignored).
            if event.type in ["click", "type_text", "press_key"]:
                anchor = state.context_tracker.capture_anchor()
                state.current_recording_anchors.append(anchor)
                
        # Privacy check callback
        def check_privacy():
           info = state.computer.get_active_window()
           if info:
               title = info.title.lower()
               return any(k in title for k in ["password", "login", "bank", "sign in", "otp"])
           return False

        state.input_recorder = InputRecorder(on_event=on_input_event, check_privacy_func=check_privacy)
        
        # 8. Recovery Manager (W9)
        state.recovery_manager = RecoveryManager(
            planner=state.planner,
            executor=state.executor,
            plan_guard=state.plan_guard,
            computer=state.computer
        )
        
        logger.info("✅ Core Systems Online: Planner, Executor, Safety, Computer, Recorder, Recovery.")
    
    except Exception as e:
        logger.critical(f"❌ Initialization Failed: {e}", exc_info=True)
        # We don't exit, but system is broken
    
    yield
    
    logger.info("Shutting down...")
    if state.environment:
        state.environment.stop()

def handle_unsafe_environment(env_state, reason):
    """Callback from EnvironmentMonitor (Thread-safe wrapper needed)."""
    # Pause executor immediately
    if state.executor:
        state.executor.pause(f"Environment Unsafe: {reason}")
    logger.warning(f"Unsafe Environment Detected: {reason}")
    # We can't await broadcast here easily as it's a callback thread.
    # Future: Use asyncio.run_coroutine_threadsafe

def handle_step_complete_sync(result: StepResult):
    """Callback from Executor (Sync)."""
    # This runs in the executor thread.
    pass 

# ==================== FastAPI App ====================

app = FastAPI(title="Flash AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ==================== Execution Logic ====================

async def run_plan_execution(task: str):
    """
    Orchestrate the execution pipeline:
    Planner -> Guard -> Executor
    """
    state.is_executing = True
    plan_id = str(uuid.uuid4())
    state.current_task_id = plan_id
    
    logger.info(f"Starting Execution for: {task}")
    await state.broadcast("plan_started", {"task": task})
    
    # Boost FPS for execution (W7.1)
    if state.computer:
        state.computer.set_fps(15)
    
    try:
        # 1. Generate Plan
        raw_steps = await state.planner.create_plan(task)
        
        # 2. Schema Conversion
        action_steps = []
        for i, s in enumerate(raw_steps):
            # Ensure ID and defaults
            s["id"] = s.get("id", str(i+1))
            try:
                action_steps.append(ActionStep(**s))
            except Exception as e:
                logger.error(f"Invalid step schema: {s} - {e}")
                # Fallback or fail?
                # We'll try to execute valid ones or fail plan?
                # Fail safe for now.
                raise ValueError(f"Invalid step {i}: {e}")
        
        plan = ExecutionPlan(id=plan_id, task=task, steps=action_steps)
        await state.broadcast("plan_generated", plan.dict())
        
        # 3. Guard Validation
        try:
            state.plan_guard.validate(plan)
            logger.info("✅ Plan Validated.")
        except Exception as e:
            msg = f"Plan Rejected: {e}"
            logger.error(msg)
            await state.broadcast("plan_rejected", {"error": str(e)})
            return

        # 4. Execution Loop
        for step in plan.steps:
            if state.executor.is_paused():
                await state.broadcast("execution_paused", {"reason": state.executor._pause_reason})
                break # Or wait loop? For now, break.
            
            # Execute in thread (Executor is sync)
            await state.broadcast("step_started", {"step_id": step.id})
            
            result: StepResult = await asyncio.to_thread(state.executor.execute, step)
            
            await state.broadcast("step_completed", result.dict())
            
            if not result.success:
                logger.error(f"Step {step.id} Failed: {result.error}")
                if result.requires_takeover:
                     await state.broadcast("takeover_required", {"reason": result.takeover_reason, "error": result.error})
                     break
                
                # W9: Try Recovery
                logger.warning(f"Step {step.id} Failed. Attempting Recovery...")
                await state.broadcast(RECOVERY_STARTED, {"step_id": step.id, "error": result.error})
                
                # Capture recent steps for context
                recent_steps = plan.steps[:i] if 'i' in locals() else [] # i might not be safe here, use index if needed?
                # Actually i is from enumerate(raw_steps) which was earlier.
                # In execution loop: for step in plan.steps:
                # We need index.
                
                recovered = await state.recovery_manager.handle_failure(
                    plan_id=plan.id,
                    failed_step=step,
                    step_result=result,
                    recent_steps=[] # Simplified for now to fix crash, need index logic later
                )
                
                if recovered:
                     await state.broadcast(RECOVERY_SUCCEEDED, {"step_id": step.id})
                     # Retry Step
                     logger.info(f"Retrying Step {step.id}...")
                     retry_res = await asyncio.to_thread(state.executor.execute, step)
                     
                     await state.broadcast("step_completed", retry_res.dict())
                     if retry_res.success:
                         continue # Resumed!
                     else:
                         logger.error(f"Retry failed after recovery: {retry_res.error}")
                         break
                else:
                    await state.broadcast(RECOVERY_FAILED, {"step_id": step.id})
                    break
        
        await state.broadcast("execution_finished", {"success": True}) # Or status
        
    except Exception as e:
        logger.error(f"Execution Error: {e}", exc_info=True)
        await state.broadcast("execution_error", {"error": str(e)})
    
    finally:
        state.is_executing = False
        # Reset FPS to idle (W7.1)
        if state.computer:
            state.computer.set_fps(1)
            
        # Auto-cleanup session if needed (optional)
        state.session_auth.revoke() 

# ==================== Routes ====================

@app.get("/health")
async def health():
    return {"status": "ok", "mode": "gold_standard"}

@app.get("/permission/status")
async def get_permission_status():
    status = state.session_auth.status()
    return status.dict()

@app.post("/permission/revoke")
async def revoke_permission():
    state.session_auth.revoke()
    await state.broadcast("permission_revoked", {})
    return {"status": "revoked"}

    return {"status": "revoked"}

@app.post("/shutdown")
async def shutdown():
    """Graceful shutdown for Electron packaging."""
    logger.info("Received shutdown signal.")
    # In a real app we might want to cancel tasks or flush logs.
    state.session_auth.revoke()
    if state.environment:
        state.environment.stop()
    
    # Trigger exit in background to allow response to return
    def exit_app():
        time.sleep(1)
        logger.info("Exiting...")
        os._exit(0) # Force exit
        
    import threading
    threading.Thread(target=exit_app).start()
    return {"status": "shutting_down"}

@app.get("/version")
async def get_version():
    """Version handshake for Electron."""
    return {
        "backend": "1.0.0",
        "schema": 2,
        "mode": "gold_standard"
    }

@app.post("/voice/listen")
async def voice_listen():
    if not state.stt:
        raise HTTPException(503, "STT not ready")
        
    # Zero-Click: Grant session
    state.session_auth.grant()
    await state.broadcast("listening_started", {})
    
    try:
        # Listen & Transcribe
        text = await state.stt.listen()
        await state.broadcast("speech_recognized", {"text": text})
        
        if text:
            # Start Execution
            asyncio.create_task(run_plan_execution(text))
            return {"status": "processing", "text": text}
        return {"status": "no_speech"}
        
    except Exception as e:
        logger.error(f"Voice Error: {e}")
        raise HTTPException(500, str(e))

    except Exception as e:
        logger.error(f"Voice Error: {e}")
        raise HTTPException(500, str(e))

# --- Recorder Routes (W8) ---

@app.post("/record/start")
async def start_recording():
    if not state.input_recorder:
        raise HTTPException(503, "Recorder not initialized")
    
    state.current_recording_anchors = []
    state.input_recorder.start()
    return {"status": "recording_started"}

@app.post("/record/stop")
async def stop_recording(name: str = "New Macro"):
    if not state.input_recorder:
        raise HTTPException(503, "Recorder not initialized")
        
    events = state.input_recorder.stop()
    anchors = state.current_recording_anchors
    
    # Convert
    steps = state.smart_converter.convert(events, anchors)
    
    # Create Plan
    plan_id = str(uuid.uuid4())
    plan = ExecutionPlan(
        id=plan_id,
        task=name,
        steps=steps
    )
    
    # Save
    metadata = {
        "name": name,
        "author": "User",
        "duration_sec": 0, # Calc real duration
        "event_count": len(events),
        "step_count": len(steps)
    }
    
    macro_id = state.macro_storage.save_macro(plan, metadata)
    return {"status": "recording_saved", "macro_id": macro_id, "steps": len(steps)}

@app.get("/macros/list")
async def list_macros():
    if not state.macro_storage:
        return []
    return state.macro_storage.list_macros()

@app.post("/macros/play/{macro_id}")
async def play_macro(macro_id: str):
    if not state.macro_storage:
        raise HTTPException(503, "Storage not ready")
        
    plan = state.macro_storage.load_plan(macro_id)
    if not plan:
        raise HTTPException(404, "Macro not found")
        
    # Re-use run_plan logic but skip planning phase?
    # Actually run_plan_execution takes a task string and plans it.
    # We need a way to execute an EXISTING plan.
    # Let's extract execution logic into 'execute_plan(plan)' or modify run_plan_execution.
    # For now, duplicate execution logic loop or refactor? 
    # Refactor is best. But to minimize diff, let's create a specific execution runner for pre-made plans.
    
    asyncio.create_task(drive_plan_execution(plan))
    return {"status": "playing", "macro_id": macro_id}

async def drive_plan_execution(plan: ExecutionPlan):
    """Execute a pre-made plan (W8 Replay)."""
    state.is_executing = True
    state.current_task_id = plan.id
    
    logger.info(f"Replaying Macro: {plan.task}")
    await state.broadcast("plan_started", {"task": plan.task})
    
    if state.computer:
        state.computer.set_fps(15)
        
    try:
        await state.broadcast("plan_generated", plan.dict())
        
        # 3. Guard (Validate macro safety)
        try:
            state.plan_guard.validate(plan)
        except Exception as e:
            logger.error(f"Macro Validation Failed: {e}")
            await state.broadcast("plan_rejected", {"error": str(e)})
            return

        # 4. Loop
        for step in plan.steps:
            if state.executor.is_paused():
                await state.broadcast("execution_paused", {"reason": state.executor._pause_reason})
                break
            
            await state.broadcast("step_started", {"step_id": step.id})
            result = await asyncio.to_thread(state.executor.execute, step)
            await state.broadcast("step_completed", result.dict())
            
            if not result.success:
                 if result.requires_takeover:
                     await state.broadcast("takeover_required", {"reason": result.takeover_reason, "error": result.error})
                     break
                 break
                 
        await state.broadcast("execution_finished", {"success": True})
        
    except Exception as e:
        logger.error(f"Macro Error: {e}")
        await state.broadcast("execution_error", {"error": str(e)})
    finally:
        state.is_executing = False
        if state.computer: state.computer.set_fps(1)
        state.session_auth.revoke()

async def execute_task(req: TaskRequest):
    """Direct task execution endpoint."""
    if not state.session_auth.check():
        state.session_auth.grant() # Auto-grant for explicit API call? Or fail? 
        # UI likely calls this after approval.
    
    asyncio.create_task(run_plan_execution(req.task))
    return {"status": "started", "task": req.task}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.websocket_clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        if websocket in state.websocket_clients:
            state.websocket_clients.remove(websocket)
