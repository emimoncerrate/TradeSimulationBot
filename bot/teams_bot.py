from botbuilder.core import ActivityHandler, TurnContext, ConversationState, UserState
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount
from typing import List
from config.settings import Settings
from services.service_container import ServiceContainer

class TeamsTradeBot(ActivityHandler):
    def __init__(
        self,
        conversation_state: ConversationState,
        user_state: UserState,
        settings: Settings,
        service_container: ServiceContainer
    ):
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.settings = settings
        self.services = service_container

    async def on_message_activity(self, turn_context: TurnContext):
        """Handle incoming messages."""
        # Add command handling logic here
        message_text = turn_context.activity.text.lower().strip()
        
        if message_text.startswith("trade"):
            await self._handle_trade_command(turn_context)
        elif message_text.startswith("portfolio"):
            await self._handle_portfolio_command(turn_context)
        elif message_text.startswith("risk"):
            await self._handle_risk_command(turn_context)
        else:
            await turn_context.send_activity("I'm your trading assistant. Try commands like 'trade', 'portfolio', or 'risk'.")

    async def _handle_trade_command(self, turn_context: TurnContext):
        """Handle trade-related commands."""
        # Add trade command logic
        await turn_context.send_activity("Trade command recognized. Implement trade logic here.")

    async def _handle_portfolio_command(self, turn_context: TurnContext):
        """Handle portfolio-related commands."""
        # Add portfolio command logic
        await turn_context.send_activity("Portfolio command recognized. Implement portfolio logic here.")

    async def _handle_risk_command(self, turn_context: TurnContext):
        """Handle risk analysis commands."""
        # Add risk analysis logic
        await turn_context.send_activity("Risk command recognized. Implement risk analysis logic here.")

    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        """Send a welcome message when a new member is added."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    f"Welcome to the Trading Bot! I can help you with trading simulations, "
                    f"portfolio management, and risk analysis. Try commands like 'trade', "
                    f"'portfolio', or 'risk' to get started."
                )

    async def on_turn(self, turn_context: TurnContext):
        """Handle the bot's turn."""
        await super().on_turn(turn_context)
        
        # Save state changes
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)
