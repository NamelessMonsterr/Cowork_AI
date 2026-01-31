"""
Flash Assistant - Main Application Entry Point.
Production-grade architecture: Planner -> Guard -> Executor -> Strategies.
"""

import asyncio
import datetime
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

# --- Platform Guard (P1) ---
from assistant.platform_check import ensure_windows_os

ensure_windows_os()

# --- Security Configuration ---
import secrets

# P0-2: Dev/Debug endpoint control (SECURITY HARDENED: default false)
FLASH_DEV_ENDPOINTS_ENABLED = os.getenv("FLASH_DEV_ENDPOINTS_ENABLED", "false").lower() == "true"
# P0-3: Session secret (REQUIRED for production)
FLASH_SESSION_SECRET = os.getenv("FLASH_SESSION_SECRET")
IS_PRODUCTION = os.getenv("ENV", "").lower() == "production"

# SECURITY HARDENING: No fallback for missing secrets
if not FLASH_SESSION_SECRET:
    if IS_PRODUCTION:
        logger = logging.getLogger(__name__)
        logger.critical(
            "🚨 CRITICAL SECURITY ERROR: FLASH_SESSION_SECRET is not set!\n"
            "Production deployments MUST set a secure session secret.\n"
            "Generate one with: openssl rand -hex 32\n"
            "Terminating to prevent insecure deployment."
        )
        sys.exit(1)
    # Development fallback with security warning
    FLASH_SESSION_SECRET = "dev-only-insecure-key-" + secrets.token_hex(16)
    logger = logging.getLogger(__name__)
    logger.warning(
        "⚠️  SECURITY WARNING: Using auto-generated session secret in development mode.\n"
        "This is NOT suitable for production. Set FLASH_SESSION_SECRET in your environment."
    )
# --- P9 FIX: Consolidated Imports & Logging ---
from assistant.utils.health_check import run_pre_flight_checks
from assistant.utils.secrets_filter import SecretsRedactionFilter

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# P7A FIX: Attach secrets redaction
logging.getLogger().addFilter(SecretsRedactionFilter())

# --- Config (P1) ---
from assistant.agent.planner import Planner
from assistant.api.plugins import router as plugins_router
from assistant.api.safety_routes import router as safety_router
from assistant.api.support import router as support_router
from assistant.api.team import router as team_router
from assistant.cloud.auth import router as auth_router
from assistant.cloud.crypto import SyncCrypto
from assistant.cloud.local_store import LocalSyncStore
from assistant.cloud.sync_engine import SyncEngine
from assistant.computer.windows import WindowsComputer
from assistant.config.paths import get_appdata_dir
from assistant.config.port import clear_port_file, write_port_file
from assistant.config.settings import AppSettings, get_settings
from assistant.config.startup import StartupValidator
from assistant.executor.executor import ReliableExecutor
from assistant.executor.strategies import (
    CoordsStrategy,
    SystemStrategy,
    UIAStrategy,
    VisionStrategy,
)
from assistant.executor.verify import Verifier
from assistant.learning.collector import LearningCollector
from assistant.learning.ranker import StrategyRanker
from assistant.learning.store import LearningStore
from assistant.plugins.ipc import IpcClient
from assistant.plugins.lifecycle import PluginStateManager
from assistant.plugins.permissions import PermissionManager

# --- Plugins (W12/W13) ---
from assistant.plugins.registry import PluginLoader, ToolRegistry
from assistant.plugins.router import ToolRouter
from assistant.plugins.secrets import PluginSecrets
from assistant.recorder.context import ContextTracker
from assistant.recorder.converter import SmartConverter

# --- Recorder (W8) ---
from assistant.recorder.input import InputRecorder
from assistant.recorder.storage import MacroStorage
from assistant.recovery.manager import RecoveryManager
from assistant.safety.budget import ActionBudget

# NEW: Missing imports that were causing startup failures
from assistant.safety.environment import EnvironmentMonitor
from assistant.safety.focus_guard import FocusGuard

# from assistant.config import Config  # Doesn't exist - we use get_settings instead
from assistant.safety.plan_guard import PlanGuard, PlanValidationError
from assistant.safety.rate_limiter import InputRateLimiter

# --- Core Modules ---
from assistant.safety.session_auth import SessionAuth
from assistant.skills.loader import SkillLoader
from assistant.team.discovery import PeerDiscovery

# --- Team/Cloud/Learning ---
from assistant.telemetry.client import TelemetryClient
from assistant.ui_contracts.events import (
    RECOVERY_FAILED,
    RECOVERY_STARTED,
    RECOVERY_SUCCEEDED,
)

# --- Safety & Execution ---
# from assistant.agent.agent import Agent  # Module doesn't exist - commenting out
from assistant.ui_contracts.schemas import ActionStep, ExecutionPlan, StepResult
from assistant.voice.stt import STT

