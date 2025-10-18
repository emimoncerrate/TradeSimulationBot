"""
Account Management Commands for Multi-Alpaca System

Provides Slack commands for managing user assignments to Alpaca accounts.
"""

import logging
from typing import Dict, Any, List
from slack_bolt import App
from slack_sdk import WebClient

logger = logging.getLogger(__name__)


class AccountManagementCommands:
    """
    Slack commands for managing multi-Alpaca account assignments.
    
    Commands:
    - /accounts - Show all available accounts and their status
    - /assign-account - Assign a user to a specific account
    - /my-account - Show current user's account assignment
    - /account-users - Show users assigned to each account
    """
    
    def __init__(self, app: App):
        self.app = app
        self.register_commands()
        logger.info("Account management commands registered")
    
    def register_commands(self) -> None:
        """Register all account management commands."""
        
        @self.app.command("/accounts")
        def handle_accounts_command(ack, body, client, context):
            ack()
            import threading
            thread = threading.Thread(
                target=self._run_accounts_command,
                args=(body, client),
                daemon=True
            )
            thread.start()
        
        @self.app.command("/assign-account")
        def handle_assign_account_command(ack, body, client, context):
            ack()
            import threading
            thread = threading.Thread(
                target=self._run_assign_account_command,
                args=(body, client),
                daemon=True
            )
            thread.start()
        
        @self.app.command("/my-account")
        def handle_my_account_command(ack, body, client, context):
            ack()
            import threading
            thread = threading.Thread(
                target=self._run_my_account_command,
                args=(body, client),
                daemon=True
            )
            thread.start()
        
        @self.app.command("/account-users")
        def handle_account_users_command(ack, body, client, context):
            ack()
            import threading
            thread = threading.Thread(
                target=self._run_account_users_command,
                args=(body, client),
                daemon=True
            )
            thread.start()
    
    def _run_accounts_command(self, body: Dict[str, Any], client: WebClient) -> None:
        """Show all available accounts and their status."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._show_accounts_status(body, client))
        finally:
            loop.close()
    
    def _run_assign_account_command(self, body: Dict[str, Any], client: WebClient) -> None:
        """Assign a user to a specific account."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._assign_user_account(body, client))
        finally:
            loop.close()
    
    def _run_my_account_command(self, body: Dict[str, Any], client: WebClient) -> None:
        """Show current user's account assignment."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._show_my_account(body, client))
        finally:
            loop.close()
    
    def _run_account_users_command(self, body: Dict[str, Any], client: WebClient) -> None:
        """Show users assigned to each account."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._show_account_users(body, client))
        finally:
            loop.close()
    
    async def _show_accounts_status(self, body: Dict[str, Any], client: WebClient) -> None:
        """Show status of all Alpaca accounts."""
        try:
            from services.service_container import get_multi_alpaca_service, get_user_account_manager
            
            multi_alpaca = get_multi_alpaca_service()
            user_manager = get_user_account_manager()
            
            if not multi_alpaca.is_available():
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text="❌ Multi-Alpaca service is not available"
                )
                return
            
            # Get account status
            accounts_status = multi_alpaca.get_all_accounts_status()
            assignment_stats = user_manager.get_assignment_stats()
            
            # Build status message
            message = "📊 *Alpaca Accounts Status*\n\n"
            
            for account_id, status in accounts_status.items():
                if status.get('is_active', False):
                    message += f"✅ *{status['account_name']}*\n"
                    message += f"   • Account: {status['account_number']}\n"
                    message += f"   • Cash: ${status['cash']:,.2f}\n"
                    message += f"   • Portfolio: ${status['portfolio_value']:,.2f}\n"
                    message += f"   • Users: {status['assigned_users']}\n"
                    message += f"   • Status: {status['status']}\n\n"
                else:
                    message += f"❌ *{status['account_name']}*\n"
                    message += f"   • Status: Inactive\n"
                    if 'error' in status:
                        message += f"   • Error: {status['error']}\n"
                    message += "\n"
            
            message += f"📈 *Assignment Statistics*\n"
            message += f"• Total Users: {assignment_stats['total_assignments']}\n"
            message += f"• Accounts in Use: {assignment_stats['accounts_in_use']}\n"
            message += f"• Strategy: {assignment_stats['assignment_strategy']}\n"
            
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error showing accounts status: {e}")
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=f"❌ Error retrieving accounts status: {str(e)}"
            )
    
    async def _assign_user_account(self, body: Dict[str, Any], client: WebClient) -> None:
        """Assign a user to a specific account."""
        try:
            # Parse command text: /assign-account @user account_id
            command_text = body.get('text', '').strip()
            
            if not command_text:
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text="Usage: `/assign-account @user account_id`\nExample: `/assign-account @john primary`"
                )
                return
            
            parts = command_text.split()
            if len(parts) != 2:
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text="Usage: `/assign-account @user account_id`\nExample: `/assign-account @john primary`"
                )
                return
            
            target_user = parts[0].replace('@', '').replace('<', '').replace('>', '')
            account_id = parts[1]
            
            from services.service_container import get_multi_alpaca_service, get_user_account_manager
            
            multi_alpaca = get_multi_alpaca_service()
            user_manager = get_user_account_manager()
            
            # Check if account exists and is active
            accounts_status = multi_alpaca.get_all_accounts_status()
            if account_id not in accounts_status or not accounts_status[account_id].get('is_active', False):
                available_accounts = [aid for aid, status in accounts_status.items() if status.get('is_active', False)]
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text=f"❌ Account '{account_id}' is not available.\nAvailable accounts: {', '.join(available_accounts)}"
                )
                return
            
            # Assign user to account
            success = await user_manager.assign_user_to_account(
                user_id=target_user,
                account_id=account_id,
                assigned_by=body['user_id'],
                reason="manual_assignment"
            )
            
            if success:
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text=f"✅ Successfully assigned user <@{target_user}> to account '{account_id}'"
                )
            else:
                client.chat_postEphemeral(
                    channel=body['channel_id'],
                    user=body['user_id'],
                    text=f"❌ Failed to assign user <@{target_user}> to account '{account_id}'"
                )
            
        except Exception as e:
            logger.error(f"Error assigning user account: {e}")
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=f"❌ Error assigning user account: {str(e)}"
            )
    
    async def _show_my_account(self, body: Dict[str, Any], client: WebClient) -> None:
        """Show current user's account assignment."""
        try:
            from services.service_container import get_multi_alpaca_service, get_user_account_manager
            
            user_id = body['user_id']
            user_manager = get_user_account_manager()
            multi_alpaca = get_multi_alpaca_service()
            
            # Get user's assigned account
            assigned_account = user_manager.get_user_account(user_id)
            
            if not assigned_account:
                # Try auto-assignment
                available_accounts = list(multi_alpaca.get_available_accounts().keys())
                assigned_account = await user_manager.auto_assign_user(user_id, available_accounts)
                
                if not assigned_account:
                    client.chat_postEphemeral(
                        channel=body['channel_id'],
                        user=body['user_id'],
                        text="❌ No account assigned and auto-assignment failed. Please contact an admin."
                    )
                    return
            
            # Get account details
            account_info = multi_alpaca.get_account_info(assigned_account)
            
            if account_info:
                message = f"📊 *Your Alpaca Account*\n\n"
                message += f"✅ *Account:* {account_info['account_name']}\n"
                message += f"• Account Number: {account_info['account_number']}\n"
                message += f"• Cash Available: ${account_info['cash']:,.2f}\n"
                message += f"• Portfolio Value: ${account_info['portfolio_value']:,.2f}\n"
                message += f"• Buying Power: ${account_info['buying_power']:,.2f}\n"
                message += f"• Day Trading Buying Power: ${account_info['day_trading_buying_power']:,.2f}\n"
                message += f"• Status: {account_info['status']}\n"
            else:
                message = f"❌ Unable to retrieve account information for '{assigned_account}'"
            
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error showing user account: {e}")
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=f"❌ Error retrieving account information: {str(e)}"
            )
    
    async def _show_account_users(self, body: Dict[str, Any], client: WebClient) -> None:
        """Show users assigned to each account."""
        try:
            from services.service_container import get_multi_alpaca_service, get_user_account_manager
            
            multi_alpaca = get_multi_alpaca_service()
            user_manager = get_user_account_manager()
            
            accounts_status = multi_alpaca.get_all_accounts_status()
            
            message = "👥 *Users by Account*\n\n"
            
            for account_id, status in accounts_status.items():
                if status.get('is_active', False):
                    users = user_manager.get_account_users(account_id)
                    message += f"📊 *{status['account_name']}*\n"
                    
                    if users:
                        for user_id in users:
                            message += f"   • <@{user_id}>\n"
                    else:
                        message += "   • No users assigned\n"
                    message += "\n"
            
            # Add assignment statistics
            stats = user_manager.get_assignment_stats()
            message += f"📈 *Summary*\n"
            message += f"• Total Users: {stats['total_assignments']}\n"
            message += f"• Assignment Strategy: {stats['assignment_strategy']}\n"
            
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error showing account users: {e}")
            client.chat_postEphemeral(
                channel=body['channel_id'],
                user=body['user_id'],
                text=f"❌ Error retrieving account users: {str(e)}"
            )


def register_account_management_commands(app: App) -> AccountManagementCommands:
    """
    Register account management commands with the Slack app.
    
    Args:
        app: Slack Bolt app instance
        
    Returns:
        AccountManagementCommands: Configured command handler
    """
    return AccountManagementCommands(app)