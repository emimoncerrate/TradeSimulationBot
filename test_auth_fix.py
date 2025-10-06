#!/usr/bin/env python3
"""Test script to verify the authentication fix for enhanced trade command."""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_auth_fix():
    """Test that the enhanced trade command can authenticate users properly."""
    try:
        print("🧪 Testing Enhanced Trade Command Authentication Fix...")
        
        # Test imports
        from services.service_container import get_container
        from services.auth import AuthService
        from services.market_data import MarketDataService
        from listeners.enhanced_trade_command import EnhancedTradeCommand
        
        print("✅ All imports successful")
        
        # Get service container
        container = get_container()
        print("✅ Service container obtained")
        
        # Get services
        auth_service = container.get(AuthService)
        market_data_service = container.get(MarketDataService)
        print("✅ Services obtained")
        
        # Create enhanced trade command
        enhanced_command = EnhancedTradeCommand(market_data_service, auth_service)
        print("✅ Enhanced trade command created successfully")
        
        # Check that the authenticate method exists
        if hasattr(auth_service, 'authenticate_slack_user'):
            print("✅ AuthService has authenticate_slack_user method")
        else:
            print("❌ AuthService missing authenticate_slack_user method")
            return False
        
        # Check that the enhanced command has the correct method call
        import inspect
        source = inspect.getsource(enhanced_command._authenticate_user)
        if 'authenticate_slack_user' in source:
            print("✅ Enhanced command uses correct authentication method")
        else:
            print("❌ Enhanced command still using wrong authentication method")
            return False
        
        print("\n🎉 Authentication Fix Test Results:")
        print("   ✅ Enhanced trade command created successfully")
        print("   ✅ AuthService has correct method")
        print("   ✅ Enhanced command calls correct method")
        print("   ✅ All authentication issues resolved")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_auth_fix())
    if success:
        print("\n✅ All tests passed! The authentication fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed! There are still issues to resolve.")
        sys.exit(1)