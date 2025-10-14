"""
Interactive Action Handlers for Advanced Trading Modal.

This module handles real-time field updates, calculations, and dynamic modal updates
for the interactive trading interface.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional
import json

from slack_bolt import App, Ack, BoltContext
from slack_sdk import WebClient

from ui.interactive_trade_widget import InteractiveTradeWidget, InteractiveTradeContext, OrderType
from services.service_container import get_market_data_service
from models.user import User, UserRole, UserProfile
from utils.formatters import format_money

logger = logging.getLogger(__name__)


class InteractiveActionHandler:
    """
    Handler for interactive trading modal actions.
    
    Manages real-time field updates, calculations, and dynamic modal refreshes
    for the advanced trading interface.
    """
    
    def __init__(self):
        """Initialize interactive action handler."""
        self.widget = InteractiveTradeWidget()
        self.logger = logging.getLogger(__name__)
        
        # Cache for user contexts to maintain state
        self.user_contexts: Dict[str, InteractiveTradeContext] = {}
        
        self.logger.info("InteractiveActionHandler initialized")
    
    def register_handlers(self, app: App) -> None:
        """
        Register all interactive action handlers with the Slack app.
        
        Args:
            app: Slack Bolt app instance
        """
        # Shares input handler (real-time calculation)
        app.action("shares_input")(self.handle_shares_input)
        
        # GMV input handler (real-time calculation)
        app.action("gmv_input")(self.handle_gmv_input)
        
        # Symbol input handler (price lookup)
        app.action("symbol_input")(self.handle_symbol_input)
        
        # Trade side selection handler
        app.action("trade_side_radio")(self.handle_trade_side_change)
        
        # Order type selection handler
        app.action("order_type_select")(self.handle_order_type_change)
        
        # Limit price input handler
        app.action("limit_price_input")(self.handle_limit_price_input)
        
        # Modal submission handler
        app.view("stock_trade_modal_interactive")(self.handle_modal_submission)
        
        self.logger.info("Interactive action handlers registered")
    
    async def handle_shares_input(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle shares input changes with real-time GMV calculation.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        await ack()
        
        try:
            # Extract context and new shares value
            context = self._extract_context_from_body(body)
            if not context:
                return
            
            # Get new shares value
            shares_value = body.get("actions", [{}])[0].get("value", "")
            
            if shares_value and shares_value.strip():
                try:
                    shares = int(float(shares_value))
                    if shares > 0:
                        # Update modal with new calculation
                        updated_modal = self.widget.update_modal_with_calculation(
                            context, "shares", shares
                        )
                        
                        # Update the modal view
                        await client.views_update(
                            view_id=body["view"]["id"],
                            view=updated_modal
                        )
                        
                        self.logger.info(f"Shares updated: {shares} -> GMV: ${context.gmv}")
                    
                except (ValueError, InvalidOperation) as e:
                    self.logger.warning(f"Invalid shares input: {shares_value} - {e}")
            
        except Exception as e:
            self.logger.error(f"Shares input handler error: {e}")
    
    async def handle_gmv_input(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle GMV input changes with real-time shares calculation.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        await ack()
        
        try:
            # Extract context and new GMV value
            context = self._extract_context_from_body(body)
            if not context:
                return
            
            # Get new GMV value
            gmv_value = body.get("actions", [{}])[0].get("value", "")
            
            if gmv_value and gmv_value.strip():
                try:
                    gmv = Decimal(str(gmv_value))
                    if gmv > 0:
                        # Update modal with new calculation
                        updated_modal = self.widget.update_modal_with_calculation(
                            context, "gmv", gmv
                        )
                        
                        # Update the modal view
                        await client.views_update(
                            view_id=body["view"]["id"],
                            view=updated_modal
                        )
                        
                        self.logger.info(f"GMV updated: ${gmv} -> Shares: {context.shares}")
                    
                except (ValueError, InvalidOperation) as e:
                    self.logger.warning(f"Invalid GMV input: {gmv_value} - {e}")
            
        except Exception as e:
            self.logger.error(f"GMV input handler error: {e}")
    
    async def handle_symbol_input(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle symbol input changes with price lookup.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        await ack()
        
        try:
            # Extract context and new symbol
            context = self._extract_context_from_body(body)
            if not context:
                return
            
            # Get new symbol value
            symbol_value = body.get("actions", [{}])[0].get("value", "").upper().strip()
            
            if symbol_value and len(symbol_value) >= 1:
                context.symbol = symbol_value
                context.price_loading = True
                
                # Show loading state first
                loading_modal = self.widget.create_interactive_modal(context)
                await client.views_update(
                    view_id=body["view"]["id"],
                    view=loading_modal
                )
                
                # Fetch new price data
                try:
                    market_service = get_market_data_service()
                    market_quote = await market_service.get_quote(symbol_value)
                    
                    # Update modal with new price
                    updated_modal = self.widget.update_modal_with_price(context, market_quote)
                    
                    await client.views_update(
                        view_id=body["view"]["id"],
                        view=updated_modal
                    )
                    
                    self.logger.info(f"Symbol updated: {symbol_value} -> Price: ${market_quote.current_price}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to fetch price for {symbol_value}: {e}")
                    context.price_loading = False
                    context.calculation_error = f"Failed to load price for {symbol_value}"
                    
                    error_modal = self.widget.create_interactive_modal(context)
                    await client.views_update(
                        view_id=body["view"]["id"],
                        view=error_modal
                    )
            
        except Exception as e:
            self.logger.error(f"Symbol input handler error: {e}")
    
    async def handle_trade_side_change(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle trade side (buy/sell) selection changes.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        await ack()
        
        try:
            context = self._extract_context_from_body(body)
            if not context:
                return
            
            # Get selected trade side
            selected_option = body.get("actions", [{}])[0].get("selected_option", {})
            trade_side = selected_option.get("value", "buy")
            
            context.trade_side = trade_side
            
            # Update modal
            updated_modal = self.widget.create_interactive_modal(context)
            await client.views_update(
                view_id=body["view"]["id"],
                view=updated_modal
            )
            
            self.logger.info(f"Trade side changed to: {trade_side}")
            
        except Exception as e:
            self.logger.error(f"Trade side handler error: {e}")
    
    async def handle_order_type_change(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle order type selection changes.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        await ack()
        
        try:
            context = self._extract_context_from_body(body)
            if not context:
                return
            
            # Get selected order type
            selected_option = body.get("actions", [{}])[0].get("selected_option", {})
            order_type_value = selected_option.get("value", "market")
            
            context.order_type = OrderType(order_type_value)
            
            # Clear limit price if not needed
            if context.order_type not in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
                context.limit_price = None
            
            # Update modal
            updated_modal = self.widget.create_interactive_modal(context)
            await client.views_update(
                view_id=body["view"]["id"],
                view=updated_modal
            )
            
            self.logger.info(f"Order type changed to: {order_type_value}")
            
        except Exception as e:
            self.logger.error(f"Order type handler error: {e}")
    
    async def handle_limit_price_input(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle limit price input changes.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        await ack()
        
        try:
            context = self._extract_context_from_body(body)
            if not context:
                return
            
            # Get new limit price value
            limit_price_value = body.get("actions", [{}])[0].get("value", "")
            
            if limit_price_value and limit_price_value.strip():
                try:
                    context.limit_price = Decimal(str(limit_price_value))
                    self.logger.info(f"Limit price updated: ${context.limit_price}")
                except (ValueError, InvalidOperation) as e:
                    self.logger.warning(f"Invalid limit price: {limit_price_value} - {e}")
            else:
                context.limit_price = None
            
        except Exception as e:
            self.logger.error(f"Limit price handler error: {e}")
    
    async def handle_modal_submission(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle interactive modal submission.
        
        Args:
            ack: Slack acknowledgment function
            body: Request body
            client: Slack web client
        """
        try:
            # Extract final trade data
            context = self._extract_context_from_submission(body)
            if not context:
                await ack(response_action="errors", errors={"general": "Invalid trade data"})
                return
            
            # Validate trade data
            validation_errors = self.widget.validate_trade_data(context)
            if validation_errors:
                await ack(response_action="errors", errors=validation_errors)
                return
            
            # Acknowledge successful submission
            await ack()
            
            # TODO: Process the trade execution
            # This would integrate with your existing trade execution system
            self.logger.info(
                f"Trade submitted: {context.symbol} {context.trade_side} "
                f"{context.shares} shares @ ${context.current_price} "
                f"(GMV: ${context.gmv}, Order: {context.order_type.value})"
            )
            
            # Send confirmation message
            await client.chat_postMessage(
                channel=context.channel_id,
                text=f"✅ Trade submitted successfully!\n"
                     f"• Symbol: {context.symbol}\n"
                     f"• Action: {context.trade_side.title()}\n"
                     f"• Shares: {context.shares:,}\n"
                     f"• GMV: {format_money(context.gmv)}\n"
                     f"• Order Type: {context.order_type.value.replace('_', ' ').title()}"
            )
            
        except Exception as e:
            self.logger.error(f"Modal submission error: {e}")
            await ack(response_action="errors", errors={"general": f"Submission failed: {e}"})
    
    def _extract_context_from_body(self, body: Dict[str, Any]) -> Optional[InteractiveTradeContext]:
        """
        Extract interactive context from action body.
        
        Args:
            body: Slack action body
            
        Returns:
            InteractiveTradeContext or None if extraction fails
        """
        try:
            # Get user info
            user_id = body.get("user", {}).get("id")
            if not user_id:
                return None
            
            # Create mock user (in real implementation, fetch from database)
            user = User(
                user_id=f"test-user-{user_id}",
                slack_user_id=user_id,
                role=UserRole.EXECUTION_TRADER,
                profile=UserProfile(
                    display_name=body.get("user", {}).get("name", "Unknown"),
                    email=f"{user_id}@example.com",
                    department="Trading"
                )
            )
            
            # Get channel and trigger info
            channel_id = body.get("container", {}).get("channel_id", "")
            trigger_id = body.get("trigger_id", "")
            
            # Extract current values from modal state
            view = body.get("view", {})
            private_metadata = json.loads(view.get("private_metadata", "{}"))
            
            # Create context
            context = InteractiveTradeContext(
                user=user,
                channel_id=channel_id,
                trigger_id=trigger_id,
                symbol=private_metadata.get("symbol", "AAPL"),
                current_price=Decimal(str(private_metadata.get("current_price", "150.00")))
            )
            
            # Cache context for this user
            self.user_contexts[user_id] = context
            
            return context
            
        except Exception as e:
            self.logger.error(f"Context extraction error: {e}")
            return None
    
    def _extract_context_from_submission(self, body: Dict[str, Any]) -> Optional[InteractiveTradeContext]:
        """
        Extract context from modal submission.
        
        Args:
            body: Modal submission body
            
        Returns:
            InteractiveTradeContext or None if extraction fails
        """
        try:
            # Get user info
            user_id = body.get("user", {}).get("id")
            if not user_id:
                return None
            
            # Create mock user
            user = User(
                user_id=f"test-user-{user_id}",
                slack_user_id=user_id,
                role=UserRole.EXECUTION_TRADER,
                profile=UserProfile(
                    display_name=body.get("user", {}).get("name", "Unknown"),
                    email=f"{user_id}@example.com",
                    department="Trading"
                )
            )
            
            # Extract values from form submission
            view = body.get("view", {})
            values = view.get("state", {}).get("values", {})
            private_metadata = json.loads(view.get("private_metadata", "{}"))
            
            # Extract form values
            symbol = values.get("trade_symbol_block", {}).get("symbol_input", {}).get("value", "AAPL").upper()
            trade_side = values.get("trade_side_block", {}).get("trade_side_radio", {}).get("selected_option", {}).get("value", "buy")
            
            # Extract shares
            shares_value = values.get("qty_shares_block", {}).get("shares_input", {}).get("value")
            shares = int(float(shares_value)) if shares_value else None
            
            # Extract GMV
            gmv_value = values.get("gmv_block", {}).get("gmv_input", {}).get("value")
            gmv = Decimal(str(gmv_value)) if gmv_value else None
            
            # Extract order type
            order_type_value = values.get("order_type_block", {}).get("order_type_select", {}).get("selected_option", {}).get("value", "market")
            order_type = OrderType(order_type_value)
            
            # Extract limit price
            limit_price_value = values.get("limit_price_block", {}).get("limit_price_input", {}).get("value")
            limit_price = Decimal(str(limit_price_value)) if limit_price_value else None
            
            # Create context
            context = InteractiveTradeContext(
                user=user,
                channel_id=private_metadata.get("channel_id", ""),
                trigger_id="",
                symbol=symbol,
                trade_side=trade_side,
                shares=shares,
                gmv=gmv,
                order_type=order_type,
                limit_price=limit_price,
                current_price=Decimal(str(private_metadata.get("current_price", "150.00")))
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Submission context extraction error: {e}")
            return None


# Global handler instance
interactive_handler = InteractiveActionHandler()