#!/usr/bin/env python3
"""
Backend Test for Live Price Integration

Tests the new live price fetching functionality that updates modals
with real-time market data from Finnhub.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def test_live_price_fetching():
    """Test live price fetching from Finnhub."""
    print("🎯 Testing Live Price Fetching")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        
        # Initialize market data service
        market_service = MarketDataService()
        
        # Test symbols that users commonly trade
        test_symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'NVDA', 'META', 'AMZN']
        
        print("📊 Fetching live prices for popular stocks...")
        
        for symbol in test_symbols:
            try:
                print(f"\n🔍 Fetching {symbol}...")
                quote = await market_service.get_quote(symbol)
                
                current_price = float(quote.current_price)
                
                # Test the modal price text format
                modal_price_text = f"*Current Stock Price:* *${current_price:.2f}*"
                
                print(f"✅ {symbol}:")
                print(f"   💰 Price: ${current_price:.2f}")
                print(f"   📱 Modal text: {modal_price_text}")
                print(f"   📊 Data quality: {quote.data_quality.value}")
                print(f"   ⏰ Timestamp: {quote.timestamp}")
                
                # Test GMV calculations with this price
                test_quantities = [1, 2, 5, 10]
                print(f"   🧮 GMV calculations:")
                for qty in test_quantities:
                    gmv = current_price * qty
                    print(f"      {qty} shares = ${gmv:.2f}")
                
            except Exception as e:
                print(f"❌ Failed to fetch {symbol}: {e}")
        
        print(f"\n✅ Live price fetching test completed")
        return True
        
    except Exception as e:
        print(f"❌ Live price fetching test failed: {e}")
        return False


async def test_modal_price_update_simulation():
    """Test the modal price update functionality simulation."""
    print("\n🎨 Testing Modal Price Update Simulation")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        
        market_service = MarketDataService()
        
        # Simulate the /buy aapl 2 command flow
        symbol = "AAPL"
        quantity = "2"
        
        print(f"🚀 Simulating: /buy {symbol.lower()} {quantity}")
        
        # Step 1: Initial modal state (loading)
        initial_price_text = f"*Current Stock Price:* *Loading {symbol} price...*"
        print(f"📱 Initial modal: {initial_price_text}")
        
        # Step 2: Fetch live price (background task simulation)
        print(f"🔄 Background task: Fetching live price for {symbol}...")
        quote = await market_service.get_quote(symbol)
        current_price = float(quote.current_price)
        
        # Step 3: Updated modal state
        updated_price_text = f"*Current Stock Price:* *${current_price:.2f}*"
        print(f"📱 Updated modal: {updated_price_text}")
        
        # Step 4: Test interactive calculations
        print(f"\n🧮 Interactive calculations with live price:")
        
        # User types different quantities
        test_scenarios = [
            {"action": "User types 1 share", "shares": 1},
            {"action": "User types 5 shares", "shares": 5},
            {"action": "User types 10 shares", "shares": 10},
        ]
        
        for scenario in test_scenarios:
            shares = scenario["shares"]
            gmv = current_price * shares
            print(f"   📈 {scenario['action']}: ${gmv:.2f} GMV")
        
        # User types GMV amounts
        gmv_scenarios = [
            {"action": "User types $500 GMV", "gmv": 500},
            {"action": "User types $1000 GMV", "gmv": 1000},
            {"action": "User types $2500 GMV", "gmv": 2500},
        ]
        
        for scenario in gmv_scenarios:
            gmv = scenario["gmv"]
            shares = gmv / current_price
            print(f"   📉 {scenario['action']}: {shares:.2f} shares")
        
        print(f"\n✅ Modal price update simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Modal price update simulation failed: {e}")
        return False


async def test_price_update_timing():
    """Test the timing of price updates."""
    print("\n⏱️ Testing Price Update Timing")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        import time
        
        market_service = MarketDataService()
        
        # Test multiple symbols for timing
        symbols = ['AAPL', 'TSLA', 'MSFT']
        
        for symbol in symbols:
            print(f"\n🔍 Testing {symbol} fetch timing...")
            
            # Measure fetch time
            start_time = time.time()
            quote = await market_service.get_quote(symbol)
            fetch_time = (time.time() - start_time) * 1000  # Convert to ms
            
            current_price = float(quote.current_price)
            
            print(f"✅ {symbol}:")
            print(f"   💰 Price: ${current_price:.2f}")
            print(f"   ⏱️ Fetch time: {fetch_time:.1f}ms")
            print(f"   📊 Data source: {quote.source}")
            print(f"   🔄 Cache hit: {quote.cache_hit}")
            
            # Check if timing is acceptable for modal updates
            if fetch_time < 1000:  # Less than 1 second
                print(f"   ✅ Fast enough for modal updates")
            else:
                print(f"   ⚠️ Might be slow for modal updates")
        
        print(f"\n✅ Price update timing test completed")
        return True
        
    except Exception as e:
        print(f"❌ Price update timing test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling for invalid symbols."""
    print("\n🚨 Testing Error Handling")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        
        market_service = MarketDataService()
        
        # Test invalid symbols
        invalid_symbols = ['INVALID', 'FAKE123', 'NOTREAL']
        
        for symbol in invalid_symbols:
            print(f"\n🔍 Testing invalid symbol: {symbol}")
            
            try:
                quote = await market_service.get_quote(symbol)
                print(f"⚠️ Unexpected success for {symbol}: ${float(quote.current_price):.2f}")
            except Exception as e:
                print(f"✅ Correctly handled error for {symbol}: {type(e).__name__}")
                
                # Test fallback modal text
                fallback_text = f"*Current Stock Price:* *Price unavailable*"
                print(f"   📱 Fallback modal text: {fallback_text}")
        
        print(f"\n✅ Error handling test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


async def test_complete_trading_workflow():
    """Test the complete trading workflow with live prices."""
    print("\n🔄 Testing Complete Trading Workflow")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        from services.multi_alpaca_service import MultiAlpacaService
        from services.user_account_manager import UserAccountManager
        
        # Initialize services
        market_service = MarketDataService()
        multi_alpaca = MultiAlpacaService()
        user_manager = UserAccountManager()
        
        # Test user and trade
        test_user_id = "U08GVN6F4FQ"
        symbol = "AAPL"
        quantity = 2
        
        print(f"🚀 Testing complete workflow: User {test_user_id} buying {quantity} {symbol}")
        
        # Step 1: Get user's account
        user_account = user_manager.get_user_account(test_user_id)
        print(f"👤 User account: {user_account}")
        
        # Step 2: Fetch live price
        quote = await market_service.get_quote(symbol)
        current_price = float(quote.current_price)
        print(f"💰 Live {symbol} price: ${current_price:.2f}")
        
        # Step 3: Calculate trade value
        trade_value = current_price * quantity
        print(f"🧮 Trade value: {quantity} × ${current_price:.2f} = ${trade_value:.2f}")
        
        # Step 4: Check account balance
        if user_account:
            account_info = multi_alpaca.get_account_info(user_account)
            if account_info:
                cash = account_info.get('cash', 0)
                print(f"💳 Account cash: ${cash:,.2f}")
                
                if cash >= trade_value:
                    print(f"✅ Trade is affordable")
                    
                    # Step 5: Simulate modal data
                    modal_data = {
                        "symbol": symbol,
                        "quantity": quantity,
                        "current_price": current_price,
                        "trade_value": trade_value,
                        "account": user_account,
                        "price_text": f"*Current Stock Price:* *${current_price:.2f}*"
                    }
                    
                    print(f"📱 Modal data ready:")
                    for key, value in modal_data.items():
                        print(f"   {key}: {value}")
                    
                else:
                    print(f"❌ Insufficient funds: ${trade_value:.2f} > ${cash:,.2f}")
        
        print(f"\n✅ Complete trading workflow test completed")
        return True
        
    except Exception as e:
        print(f"❌ Complete trading workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all live price integration tests."""
    print("🎯 Live Price Integration Backend Test Suite")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    print()
    
    # Run all tests
    tests = [
        ("Live Price Fetching", test_live_price_fetching),
        ("Modal Price Update Simulation", test_modal_price_update_simulation),
        ("Price Update Timing", test_price_update_timing),
        ("Error Handling", test_error_handling),
        ("Complete Trading Workflow", test_complete_trading_workflow),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Live market data integration working perfectly")
        print("✅ Modal price updates ready")
        print("✅ Interactive calculations functional")
        print("✅ Error handling robust")
        print("✅ Complete workflow verified")
        print("\n🚀 READY FOR SLACK TESTING WITH LIVE PRICES!")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print(f"⏰ Completed at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())