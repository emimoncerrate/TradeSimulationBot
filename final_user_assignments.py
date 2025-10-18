#!/usr/bin/env python3
"""
Final User Assignments

This script sets up the final user assignments as requested:
- Primary: Maurice, Kelvin
- Account_1: Emily, Brandon, Ethan, Josue
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


async def final_user_assignments():
    """Set up final user assignments."""
    print("🏦 Setting Up Final User Assignments")
    print("=" * 60)
    
    try:
        # Get services
        from services.service_container import get_container, get_multi_alpaca_service, get_user_account_manager
        
        container = get_container()
        multi_alpaca = get_multi_alpaca_service()
        user_manager = get_user_account_manager()
        
        print(f"✅ Services initialized")
        
        # Final assignments as requested
        final_assignments = {
            # Primary Account: Maurice, Kelvin
            "primary": [
                {"slack_id": "U08GVND66H4", "name": "Maurice Dixon"},
                {"slack_id": "U08GVN6F4FQ", "name": "Kelvin Saldana (you)"}
            ],
            # Account 1: Emily, Brandon, Ethan, Josue
            "account_1": [
                {"slack_id": "U08GVN8R7M4", "name": "Emily Moncerrate"},
                {"slack_id": "U08GVNAPX3Q", "name": "Brandon Jackson"},
                {"slack_id": "U08GVNDCQ14", "name": "Ethan Davey"},
                {"slack_id": "U08GVN46BRC", "name": "Josue Villalona"}
            ]
        }
        
        print(f"\n📋 Final Assignment Plan:")
        for account_id, users in final_assignments.items():
            print(f"\n🏦 {account_id.upper()}:")
            for user in users:
                print(f"   • {user['name']} ({user['slack_id']})")
        
        print(f"\n🚀 Assigning all users...")
        
        # Perform assignments
        total_assigned = 0
        
        for account_id, users in final_assignments.items():
            print(f"\n🏦 Assigning users to {account_id}...")
            
            for user in users:
                slack_id = user["slack_id"]
                name = user["name"]
                
                try:
                    # Check current assignment
                    current_account = user_manager.get_user_account(slack_id)
                    
                    if current_account == account_id:
                        print(f"   ✅ {name} already assigned to {account_id}")
                        total_assigned += 1
                    else:
                        # Assign/reassign user to account
                        if current_account:
                            # Reassign
                            success = await user_manager.reassign_user(
                                user_id=slack_id,
                                new_account_id=account_id,
                                assigned_by="admin_script",
                                reason=f"final_assignment_to_{account_id}"
                            )
                        else:
                            # New assignment
                            success = await user_manager.assign_user_to_account(
                                user_id=slack_id,
                                account_id=account_id,
                                assigned_by="admin_script",
                                reason=f"final_assignment_to_{account_id}"
                            )
                        
                        if success:
                            print(f"   ✅ {name} → {account_id}")
                            total_assigned += 1
                        else:
                            print(f"   ❌ Failed to assign {name} to {account_id}")
                        
                except Exception as e:
                    print(f"   ❌ Error assigning {name}: {e}")
        
        print(f"\n📊 Assignment Summary:")
        print(f"   Total users assigned: {total_assigned}")
        
        # Show final assignment statistics
        stats = user_manager.get_assignment_stats()
        print(f"\n📈 Final Statistics:")
        print(f"   Total assignments: {stats['total_assignments']}")
        print(f"   Accounts in use: {stats['accounts_in_use']}")
        
        if stats['account_distribution']:
            print(f"\n🏦 Final Account Distribution:")
            for account_id, count in stats['account_distribution'].items():
                print(f"   • {account_id}: {count} users")
                
                # Get users for this account and map to names
                users = user_manager.get_account_users(account_id)
                if users:
                    name_mapping = {
                        "U08GVN8R7M4": "Emily Moncerrate",
                        "U08GVNAPX3Q": "Brandon Jackson", 
                        "U08GVND66H4": "Maurice Dixon",
                        "U08GVN6F4FQ": "Kelvin Saldana",
                        "U08GVNDCQ14": "Ethan Davey",
                        "U08GVN46BRC": "Josue Villalona"
                    }
                    
                    user_names = [name_mapping.get(user_id, user_id) for user_id in users]
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
        print("🎉 FINAL ASSIGNMENTS COMPLETED!")
        print("=" * 60)
        
        print(f"✅ Final account assignments:")
        print(f"   🏦 PRIMARY (2 users): Maurice Dixon, Kelvin Saldana")
        print(f"   🏦 ACCOUNT_1 (4 users): Emily Moncerrate, Brandon Jackson, Ethan Davey, Josue Villalona")
        
        print(f"\n💡 Next Steps:")
        print(f"1. 🔄 Restart your Slack app to activate multi-account system")
        print(f"2. 📱 Have users test with: /my-account")
        print(f"3. 📊 Check assignments with: /account-users")
        print(f"4. 💹 Test enhanced trading with: /trade AAPL")
        
        print(f"\n🎯 All users will now see their assigned account info in trade modals!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(final_user_assignments())