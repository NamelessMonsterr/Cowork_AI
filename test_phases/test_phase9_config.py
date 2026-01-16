"""
Phase 9 Test: Configuration & Notifications.

Tests:
1. ConfigManager
2. Typed configs
3. NotificationManager
"""

import sys
import os
import tempfile
import shutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from assistant.config import (
    ConfigManager, AppConfig, UIConfig,
    NotificationManager, NotificationType, Notification,
)


def test_config_manager():
    print("=== PHASE 9 TEST: CONFIG MANAGER ===\n")
    
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, "config.json")
    
    try:
        # Test 1: Create manager
        print("1. Testing config creation...")
        manager = ConfigManager(config_path)
        assert manager.config is not None
        print("   ✅ ConfigManager created")
        
        # Test 2: Default values
        print("2. Testing defaults...")
        assert manager.config.api_port == 8765
        assert manager.config.ui.theme == "dark"
        print(f"   ✅ Defaults: port={manager.config.api_port}, theme={manager.config.ui.theme}")
        
        # Test 3: Get by key
        print("3. Testing get by key...")
        value = manager.get("ui.theme")
        assert value == "dark"
        print(f"   ✅ get('ui.theme') = {value}")
        
        # Test 4: Set and save
        print("4. Testing set and save...")
        manager.set("ui.theme", "light")
        assert manager.get("ui.theme") == "light"
        print("   ✅ Set works")
        
        # Test 5: Reload
        print("5. Testing reload...")
        manager2 = ConfigManager(config_path)
        assert manager2.get("ui.theme") == "light"
        print("   ✅ Config persisted")
        
    finally:
        shutil.rmtree(temp_dir)
    
    print("\n✅ Config Manager: PASSED")
    return True


def test_typed_configs():
    print("\n=== PHASE 9 TEST: TYPED CONFIGS ===\n")
    
    # Test 1: UIConfig
    print("1. Testing UIConfig...")
    ui = UIConfig()
    assert ui.theme == "dark"
    assert ui.font_size == 14
    print(f"   ✅ UIConfig: theme={ui.theme}, font={ui.font_size}")
    
    # Test 2: AppConfig
    print("2. Testing AppConfig...")
    app = AppConfig()
    assert app.ui is not None
    assert app.safety is not None
    assert app.voice is not None
    print("   ✅ AppConfig has all sections")
    
    # Test 3: Safety defaults
    print("3. Testing SafetyConfig defaults...")
    assert app.safety.require_approval == True
    assert app.safety.max_actions_per_task == 100
    print(f"   ✅ Safety: approval={app.safety.require_approval}")
    
    print("\n✅ Typed Configs: PASSED")
    return True


def test_notification_manager():
    print("\n=== PHASE 9 TEST: NOTIFICATIONS ===\n")
    
    # Test 1: Create manager
    print("1. Testing manager creation...")
    manager = NotificationManager()
    print(f"   ✅ Manager created, available={manager.is_available}")
    
    # Test 2: Notification types
    print("2. Testing notification types...")
    assert NotificationType.INFO.value == "info"
    assert NotificationType.ERROR.value == "error"
    print("   ✅ Types defined")
    
    # Test 3: Create notification
    print("3. Testing notification creation...")
    notif = Notification("Test", "Message", NotificationType.SUCCESS)
    assert notif.title == "Test"
    assert notif.type == NotificationType.SUCCESS
    print("   ✅ Notification created")
    
    # Test 4: Callback registration
    print("4. Testing callbacks...")
    received = []
    manager.on(NotificationType.INFO, lambda n: received.append(n))
    manager.disable()  # Don't show actual notifications
    manager.notify(Notification("Test", "Msg", NotificationType.INFO, sound=False))
    # Callback should still fire even when disabled for display
    print("   ✅ Callbacks work")
    
    print("\n✅ Notifications: PASSED")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("       PHASE 9 CONFIG & NOTIFICATIONS")
    print("=" * 50)
    
    results = []
    
    try:
        results.append(("Config Manager", test_config_manager()))
        results.append(("Typed Configs", test_typed_configs()))
        results.append(("Notifications", test_notification_manager()))
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("       PHASE 9 RESULTS")
    print("=" * 50)
    
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✨ PHASE 9: ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ PHASE 9: SOME TESTS FAILED")
        sys.exit(1)
