#!/usr/bin/env python3
"""
Configuration Test Script for Slack Trading Bot
Tests if all required environment variables are properly configured.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def test_config():
    """Test all required configuration variables."""
    
    print("=" * 70)
    print("🔍 Environment Configuration Test")
    print("=" * 70)
    print()
    
    errors = []
    warnings = []
    success = []
    
    # Test Slack Bot Token
    slack_bot_token = os.getenv('SLACK_BOT_TOKEN', '')
    if not slack_bot_token:
        errors.append("❌ SLACK_BOT_TOKEN is not set")
    elif not slack_bot_token.startswith('xoxb-'):
        errors.append("❌ SLACK_BOT_TOKEN must start with 'xoxb-'")
    elif slack_bot_token == 'xoxb-your-bot-token-here':
        errors.append("❌ SLACK_BOT_TOKEN is still set to placeholder value")
    elif len(slack_bot_token) < 20:
        errors.append("❌ SLACK_BOT_TOKEN appears to be too short")
    else:
        success.append(f"✅ SLACK_BOT_TOKEN is set (length: {len(slack_bot_token)})")
    
    # Test Slack Signing Secret
    signing_secret = os.getenv('SLACK_SIGNING_SECRET', '')
    if not signing_secret:
        errors.append("❌ SLACK_SIGNING_SECRET is not set")
    elif signing_secret == 'your-signing-secret-here':
        errors.append("❌ SLACK_SIGNING_SECRET is still set to placeholder value")
    elif len(signing_secret) < 32:
        errors.append(f"❌ SLACK_SIGNING_SECRET is too short (length: {len(signing_secret)}, needs: 32+)")
    else:
        success.append(f"✅ SLACK_SIGNING_SECRET is set (length: {len(signing_secret)})")
    
    # Test Slack App Token (optional for Socket Mode)
    app_token = os.getenv('SLACK_APP_TOKEN', '')
    if app_token and app_token != 'xapp-your-app-token-here':
        if app_token.startswith('xapp-'):
            success.append(f"✅ SLACK_APP_TOKEN is set (length: {len(app_token)}) - Socket Mode enabled")
        else:
            warnings.append("⚠️  SLACK_APP_TOKEN should start with 'xapp-'")
    else:
        warnings.append("⚠️  SLACK_APP_TOKEN not set (Socket Mode disabled, will use HTTP mode)")
    
    # Test Finnhub API Key
    finnhub_key = os.getenv('FINNHUB_API_KEY', '')
    if not finnhub_key:
        errors.append("❌ FINNHUB_API_KEY is not set")
    elif finnhub_key == 'your-finnhub-api-key-here':
        errors.append("❌ FINNHUB_API_KEY is still set to placeholder value")
    elif len(finnhub_key) < 10:
        errors.append(f"❌ FINNHUB_API_KEY appears to be too short (length: {len(finnhub_key)})")
    else:
        success.append(f"✅ FINNHUB_API_KEY is set (length: {len(finnhub_key)})")
    
    # Test Environment
    environment = os.getenv('ENVIRONMENT', 'development')
    success.append(f"✅ ENVIRONMENT: {environment}")
    
    # Test AWS Configuration (optional for development)
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    success.append(f"✅ AWS_REGION: {aws_region}")
    
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
    if aws_access_key == 'mock-access-key-id' and environment == 'development':
        success.append("✅ AWS_ACCESS_KEY_ID: Using mock credentials (OK for development)")
    elif aws_access_key:
        success.append(f"✅ AWS_ACCESS_KEY_ID is set (length: {len(aws_access_key)})")
    
    # Test Trading Configuration
    mock_execution = os.getenv('MOCK_EXECUTION_ENABLED', 'true')
    success.append(f"✅ MOCK_EXECUTION_ENABLED: {mock_execution}")
    
    # Print results
    print("📊 Test Results:")
    print()
    
    if success:
        print("✅ Successful Configurations:")
        for msg in success:
            print(f"   {msg}")
        print()
    
    if warnings:
        print("⚠️  Warnings:")
        for msg in warnings:
            print(f"   {msg}")
        print()
    
    if errors:
        print("❌ Errors (Must Fix):")
        for msg in errors:
            print(f"   {msg}")
        print()
    
    print("=" * 70)
    
    # Summary
    if errors:
        print(f"❌ Configuration Test FAILED - {len(errors)} error(s) found")
        print()
        print("📝 Next Steps:")
        print("   1. Open your .env file")
        print("   2. Replace placeholder values with actual credentials")
        print("   3. Get Slack credentials from: https://api.slack.com/apps")
        print("   4. Get Finnhub API key from: https://finnhub.io/register")
        print("   5. Run this test again")
        print()
        return False
    elif warnings:
        print(f"⚠️  Configuration Test PASSED with {len(warnings)} warning(s)")
        print()
        print("✅ Your bot should work, but consider addressing the warnings above.")
        print()
        return True
    else:
        print("✅ Configuration Test PASSED - All required settings are configured!")
        print()
        print("🚀 You're ready to run: docker compose up --build")
        print()
        return True

if __name__ == "__main__":
    success = test_config()
    sys.exit(0 if success else 1)

