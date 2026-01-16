"""
Failure Taxonomy - Standardized error categories for Benchmarks (W11.6).
"""

from enum import Enum

class FailureCategory(Enum):
    PERMISSION_MISSING = "permission_missing"
    UAC_INTERVENTION = "uac_intervention" 
    SUCCESS_CRITERIA_FAILED = "success_criteria_failed"
    ELEMENT_NOT_FOUND = "element_not_found"
    RECOVERY_FAILED = "recovery_failed"
    TIMEOUT = "timeout"
    CRASH_BACKEND = "crash_backend"
    CRASH_UI = "crash_ui"
    UNKNOWN = "unknown"

def classify_error(error_msg: str) -> FailureCategory:
    """Map raw error string to failure category."""
    e = error_msg.lower()
    if "permission" in e or "access denied" in e:
        return FailureCategory.PERMISSION_MISSING
    if "uac" in e or "elevation" in e:
        return FailureCategory.UAC_INTERVENTION
    if "verifier" in e or "not found" in e or "timeout" in e:
        return FailureCategory.ELEMENT_NOT_FOUND
    if "recovery" in e:
        return FailureCategory.RECOVERY_FAILED
    return FailureCategory.UNKNOWN
