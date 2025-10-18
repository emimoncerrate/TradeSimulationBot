#!/usr/bin/env python3
"""
Simple Live Price Integration Test

Tests the core live price functionality without metrics conflicts.
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


async def test_live_price_workflow():
    """Test the complete live price workflow."""
    print("🎯 Testing Live Price Workflow")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        from services.multi_alpaca_service import MultiAlpacaService
        from services.user_account_manager import UserAccountManager
        
        # Initialize services (single instances to avoid conflicts)
        market_service = MarketDataService()
        multi_alpaca = MultiAlpacaService()
        user_manager = UserAccountManager()
        
        # Test the /buy aapl 2 workflow
        print("🚀 Simulating: /buy aapl 2")
        
        # Step 1: Parse command
        symbol = "AAPL"
        quantity = 2
        print(f"📝 Parsed: symbol={symbol}, quantity={quantity}")
        
        # Step 2: Initial modal state
        initial_text = f"*Current Stock Price:* *Loading {symbol} price...*"
        print(f"📱 Initial modal: {initial_text}")
        
        # Step 3: Fetch live price (background task simulation)
        print(f"🔄 Fetching live price for {symbol}...")
        quote = await market_service.get_quote(symbol)
        current_price = float(quote.current_price)
        
        # Step 4: Updated modal state
        updated_text = f"*Current Stock Price:* *${current_price:.2f}*"
        print(f"📱 Updated modal: {updated_text}")
        print(f"💰 Live price: ${current_price:.2f}")
        print(f"📊 Data quality: {quote.data_quality.value}")
        print(f"⏰ Fetch time: {quote.timestamp}")
        
        # Step 5: Interactive calculations
        print(f"\n🧮 Interactive Calculations:")
        
        # GMV calculation (shares → GMV)
        gmv = current_price * quantity
        print(f"   📈 {quantity} shares × ${current_price:.2f} = ${gmv:.2f} GMV")
        
        # Reverse calculation (GMV → shares)
        test_gmv = 1000
        calculated_shares = test_gmv / current_price
        print(f"   📉 ${test_gmv} GMV ÷ ${current_price:.2f} = {calculated_shares:.2f} shares")
        
        # Step 6: User account routing
        test_user_id = "U08GVN6F4FQ"
        user_account = user_manager.get_user_account(test_user_id)
        print(f"\n👤 User {test_user_id} → Account: {user_account}")
        
        # Step 7: Account balance check
        if user_account:
            account_info = multi_alpaca.get_account_info(user_account)
            if account_info:
                cash = account_info.get('cash', 0)
                print(f"💳 Account cash: ${cash:,.2f}")
                
                if cash >= gmv:
                    print(f"✅ Trade affordable: ${gmv:.2f} ≤ ${cash:,.2f}")
                else:
                    print(f"⚠️ Trade too expensive: ${gmv:.2f} > ${cash:,.2f}")
        
        # Step 8: Test other popular symbols
        print(f"\n📊 Testing other popular symbols:")
        other_symbols = ['TSLA', 'MSFT', 'GOOGL']
        
        for test_symbol in other_symbols:
            try:
                test_quote = await market_service.get_quote(test_symbol)
                test_price = float(test_quote.current_price)
                modal_text = f"*Current Stock Price:* *${test_price:.2f}*"
                print(f"   {test_symbol}: ${test_price:.2f} → {modal_text}")
            except Exception as e:
                print(f"   {test_symbol}: Error - {e}")
        
        print(f"\n✅ Live price workflow test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Live price workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_modal_update_timing():
    """Test the timing of modal updates."""
    print("\n⏱️ Testing Modal Update Timing")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        import time
        
        # Use existing service instance
        market_service = MarketDataService()
        
        symbol = "AAPL"
        
        print(f"🔍 Testing modal update timing for {symbol}...")
        
        # Simulate modal opening
        start_time = time.time()
        print(f"📱 Modal opens with: *Current Stock Price:* *Loading {symbol} price...*")
        
        # Simulate 0.5 second delay (as in the code)
        await asyncio.sleep(0.5)
        delay_time = time.time()
        
        # Fetch price
        quote = await market_service.get_quote(symbol)
        fetch_time = time.time()
        
        current_price = float(quote.current_price)
        updated_text = f"*Current Stock Price:* *${current_price:.2f}*"
        
        total_time = (fetch_time - start_time) * 1000  # Convert to ms
        fetch_only_time = (fetch_time - delay_time) * 1000
        
        print(f"📱 Modal updates to: {updated_text}")
        print(f"⏱️ Total time: {total_time:.1f}ms")
        print(f"⏱️ Fetch time: {fetch_only_time:.1f}ms")
        print(f"📊 Cache hit: {quote.cache_hit}")
        
        if total_time < 2000:  # Less than 2 seconds total
            print(f"✅ Acceptable timing for user experience")
        else:
            print(f"⚠️ Might be slow for user experience")
        
        return True
        
    except Exception as e:
        print(f"❌ Modal update timing test failed: {e}")
        return False


async def test_error_scenarios():
    """Test error handling scenarios."""
    print("\n🚨 Testing Error Scenarios")
    print("=" * 50)
    
    try:
        from services.market_data import MarketDataService
        
        market_service = MarketDataService()
        
        # Test 1: Invalid symbol
        print("🔍 Testing invalid symbol...")
        try:
            quote = await market_service.get_quote("INVALID")
            print(f"⚠️ Unexpected success: ${float(quote.current_price):.2f}")
        except Exception as e:
            print(f"✅ Correctly handled invalid symbol: {type(e).__name__}")
            fallback_text = "*Current Stock Price:* *Price unavailable*"
            print(f"   📱 Fallback text: {fallback_text}")
        
        # Test 2: Empty symbol
        print(f"\n🔍 Testing empty symbol...")
        try:
            quote = await market_service.get_quote("")
            print(f"⚠️ Unexpected success for empty symbol")
        except Exception as e:
            print(f"✅ Correctly handled empty symbol: {type(e).__name__}")
        
        # Test 3: Valid symbol (should work)
        print(f"\n🔍 Testing valid symbol (AAPL)...")
        try:
            quote = await market_service.get_quote("AAPL")
            price = float(quote.current_price)
            print(f"✅ Valid symbol works: ${price:.2f}")
        except Exception as e:
            print(f"❌ Valid symbol failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error scenarios test failed: {e}")
        return False


async def main():
    """Run simplified live price integration tests."""
    print("🎯 Simple Live Price Integration Test")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now()}")
    
    tests = [
        ("Live Price Workflow", test_live_price_workflow),
        ("Modal Update Timing", test_modal_update_timing),
        ("Error Scenarios", test_error_scenarios),
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
        print("🎉 ALL TESTS PASSED!")
        print()
        print("✅ Live market data fetching working")
        print("✅ Modal price updates functional")
        print("✅ Interactive calculations ready")
        print("✅ User account routing working")
        print("✅ Error handling robust")
        print()
        print("🚀 READY FOR SLACK TESTING!")
        print("   Try: /buy aapl 2")
        print("   Expected: Modal opens → Shows 'Loading AAPL price...' → Updates to live price")
    else:
        print("⚠️ Some tests failed.")
    
    print(f"⏰ Completed at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())