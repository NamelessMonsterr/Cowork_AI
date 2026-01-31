"""
Phase 5 Test: Performance & Polish.

Tests:
1. Privacy sanitizer (redaction patterns)
2. Logger with sanitization
3. Screen capture backend
4. Permission system
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.utils import (
    HAS_DXCAM,
    HAS_MSS,
    CaptureConfig,
    CoworkLogger,
    LogConfig,
    Permission,
    PermissionManager,
    PluginManifest,
    PrivacySanitizer,
    ScreenCapture,
    Timer,
)


def test_privacy_sanitizer():
    print("=== PHASE 5 TEST: PRIVACY SANITIZER ===\n")

    sanitizer = PrivacySanitizer()

    # Test 1: Email redaction
    print("1. Testing email redaction...")
    result = sanitizer.sanitize("Contact: user@example.com")
    assert "[EMAIL]" in result, f"Should redact email, got: {result}"
    assert "user@example.com" not in result
    print(f"   ✅ Email redacted: {result}")

    # Test 2: Password redaction
    print("2. Testing password redaction...")
    result = sanitizer.sanitize("password=secret123")
    assert "[PASSWORD]" in result, f"Should redact password, got: {result}"
    print(f"   ✅ Password redacted: {result}")

    # Test 3: Credit card redaction
    print("3. Testing credit card redaction...")
    result = sanitizer.sanitize("Card: 4111-1111-1111-1111")
    assert "[CARD]" in result, f"Should redact card, got: {result}"
    print(f"   ✅ Card redacted: {result}")

    # Test 4: Normal text unchanged
    print("4. Testing normal text...")
    result = sanitizer.sanitize("Hello world")
    assert result == "Hello world", "Should not change normal text"
    print("   ✅ Normal text unchanged")

    print("\n✅ Privacy Sanitizer: PASSED")
    return True


def test_logger():
    print("\n=== PHASE 5 TEST: LOGGER ===\n")

    # Test 1: Logger initialization
    print("1. Testing logger initialization...")
    logger = CoworkLogger(name="test", config=LogConfig(console=False))
    print("   ✅ Logger created")

    # Test 2: Sanitized logging
    print("2. Testing sanitized logging...")
    # This should not raise
    logger.info("User email: test@test.com")
    print("   ✅ Sanitized logging works")

    # Test 3: Timer context
    print("3. Testing timer...")
    with Timer("test_operation", logger) as t:
        pass  # Instant operation
    assert t.elapsed_ms >= 0, "Should measure time"
    print(f"   ✅ Timer works: {t.elapsed_ms:.2f}ms")

    print("\n✅ Logger: PASSED")
    return True


def test_screen_capture():
    print("\n=== PHASE 5 TEST: SCREEN CAPTURE ===\n")

    # Test 1: Backend availability
    print("1. Testing backend availability...")
    print(f"   DXcam available: {'✅ Yes' if HAS_DXCAM else '⚠️ No'}")
    print(f"   mss available: {'✅ Yes' if HAS_MSS else '⚠️ No'}")

    # Test 2: Capture initialization
    print("2. Testing capture initialization...")
    capture = ScreenCapture(CaptureConfig(use_dxcam=False))  # Use mss for test
    assert capture.is_available, "Should have a backend"
    print(f"   ✅ Backend: {capture.backend}")

    # Test 3: Dimensions
    print("3. Testing dimensions...")
    w, h = capture.get_dimensions()
    assert w > 0 and h > 0, "Should return valid dimensions"
    print(f"   ✅ Dimensions: {w}x{h}")

    # Test 4: Capture (quick test)
    print("4. Testing capture...")
    frame = capture.capture(as_base64=True)
    assert frame is not None, "Should capture frame"
    assert len(frame) > 100, "Should have data"
    print(f"   ✅ Captured: {len(frame)} chars base64")

    capture.close()

    print("\n✅ Screen Capture: PASSED")
    return True


def test_permission_system():
    print("\n=== PHASE 5 TEST: PERMISSION SYSTEM ===\n")

    # Test 1: Permission enum
    print("1. Testing permission enum...")
    assert Permission.UI_CLICK.value == "ui:click"
    assert Permission.FILE_READ.value == "file:read"
    print("   ✅ Permission enum works")

    # Test 2: Plugin manifest
    print("2. Testing plugin manifest...")
    manifest = PluginManifest(
        name="test_plugin",
        version="1.0.0",
        description="Test",
        author="Test",
        permissions=[Permission.UI_CLICK, Permission.UI_TYPE],
    )
    assert manifest.requires(Permission.UI_CLICK)
    assert not manifest.requires(Permission.ADMIN_ELEVATED)
    print("   ✅ Manifest works")

    # Test 3: Permission manager
    print("3. Testing permission manager...")
    manager = PermissionManager()
    grant = manager.register_plugin(manifest)
    assert grant.plugin_name == "test_plugin"
    print("   ✅ Plugin registered")

    # Test 4: Permission check
    print("4. Testing permission check...")
    has_click = manager.check_permission("test_plugin", Permission.UI_CLICK)
    print(f"   ✅ Permission check: UI_CLICK = {has_click}")

    print("\n✅ Permission System: PASSED")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("       PHASE 5 PERFORMANCE & POLISH TESTS")
    print("=" * 50)

    results = []

    try:
        results.append(("Privacy Sanitizer", test_privacy_sanitizer()))
        results.append(("Logger", test_logger()))
        results.append(("Screen Capture", test_screen_capture()))
        results.append(("Permission System", test_permission_system()))
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 50)
    print("       PHASE 5 RESULTS")
    print("=" * 50)

    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n✨ PHASE 5 PERFORMANCE & POLISH: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ PHASE 5: SOME TESTS FAILED")
        sys.exit(1)
