#!/usr/bin/env python3
"""Test enhanced trade command imports."""

try:
    print("Testing enhanced trade command imports...")
    
    from listeners.enhanced_trade_command import EnhancedTradeCommand
    print("✅ EnhancedTradeCommand imported successfully")
    
    from listeners.enhanced_market_actions import EnhancedMarketActions  
    print("✅ EnhancedMarketActions imported successfully")
    
    from services.market_data import MarketDataService
    print("✅ MarketDataService imported successfully")
    
    print("\n🎉 All imports successful!")
    print("The enhanced trade command should work now.")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n🔧 Troubleshooting:")
    print("1. Make sure all files exist")
    print("2. Check for syntax errors")
    print("3. Verify dependencies are installed")