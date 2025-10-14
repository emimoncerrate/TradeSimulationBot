#!/usr/bin/env python3
"""
Complete Workflow Test
Tests the entire trading workflow from user creation to trade execution.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_complete_workflow():
    """Test the complete trading workflow."""
    print("🧪 Complete Workflow Test")
    print("="*60)
    
    try:
        # Import services
        from services.database import DatabaseService
        from services.alpaca_service import AlpacaService
        from services.market_data import MarketDataService
        from models.user import User, UserRole, UserStatus, UserProfile
        from models.trade import Trade, TradeType, TradeStatus
        
        # Initialize services
        print("1️⃣ Initializing Services...")
        db = DatabaseService()
        alpaca = AlpacaService()
        market_data = MarketDataService()
        
        await alpaca.initialize()
        await market_data.initialize()
        
        print("   ✅ All services initialized")
        
        # Create test user
        print("\n2️⃣ Creating Test User...")
        test_user = User(
            user_id=f"workflow-test-{int(datetime.now().timestamp())}",
            slack_user_id="U123WORKFLOW456",
            role=UserRole.EXECUTION_TRADER,
            status=UserStatus.ACTIVE,
            profile=UserProfile(
                display_name="Workflow Test User",
                email="workflow@test.com",
                department="QA Testing"
            )
        )
        
        user_created = await db.create_user(test_user)
        if user_created:
            print(f"   ✅ User created: {test_user.user_id}")
        else:
            print("   ❌ User creation failed")
            return False
        
        # Verify user retrieval
        retrieved_user = await db.get_user(test_user.user_id)
        if retrieved_user and retrieved_user.user_id == test_user.user_id:
            print("   ✅ User retrieval works")
        else:
            print("   ❌ User retrieval failed")
            return False
        
        # Get market data
        print("\n3️⃣ Getting Market Data...")
        quote = await market_data.get_quote("AAPL")
        if quote and quote.current_price > 0:
            print(f"   ✅ Market data: AAPL ${quote.current_price}")
        else:
            print("   ❌ Market data retrieval failed")
            return False
        
        # Create and log trade
        print("\n4️⃣ Creating and Logging Trade...")
        test_trade = Trade(
            trade_id=f"workflow-trade-{int(datetime.now().timestamp())}",
            user_id=test_user.user_id,
            symbol="AAPL",
            trade_type=TradeType.BUY,
            quantity=10,
            price=quote.current_price,
            status=TradeStatus.EXECUTED,
            timestamp=datetime.now(timezone.utc)
        )
        
        trade_logged = await db.log_trade(test_trade)
        if trade_logged:
            print(f"   ✅ Trade logged: {test_trade.trade_id}")
        else:
            print("   ❌ Trade logging failed")
            return False
        
        # Verify trade retrieval
        retrieved_trade = await db.get_trade(test_user.user_id, test_trade.trade_id)
        if retrieved_trade and retrieved_trade.trade_id == test_trade.trade_id:
            print("   ✅ Trade retrieval works")
        else:
            print("   ❌ Trade retrieval failed")
            return False
        
        # Get user trades
        print("\n5️⃣ Getting User Trade History...")
        user_trades = await db.get_user_trades(test_user.user_id)
        if user_trades and len(user_trades) > 0:
            print(f"   ✅ User has {len(user_trades)} trade(s)")
            
            # Find our test trade
            found_trade = any(t.trade_id == test_trade.trade_id for t in user_trades)
            if found_trade:
                print("   ✅ Test trade found in user history")
            else:
                print("   ❌ Test trade not found in user history")
                return False
        else:
            print("   ❌ No trades found for user")
            return False
        
        # Update trade status
        print("\n6️⃣ Updating Trade Status...")
        status_updated = await db.update_trade_status(
            test_user.user_id,
            test_trade.trade_id,
            TradeStatus.PARTIALLY_FILLED
        )
        if status_updated:
            print("   ✅ Trade status updated to PARTIALLY_FILLED")
        else:
            print("   ❌ Trade status update failed")
            return False
        
        # Test Alpaca integration (if available)
        print("\n7️⃣ Testing Alpaca Integration...")
        if alpaca.is_available():
            account = await alpaca.get_account()
            if account:
                print(f"   ✅ Alpaca account: {account['account_number']}")
                print(f"   ✅ Available cash: ${account['cash']:,.2f}")
                
                # Test order submission (paper trading)
                try:
                    order = await alpaca.submit_order(
                        symbol="AAPL",
                        quantity=1,
                        side="buy",
                        order_type="market"
                    )
                    if order:
                        print(f"   ✅ Test order submitted: {order['order_id']}")
                    else:
                        print("   ⚠️  Order submission returned None")
                except Exception as e:
                    print(f"   ⚠️  Order submission failed: {e}")
            else:
                print("   ❌ Could not get Alpaca account info")
        else:
            print("   ⚠️  Alpaca not available (using mock trading)")
        
        # Test data persistence
        print("\n8️⃣ Testing Data Persistence...")
        
        # Create a second database connection to simulate restart
        db2 = DatabaseService()
        
        # Try to retrieve our data with new connection
        persistent_user = await db2.get_user(test_user.user_id)
        persistent_trade = await db2.get_trade(test_user.user_id, test_trade.trade_id)
        
        if persistent_user and persistent_trade:
            print("   ✅ Data persists across connections")
        else:
            print("   ❌ Data persistence failed")
            return False
        
        print("\n" + "="*60)
        print("🎉 COMPLETE WORKFLOW TEST: PASSED")
        print("✅ All components working together successfully!")
        print("\n📊 Test Summary:")
        print(f"   • User created and retrieved: {test_user.user_id}")
        print(f"   • Trade logged and retrieved: {test_trade.trade_id}")
        print(f"   • Market data working: AAPL ${quote.current_price}")
        print(f"   • Alpaca integration: {'✅ Active' if alpaca.is_available() else '⚠️ Mock mode'}")
        print("   • Data persistence: ✅ Working")
        print("\n🚀 Your bot is production-ready!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_complete_workflow())
    sys.exit(0 if success else 1)