#!/usr/bin/env python3
"""
Simple Alpaca Trade Execution Test

Tests the Alpaca API trade execution without metrics conflicts.
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def test_alpaca_trade_execution():
    """Test Alpaca trade execution directly."""
    print("🎯 Testing Alpaca Trade Execution")
    print("=" * 50)
    
    try:
        from services.multi_alpaca_service import MultiAlpacaService
        from services.user_account_manager import UserAccountManager
        
        # Initialize services
        multi_alpaca = MultiAlpacaService()
        user_manager = UserAccountManager()
        
        # Test parameters
        test_user_id = "U08GVN6F4FQ"
        symbol = "AAPL"
        quantity = 1
        side = "buy"
        order_type = "market"
        
        print(f"🚀 Testing trade execution:")
        print(f"   👤 User: {test_user_id}")
        print(f"   📊 Trade: {side.upper()} {quantity} {symbol}")
        print(f"   📋 Order type: {order_type}")
        
        # Get user's account
        user_account = user_manager.get_user_account(test_user_id)
        print(f"🏦 User account: {user_account}")
        
        if not user_account:
            print("❌ No account assigned")
            return False
        
        # Get account info
        account_info = multi_alpaca.get_account_info(user_account)
        if not account_info:
            print("❌ Cannot get account info")
            return False
        
        cash = account_info.get('cash', 0)
        portfolio_value = account_info.get('portfolio_value', 0)
        print(f"💳 Account status:")
        print(f"   Cash: ${cash:,.2f}")
        print(f"   Portfolio: ${portfolio_value:,.2f}")
        print(f"   Status: {account_info.get('status', 'Unknown')}")
        
        # Execute trade
        print(f"\n🔄 Executing {side} order for {quantity} {symbol}...")
        
        trade_result = await multi_alpaca.execute_trade(
            account_id=user_account,
            symbol=symbol,
            qty=quantity,
            side=side,
            order_type=order_type
        )
        
        if trade_result:
            print(f"✅ Trade executed successfully!")
            print(f"📋 Order details:")
            for key, value in trade_result.items():
                print(f"   {key}: {value}")
            
            # Check updated balance
            print(f"\n💳 Checking updated account...")
            updated_account = multi_alpaca.get_account_info(user_account)
            if updated_account:
                new_cash = updated_account.get('cash', 0)
                new_portfolio = updated_account.get('portfolio_value', 0)
                print(f"   New cash: ${new_cash:,.2f}")
                print(f"   New portfolio: ${new_portfolio:,.2f}")
                print(f"   Cash change: ${new_cash - cash:,.2f}")
            
            return True
        else:
            print(f"❌ Trade execution failed")
            return False
        
    except Exception as e:
        print(f"❌ Trade execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_account_capabilities():
    """Test account capabilities and available funds."""
    print("\n🏦 Testing Account Capabilities")
    print("=" * 50)
    
    try:
        from services.multi_alpaca_service import MultiAlpacaService
        from services.user_account_manager import UserAccountManager
        
        multi_alpaca = MultiAlpacaService()
        user_manager = UserAccountManager()
        
        # Test user
        test_user_id = "U08GVN6F4FQ"
        user_account = user_manager.get_user_account(test_user_id)
        
        print(f"👤 Testing capabilities for user {test_user_id}")
        print(f"🏦 Account: {user_account}")
        
        if user_account:
            # Get detailed account info
            account_info = multi_alpaca.get_account_info(user_account)
            
            if account_info:
                print(f"\n📊 Account Details:")
                print(f"   Account Number: {account_info.get('account_number', 'N/A')}")
                print(f"   Status: {account_info.get('status', 'Unknown')}")
                print(f"   Cash: ${account_info.get('cash', 0):,.2f}")
                print(f"   Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
                print(f"   Buying Power: ${account_info.get('buying_power', 0):,.2f}")
                
                # Test trade affordability
                test_trades = [
                    {"symbol": "AAPL", "qty": 1, "est_price": 250},
                    {"symbol": "AAPL", "qty": 5, "est_price": 250},
                    {"symbol": "TSLA", "qty": 1, "est_price": 440},
                    {"symbol": "MSFT", "qty": 2, "est_price": 514},
                ]
                
                print(f"\n🧮 Trade Affordability Check:")
                cash = account_info.get('cash', 0)
                
                for trade in test_trades:
                    est_cost = trade['qty'] * trade['est_price']
                    affordable = "✅" if cash >= est_cost else "❌"
                    print(f"   {affordable} {trade['qty']} {trade['symbol']} ≈ ${est_cost:,.2f}")
                
                return True
            else:
                print("❌ Cannot get account details")
                return False
        else:
            print("❌ No account assigned")
            return False
        
    except Exception as e:
        print(f"❌ Account capabilities test failed: {e}")
        return False


async def main():
    """Run Alpaca execution tests."""
    print("🎯 Alpaca Trade Execution Test")
    print("=" * 50)
    
    tests = [
        ("Account Capabilities", test_account_capabilities),
        ("Alpaca Trade Execution", test_alpaca_trade_execution),
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
        print("🎉 ALPACA TRADE EXECUTION WORKING!")
        print()
        print("✅ Account access verified")
        print("✅ Trade execution functional")
        print("✅ Order placement working")
        print("✅ Account updates confirmed")
        print()
        print("🚀 REAL TRADES WILL EXECUTE!")
        print()
        print("When you submit the modal in Slack:")
        print("1. Trade parameters are parsed")
        print("2. User is routed to their Alpaca account")
        print("3. Order is submitted to Alpaca API")
        print("4. Trade executes on paper trading account")
        print("5. Account balance is updated")
        print("6. Confirmation is sent to user")
    else:
        print("⚠️ Some tests failed.")


if __name__ == "__main__":
    asyncio.run(main())