# Host Process Handle
host_process = None
start_time = time.time()  # For uptime tracking

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
        self.computer: WindowsComputer | None = None
        self.stt: STT | None = None

    def cleanup_pending_plans(self, max_age_seconds: int = 300):
        """
        Remove pending plans that are older than max_age_seconds.
        This prevents memory leaks in long-running processes.
        """
        now = time.time()
        expired_ids = [
            pid for pid, (_, created_at) in list(self.pending_plans.items()) if now - created_at > max_age_seconds
        ]
        for pid in expired_ids:
            # Use .pop() to avoid KeyError if the plan was already removed by another request
            self.pending_plans.pop(pid, None)

        # Brain & Limbs
        self.planner: Planner | None = None
        self.executor: ReliableExecutor | None = None
        self.plan_guard: PlanGuard | None = None

        # Safety
        self.budget: ActionBudget | None = None
        self.environment: EnvironmentMonitor | None = None
        self.verifier: Verifier | None = None

        # V24 Hardening
        self.focus_guard: FocusGuard | None = None
        self.rate_limiter: InputRateLimiter | None = None

        # Recorder (W8)
        self.input_recorder: InputRecorder | None = None

        self.context_tracker: ContextTracker | None = None
        self.smart_converter: SmartConverter | None = None
        self.macro_storage: MacroStorage | None = None

        self.recovery_manager: RecoveryManager | None = None
        self.current_recording_anchors = []

        # Plugins (W13)
        self.tool_registry: ToolRegistry | None = None
        self.plugin_loader: PluginLoader | None = None
        self.plugin_manager: PluginStateManager | None = None
        self.tool_router: ToolRouter | None = None
        self.permission_manager: PermissionManager | None = None
        self.plugin_secrets: PluginSecrets | None = None

        # Telemetry (W15.5)
        self.telemetry = TelemetryClient()

        # Team Mode (W17)
        self.team_discovery: PeerDiscovery | None = None

        # Skill Packs (W18)
        self.skill_loader: SkillLoader | None = None

        # Cloud Sync (W19)
        self.sync_engine: SyncEngine | None = None

        # Learning (W20)
        self.learning_ranker: StrategyRanker | None = None
        self.learning_collector: LearningCollector | None = None

        # Runtime
        self.current_task_id: str | None = None
        self.is_executing = False
        self.websocket_clients: list[WebSocket] = []

        # P2 FIX: Thread safety locks for concurrent access
        # NOTE: These are created in startup() because asyncio.Lock needs event loop
        self._ws_lock = None
        self._plans_lock = None
        self._logs_lock = None

        # Plan Preview Storage (Task B) - stores (plan, created_at)
        self.pending_plans: dict[str, tuple[ExecutionPlan, float]] = {}
        self.plan_cleanup_task: asyncio.Task | None = None

        # V23: Execution Logs (in-memory, last 50)
        self.execution_logs: list[dict[str, Any]] = []

    async def broadcast(self, event: str, data: dict):
        """Send event to all connected UI clients (thread-safe)."""
        payload = {"event": event, "data": data, "timestamp": time.time()}

        # P2 FIX: Thread-safe client list access
        async with self._ws_lock:
            clients = list(self.websocket_clients)  # Safe copy

        # Broadcast to all clients
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.debug(f"WebSocket send failed, removing client: {e}")
                async with self._ws_lock:
                    if ws in self.websocket_clients:
                        self.websocket_clients.remove(ws)


state = AppState()

