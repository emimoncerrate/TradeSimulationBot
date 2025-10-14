import logging
from botbuilder.core import MessageFactory, CardFactory
from botbuilder.dialogs import (
    ComponentDialog,
    WaterfallDialog,
    WaterfallStepContext,
    DialogTurnResult,
)
from botbuilder.dialogs.prompts import (
    TextPrompt,
    NumberPrompt,
    ChoicePrompt,
    ConfirmPrompt,
)
from botbuilder.schema import ActivityTypes, Activity
from typing import Dict, Any, Optional
from decimal import Decimal
from ..cards.card_manager import CardManager

logger = logging.getLogger(__name__)

class TradeValidationError(Exception):
    """Exception for trade validation errors."""
    pass

class TradeDialog(ComponentDialog):
    def __init__(self, dialog_id: str = None, market_service=None, risk_service=None):
        super(TradeDialog, self).__init__(dialog_id or TradeDialog.__name__)
        
        self.card_manager = CardManager()
        self.market_service = market_service
        self.risk_service = risk_service
        
        # Add prompts
        self.add_dialog(TextPrompt("text_prompt", self._validate_symbol))
        self.add_dialog(NumberPrompt("number_prompt", self._validate_quantity))
        self.add_dialog(ChoicePrompt("choice_prompt"))
        self.add_dialog(ConfirmPrompt("confirm_prompt"))
        
        # Add waterfall dialog
        self.add_dialog(
            WaterfallDialog(
                "trade_waterfall",
                [
                    self.show_trade_card_step,
                    self.process_trade_step,
                    self.validate_and_analyze_step,
                    self.confirm_trade_step,
                    self.execute_trade_step,
                ],
            )
        )
        
        # Set the initial dialog
        self.initial_dialog_id = "trade_waterfall"
        
    async def _validate_symbol(self, prompt_context) -> bool:
        """Validate the entered stock symbol."""
        if not prompt_context.recognized.value:
            return False
            
        symbol = prompt_context.recognized.value.upper()
        try:
            # Check if symbol exists and get market data
            if self.market_service:
                quote = await self.market_service.get_quote(symbol)
                if quote:
                    prompt_context.state["quote"] = quote
                    return True
            return False
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {str(e)}")
            return False
            
    async def _validate_quantity(self, prompt_context) -> bool:
        """Validate the trade quantity."""
        if not prompt_context.recognized.succeeded:
            return False
            
        quantity = prompt_context.recognized.value
        try:
            if quantity <= 0:
                await prompt_context.context.send_activity("Quantity must be greater than 0.")
                return False
                
            if quantity > 10000:  # Max from settings
                await prompt_context.context.send_activity("Quantity exceeds maximum allowed.")
                return False
                
            # Validate total value if we have quote data
            if "quote" in prompt_context.state:
                total_value = Decimal(str(quantity)) * Decimal(str(prompt_context.state["quote"]["price"]))
                if total_value > 1000000:  # Max from settings
                    await prompt_context.context.send_activity("Total trade value exceeds limit.")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating quantity {quantity}: {str(e)}")
            return False
            
    async def show_trade_card_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Show the trade card to collect trade details."""
        try:
            # Get market data if symbol provided
            symbol = step_context.options.get("symbol", "")
            market_data = {}
            
            if symbol and self.market_service:
                quote = await self.market_service.get_quote(symbol)
                if quote:
                    market_data = {
                        "symbol": symbol,
                        "lastPrice": f"${quote['price']:,.2f}",
                        "priceChange": f"{quote['change']:+.2f} ({quote['change_percent']:+.1f}%)",
                        "volume": f"{quote['volume']:,}"
                    }
            
            # Create and show the card
            card = self.card_manager.create_trade_card(market_data)
            message = Activity(
                type=ActivityTypes.message,
                attachments=[card],
            )
            await step_context.context.send_activity(message)
            return DialogTurnResult(DialogTurnResult.waiting)
            
        except Exception as e:
            logger.error(f"Error showing trade card: {str(e)}")
            await step_context.context.send_activity("Sorry, there was an error displaying the trade form.")
            return await step_context.end_dialog()
            
    async def process_trade_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Process the trade card submission."""
        try:
            if not step_context.result:
                return await step_context.end_dialog()
                
            trade_details = step_context.result
            if trade_details.get("action") == "cancel_trade":
                await step_context.context.send_activity("Trade cancelled.")
                return await step_context.end_dialog()
                
            # Basic validation
            try:
                self._validate_trade_details(trade_details)
            except TradeValidationError as e:
                await step_context.context.send_activity(str(e))
                return await step_context.replace_dialog(self.id)
                
            step_context.values["trade_details"] = trade_details
            return await step_context.next(trade_details)
            
        except Exception as e:
            logger.error(f"Error processing trade: {str(e)}")
            await step_context.context.send_activity("Sorry, there was an error processing your trade.")
            return await step_context.end_dialog()
            
    async def validate_and_analyze_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Validate trade and perform risk analysis."""
        try:
            trade_details = step_context.values["trade_details"]
            
            # Get current market data
            quote = None
            if self.market_service:
                quote = await self.market_service.get_quote(trade_details["symbol"])
                if quote:
                    trade_details["current_price"] = quote["price"]
                    
            # Perform risk analysis
            if self.risk_service:
                risk_analysis = await self.risk_service.analyze_trade(trade_details)
                trade_details["risk_analysis"] = risk_analysis
                
            step_context.values["trade_details"] = trade_details
            return await step_context.next()
            
        except Exception as e:
            logger.error(f"Error in validation and analysis: {str(e)}")
            await step_context.context.send_activity("Sorry, there was an error analyzing your trade.")
            return await step_context.end_dialog()
            
    async def confirm_trade_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Show trade confirmation with analysis."""
        try:
            trade_details = step_context.values["trade_details"]
            risk_analysis = trade_details.get("risk_analysis", {})
            
            # Create confirmation card with risk analysis
            confirmation_data = {
                **trade_details,
                "estimatedTotal": self._calculate_total(trade_details),
                "portfolioImpact": risk_analysis.get("portfolio_impact", "N/A"),
                "riskLevel": risk_analysis.get("risk_level", "N/A"),
                "positionSize": risk_analysis.get("position_size", "N/A"),
                "warningMessage": risk_analysis.get("warning", ""),
                "hasWarning": bool(risk_analysis.get("warning"))
            }
            
            card = self.card_manager.create_confirmation_card(confirmation_data)
            message = Activity(
                type=ActivityTypes.message,
                attachments=[card],
            )
            await step_context.context.send_activity(message)
            return DialogTurnResult(DialogTurnResult.waiting)
            
        except Exception as e:
            logger.error(f"Error showing confirmation: {str(e)}")
            await step_context.context.send_activity("Sorry, there was an error confirming your trade.")
            return await step_context.end_dialog()
            
    async def execute_trade_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Execute the confirmed trade."""
        try:
            if not step_context.result or step_context.result.get("action") == "cancel_trade":
                await step_context.context.send_activity("Trade cancelled.")
                return await step_context.end_dialog()
                
            if step_context.result.get("action") == "modify_trade":
                return await step_context.replace_dialog(self.id, step_context.values["trade_details"])
                
            trade_details = step_context.values["trade_details"]
            
            # Execute trade through trading service
            try:
                # Here you would integrate with your trading service
                order_id = f"DEMO-{hash(str(trade_details))}"
                await step_context.context.send_activity(
                    f"Trade executed successfully!\n"
                    f"Order ID: {order_id}\n"
                    f"{trade_details['orderType'].upper()} {trade_details['quantity']} {trade_details['symbol']}"
                )
            except Exception as e:
                logger.error(f"Trade execution error: {str(e)}")
                await step_context.context.send_activity("Sorry, there was an error executing your trade.")
                
            return await step_context.end_dialog()
            
        except Exception as e:
            logger.error(f"Error in execute step: {str(e)}")
            await step_context.context.send_activity("Sorry, there was an error with your trade.")
            return await step_context.end_dialog()
            
    def _validate_trade_details(self, trade_details: Dict[str, Any]) -> bool:
        """Validate trade details."""
        if not trade_details.get("symbol"):
            raise TradeValidationError("Please enter a valid symbol.")
            
        if not trade_details.get("orderType"):
            raise TradeValidationError("Please select an order type.")
            
        if not trade_details.get("orderMethod"):
            raise TradeValidationError("Please select an order method.")
            
        try:
            quantity = float(trade_details.get("quantity", 0))
            if quantity <= 0:
                raise TradeValidationError("Quantity must be greater than 0.")
            if quantity > 10000:  # Max from settings
                raise TradeValidationError("Quantity exceeds maximum allowed.")
        except ValueError:
            raise TradeValidationError("Please enter a valid quantity.")
            
        if trade_details["orderMethod"] in ["limit", "stop"]:
            try:
                price = float(trade_details.get("price", 0))
                if price <= 0:
                    raise TradeValidationError("Please enter a valid price for limit/stop order.")
            except ValueError:
                raise TradeValidationError("Please enter a valid price.")
                
        return True
        
    def _calculate_total(self, trade_details: Dict[str, Any]) -> str:
        """Calculate estimated total value of trade."""
        try:
            quantity = float(trade_details["quantity"])
            price = float(trade_details.get("price") or trade_details.get("current_price", 0))
            total = quantity * price
            return f"${total:,.2f}"
        except (ValueError, TypeError):
            return "N/A"
