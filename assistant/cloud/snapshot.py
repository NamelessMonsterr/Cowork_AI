"""
W19.2 Sync Snapshot Model.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import time


class SyncPayload(BaseModel):
    settings: Dict[str, Any] = {}
    permissions: Dict[str, Any] = {}
    plugins: List[str] = []  # List of enabled plugin IDs
    skills: List[str] = []  # List of enabled skill IDs
    preferences: Dict[str, Any] = {}


class Snapshot(BaseModel):
    snapshot_id: str
    user_id: str
    device_id: str
    created_at: float = Field(default_factory=time.time)
    revision: int
    payload: Optional[SyncPayload] = None  # Decrypted
    encrypted_payload: Optional[str] = None  # Base64 Encrypted Blob

    class Config:
        arbitrary_types_allowed = True
