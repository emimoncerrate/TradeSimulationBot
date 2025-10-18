#!/usr/bin/env python3
"""
Check Slack Users in Database

This script queries the database to show all Slack user IDs currently stored.
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
logging.basicConfig(level=logging.WARNING)  # Reduce log noise
logger = logging.getLogger(__name__)


async def check_slack_users():
    """Check all Slack users in the database."""
    print("🔍 Checking Slack Users in Database")
    print("=" * 50)
    
    try:
        # Get database service
        from services.service_container import get_container
        from services.database import DatabaseService
        from models.user import UserRole
        
        container = get_container()
        db_service = container.get(DatabaseService)
        
        print(f"✅ Database service connected")
        
        # Check if we're in mock mode
        if hasattr(db_service, 'is_mock_mode') and db_service.is_mock_mode:
            print("🧪 Database is in MOCK MODE")
            
            # Get mock users
            if hasattr(db_service, 'mock_data') and 'users' in db_service.mock_data:
                mock_users = db_service.mock_data['users']
                print(f"📊 Found {len(mock_users)} users in mock data:")
                
                for user_id, user in mock_users.items():
                    print(f"\n👤 User: {user_id}")
                    print(f"   Slack ID: {getattr(user, 'slack_user_id', 'N/A')}")
                    print(f"   Username: {getattr(user, 'username', 'N/A')}")
                    print(f"   Display Name: {getattr(user, 'profile', {}).get('display_name', 'N/A') if hasattr(user, 'profile') else 'N/A'}")
                    print(f"   Role: {getattr(user, 'role', 'N/A')}")
                    print(f"   Status: {getattr(user, 'status', 'N/A')}")
            else:
                print("📭 No mock users found")
        
        else:
            print("🗄️  Database is in LIVE MODE")
            
            # Try to get users by different roles
            print("\n🔍 Searching for users by role...")
            
            total_users = 0
            all_slack_ids = set()
            
            for role in UserRole:
                try:
                    users = await db_service.get_users_by_role(role)
                    if users:
                        print(f"\n📋 {role.value} users ({len(users)}):")
                        for user in users:
                            total_users += 1
                            slack_id = getattr(user, 'slack_user_id', 'N/A')
                            all_slack_ids.add(slack_id)
                            
                            print(f"   👤 {getattr(user, 'username', 'Unknown')}")
                            print(f"      Slack ID: {slack_id}")
                            print(f"      User ID: {getattr(user, 'user_id', 'N/A')}")
                            print(f"      Status: {getattr(user, 'status', 'N/A')}")
                except Exception as e:
                    print(f"   ❌ Error getting {role.value} users: {e}")
            
            print(f"\n📊 SUMMARY:")
            print(f"   Total users found: {total_users}")
            print(f"   Unique Slack IDs: {len(all_slack_ids)}")
            
            if all_slack_ids:
                print(f"\n📋 All Slack User IDs:")
                for slack_id in sorted(all_slack_ids):
                    if slack_id != 'N/A':
                        print(f"   • {slack_id}")
        
        # Check for any recent trades to find active users
        print(f"\n📈 Checking recent trading activity...")
        
        try:
            # Try to find users from recent trades
            # This is a bit of a hack since we don't have a direct "get all users" method
            
            # Check if there are any methods to get recent activity
            if hasattr(db_service, 'mock_data') and db_service.is_mock_mode:
                trades = db_service.mock_data.get('trades', {})
                if trades:
                    trader_ids = set()
                    for trade_key, trade in trades.items():
                        if hasattr(trade, 'user_id'):
                            trader_ids.add(trade.user_id)
                    
                    print(f"📊 Found {len(trader_ids)} unique trader IDs:")
                    for trader_id in sorted(trader_ids):
                        print(f"   • {trader_id}")
                        
                        # Try to get user details
                        try:
                            user = await db_service.get_user(trader_id)
                            if user:
                                print(f"     Slack ID: {getattr(user, 'slack_user_id', 'N/A')}")
                        except:
                            pass
                else:
                    print("📭 No trading activity found")
            else:
                print("🔍 Live database - cannot easily scan all trades")
        
        except Exception as e:
            print(f"❌ Error checking trading activity: {e}")
        
        # Check multi-account assignments
        print(f"\n🏦 Checking multi-account assignments...")
        
        try:
            from services.service_container import get_user_account_manager
            user_manager = get_user_account_manager()
            
            stats = user_manager.get_assignment_stats()
            print(f"📊 Assignment Statistics:")
            print(f"   Total assignments: {stats['total_assignments']}")
            print(f"   Accounts in use: {stats['accounts_in_use']}")
            print(f"   Assignment strategy: {stats['assignment_strategy']}")
            
            if stats['account_distribution']:
                print(f"   Account distribution:")
                for account_id, count in stats['account_distribution'].items():
                    print(f"     • {account_id}: {count} users")
                    
                    # Get users for this account
                    users = user_manager.get_account_users(account_id)
                    if users:
                        print(f"       Users: {', '.join(users)}")
            
        except Exception as e:
            print(f"❌ Error checking multi-account assignments: {e}")
        
        print(f"\n" + "=" * 50)
        print("💡 NEXT STEPS:")
        print("1. If no users found, they will be created when users first interact")
        print("2. Users are created automatically when they run /trade or other commands")
        print("3. Use /my-account in Slack to trigger user creation and account assignment")
        print("4. Use /account-users to see current user assignments")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_slack_users())