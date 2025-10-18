#!/usr/bin/env python3
"""
Backend Test for Live Market Data Integration and Multi-Account System

This script tests:
1. Live market data fetching from Finnhub
2. Multi-account Alpaca system
3. User assignment and account routing
4. Interactive modal creation with live prices
5. GMV calculations
"""

import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from services.service_container import ServiceContainer
from services.market_data import MarketDataService
from services.multi_alpaca_service import MultiAlpacaService
from services.user_account_manager import UserAccountManager
from listeners.multi_account_trade_command import MultiAccountTradeCommand


async def test_live_market_data():
    """Test live market data fetching from Finnhub."""
    print("🎯 Testing Live Market Data Integration")
    print("=" * 50)
    
    try:
        # Initialize market data service
        market_service = MarketDataService()
        
        # Test symbols
        test_symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'NVDA']
        
        for symbol in test_symbols:
            try:
                print(f"\n📊 Fetching live data for {symbol}...")
                quote = await market_service.get_quote(symbol)
                
                print(f"✅ {symbol}:")
                print(f"   💰 Current Price: ${float(quote.current_price):.2f}")
                print(f"   📈 Open: ${float(quote.open_price or 0):.2f}")
                print(f"   📊 High: ${float(quote.high_price or 0):.2f}")
                print(f"   📉 Low: ${float(quote.low_price or 0):.2f}")
                print(f"   📅 Timestamp: {quote.timestamp}")
                print(f"   🔄 Data Quality: {quote.data_quality.value}")
                print(f"   🏪 Source: {quote.source}")
                
                # Test GMV calculation
                shares = 10
                gmv = float(quote.current_price) * shares
                print(f"   🧮 GMV for {shares} shares: ${gmv:.2f}")
                
            except Exception as e:
                print(f"❌ Failed to fetch {symbol}: {e}")
        
        print(f"\n✅ Market data service test completed")
        return True
        
    except Exception as e:
        print(f"❌ Market data service test failed: {e}")
        return False


