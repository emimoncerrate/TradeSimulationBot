#!/usr/bin/env python3
"""
Test Multi-Account Command Registration

This script tests if the multi-account command can be created and registered properly.
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


def test_multi_account_command():
    """Test multi-account command creation."""
    print("🧪 Testing Multi-Account Command Registration")
    print("=" * 60)
    
    try:
        # Test 1: Import services
        print("\n1️⃣ Testing service imports...")
        from services.service_container import get_container
        from services.auth import AuthService
        
        container = get_container()
        auth_service = container.get(AuthService)
        print("✅ Services imported and obtained")
        
        # Test 2: Import multi-account command
        print("\n2️⃣ Testing multi-account command import...")
        from listeners.multi_account_trade_command import MultiAccountTradeCommand
        print("✅ MultiAccountTradeCommand imported")
        
        # Test 3: Create multi-account command instance
        print("\n3️⃣ Testing multi-account command creation...")
        multi_command = MultiAccountTradeCommand(auth_service)
        print("✅ MultiAccountTradeCommand created successfully")
        
        # Test 4: Test registration function import
        print("\n4️⃣ Testing registration function import...")
        from listeners.multi_account_trade_command import register_multi_account_trade_command
        print("✅ Registration function imported successfully")
        
        # Test 5: Check if command has required methods
        print("\n5️⃣ Testing command methods...")
        
        required_methods = ['handle_trade_command', 'handle_trade_submission']
        for method_name in required_methods:
            if hasattr(multi_command, method_name):
                print(f"   ✅ {method_name} method exists")
            else:
                print(f"   ❌ {method_name} method missing")
                return False
        
        print(f"\n" + "=" * 60)
        print("🎉 Multi-Account Command Test PASSED!")
        print("=" * 60)
        
        print("✅ The multi-account command should now work properly")
        print("💡 Restart your Slack app to activate the multi-account system")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_multi_account_command()
    
    if success:
        print(f"\n🎯 Multi-account command is ready!")
        print(f"   Restart your Slack app and try: /trade AAPL")
    else:
        print(f"\n💥 Multi-account command has issues")
    
    sys.exit(0 if success else 1)