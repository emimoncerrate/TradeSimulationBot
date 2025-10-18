#!/usr/bin/env python3
"""
Reassign Emily and Brandon to Account 1

This script moves Emily and Brandon from Primary to Account 1.
"""

import os
import sys
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reassign_users():
    """Reassign Emily and Brandon to Account 1."""
    print("🔄 Reassigning Emily and Brandon to Account 1")
    print("=" * 60)
    
    try:
        # Get services
        from services.service_container import get_container, get_multi_alpaca_service, get_user_account_manager
        
        container = get_container()
        multi_alpaca = get_multi_alpaca_service()
        user_manager = get_user_account_manager()
        
        print(f"✅ Services initialized")
        
        # Users to reassign
        users_to_reassign = [
            {"slack_id": "U08GVN8R7M4", "name": "Emily Moncerrate"},
            {"slack_id": "U08GVNAPX3Q", "name": "Brandon Jackson"}
        ]
        
        print(f"\n📋 Current Assignment Status:")
        
        # Show current assignments
        for user in users_to_reassign:
            current_account = user_manager.get_user_account(user["slack_id"])
            print(f"   • {user['name']}: {current_account}")
        
        print(f"\n🔄 Reassigning users to account_1...")
        
        # Reassign users
        for user in users_to_reassign:
            slack_id = user["slack_id"]
            name = user["name"]
            
            try:
                # Reassign user to account_1
                success = await user_manager.reassign_user(
                    user_id=slack_id,
                    new_account_id="account_1",
                    assigned_by="admin_script",
                    reason="moved_to_account_1_per_admin_request"
                )
                
                if success:
                    print(f"   ✅ {name} → account_1")
                else:
                    print(f"   ❌ Failed to reassign {name}")
                    
            except Exception as e:
                print(f"   ❌ Error reassigning {name}: {e}")
        
        # Show final assignment statistics
        print(f"\n📊 Final Assignment Status:")
        
        stats = user_manager.get_assignment_stats()
        print(f"   Total assignments: {stats['total_assignments']}")
        print(f"   Accounts in use: {stats['accounts_in_use']}")
        
        if stats['account_distribution']:
            print(f"\n🏦 Updated Account Distribution:")
            for account_id, count in stats['account_distribution'].items():
                print(f"   • {account_id}: {count} users")
                
                # Get users for this account
                users = user_manager.get_account_users(account_id)
                if users:
                    # Map Slack IDs to names
                    user_names = []
                    name_mapping = {
                        "U08GVN8R7M4": "Emily Moncerrate",
                        "U08GVNAPX3Q": "Brandon Jackson", 
                        "U08GVND66H4": "Maurice Dixon",
                        "U08GVN6F4FQ": "Kelvin Saldana",
                        "U08GVNDCQ14": "Ethan Davey",
                        "U08GVN46BRC": "Josue Villalona"
                    }
                    
                    for user_id in users:
                        name = name_mapping.get(user_id, user_id)
                        user_names.append(name)
                    
                    print(f"     Users: {', '.join(user_names)}")
        
        # Get account information
        print(f"\n💰 Account Information:")
        
        available_accounts = multi_alpaca.get_available_accounts()
        for account_id in available_accounts.keys():
            account_info = multi_alpaca.get_account_info(account_id)
            if account_info:
                users_in_account = user_manager.get_account_users(account_id)
                print(f"\n🏦 {account_id.upper()} ({len(users_in_account)} users):")
                print(f"   • Account: {account_info['account_name']}")
                print(f"   • Cash: ${account_info['cash']:,.2f}")
                print(f"   • Portfolio: ${account_info['portfolio_value']:,.2f}")
                print(f"   • Buying Power: ${account_info['buying_power']:,.2f}")
                print(f"   • Status: {account_info['status']}")
        
        print(f"\n" + "=" * 60)
        print("🎉 REASSIGNMENT COMPLETED!")
        print("=" * 60)
        
        print(f"✅ New account assignments:")
        print(f"   🏦 PRIMARY: Maurice Dixon, Kelvin Saldana")
        print(f"   🏦 ACCOUNT_1: Emily Moncerrate, Brandon Jackson, Ethan Davey, Josue Villalona")
        
        print(f"\n💡 Next Steps:")
        print(f"1. 🔄 Restart your Slack app if it's running")
        print(f"2. 📱 Have Emily and Brandon test with: /my-account")
        print(f"3. 📊 Verify assignments with: /account-users")
        print(f"4. 💹 Test trading with: /trade AAPL")
        
        print(f"\n🎯 Emily and Brandon will now see Account_1 info in their trade modals!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(reassign_users())