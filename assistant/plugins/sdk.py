"""
Tool SDK - Core interfaces for CoworkAI Plugins (W12.1).

Defines the contract for creating tools and plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """Defines the interface and metadata for a tool."""

    name: str = Field(
        ..., description="Unique name of the tool (e.g., 'send_slack_message')"
    )
    description: str = Field(..., description="Description for the LLM Planner")
    input_schema: Dict[str, Any] = Field(
        ..., description="JSON Schema for input arguments"
    )
    output_schema: Optional[Dict[str, Any]] = None
    risk_level: str = Field("low", description="Risk level (low, medium, high)")
    requires_network: bool = False
    requires_filesystem: bool = False
    requires_secrets: List[str] = Field(
        default_factory=list, description="List of secret keys required"
    )


class ToolContext(BaseModel):
    """Context passed to tool execution."""

    session_id: str
    user_id: Optional[str] = None
    active_window: Optional[str] = None


class Tool(ABC):
    """Abstract base class for all tools."""

    def __init__(self, spec: ToolSpec):
        self.spec = spec

    @abstractmethod
    async def run(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        """Execute the tool logic."""
        pass


class Plugin(ABC):
    """Abstract base class for a plugin."""

    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return list of tools provided by this plugin."""
        pass
