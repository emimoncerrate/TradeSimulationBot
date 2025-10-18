#!/usr/bin/env python3
"""
Test complete trade execution with fixed Alpaca service
"""
import asyncio
import os
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime, timezone

async def test_complete_trade():
    """Test complete trade execution"""
    load_dotenv()
    
    print("🎯 Testing Complete Trade Execution with Fixed Alpaca")
    print("=" * 60)
    
    try:
        # Import services
        from services.service_container import ServiceContainer
        from models.trade import Trade, TradeType, TradeStatus
        from listeners.interactive_actions import InteractiveActionHandler
        
        # Initialize service container
        container = ServiceContainer()
        await container.start_all_services()
        
        # Get services using convenience functions
        from services.service_container import get_alpaca_service, get_database_service
        
        alpaca_service = get_alpaca_service()
        db_service = get_database_service()
        
        print(f"✅ Alpaca Service Available: {alpaca_service.is_available()}")
        
        if not alpaca_service.is_available():
            print("❌ Alpaca service not available - test cannot proceed")
            return
        
        # Create test trade
        test_trade = Trade(
            trade_id="test-fix-" + str(int(datetime.now().timestamp())),
            user_id="test-user-fix",
            symbol="AAPL",
            quantity=1,
            trade_type=TradeType.BUY,
            price=Decimal("247.77"),
            timestamp=datetime.now(timezone.utc),
            status=TradeStatus.PENDING
        )
        
        print(f"✅ Created test trade: {test_trade.symbol} {test_trade.quantity} shares")
        
        # Create action handler
        action_handler = InteractiveActionHandler()
        
        # Execute trade
        print("🚀 Executing trade with fixed Alpaca service...")
        execution_result = await action_handler._execute_trade_with_alpaca(test_trade, alpaca_service)
        
        print(f"✅ Trade execution result:")
        print(f"   Success: {execution_result.success}")
        print(f"   Execution ID: {execution_result.execution_id}")
        print(f"   Execution Price: ${execution_result.execution_price}")
        print(f"   Alpaca Order ID: {execution_result.alpaca_order_id}")
        
        if execution_result.success:
            print("🎉 SUCCESS: Real Alpaca trade executed successfully!")
        else:
            print(f"❌ FAILED: {execution_result.error_message}")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'container' in locals():
            await container.stop_all_services()

if __name__ == "__main__":
    asyncio.run(test_complete_trade())