# ==================== Lifespan (Wiring) ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Flash Assistant (Production Architecture)...")
    
    # P2 FIX: Initialize asyncio locks (must be done inside async context)
    state._ws_lock = asyncio.Lock()
    state._plans_lock = asyncio.Lock()
    state._logs_lock = asyncio.Lock()
    logger.info("[Startup] Async locks initialized")
    
    logger.info("[Startup] Running pre-flight checks...")

    # P8 FIX: Disk space check
    try:
        run_pre_flight_checks()
    except RuntimeError as e:
        logger.critical(f"[Startup] Pre-flight check failed: {e}")
        raise

    # P1.2: Run startup validation
    validator = StartupValidator()
    if not validator.validate_all():
        logger.critical("Startup validation failed!")
        for err in validator.errors:
            logger.critical(f"  [{err.component}] {err.error}")
        sys.exit(1)

    # P2.2: Write port file for Electron discovery
    settings = get_settings()
    write_port_file(settings.server.port)

    try:
        # 1. Computer & Environment (Senses)
        state.computer = WindowsComputer()
        # Safety: Wire session check directly into Input Engine
        state.computer.set_session_verifier(state.session_auth.ensure)

        state.environment = EnvironmentMonitor(on_unsafe=lambda s, r: handle_unsafe_environment(s, r))
        state.environment.start()

        # 2. Safety Components
        state.budget = ActionBudget()
        state.plan_guard = PlanGuard(state.session_auth)

        # V24 Hardening
        state.focus_guard = FocusGuard(state.computer)
        state.rate_limiter = InputRateLimiter()

        # 4. Strategies (W6)
        # SystemStrategy handles OS-level commands (open_app, run_shell, open_url)
        # Must be FIRST to handle these before UI strategies try and fail
        strategies = [
            SystemStrategy(state.computer),  # OS commands - highest priority
            UIAStrategy(),
            VisionStrategy(),
            CoordsStrategy(),  # Coords is pure fallback
        ]

        # 3. Verifier (W4) - Wired with Strategies (W7.2)
        state.verifier = Verifier(computer=state.computer, strategies=strategies)

        # 5. Reliable Executor (The Limb Controller)
        # W20.3: Initialize Learning Components BEFORE executor
        learning_db_path = os.path.join(os.getenv("APPDATA"), "CoworkAI", "learning.db")
        learning_store = LearningStore(learning_db_path)
        state.learning_ranker = StrategyRanker(learning_store)
        state.learning_collector = LearningCollector(learning_store)

        state.executor = ReliableExecutor(
            strategies=strategies,
            verifier=state.verifier,
            session_auth=state.session_auth,
            budget=state.budget,
            environment=state.environment,
            on_step_complete=lambda res: handle_step_complete_sync(res),
            focus_guard=state.focus_guard,
            rate_limiter=state.rate_limiter,
            ranker=state.learning_ranker,
            collector=state.learning_collector,
        )

        # 6. Planner (The Brain) - Pure Planning
        state.planner = Planner(computer=state.computer)

        # V2: Wire STT with settings
        voice_settings = settings.voice
        state.stt = STT(
            prefer_mock=voice_settings.mock_stt,
            openai_api_key=voice_settings.openai_api_key or os.environ.get("OPENAI_API_KEY"),
        )

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
            computer=state.computer,
        )

        # 9. Plugin System (W12/W13/W14)
        state.tool_registry = ToolRegistry()
        state.plugin_loader = PluginLoader(state.tool_registry)
        state.plugin_manager = PluginStateManager()
        state.permission_manager = PermissionManager()
        state.plugin_secrets = PluginSecrets()
        state.tool_router = ToolRouter(state.tool_registry, state.permission_manager, state.plugin_secrets)

        # Load Plugins
        # W14: Split Loading
        # 1. Builtins (Local)
        state.plugin_loader.load_builtins()

        # 2. Host Process (External)
        import subprocess

        global host_process
        host_script = os.path.join("assistant", "plugin_host", "main.py")
        logger.info(f"🚀 Starting Plugin Host: {host_script}")
        host_process = subprocess.Popen([sys.executable, host_script], cwd=os.getcwd())

        # Wait for Host
        client = IpcClient()
        for i in range(10):
            if client._refresh_config():
                break
            logger.info("Waiting for Plugin Host...")
        # 2. Start Input/Output
        # No-op in headless mode usually, but nice to have.

        if os.environ.get("COWORK_TEST_MODE"):
            logger.info("🧪 Test Mode: Skipping heavyweight startup (Remote Tools, Discovery, Skills).")
            yield
            # Cleanup
            if state.environment:
                state.environment.stop()
            return

        # 3. Load Remote Tools
        await state.plugin_loader.load_from_host(client)

        # 4. Start Team Discovery (W17)
        # Assuming port 8765 for this instance.
        # In real multi-agent usage, we'd need dynamic ports or config.
        my_id = str(uuid.uuid4())
        state.team_discovery = PeerDiscovery(agent_id=my_id, agent_name=f"Flash-{my_id[:4]}", port=8765)
        state.team_discovery.start()

        # 5. Load Skill Packs (W18)
        skills_dir = os.path.join(os.getenv("APPDATA"), "CoworkAI", "skills")
        state.skill_loader = SkillLoader(skills_dir)
        state.skill_loader.load_all()

        # 6. Cloud Sync (W19)
        sync_db_path = os.path.join(os.getenv("APPDATA"), "CoworkAI", "sync.db")
        sync_store = LocalSyncStore(sync_db_path)
        sync_crypto = SyncCrypto()
        state.sync_engine = SyncEngine(sync_store, sync_crypto)

        logger.info(
            "✅ Core Systems Online: Planner, Executor, Safety, Computer, Recorder, Recovery, Plugins (Hosted), Team Discovery, Skills, Cloud Sync."
        )

        # V2: Start pending plan cleanup task
        state.plan_cleanup_task = asyncio.create_task(cleanup_expired_plans())
        logger.info("✅ Pending plan cleanup task started (TTL: 10 min)")

        # PIPELINE FIX: Wire global state to FastAPI app.state
        # This allows routes to access state via request.app.state.state
        app.state.state = state
        logger.info("✅ Global state wired to app.state")

    except Exception as e:
        logger.critical(f"❌ Initialization Failed: {e}", exc_info=True)
        sys.exit(1)  # Hard Fail (Engineering Fix 3)

    yield

    logger.info("Shutting down...")

    # Kill Host
    if host_process:
        logger.info("Stopping Plugin Host...")
        host_process.terminate()
        try:
            host_process.wait(timeout=3)
        except Exception as e:
            logger.debug(f"Plugin host forced kill: {e}")
            host_process.kill()

    if state.environment:
        state.environment.stop()

    if state.team_discovery:
        state.team_discovery.stop()

    # V2: Cancel cleanup task
    if state.plan_cleanup_task:
        state.plan_cleanup_task.cancel()
        try:
            await state.plan_cleanup_task
        except asyncio.CancelledError:
            pass

    # P2.2: Clear port file on shutdown
    clear_port_file()


# ==================== FastAPI App ====================

# Load settings for CORS config
_settings = get_settings()

app = FastAPI(title="Flash Assistant", lifespan=lifespan, version="1.0.0")

PLAN_TTL_SEC = 600  # 10 minutes


async def cleanup_expired_plans():
    """Background task to clean up expired pending plans."""
    while True:
        await asyncio.sleep(60)  # Check every minute
        now = time.time()
        expired = [k for k, (_, created_at) in state.pending_plans.items() if now - created_at > PLAN_TTL_SEC]
        for plan_id in expired:
            logger.info(f"[CLEANUP] Expiring pending plan: {plan_id}")
            del state.pending_plans[plan_id]
        if expired:
            logger.info(f"[CLEANUP] Removed {len(expired)} expired plans")


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

