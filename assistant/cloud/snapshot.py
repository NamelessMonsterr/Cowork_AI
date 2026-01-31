"""
W19.2 Sync Snapshot Model.
"""

import time
from typing import Any

from pydantic import BaseModel, Field


class SyncPayload(BaseModel):
    settings: dict[str, Any] = {}
    permissions: dict[str, Any] = {}
    plugins: list[str] = []  # List of enabled plugin IDs
    skills: list[str] = []  # List of enabled skill IDs
    preferences: dict[str, Any] = {}


class Snapshot(BaseModel):
    snapshot_id: str
    user_id: str
    device_id: str
    created_at: float = Field(default_factory=time.time)
    revision: int
    payload: SyncPayload | None = None  # Decrypted
    encrypted_payload: str | None = None  # Base64 Encrypted Blob

    class Config:
        arbitrary_types_allowed = True
