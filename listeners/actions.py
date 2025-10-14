"""
Comprehensive Slack Interactive Action Handlers for Jain Global Trading Bot

This module provides complete action handling functionality for button clicks, form
submissions, and modal interactions. It implements trade confirmation processing,
risk analysis triggers, UI state management, comprehensive validation, error handling,
user feedback mechanisms, action routing system with middleware support, and
comprehensive request/response logging.

The ActionHandler class manages complex UI workflows including trade execution,
risk analysis, market data retrieval, and high-risk confirmations while maintaining
detailed audit trails and providing rich user feedback throughout the process.
"""

import asyncio
from utils.async_compat import to_thread
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, List, Tuple, Union, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import json

if TYPE_CHECKING:
    from services.service_container import ServiceContainer

from slack_bolt import App, Ack, BoltContext
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Import our services and models
from services.auth import AuthService, AuthenticationError, AuthorizationError, SessionError
from services.database import DatabaseService, DatabaseError, NotFoundError
from services.market_data import MarketDataService, MarketDataError, MarketQuote
from services.risk_analysis import RiskAnalysisService, RiskAnalysisError, RiskAnalysis
from services.trading_api import TradingAPIService, TradingError, TradeExecution
from services.service_container import ServiceContainer, get_container
from models.trade import Trade, TradeType, TradeStatus, RiskLevel
from models.user import User, UserRole, Permission
from ui.trade_widget import TradeWidget, WidgetContext, WidgetState, UITheme
from ui.notifications import NotificationService
from utils.validators import validate_symbol, validate_quantity, validate_price, ValidationError
from utils.formatters import format_money, format_percent
from config.settings import get_config

# Configure logging
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enumeration of supported action types."""
    GET_MARKET_DATA = "get_market_data"
    ANALYZE_RISK = "analyze_risk"
    SUBMIT_TRADE = "submit_trade"
    CONFIRM_HIGH_RISK = "confirm_high_risk"
    CANCEL_TRADE = "cancel_trade"
    REFRESH_DATA = "refresh_data"
    VIEW_DETAILS = "view_details"


class ActionError(Exception):
    """Base exception for action handling errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, user_friendly: bool = True):
        self.message = message
        self.error_code = error_code
        self.user_friendly = user_friendly
        super().__init__(self.message)


class ActionValidationError(ActionError):
    """Exception for action validation errors."""
    pass


class ActionProcessingError(ActionError):
    """Exception for action processing errors."""
    pass


@dataclass
class ActionContext:
    """Context information for action processing."""
    action_type: ActionType
    user_id: str
    slack_user_id: str
    team_id: str
    channel_id: str
    trigger_id: str
    view_id: Optional[str]
    callback_id: str
    
    # Action payload data
    action_id: str
    block_id: Optional[str]
    value: Optional[str]
    selected_option: Optional[Dict[str, Any]]
    
    # Form submission data
    state_values: Optional[Dict[str, Any]]
    private_metadata: Optional[Dict[str, Any]]
    
    # Request metadata
    request_id: str
    timestamp: datetime
    response_url: Optional[str]
    
    # Authentication context
    user: Optional[User] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


class ActionMetrics:
    """Action execution metrics tracking."""
    
    def __init__(self):
        self.actions_processed = 0
        self.actions_successful = 0
        self.actions_failed = 0
        self.market_data_requests = 0
        self.risk_analyses = 0
        self.trades_submitted = 0
        self.high_risk_confirmations = 0
        self.response_times = {}
        self.error_counts = {}
        
    def record_action(self, action_type: ActionType, success: bool, response_time: float,
                     error_type: Optional[str] = None):
        """Record action execution metrics."""
        self.actions_processed += 1
        if success:
            self.actions_successful += 1
        else:
            self.actions_failed += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Track response times by action type
        if action_type.value not in self.response_times:
            self.response_times[action_type.value] = []
        self.response_times[action_type.value].append(response_time)
        
        # Keep only last 100 response times per action type
        if len(self.response_times[action_type.value]) > 100:
            self.response_times[action_type.value] = self.response_times[action_type.value][-100:]
        
        # Track specific action types
        if action_type == ActionType.GET_MARKET_DATA:
            self.market_data_requests += 1
        elif action_type == ActionType.ANALYZE_RISK:
            self.risk_analyses += 1
        elif action_type == ActionType.SUBMIT_TRADE:
            self.trades_submitted += 1
        elif action_type == ActionType.CONFIRM_HIGH_RISK:
            self.high_risk_confirmations += 1
    
    def get_average_response_time(self, action_type: Optional[ActionType] = None) -> float:
        """Get average response time in milliseconds."""
        if action_type:
            times = self.response_times.get(action_type.value, [])
            return sum(times) / len(times) * 1000 if times else 0.0
        else:
            all_times = []
            for times in self.response_times.values():
                all_times.extend(times)
            return sum(all_times) / len(all_times) * 1000 if all_times else 0.0
    
    def get_success_rate(self) -> float:
        """Get action success rate as percentage."""
        return (self.actions_successful / self.actions_processed * 100) if self.actions_processed > 0 else 0.0


