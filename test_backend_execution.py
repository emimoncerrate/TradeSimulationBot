#!/usr/bin/env python3
"""
Backend Test for Enhanced Trade Execution

This script tests the enhanced trade execution functionality directly
without going through Slack, so we can verify everything works in the backend.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our services and models
from models.trade import Trade, TradeType, TradeStatus
from models.user import User, UserRole, UserStatus, UserProfile, Permission
from services.service_container import get_container, get_alpaca_service, get_database_service, get_market_data_service
from listeners.interactive_actions import InteractiveActionHandler
from ui.interactive_trade_widget import InteractiveTradeContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_services_initialization():
    """Test that all services initialize properly."""
    logger.info("🔧 Testing Services Initialization...")
    
    try:
        # Test service container
        container = get_container()
        logger.info("✅ Service container initialized")
        
        # Test database service
        db_service = get_database_service()
        logger.info("✅ Database service available")
        
        # Test Alpaca service
        alpaca_service = get_alpaca_service()
        if not alpaca_service.is_initialized:
            await alpaca_service._async_initialize()
        
        if alpaca_service.is_available():
            logger.info("✅ Alpaca Paper Trading service available")
            account_info = await alpaca_service.get_account()
            if account_info:
                logger.info(f"   Account: {account_info['account_number']}")
                logger.info(f"   Cash: ${account_info['cash']:,.2f}")
        else:
            logger.info("ℹ️  Alpaca service not available (will use simulation)")
        
        # Test market data service
        market_service = get_market_data_service()
        quote = await market_service.get_quote("AAPL")
        logger.info(f"✅ Market data service available - AAPL: ${quote.current_price}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Services initialization failed: {e}")
        return False


async def test_trade_creation_and_logging():
    """Test creating and logging a trade to the database."""
    logger.info("📝 Testing Trade Creation and Database Logging...")
    
    try:
        # Create a test user
        test_user = User(
            user_id="backend-test-user-123",
            slack_user_id="U_BACKEND_TEST",
            role=UserRole.EXECUTION_TRADER,
            profile=UserProfile(
                display_name="Backend Test User",
                email="test@backend.com",
                department="Testing"
            ),
            status=UserStatus.ACTIVE
        )
        
        # Create a test trade
        test_trade = Trade(
            trade_id="backend-test-trade-456",
            user_id=test_user.user_id,
            symbol="AAPL",
            quantity=50,
            trade_type=TradeType.BUY,
            price=Decimal("247.77"),
            timestamp=datetime.now(timezone.utc),
            status=TradeStatus.PENDING
        )
        
        # Log the trade to database
        db_service = get_database_service()
        success = await db_service.log_trade(test_trade)
        
        if success:
            logger.info("✅ Trade logged to database successfully")
            logger.info(f"   Trade ID: {test_trade.trade_id}")
            logger.info(f"   Symbol: {test_trade.symbol}")
            logger.info(f"   Quantity: {test_trade.quantity}")
            logger.info(f"   Price: ${test_trade.price}")
            
            # Try to retrieve the trade
            retrieved_trade = await db_service.get_trade(test_user.user_id, test_trade.trade_id)
            if retrieved_trade:
                logger.info("✅ Trade retrieved from database successfully")
                return True
            else:
                logger.error("❌ Failed to retrieve trade from database")
                return False
        else:
            logger.error("❌ Failed to log trade to database")
            return False
            
    except Exception as e:
        logger.error(f"❌ Trade creation and logging failed: {e}")
        return False


async def test_interactive_trade_execution():
    """Test the interactive trade execution system."""
    logger.info("🚀 Testing Interactive Trade Execution...")
    
    try:
        # Create test user
        test_user = User(
            user_id="interactive-test-user-789",
            slack_user_id="U_INTERACTIVE_TEST",
            role=UserRole.EXECUTION_TRADER,
            profile=UserProfile(
                display_name="Interactive Test User",
                email="interactive@test.com",
                department="Trading"
            ),
            status=UserStatus.ACTIVE
        )
        
        # Create interactive trade context
        context = InteractiveTradeContext(
            user=test_user,
            channel_id="C_TEST_CHANNEL",
            trigger_id="test_trigger_123",
            symbol="TSLA",
            trade_side="buy",
            shares=25,
            current_price=Decimal("200.00")
        )
        
        # Calculate GMV
        context.gmv = context.shares * context.current_price
        
        logger.info(f"📊 Test Trade Context:")
        logger.info(f"   Symbol: {context.symbol}")
        logger.info(f"   Side: {context.trade_side}")
        logger.info(f"   Shares: {context.shares}")
        logger.info(f"   Price: ${context.current_price}")
        logger.info(f"   GMV: ${context.gmv}")
        
        # Create interactive action handler
        handler = InteractiveActionHandler()
        
        # Create a mock Slack client for testing
        class MockSlackClient:
            def __init__(self):
                self.messages = []
                self.updates = []
            
            async def chat_postMessage(self, **kwargs):
                self.messages.append(kwargs)
                logger.info(f"📤 Mock Slack Message: {kwargs.get('text', '')[:100]}...")
                return {'ts': '1234567890.123456'}
            
            async def chat_update(self, **kwargs):
                self.updates.append(kwargs)
                logger.info(f"📝 Mock Slack Update: {kwargs.get('text', '')[:100]}...")
                return {'ts': '1234567890.123456'}
        
        mock_client = MockSlackClient()
        
        # Execute the interactive trade
        logger.info("🎯 Executing interactive trade...")
        await handler._execute_interactive_trade(context, mock_client)
        
        # Check results
        if mock_client.messages or mock_client.updates:
            logger.info("✅ Interactive trade execution completed")
            logger.info(f"   Messages sent: {len(mock_client.messages)}")
            logger.info(f"   Updates sent: {len(mock_client.updates)}")
            return True
        else:
            logger.error("❌ No messages sent - execution may have failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Interactive trade execution failed: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False


async def test_alpaca_integration():
    """Test Alpaca integration specifically."""
    logger.info("🧪 Testing Alpaca Integration...")
    
    try:
        alpaca_service = get_alpaca_service()
        
        if not alpaca_service.is_available():
            logger.info("ℹ️  Alpaca not available - testing simulation mode")
            return True
        
        # Test account info
        account_info = await alpaca_service.get_account()
        if account_info:
            logger.info("✅ Alpaca account info retrieved")
            logger.info(f"   Account: {account_info['account_number']}")
            logger.info(f"   Status: {account_info['status']}")
            logger.info(f"   Cash: ${account_info['cash']:,.2f}")
            logger.info(f"   Buying Power: ${account_info['buying_power']:,.2f}")
        
        # Test order submission (small test order)
        logger.info("📤 Testing Alpaca order submission...")
        test_order = await alpaca_service.submit_order(
            symbol="AAPL",
            quantity=1,  # Small test order
            side="buy",
            order_type="market",
            time_in_force="day"
        )
        
        if test_order:
            logger.info("✅ Alpaca test order submitted successfully")
            logger.info(f"   Order ID: {test_order.get('order_id')}")
            logger.info(f"   Status: {test_order.get('status')}")
            
            # Check order status
            if test_order.get('order_id'):
                order_status = await alpaca_service.get_order(test_order['order_id'])
                if order_status:
                    logger.info(f"   Order Status Check: {order_status.get('status')}")
            
            return True
        else:
            logger.warning("⚠️  Alpaca order submission returned None")
            return False
            
    except Exception as e:
        logger.error(f"❌ Alpaca integration test failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🎯 Starting Backend Trade Execution Tests")
    logger.info("=" * 60)
    
    # Test results
    results = {
        'services_initialization': False,
        'trade_creation_logging': False,
        'interactive_execution': False,
        'alpaca_integration': False
    }
    
    try:
        # Test 1: Services Initialization
        logger.info("\n" + "=" * 60)
        results['services_initialization'] = await test_services_initialization()
        
        # Test 2: Trade Creation and Logging
        logger.info("\n" + "=" * 60)
        results['trade_creation_logging'] = await test_trade_creation_and_logging()
        
        # Test 3: Interactive Trade Execution
        logger.info("\n" + "=" * 60)
        results['interactive_execution'] = await test_interactive_trade_execution()
        
        # Test 4: Alpaca Integration
        logger.info("\n" + "=" * 60)
        results['alpaca_integration'] = await test_alpaca_integration()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 Backend Test Summary:")
        logger.info("=" * 60)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        logger.info("")
        logger.info(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All backend tests passed! Enhanced trade execution is ready.")
            logger.info("✅ You can now test with the Slack app using: python app.py")
        else:
            logger.info("⚠️  Some backend tests failed. Check the logs above for details.")
            logger.info("🔧 Fix the issues before testing with Slack.")
        
        return passed_tests == total_tests
        
    except Exception as e:
        logger.error(f"❌ Backend test suite failed: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    # Run the backend test suite
    success = asyncio.run(main())
    sys.exit(0 if success else 1)