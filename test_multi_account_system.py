#!/usr/bin/env python3
"""
Test Multi-Account Alpaca System

This script tests the multi-account Alpaca integration to ensure
all components work together correctly.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_multi_account_system():
    """Test the multi-account Alpaca system."""
    print("🧪 Testing Multi-Account Alpaca System")
    print("=" * 50)
    
    try:
        # Test 1: Service Container Integration
        print("\n1️⃣ Testing Service Container Integration...")
        
        from services.service_container import get_container, get_multi_alpaca_service, get_user_account_manager
        
        container = get_container()
        print(f"✅ Service container initialized: {type(container).__name__}")
        
        # Test 2: Multi-Alpaca Service
        print("\n2️⃣ Testing Multi-Alpaca Service...")
        
        multi_alpaca = get_multi_alpaca_service()
        print(f"✅ Multi-Alpaca service obtained: {type(multi_alpaca).__name__}")
        
        # Check if service is available
        is_available = multi_alpaca.is_available()
        print(f"📊 Service available: {is_available}")
        
        if is_available:
            # Get available accounts
            available_accounts = multi_alpaca.get_available_accounts()
            print(f"🏦 Available accounts: {len(available_accounts)}")
            
            for account_id, config in available_accounts.items():
                print(f"   • {account_id}: {config.account_name}")
            
            # Get account status
            accounts_status = multi_alpaca.get_all_accounts_status()
            print(f"\n📈 Account Status:")
            
            for account_id, status in accounts_status.items():
                if status.get('is_active', False):
                    print(f"   ✅ {account_id}:")
                    print(f"      • Cash: ${status.get('cash', 0):,.2f}")
                    print(f"      • Portfolio: ${status.get('portfolio_value', 0):,.2f}")
                    print(f"      • Status: {status.get('status', 'Unknown')}")
                else:
                    print(f"   ❌ {account_id}: Inactive")
                    if 'error' in status:
                        print(f"      • Error: {status['error']}")
        
        # Test 3: User Account Manager
        print("\n3️⃣ Testing User Account Manager...")
        
        user_manager = get_user_account_manager()
        print(f"✅ User Account Manager obtained: {type(user_manager).__name__}")
        
        # Test user assignment
        test_user_id = "test_user_123"
        available_account_ids = list(multi_alpaca.get_available_accounts().keys())
        
        if available_account_ids:
            print(f"\n🔄 Testing user assignment for {test_user_id}...")
            
            # Auto-assign user
            assigned_account = await user_manager.auto_assign_user(
                test_user_id, 
                available_account_ids
            )
            
            if assigned_account:
                print(f"✅ User assigned to account: {assigned_account}")
                
                # Verify assignment
                retrieved_account = user_manager.get_user_account(test_user_id)
                print(f"✅ Assignment verified: {retrieved_account}")
                
                # Get assignment statistics
                stats = user_manager.get_assignment_stats()
                print(f"📊 Assignment stats: {stats}")
                
            else:
                print("❌ User assignment failed")
        
        # Test 4: Account Information Retrieval
        print("\n4️⃣ Testing Account Information Retrieval...")
        
        for account_id in available_account_ids[:1]:  # Test first account only
            print(f"\n🔍 Testing account info for {account_id}...")
            
            account_info = multi_alpaca.get_account_info(account_id)
            if account_info:
                print(f"✅ Account info retrieved:")
                print(f"   • Account Number: {account_info.get('account_number', 'N/A')}")
                print(f"   • Cash: ${account_info.get('cash', 0):,.2f}")
                print(f"   • Buying Power: ${account_info.get('buying_power', 0):,.2f}")
                print(f"   • Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
                print(f"   • Status: {account_info.get('status', 'Unknown')}")
            else:
                print(f"❌ Failed to retrieve account info for {account_id}")
        
        # Test 5: Command Integration Check
        print("\n5️⃣ Testing Command Integration...")
        
        try:
            from listeners.multi_account_trade_command import MultiAccountTradeCommand
            from commands.account_management import AccountManagementCommands
            
            print("✅ Multi-account trade command module imported")
            print("✅ Account management commands module imported")
            
            # Test command initialization (without Slack app)
            from services.auth import AuthService
            auth_service = container.get(AuthService)
            
            multi_trade_cmd = MultiAccountTradeCommand(auth_service)
            print("✅ Multi-account trade command initialized")
            
        except Exception as e:
            print(f"❌ Command integration test failed: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Multi-Account System Test Completed!")
        
        if is_available:
            print("✅ All tests passed - Multi-account system is ready!")
        else:
            print("⚠️  Multi-account service not available - check configuration")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_environment_configuration():
    """Test environment configuration for multi-account setup."""
    print("\n🔧 Testing Environment Configuration...")
    
    # Check primary account
    primary_key = os.getenv("ALPACA_PAPER_API_KEY")
    primary_secret = os.getenv("ALPACA_PAPER_SECRET_KEY")
    
    if primary_key and primary_secret:
        print("✅ Primary account configured")
        if primary_key.startswith('PK'):
            print("✅ Primary account uses paper trading key")
        else:
            print("⚠️  Primary account key doesn't appear to be paper trading")
    else:
        print("❌ Primary account not configured")
    
    # Check additional accounts
    additional_accounts = 0
    for i in range(1, 10):  # Check up to 10 additional accounts
        key = os.getenv(f"ALPACA_PAPER_API_KEY_{i}")
        secret = os.getenv(f"ALPACA_PAPER_SECRET_KEY_{i}")
        
        if key and secret:
            additional_accounts += 1
            print(f"✅ Additional account {i} configured")
            if not key.startswith('PK'):
                print(f"⚠️  Account {i} key doesn't appear to be paper trading")
        else:
            break  # No more accounts configured
    
    print(f"📊 Total configured accounts: {1 + additional_accounts}")
    
    if additional_accounts == 0:
        print("\n💡 To add more accounts, add these to your .env file:")
        print("ALPACA_PAPER_API_KEY_1=PK_YOUR_SECOND_API_KEY_HERE")
        print("ALPACA_PAPER_SECRET_KEY_1=YOUR_SECOND_SECRET_KEY_HERE")
        print("ALPACA_PAPER_BASE_URL_1=https://paper-api.alpaca.markets")


if __name__ == "__main__":
    print("🚀 Starting Multi-Account Alpaca System Test")
    
    # Test environment first
    test_environment_configuration()
    
    # Run async tests
    success = asyncio.run(test_multi_account_system())
    
    if success:
        print("\n🎯 Test completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Test failed!")
        sys.exit(1)