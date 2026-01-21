"""
Safety configuration API router.
Allows runtime management of trusted apps, domains, and safety policies.
"""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class TrustedAppsUpdate(BaseModel):
    trusted_apps: list[str]
    app_aliases: dict[str, str] = {}


class TrustedDomainsUpdate(BaseModel):
    trusted_domains: list[str]


@router.get("/trusted_apps")
async def get_trusted_apps():
    """Get current trusted apps configuration."""
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_apps.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Safety] Failed to load trusted apps: {e}")
        raise HTTPException(500, f"Failed to load configuration: {e}")


@router.post("/trusted_apps")
async def update_trusted_apps(apps: TrustedAppsUpdate):
    """Update trusted apps configuration (requires active session)."""
    from assistant.main import state  # Import state from main
    
    if not state.session_auth.check():
        raise HTTPException(403, "Forbidden: Active session required")
    
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_apps.json"
        data = {
            "trusted_apps": apps.trusted_apps,
            "app_aliases": apps.app_aliases
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Reload PlanGuard config
        from assistant.safety.plan_guard import load_trusted_apps
        state.plan_guard.trusted_apps, state.plan_guard.app_aliases = load_trusted_apps()
        
        logger.info(f"[Safety] Trusted apps updated: {len(apps.trusted_apps)} apps")
        return {"status": "updated", "count": len(apps.trusted_apps)}
    
    except Exception as e:
        logger.error(f"[Safety] Failed to update trusted apps: {e}")
        raise HTTPException(500, f"Failed to update configuration: {e}")


@router.get("/trusted_domains")
async def get_trusted_domains():
    """Get current trusted domains configuration."""
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_domains.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"[Safety] Failed to load trusted domains: {e}")
        raise HTTPException(500, f"Failed to load configuration: {e}")


@router.post("/trusted_domains")
async def update_trusted_domains(domains: TrustedDomainsUpdate):
    """Update trusted domains configuration (requires active session)."""
    from assistant.main import state
    
    if not state.session_auth.check():
        raise HTTPException(403, "Forbidden: Active session required")
    
    try:
        config_path = Path(__file__).parent.parent / "config" / "trusted_domains.json"
        data = {"trusted_domains": domains.trusted_domains}
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Reload PlanGuard config
        from assistant.safety.plan_guard import load_trusted_domains
        state.plan_guard.trusted_domains = load_trusted_domains()
        
        logger.info(f"[Safety] Trusted domains updated: {len(domains.trusted_domains)} domains")
        return {"status": "updated", "count": len(domains.trusted_domains)}
    
    except Exception as e:
        logger.error(f"[Safety] Failed to update trusted domains: {e}")
        raise HTTPException(500, f"Failed to update configuration: {e}")