class ActionHandler:
    """
    Comprehensive interactive action handler with validation and processing.
    
    This class provides complete action processing functionality including:
    - Button click and form submission handling
    - Trade confirmation processing and validation
    - Risk analysis triggers and result processing
    - UI state management and modal updates
    - Market data retrieval and display
    - Comprehensive error handling and user feedback
    - Action routing system with middleware support
    - Request/response logging and audit trails
    - Performance metrics and monitoring
    """
    
    def __init__(self, auth_service: AuthService, database_service: DatabaseService,
                 market_data_service: MarketDataService, risk_analysis_service: RiskAnalysisService,
                 trading_api_service: TradingAPIService):
        """
        Initialize action handler with required services.
        
        Args:
            auth_service: Authentication service instance
            database_service: Database service instance
            market_data_service: Market data service instance
            risk_analysis_service: Risk analysis service instance
            trading_api_service: Trading API service instance
        """
        self.auth_service = auth_service
        self.db_service = database_service
        self.market_data_service = market_data_service
        self.risk_analysis_service = risk_analysis_service
        self.trading_api_service = trading_api_service
        self.config = get_config()
        
        # Initialize UI components
        self.trade_widget = TradeWidget()
        self.notification_service = NotificationService()
        
        # Metrics tracking
        self.metrics = ActionMetrics()
        
        # Action routing table
        self.action_routes = {
            ActionType.GET_MARKET_DATA: self._handle_get_market_data,
            ActionType.ANALYZE_RISK: self._handle_analyze_risk,
            ActionType.SUBMIT_TRADE: self._handle_submit_trade,
            ActionType.CONFIRM_HIGH_RISK: self._handle_confirm_high_risk,
            ActionType.CANCEL_TRADE: self._handle_cancel_trade,
            ActionType.REFRESH_DATA: self._handle_refresh_data,
            ActionType.VIEW_DETAILS: self._handle_view_details
        }
        
        # State management for ongoing operations
        self._active_operations = {}  # request_id -> operation_data
        
        logger.info("ActionHandler initialized with comprehensive processing capabilities")
    
    async def process_action(self, action_type: ActionType, body: Dict[str, Any],
                           client: WebClient, ack: Ack, context: BoltContext) -> None:
        """
        Process interactive action with comprehensive validation and error handling.
        
        Args:
            action_type: Type of action being processed
            body: Slack action payload
            client: Slack WebClient instance
            ack: Slack acknowledgment function
            context: Bolt context
        """
        start_time = time.time()
        action_context = None
        success = False
        error_type = None
        
        try:
            # Acknowledge action immediately (within 3 seconds)
            ack()
            
            # Create action context
            action_context = self._create_action_context(action_type, body, context)
            
            logger.info(
                "Processing action",
                action_type=action_type.value,
                user_id=action_context.slack_user_id,
                channel_id=action_context.channel_id,
                request_id=action_context.request_id
            )
            
            # Validate and authenticate
            await self._validate_and_authenticate(action_context)
            
            # Route to specific action handler
            handler = self.action_routes.get(action_type)
            if not handler:
                raise ActionError(f"Unknown action type: {action_type.value}", "UNKNOWN_ACTION")
            
            # Execute action handler
            await handler(action_context, client)
            
            success = True
            logger.info(
                "Action processed successfully",
                action_type=action_type.value,
                user_id=action_context.slack_user_id,
                request_id=action_context.request_id,
                response_time=f"{(time.time() - start_time) * 1000:.2f}ms"
            )
            
        except AuthenticationError as e:
            error_type = "AUTHENTICATION"
            await self._send_error_response(
                client, action_context,
                f"🔐 Authentication failed: {e.message}"
            )
            logger.warning(
                "Authentication failed for action",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except AuthorizationError as e:
            error_type = "AUTHORIZATION"
            await self._send_error_response(
                client, action_context,
                f"🚫 Access denied: {e.message}"
            )
            logger.warning(
                "Authorization failed for action",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except ActionValidationError as e:
            error_type = "VALIDATION"
            await self._send_error_response(
                client, action_context,
                f"❌ Invalid action: {e.message}"
            )
            logger.warning(
                "Action validation failed",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except MarketDataError as e:
            error_type = "MARKET_DATA"
            await self._send_error_response(
                client, action_context,
                f"📊 Market data error: {e.message}"
            )
            logger.warning(
                "Market data error",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except RiskAnalysisError as e:
            error_type = "RISK_ANALYSIS"
            await self._send_error_response(
                client, action_context,
                f"🔍 Risk analysis error: {e.message}"
            )
            logger.warning(
                "Risk analysis error",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except TradingError as e:
            error_type = "TRADING"
            await self._send_error_response(
                client, action_context,
                f"💼 Trading error: {e.message}"
            )
            logger.warning(
                "Trading error",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except SlackApiError as e:
            error_type = "SLACK_API"
            await self._send_error_response(
                client, action_context,
                "📡 Communication error with Slack. Please try again."
            )
            logger.error(
                "Slack API error",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e)
            )
            
        except Exception as e:
            error_type = "SYSTEM"
            await self._send_error_response(
                client, action_context,
                "⚠️ System error occurred. Please try again or contact support."
            )
            logger.error(
                "Unexpected error processing action",
                action_type=action_type.value if action_type else "unknown",
                user_id=action_context.slack_user_id if action_context else "unknown",
                error=str(e),
                exc_info=True
            )
            
        finally:
            # Record metrics
            response_time = time.time() - start_time
            self.metrics.record_action(action_type, success, response_time, error_type)
            
            # Log audit event
            if action_context:
                await self._log_audit_event(action_context, success, error_type, response_time)
    
    def _create_action_context(self, action_type: ActionType, body: Dict[str, Any],
                              context: BoltContext) -> ActionContext:
        """Create action context from Slack payload."""
        # Extract action data based on payload type
        if 'actions' in body and body['actions']:
            action = body['actions'][0]
            action_id = action.get('action_id', '')
            block_id = action.get('block_id')
            value = action.get('value')
            selected_option = action.get('selected_option')
        else:
            action_id = ''
            block_id = None
            value = None
            selected_option = None
        
        # Extract view data if present
        view = body.get('view', {})
        view_id = view.get('id')
        callback_id = view.get('callback_id', body.get('callback_id', ''))
        state_values = view.get('state', {}).get('values', {})
        private_metadata = json.loads(view.get('private_metadata', '{}')) if view.get('private_metadata') else {}
        
        # Extract user and channel info
        user = body.get('user', {})
        channel = body.get('channel', {})
        
        return ActionContext(
            action_type=action_type,
            user_id=user.get('id', ''),
            slack_user_id=user.get('id', ''),
            team_id=body.get('team', {}).get('id', ''),
            channel_id=channel.get('id', private_metadata.get('channel_id', '')),
            trigger_id=body.get('trigger_id', ''),
            view_id=view_id,
            callback_id=callback_id,
            action_id=action_id,
            block_id=block_id,
            value=value,
            selected_option=selected_option,
            state_values=state_values,
            private_metadata=private_metadata,
            timestamp=datetime.now(timezone.utc),
            response_url=body.get('response_url')
        )
    
    async def _validate_and_authenticate(self, action_context: ActionContext) -> None:
        """Validate action and authenticate user."""
        # Validate basic action structure
        if not action_context.slack_user_id:
            raise ActionValidationError("Missing user ID", "MISSING_USER_ID")
        
        if not action_context.team_id:
            raise ActionValidationError("Missing team ID", "MISSING_TEAM_ID")
        
        # Authenticate user using existing session or create new one
        try:
            user, session = await self.auth_service.authenticate_slack_user(
                action_context.slack_user_id,
                action_context.team_id,
                action_context.channel_id
            )
            
            action_context.user = user
            action_context.session_id = session.session_id
            
        except AuthenticationError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            raise AuthenticationError(f"Failed to authenticate user: {str(e)}", "AUTH_FAILED")
    
    async def _handle_get_market_data(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle market data retrieval action."""
        try:
            # Extract symbol from form data
            symbol = self._extract_form_value(action_context, 'symbol_input', 'symbol')
            if not symbol:
                raise ActionValidationError("Symbol is required for market data", "MISSING_SYMBOL")
            
            # Validate symbol
            try:
                validate_symbol(symbol)
                symbol = symbol.upper()
            except ValidationError as e:
                raise ActionValidationError(f"Invalid symbol: {e.message}", "INVALID_SYMBOL")
            
            # Check user permissions
            if not action_context.user.has_permission(Permission.VIEW_MARKET_DATA):
                raise AuthorizationError(
                    "You don't have permission to view market data",
                    Permission.VIEW_MARKET_DATA.value
                )
            
            # Update modal to show loading state
            widget_context = self._create_widget_context(action_context)
            widget_context.symbol = symbol
            widget_context.state = WidgetState.LOADING_MARKET_DATA
            
            loading_modal = self.trade_widget.create_trade_modal(widget_context)
            await self._update_modal(client, action_context.view_id, loading_modal)
            
            # Fetch market data
            market_quote = await self.market_data_service.get_quote(symbol)
            
            # Update modal with market data
            widget_context.market_quote = market_quote
            widget_context.state = WidgetState.MARKET_DATA_LOADED
            
            updated_modal = self.trade_widget.update_modal_with_market_data(widget_context, market_quote)
            await self._update_modal(client, action_context.view_id, updated_modal)
            
            logger.info(
                "Market data retrieved successfully",
                user_id=action_context.user.user_id,
                symbol=symbol,
                price=float(market_quote.current_price)
            )
            
        except ValidationError as e:
            raise ActionValidationError(str(e), "VALIDATION_FAILED")
        except MarketDataError:
            # Re-raise market data errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting market data: {str(e)}")
            raise ActionProcessingError(f"Failed to get market data: {str(e)}", "MARKET_DATA_FAILED")
    
    async def _handle_analyze_risk(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle risk analysis action."""
        try:
            # Extract trade data from form
            trade_data = self._extract_trade_data(action_context)
            
            # Validate trade data
            self._validate_trade_data(trade_data)
            
            # Check user permissions
            if not action_context.user.has_permission(Permission.ANALYZE_RISK):
                raise AuthorizationError(
                    "You don't have permission to analyze risk",
                    Permission.ANALYZE_RISK.value
                )
            
            # Update modal to show analyzing state
            widget_context = self._create_widget_context(action_context)
            widget_context.symbol = trade_data['symbol']
            widget_context.quantity = trade_data['quantity']
            widget_context.trade_type = trade_data['trade_type']
            widget_context.price = trade_data['price']
            widget_context.state = WidgetState.ANALYZING_RISK
            
            analyzing_modal = self.trade_widget.create_trade_modal(widget_context)
            await self._update_modal(client, action_context.view_id, analyzing_modal)
            
            # Create trade object for analysis
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                user_id=action_context.user.user_id,
                symbol=trade_data['symbol'],
                quantity=trade_data['quantity'],
                trade_type=trade_data['trade_type'],
                price=trade_data['price'],
                timestamp=datetime.now(timezone.utc),
                status=TradeStatus.PENDING
            )
            
            # Get user's current portfolio
            positions = await self.db_service.get_user_positions(action_context.user.user_id)
            
            # Perform risk analysis
            risk_analysis = await self.risk_analysis_service.analyze_trade_risk(trade, positions)
            
            # Update modal with risk analysis
            widget_context.risk_analysis = risk_analysis
            widget_context.state = WidgetState.RISK_ANALYSIS_COMPLETE
            
            if risk_analysis.is_high_risk:
                widget_context.confirmation_required = True
                widget_context.state = WidgetState.HIGH_RISK_CONFIRMATION
                widget_context.theme = UITheme.HIGH_RISK
            
            updated_modal = self.trade_widget.update_modal_with_risk_analysis(widget_context, risk_analysis)
            await self._update_modal(client, action_context.view_id, updated_modal)
            
            logger.info(
                "Risk analysis completed",
                user_id=action_context.user.user_id,
                trade_id=trade.trade_id,
                risk_level=risk_analysis.overall_risk_level.value,
                risk_score=risk_analysis.overall_risk_score
            )
            
        except ValidationError as e:
            raise ActionValidationError(str(e), "VALIDATION_FAILED")
        except RiskAnalysisError:
            # Re-raise risk analysis errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error analyzing risk: {str(e)}")
            raise ActionProcessingError(f"Failed to analyze risk: {str(e)}", "RISK_ANALYSIS_FAILED")
    
    async def _handle_submit_trade(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle trade submission action."""
        try:
            # Extract and validate trade data
            trade_data = self._extract_trade_data(action_context)
            self._validate_trade_data(trade_data)
            
            # Check user permissions
            if not action_context.user.has_permission(Permission.EXECUTE_TRADES):
                raise AuthorizationError(
                    "You don't have permission to execute trades",
                    Permission.EXECUTE_TRADES.value
                )
            
            # Check for high-risk confirmation if required
            if self._requires_high_risk_confirmation(action_context):
                confirmation_text = self._extract_form_value(action_context, 'confirmation_input', 'confirmation_text')
                if not confirmation_text or confirmation_text.lower().strip() != 'confirm':
                    raise ActionValidationError(
                        "High-risk trade requires typing 'confirm' in the confirmation field",
                        "CONFIRMATION_REQUIRED"
                    )
            
            # Create trade object
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                user_id=action_context.user.user_id,
                symbol=trade_data['symbol'],
                quantity=trade_data['quantity'],
                trade_type=trade_data['trade_type'],
                price=trade_data['price'],
                timestamp=datetime.now(timezone.utc),
                status=TradeStatus.PENDING
            )
            
            # Update modal to show submitting state
            widget_context = self._create_widget_context(action_context)
            widget_context.state = WidgetState.SUBMITTING
            
            submitting_modal = self.trade_widget.create_trade_modal(widget_context)
            await self._update_modal(client, action_context.view_id, submitting_modal)
            
            # Log trade to database
            await self.db_service.log_trade(trade)
            
            # Submit trade to trading API
            execution_result = await self.trading_api_service.execute_trade(trade)
            
            # Update trade status based on execution result
            if execution_result.success:
                trade.status = TradeStatus.EXECUTED
                trade.execution_id = execution_result.execution_id
                
                # Check trade against active risk alerts
                try:
                    await alert_monitor.check_trade_against_alerts(trade)
                    logger.info(f"Trade {trade.trade_id} checked against risk alerts")
                except Exception as e:
                    logger.error(f"Failed to check risk alerts: {e}")
                    # Don't fail trade if alert check fails
                
                # Update position
                await self.db_service.update_position(
                    trade.user_id,
                    trade.symbol,
                    trade.quantity if trade.trade_type == TradeType.BUY else -trade.quantity,
                    trade.price,
                    trade.trade_id
                )
                
                # Send success notification
                await self._send_trade_success_notification(client, action_context, trade, execution_result)
                
            else:
                trade.status = TradeStatus.FAILED
                
                # Send failure notification
                await self._send_trade_failure_notification(client, action_context, trade, execution_result.error_message)
            
            # Update trade in database
            await self.db_service.update_trade_status(
                trade.user_id,
                trade.trade_id,
                trade.status,
                {
                    'execution_id': execution_result.execution_id,
                    'execution_price': str(execution_result.execution_price) if execution_result.execution_price else None,
                    'execution_timestamp': execution_result.execution_timestamp.isoformat() if execution_result.execution_timestamp else None,
                    'error_message': execution_result.error_message
                }
            )
            
            # Close modal
            await self._close_modal(client, action_context.view_id)
            
            logger.info(
                "Trade submitted successfully",
                user_id=action_context.user.user_id,
                trade_id=trade.trade_id,
                status=trade.status.value,
                execution_id=execution_result.execution_id
            )
            
        except ValidationError as e:
            raise ActionValidationError(str(e), "VALIDATION_FAILED")
        except TradingError:
            # Re-raise trading errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error submitting trade: {str(e)}")
            raise ActionProcessingError(f"Failed to submit trade: {str(e)}", "TRADE_SUBMIT_FAILED")
    
    async def _handle_confirm_high_risk(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle high-risk trade confirmation action."""
        try:
            # This is handled as part of submit_trade, but we can add specific logging here
            logger.info(
                "High-risk trade confirmation processed",
                user_id=action_context.user.user_id,
                request_id=action_context.request_id
            )
            
            # Delegate to submit_trade handler
            await self._handle_submit_trade(action_context, client)
            
        except Exception as e:
            logger.error(f"Error handling high-risk confirmation: {str(e)}")
            raise
    
    async def _handle_cancel_trade(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle trade cancellation action."""
        try:
            # Close modal
            await self._close_modal(client, action_context.view_id)
            
            # Send cancellation message
            await to_thread(
                client.chat_postEphemeral,
                channel=action_context.channel_id,
                user=action_context.slack_user_id,
                text="❌ Trade cancelled by user."
            )
            
            logger.info(
                "Trade cancelled",
                user_id=action_context.user.user_id,
                request_id=action_context.request_id
            )
            
        except Exception as e:
            logger.error(f"Error handling trade cancellation: {str(e)}")
            raise ActionProcessingError(f"Failed to cancel trade: {str(e)}", "CANCEL_FAILED")
    
    async def _handle_refresh_data(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle data refresh action."""
        try:
            # Extract current trade data
            trade_data = self._extract_trade_data(action_context)
            
            if trade_data.get('symbol'):
                # Refresh market data
                await self._handle_get_market_data(action_context, client)
            else:
                raise ActionValidationError("No symbol available for data refresh", "NO_SYMBOL")
            
        except Exception as e:
            logger.error(f"Error handling data refresh: {str(e)}")
            raise ActionProcessingError(f"Failed to refresh data: {str(e)}", "REFRESH_FAILED")
    
    async def _handle_view_details(self, action_context: ActionContext, client: WebClient) -> None:
        """Handle view details action."""
        try:
            # This could show additional details in a new modal or update the current one
            # For now, we'll just log the action
            logger.info(
                "View details requested",
                user_id=action_context.user.user_id,
                request_id=action_context.request_id
            )
            
            # Could implement detailed view modal here
            await to_thread(
                client.chat_postEphemeral,
                channel=action_context.channel_id,
                user=action_context.slack_user_id,
                text="📋 Detailed view feature coming soon!"
            )
            
        except Exception as e:
            logger.error(f"Error handling view details: {str(e)}")
            raise ActionProcessingError(f"Failed to show details: {str(e)}", "VIEW_DETAILS_FAILED")
    
    def _extract_form_value(self, action_context: ActionContext, block_id: str, action_id: str) -> Optional[str]:
        """Extract value from form state."""
        if not action_context.state_values:
            return None
        
        block_data = action_context.state_values.get(block_id, {})
        action_data = block_data.get(action_id, {})
        
        # Handle different input types
        if 'value' in action_data:
            return action_data['value']
        elif 'selected_option' in action_data:
            return action_data['selected_option'].get('value')
        elif 'selected_options' in action_data:
            options = action_data['selected_options']
            return options[0].get('value') if options else None
        
        return None
    
    def _extract_trade_data(self, action_context: ActionContext) -> Dict[str, Any]:
        """Extract trade data from form state."""
        trade_data = {}
        
        # Extract symbol
        symbol = self._extract_form_value(action_context, 'symbol_input', 'symbol')
        if symbol:
            trade_data['symbol'] = symbol.upper()
        
        # Extract quantity
        quantity_str = self._extract_form_value(action_context, 'quantity_input', 'quantity')
        if quantity_str:
            try:
                trade_data['quantity'] = int(quantity_str)
            except ValueError:
                raise ValidationError(f"Invalid quantity: {quantity_str}")
        
        # Extract price
        price_str = self._extract_form_value(action_context, 'price_input', 'price')
        if price_str:
            try:
                trade_data['price'] = Decimal(price_str)
            except (ValueError, InvalidOperation):
                raise ValidationError(f"Invalid price: {price_str}")
        
        # Extract trade type
        trade_type_str = self._extract_form_value(action_context, 'trade_type_input', 'trade_type')
        if trade_type_str:
            trade_data['trade_type'] = TradeType.BUY if trade_type_str == 'buy' else TradeType.SELL
        
        return trade_data
    
    def _validate_trade_data(self, trade_data: Dict[str, Any]) -> None:
        """Validate extracted trade data."""
        if not trade_data.get('symbol'):
            raise ValidationError("Symbol is required")
        
        if not trade_data.get('quantity'):
            raise ValidationError("Quantity is required")
        
        if not trade_data.get('price'):
            raise ValidationError("Price is required")
        
        if not trade_data.get('trade_type'):
            raise ValidationError("Trade type is required")
        
        # Validate individual fields
        validate_symbol(trade_data['symbol'])
        validate_quantity(trade_data['quantity'])
        validate_price(trade_data['price'])
    
    def _create_widget_context(self, action_context: ActionContext) -> WidgetContext:
        """Create widget context from action context."""
        return WidgetContext(
            user=action_context.user,
            channel_id=action_context.channel_id,
            trigger_id=action_context.trigger_id,
            state=WidgetState.INITIAL,
            theme=UITheme.STANDARD
        )
    
    def _requires_high_risk_confirmation(self, action_context: ActionContext) -> bool:
        """Check if high-risk confirmation is required."""
        # Check private metadata for risk analysis results
        if action_context.private_metadata:
            risk_data = action_context.private_metadata.get('risk_analysis')
            if risk_data:
                return risk_data.get('is_high_risk', False)
        
        return False
    
    async def _update_modal(self, client: WebClient, view_id: str, modal: Dict[str, Any]) -> None:
        """Update existing modal."""
        try:
            await to_thread(
                client.views_update,
                view_id=view_id,
                view=modal
            )
        except SlackApiError as e:
            logger.error(f"Failed to update modal: {str(e)}")
            raise
    
    async def _close_modal(self, client: WebClient, view_id: str) -> None:
        """Close modal."""
        try:
            await to_thread(
                client.views_update,
                view_id=view_id,
                view={"type": "modal", "close": {"type": "plain_text", "text": "Close"}}
            )
        except SlackApiError as e:
            logger.error(f"Failed to close modal: {str(e)}")
            # Don't raise error for modal close failures
    
    async def _send_trade_success_notification(self, client: WebClient, action_context: ActionContext,
                                             trade: Trade, execution_result: TradeExecution) -> None:
        """Send trade success notification."""
        try:
            message = (
                f"✅ *Trade Executed Successfully*\n\n"
                f"• Symbol: {trade.symbol}\n"
                f"• Type: {trade.trade_type.value.title()}\n"
                f"• Quantity: {trade.quantity:,}\n"
                f"• Price: {format_money(trade.price)}\n"
                f"• Total Value: {format_money(abs(trade.quantity * trade.price))}\n"
                f"• Execution ID: {execution_result.execution_id}\n"
                f"• Time: {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            await to_thread(
                client.chat_postEphemeral,
                channel=action_context.channel_id,
                user=action_context.slack_user_id,
                text=message
            )
            
            # Send notification to Portfolio Manager if high-risk trade
            if hasattr(execution_result, 'is_high_risk') and execution_result.is_high_risk:
                await self.notification_service.send_high_risk_notification(
                    client, action_context.user, trade
                )
                
        except Exception as e:
            logger.error(f"Failed to send success notification: {str(e)}")
    
    async def _send_trade_failure_notification(self, client: WebClient, action_context: ActionContext,
                                             trade: Trade, error_message: str) -> None:
        """Send trade failure notification."""
        try:
            message = (
                f"❌ *Trade Execution Failed*\n\n"
                f"• Symbol: {trade.symbol}\n"
                f"• Type: {trade.trade_type.value.title()}\n"
                f"• Quantity: {trade.quantity:,}\n"
                f"• Price: {format_money(trade.price)}\n"
                f"• Error: {error_message}\n"
                f"• Time: {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                f"Please try again or contact support if the issue persists."
            )
            
            await to_thread(
                client.chat_postEphemeral,
                channel=action_context.channel_id,
                user=action_context.slack_user_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to send failure notification: {str(e)}")
    
    async def _send_error_response(self, client: WebClient, action_context: Optional[ActionContext],
                                 message: str) -> None:
        """Send error response to user."""
        try:
            if not action_context or not action_context.channel_id:
                logger.error("Cannot send error response: missing action context or channel")
                return
            
            await to_thread(
                client.chat_postEphemeral,
                channel=action_context.channel_id,
                user=action_context.slack_user_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to send error response: {str(e)}")
    
    async def _log_audit_event(self, action_context: ActionContext, success: bool,
                             error_type: Optional[str], response_time: float) -> None:
        """Log audit event for action execution."""
        try:
            audit_data = {
                'action_type': action_context.action_type.value,
                'action_id': action_context.action_id,
                'callback_id': action_context.callback_id,
                'user_id': action_context.user.user_id if action_context.user else None,
                'slack_user_id': action_context.slack_user_id,
                'channel_id': action_context.channel_id,
                'success': success,
                'error_type': error_type,
                'response_time_ms': response_time * 1000,
                'request_id': action_context.request_id,
                'view_id': action_context.view_id
            }
            
            # Log to database audit trail
            await self.db_service.log_audit_event(
                'action_executed',
                action_context.user.user_id if action_context.user else action_context.slack_user_id,
                audit_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")


# Global action handler instance
_action_handler: Optional[ActionHandler] = None


def initialize_action_handler(auth_service: AuthService, database_service: DatabaseService,
                            market_data_service: MarketDataService, risk_analysis_service: RiskAnalysisService,
                            trading_api_service: TradingAPIService) -> None:
    """Initialize global action handler instance."""
    global _action_handler
    _action_handler = ActionHandler(
        auth_service, database_service, market_data_service,
        risk_analysis_service, trading_api_service
    )
    logger.info("Action handler initialized globally")


def register_action_handlers(app: App, service_container: Optional['ServiceContainer'] = None) -> None:
    """
    Register all action handlers with the Slack app.
    
    Args:
        app: Slack Bolt application instance
        service_container: Service container for dependency injection
    """
    # Use provided service container or get global one
    container = service_container or get_container()
    
    # Get services from container
    auth_service = container.get(AuthService)
    database_service = container.get(DatabaseService)
    market_data_service = container.get(MarketDataService)
    risk_analysis_service = container.get(RiskAnalysisService)
    trading_api_service = container.get(TradingAPIService)
    
    # Create action handler
    action_handler = ActionHandler(
        auth_service, database_service, market_data_service,
        risk_analysis_service, trading_api_service
    )
    
    # Button action handlers
    @app.action("get_market_data")
    async def handle_get_market_data(ack, body, client, context):
        """Handle get market data button click."""
        await action_handler.process_action(
            ActionType.GET_MARKET_DATA, body, client, ack, context
        )
    
    @app.action("analyze_risk")
    async def handle_analyze_risk(ack, body, client, context):
        """Handle analyze risk button click."""
        await action_handler.process_action(
            ActionType.ANALYZE_RISK, body, client, ack, context
        )
    
    @app.action("refresh_data")
    async def handle_refresh_data(ack, body, client, context):
        """Handle refresh data button click."""
        await action_handler.process_action(
            ActionType.REFRESH_DATA, body, client, ack, context
        )
    
    @app.action("view_details")
    async def handle_view_details(ack, body, client, context):
        """Handle view details button click."""
        await action_handler.process_action(
            ActionType.VIEW_DETAILS, body, client, ack, context
        )
    
    @app.action("cancel_trade")
    async def handle_cancel_trade(ack, body, client, context):
        """Handle cancel trade button click."""
        await action_handler.process_action(
            ActionType.CANCEL_TRADE, body, client, ack, context
        )
    
    # Interactive input handlers for real-time modal updates
    @app.action("shares_input")
    async def handle_shares_input(ack, body, client):
        """Handle shares input change - auto-calculate GMV."""
        await ack()
        try:
            # Extract current values from the modal
            view = body.get("view", {})
            state_values = view.get("state", {}).get("values", {})
            
            # Get shares value
            shares_block = state_values.get("qty_shares_block", {})
            shares_value = shares_block.get("shares_input", {}).get("value")
            
            # Get current price from display or use market quote
            current_price = None
            current_price_block = None
            
            # Try to get price from current_price_display block
            for block in view.get("blocks", []):
                if block.get("block_id") == "current_price_display":
                    text = block.get("text", {}).get("text", "")
                    # Extract price from "*Current Stock Price:* *$150.00*"
                    import re
                    price_match = re.search(r'\$([0-9,.]+)', text)
                    if price_match:
                        current_price = float(price_match.group(1).replace(',', ''))
                    break
            
            # If we have both shares and price, calculate GMV
            if shares_value and current_price:
                try:
                    shares = int(shares_value)
                    gmv = shares * current_price
                    
                    # Update the modal with calculated GMV
                    updated_blocks = []
                    for block in view.get("blocks", []):
                        if block.get("block_id") == "gmv_block":
                            # Update GMV value
                            updated_block = block.copy()
                            updated_block["element"] = updated_block.get("element", {}).copy()
                            updated_block["element"]["initial_value"] = str(gmv)
                            updated_blocks.append(updated_block)
                        else:
                            updated_blocks.append(block)
                    
                    # Update the view
                    await client.views_update(
                        view_id=view["id"],
                        view={
                            "type": "modal",
                            "callback_id": view.get("callback_id"),
                            "title": view.get("title"),
                            "submit": view.get("submit"),
                            "close": view.get("close"),
                            "blocks": updated_blocks,
                            "private_metadata": view.get("private_metadata")
                        }
                    )
                    logger.info(f"Updated GMV to {gmv} based on {shares} shares at ${current_price}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to calculate GMV: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling shares input: {e}")
    
    @app.action("gmv_input")
    async def handle_gmv_input(ack, body, client):
        """Handle GMV input change - auto-calculate shares."""
        await ack()
        try:
            # Extract current values from the modal
            view = body.get("view", {})
            state_values = view.get("state", {}).get("values", {})
            
            # Get GMV value
            gmv_block = state_values.get("gmv_block", {})
            gmv_value = gmv_block.get("gmv_input", {}).get("value")
            
            # Get current price from display
            current_price = None
            for block in view.get("blocks", []):
                if block.get("block_id") == "current_price_display":
                    text = block.get("text", {}).get("text", "")
                    import re
                    price_match = re.search(r'\$([0-9,.]+)', text)
                    if price_match:
                        current_price = float(price_match.group(1).replace(',', ''))
                    break
            
            # If we have both GMV and price, calculate shares
            if gmv_value and current_price and current_price > 0:
                try:
                    gmv = float(gmv_value)
                    shares = int(gmv / current_price)
                    
                    # Update the modal with calculated shares
                    updated_blocks = []
                    for block in view.get("blocks", []):
                        if block.get("block_id") == "qty_shares_block":
                            # Update shares value
                            updated_block = block.copy()
                            updated_block["element"] = updated_block.get("element", {}).copy()
                            updated_block["element"]["initial_value"] = str(shares)
                            updated_blocks.append(updated_block)
                        else:
                            updated_blocks.append(block)
                    
                    # Update the view
                    await client.views_update(
                        view_id=view["id"],
                        view={
                            "type": "modal",
                            "callback_id": view.get("callback_id"),
                            "title": view.get("title"),
                            "submit": view.get("submit"),
                            "close": view.get("close"),
                            "blocks": updated_blocks,
                            "private_metadata": view.get("private_metadata")
                        }
                    )
                    logger.info(f"Updated shares to {shares} based on GMV ${gmv} at ${current_price}")
                    
                except (ValueError, TypeError, ZeroDivisionError) as e:
                    logger.warning(f"Failed to calculate shares: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling GMV input: {e}")
    
    @app.action("symbol_input")
    async def handle_symbol_input(ack, body, client):
        """Handle symbol input change - fetch and display current price."""
        await ack()
        try:
            # Extract symbol from input
            view = body.get("view", {})
            state_values = view.get("state", {}).get("values", {})
            
            symbol_block = state_values.get("trade_symbol_block", {})
            symbol = symbol_block.get("symbol_input", {}).get("value", "").strip().upper()
            
            if not symbol:
                return
            
            # Fetch market data for symbol
            try:
                market_quote = await market_data_service.get_quote(symbol)
                
                # Update the price display block
                updated_blocks = []
                for block in view.get("blocks", []):
                    if block.get("block_id") == "current_price_display":
                        # Update price display
                        updated_block = {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*Current Stock Price:* *${market_quote.current_price:.2f}*"
                            },
                            "block_id": "current_price_display"
                        }
                        updated_blocks.append(updated_block)
                    else:
                        updated_blocks.append(block)
                
                # Update the view
                await client.views_update(
                    view_id=view["id"],
                    view={
                        "type": "modal",
                        "callback_id": view.get("callback_id"),
                        "title": view.get("title"),
                        "submit": view.get("submit"),
                        "close": view.get("close"),
                        "blocks": updated_blocks,
                        "private_metadata": view.get("private_metadata")
                    }
                )
                logger.info(f"Updated price for {symbol}: ${market_quote.current_price:.2f}")
                
            except Exception as e:
                logger.warning(f"Failed to fetch price for {symbol}: {e}")
                
        except Exception as e:
            logger.error(f"Error handling symbol input: {e}")
    
    # Modal submission handlers
    @app.view("trade_modal")
    @app.view("stock_trade_modal_interactive")
    async def handle_trade_modal_submission(ack, body, client, context):
        """Handle trade modal form submission."""
        await action_handler.process_action(
            ActionType.SUBMIT_TRADE, body, client, ack, context
        )
    
    @app.view("trade_confirmation_modal")
    async def handle_trade_confirmation_submission(ack, body, client, context):
        """Handle high-risk trade confirmation modal submission."""
        await action_handler.process_action(
            ActionType.CONFIRM_HIGH_RISK, body, client, ack, context
        )
    
    # Note: Generic catch-all handler removed to prevent conflicts with specific handlers
    # Specific action handlers are registered in their respective modules
    
    # Store handler globally for metrics access
    global _action_handler
    _action_handler = action_handler
    
    logger.info("All action handlers registered successfully with service container integration")


def get_action_metrics() -> ActionMetrics:
    """Get current action execution metrics."""
    if not _action_handler:
        return ActionMetrics()
    return _action_handler.metrics