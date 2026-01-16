"""
Events - WebSocket Event Types (including W9 Recovery).
"""
# This file is usually auto-generated or static, but for W9 we modify schemas/events logic.
# Actually I need to check where events are defined. Usually just strings in main.py broadcast.
# But keeping a constants file is good practice.

RECOVERY_STARTED = "recovery_started"
RECOVERY_ATTEMPT = "recovery_attempt"
RECOVERY_SUCCEEDED = "recovery_succeeded"
RECOVERY_FAILED = "recovery_failed"
TAKEOVER_REQUIRED = "takeover_required"
