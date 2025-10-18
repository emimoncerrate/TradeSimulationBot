#!/usr/bin/env python3
"""
Assign Users to Specific Accounts

This script manually assigns users to specific Alpaca accounts as requested.
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


async def assign_users_to_accounts():
    """Assign users to specific accounts."""
    print("🏦 Assigning Users to Specific Accounts")
    print("=" * 60)
    
    try:
        # Get services
        from services.service_container import get_container, get_multi_alpaca_service, get_user_account_manager
        
        container = get_container()
        multi_alpaca = get_multi_alpaca_service()
        user_manager = get_user_account_manager()
        
        print(f"✅ Services initialized")
        
        # Check available accounts
        available_accounts = multi_alpaca.get_available_accounts()
        print(f"🏦 Available accounts: {list(available_accounts.keys())}")
        
        # Define user assignments as requested
        assignments = {
            # Primary Account: Emily, Brandon, Maurice, Kelvin (you)
            "primary": [
                {"slack_id": "U08GVN8R7M4", "name": "Emily Moncerrate"},
                {"slack_id": "U08GVNAPX3Q", "name": "Brandon Jackson"},
                {"slack_id": "U08GVND66H4", "name": "Maurice Dixon"},
                {"slack_id": "U08GVN6F4FQ", "name": "Kelvin Saldana (you)"}
            ],
            # Account 1: Ethan, Josue
            "account_1": [
                {"slack_id": "U08GVNDCQ14", "name": "Ethan Davey"},
                {"slack_id": "U08GVN46BRC", "name": "Josue Villalona"}
            ]
        }
        
        print(f"\n📋 Assignment Plan:")
        for account_id, users in assignments.items():
            print(f"\n🏦 {account_id.upper()}:")
            for user in users:
                print(f"   • {user['name']} ({user['slack_id']})")
        
        # Check if account_1 exists
        if "account_1" not in available_accounts:
            print(f"\n⚠️  WARNING: account_1 not available!")
            print(f"   Available accounts: {list(available_accounts.keys())}")
            print(f"   Make sure you have ALPACA_PAPER_API_KEY_1 in your .env file")
            
            # Ask if we should continue with just primary
            response = input(f"\n❓ Continue with just primary account assignments? (y/n): ")
            if response.lower() != 'y':
                print(f"❌ Aborted. Please add account_1 credentials to .env file first.")
                return
        
        print(f"\n🚀 Starting user assignments...")
        
        # Perform assignments
        total_assigned = 0
        
        for account_id, users in assignments.items():
            if account_id not in available_accounts:
                print(f"\n❌ Skipping {account_id} - not available")
                continue
                
            print(f"\n🏦 Assigning users to {account_id}...")
            
            for user in users:
                slack_id = user["slack_id"]
                name = user["name"]
                
                try:
                    # Assign user to account
                    success = await user_manager.assign_user_to_account(
                        user_id=slack_id,
                        account_id=account_id,
                        assigned_by="admin_script",
                        reason=f"manual_assignment_by_admin"
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
        print(f"   Assignment strategy: {stats['assignment_strategy']}")
        
        if stats['account_distribution']:
            print(f"\n🏦 Account Distribution:")
            for account_id, count in stats['account_distribution'].items():
                print(f"   • {account_id}: {count} users")
                
                # Get users for this account
                users = user_manager.get_account_users(account_id)
                if users:
                    print(f"     Users: {', '.join(users)}")
        
        # Get account information
        print(f"\n💰 Account Information:")
        
        for account_id in available_accounts.keys():
            if account_id in [acc for acc, users in assignments.items() if users]:
                account_info = multi_alpaca.get_account_info(account_id)
                if account_info:
                    print(f"\n🏦 {account_id.upper()}:")
                    print(f"   • Account: {account_info['account_name']}")
                    print(f"   • Cash: ${account_info['cash']:,.2f}")
                    print(f"   • Portfolio: ${account_info['portfolio_value']:,.2f}")
                    print(f"   • Buying Power: ${account_info['buying_power']:,.2f}")
                    print(f"   • Status: {account_info['status']}")
        
        print(f"\n" + "=" * 60)
        print("🎉 USER ASSIGNMENT COMPLETED!")
        print("=" * 60)
        
        print(f"✅ Users have been assigned to accounts as requested:")
        print(f"   🏦 PRIMARY: Emily, Brandon, Maurice, Kelvin")
        print(f"   🏦 ACCOUNT_1: Ethan, Josue")
        
        print(f"\n💡 Next Steps:")
        print(f"1. 🔄 Restart your Slack app if it's running")
        print(f"2. 📱 Have users test with: /my-account")
        print(f"3. 📊 Check assignments with: /account-users")
        print(f"4. 💹 Test trading with: /trade AAPL")
        
        print(f"\n🎯 Users will now see their assigned account info in trade modals!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(assign_users_to_accounts())