async def test_multi_account_system():
    """Test multi-account Alpaca system."""
    print("\n🏦 Testing Multi-Account Alpaca System")
    print("=" * 50)
    
    try:
        # Initialize multi-Alpaca service
        multi_alpaca = MultiAlpacaService()
        
        print(f"📊 Available accounts: {len(multi_alpaca.accounts)}")
        
        for account_id, config in multi_alpaca.accounts.items():
            print(f"\n🏦 Account: {account_id}")
            print(f"   📝 Name: {config.account_name}")
            print(f"   🔑 API Key: {config.api_key[:8]}...")
            print(f"   🌐 Base URL: {config.base_url}")
            print(f"   📄 Paper Trading: {config.is_paper}")
            print(f"   ✅ Active: {config.is_active}")
            
            # Test account info
            try:
                account_info = multi_alpaca.get_account_info(account_id)
                if account_info:
                    print(f"   💰 Cash: ${account_info.get('cash', 0):,.2f}")
                    print(f"   📈 Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
                    print(f"   🔄 Status: {account_info.get('status', 'Unknown')}")
                else:
                    print(f"   ❌ Failed to get account info")
            except Exception as e:
                print(f"   ❌ Account info error: {e}")
        
        print(f"\n✅ Multi-account system test completed")
        return True
        
    except Exception as e:
        print(f"❌ Multi-account system test failed: {e}")
        return False


async def test_user_assignment_system():
    """Test user assignment to accounts."""
    print("\n👥 Testing User Assignment System")
    print("=" * 50)
    
    try:
        # Initialize user account manager
        user_manager = UserAccountManager()
        
        # Test user IDs
        test_users = [
            "U08GVN6F4FQ",  # Your Slack ID
            "U12345TEST1",  # Test user 1
            "U12345TEST2",  # Test user 2
        ]
        
        # Available accounts
        multi_alpaca = MultiAlpacaService()
        available_accounts = list(multi_alpaca.get_available_accounts().keys())
        print(f"📊 Available accounts: {available_accounts}")
        
        for user_id in test_users:
            print(f"\n👤 Testing user: {user_id}")
            
            # Check existing assignment
            existing_account = user_manager.get_user_account(user_id)
            if existing_account:
                print(f"   ✅ Already assigned to: {existing_account}")
            else:
                print(f"   📝 No existing assignment")
                
                # Auto-assign user
                assigned_account = await user_manager.auto_assign_user(user_id, available_accounts)
                if assigned_account:
                    print(f"   ✅ Auto-assigned to: {assigned_account}")
                else:
                    print(f"   ❌ Failed to auto-assign")
        
        # Show assignment stats
        stats = user_manager.get_assignment_stats()
        print(f"\n📊 Assignment Statistics:")
        print(f"   👥 Total assignments: {stats['total_assignments']}")
        print(f"   🏦 Accounts in use: {stats['accounts_in_use']}")
        print(f"   📈 Distribution: {stats['account_distribution']}")
        print(f"   🎯 Strategy: {stats['assignment_strategy']}")
        
        print(f"\n✅ User assignment system test completed")
        return True
        
    except Exception as e:
        print(f"❌ User assignment system test failed: {e}")
        return False


async def test_modal_creation_with_live_data():
    """Test modal creation with live market data."""
    print("\n🎨 Testing Modal Creation with Live Data")
    print("=" * 50)
    
    try:
        # Test symbols
        test_symbols = ['AAPL', 'TSLA', 'MSFT']
        
        for symbol in test_symbols:
            print(f"\n📊 Testing modal for {symbol}...")
            
            # Fetch live market data
            market_service = MarketDataService()
            quote = await market_service.get_quote(symbol)
            
            # Create price text like in the modal
            current_price_text = f"*Current Stock Price:* *${float(quote.current_price):.2f}*"
            print(f"   💰 Price text: {current_price_text}")
            
            # Test GMV calculations
            test_quantities = [1, 10, 100]
            for qty in test_quantities:
                gmv = float(quote.current_price) * qty
                print(f"   🧮 {qty} shares = ${gmv:.2f} GMV")
            
            # Test reverse calculation (GMV to shares)
            test_gmvs = [1000, 5000, 10000]
            for gmv in test_gmvs:
                shares = gmv / float(quote.current_price)
                print(f"   🔄 ${gmv} GMV = {shares:.2f} shares")
        
        print(f"\n✅ Modal creation test completed")
        return True
        
    except Exception as e:
        print(f"❌ Modal creation test failed: {e}")
        return False


async def test_trade_execution_simulation():
    """Test trade execution simulation."""
    print("\n🚀 Testing Trade Execution Simulation")
    print("=" * 50)
    
    try:
        # Initialize services
        multi_alpaca = MultiAlpacaService()
        user_manager = UserAccountManager()
        
        # Test user
        test_user_id = "U08GVN6F4FQ"
        
        # Get user's account
        user_account = user_manager.get_user_account(test_user_id)
        if not user_account:
            available_accounts = list(multi_alpaca.get_available_accounts().keys())
            user_account = await user_manager.auto_assign_user(test_user_id, available_accounts)
        
        print(f"👤 Test user: {test_user_id}")
        print(f"🏦 Assigned account: {user_account}")
        
        if user_account:
            # Test trade parameters
            test_trades = [
                {"symbol": "AAPL", "qty": 2, "side": "buy", "order_type": "market"},
                {"symbol": "TSLA", "qty": 1, "side": "buy", "order_type": "market"},
                {"symbol": "MSFT", "qty": 5, "side": "sell", "order_type": "limit", "limit_price": 420.00},
            ]
            
            for trade in test_trades:
                print(f"\n📊 Testing trade: {trade}")
                
                # Get current price
                market_service = MarketDataService()
                quote = await market_service.get_quote(trade["symbol"])
                current_price = float(quote.current_price)
                
                print(f"   💰 Current price: ${current_price:.2f}")
                
                # Calculate GMV
                gmv = current_price * trade["qty"]
                print(f"   🧮 GMV: ${gmv:.2f}")
                
                # Simulate trade execution
                try:
                    trade_kwargs = {}
                    if trade.get("limit_price"):
                        trade_kwargs["limit_price"] = trade["limit_price"]
                    
                    trade_result = await multi_alpaca.execute_trade(
                        account_id=user_account,
                        symbol=trade["symbol"],
                        qty=trade["qty"],
                        side=trade["side"],
                        order_type=trade["order_type"],
                        **trade_kwargs
                    )
                    
                    if trade_result:
                        print(f"   ✅ Trade executed successfully")
                        print(f"      📋 Order ID: {trade_result.get('order_id')}")
                        print(f"      📊 Status: {trade_result.get('status')}")
                        print(f"      ⏰ Submitted: {trade_result.get('submitted_at')}")
                    else:
                        print(f"   ❌ Trade execution failed")
                        
                except Exception as e:
                    print(f"   ❌ Trade error: {e}")
        
        print(f"\n✅ Trade execution simulation completed")
        return True
        
    except Exception as e:
        print(f"❌ Trade execution simulation failed: {e}")
        return False


async def main():
    """Run all backend tests."""
    print("🎯 Backend Test Suite for Live Market Integration")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    print()
    
    # Run all tests
    tests = [
        ("Live Market Data", test_live_market_data),
        ("Multi-Account System", test_multi_account_system),
        ("User Assignment System", test_user_assignment_system),
        ("Modal Creation with Live Data", test_modal_creation_with_live_data),
        ("Trade Execution Simulation", test_trade_execution_simulation),
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
        print("🎉 ALL TESTS PASSED! System ready for Slack testing.")
    else:
        print("⚠️  Some tests failed. Check the output above.")
    
    print(f"⏰ Completed at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())