"""
Test script for Alpaca trading integration.

This script tests the Alpaca API connection and validates that the integration
is working correctly with paper trading before enabling real trading.
"""

import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime

# Ensure we're loading from the right path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.alpaca_trading import get_alpaca_trading_service, AlpacaConfig
from models.trade import Trade, TradeType
from config.settings import get_config


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_alpaca_connection():
    """Test 1: Verify Alpaca API connection and account access"""
    print_section("TEST 1: Alpaca API Connection")
    
    try:
        service = await get_alpaca_trading_service()
        print("✅ Alpaca service initialized successfully")
        
        account_info = await service.get_account_info()
        print("\n📊 Account Information:")
        print(f"   Account Number: {account_info['account_number']}")
        print(f"   Status: {account_info['status']}")
        print(f"   Currency: {account_info['currency']}")
        print(f"   Buying Power: ${account_info['buying_power']:,.2f}")
        print(f"   Cash: ${account_info['cash']:,.2f}")
        print(f"   Portfolio Value: ${account_info['portfolio_value']:,.2f}")
        print(f"   Trading Blocked: {account_info['trading_blocked']}")
        print(f"   Pattern Day Trader: {account_info['pattern_day_trader']}")
        
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


async def test_get_positions():
    """Test 2: Retrieve current positions from Alpaca"""
    print_section("TEST 2: Get Current Positions")
    
    try:
        service = await get_alpaca_trading_service()
        positions = await service.get_positions()
        
        if positions:
            print(f"\n📈 You have {len(positions)} position(s):\n")
            for pos in positions:
                print(f"   {pos['symbol']}:")
                print(f"      Quantity: {pos['quantity']}")
                print(f"      Market Value: ${pos['market_value']:,.2f}")
                print(f"      Cost Basis: ${pos['cost_basis']:,.2f}")
                print(f"      Unrealized P/L: ${pos['unrealized_pl']:,.2f} ({pos['unrealized_plpc']:.2f}%)")
                print(f"      Current Price: ${pos['current_price']:.2f}")
                print()
        else:
            print("\n📊 No open positions")
        
        return True
    except Exception as e:
        print(f"❌ Get positions test failed: {e}")
        return False


