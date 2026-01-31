"""
Team API (W17.2/W17.3).
Expose peer info and delegation endpoints.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("TeamAPI")
router = APIRouter(prefix="/team", tags=["Team"])

# We need access to the state's discovery instance
# Ideally dependency injection, but state is global in main.py
# We'll attach it to router state or access global state via import (careful of circular deps)
# Safe Pattern: Pass discovery instance to router logic or assume connected state


class DelegateRequest(BaseModel):
    task: str
    context: dict[str, Any] = {}
    target_peer_id: str | None = None


@router.get("/peers")
async def list_peers():
    # Helper to access state?
    # For now, we rely on main.py to mount this and init discovery.
    # To access state, we might need a getter provided at init.
    # Or import state inside function (runtime import) to avoid circular dep.
    from assistant.main import state

    if not state.team_discovery:
        return {"status": "disabled", "peers": []}

    return {"peers": [p.dict() for p in state.team_discovery.get_peers()]}


@router.post("/delegate")
async def receive_delegation(req: DelegateRequest):
    """
    Receive a task delegated from another agent.
    """
    logger.info(f"Received Delegated Task: {req.task} from {req.target_peer_id or 'unknown'}")

    # Ideally: Validate auth/trust
    # Then: Queue for execution

    # Check if we accept delegation? W17.3 Policy
    # For MVP: Accept

    # Security Harden: Disable auto-execution by default (RCE Risk)
    # import asyncio
    # asyncio.create_task(run_plan_execution(f"Delegated: {req.task}"))

    logger.info(f"Delegation received (Dry Run): {req.task}. Auto-execution disabled for safety.")
    return {"status": "accepted", "message": "Task logged (Auto-execution disabled)."}

    return {"status": "accepted", "message": "Task received and queued."}


@router.post("/send_task")
async def send_task(peer_id: str, task: str):
    """
    Send a task to a peer.
    """
    from assistant.main import state

    if not state.team_discovery:
        raise HTTPException(503, "Team mode disabled")

    peers = state.team_discovery.get_peers()
    target = next((p for p in peers if p.id == peer_id), None)

    if not target:
        raise HTTPException(404, "Peer not found")

    # Send HTTP POST to peer
    import aiohttp

    url = f"http://{target.ip}:{target.port}/team/delegate"

    try:
        async with aiohttp.ClientSession() as session:
            payload = {"task": task, "target_peer_id": state.team_discovery.agent_id}
            async with session.post(url, json=payload, timeout=5) as resp:
                if resp.status == 200:
                    return {"status": "sent", "peer": target.name}
                else:
                    raise HTTPException(502, f"Peer rejected: {resp.status}")
    except Exception as e:
        logger.error(f"Delegation failed: {e}")
        raise HTTPException(502, f"Failed to reach peer: {e}")
