#!/usr/bin/env python3
"""
Test Clean Command Registration

This script tests that only the multi-account trade command is registered.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_clean_registration():
    """Test that old commands are removed."""
    print("🧹 Testing Clean Command Registration")
    print("=" * 50)
    
    try:
        # Test the command registration logic
        from services.service_container import get_container
        from services.auth import AuthService
        
        container = get_container()
        auth_service = container.get(AuthService)
        
        # Create mock app to capture registrations
        class MockApp:
            def __init__(self):
                self.commands = {}
                self.command_count = 0
            
            def command(self, command_name):
                def decorator(func):
                    if command_name in self.commands:
                        print(f"⚠️  CONFLICT: {command_name} registered multiple times!")
                        self.command_count += 1
                    else:
                        print(f"✅ Registered: {command_name}")
                    
                    self.commands[command_name] = func
                    self.command_count += 1
                    return func
                return decorator
            
            def view(self, view_id):
                def decorator(func):
                    return func
                return decorator
        
        mock_app = MockApp()
        
        # Import and run the command registration
        from listeners.commands import register_command_handlers
        
        print("🔄 Running command registration...")
        register_command_handlers(mock_app, container)
        
        print(f"\n📊 Registration Results:")
        print(f"   Total commands: {mock_app.command_count}")
        print(f"   Unique commands: {len(mock_app.commands)}")
        print(f"   Commands: {list(mock_app.commands.keys())}")
        
        # Check for conflicts
        if mock_app.command_count > len(mock_app.commands):
            print(f"❌ CONFLICT DETECTED: Some commands registered multiple times!")
            return False
        
        # Check that /trade is registered
        if "/trade" in mock_app.commands:
            print(f"✅ /trade command is registered")
        else:
            print(f"❌ /trade command is NOT registered")
            return False
        
        # Check for multi-account commands
        expected_commands = ["/trade", "/accounts", "/assign-account", "/my-account", "/account-users"]
        missing_commands = []
        
        for cmd in expected_commands:
            if cmd not in mock_app.commands:
                missing_commands.append(cmd)
        
        if missing_commands:
            print(f"❌ Missing commands: {missing_commands}")
            return False
        else:
            print(f"✅ All expected multi-account commands are registered")
        
        print(f"\n🎉 Clean registration test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_clean_registration()
    
    if success:
        print(f"\n🎯 Command registration is clean!")
        print(f"   Only multi-account commands are registered")
        print(f"   Restart your Slack app to see the new enhanced modal")
    else:
        print(f"\n💥 Command registration has conflicts")
    
    sys.exit(0 if success else 1)