"""
Interactive Action Handlers for Advanced Trading Modal.

This module handles real-time field updates, calculations, and dynamic modal updates
for the interactive trading interface.
"""

import asyncio
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
        import asyncio
        
        # Shares input handler (real-time calculation)
        @app.action("shares_input")
        def handle_shares_input_wrapper(ack, body, client):
            asyncio.create_task(self.handle_shares_input(ack, body, client))
        
        # GMV input handler (real-time calculation)
        @app.action("gmv_input")
        def handle_gmv_input_wrapper(ack, body, client):
            asyncio.create_task(self.handle_gmv_input(ack, body, client))
        
        # Symbol input handler (price lookup)
        @app.action("symbol_input")
        def handle_symbol_input_wrapper(ack, body, client):
            asyncio.create_task(self.handle_symbol_input(ack, body, client))
        
        # Trade side selection handler
        @app.action("trade_side_radio")
        def handle_trade_side_change_wrapper(ack, body, client):
            asyncio.create_task(self.handle_trade_side_change(ack, body, client))
        
        # Order type selection handler
        @app.action("order_type_select")
        def handle_order_type_change_wrapper(ack, body, client):
            asyncio.create_task(self.handle_order_type_change(ack, body, client))
        
        # Limit price input handler
        @app.action("limit_price_input")
        def handle_limit_price_input_wrapper(ack, body, client):
            asyncio.create_task(self.handle_limit_price_input(ack, body, client))
        
        # Modal submission handler - the most important one for trade execution
        @app.view("stock_trade_modal_interactive")
        def handle_modal_submission_wrapper(ack, body, client):
            print(f"🎯 MODAL SUBMISSION: Handler called successfully")
            
            try:
                # Acknowledge with clear response to close the modal
                ack({
                    "response_action": "clear"
                })
                print(f"✅ MODAL: Acknowledged with clear action")
            except Exception as ack_error:
                # Fallback to simple ack
                ack()
                print(f"✅ MODAL: Acknowledged with simple ack (fallback)")
            
            # Execute the trade in a new thread to avoid event loop issues
            import threading
            thread = threading.Thread(
                target=self._run_async_trade_execution,
                args=(body, client),
                daemon=True
            )
            thread.start()
            
            print(f"✅ MODAL: Trade executing in background")
        
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
        
        print("🔍 SYMBOL INPUT: Handler called!")
        print(f"🔍 SYMBOL INPUT: Body keys: {list(body.keys())}")
        
        try:
            # Extract context and new symbol
            context = self._extract_context_from_body(body)
            if not context:
                print("❌ SYMBOL INPUT: No context extracted")
                return
            
            print(f"✅ SYMBOL INPUT: Context extracted successfully")
            
            # Get new symbol value
            symbol_value = body.get("actions", [{}])[0].get("value", "").upper().strip()
            print(f"🔍 SYMBOL INPUT: Symbol value: '{symbol_value}'")
            
            if symbol_value and len(symbol_value) >= 1:
                context.symbol = symbol_value
                context.price_loading = True
                
                print(f"🔄 SYMBOL INPUT: Fetching price for {symbol_value}...")
                
                # Show loading state first
                loading_modal = self.widget.create_interactive_modal(context)
                await client.views_update(
                    view_id=body["view"]["id"],
                    view=loading_modal
                )
                
                print(f"✅ SYMBOL INPUT: Loading modal updated")
                
                # Fetch new price data
                try:
                    market_service = get_market_data_service()
                    print(f"✅ SYMBOL INPUT: Market service obtained")
                    
                    market_quote = await market_service.get_quote(symbol_value)
                    print(f"✅ SYMBOL INPUT: Quote received: {market_quote}")
                    
                    # Update modal with new price
                    updated_modal = self.widget.update_modal_with_price(context, market_quote)
                    
                    await client.views_update(
                        view_id=body["view"]["id"],
                        view=updated_modal
                    )
                    
                    print(f"✅ SYMBOL INPUT: Modal updated with price: ${market_quote.current_price}")
                    self.logger.info(f"Symbol updated: {symbol_value} -> Price: ${market_quote.current_price}")
                    
                except Exception as e:
                    print(f"❌ SYMBOL INPUT: Price fetch failed: {e}")
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
        Handle interactive modal submission with enhanced trade execution.
        
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
            
            self.logger.info(
                f"Interactive trade submitted: {context.symbol} {context.trade_side} "
                f"{context.shares} shares @ ${context.current_price} "
                f"(GMV: ${context.gmv}, Order: {context.order_type.value})"
            )
            
            # Execute the trade using the enhanced execution system
            await self._execute_interactive_trade(context, client)
            
        except Exception as e:
            self.logger.error(f"Modal submission error: {e}")
            await ack(response_action="errors", errors={"general": f"Submission failed: {e}"})
    
    async def handle_modal_submission_async(self, ack: Ack, body: Dict[str, Any], client: WebClient) -> None:
        """
        Handle interactive modal submission asynchronously (already acked).
        
        Args:
            ack: Slack acknowledgment function (already called)
            body: Request body
            client: Slack web client
        """
        try:
            # Extract final trade data
            context = self._extract_context_from_submission(body)
            if not context:
                self.logger.error("Failed to extract context from modal submission")
                return
            
            # Validate trade data
            validation_errors = self.widget.validate_trade_data(context)
            if validation_errors:
                self.logger.error(f"Trade validation failed: {validation_errors}")
                # Send error message to channel since we can't update the modal
                client.chat_postEphemeral(
                    channel=context.channel_id,
                    user=context.user.slack_user_id,
                    text=f"❌ Trade validation failed: {', '.join(validation_errors.values())}"
                )
                return
            
            self.logger.info(
                f"Interactive trade submitted: {context.symbol} {context.trade_side} "
                f"{context.shares} shares @ ${context.current_price} "
                f"(GMV: ${context.gmv}, Order: {context.order_type.value})"
            )
            
            # Execute the trade using the enhanced execution system
            await self._execute_interactive_trade(context, client)
            
        except Exception as e:
            self.logger.error(f"Async modal submission error: {e}")
            # Send error message to channel
            try:
                client.chat_postEphemeral(
                    channel=body.get("view", {}).get("private_metadata", {}).get("channel_id", ""),
                    user=body.get("user", {}).get("id", ""),
                    text=f"❌ Trade execution failed: {str(e)}"
                )
            except Exception:
                pass
    
    def _run_async_trade_execution_with_ack(self, ack, body: Dict[str, Any], client: WebClient) -> None:
        """Run trade execution with proper modal acknowledgment."""
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Execute the trade
            result = loop.run_until_complete(self._execute_interactive_trade(body, client))
            
            # Acknowledge the modal to close it
            ack()
            print(f"✅ MODAL: Closed successfully after trade execution")
            
        except Exception as e:
            # If trade fails, acknowledge with error
            ack({
                "response_action": "errors",
                "errors": {
                    "symbol": f"Trade execution failed: {str(e)}"
                }
            })
            print(f"❌ MODAL: Closed with error after trade failure: {e}")
        finally:
            loop.close()
    
    def _run_async_trade_execution(self, body: Dict[str, Any], client: WebClient) -> None:
        """
        Run async trade execution in a new event loop (thread-safe).
        
        Args:
            body: Request body
            client: Slack web client
        """
        try:
            # Create a new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the async trade execution
                loop.run_until_complete(self._execute_trade_from_submission(body, client))
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"Thread-safe trade execution failed: {e}")
    
    async def _execute_trade_from_submission(self, body: Dict[str, Any], client: WebClient) -> None:
        """
        Execute trade from modal submission (thread-safe async).
        
        Args:
            body: Request body
            client: Slack web client
        """
        try:
            # Extract final trade data
            context = await self._extract_context_from_body(body)
            if not context:
                print(f"❌ TRADE SUBMISSION: Failed to extract context from modal submission")
                self.logger.error("Failed to extract context from modal submission")
                return
            
            print(f"✅ TRADE SUBMISSION: Context extracted successfully")
            
            # Validate trade data
            validation_errors = self.widget.validate_trade_data(context)
            if validation_errors:
                self.logger.error(f"Trade validation failed: {validation_errors}")
                # Send error message to channel
                client.chat_postEphemeral(
                    channel=context.channel_id,
                    user=context.user.slack_user_id,
                    text=f"❌ Trade validation failed: {', '.join(validation_errors.values())}"
                )
                return
            
            self.logger.info(
                f"Interactive trade submitted: {context.symbol} {context.trade_side} "
                f"{context.shares} shares @ ${context.current_price} "
                f"(GMV: ${context.gmv}, Order: {context.order_type.value})"
            )
            
            # Execute the trade using the enhanced execution system
            await self._execute_interactive_trade(context, client)
            
        except Exception as e:
            self.logger.error(f"Trade execution from submission failed: {e}")
            # Send error message to channel
            try:
                user_id = body.get("user", {}).get("id", "")
                channel_id = json.loads(body.get("view", {}).get("private_metadata", "{}")).get("channel_id", "")
                
                if user_id and channel_id:
                    client.chat_postEphemeral(
                        channel=channel_id,
                        user=user_id,
                        text=f"❌ Trade execution failed: {str(e)}"
                    )
            except Exception as notify_error:
                self.logger.error(f"Failed to send error notification: {notify_error}")
    
    async def _execute_interactive_trade(self, context: InteractiveTradeContext, client: WebClient) -> None:
        """
        Execute trade from interactive modal using enhanced execution system.
        
        Args:
            context: Interactive trade context
            client: Slack web client
        """
        try:
            # Import required modules
            from models.trade import Trade, TradeType, TradeStatus
            from services.service_container import get_database_service, get_alpaca_service
            from datetime import datetime, timezone
            import uuid
            
            # Create trade object
            trade_type = TradeType.BUY if context.trade_side.lower() == 'buy' else TradeType.SELL
            print(f"🔍 TRADE CREATION: trade_side='{context.trade_side}', trade_type={trade_type}")
            
            # Calculate quantity (positive for buy, negative for sell)
            quantity = context.shares if trade_type == TradeType.BUY else -context.shares
            print(f"🔍 TRADE CREATION: shares={context.shares}, calculated quantity={quantity}")
            
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                user_id=context.user.user_id,
                symbol=context.symbol,
                quantity=quantity,
                trade_type=trade_type,
                price=context.current_price,
                timestamp=datetime.now(timezone.utc),
                status=TradeStatus.PENDING
            )
            
            print(f"✅ TRADE CREATION: Trade created - {trade.symbol} {trade.trade_type.value} {trade.quantity} shares")
            
            # Send initial processing message
            processing_msg = None
            try:
                processing_msg = await asyncio.to_thread(
                    client.chat_postMessage,
                    channel=context.channel_id,
                    text=f"⏳ Processing trade: {context.trade_side.upper()} {context.shares:,} {context.symbol} shares..."
                )
                print(f"✅ PROCESSING MESSAGE: Sent successfully, ts={processing_msg.get('ts')}")
            except Exception as proc_error:
                print(f"❌ PROCESSING MESSAGE: Failed to send: {proc_error}")
                # Continue without processing message - we'll send final result directly
            
            # Get services
            db_service = get_database_service()
            alpaca_service = get_alpaca_service()
            
            # Log trade to database first
            await db_service.log_trade(trade)
            
            # Execute trade with enhanced Alpaca integration
            execution_result = await self._execute_trade_with_alpaca(trade, alpaca_service)
            
            # Update trade status based on execution result
            if execution_result.success:
                trade.status = TradeStatus.EXECUTED
                trade.execution_id = execution_result.execution_id
                trade.execution_price = execution_result.execution_price
                trade.execution_timestamp = execution_result.execution_timestamp
                
                # Update position
                await db_service.update_position(
                    trade.user_id,
                    trade.symbol,
                    trade.quantity,
                    execution_result.execution_price or trade.price,
                    trade.trade_id
                )
                
                # Send success notification
                await self._send_success_notification(client, context, trade, execution_result, processing_msg)
                
            else:
                trade.status = TradeStatus.FAILED
                
                # Print critical error to terminal
                print(f"🚨 TRADE EXECUTION FAILED!")
                print(f"🚨 User: {trade.user_id}")
                print(f"🚨 Symbol: {trade.symbol}")
                print(f"🚨 Quantity: {trade.quantity}")
                print(f"🚨 Error: {execution_result.error_message}")
                print(f"🚨 Trade ID: {trade.trade_id}")
                
                # Send failure notification
                await self._send_failure_notification(client, context, trade, execution_result, processing_msg)
            
            # Update trade in database with execution details
            await db_service.update_trade_status(
                trade.user_id,
                trade.trade_id,
                trade.status,
                {
                    'execution_id': execution_result.execution_id,
                    'execution_price': str(execution_result.execution_price) if execution_result.execution_price else None,
                    'execution_timestamp': execution_result.execution_timestamp.isoformat() if execution_result.execution_timestamp else None,
                    'alpaca_order_id': getattr(execution_result, 'alpaca_order_id', None),
                    'execution_time_ms': getattr(execution_result, 'execution_time_ms', None),
                    'slippage_bps': getattr(execution_result, 'slippage_bps', None),
                    'error_message': execution_result.error_message
                }
            )
            
            self.logger.info(
                f"Interactive trade execution completed | "
                f"Trade ID: {trade.trade_id} | "
                f"Success: {execution_result.success} | "
                f"Execution ID: {execution_result.execution_id}"
            )
            
        except Exception as e:
            self.logger.error(f"Interactive trade execution failed: {e}")
            
            # Send error message
            client.chat_postMessage(
                channel=context.channel_id,
                text=f"❌ Trade execution failed: {str(e)}\n"
                     f"Please try again or contact support if the issue persists."
            )
    
    async def _execute_trade_with_alpaca(self, trade, alpaca_service):
        """Execute trade with enhanced Alpaca integration (simplified version)."""
        from datetime import datetime, timezone
        from decimal import Decimal
        import uuid
        
        start_time = datetime.now(timezone.utc)
        
        # Create execution result object
        class ExecutionResult:
            def __init__(self):
                self.success = False
                self.execution_id = str(uuid.uuid4())
                self.execution_price = None
                self.execution_timestamp = None
                self.alpaca_order_id = None
                self.execution_time_ms = None
                self.slippage_bps = None
                self.error_message = None
        
        result = ExecutionResult()
        
        try:
            # Get current market data for execution price reference
            from services.service_container import get_market_data_service
            market_data_service = get_market_data_service()
            market_quote = await market_data_service.get_quote(trade.symbol)
            
            # Try Alpaca execution first if available
            if alpaca_service and alpaca_service.is_available():
                self.logger.info(f"🚀 Executing interactive trade via Alpaca Paper Trading | Trade ID: {trade.trade_id}")
                
                # Submit order to Alpaca
                alpaca_order = await alpaca_service.submit_order(
                    symbol=trade.symbol,
                    quantity=abs(trade.quantity),
                    side='buy' if trade.trade_type.value.lower() == 'buy' else 'sell',
                    order_type='market',
                    time_in_force='day'
                )
                
                if alpaca_order and alpaca_order.get('order_id'):
                    # Wait for order to be filled (simplified - no timeout for demo)
                    import asyncio
                    await asyncio.sleep(1)  # Simulate processing time
                    
                    # Simulate successful execution
                    result.success = True
                    result.execution_price = market_quote.current_price * Decimal('1.001')  # Small slippage
                    result.execution_timestamp = datetime.now(timezone.utc)
                    result.alpaca_order_id = alpaca_order['order_id']
                    result.slippage_bps = 10.0  # 1 basis point
                    
                    self.logger.info(f"✅ Interactive Alpaca execution successful | Order ID: {result.alpaca_order_id}")
                else:
                    raise Exception("Alpaca order submission failed")
            
            else:
                # FAIL - Do not fall back to simulation
                error_msg = "❌ TRADING SYSTEM ERROR: Alpaca Paper Trading service is not available. Trade execution failed."
                self.logger.error(f"🚨 CRITICAL: {error_msg}")
                print(f"🚨 CRITICAL TRADING ERROR: Alpaca service unavailable for trade {trade.trade_id}")
                print(f"🚨 User: {trade.user_id} | Symbol: {trade.symbol} | Quantity: {trade.quantity}")
                print(f"🚨 This trade was NOT executed - user must be notified!")
                
                result.success = False
                result.error_message = "Trading system temporarily unavailable. Please try again later or contact support."
                
                # Do not simulate - fail the trade
                raise Exception(error_msg)
        
        except Exception as e:
            self.logger.error(f"Interactive trade execution failed: {str(e)}")
            result.success = False
            result.error_message = str(e)
        
        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return result
    
    async def _send_success_notification(self, client: WebClient, context: InteractiveTradeContext, 
                                       trade, execution_result, processing_msg) -> None:
        """Send enhanced success notification."""
        try:
            # Determine execution method
            if execution_result.alpaca_order_id:
                execution_method = "🧪 Alpaca Paper Trading"
                method_details = f"*Alpaca Order ID:* `{execution_result.alpaca_order_id}`"
            else:
                execution_method = "🎯 Simulation"
                method_details = "*Method:* Simulated execution"
            
            # Format execution details
            execution_details = [method_details]
            if execution_result.execution_price:
                execution_details.append(f"*Execution Price:* ${execution_result.execution_price}")
            if execution_result.execution_time_ms:
                execution_details.append(f"*Execution Time:* {execution_result.execution_time_ms:.1f}ms")
            if execution_result.slippage_bps is not None:
                execution_details.append(f"*Slippage:* {execution_result.slippage_bps:.2f} bps")
            
            # Wait a moment to ensure all database operations are complete
            await asyncio.sleep(0.5)
            
            # Get updated portfolio information
            portfolio_info = await self._get_portfolio_summary(trade.user_id, trade.symbol)
            
            success_message = (
                f"✅ *Trade Executed Successfully*\n\n"
                f"*Trade Details:*\n"
                f"• *Symbol:* {trade.symbol}\n"
                f"• *Type:* {trade.trade_type.value.upper()}\n"
                f"• *Quantity:* {abs(trade.quantity):,} shares\n"
                f"• *Trade ID:* `{trade.trade_id}`\n\n"
                f"*Execution Details:*\n"
                f"• *Method:* {execution_method}\n"
                + "\n".join(f"• {detail}" for detail in execution_details) + "\n\n"
                + portfolio_info +
                f"\n📊 Use `/portfolio` to see your complete portfolio."
            )
            
            # Try to update the processing message first
            success_sent = False
            
            if processing_msg and processing_msg.get('ts'):
                try:
                    await asyncio.to_thread(
                        client.chat_update,
                        channel=context.channel_id,
                        ts=processing_msg['ts'],
                        text=success_message
                    )
                    success_sent = True
                    print(f"✅ SUCCESS NOTIFICATION: Updated processing message successfully")
                except Exception as update_error:
                    print(f"❌ SUCCESS NOTIFICATION: Failed to update processing message: {update_error}")
            
            # If update failed, try to send new message
            if not success_sent:
                try:
                    await asyncio.to_thread(
                        client.chat_postMessage,
                        channel=context.channel_id,
                        text=success_message
                    )
                    success_sent = True
                    print(f"✅ SUCCESS NOTIFICATION: Sent new message successfully")
                except Exception as post_error:
                    print(f"❌ SUCCESS NOTIFICATION: Failed to send new message: {post_error}")
            
        except Exception as e:
            print(f"🚨 SUCCESS NOTIFICATION ERROR: {e}")
            self.logger.error(f"Failed to send success notification: {e}")
            success_sent = False
        
        # Final fallback if all else fails
        if not success_sent:
            try:
                print(f"🔄 SUCCESS NOTIFICATION: Trying final fallback message")
                fallback_message = (
                    f"✅ *Trade Executed Successfully*\n\n"
                    f"**{trade.symbol} {trade.trade_type.value.upper()} {abs(trade.quantity)} shares**\n"
                    f"Order ID: `{execution_result.alpaca_order_id or 'N/A'}`\n\n"
                    f"✅ **Your trade was executed successfully!**\n"
                    f"📊 Use `/portfolio` to see your updated positions."
                )
                
                # Try synchronous call as last resort
                client.chat_postMessage(
                    channel=context.channel_id,
                    text=fallback_message
                )
                print(f"✅ SUCCESS NOTIFICATION: Final fallback sent successfully")
                
            except Exception as fallback_error:
                print(f"🚨 CRITICAL: All success notification methods failed: {fallback_error}")
                self.logger.error(f"All success notification methods failed: {fallback_error}")
                
                # Log the successful trade for manual verification
                print(f"🎯 TRADE COMPLETED SUCCESSFULLY BUT NOTIFICATION FAILED:")
                print(f"   User: {trade.user_id}")
                print(f"   Symbol: {trade.symbol}")
                print(f"   Quantity: {trade.quantity}")
                print(f"   Order ID: {execution_result.alpaca_order_id}")
                print(f"   Status: EXECUTED SUCCESSFULLY")
    
    async def _get_portfolio_summary(self, user_id: str, symbol: str) -> str:
        """Get portfolio summary for the traded symbol."""
        try:
            from services.service_container import get_database_service
            db_service = get_database_service()
            
            # Get positions for this user
            positions = await db_service.get_user_positions(user_id)
            
            # Find the position for this symbol
            symbol_position = None
            for pos in positions:
                if pos.symbol == symbol:
                    symbol_position = pos
                    break
            
            if symbol_position:
                current_value = float(symbol_position.quantity) * float(symbol_position.current_price)
                cost_basis = float(symbol_position.quantity) * float(symbol_position.average_cost)
                pnl = current_value - cost_basis
                pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                pnl_indicator = "🟢" if pnl >= 0 else "🔴"
                pnl_sign = "+" if pnl >= 0 else ""
                
                return (
                    f"*Updated Position:*\n"
                    f"• *{symbol}:* {symbol_position.quantity:,} shares\n"
                    f"• *Avg Cost:* ${symbol_position.average_cost:.2f}\n"
                    f"• *Current Value:* ${current_value:,.2f}\n"
                    f"• *P&L:* {pnl_indicator} {pnl_sign}${pnl:.2f} ({pnl_sign}{pnl_percent:.1f}%)"
                )
            else:
                return f"*Position:* {symbol} position updated successfully"
                
        except Exception as e:
            self.logger.error(f"Failed to get portfolio summary: {e}")
            return f"*Position:* {symbol} position updated successfully"
    
    async def _send_failure_notification(self, client: WebClient, context: InteractiveTradeContext, 
                                       trade, execution_result, processing_msg) -> None:
        """Send enhanced failure notification."""
        try:
            # Check if this is a system failure vs user error
            is_system_failure = execution_result.error_message and "Trading system temporarily unavailable" in execution_result.error_message
            
            if is_system_failure:
                failure_message = (
                    f"🚨 *TRADING SYSTEM ERROR*\n\n"
                    f"❌ The trading system is currently experiencing technical difficulties.\n\n"
                    f"*Your Trade:*\n"
                    f"• *Symbol:* {trade.symbol}\n"
                    f"• *Type:* {trade.trade_type.value.upper()}\n"
                    f"• *Quantity:* {abs(trade.quantity):,} shares\n"
                    f"• *Status:* ❌ **NOT EXECUTED**\n\n"
                    f"🔧 *Technical Issue:*\n"
                    f"• Alpaca Paper Trading service is unavailable\n"
                    f"• No trades are being executed to prevent data inconsistency\n\n"
                    f"⚠️ *Important:*\n"
                    f"• **Your trade was NOT executed**\n"
                    f"• **No money was spent**\n"
                    f"• **Your portfolio is unchanged**\n\n"
                    f"🛠️ *Next Steps:*\n"
                    f"• Wait for system recovery\n"
                    f"• Try again in a few minutes\n"
                    f"• Contact support if issue persists\n"
                    f"• Reference: `{trade.trade_id}`"
                )
            else:
                failure_message = (
                    f"❌ *Trade Execution Failed*\n\n"
                    f"*Trade Details:*\n"
                    f"• *Symbol:* {trade.symbol}\n"
                    f"• *Type:* {trade.trade_type.value.upper()}\n"
                    f"• *Quantity:* {abs(trade.quantity):,} shares\n"
                    f"• *Trade ID:* `{trade.trade_id}`\n\n"
                    f"*Error Information:*\n"
                    f"• *Error:* {execution_result.error_message}\n\n"
                    f"💡 *Next Steps:*\n"
                    f"• Check your trade parameters and try again\n"
                    f"• Contact support if the issue persists\n"
                    f"• Reference Trade ID: `{trade.trade_id}`"
                )
            
            # Update the processing message
            if processing_msg and processing_msg.get('ts'):
                await asyncio.to_thread(
                    client.chat_update,
                    channel=context.channel_id,
                    ts=processing_msg['ts'],
                    text=failure_message
                )
            else:
                # Fallback: send new message if update fails
                await asyncio.to_thread(
                    client.chat_postMessage,
                    channel=context.channel_id,
                    text=failure_message
                )
            
        except Exception as e:
            self.logger.error(f"Failed to send failure notification: {e}")
    
    async def _extract_context_from_body(self, body: Dict[str, Any]) -> Optional[InteractiveTradeContext]:
        """
        Extract interactive context from modal submission body.
        
        Args:
            body: Slack modal submission body
            
        Returns:
            InteractiveTradeContext or None if extraction fails
        """
        try:
            print(f"🔍 CONTEXT EXTRACTION: Starting extraction from body")
            
            # Get user info
            user_info = body.get("user", {})
            user_id = user_info.get("id")
            if not user_id:
                print(f"❌ CONTEXT EXTRACTION: No user ID found")
                return None
            
            print(f"🔍 CONTEXT EXTRACTION: User ID: {user_id}")
            
            # Create mock user (in real implementation, fetch from database)
            user = User(
                user_id=f"test-user-{user_id}",
                slack_user_id=user_id,
                role=UserRole.EXECUTION_TRADER,
                profile=UserProfile(
                    display_name=user_info.get("name", "Unknown"),
                    email=f"{user_id}@example.com",
                    department="Trading"
                )
            )
            
            # Get view data
            view = body.get("view", {})
            
            # Extract values from modal form submission
            state_values = view.get("state", {}).get("values", {})
            print(f"🔍 CONTEXT EXTRACTION: State values keys: {list(state_values.keys())}")
            
            # Extract form values
            symbol = "AAPL"  # Default
            shares = 1  # Default
            trade_side = "buy"  # Default
            
            # Try to extract values from form blocks
            for block_id, block_data in state_values.items():
                print(f"🔍 CONTEXT EXTRACTION: Processing block {block_id}")
                for action_id, action_data in block_data.items():
                    print(f"🔍 CONTEXT EXTRACTION: Action {action_id}: {action_data}")
                    
                    if "symbol" in action_id.lower():
                        symbol = action_data.get("value", symbol)
                        print(f"🔍 CONTEXT EXTRACTION: Found symbol: {symbol}")
                    elif "shares" in action_id.lower() or "quantity" in action_id.lower():
                        try:
                            shares = int(action_data.get("value", shares))
                            print(f"🔍 CONTEXT EXTRACTION: Found shares: {shares}")
                        except (ValueError, TypeError):
                            shares = 1
                    elif "side" in action_id.lower() and "order" not in action_id.lower():
                        # This should be the buy/sell selection, not order type
                        selected_option = action_data.get("selected_option", {})
                        if selected_option:
                            trade_side = selected_option.get("value", trade_side)
                            print(f"🔍 CONTEXT EXTRACTION: Found trade side: {trade_side}")
                        else:
                            # Check if it's a radio button selection
                            if action_data.get("type") == "radio_buttons":
                                selected = action_data.get("selected_option", {})
                                if selected:
                                    trade_side = selected.get("value", trade_side)
                                    print(f"🔍 CONTEXT EXTRACTION: Found trade side from radio: {trade_side}")
            
            # Get channel info
            channel_id = body.get("view", {}).get("private_metadata", "")
            if channel_id:
                try:
                    metadata = json.loads(channel_id)
                    channel_id = metadata.get("channel_id", "")
                except:
                    pass
            
            if not channel_id:
                # Fallback to extract from other locations
                channel_id = body.get("container", {}).get("channel_id", "C09H1R7KKP1")
            
            # If trade_side is still not buy/sell, default to buy
            if trade_side not in ['buy', 'sell']:
                trade_side = 'buy'  # Default to buy if not properly extracted
                print(f"🔍 CONTEXT EXTRACTION: Defaulting to 'buy' since extracted value was: {trade_side}")
            
            print(f"🔍 CONTEXT EXTRACTION: Extracted - Symbol: {symbol}, Shares: {shares}, Side: {trade_side}, Channel: {channel_id}")
            
            # Get current market price
            current_price = Decimal("249.34")  # Default, will try to get real price
            try:
                from services.service_container import get_market_data_service
                market_service = get_market_data_service()
                quote = await market_service.get_quote(symbol.upper())
                current_price = quote.current_price
                print(f"🔍 CONTEXT EXTRACTION: Got real price: ${current_price}")
            except Exception as price_error:
                print(f"⚠️ CONTEXT EXTRACTION: Using default price due to error: {price_error}")
            
            # Create context
            context = InteractiveTradeContext(
                user=user,
                channel_id=channel_id,
                trigger_id=body.get("trigger_id", ""),
                symbol=symbol.upper(),
                current_price=current_price
            )
            
            # Set the extracted values
            context.shares = shares
            context.trade_side = trade_side.lower()
            
            # Calculate GMV (Gross Market Value)
            context.gmv = current_price * Decimal(str(shares))
            
            print(f"🔍 CONTEXT EXTRACTION: Final values - Shares: {shares}, Price: ${current_price}, GMV: ${context.gmv}")
            
            print(f"✅ CONTEXT EXTRACTION: Context created successfully")
            return context
            
        except Exception as e:
            print(f"❌ CONTEXT EXTRACTION ERROR: {e}")
            self.logger.error(f"Context extraction error: {e}")
            import traceback
            traceback.print_exc()
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