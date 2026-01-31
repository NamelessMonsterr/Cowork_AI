"""
Sensitive Screen Detector.

Detects screens that require human attention:
- Login pages (password fields)
- CAPTCHA prompts
- OTP/2FA verification
- Admin/UAC prompts
- Payment/Credit card forms

When detected, the agent should pause and request human takeover.
"""

import re
from typing import List
from dataclasses import dataclass
from enum import Enum


class SensitiveType(str, Enum):
    """Types of sensitive screens."""

    LOGIN = "login"
    CAPTCHA = "captcha"
    OTP = "otp"
    PAYMENT = "payment"
    ADMIN = "admin"
    UNKNOWN = "unknown"


@dataclass
class SensitiveDetection:
    """Result of sensitive screen detection."""

    detected: bool
    type: SensitiveType
    confidence: float
    reason: str
    recommended_action: str


class SensitiveDetector:
    """
    Detects sensitive UI elements that require human intervention.

    Uses multiple signals:
    - Window titles
    - OCR text patterns
    - UI element types (password fields)
    - Process names
    """

    # Patterns for different sensitive types
    LOGIN_PATTERNS = [
        r"sign.?in",
        r"log.?in",
        r"password",
        r"username",
        r"email.*password",
        r"enter.*credentials",
        r"authentication",
    ]

    CAPTCHA_PATTERNS = [
        r"captcha",
        r"verify.*human",
        r"i.*m.*not.*robot",
        r"recaptcha",
        r"hcaptcha",
        r"security.*check",
        r"prove.*human",
    ]

    OTP_PATTERNS = [
        r"verification.*code",
        r"otp",
        r"one.*time.*password",
        r"2fa",
        r"two.*factor",
        r"authenticator",
        r"6.*digit.*code",
        r"enter.*code.*sent",
    ]

    PAYMENT_PATTERNS = [
        r"credit.*card",
        r"debit.*card",
        r"card.*number",
        r"cvv",
        r"expir.*date",
        r"billing.*address",
        r"payment.*method",
        r"checkout",
    ]

    ADMIN_PATTERNS = [
        r"administrator",
        r"elevated.*permissions",
        r"run.*as.*admin",
        r"user.*account.*control",
        r"uac",
    ]

    def __init__(self):
        """Initialize detector with compiled patterns."""
        self._patterns = {
            SensitiveType.LOGIN: [
                re.compile(p, re.IGNORECASE) for p in self.LOGIN_PATTERNS
            ],
            SensitiveType.CAPTCHA: [
                re.compile(p, re.IGNORECASE) for p in self.CAPTCHA_PATTERNS
            ],
            SensitiveType.OTP: [
                re.compile(p, re.IGNORECASE) for p in self.OTP_PATTERNS
            ],
            SensitiveType.PAYMENT: [
                re.compile(p, re.IGNORECASE) for p in self.PAYMENT_PATTERNS
            ],
            SensitiveType.ADMIN: [
                re.compile(p, re.IGNORECASE) for p in self.ADMIN_PATTERNS
            ],
        }

        # Actions for each type
        self._actions = {
            SensitiveType.LOGIN: "Request human to enter credentials",
            SensitiveType.CAPTCHA: "Request human to solve CAPTCHA",
            SensitiveType.OTP: "Request human to enter verification code",
            SensitiveType.PAYMENT: "Request human to review payment details",
            SensitiveType.ADMIN: "Request human to approve admin action",
        }

    def detect_from_text(self, text: str) -> SensitiveDetection:
        """
        Detect sensitive content from OCR/screen text.

        Args:
            text: Text extracted from screen

        Returns:
            SensitiveDetection with results
        """
        text_lower = text.lower()

        for sens_type, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    return SensitiveDetection(
                        detected=True,
                        type=sens_type,
                        confidence=0.8,
                        reason=f"Matched pattern: {pattern.pattern}",
                        recommended_action=self._actions[sens_type],
                    )

        return SensitiveDetection(
            detected=False,
            type=SensitiveType.UNKNOWN,
            confidence=0.0,
            reason="No sensitive patterns detected",
            recommended_action="Continue automation",
        )

    def detect_from_window(
        self, title: str, process_name: str = ""
    ) -> SensitiveDetection:
        """
        Detect sensitive content from window title and process.

        Args:
            title: Window title
            process_name: Process executable name

        Returns:
            SensitiveDetection with results
        """
        combined = f"{title} {process_name}"
        return self.detect_from_text(combined)

    def detect_from_elements(self, elements: List[dict]) -> SensitiveDetection:
        """
        Detect sensitive content from UI elements.

        Args:
            elements: List of UI element info dicts

        Returns:
            SensitiveDetection with results
        """
        for element in elements:
            control_type = element.get("control_type", "").lower()
            name = element.get("name", "").lower()
            automation_id = element.get("automation_id", "").lower()

            # Password fields are always sensitive
            if control_type == "edit" and "password" in (name + automation_id):
                return SensitiveDetection(
                    detected=True,
                    type=SensitiveType.LOGIN,
                    confidence=0.95,
                    reason="Password input field detected",
                    recommended_action=self._actions[SensitiveType.LOGIN],
                )

            # Check names for patterns
            combined = f"{name} {automation_id}"
            detection = self.detect_from_text(combined)
            if detection.detected:
                return detection

        return SensitiveDetection(
            detected=False,
            type=SensitiveType.UNKNOWN,
            confidence=0.0,
            reason="No sensitive elements detected",
            recommended_action="Continue automation",
        )

    def check_screen(
        self,
        window_title: str = "",
        screen_text: str = "",
        elements: List[dict] = None,
    ) -> SensitiveDetection:
        """
        Comprehensive check using all available signals.

        Args:
            window_title: Current window title
            screen_text: OCR text from screen
            elements: UI elements list

        Returns:
            SensitiveDetection with highest confidence result
        """
        detections = []

        if window_title:
            detections.append(self.detect_from_window(window_title))

        if screen_text:
            detections.append(self.detect_from_text(screen_text))

        if elements:
            detections.append(self.detect_from_elements(elements))

        # Return highest confidence detection
        detected = [d for d in detections if d.detected]
        if detected:
            return max(detected, key=lambda d: d.confidence)

        return SensitiveDetection(
            detected=False,
            type=SensitiveType.UNKNOWN,
            confidence=0.0,
            reason="Screen appears safe for automation",
            recommended_action="Continue automation",
        )
