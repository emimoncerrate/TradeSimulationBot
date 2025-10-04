#!/usr/bin/env python3
"""
Test script to validate Slack token directly.
"""

import os
import requests

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_slack_token():
    """Test the Slack token directly with the API."""
    token = os.getenv('SLACK_BOT_TOKEN')
    
    if not token:
        print("❌ No SLACK_BOT_TOKEN found in environment")
        return False
    
    print(f"🔍 Testing token: {token[:20]}...")
    print(f"📏 Token length: {len(token)}")
    print(f"🔤 Token starts with: {token[:4]}")
    
    # Test with direct API call
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post('https://slack.com/api/auth.test', headers=headers)
        result = response.json()
        
        print(f"📡 API Response: {result}")
        
        if result.get('ok'):
            print("✅ Token is valid!")
            print(f"👤 Bot user: {result.get('user')}")
            print(f"🏢 Team: {result.get('team')}")
            return True
        else:
            print(f"❌ Token validation failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

def test_signing_secret():
    """Test the signing secret."""
    secret = os.getenv('SLACK_SIGNING_SECRET')
    
    if not secret:
        print("❌ No SLACK_SIGNING_SECRET found in environment")
        return False
    
    print(f"🔍 Testing signing secret: {secret[:10]}...")
    print(f"📏 Secret length: {len(secret)}")
    
    if len(secret) >= 32:
        print("✅ Signing secret length looks good")
        return True
    else:
        print("❌ Signing secret too short")
        return False

def main():
    print("🔐 Slack Credentials Test")
    print("=" * 30)
    
    token_valid = test_slack_token()
    print()
    secret_valid = test_signing_secret()
    
    print("\n" + "=" * 30)
    if token_valid and secret_valid:
        print("🎉 All credentials look good!")
    else:
        print("⚠️  Credential issues found. Please check your Slack app configuration.")
        print("\n💡 Troubleshooting steps:")
        print("1. Go to https://api.slack.com/apps")
        print("2. Select your app")
        print("3. Go to 'OAuth & Permissions' and copy the 'Bot User OAuth Token'")
        print("4. Go to 'Basic Information' and copy the 'Signing Secret'")
        print("5. Make sure the app is installed to your workspace")

if __name__ == "__main__":
    main()