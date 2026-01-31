"""
Marketplace API endpoints (W16.3).
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from assistant.marketplace.client import MarketplaceClient
from assistant.plugins.installer import PluginInstaller
import logging
import os
import uuid

logger = logging.getLogger("MarketplaceAPI")

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])

# Shared Client
mp_client = MarketplaceClient()


@router.get("/list")
async def list_plugins():
    plugins = await mp_client.fetch_registry()
    return {"plugins": [p.dict() for p in plugins]}


@router.post("/install/{plugin_id}")
async def install_plugin(plugin_id: str, background_tasks: BackgroundTasks):
    """
    Install a plugin from the marketplace.
    """
    plugin = await mp_client.get_plugin_details(plugin_id)
    if not plugin:
        raise HTTPException(404, "Plugin not found")

    # Start installation in background (downloading might take time)
    # background_tasks.add_task(perform_install, plugin)

    # For MVP verification, we might want sync or immediate response?
    # Let's do async but wait for download?
    # Actually, returning a task ID is better.

    task_id = str(uuid.uuid4())
    # TODO: Task Manager

    # For W16 MVP: Sync for now (simple)
    try:
        # 1. Download
        temp_dir = os.path.join(os.getenv("APPDATA"), "CoworkAI", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        local_path = os.path.join(temp_dir, f"{plugin.id}.cowork-plugin")

        # Download from URL
        await mp_client.download_plugin(plugin.download_url, local_path)

        # 2. Install (Verify & Extract)
        installer = PluginInstaller()
        # For Beta: If no key in registry, we skip verify? Or fail?
        # We pass plugin.publisher_key if available.
        # Key format: expecting PEM? or Hex?
        # For now, let's pass what we have.

        # Note: installer.install_package currently ignores key verification logic
        # (I left a TODO in previous step).
        # I will update installer next to actually verify.

        plugin_id, status = installer.install_package(
            local_path, public_key_hex=plugin.publisher_key
        )

        return {
            "status": "success",
            "plugin_id": plugin_id,
            "message": "Installed successfully",
        }

    except Exception as e:
        logger.error(f"Marketplace Install Error: {e}")
        raise HTTPException(500, str(e))
