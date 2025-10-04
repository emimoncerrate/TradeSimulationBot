#!/usr/bin/env python3
"""
Simple startup script for the Slack Trading Bot with minimal dependencies.
"""

import os
import sys
import logging
from datetime import datetime

# Set up environment for development
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG_MODE'] = 'true'
os.environ['MOCK_EXECUTION_ENABLED'] = 'true'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_minimal_slack_app():
    """Create a minimal Slack app for testing."""
    from slack_bolt import App
    
    # Get credentials
    token = os.getenv('SLACK_BOT_TOKEN')
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    
    if not token or not signing_secret:
        print("❌ Missing Slack credentials")
        return None
    
    print(f"🔑 Using token: {token[:20]}...")
    print(f"🔐 Using secret: {signing_secret[:10]}...")
    
    # Create minimal app (disable OAuth to use direct bot token)
    app = App(
        token=token,
        signing_secret=signing_secret,
        process_before_response=True,
        # Disable OAuth installation flow - use direct bot token
        installation_store=None,
        oauth_settings=None
    )
    
    # Add a simple command handler
    @app.command("/hello")
    def handle_hello_command(ack, respond, command):
        ack()
        respond(f"Hello <@{command['user_id']}>! 👋 The trading bot is running!")
    
    # Add a simple message handler
    @app.message("hello")
    def handle_hello_message(message, say):
        say(f"Hello <@{message['user']}>! 🤖 Trading bot is online!")
    
    # Add app mention handler
    @app.event("app_mention")
    def handle_app_mention(event, say):
        say(f"Hi <@{event['user']}>! I'm the trading bot. Try `/hello` to test me!")
    
    return app

def main():
    """Main function."""
    print("🚀 Starting Simple Slack Trading Bot")
    print("=" * 50)
    print(f"📅 Start time: {datetime.now()}")
    print(f"🔧 Environment: {os.getenv('ENVIRONMENT')}")
    print("=" * 50)
    
    try:
        # Create minimal Slack app
        app = create_minimal_slack_app()
        
        if not app:
            print("❌ Failed to create Slack app")
            return 1
        
        print("✅ Slack app created successfully")
        print("🎯 Available commands:")
        print("   - /hello - Test command")
        print("   - @tradingsimulator hello - Test mention")
        print("   - Type 'hello' in a channel with the bot")
        
        # Start the app
        print("\n🚀 Starting Slack app...")
        print("📡 Bot is now listening for events...")
        print("🛑 Press Ctrl+C to stop")
        
        # Start in Socket Mode (much easier!)
        app_token = os.getenv('SLACK_APP_TOKEN')
        if app_token:
            print("🔌 Starting in Socket Mode...")
            print("✨ No ngrok needed - direct connection to Slack!")
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            handler = SocketModeHandler(app, app_token)
            handler.start()
        else:
            print("⚠️  No SLACK_APP_TOKEN found, starting HTTP server...")
            app.start(port=int(os.environ.get("PORT", 3000)))
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())