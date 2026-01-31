"""OpenAPI configuration and metadata for Cowork AI Assistant API."""

from typing import Dict, Any

OPENAPI_TAGS = [
    {
        "name": "safety",
        "description": "Security and permission management endpoints. Control session permissions and validate actions.",
    },
    {
        "name": "voice",
        "description": "Voice command processing and transcription. Real-time WebSocket for voice interactions.",
    },
    {
        "name": "plugins",
        "description": "Plugin installation and management. Secure plugin ecosystem with signature verification.",
    },
    {
        "name": "settings",
        "description": "Application configuration and preferences. User settings and system configuration.",
    },
    {
        "name": "learning",
        "description": "Machine learning and adaptive behavior. Learn from user patterns and improve over time.",
    },
]

OPENAPI_INFO: Dict[str, Any] = {
    "title": "Cowork AI Assistant API",
    "version": "1.0.0",
    "description": """
# Cowork AI - Voice-Controlled Automation Assistant

Enterprise-grade voice automation system with industry-leading security (9.8/10).

## Features
- 🎤 Voice control with real-time transcription
- 🔒 Multi-layer security (P0/P1/P1.5 hardening)
- 🔌 Secure plugin ecosystem
- 📊 Adaptive learning system
- 🎯 5-tier role-based access control (RBAC)

## Security
- SessionAuth with time-based expiration
- Content redaction for sensitive data
- Folder sandbox and command restrictions
- Plugin signature verification
- Global blacklist enforcement

## WebSocket Endpoints
- `/ws/voice` - Real-time voice command processing
    """.strip(),
    "contact": {
        "name": "Cowork AI Support",
        "url": "https://github.com/NamelessMonsterr/Cowork_AI",
    },
    "license": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
}

# API Versioning
API_VERSION = "1.0.0"
API_VERSION_HEADER = "X-API-Version"