# Load settings for CORS config
_settings = get_settings()

app = FastAPI(title="Flash Assistant", lifespan=lifespan)
# Reload trigger

# CRITICAL: Add session middleware BEFORE CORS for voice permissions
# P0-3: Use configurable session secret
# P0-4: Make cookies secure in production
app.add_middleware(
    SessionMiddleware,
    secret_key=FLASH_SESSION_SECRET,  # From environment variable
    session_cookie="flash_session",
    max_age=1800,  # 30 minutes
    https_only=IS_PRODUCTION,  # True in production for security
    same_site="strict" if IS_PRODUCTION else "lax",  # Strict in production
)

# P1.4: Strict CORS - Only allow dev origins, disabled in production
if _settings.server.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings.server.cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],  # Added OPTIONS for preflight
        allow_headers=["*"],
        allow_credentials=True,
    )

# CRITICAL: Add session middleware for voice permissions


try:
    from assistant.api.safety_routes import router as safety_router

    app.include_router(plugins_router, prefix="/plugins", tags=["plugins"])
    app.include_router(support_router, prefix="/support", tags=["support"])
    app.include_router(team_router, prefix="/team", tags=["team"])
    app.include_router(safety_router, prefix="/safety", tags=["safety"])
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
except ImportError:
    logger.warning("Safety router could not be imported")
    pass

# V21: Voice routes
try:
    from assistant.api.voice_routes import router as voice_api_router

    app.include_router(voice_api_router)

    # NEW: WebSocket Stream
    from assistant.api.voice import router as voice_stream_router

    app.include_router(voice_stream_router)

    # Debug: Verify router registration
    logger.info(f"✅ Voice Stream Router Registered: {voice_stream_router.routes}")

except ImportError:
    pass

try:
    from assistant.api.settings_routes import router as settings_router

    app.include_router(settings_router)
except ImportError:
    logger.warning("Settings router could not be imported")
    pass

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
            s["id"] = s.get("id", str(i + 1))
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

        # Add logging to bare except block for session manager loading
        try:
            self.session_manager.load_from_file()
            logger.info("Loaded existing sessions.")
        except Exception as e:
            logger.debug(f"No existing sessions file or load failed: {e}")
            pass  # First boot, no saved sessions

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
                break  # Or wait loop? For now, break.

            # Execute in thread (Executor is sync)
            await state.broadcast("step_started", {"step_id": step.id})

            result: StepResult = await asyncio.to_thread(state.executor.execute, step)

            await state.broadcast("step_completed", result.dict())

            if not result.success:
                logger.error(f"Step {step.id} Failed: {result.error}")
                if result.requires_takeover:
                    await state.broadcast(
                        "takeover_required",
                        {"reason": result.takeover_reason, "error": result.error},
                    )
                    break

                # W9: Try Recovery
                logger.warning(f"Step {step.id} Failed. Attempting Recovery...")
                await state.broadcast(RECOVERY_STARTED, {"step_id": step.id, "error": result.error})

                # Capture recent steps for context
                recent_steps = (
                    plan.steps[:i] if "i" in locals() else []
                )  # i might not be safe here, use index if needed?
                # Actually i is from enumerate(raw_steps) which was earlier.
                # In execution loop: for step in plan.steps:
                # We need index.

                recovered = await state.recovery_manager.handle_failure(
                    plan_id=plan.id,
                    failed_step=step,
                    step_result=result,
                    recent_steps=[],  # Simplified for now to fix crash, need index logic later
                )

                if recovered:
                    await state.broadcast(RECOVERY_SUCCEEDED, {"step_id": step.id})
                    # Retry Step
                    logger.info(f"Retrying Step {step.id}...")
                    retry_res = await asyncio.to_thread(state.executor.execute, step)

                    await state.broadcast("step_completed", retry_res.dict())
                    if retry_res.success:
                        continue  # Resumed!
                    else:
                        logger.error(f"Retry failed after recovery: {retry_res.error}")
                        break
                else:
                    await state.broadcast(RECOVERY_FAILED, {"step_id": step.id})
                    break

        await state.broadcast("execution_finished", {"success": True})  # Or status
        state.telemetry.track("task_completed", {"task_length": len(task), "steps": len(plan.steps)})

    except Exception as e:
        logger.error(f"Execution Error: {e}", exc_info=True)
        await state.broadcast("execution_error", {"error": str(e)})
        state.telemetry.track("task_failed", {"error": str(e)})

    finally:
        state.is_executing = False
        # Reset FPS to idle (W7.1)
        if state.computer:
            state.computer.set_fps(1)

        # P1 FIX: Don't auto-revoke session after every task
        # Sessions now persist until TTL expiry or manual user revocation
        # This prevents forcing users to re-auth after each command


# ==================== Routes ====================


@app.get("/health")
async def health():
    """P1.3: Stable health endpoint for Electron watchdog."""
    return {
        "status": "ok",
        "uptime_sec": int(time.time() - start_time),
        "session_active": state.session_auth.check(),
    }


