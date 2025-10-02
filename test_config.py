#!/usr/bin/env python3
"""
Quick configuration test script to verify the foundation setup.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all core modules can be imported."""
    try:
        from config.settings import get_config, ConfigurationManager
        print("✅ Configuration module imported successfully")
        
        from listeners.commands import register_command_handlers
        from listeners.actions import register_action_handlers  
        from listeners.events import register_event_handlers
        print("✅ Listener modules imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_loading():
    """Test configuration loading with minimal environment."""
    try:
        # Set minimal required environment variables
        os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-validation'
        os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-32-characters-long'
        os.environ['FINNHUB_API_KEY'] = 'test-api-key'
        
        from config.settings import get_config
        config = get_config()
        
        print(f"✅ Configuration loaded successfully")
        print(f"   Environment: {config.environment.value}")
        print(f"   App Name: {config.app_name}")
        print(f"   Version: {config.app_version}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_app_creation():
    """Test that the main app can be created."""
    try:
        # Import after setting environment variables
        from app import create_slack_app
        
        app = create_slack_app()
        print("✅ Slack app created successfully")
        
        return True
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Jain Global Slack Trading Bot Foundation")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Configuration Loading", test_config_loading),
        ("App Creation", test_app_creation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"   Test failed!")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All foundation tests passed! Ready for development.")
        return 0
    else:
        print("❌ Some tests failed. Please check the configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())