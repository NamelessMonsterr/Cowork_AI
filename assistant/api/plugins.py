"""
Plugin Management API (W13.1).

Exposes endpoints for listing, enabling, disabling, and installing plugins.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from assistant.plugins.lifecycle import PluginState
from assistant.plugins.installer import PluginInstaller
# We will import 'state' from main inside functions to avoid circular imports?
# Or better, pass dependencies. For now, accessing state via a helper or direct import if safe.
# Circular import main <-> api is risky.
# Best pattern: Define router here, include in main, use dependency injection or generic state accessor.

router = APIRouter(prefix="/plugins", tags=["plugins"])


# Data Models
class PluginDTO(BaseModel):
    id: str
    name: str
    version: str
    publisher: Optional[str]
    description: str
    state: str
    tools: List[str]
    permissions_required: List[str]
    # secrets...


@router.get("/list", response_model=List[PluginDTO])
async def list_plugins():
    from assistant.main import state  # Late import to avoid circular dependency

    if not state.tool_registry:
        return []

    plugins_dto = []

    # Iterate over all registered manifests
    for pid, manifest in state.tool_registry.manifests.items():
        is_enabled = False
        if state.plugin_manager:
            is_enabled = state.plugin_manager.is_enabled(pid)

        # Determine State
        status = PluginState.ENABLED.value if is_enabled else PluginState.DISABLED.value
        # Use TRUSTED_PUBLISHERS check logic here or reuse from Registry?
        # For MVP, just state. (Registry warns on load).

        dto = PluginDTO(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            publisher=manifest.publisher,
            description=manifest.description,
            state=status,
            tools=manifest.tools,
            permissions_required=manifest.permissions_required,
        )
        plugins_dto.append(dto)

    return plugins_dto


@router.post("/enable/{plugin_id}")
async def enable_plugin(plugin_id: str):
    from assistant.main import state

    if state.plugin_manager:
        state.plugin_manager.enable(plugin_id)
        # TODO: Trigger dynamic reload?
    return {"status": "enabled", "id": plugin_id}


@router.post("/disable/{plugin_id}")
async def disable_plugin(plugin_id: str):
    from assistant.main import state

    if state.plugin_manager:
        state.plugin_manager.disable(plugin_id)
        # TODO: Unload tools?
    return {"status": "disabled", "id": plugin_id}


@router.post("/install")
async def install_plugin(file: UploadFile = File(...)):
    """Install plugin from .zip file."""
    installer = PluginInstaller()
    try:
        content = await file.read()
        plugin_id, status = installer.install_zip(content)

        # Trigger reload (W13 dynamic load)
        from assistant.main import state

        if state.plugin_loader:
            # Basic reload logic: Just run load_all again?
            # It acts as refresh for new folders.
            state.plugin_loader.load_all()

        return {"id": plugin_id, "status": status}
    except Exception as e:
        raise HTTPException(400, f"Install failed: {str(e)}")


# --- W13.3 Trust API ---


@router.get("/trusted_publishers")
async def list_trusted_publishers():
    from assistant.main import state

    if not state.plugin_manager:
        return []
    return list(state.plugin_manager.trusted_publishers)


@router.post("/trust_publisher")
async def trust_publisher(publisher: str):
    from assistant.main import state

    if state.plugin_manager:
        state.plugin_manager.trust_publisher(publisher)
    return {"status": "trusted", "publisher": publisher}


# --- W13.4 Permissions API ---


class PermissionGrant(BaseModel):
    plugin_id: str
    scopes: List[str]


@router.get("/permissions/{plugin_id}")
async def get_permissions(plugin_id: str):
    from assistant.main import state

    if not state.permission_manager:
        return {}

    # In full impl, we'd look up required scopes from manifest
    # For now returning granted
    granted = list(state.permission_manager.grants.get(plugin_id, []))
    return {"plugin_id": plugin_id, "granted": granted}


@router.post("/permissions/grant")
async def grant_permissions(grant: PermissionGrant):
    from assistant.main import state

    if state.permission_manager:
        state.permission_manager.grant(grant.plugin_id, grant.scopes)
    return {"status": "granted"}


# --- W13.5 Secrets API ---


class SecretSet(BaseModel):
    plugin_id: str
    key: str
    value: str


@router.post("/secrets/set")
async def set_secret(s: SecretSet):
    from assistant.main import state

    if state.plugin_secrets:
        state.plugin_secrets.set(s.plugin_id, s.key, s.value)
    return {"status": "set"}


# --- W13.6 Audit API ---


@router.get("/audit/recent")
async def get_audit_logs(limit: int = 50):
    import os
    import json

    log_path = os.path.join("logs", "plugin_audit.jsonl")
    logs = []

    if os.path.exists(log_path):
        try:
            # Read last N lines (inefficient but OK for MVP)
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass
        except Exception:
            pass

    return logs[::-1]  # Newest first
