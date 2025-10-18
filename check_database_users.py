#!/usr/bin/env python3
"""
Check Database Users

This script queries the database to show all Slack user IDs and user information
currently stored in the system.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

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


async def check_database_users():
    """Check all users in the database."""
    print("🔍 Checking Database Users")
    print("=" * 60)
    
    try:
        # Get database service
        from services.service_container import get_container
        from services.database import DatabaseService
        
        container = get_container()
        db_service = container.get(DatabaseService)
        
        print(f"✅ Database service obtained: {type(db_service).__name__}")
        
        # Check if we can connect to the database
        try:
            # Try to list tables to verify connection
            tables = await db_service.list_tables()
            print(f"📊 Database connection successful")
            print(f"📋 Available tables: {', '.join(tables) if tables else 'None found'}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        print("\n" + "=" * 60)
        print("👥 USERS IN DATABASE")
        print("=" * 60)
        
        # Method 1: Try to get users directly if there's a get_all_users method
        try:
            if hasattr(db_service, 'get_all_users'):
                users = await db_service.get_all_users()
                if users:
                    print(f"📊 Found {len(users)} users:")
                    for i, user in enumerate(users, 1):
                        print(f"\n{i}. User ID: {user.get('user_id', 'N/A')}")
                        print(f"   Slack ID: {user.get('slack_user_id', 'N/A')}")
                        print(f"   Username: {user.get('username', 'N/A')}")
                        print(f"   Email: {user.get('email', 'N/A')}")
                        print(f"   Role: {user.get('role', 'N/A')}")
                        print(f"   Status: {user.get('status', 'N/A')}")
                        print(f"   Created: {user.get('created_at', 'N/A')}")
                else:
                    print("📭 No users found using get_all_users method")
            else:
                print("📋 get_all_users method not available")
        except Exception as e:
            print(f"⚠️  Error using get_all_users: {e}")
        
        # Method 2: Try to scan the users table directly
        try:
            print(f"\n🔍 Scanning users table directly...")
            
            # Try different possible table names
            possible_table_names = [
                'users',
                'jain-trading-bot-users',
                f"{os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')}-users"
            ]
            
            users_found = False
            
            for table_name in possible_table_names:
                try:
                    print(f"   Checking table: {table_name}")
                    
                    # Use the database service's DynamoDB client
                    if hasattr(db_service, 'dynamodb'):
                        table = db_service.dynamodb.Table(table_name)
                        response = table.scan(Limit=50)  # Limit to first 50 users
                        
                        items = response.get('Items', [])
                        if items:
                            users_found = True
                            print(f"✅ Found {len(items)} users in table '{table_name}':")
                            
                            for i, item in enumerate(items, 1):
                                print(f"\n{i}. Raw User Data:")
                                for key, value in item.items():
                                    print(f"   {key}: {value}")
                                print("   " + "-" * 40)
                            break
                        else:
                            print(f"   📭 Table '{table_name}' is empty")
                            
                except Exception as table_error:
                    print(f"   ❌ Error accessing table '{table_name}': {table_error}")
            
            if not users_found:
                print("📭 No users found in any table")
                
        except Exception as e:
            print(f"❌ Error scanning tables: {e}")
        
        # Method 3: Check for authentication/session data
        print(f"\n🔐 Checking for authentication data...")
        
        try:
            auth_table_names = [
                'auth_sessions',
                'sessions',
                'jain-trading-bot-sessions',
                f"{os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')}-sessions"
            ]
            
            for table_name in auth_table_names:
                try:
                    print(f"   Checking auth table: {table_name}")
                    
                    if hasattr(db_service, 'dynamodb'):
                        table = db_service.dynamodb.Table(table_name)
                        response = table.scan(Limit=20)
                        
                        items = response.get('Items', [])
                        if items:
                            print(f"✅ Found {len(items)} auth records in '{table_name}':")
                            
                            unique_users = set()
                            for item in items:
                                user_id = item.get('user_id') or item.get('slack_user_id')
                                if user_id:
                                    unique_users.add(user_id)
                            
                            print(f"   👥 Unique user IDs: {', '.join(sorted(unique_users))}")
                            break
                        else:
                            print(f"   📭 Auth table '{table_name}' is empty")
                            
                except Exception as table_error:
                    print(f"   ❌ Error accessing auth table '{table_name}': {table_error}")
                    
        except Exception as e:
            print(f"❌ Error checking auth data: {e}")
        
        # Method 4: Check trading history for user activity
        print(f"\n📈 Checking trading history for user activity...")
        
        try:
            trade_table_names = [
                'trades',
                'trading_history',
                'jain-trading-bot-trades',
                f"{os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')}-trades"
            ]
            
            for table_name in trade_table_names:
                try:
                    print(f"   Checking trades table: {table_name}")
                    
                    if hasattr(db_service, 'dynamodb'):
                        table = db_service.dynamodb.Table(table_name)
                        response = table.scan(Limit=20)
                        
                        items = response.get('Items', [])
                        if items:
                            print(f"✅ Found {len(items)} trade records in '{table_name}':")
                            
                            unique_users = set()
                            for item in items:
                                user_id = item.get('user_id') or item.get('slack_user_id') or item.get('trader_id')
                                if user_id:
                                    unique_users.add(user_id)
                            
                            if unique_users:
                                print(f"   👥 Active trader IDs: {', '.join(sorted(unique_users))}")
                            else:
                                print(f"   📊 No user IDs found in trade records")
                            break
                        else:
                            print(f"   📭 Trades table '{table_name}' is empty")
                            
                except Exception as table_error:
                    print(f"   ❌ Error accessing trades table '{table_name}': {table_error}")
                    
        except Exception as e:
            print(f"❌ Error checking trading history: {e}")
        
        print("\n" + "=" * 60)
        print("📋 SUMMARY")
        print("=" * 60)
        print("If no users were found, this could mean:")
        print("1. 🆕 This is a fresh installation with no users yet")
        print("2. 📊 Users are stored in a different table structure")
        print("3. 🔐 Database permissions or connection issues")
        print("4. 📝 Users are created on-demand when they first use commands")
        
        print(f"\n💡 To add users to the multi-account system:")
        print(f"   1. Have users run /trade or /my-account in Slack")
        print(f"   2. Users will be automatically assigned to accounts")
        print(f"   3. Use /account-users to see current assignments")
        
    except Exception as e:
        print(f"\n❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting Database User Check")
    
    # Run the async function
    asyncio.run(check_database_users())
    
    print(f"\n🎯 Database check completed!")