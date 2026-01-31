"""
UI Contracts - Pydantic schemas for agent communication.

These schemas define the contract between:
- Python backend (FastAPI)
- Frontend UI (React/Electron)
- LLM planner output

All data exchanged between components should use these types.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ==================== UI Selector (Unified element reference) ====================


class UISelector(BaseModel):
    """
    Unified selector for UI elements across all strategies.

    This allows converting between:
    - UIA element properties
    - OCR bounding boxes
    - Vision template matches
    - Raw coordinates

    The selector memory caches these to speed up repeated actions.
    """

    strategy: Literal["uia", "ocr", "vision", "coords"]

    # For UIA strategy
    window_title: str | None = None
    control_type: str | None = None  # Button, Edit, Text, etc.
    name: str | None = None
    automation_id: str | None = None

    # For OCR/Vision strategies
    text_content: str | None = None
    template_name: str | None = None  # Reference to saved template image

    # Universal: bounding box (can be derived from any strategy)
    bbox: tuple[int, int, int, int] | None = None  # x1, y1, x2, y2

    # Confidence of the match (0.0 - 1.0)
    confidence: float = 1.0

    # When this selector was last validated
    last_validated_at: float | None = None

    def get_center(self) -> tuple[int, int] | None:
        """Get center point of bounding box."""
        if self.bbox is None:
            return None
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def to_click_coords(self) -> tuple[int, int] | None:
        """Get coordinates suitable for click action."""
        return self.get_center()


# ==================== Verification ====================


class VerifyType(str, Enum):
    """Types of verification checks."""

    WINDOW_TITLE = "window_title"
    TEXT_PRESENT = "text_present"
    TEXT_ABSENT = "text_absent"
    FILE_EXISTS = "file_exists"
    FILE_ABSENT = "file_absent"
    PROCESS_RUNNING = "process_running"
    PROCESS_NOT_RUNNING = "process_not_running"
    URL_CONTAINS = "url_contains"
    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_NOT_VISIBLE = "element_not_visible"
    CUSTOM = "custom"


class VerifySpec(BaseModel):
    """
    Specification for verifying an action succeeded.

    Each action step should have a verification spec that defines
    how to confirm the action had the intended effect.
    """

    type: VerifyType
    value: str  # What to check for (text, title, path, etc.)
    timeout: int = Field(default=5, ge=1, le=60)  # Seconds to wait
    region: tuple[int, int, int, int] | None = None  # Screen region for text search
    negate: bool = False  # If True, verification succeeds when condition is NOT met

    model_config = ConfigDict(use_enum_values=True)


class VerificationResult(BaseModel):
    """Result of a verification check."""

    success: bool
    verify_type: str
    expected: str
    actual: str | None = None
    duration_ms: int
    error: str | None = None


# ==================== Action Steps ====================


class RiskLevel(str, Enum):
    """Risk level of an action."""

    LOW = "low"  # Safe operations (clicking, typing in safe apps)
    MEDIUM = "medium"  # Operations that could have side effects
    HIGH = "high"  # Potentially dangerous (requires explicit approval)


class ActionStep(BaseModel):
    """
    A single step in an execution plan.

    This is the core unit of work that the executor processes.
    """

    id: str = Field(..., description="Unique step identifier")
    tool: str = Field(..., description="Name of the tool/action to execute")
    args: dict = Field(default_factory=dict, description="Arguments for the tool")

    # Execution control
    timeout: int = Field(default=10, ge=1, le=120, description="Timeout in seconds")
    retries: int = Field(default=3, ge=0, le=10, description="Max retry attempts")

    # Risk and verification
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    verify: VerifySpec | None = Field(default=None, description="How to verify success")
    unverifiable: bool = Field(default=False, description="Mark if verification not possible")

    # UI display
    description: str | None = Field(default=None, description="Human-readable description")

    # Selector (cached from previous execution or pre-computed)
    selector: UISelector | None = None

    model_config = ConfigDict(use_enum_values=True)


class StepResult(BaseModel):
    """Result of executing a single step."""

    step_id: str
    success: bool
    strategy_used: str | None = None
    attempts: int = 1
    duration_ms: int
    verification: VerificationResult | None = None
    error: str | None = None
    screenshot_before: str | None = None  # Base64 or path
    screenshot_after: str | None = None
    selector_cached: UISelector | None = None  # For selector memory
    requires_takeover: bool = False
    takeover_reason: str | None = None


# ==================== Execution Plan ====================


class ExecutionPlan(BaseModel):
    """
    Complete execution plan generated by the planner.

    This is what the LLM produces and the executor runs.
    """

    id: str = Field(..., description="Unique plan identifier")
    task: str = Field(..., description="What this plan accomplishes")
    steps: list[ActionStep] = Field(..., description="Ordered list of steps")

    # Metadata
    estimated_time_sec: int = Field(default=0, description="Estimated execution time")
    requires_network: bool = Field(default=False)
    requires_admin: bool = Field(default=False)

    # For display
    summary: str | None = None

    def total_risk_score(self) -> int:
        """Calculate total risk score (for UI display)."""
        scores = {"low": 1, "medium": 2, "high": 5}
        return sum(scores.get(step.risk_level, 1) for step in self.steps)


class ExecutionResult(BaseModel):
    """Result of executing a complete plan."""

    plan_id: str
    success: bool
    steps_completed: int
    steps_total: int
    step_results: list[StepResult]
    total_duration_ms: int
    was_interrupted: bool = False
    interrupt_reason: str | None = None
    requires_takeover: bool = False
    takeover_reason: str | None = None


# ==================== Agent Events ====================


class EventType(str, Enum):
    """Types of events the agent can emit."""

    # Lifecycle
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Execution
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRYING = "step_retrying"

    # Safety
    PERMISSION_REQUIRED = "permission_required"
    TAKEOVER_REQUIRED = "takeover_required"
    TAKEOVER_REQUESTED = "takeover_requested"
    TAKEOVER_COMPLETED = "takeover_completed"
    SENSITIVE_SCREEN_DETECTED = "sensitive_screen_detected"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNSAFE_ENVIRONMENT = "unsafe_environment"

    # Voice
    LISTENING_STARTED = "listening_started"
    LISTENING_STOPPED = "listening_stopped"
    SPEECH_RECOGNIZED = "speech_recognized"
    SPEAKING_STARTED = "speaking_started"
    SPEAKING_FINISHED = "speaking_finished"

    # User actions
    USER_INTERRUPT = "user_interrupt"
    USER_RESUME = "user_resume"
    USER_CANCEL = "user_cancel"


class AgentEvent(BaseModel):
    """
    Event emitted by the agent for UI updates.

    These are sent via WebSocket to the frontend.
    """

    type: EventType
    timestamp: float
    data: dict = Field(default_factory=dict)

    # For step-related events
    step_id: str | None = None
    step_index: int | None = None

    # For error events
    error: str | None = None

    model_config = ConfigDict(use_enum_values=True)


# ==================== Session / Permission ====================


class PermissionRequest(BaseModel):
    """Request for session permission (sent to UI)."""

    apps: list[str] = Field(default_factory=list)
    folders: list[str] = Field(default_factory=list)
    network: bool = False
    suggested_ttl_min: int = 30


class PermissionGrant(BaseModel):
    """Permission grant from user (received from UI)."""

    mode: Literal["session", "once", "denied"]
    apps: list[str] = Field(default_factory=list)
    folders: list[str] = Field(default_factory=list)
    network: bool = False
    ttl_min: int = 30


class SessionStatus(BaseModel):
    """Current session status (for UI display)."""

    allowed: bool
    mode: str
    granted_apps: list[str]
    granted_folders: list[str]
    allow_network: bool
    time_remaining_sec: int
    expires_at_iso: str | None = None