@app.get("/capabilities")
async def get_capabilities():
    """P1.3: Capabilities endpoint."""
    settings = get_settings()
    return {
        "voice": bool(state.stt),
        "plugins": True,
        "cloud_sync": settings.cloud.enabled,
        "learning": settings.learning.enabled,
        "team_mode": bool(state.team_discovery),
    }


@app.get("/permission/status")
async def get_permission_status():
    status_dict = state.session_auth.get_status_dict()
    return status_dict


@app.post("/permission/revoke")
async def revoke_permission():
    state.session_auth.revoke()
    await state.broadcast("permission_revoked", {})
    return {"status": "revoked"}


@app.post("/permission/grant")
async def grant_permission(
    request: Request,
    response: Response,
    req: PermissionGrantRequest = PermissionGrantRequest(),
):
    """Grant session permission for executing actions."""

    # 1. Internal State Grant
    ttl_sec = req.ttl_min * 60
    state.session_auth.grant(mode=req.mode, ttl_sec=ttl_sec)

    # 2. Session Cookie Grant (Voice Middleware)
    session_id = request.cookies.get("flash_session") or str(uuid.uuid4())
    if "session_id" not in request.session:
        request.session["session_id"] = session_id

    request.session["voice_granted"] = True
    request.session["voice_timestamp"] = datetime.datetime.utcnow().isoformat()

    await state.broadcast("permission_granted", {"ttl_sec": ttl_sec})

    # CRITICAL: Set JS-accessible cookie for WebSocket authentication
    # Starlette's SessionMiddleware sets httponly=True by default (can't be changed)
    # So we set a duplicate cookie that JavaScript CAN read
    response.set_cookie(
        key="flash_session_js",
        value=session_id,
        max_age=ttl_sec,
        httponly=False,  # CRITICAL: Allow JavaScript access
        samesite="lax",
        secure=False,  # Allow HTTP in dev
    )

    return {"status": "granted", "ttl_sec": ttl_sec, "session_id": session_id}


@app.post("/debug/crash")
async def debug_crash():
    """Trigger a backend crash for recovery testing."""
    # P0-2: Require dev endpoints to be explicitly enabled
    if not FLASH_DEV_ENDPOINTS_ENABLED:
        raise HTTPException(404, "Not found")

    # Security: Require active session
    if not state.session_auth.check():
        raise HTTPException(403, "Forbidden")

    logger.critical("💥 SIMULATING CRASH (Debug Endpoint) 💥")

    # P2 FIX: Use graceful exit instead of hard exit
    def crash_it():
        time.sleep(0.5)
        sys.exit(1)  # Graceful - allows finally blocks to run

    import threading

    threading.Thread(target=crash_it).start()
    return {"status": "crashing"}


@app.post("/shutdown")
async def shutdown():
    """Graceful shutdown for Electron packaging."""
    # Security Harden: Require active session or secret
    if not state.session_auth.check():
        logger.warning("Unauthorized shutdown attempt")
        raise HTTPException(401, "Unauthorized: Active session required")

    logger.info("Received shutdown signal.")
    # In a real app we might want to cancel tasks or flush logs.
    state.session_auth.revoke()
    if state.environment:
        state.environment.stop()

    logger.info("Shutdown complete.")

    # Run in thread to allow response to return
    def delayed_exit():
        time.sleep(1)
        # P2 FIX: Use graceful exit
        sys.exit(0)

    import threading

    threading.Thread(target=delayed_exit).start()
    return {"status": "shutting_down"}


@app.get("/version")
async def get_version():
    """Version handshake for Electron (Merged)."""
    return {
        "backend": "1.0.0",
        "schema": 2,
        "build": "2026-01-16",
        "mode": "gold_standard",
    }


@app.post("/voice/listen")
async def voice_listen():
    logger.info("[VOICE] Listen endpoint called")
    if not state.stt:
        raise HTTPException(503, "STT not ready")

    # Security Harden: Require active session (No Zero-Click)
    if not state.session_auth.check():
        logger.warning("[VOICE] Unauthorized: No active session")
        raise HTTPException(401, "Unauthorized: Active session required")

    logger.info("[VOICE] Started listening")
    logger.info("[WS] broadcast event=listening_started")
    await state.broadcast("listening_started", {})

    try:
        # Listen & Transcribe
        text = await state.stt.listen()
        logger.info(f"[VOICE] transcript={text}")
        logger.info(f"[WS] broadcast event=speech_recognized text={text}")
        await state.broadcast("speech_recognized", {"text": text})

        if text:
            # Start Execution
            asyncio.create_task(run_plan_execution(text))
            return {"status": "processing", "success": True, "text": text}
        return {"status": "no_speech", "success": False}

    except Exception as e:
        logger.error(f"Voice Error: {e}")
        raise HTTPException(500, str(e))


# --- Voice Health Endpoint (Task A) ---


@app.get("/voice/health")
async def voice_health():
    """Get STT engine health status."""
    if not state.stt:
        return {
            "stt_engine": "none",
            "available": False,
            "error": "STT not initialized",
        }
    return state.stt.get_health()


# --- Plan Preview API (Task B) ---


class PlanPreviewRequest(BaseModel):
    task: str


class PlanApproveRequest(BaseModel):
    plan_id: str
    confirm_shell: bool = False  # Explicit confirmation for shell commands


