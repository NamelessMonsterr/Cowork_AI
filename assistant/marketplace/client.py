"""
Marketplace Client (W16.2).
Handles registry fetching and plugin downloads.
"""

import os
import logging
import aiohttp
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger("Marketplace")


class MarketplacePlugin(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    publisher_key: Optional[str] = None
    download_url: str
    icon_url: Optional[str] = None
    verified: bool = False


# Mock Registry for Beta
MOCK_REGISTRY = {
    "plugins": [
        {
            "id": "com.cowork.weather",
            "name": "Weather Pro",
            "version": "1.0.0",
            "description": "Advanced weather forecasts via OpenMeteo.",
            "author": "Cowork Team",
            "verified": True,
            "download_url": "http://localhost:8000/plugins/weather.cowork-plugin",
        },
        {
            "id": "com.cowork.spotify",
            "name": "Spotify Control",
            "version": "2.1.0",
            "description": "Control music playback.",
            "author": "Community",
            "verified": False,
            "download_url": "http://localhost:8000/plugins/spotify.cowork-plugin",
        },
    ]
}


class MarketplaceClient:
    def __init__(self, registry_url: str = None):
        self.registry_url = registry_url or os.getenv(
            "MARKETPLACE_URL", "https://api.cowork.ai/registry.json"
        )
        self.cache: List[MarketplacePlugin] = []

    async def fetch_registry(self) -> List[MarketplacePlugin]:
        """Fetch the plugin registry."""
        # For W16 Beta, return Stub if URL fails
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.registry_url, timeout=2) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.cache = [
                            MarketplacePlugin(**p) for p in data.get("plugins", [])
                        ]
                        return self.cache
        except Exception as e:
            logger.warning(
                f"Failed to fetch registry from {self.registry_url}: {e}. Using Mock."
            )

        # Fallback Mock
        self.cache = [MarketplacePlugin(**p) for p in MOCK_REGISTRY["plugins"]]
        return self.cache

    async def get_plugin_details(self, plugin_id: str) -> Optional[MarketplacePlugin]:
        if not self.cache:
            await self.fetch_registry()

        for p in self.cache:
            if p.id == plugin_id:
                return p
        return None

    async def download_plugin(self, url: str, dest_path: str):
        """Download plugin package."""
        # Check safe URL schems
        if not url.startswith("http"):
            raise ValueError("Invalid URL scheme")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise IOError(f"Download failed: {resp.status}")

                with open(dest_path, "wb") as f:
                    while True:
                        chunk = await resp.content.read(1024 * 64)
                        if not chunk:
                            break
                        f.write(chunk)
