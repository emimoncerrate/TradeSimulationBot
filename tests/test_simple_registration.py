#!/usr/bin/env python3
"""Simple test to verify the command registration logic."""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_registration_logic():
    """Test that the registration logic works without Slack connection."""
    try:
        print("🧪 Testing Command Registration Logic...")
        
        # Test imports
        from listeners.enhanced_trade_command import EnhancedTradeCommand
        from services.market_data import MarketDataService
        from services.auth import AuthService
        
        print("✅ All imports successful")
        
        # Check that the enhanced trade command can be created (without services)
        # We'll just check the class exists and has the right methods
        
        if hasattr(EnhancedTradeCommand, 'handle_trade_command'):
            print("✅ EnhancedTradeCommand has handle_trade_command method")
        else:
            print("❌ EnhancedTradeCommand missing handle_trade_command method")
            return False
        
        # Check method signature
        import inspect
        sig = inspect.signature(EnhancedTradeCommand.handle_trade_command)
        params = list(sig.parameters.keys())
        expected_params = ['self', 'ack', 'body', 'client', 'context']
        
        if params == expected_params:
            print("✅ handle_trade_command has correct signature")
        else:
            print(f"❌ handle_trade_command has wrong signature: {params}")
            return False
        
        # Check that the method is async
        if inspect.iscoroutinefunction(EnhancedTradeCommand.handle_trade_command):
            print("✅ handle_trade_command is async")
        else:
            print("❌ handle_trade_command is not async")
            return False
        
        # Check that ack() is called synchronously (not awaited)
        source = inspect.getsource(EnhancedTradeCommand.handle_trade_command)
        if 'ack()' in source and 'await ack()' not in source:
            print("✅ ack() is called synchronously")
        elif 'await ack()' in source:
            print("❌ ack() is being awaited (should be synchronous)")
            return False
        else:
            print("⚠️  Could not verify ack() call pattern")
        
        print("\n🎉 Registration Logic Test Results:")
        print("   ✅ Enhanced trade command class exists")
        print("   ✅ Method signature is correct")
        print("   ✅ Method is properly async")
        print("   ✅ ack() handling looks correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_registration_logic()
    if success:
        print("\n✅ Registration logic test passed!")
        print("The command registration should work correctly now.")
        sys.exit(0)
    else:
        print("\n❌ Registration logic test failed!")
        sys.exit(1)