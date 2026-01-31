import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from assistant.support.diagnostics import DiagnosticsManager

router = APIRouter(prefix="/support", tags=["Support"])


@router.get("/diagnostics")
async def get_diagnostics():
    """Generate and download a diagnostics bundle."""
    mgr = DiagnosticsManager()
    try:
        zip_path = mgr.create_bundle()
        if not os.path.exists(zip_path):
            raise HTTPException(500, "Failed to generate bundle")

        return FileResponse(
            path=zip_path,
            filename=os.path.basename(zip_path),
            media_type="application/zip",
        )
    except Exception as e:
        raise HTTPException(500, f"Diagnostics error: {str(e)}")
