#!/usr/bin/env python3
"""
Debug Trade Command Registration

This script helps debug which trade command is actually being used.
"""

import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_command_registration():
    """Debug which command is registered."""
    print("🔍 Debugging Trade Command Registration")
    print("=" * 60)
    
    try:
        # Simulate the exact same logic as in commands.py
        from services.service_container import get_container
        from services.auth import AuthService
        
        container = get_container()
        auth_service = container.get(AuthService)
        
        print("✅ Services obtained")
        
        # Check multi-account system availability (same logic as commands.py)
        multi_account_available = False
        try:
            # Check if multi-account services can be imported
            from services.multi_alpaca_service import MultiAlpacaService
            from services.user_account_manager import UserAccountManager
            
            # Try to get the services from container
            try:
                multi_alpaca = container.get(MultiAlpacaService)
                user_manager = container.get(UserAccountManager)
                
                # Check if the multi-alpaca service is available
                if multi_alpaca.is_available():
                    multi_account_available = True
                    print("✅ Multi-account system detected and available")
                else:
                    print("📊 Multi-account services loaded but no accounts available")
                    
            except Exception as service_error:
                print(f"📋 Multi-account services not in container: {service_error}")
                
        except ImportError as import_error:
            print(f"📦 Multi-account modules not available: {import_error}")
        except Exception as e:
            print(f"❌ Error checking multi-account system: {e}")
        
        print(f"\n🎯 Multi-account available: {multi_account_available}")
        
        if multi_account_available:
            print("\n🚀 Testing multi-account command registration...")
            
            try:
                # Test the registration process
                from listeners.multi_account_trade_command import register_multi_account_trade_command
                from commands.account_management import register_account_management_commands
                
                print("✅ Multi-account modules imported successfully")
                
                # Create a mock Slack app to test registration
                class MockApp:
                    def __init__(self):
                        self.commands = {}
                        self.views = {}
                    
                    def command(self, command_name):
                        def decorator(func):
                            self.commands[command_name] = func
                            print(f"   📝 Registered command: {command_name}")
                            return func
                        return decorator
                    
                    def view(self, view_id):
                        def decorator(func):
                            self.views[view_id] = func
                            print(f"   📋 Registered view: {view_id}")
                            return func
                        return decorator
                
                mock_app = MockApp()
                
                # Test multi-account registration
                print("\n   Testing multi-account command registration...")
                multi_command = register_multi_account_trade_command(mock_app, auth_service)
                print(f"   ✅ Multi-account command created: {type(multi_command).__name__}")
                
                # Test account management registration
                print("\n   Testing account management registration...")
                register_account_management_commands(mock_app)
                print("   ✅ Account management commands registered")
                
                print(f"\n📊 Registration Summary:")
                print(f"   Commands registered: {list(mock_app.commands.keys())}")
                print(f"   Views registered: {list(mock_app.views.keys())}")
                
                if "/trade" in mock_app.commands:
                    print("   ✅ /trade command is registered with multi-account handler")
                else:
                    print("   ❌ /trade command NOT registered")
                
                if "trade_form_submission" in mock_app.views:
                    print("   ✅ trade_form_submission view is registered")
                else:
                    print("   ❌ trade_form_submission view NOT registered")
                
                return True
                
            except Exception as e:
                print(f"❌ Multi-account registration failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("📝 Would register single-account command")
            return False
        
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_command_registration()
    
    if success:
        print(f"\n🎯 Multi-account command should be working!")
        print(f"   If you're still seeing the old form, there might be a Slack caching issue.")
        print(f"   Try: /trade aapl (with a different symbol)")
    else:
        print(f"\n💥 Multi-account command registration has issues")
    
    sys.exit(0 if success else 1)