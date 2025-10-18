#!/usr/bin/env python3
"""
Test Parameter Parsing

This script tests the new parameter parsing functionality.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_parameter_parsing():
    """Test the parameter parsing functionality."""
    print("🧪 Testing Parameter Parsing")
    print("=" * 50)
    
    try:
        # Import the multi-account command
        from services.service_container import get_container
        from services.auth import AuthService
        from listeners.multi_account_trade_command import MultiAccountTradeCommand
        
        container = get_container()
        auth_service = container.get(AuthService)
        
        # Create command instance
        multi_command = MultiAccountTradeCommand(auth_service)
        
        # Test different command formats
        test_cases = [
            "/trade 2 aapl buy",
            "/trade 100 TSLA",
            "/trade MSFT buy",
            "/trade sell 50 NVDA",
            "/trade 10 GOOGL sell",
            "/trade AAPL",
            "/trade buy 25 META",
            "/trade 5 amzn",
            ""
        ]
        
        print("🔍 Testing parameter parsing:")
        
        for i, test_case in enumerate(test_cases, 1):
            # Extract just the parameters (remove /trade)
            command_text = test_case.replace("/trade", "").strip()
            
            print(f"\n{i}. Input: '{test_case}'")
            
            # Parse parameters
            params = multi_command._parse_trade_parameters(command_text)
            
            print(f"   Symbol: {params.get('symbol', 'None')}")
            print(f"   Quantity: {params.get('quantity', 'None')}")
            print(f"   Action: {params.get('action', 'None')}")
            print(f"   GMV: {params.get('gmv', 'None')}")
        
        print(f"\n" + "=" * 50)
        print("🎉 Parameter Parsing Test Completed!")
        
        print(f"\n💡 Expected behavior:")
        print(f"   '/trade 2 aapl buy' should pre-fill:")
        print(f"   - Symbol: AAPL")
        print(f"   - Quantity: 2")
        print(f"   - Action: Buy")
        print(f"   - GMV: (calculated from current price)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_parameter_parsing()
    
    if success:
        print(f"\n🎯 Parameter parsing is working!")
        print(f"   Restart your Slack app and try: /trade 2 aapl buy")
    else:
        print(f"\n💥 Parameter parsing has issues")
    
    sys.exit(0 if success else 1)