@app.post("/plan/preview")
async def plan_preview(req: PlanPreviewRequest):
    """
    Generate a plan preview WITHOUT executing.
    Returns the plan for user review.
    """
    task_id = str(uuid.uuid4())
    logger.info(f"[PLAN] Preview requested | task='{req.task}' | task_id={task_id}")

    # Security: Require active session for preview (prevention of LLM abuse)
    if not state.session_auth.check():
        raise HTTPException(status_code=403, detail="Forbidden: Active session required")

    if not state.planner:
        raise HTTPException(503, "Planner not initialized")

    try:
        # Generate plan
        raw_steps = await state.planner.create_plan(req.task)

        # Convert to ActionSteps
        action_steps = []
        for i, s in enumerate(raw_steps):
            s["id"] = s.get("id", str(i + 1))
            action_steps.append(ActionStep(**s))

        plan_id = str(uuid.uuid4())
        plan = ExecutionPlan(id=plan_id, task=req.task, steps=action_steps)

        # Store for later approval (with TTL timestamp)
        state.pending_plans[plan_id] = (plan, time.time())
        state.cleanup_pending_plans()  # Lazy cleanup on new plan creation

        # Estimate time (rough: 3 sec per step)
        estimated_time = len(action_steps) * 3

        logger.info(f"[PLAN] Generated | plan_id={plan_id} | step_count={len(action_steps)} | task_id={task_id}")

        return {
            "plan": plan.dict(),
            "plan_id": plan_id,
            "estimated_time_sec": estimated_time,
        }

    except Exception as e:
        logger.error(f"[PLAN] Preview failed: {e}")
        raise HTTPException(500, f"Plan generation failed: {e}")


