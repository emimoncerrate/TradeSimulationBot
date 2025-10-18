#!/usr/bin/env python3
"""
Core Functionality Test - Simplified Backend Test

Tests the essential features without metrics conflicts.
"""

import asyncio
import os
import sys
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def test_market_data_and_calculations():
    """Test market data fetching and GMV calculations."""
    print("🎯 Testing Core Market Data & Calculations")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        
        # Initialize service
        market_service = MarketDataService()
        
        # Test AAPL
        symbol = "AAPL"
        print(f"📊 Fetching live price for {symbol}...")
        
        quote = await market_service.get_quote(symbol)
        current_price = float(quote.current_price)
        
        print(f"✅ {symbol} Current Price: ${current_price:.2f}")
        
        # Test GMV calculations like in the modal
        test_scenarios = [
            {"shares": 2, "description": "User types 2 shares"},
            {"shares": 10, "description": "User types 10 shares"},
            {"gmv": 1000, "description": "User types $1000 GMV"},
            {"gmv": 5000, "description": "User types $5000 GMV"},
        ]
        
        print(f"\n🧮 Testing Interactive Calculations:")
        for scenario in test_scenarios:
            if "shares" in scenario:
                shares = scenario["shares"]
                gmv = current_price * shares
                print(f"   📈 {scenario['description']}: {shares} shares = ${gmv:.2f} GMV")
            else:
                gmv = scenario["gmv"]
                shares = gmv / current_price
                print(f"   📉 {scenario['description']}: ${gmv} GMV = {shares:.2f} shares")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_user_account_routing():
    """Test user to account routing."""
    print("\n🏦 Testing User Account Routing")
    print("=" * 50)
    
    try:
        from services.multi_alpaca_service import MultiAlpacaService
        from services.user_account_manager import UserAccountManager
        
        # Initialize services
        multi_alpaca = MultiAlpacaService()
        user_manager = UserAccountManager()
        
        # Test user
        test_user_id = "U08GVN6F4FQ"
        
        print(f"👤 Testing user: {test_user_id}")
        
        # Get user's assigned account
        user_account = user_manager.get_user_account(test_user_id)
        print(f"🏦 Assigned account: {user_account}")
        
        # Get account info
        if user_account:
            account_info = multi_alpaca.get_account_info(user_account)
            if account_info:
                print(f"💰 Account cash: ${account_info.get('cash', 0):,.2f}")
                print(f"📈 Portfolio value: ${account_info.get('portfolio_value', 0):,.2f}")
                print(f"✅ Account routing working correctly")
                return True
        
        print(f"❌ Account routing failed")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_modal_price_integration():
    """Test modal creation with live prices (simulation)."""
    print("\n🎨 Testing Modal Price Integration")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        
        market_service = MarketDataService()
        
        # Simulate what happens when /buy aapl 2 is called
        symbol = "AAPL"
        quantity = "2"
        
        print(f"🚀 Simulating: /buy {symbol.lower()} {quantity}")
        
        # Fetch live price (like in the command handler)
        quote = await market_service.get_quote(symbol)
        current_price = float(quote.current_price)
        
        # Create price text for modal
        current_price_text = f"*Current Stock Price:* *${current_price:.2f}*"
        print(f"📊 Modal price display: {current_price_text}")
        
        # Simulate modal fields
        modal_data = {
            "symbol": symbol,
            "initial_quantity": quantity,
            "current_price": current_price,
            "price_text": current_price_text
        }
        
        print(f"✅ Modal data prepared:")
        print(f"   📝 Symbol: {modal_data['symbol']}")
        print(f"   🔢 Initial quantity: {modal_data['initial_quantity']}")
        print(f"   💰 Current price: ${modal_data['current_price']:.2f}")
        print(f"   🎨 Price text: {modal_data['price_text']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def main():
    """Run core functionality tests."""
    print("🎯 Core Functionality Backend Test")
    print("=" * 50)
    
    tests = [
        ("Market Data & Calculations", test_market_data_and_calculations),
        ("User Account Routing", test_user_account_routing),
        ("Modal Price Integration", test_modal_price_integration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL CORE TESTS PASSED!")
        print("✅ Live market data integration working")
        print("✅ Multi-account system working") 
        print("✅ User routing working")
        print("✅ Ready for Slack testing!")
    else:
        print("⚠️  Some tests failed.")


if __name__ == "__main__":
    asyncio.run(main())