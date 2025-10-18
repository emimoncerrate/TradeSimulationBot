#!/usr/bin/env python3
"""
Test the fixed Alpaca service initialization
"""
import os
from dotenv import load_dotenv

def test_alpaca_service():
    """Test the fixed Alpaca service"""
    load_dotenv()
    
    print("🎯 Testing Fixed Alpaca Service")
    print("=" * 50)
    
    try:
        from services.alpaca_service import AlpacaService
        
        print("✅ Creating AlpacaService...")
        alpaca_service = AlpacaService()
        
        print("✅ Initializing AlpacaService (sync)...")
        alpaca_service.initialize()
        
        print(f"✅ Service initialized: {alpaca_service.is_initialized}")
        print(f"✅ Service available: {alpaca_service.is_available()}")
        
        if alpaca_service.is_available():
            print("🎉 SUCCESS: Alpaca service is working!")
            
            # Test account info
            account_info = alpaca_service.account_info
            if account_info:
                print(f"💰 Account: {account_info['account_number']}")
                print(f"💰 Cash: ${account_info['cash']:,.2f}")
                print(f"💰 Status: {account_info['status']}")
        else:
            print("❌ FAILED: Alpaca service is not available")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_alpaca_service()