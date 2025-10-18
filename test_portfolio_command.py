#!/usr/bin/env python3
"""
Test the portfolio command functionality
"""
import asyncio
import os
from dotenv import load_dotenv
from services.service_container import ServiceContainer
from listeners.commands import CommandHandler, CommandType, CommandContext
from datetime import datetime, timezone

async def test_portfolio_command():
    """Test the portfolio command functionality"""
    load_dotenv()
    
    print("🎯 Testing Portfolio Command")
    print("=" * 50)
    
    # Initialize services
    container = ServiceContainer()
    await container.startup()
    
    # Get services
    auth_service = container.get_service('AuthService')
    db_service = container.get_service('DatabaseService')
    
    # Create command handler
    command_handler = CommandHandler(auth_service, db_service)
    
    # Create a mock command context
    command_context = CommandContext(
        command_type=CommandType.PORTFOLIO,
        user_id="test-user-U08GVN6F4FQ",
        slack_user_id="test-user-U08GVN6F4FQ",
        team_id="T123456",
        channel_id="C123456",
        channel_name="test-channel",
        trigger_id="trigger123",
        command_text="",
        response_url="https://hooks.slack.com/commands/123",
        timestamp=datetime.now(timezone.utc)
    )
    
    # Mock user with permissions
    from models.user import User, UserRole, Permission
    mock_user = User(
        user_id="test-user-U08GVN6F4FQ",
        slack_user_id="test-user-U08GVN6F4FQ",
        role=UserRole.EXECUTION_TRADER,
        permissions={Permission.VIEW_PORTFOLIO, Permission.EXECUTE_TRADES}
    )
    command_context.user = mock_user
    
    # Mock Slack client
    class MockSlackClient:
        def __init__(self):
            self.messages = []
        
        def chat_postEphemeral(self, channel, user, text):
            self.messages.append({
                'channel': channel,
                'user': user,
                'text': text
            })
            print(f"📱 Slack Message to {user}:")
            print(text)
            print()
    
    client = MockSlackClient()
    
    try:
        # Test portfolio command
        await command_handler._handle_portfolio_command(command_context, client)
        
        print("✅ Portfolio command executed successfully!")
        print(f"📊 Messages sent: {len(client.messages)}")
        
        if client.messages:
            message = client.messages[0]
            if "AAPL" in message['text'] and "2" in message['text']:
                print("✅ Portfolio shows correct AAPL position (2 shares)")
            else:
                print("❌ Portfolio message doesn't show expected position")
                print(f"Message: {message['text']}")
        
    except Exception as e:
        print(f"❌ Portfolio command failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await container.shutdown()

if __name__ == "__main__":
    asyncio.run(test_portfolio_command())