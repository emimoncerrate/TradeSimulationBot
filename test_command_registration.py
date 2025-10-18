#!/usr/bin/env python3
"""
Test Command Registration

This script tests whether the multi-account commands are being registered correctly.
"""

import os
import sys
import logging

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


def test_command_registration():
    """Test the command registration logic."""
    print("🧪 Testing Command Registration Logic")
    print("=" * 50)
    
    try:
        # Test 1: Service Container
        print("\n1️⃣ Testing Service Container...")
        from services.service_container import get_container
        container = get_container()
        print(f"✅ Service container obtained: {type(container).__name__}")
        
        # Test 2: Multi-Account Services
        print("\n2️⃣ Testing Multi-Account Services...")
        
        try:
            from services.multi_alpaca_service import MultiAlpacaService
            from services.user_account_manager import UserAccountManager
            print("✅ Multi-account modules imported successfully")
            
            # Try to get services from container
            try:
                multi_alpaca = container.get(MultiAlpacaService)
                user_manager = container.get(UserAccountManager)
                print("✅ Multi-account services obtained from container")
                
                # Check availability
                is_available = multi_alpaca.is_available()
                print(f"📊 Multi-Alpaca service available: {is_available}")
                
                if is_available:
                    accounts = multi_alpaca.get_available_accounts()
                    print(f"🏦 Available accounts: {len(accounts)}")
                    for account_id, config in accounts.items():
                        print(f"   • {account_id}: {config.account_name}")
                
            except Exception as service_error:
                print(f"❌ Services not in container: {service_error}")
                return False
                
        except ImportError as import_error:
            print(f"❌ Multi-account modules not available: {import_error}")
            return False
        
        # Test 3: Command Registration Logic
        print("\n3️⃣ Testing Command Registration Logic...")
        
        # Simulate the registration logic from commands.py
        multi_account_available = False
        
        try:
            # Check if multi-account services can be imported
            from services.multi_alpaca_service import MultiAlpacaService
            from services.user_account_manager import UserAccountManager
            
            # Try to get the services from container
            try:
                multi_alpaca = container.get(MultiAlpacaService)
                user_manager = container.get(UserAccountManager)
                
                # Check if the multi-alpaca service is available
                if multi_alpaca.is_available():
                    multi_account_available = True
                    print("✅ Multi-account system detected and available")
                else:
                    print("📊 Multi-account services loaded but no accounts available")
                    
            except Exception as service_error:
                print(f"📋 Multi-account services not in container: {service_error}")
                
        except ImportError as import_error:
            print(f"📦 Multi-account modules not available: {import_error}")
        except Exception as e:
            print(f"❌ Error checking multi-account system: {e}")
        
        print(f"\n🎯 Multi-account available: {multi_account_available}")
        
        if multi_account_available:
            print("✅ Should register multi-account commands")
            
            # Test command imports
            try:
                from listeners.multi_account_trade_command import register_multi_account_trade_command
                from commands.account_management import register_account_management_commands
                print("✅ Multi-account command modules imported successfully")
                
            except Exception as e:
                print(f"❌ Failed to import multi-account command modules: {e}")
                return False
        else:
            print("📝 Should register single-account commands")
        
        print("\n" + "=" * 50)
        print("🎉 Command Registration Test Completed!")
        
        return multi_account_available
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Command Registration Test")
    
    success = test_command_registration()
    
    if success:
        print("\n🎯 Multi-account commands should be registered!")
        print("\n💡 If you're still seeing the old form, restart the Slack app:")
        print("   1. Stop the current app process")
        print("   2. Run: python app.py")
        print("   3. Look for 'Multi-account commands registered successfully' in logs")
    else:
        print("\n⚠️  Multi-account system not available - single account mode will be used")
    
    sys.exit(0 if success else 1)