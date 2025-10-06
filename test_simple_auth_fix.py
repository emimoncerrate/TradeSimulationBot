#!/usr/bin/env python3
"""Simple test to verify the authentication method fix."""

import sys
import os
import inspect

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_auth_method_fix():
    """Test that the enhanced trade command uses the correct authentication method."""
    try:
        print("🧪 Testing Enhanced Trade Command Authentication Method Fix...")
        
        # Test imports
        from listeners.enhanced_trade_command import EnhancedTradeCommand
        from services.auth import AuthService
        
        print("✅ All imports successful")
        
        # Check that AuthService has the correct method
        if hasattr(AuthService, 'authenticate_slack_user'):
            print("✅ AuthService has authenticate_slack_user method")
        else:
            print("❌ AuthService missing authenticate_slack_user method")
            return False
        
        # Check that AuthService does NOT have the old method
        if hasattr(AuthService, 'authenticate_user'):
            print("⚠️  AuthService still has old authenticate_user method (this is okay)")
        else:
            print("✅ AuthService doesn't have old authenticate_user method")
        
        # Check the enhanced command source code
        source = inspect.getsource(EnhancedTradeCommand._authenticate_user)
        if 'authenticate_slack_user' in source:
            print("✅ Enhanced command uses authenticate_slack_user method")
        else:
            print("❌ Enhanced command still using wrong authentication method")
            print("Source code:")
            print(source)
            return False
        
        if 'authenticate_user(' in source and 'authenticate_slack_user' not in source:
            print("❌ Enhanced command still using old authenticate_user method")
            return False
        
        print("\n🎉 Authentication Method Fix Test Results:")
        print("   ✅ Enhanced trade command imports successfully")
        print("   ✅ AuthService has correct authenticate_slack_user method")
        print("   ✅ Enhanced command calls authenticate_slack_user")
        print("   ✅ Authentication method fix is working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auth_method_fix()
    if success:
        print("\n✅ All tests passed! The authentication method fix is working correctly.")
        print("The '/trade' command should now work without the 'authenticate_user' error.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed! There are still issues to resolve.")
        sys.exit(1)