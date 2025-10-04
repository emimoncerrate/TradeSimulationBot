#!/usr/bin/env python3
"""
Simple test script to verify app components can be imported and initialized.
"""

import os
import sys
from datetime import datetime

# Set environment variables for testing
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG_MODE'] = 'true'
os.environ['MOCK_EXECUTION_ENABLED'] = 'true'

def test_imports():
    """Test that all major components can be imported."""
    print("Testing imports...")
    
    try:
        from config.settings import get_config
        print("✅ Config module imported successfully")
        
        from services.service_container import get_container
        print("✅ Service container imported successfully")
        
        from models.user import User, UserRole
        print("✅ User models imported successfully")
        
        from models.trade import Trade, TradeType
        print("✅ Trade models imported successfully")
        
        from utils.formatters import format_money, format_percent
        print("✅ Formatters imported successfully")
        
        from utils.validators import validate_symbol
        print("✅ Validators imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from config.settings import get_config
        config = get_config()
        
        print(f"✅ Environment: {config.environment}")
        print(f"✅ Debug mode: {config.debug_mode}")
        print(f"✅ Mock execution: {config.trading.mock_execution_enabled}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_services():
    """Test service container initialization."""
    print("\nTesting services...")
    
    try:
        from services.service_container import get_container
        container = get_container()
        
        print("✅ Service container initialized")
        print(f"✅ Container has {len(container._services)} service types registered")
        
        return True
        
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

def test_formatters():
    """Test formatter functions."""
    print("\nTesting formatters...")
    
    try:
        from utils.formatters import format_money, format_percent
        
        # Test currency formatting
        money_result = format_money(1234.56)
        print(f"✅ Currency formatting: {money_result}")
        
        # Test percentage formatting
        percent_result = format_percent(0.1234)
        print(f"✅ Percentage formatting: {percent_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Formatter test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Slack Trading Bot component tests...")
    print(f"📅 Test time: {datetime.now()}")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_services,
        test_formatters
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The app structure is working correctly.")
        print("\n💡 Next steps:")
        print("1. Get a valid Slack bot token from your Slack app")
        print("2. Get a Finnhub API key from https://finnhub.io/")
        print("3. Update your .env file with real credentials")
        print("4. Run the full app with: python3 app.py")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())