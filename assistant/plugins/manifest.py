"""
Plugin Manifest - Configuration schema for plugins (W12.1).

Maps to plugin.json files.
"""

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    id: str = Field(..., description="Unique plugin ID (e.g. 'cowork.slack')")
    name: str
    version: str
    author: str | None = "Unknown"
    publisher: str | None = None  # W12 Trust: Trusted entity name
    signature: str | None = None  # W12 Trust: Hash/Signature
    description: str
    entrypoint: str = Field(..., description="Python module path (e.g. 'slack_plugin:SlackPlugin')")
    permissions_required: list[str] = Field(default_factory=list, description="List of required permissions")
    tools: list[str] = Field(default_factory=list, description="List of tool names provided")
