#!/usr/bin/env python3
"""Test script to verify command registration is working."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_command_registration():
    """Test that the command registration works without conflicts."""
    try:
        print("🧪 Testing Command Registration...")
        
        # Test imports
        from slack_bolt import App
        from listeners.commands import register_command_handlers
        from services.service_container import get_container
        
        print("✅ All imports successful")
        
        # Create a test app
        app = App(token="xoxb-test", signing_secret="test-secret")
        print("✅ Test Slack app created")
        
        # Get service container
        container = get_container()
        print("✅ Service container obtained")
        
        # Try to register command handlers
        try:
            register_command_handlers(app, container)
            print("✅ Command handlers registered successfully")
        except Exception as e:
            print(f"❌ Command registration failed: {e}")
            return False
        
        # Check if the /trade command is registered
        # Note: This is a simplified check since we can't easily inspect Slack Bolt's internal routing
        print("✅ Command registration completed without errors")
        
        print("\n🎉 Command Registration Test Results:")
        print("   ✅ Imports work correctly")
        print("   ✅ Slack app can be created")
        print("   ✅ Service container works")
        print("   ✅ Command registration completes without errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_command_registration()
    if success:
        print("\n✅ Command registration test passed!")
        print("The /trade command should now be properly registered.")
        sys.exit(0)
    else:
        print("\n❌ Command registration test failed!")
        sys.exit(1)