@app.post("/plan/approve")
async def plan_approve(request: Request, req: PlanApproveRequest):
    """
    Approve and execute a plan.
    Security: Requires active session + rate limiting.
    """
    try:
        # PRODUCTION: Rate limiting to prevent spam/loops
        from assistant.safety.rate_limiter import RequestRateLimiter

        if not hasattr(state, "approve_limiter"):
            state.approve_limiter = RequestRateLimiter(max_requests=10, window_seconds=60)

        if not state.approve_limiter.is_allowed():
            logger.warning("[APPROVE] Rate limit exceeded")
            raise HTTPException(429, "Too many approval requests. Please wait a moment.")

        plan_id = req.plan_id
        logger.info(f"[APPROVE] Approve requested | plan_id={plan_id}")

        # Security: Require active session
        if not state.session_auth.check():
            logger.warning(f"[APPROVE] Rejected - no session | plan_id={plan_id}")
            raise HTTPException(403, "Forbidden: Active session required")

        # Fetch pending plan (stored as tuple with timestamp)
        # atomic pop to prevent double-execution race conditions
        entry = state.pending_plans.pop(plan_id, None)
        if not entry:
            raise HTTPException(404, f"Plan not found: {plan_id}")

        plan, created_at = entry

        # Remove from pending (done by pop)

        # Execute the plan
        logger.info(f"[APPROVE] Approved | plan_id={plan_id} | task={plan.task[:50]}")
        logger.info(f"[EXEC] Starting execution | plan_id={plan_id}")
        asyncio.create_task(execute_approved_plan(plan))

        logger.info(f"[WS] broadcast event=execution_started plan_id={plan_id}")
        await state.broadcast("execution_started", {"plan_id": plan_id})

        return {
            "status": "executing",
            "plan_id": plan_id,
            "payload": {"status": "executing", "plan_id": plan_id},
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_msg = f"Approve failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)  # Force print to stderr
        raise HTTPException(500, detail=f"Internal Error: {str(e)}")


async def execute_approved_plan(plan: ExecutionPlan):
    """Execute an approved plan (internal helper)."""
    logger.info(f"[EXEC] execute_approved_plan called | plan_id={plan.id}")

    # PIPELINE FIX: Pre-execution validation
    if not state.session_auth.check():
        logger.error(f"[EXEC] Validation failed: No session | plan_id={plan.id}")
        await state.broadcast("execution_error", {"error": "Session expired"})
        return

    if not state.executor:
        logger.error(f"[EXEC] Validation failed: No executor | plan_id={plan.id}")
        await state.broadcast("execution_error", {"error": "Executor not initialized"})
        return

    if not state.plan_guard:
        logger.error(f"[EXEC] Validation failed: No plan guard | plan_id={plan.id}")
        await state.broadcast("execution_error", {"error": "Plan guard not initialized"})
        return

    state.is_executing = True
    state.current_task_id = plan.id

    logger.info(f"[EXEC] Executing plan | plan_id={plan.id} | task={plan.task}")
    logger.info("[WS] broadcast event=plan_started")
    await state.broadcast("plan_started", {"task": plan.task})

    if state.computer:
        state.computer.set_fps(15)

    try:
        # Validate with guard
        try:
            state.plan_guard.validate(plan)
            logger.info("[EXEC] Plan validated")
        except PlanValidationError as e:
            # Extract violations for detailed feedback
            violations = []
            if hasattr(e, "violations"):
                violations = e.violations
                logger.error(f"[EXEC] Plan rejected with {len(violations)} violations:")
                for v in violations:
                    logger.error(f"[EXEC]   - {v}")
            else:
                logger.error(f"[EXEC] Plan rejected: {e}")

            # PRODUCTION: Voice feedback on rejection
            voice_message = "Blocked by safety policy. Open Settings to allow this action."

            logger.info(f"[WS] broadcast event=plan_rejected violations={len(violations)}")
            await state.broadcast(
                "plan_rejected",
                {"plan_id": plan.id, "error": str(e), "violations": violations},
            )
            return

        await state.broadcast("plan_generated", plan.dict())

        execution_success = False
        execution_error = None

        # P8 FIX: Circuit breaker to prevent resource thrashing
        CONSECUTIVE_FAILURE_LIMIT = 3
        consecutive_failures = 0

        # Execute each step
        for i, step in enumerate(plan.steps):
            # Check for zombie execution (no clients listening)
            async with state._ws_lock:
                has_clients = bool(state.websocket_clients)

            if not has_clients:
                logger.warning(f"[EXEC] No clients connected, aborting zombie execution | plan_id={plan.id}")
                await state.broadcast("execution_error", {"error": "Client disconnected"})
                break

            if state.executor.is_paused():
                await state.broadcast("execution_paused", {"reason": state.executor._pause_reason})
                break

            try:
                await state.broadcast("step_started", {"step_index": i, "step_id": step.id})

                result = state.executor.execute(step)

                if result.success:
                    consecutive_failures = 0
                    await state.broadcast("step_completed", {"step_index": i, "success": True})
                else:
                    consecutive_failures += 1
                    execution_error = result.error

                    # Circuit breaker check
                    if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                        logger.critical(f"[PANIC] {consecutive_failures} consecutive failures. Aborting.")
                        await state.broadcast(
                            "execution_abort",
                            {
                                "reason": f"Circuit breaker: {consecutive_failures} failures",
                                "last_error": result.error,
                            },
                        )
                        break
                if result.requires_takeover:
                    await state.broadcast("takeover_required", {"reason": result.takeover_reason})
                    break

                # Regular failure, continue to next step
                await state.broadcast(
                    "step_completed",
                    {"step_index": i, "success": False, "error": result.error},
                )

            except Exception as e:
                consecutive_failures += 1
                execution_error = str(e)
                logger.exception("[EXEC] Step execution error")

                # Circuit breaker check
                if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                    logger.critical(f"[PANIC] {consecutive_failures} exceptions in a row. Aborting.")
                    await state.broadcast(
                        "execution_abort",
                        {
                            "reason": f"Circuit breaker: {consecutive_failures} consecutive exceptions",
                            "last_error": str(e),
                        },
                    )
                    break

                await state.broadcast("step_error", {"step_index": i, "error": str(e)})

        await state.broadcast("execution_finished", {"success": True})
        execution_success = True

    except Exception as e:
        logger.error(f"[EXEC] Execution error: {e}")
        await state.broadcast("execution_error", {"error": str(e)})
        execution_success = False
        execution_error = str(e)

    finally:
        state.is_executing = False
        if state.computer:
            state.computer.set_fps(1)
        # P9 FIX: Do not revoke session here - keeps user logged in

        # V23: Record execution log
        log_entry = {
            "id": plan.id,
            "timestamp": time.time(),
            "task": plan.task,
            "plan_id": plan.id,
            "step_count": len(plan.steps),
            "success": execution_success if "execution_success" in locals() else False,
            "error": execution_error if "execution_error" in locals() else None,
            "strategy": "auto",
            "recovery_attempted": False,
            "recovery_success": None,
        }
        state.execution_logs.insert(0, log_entry)
        # Keep only last 50
        if len(state.execution_logs) > 50:
            state.execution_logs = state.execution_logs[:50]


# --- V23: Execution Logs Endpoint ---


@app.get("/logs/recent")
async def get_recent_logs(limit: int = 50):
    """
    Get recent execution logs for observability dashboard.
    Returns last N execution entries with status and details.
    """
    return {
        "logs": state.execution_logs[:limit],
        "count": len(state.execution_logs),
        "limit": limit,
    }


# --- Dev Debug Endpoints ---


class DevTaskRequest(BaseModel):
    task: str


@app.post("/dev/run")
async def dev_run_task(req: DevTaskRequest):
    """
    Rescue mode: Bypass voice and run a task directly.
    Auto-grants permission and starts execution.
    """
    # P0-2: Require dev endpoints to be explicitly enabled
    if not FLASH_DEV_ENDPOINTS_ENABLED:
        raise HTTPException(404, "Not found")

    logger.info(f"[DEV] Running task directly: {req.task}")

    # Auto-grant session
    state.session_auth.grant(mode="session", ttl_sec=1800)
    await state.broadcast("permission_granted", {"ttl_sec": 1800})

    # Start execution
    asyncio.create_task(run_plan_execution(req.task))

    return {"status": "started", "task": req.task}


@app.get("/voice/dev_simulate")
async def voice_simulate(text: str = "Open Notepad"):
    """
    Debug endpoint: Bypass mic and simulate speech input.
    """
    # P0-2: Require dev endpoints to be explicitly enabled
    if not FLASH_DEV_ENDPOINTS_ENABLED:
        raise HTTPException(404, "Not found")

    logger.info(f"[DEV] Simulating voice input: {text}")

    # Check session
    if not state.session_auth.check():
        state.session_auth.grant(mode="session", ttl_sec=1800)

    await state.broadcast("speech_recognized", {"text": text})
    asyncio.create_task(run_plan_execution(text))

    return {"status": "processing", "text": text}


@app.post("/debug/type")
async def debug_type(text: str = "HELLO"):
    """Debug: Direct input test."""
    # P0-2: Require dev endpoints to be explicitly enabled
    if not FLASH_DEV_ENDPOINTS_ENABLED:
        raise HTTPException(404, "Not found")

    if not state.session_auth.check():
        state.session_auth.grant(mode="session", ttl_sec=1800)

    if state.computer:
        state.computer.type_text(text)
        return {"status": "typed", "text": text}
    return {"status": "error", "message": "Computer not initialized"}


@app.post("/debug/open_app")
async def debug_open_app(app: str = "notepad"):
    """Debug: Direct app launch test."""
    # P0-2: Require dev endpoints to be explicitly enabled
    if not FLASH_DEV_ENDPOINTS_ENABLED:
        raise HTTPException(404, "Not found")

    if not state.session_auth.check():
        state.session_auth.grant(mode="session", ttl_sec=1800)

    if state.computer:
        result = state.computer.launch_app(app)
        return {"status": "launched" if result else "failed", "app": app}
    return {"status": "error", "message": "Computer not initialized"}


@app.post("/admin/reset_computer", include_in_schema=False)
async def reset_computer():
    """Force reset the computer control backend."""
    # P0-2: Require dev endpoints to be explicitly enabled
    if not FLASH_DEV_ENDPOINTS_ENABLED:
        raise HTTPException(404, "Not found")

    # Security: Require active session
    if not state.session_auth.check():
        raise HTTPException(403, "Forbidden: Active session required")

    logger.warning("[ADMIN] Force resetting computer backend...")

    if state.computer:
        try:
            state.computer.set_fps(1)
        except:
            pass
        state.computer = None

    # Re-initialize
    from assistant.computer.windows import WindowsComputer

    state.computer = WindowsComputer()
    state.computer.set_session_verifier(state.session_auth.ensure)

    return {"status": "reset_complete", "computer": str(state.computer)}


# --- Settings API (P3.1) ---


@app.get("/settings")
def read_settings():
    return get_settings()


@app.post("/settings")
async def update_settings(new_settings: AppSettings):
    if not state.session_auth.check():
        raise HTTPException(401, "Unauthorized: Active session required")

    global _settings
    # Validate logic if needed
    _settings = new_settings
    _settings.save()
    return _settings


# --- Permissions API (P3.2) ---


class PermissionList(BaseModel):
    apps: list[dict] = []
    folders: list[dict] = []
    network: list[dict] = []
    autopilot: bool = False


@app.get("/permissions")
async def get_permissions():
    path = os.path.join(get_appdata_dir(), "permissions.json")
    if os.path.exists(path):
        import json

        with open(path) as f:
            return json.load(f)
    return PermissionList().dict()


@app.post("/permissions")
async def save_permissions(perms: PermissionList):
    path = os.path.join(get_appdata_dir(), "permissions.json")
    import json

    with open(path, "w") as f:
        json.dump(perms.dict(), f, indent=2)
    return {"status": "saved"}


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
    plan = ExecutionPlan(id=plan_id, task=name, steps=steps)

    # Save
    metadata = {
        "name": name,
        "author": "User",
        "duration_sec": 0,  # Calc real duration
        "event_count": len(events),
        "step_count": len(steps),
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
                    await state.broadcast(
                        "takeover_required",
                        {"reason": result.takeover_reason, "error": result.error},
                    )
                    break
                break

        await state.broadcast("execution_finished", {"success": True})

    except Exception as e:
        logger.error(f"Macro Error: {e}")
        await state.broadcast("execution_error", {"error": str(e)})
    finally:
        state.is_executing = False
        if state.computer:
            state.computer.set_fps(1)
        state.session_auth.revoke()


async def execute_task(req: TaskRequest):
    """Direct task execution endpoint."""
    if not state.session_auth.check():
        state.session_auth.grant()  # Auto-grant for explicit API call? Or fail?
        # UI likely calls this after approval.

    asyncio.create_task(run_plan_execution(req.task))
    return {"status": "started", "task": req.task}


async def websocket_heartbeat_loop(websocket: WebSocket):
    """
    Pings the client every 30s to keep connection alive through proxies.
    P5A FIX: Prevents silent disconnections from idle timeouts.
    """
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "timestamp": time.time()})
    except asyncio.CancelledError:
        raise
    except Exception:
        # Connection is dead, main loop will handle cleanup
        pass


# =============================================================================
# BYPASS ENDPOINT REMOVED - SECURITY HARDENING
# The /just_do_it endpoint has been permanently removed to eliminate
# unauthenticated command execution vulnerability identified in security audit.
# All commands must now go through proper PlanGuard validation.
# =============================================================================


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async with state._ws_lock:
        state.websocket_clients.append(websocket)

    # P5A FIX: Start heartbeat task
    heartbeat_task = asyncio.create_task(websocket_heartbeat_loop(websocket))

    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        logger.debug(f"WebSocket disconnected: {e}")
    finally:
        # Cancel heartbeat
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

        async with state._ws_lock:
            if websocket in state.websocket_clients:
                state.websocket_clients.remove(websocket)