async def test_paper_trade_small():
    """Test 3: Execute a small paper trade (1 share)"""
    print_section("TEST 3: Execute Small Paper Trade")
    
    print("\n⚠️  WARNING: This will execute a REAL trade on your paper trading account!")
    print("Symbol: AAPL")
    print("Quantity: 1 share")
    print("Type: Market Buy")
    
    response = input("\nProceed with paper trade? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Test skipped by user")
        return False
    
    try:
        service = await get_alpaca_trading_service()
        
        # Create a test trade
        test_trade = Trade(
            user_id="TEST_USER",
            symbol="AAPL",
            quantity=1,
            trade_type=TradeType.BUY,
            price=Decimal("150.00")  # This is just for reference, market order will use current price
        )
        
        print("\n🚀 Submitting trade to Alpaca...")
        execution_report = await service.execute_trade(test_trade)
        
        print("\n✅ Trade executed successfully!")
        print(f"\n📋 Execution Report:")
        print(f"   Order ID: {execution_report.order_id}")
        print(f"   Status: {execution_report.status.value}")
        print(f"   Filled Quantity: {execution_report.filled_quantity}")
        print(f"   Average Fill Price: ${execution_report.average_fill_price:.2f}" if execution_report.average_fill_price else "   Average Fill Price: N/A")
        print(f"   Total Value: ${float(execution_report.total_execution_value):,.2f}")
        print(f"   Total Commission: ${float(execution_report.total_commission):,.2f}")
        print(f"   Execution Time: {execution_report.execution_time_ms:.2f}ms" if execution_report.execution_time_ms else "   Execution Time: N/A")
        
        if execution_report.fills:
            print(f"\n   Fills ({len(execution_report.fills)}):")
            for fill in execution_report.fills:
                print(f"      - {fill.quantity} @ ${fill.price:.2f} on {fill.venue.value}")
        
        return True
    except Exception as e:
        print(f"❌ Paper trade test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_with_trading_service():
    """Test 4: Test integration with main TradingAPIService"""
    print_section("TEST 4: Integration with TradingAPIService")
    
    try:
        from services.trading_api import get_trading_api_service
        
        service = await get_trading_api_service()
        print("✅ TradingAPIService initialized")
        
        # Check configuration
        config = get_config()
        print(f"\n⚙️  Configuration:")
        print(f"   Use Real Trading: {config.trading.use_real_trading}")
        print(f"   Alpaca Enabled: {config.alpaca.enabled}")
        print(f"   Paper Trading: {config.alpaca.paper_trading}")
        print(f"   Mock Execution: {config.trading.mock_execution_enabled}")
        
        # Test routing logic
        test_trade = Trade(
            user_id="TEST_USER",
            symbol="MSFT",
            quantity=1,
            trade_type=TradeType.BUY,
            price=Decimal("300.00")
        )
        
        if config.trading.use_real_trading and config.alpaca.enabled:
            print("\n✅ Configuration set for REAL trading via Alpaca")
            print("   Trades will be routed to Alpaca paper trading account")
        else:
            print("\n✅ Configuration set for MOCK trading")
            print("   Trades will use simulation engine")
        
        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_configuration():
    """Test 5: Validate configuration settings"""
    print_section("TEST 5: Configuration Validation")
    
    try:
        config = get_config()
        
        print("\n📋 Current Configuration:")
        print(f"\n   Environment: {config.environment.value}")
        print(f"   Debug Mode: {config.debug_mode}")
        
        print(f"\n   🔧 Trading Settings:")
        print(f"      Use Real Trading: {config.trading.use_real_trading}")
        print(f"      Mock Execution: {config.trading.mock_execution_enabled}")
        print(f"      Max Position Size: {config.trading.max_position_size:,}")
        print(f"      Max Trade Value: ${config.trading.max_trade_value:,.2f}")
        
        print(f"\n   🦙 Alpaca Settings:")
        print(f"      Enabled: {config.alpaca.enabled}")
        print(f"      Paper Trading: {config.alpaca.paper_trading}")
        print(f"      Base URL: {config.alpaca.base_url}")
        print(f"      API Key Set: {'Yes' if config.alpaca.api_key else 'No'}")
        print(f"      Secret Key Set: {'Yes' if config.alpaca.secret_key else 'No'}")
        
        # Validate required environment variables
        required_for_alpaca = ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY']
        missing = []
        
        for var in required_for_alpaca:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            print(f"\n   ⚠️  Missing environment variables for Alpaca:")
            for var in missing:
                print(f"      - {var}")
            print("\n   To enable Alpaca trading:")
            print("   1. Get API keys from https://alpaca.markets")
            print("   2. Add them to your .env file")
            print("   3. Set ALPACA_ENABLED=true")
            print("   4. Set USE_REAL_TRADING=true")
        else:
            print(f"\n   ✅ All required Alpaca environment variables are set")
        
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  ALPACA TRADING INTEGRATION TEST SUITE".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    print(f"\nTest started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Test 5: Configuration (run first)
    results['configuration'] = await test_configuration()
    
    # Test 1: Connection
    results['connection'] = await test_alpaca_connection()
    
    # Test 2: Get Positions
    if results['connection']:
        results['positions'] = await test_get_positions()
    else:
        print("\n⏩ Skipping position test (connection failed)")
        results['positions'] = False
    
    # Test 4: Integration
    results['integration'] = await test_integration_with_trading_service()
    
    # Test 3: Paper Trade (only if user confirms)
    if results['connection']:
        results['paper_trade'] = await test_paper_trade_small()
    else:
        print("\n⏩ Skipping paper trade test (connection failed)")
        results['paper_trade'] = False
    
    # Summary
    print_section("TEST SUMMARY")
    print()
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\n   Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Alpaca integration is ready.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def main():
    """Main entry point"""
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

