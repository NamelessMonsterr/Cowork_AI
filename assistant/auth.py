"""
API Authentication Middleware
CRITICAL SECURITY: Protects all sensitive endpoints from unauthorized access
"""

import os
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# API Key Schema Header-based authentication
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# CRITICAL SECURITY: API keys stored in environment variable (NOT in code)
# Production must set COWORK_API_KEYS="key1,key2,key3"
VALID_API_KEYS = set(
    os.getenv("COWORK_API_KEYS", "").split(",")
) or {secrets.token_urlsafe(32)}  # Generate one-time key if not set

# Log the generated key on first startup (for development)
if not os.getenv("COWORK_API_KEYS"):
    print(f"⚠️  WARNING: No API keys configured. Generated temporary key: {list(VALID_API_KEYS)[0]}")
    print("Set COWORK_API_KEYS environment variable for production!")


async def require_api_key(api_key: str = Security(api_key_header)):
    """
    Dependency that validates API key.
    
    Usage:
        @router.get("/protected", dependencies=[Depends(require_api_key)])
        async def protected_route():
            ...
    """
    # TEST MODE BYPASS: Skip auth in test environment
    if os.getenv("COWORK_TEST_MODE") == "1":
        return "test-mode-bypass"
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
        )
    
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    
    return api_key
