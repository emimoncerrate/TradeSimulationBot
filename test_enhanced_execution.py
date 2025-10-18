#!/usr/bin/env python3
"""
Test script for enhanced trade execution with Alpaca integration.

This script tests the enhanced trade execution functionality that integrates
with the Alpaca Paper Trading API and provides comprehensive database logging.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our services and models
from models.trade import Trade, TradeType, TradeStatus
from models.user import User, UserRole, UserStatus, UserProfile, Permission
from services.service_container import get_container, get_alpaca_service, get_database_service
from services.alpaca_service import AlpacaService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_alpaca_service():
    """Test Alpaca service initialization and basic functionality."""
    logger.info("🧪 Testing Alpaca Service...")
    
    try:
        # Get Alpaca service from container
        alpaca_service = get_alpaca_service()
        
        # Initialize if not already done
        if not alpaca_service.is_initialized:
            await alpaca_service._async_initialize()
        
        # Check if service is available
        if alpaca_service.is_available():
            logger.info("✅ Alpaca Paper Trading is AVAILABLE")
            
            # Get account info
            account_info = await alpaca_service.get_account()
            if account_info:
                logger.info(f"📊 Account Info:")
                logger.info(f"   Account Number: {account_info['account_number']}")
                logger.info(f"   Cash: ${account_info['cash']:,.2f}")
                logger.info(f"   Buying Power: ${account_info['buying_power']:,.2f}")
                logger.info(f"   Portfolio Value: ${account_info['portfolio_value']:,.2f}")
            else:
                logger.warning("⚠️  Could not retrieve account info")
        else:
            logger.info("ℹ️  Alpaca Paper Trading is NOT AVAILABLE (will use simulation)")
            logger.info("   This is normal if:")
            logger.info("   - ALPACA_PAPER_ENABLED=false")
            logger.info("   - API keys are not configured")
            logger.info("   - Running in mock mode")
        
        return alpaca_service.is_available()
        
    except Exception as e:
        logger.error(f"❌ Alpaca service test failed: {e}")
        return False


async def test_database_logging():
    """Test database logging functionality."""
    logger.info("🗄️  Testing Database Logging...")
    
    try:
        # Get database service
        db_service = get_database_service()
        
        # Create a test trade
        test_trade = Trade(
            trade_id="test-trade-123",
            user_id="test-user-456",
            symbol="AAPL",
            quantity=100,
            trade_type=TradeType.BUY,
            price=Decimal("150.00"),
            timestamp=datetime.now(timezone.utc),
            status=TradeStatus.PENDING
        )
        
        # Log the trade
        success = await db_service.log_trade(test_trade)
        
        if success:
            logger.info("✅ Trade logged to database successfully")
            
            # Try to retrieve the trade
            retrieved_trade = await db_service.get_trade("test-user-456", "test-trade-123")
            
            if retrieved_trade:
                logger.info("✅ Trade retrieved from database successfully")
                logger.info(f"   Trade ID: {retrieved_trade.trade_id}")
                logger.info(f"   Symbol: {retrieved_trade.symbol}")
                logger.info(f"   Quantity: {retrieved_trade.quantity}")
                logger.info(f"   Status: {retrieved_trade.status.value}")
                return True
            else:
                logger.warning("⚠️  Could not retrieve trade from database")
                return False
        else:
            logger.error("❌ Failed to log trade to database")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database logging test failed: {e}")
        return False


async def simulate_enhanced_trade_execution():
    """Simulate the enhanced trade execution flow."""
    logger.info("🚀 Simulating Enhanced Trade Execution...")
    
    try:
        # Import the enhanced execution logic from actions
        from listeners.actions import ActionHandler
        from services.service_container import get_database_service, get_market_data_service, get_trading_api_service
        
        # Create action handler (this would normally be done by the Slack app)
        action_handler = ActionHandler(
            auth_service=None,  # We'll skip auth for this test
            db_service=get_database_service(),
            market_data_service=get_market_data_service(),
            risk_analysis_service=None,  # Skip risk analysis for this test
            trading_api_service=get_trading_api_service()
        )
        
        # Create a test trade
        test_trade = Trade(
            trade_id="enhanced-test-trade-789",
            user_id="test-user-enhanced",
            symbol="TSLA",
            quantity=50,
            trade_type=TradeType.BUY,
            price=Decimal("200.00"),
            timestamp=datetime.now(timezone.utc),
            status=TradeStatus.PENDING
        )
        
        # Execute the trade using the enhanced method
        execution_result = await action_handler._execute_trade_with_alpaca(test_trade)
        
        # Display results
        logger.info("📊 Execution Results:")
        logger.info(f"   Success: {execution_result.success}")
        logger.info(f"   Execution ID: {execution_result.execution_id}")
        logger.info(f"   Execution Price: ${execution_result.execution_price}")
        logger.info(f"   Execution Time: {execution_result.execution_time_ms:.2f}ms")
        logger.info(f"   Alpaca Order ID: {execution_result.alpaca_order_id or 'N/A (Simulation)'}")
        
        if execution_result.slippage_bps is not None:
            logger.info(f"   Slippage: {execution_result.slippage_bps:.2f} bps")
        
        if execution_result.error_message:
            logger.info(f"   Error: {execution_result.error_message}")
        
        return execution_result.success
        
    except Exception as e:
        logger.error(f"❌ Enhanced trade execution simulation failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🎯 Starting Enhanced Trade Execution Tests")
    logger.info("=" * 60)
    
    # Test results
    results = {
        'alpaca_service': False,
        'database_logging': False,
        'enhanced_execution': False
    }
    
    try:
        # Test 1: Alpaca Service
        results['alpaca_service'] = await test_alpaca_service()
        logger.info("")
        
        # Test 2: Database Logging
        results['database_logging'] = await test_database_logging()
        logger.info("")
        
        # Test 3: Enhanced Trade Execution
        results['enhanced_execution'] = await simulate_enhanced_trade_execution()
        logger.info("")
        
        # Summary
        logger.info("📋 Test Summary:")
        logger.info("=" * 60)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        logger.info("")
        logger.info(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 All tests passed! Enhanced trade execution is ready.")
        else:
            logger.info("⚠️  Some tests failed. Check the logs above for details.")
        
        return passed_tests == total_tests
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return False


if __name__ == "__main__":
    # Run the test suite
    success = asyncio.run(main())
    sys.exit(0 if success else 1)