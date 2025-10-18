#!/usr/bin/env python3
"""
Get Detailed User Information

This script gets detailed information about users including names, usernames, and profiles.
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


async def get_user_details():
    """Get detailed user information."""
    print("👥 Getting Detailed User Information")
    print("=" * 60)
    
    try:
        # Get database service
        from services.service_container import get_container
        from services.database import DatabaseService
        
        container = get_container()
        db_service = container.get(DatabaseService)
        
        # Known Slack user IDs from previous check
        slack_user_ids = [
            "U08GVN46BRC",
            "U08GVN6F4FQ", 
            "U08GVN8R7M4",
            "U08GVNAPX3Q",
            "U08GVND66H4",
            "U08GVNDCQ14"
        ]
        
        print(f"🔍 Checking details for {len(slack_user_ids)} users...")
        
        for i, slack_id in enumerate(slack_user_ids, 1):
            print(f"\n{i}. 👤 Slack ID: {slack_id}")
            
            try:
                # Get user by Slack ID
                user = await db_service.get_user_by_slack_id(slack_id)
                
                if user:
                    print(f"   ✅ User found in database:")
                    print(f"   📋 User ID: {getattr(user, 'user_id', 'N/A')}")
                    print(f"   👤 Username: {getattr(user, 'username', 'N/A')}")
                    print(f"   📧 Email: {getattr(user, 'email', 'N/A')}")
                    print(f"   🎭 Role: {getattr(user, 'role', 'N/A')}")
                    print(f"   📊 Status: {getattr(user, 'status', 'N/A')}")
                    print(f"   📅 Created: {getattr(user, 'created_at', 'N/A')}")
                    print(f"   🔄 Updated: {getattr(user, 'updated_at', 'N/A')}")
                    
                    # Check if user has a profile
                    if hasattr(user, 'profile') and user.profile:
                        profile = user.profile
                        print(f"   👤 Profile Information:")
                        print(f"      Display Name: {getattr(profile, 'display_name', 'N/A')}")
                        print(f"      First Name: {getattr(profile, 'first_name', 'N/A')}")
                        print(f"      Last Name: {getattr(profile, 'last_name', 'N/A')}")
                        print(f"      Department: {getattr(profile, 'department', 'N/A')}")
                        print(f"      Title: {getattr(profile, 'title', 'N/A')}")
                        print(f"      Phone: {getattr(profile, 'phone', 'N/A')}")
                        print(f"      Timezone: {getattr(profile, 'timezone', 'N/A')}")
                    else:
                        print(f"   📝 No profile information available")
                    
                    # Check permissions
                    if hasattr(user, 'permissions') and user.permissions:
                        print(f"   🔐 Permissions: {', '.join([p.value for p in user.permissions])}")
                    else:
                        print(f"   🔐 No specific permissions set")
                    
                    # Check portfolio manager
                    if hasattr(user, 'portfolio_manager_id') and user.portfolio_manager_id:
                        print(f"   💼 Portfolio Manager ID: {user.portfolio_manager_id}")
                    
                else:
                    print(f"   ❌ User not found in database")
                    
            except Exception as e:
                print(f"   ❌ Error getting user details: {e}")
        
        # Try to get names from Slack API if available
        print(f"\n" + "=" * 60)
        print("🔍 Attempting to get names from Slack API...")
        
        try:
            # Check if we have Slack credentials
            slack_token = os.getenv('SLACK_BOT_TOKEN')
            
            if slack_token:
                print(f"✅ Slack bot token found")
                
                # Try to import Slack client
                try:
                    from slack_sdk import WebClient
                    from slack_sdk.errors import SlackApiError
                    
                    client = WebClient(token=slack_token)
                    
                    print(f"🔍 Fetching user info from Slack API...")
                    
                    for i, slack_id in enumerate(slack_user_ids, 1):
                        try:
                            # Get user info from Slack
                            response = client.users_info(user=slack_id)
                            
                            if response["ok"]:
                                user_info = response["user"]
                                profile = user_info.get("profile", {})
                                
                                print(f"\n{i}. 👤 Slack ID: {slack_id}")
                                print(f"   📛 Real Name: {profile.get('real_name', 'N/A')}")
                                print(f"   👤 Display Name: {profile.get('display_name', 'N/A')}")
                                print(f"   🏷️  Username: {user_info.get('name', 'N/A')}")
                                print(f"   📧 Email: {profile.get('email', 'N/A')}")
                                print(f"   📱 Phone: {profile.get('phone', 'N/A')}")
                                print(f"   🏢 Title: {profile.get('title', 'N/A')}")
                                print(f"   🌍 Timezone: {user_info.get('tz_label', 'N/A')}")
                                print(f"   🔄 Status: {'Active' if not user_info.get('deleted', False) else 'Deleted'}")
                                
                                # Check if user is admin
                                if user_info.get('is_admin', False):
                                    print(f"   👑 Admin: Yes")
                                if user_info.get('is_owner', False):
                                    print(f"   👑 Owner: Yes")
                                    
                            else:
                                print(f"\n{i}. ❌ Slack ID: {slack_id} - Could not fetch info")
                                
                        except SlackApiError as e:
                            print(f"\n{i}. ❌ Slack ID: {slack_id} - API Error: {e.response['error']}")
                        except Exception as e:
                            print(f"\n{i}. ❌ Slack ID: {slack_id} - Error: {e}")
                    
                except ImportError:
                    print(f"❌ Slack SDK not available")
                except Exception as e:
                    print(f"❌ Error setting up Slack client: {e}")
            else:
                print(f"❌ No Slack bot token found in environment")
                
        except Exception as e:
            print(f"❌ Error accessing Slack API: {e}")
        
        print(f"\n" + "=" * 60)
        print("📋 SUMMARY")
        print("=" * 60)
        print("The users above are ready for the multi-account system.")
        print("When they use the new /trade command, they'll be automatically")
        print("assigned to different Alpaca accounts for better isolation.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(get_user_details())