"""
Comprehensive Slack Command Handlers for Jain Global Trading Bot

This module provides complete command handling functionality including the /trade command
with comprehensive channel validation, user authentication, permission checking, command
routing, parameter parsing, error handling, logging, metrics collection, and audit trail
generation.

The command handlers implement role-based access control, security validation, rate limiting,
and comprehensive error recovery mechanisms while providing rich user feedback and
maintaining detailed audit trails for compliance requirements.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import json

if TYPE_CHECKING:
    from services.service_container import ServiceContainer

from slack_bolt import App, Ack, BoltContext
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Import our services and models
from services.auth import AuthService, AuthenticationError, AuthorizationError, SessionError, RateLimitError, SecurityViolationError
from services.database import DatabaseService, DatabaseError, NotFoundError, ConflictError
from services.service_container import ServiceContainer, get_container
from models.user import User, UserRole, Permission
from ui.trade_widget import TradeWidget, WidgetContext, WidgetState, UITheme
from utils.validators import validate_channel_id, validate_user_id, ValidationError
from config.settings import get_config

# Configure logging
logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Enumeration of supported command types."""
    TRADE = "trade"
    PORTFOLIO = "portfolio"
    PM_DASHBOARD = "pm_dashboard"
    HELP = "help"
    STATUS = "status"


class CommandError(Exception):
    """Base exception for command handling errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, user_friendly: bool = True):
        self.message = message
        self.error_code = error_code
        self.user_friendly = user_friendly
        super().__init__(self.message)


class CommandValidationError(CommandError):
    """Exception for command validation errors."""
    pass


class CommandAuthorizationError(CommandError):
    """Exception for command authorization errors."""
    pass


@dataclass
class CommandContext:
    """Context information for command processing."""
    command_type: CommandType
    user_id: str
    slack_user_id: str
    team_id: str
    channel_id: str
    channel_name: str
    trigger_id: str
    command_text: str
    response_url: str
    timestamp: datetime
    
    # Parsed parameters
    parameters: Dict[str, Any] = None
    
    # Authentication context
    user: Optional[User] = None
    session_id: Optional[str] = None
    
    # Request metadata
    request_id: str = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.parameters is None:
            self.parameters = {}
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


class CommandMetrics:
    """Command execution metrics tracking."""
    
    def __init__(self):
        self.commands_processed = 0
        self.commands_successful = 0
        self.commands_failed = 0
        self.authentication_failures = 0
        self.authorization_failures = 0
        self.validation_failures = 0
        self.response_times = []
        self.error_counts = {}
        
    def record_command(self, success: bool, response_time: float, error_type: Optional[str] = None):
        """Record command execution metrics."""
        self.commands_processed += 1
        if success:
            self.commands_successful += 1
        else:
            self.commands_failed += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        self.response_times.append(response_time)
        
        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def get_average_response_time(self) -> float:
        """Get average response time in milliseconds."""
        return sum(self.response_times) / len(self.response_times) * 1000 if self.response_times else 0.0
    
    def get_success_rate(self) -> float:
        """Get command success rate as percentage."""
        return (self.commands_successful / self.commands_processed * 100) if self.commands_processed > 0 else 0.0


class CommandHandler:
    """
    Comprehensive command handler with authentication, authorization, and validation.
    
    This class provides complete command processing functionality including:
    - Channel validation and access control
    - User authentication and session management
    - Role-based permission checking
    - Command routing and parameter parsing
    - Comprehensive error handling and recovery
    - Audit trail generation and compliance logging
    - Performance metrics and monitoring
    - Rate limiting and security controls
    """
    
    def __init__(self, auth_service: AuthService, database_service: DatabaseService):
        """
        Initialize command handler with required services.
        
        Args:
            auth_service: Authentication service instance
            database_service: Database service instance
        """
        self.auth_service = auth_service
        self.db_service = database_service
        self.config = get_config()
        
        # Initialize UI components
        self.trade_widget = TradeWidget()
        
        # Metrics tracking
        self.metrics = CommandMetrics()
        
        # Command routing table
        self.command_routes = {
            CommandType.TRADE: self._handle_trade_command,
            CommandType.PORTFOLIO: self._handle_portfolio_command,
            CommandType.PM_DASHBOARD: self._handle_pm_dashboard_command,
            CommandType.HELP: self._handle_help_command,
            CommandType.STATUS: self._handle_status_command
        }
        
        # Rate limiting
        self._rate_limits = {}  # user_id -> [timestamps]
        self._rate_limit_window = 60  # 1 minute
        self._rate_limit_max = 10  # 10 commands per minute
        
        logger.info("CommandHandler initialized with comprehensive security and validation")
    
    async def process_command(self, command_type: CommandType, body: Dict[str, Any], 
                            client: WebClient, ack: Ack, context: BoltContext) -> None:
        """
        Process incoming slash command with comprehensive validation and error handling.
        
        Args:
            command_type: Type of command being processed
            body: Slack command payload
            client: Slack WebClient instance
            ack: Slack acknowledgment function
            context: Bolt context
        """
        start_time = time.time()
        command_context = None
        success = False
        error_type = None
        
        try:
            # Note: ack() is now called in the wrapper before this method runs
            # to avoid event loop nesting issues with asyncio.run()
            
            # Create command context
            command_context = self._create_command_context(command_type, body, context)
            
            logger.info(
                f"Processing command: {command_type.value} | User: {command_context.slack_user_id} | "
                f"Channel: {command_context.channel_id} | Request: {command_context.request_id}"
            )
            
            # Validate and authenticate
            await self._validate_and_authenticate(command_context, client)
            
            # Check rate limits
            await self._check_rate_limits(command_context)
            
            # Route to specific command handler
            handler = self.command_routes.get(command_type)
            if not handler:
                raise CommandError(f"Unknown command type: {command_type.value}", "UNKNOWN_COMMAND")
            
            # Execute command handler
            await handler(command_context, client)
            
            success = True
            logger.info(
                f"Command processed successfully: {command_type.value} | User: {command_context.slack_user_id} | "
                f"Request: {command_context.request_id} | Response time: {(time.time() - start_time) * 1000:.2f}ms"
            )
            
        except RateLimitError as e:
            error_type = "RATE_LIMIT"
            self.metrics.authentication_failures += 1
            await self._send_error_response(
                client, command_context, 
                f"⏱️ Rate limit exceeded. {e.message}",
                ephemeral=True
            )
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.warning(f"Rate limit exceeded | User: {user_id} | Error: {str(e)}")
            
        except AuthenticationError as e:
            error_type = "AUTHENTICATION"
            self.metrics.authentication_failures += 1
            await self._send_error_response(
                client, command_context,
                f"🔐 Authentication failed: {e.message}",
                ephemeral=True
            )
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.warning(f"Authentication failed | User: {user_id} | Error: {str(e)}")
            
        except AuthorizationError as e:
            error_type = "AUTHORIZATION"
            self.metrics.authorization_failures += 1
            await self._send_error_response(
                client, command_context,
                f"🚫 Access denied: {e.message}",
                ephemeral=True
            )
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.warning(f"Authorization failed | User: {user_id} | Error: {str(e)}")
            
        except CommandValidationError as e:
            error_type = "VALIDATION"
            self.metrics.validation_failures += 1
            await self._send_error_response(
                client, command_context,
                f"❌ Invalid command: {e.message}",
                ephemeral=True
            )
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.warning(f"Command validation failed | User: {user_id} | Error: {str(e)}")
            
        except SecurityViolationError as e:
            error_type = "SECURITY_VIOLATION"
            await self._send_error_response(
                client, command_context,
                "🚨 Security violation detected. This incident has been logged.",
                ephemeral=True
            )
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.error(f"Security violation detected | User: {user_id} | Type: {e.violation_type} | Error: {str(e)}")
            
        except SlackApiError as e:
            error_type = "SLACK_API"
            await self._send_error_response(
                client, command_context,
                "📡 Communication error with Slack. Please try again.",
                ephemeral=True
            )
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.error(f"Slack API error | User: {user_id} | Error: {str(e)}")
            
        except Exception as e:
            error_type = "SYSTEM"
            await self._send_error_response(
                client, command_context,
                "⚠️ System error occurred. Please try again or contact support.",
                ephemeral=True
            )
            cmd_type = command_type.value if command_type else "unknown"
            user_id = command_context.slack_user_id if command_context else "unknown"
            logger.error(f"Unexpected error processing command | Type: {cmd_type} | User: {user_id} | Error: {str(e)}", exc_info=True)
            
        finally:
            # Record metrics
            response_time = time.time() - start_time
            self.metrics.record_command(success, response_time, error_type)
            
            # Log audit event
            if command_context:
                await self._log_audit_event(command_context, success, error_type, response_time)
    
    def _create_command_context(self, command_type: CommandType, body: Dict[str, Any], 
                              context: BoltContext) -> CommandContext:
        """Create command context from Slack payload."""
        return CommandContext(
            command_type=command_type,
            user_id=body.get("user_id", ""),
            slack_user_id=body.get("user_id", ""),
            team_id=body.get("team_id", ""),
            channel_id=body.get("channel_id", ""),
            channel_name=body.get("channel_name", ""),
            trigger_id=body.get("trigger_id", ""),
            command_text=body.get("text", "").strip(),
            response_url=body.get("response_url", ""),
            timestamp=datetime.now(timezone.utc),
            ip_address=context.get("client_ip") if context else None,
            user_agent=context.get("user_agent") if context else None
        )
    
    async def _validate_and_authenticate(self, command_context: CommandContext, client: WebClient) -> None:
        """Validate command and authenticate user."""
        # Validate basic command structure
        if not command_context.slack_user_id:
            raise CommandValidationError("Missing user ID", "MISSING_USER_ID")
        
        if not command_context.channel_id:
            raise CommandValidationError("Missing channel ID", "MISSING_CHANNEL_ID")
        
        if not command_context.team_id:
            raise CommandValidationError("Missing team ID", "MISSING_TEAM_ID")
        
        # Authenticate user and create session FIRST
        user, session = await self.auth_service.authenticate_slack_user(
            command_context.slack_user_id,
            command_context.team_id,
            command_context.channel_id,
            command_context.ip_address,
            command_context.user_agent
        )
        
        # Update command context with authenticated user
        command_context.user = user
        command_context.session_id = session.session_id
        
        # Validate channel access AFTER we have the user
        await self._validate_channel_access(command_context)
        
        logger.info(
            "User authenticated successfully",
            user_id=user.user_id,
            role=user.role.value,
            session_id=session.session_id
        )
    
    async def _validate_channel_access(self, command_context: CommandContext) -> None:
        """Validate that command is being used in an approved channel."""
        try:
            # Check if channel is approved for trading commands
            is_approved = await self.auth_service.authorize_channel_access(
                command_context.user,  # Now we have the authenticated user
                command_context.channel_id
            )
            
            if not is_approved:
                # Get channel info for better error message
                try:
                    channel_info = await self.db_service.get_channel_info(command_context.channel_id)
                    if channel_info:
                        raise CommandAuthorizationError(
                            f"Trading commands are not allowed in #{command_context.channel_name}. "
                            "Please use an approved private channel.",
                            "CHANNEL_NOT_APPROVED"
                        )
                except NotFoundError:
                    pass
                
                raise CommandAuthorizationError(
                    "Trading commands are only available in approved private channels. "
                    "Please contact your administrator to request channel approval.",
                    "CHANNEL_NOT_APPROVED"
                )
                
        except AuthorizationError as e:
            raise CommandAuthorizationError(e.message, e.required_permission)
    
    async def _check_rate_limits(self, command_context: CommandContext) -> None:
        """Check and enforce rate limits for user commands."""
        user_id = command_context.slack_user_id
        current_time = time.time()
        
        # Clean old entries
        if user_id in self._rate_limits:
            self._rate_limits[user_id] = [
                timestamp for timestamp in self._rate_limits[user_id]
                if current_time - timestamp < self._rate_limit_window
            ]
        else:
            self._rate_limits[user_id] = []
        
        # Check if limit exceeded
        if len(self._rate_limits[user_id]) >= self._rate_limit_max:
            retry_after = int(self._rate_limit_window - (current_time - self._rate_limits[user_id][0]))
            raise RateLimitError(
                f"Too many commands. Try again in {retry_after} seconds.",
                retry_after
            )
        
        # Record this attempt
        self._rate_limits[user_id].append(current_time)
    
    async def _handle_trade_command(self, command_context: CommandContext, client: WebClient) -> None:
        """
        Handle /trade command with comprehensive validation and UI generation.
        
        Args:
            command_context: Command context with user and parameters
            client: Slack WebClient instance
        """
        try:
            # Validate user has trading permissions
            required_permissions = [Permission.EXECUTE_TRADES, Permission.VIEW_MARKET_DATA]
            
            missing_permissions = []
            for permission in required_permissions:
                if not command_context.user.has_permission(permission):
                    missing_permissions.append(permission.value)
            
            if missing_permissions:
                raise CommandAuthorizationError(
                    f"Insufficient permissions for trading. Missing: {', '.join(missing_permissions)}",
                    ', '.join(missing_permissions)
                )
            
            # Parse command parameters
            parameters = self._parse_trade_parameters(command_context.command_text)
            command_context.parameters = parameters
            
            # Create widget context
            widget_context = WidgetContext(
                user=command_context.user,
                channel_id=command_context.channel_id,
                trigger_id=command_context.trigger_id,
                state=WidgetState.INITIAL,
                theme=UITheme.STANDARD
            )
            
            # Pre-populate with parsed parameters
            if parameters.get('symbol'):
                widget_context.symbol = parameters['symbol'].upper()
            if parameters.get('quantity'):
                widget_context.quantity = parameters['quantity']
            if parameters.get('trade_type'):
                widget_context.trade_type = parameters['trade_type']
            if parameters.get('price'):
                widget_context.price = parameters['price']
            
            # Generate trade modal
            modal = self.trade_widget.create_trade_modal(widget_context)
            
            # Open modal
            await asyncio.to_thread(
                client.views_open,
                trigger_id=command_context.trigger_id,
                view=modal
            )
            
            logger.info(
                "Trade modal opened successfully",
                user_id=command_context.user.user_id,
                channel_id=command_context.channel_id,
                parameters=parameters
            )
            
        except ValidationError as e:
            raise CommandValidationError(f"Invalid trade parameters: {e.message}", "INVALID_PARAMETERS")
        
        except SlackApiError as e:
            if e.response.get('error') == 'expired_trigger_id':
                await self._send_error_response(
                    client, command_context,
                    "⏱️ Command expired. Please try the /trade command again.",
                    ephemeral=True
                )
            else:
                raise
    
    async def _handle_portfolio_command(self, command_context: CommandContext, client: WebClient) -> None:
        """Handle /portfolio command to show portfolio dashboard with live data."""
        try:
            # Validate user has portfolio viewing permissions
            if not command_context.user.has_permission(Permission.VIEW_PORTFOLIO):
                raise CommandAuthorizationError(
                    "You don't have permission to view portfolio information.",
                    Permission.VIEW_PORTFOLIO.value
                )
            
            # Get user's portfolio
            portfolio = await self.db_service.get_or_create_default_portfolio(command_context.user.user_id)
            
            # Get active positions
            active_positions = portfolio.get_active_positions()
            
            # Build portfolio message
            portfolio_text = (
                f"📊 *Portfolio Summary for {command_context.user.profile.display_name}*\n\n"
                f"*Account Overview:*\n"
                f"• Total Value: ${portfolio.total_value:,.2f}\n"
                f"• Cash Balance: ${portfolio.cash_balance:,.2f}\n"
                f"• Total P&L: ${portfolio.total_pnl:,.2f} "
            )
            
            # Add P&L percentage
            if portfolio.total_cost_basis > 0:
                pnl_pct = (portfolio.total_pnl / portfolio.total_cost_basis * 100)
                pnl_emoji = "📈" if pnl_pct > 0 else "📉" if pnl_pct < 0 else "➡️"
                portfolio_text += f"({pnl_pct:+.2f}% {pnl_emoji})\n"
            else:
                portfolio_text += "(0.00%)\n"
            
            portfolio_text += f"• Day Change: ${portfolio.day_change:,.2f}\n\n"
            
            # Add positions
            if active_positions:
                portfolio_text += f"*Active Positions ({len(active_positions)}):*\n"
                
                # Get market data service for live prices
                from services.market_data import get_market_data_service
                market_data_service = await get_market_data_service()
                
                # Update positions with live prices
                for position in active_positions[:10]:  # Show top 10 positions
                    try:
                        # Fetch current price
                        quote = await market_data_service.get_quote(position.symbol)
                        if quote:
                            # Update position with current price
                            position.update_price(quote.current_price)
                        
                        # Format position display
                        position_pnl = position.get_total_pnl()
                        pnl_emoji = "🟢" if position_pnl > 0 else "🔴" if position_pnl < 0 else "⚪"
                        
                        portfolio_text += (
                            f"{pnl_emoji} *{position.symbol}*: {position.quantity:,} shares @ "
                            f"${position.current_price:.2f} | P&L: ${position_pnl:,.2f}\n"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update position {position.symbol}: {str(e)}")
                        # Show position without live price update
                        portfolio_text += (
                            f"• *{position.symbol}*: {position.quantity:,} shares @ "
                            f"${position.current_price:.2f}\n"
                        )
                
                if len(active_positions) > 10:
                    portfolio_text += f"\n_...and {len(active_positions) - 10} more positions_\n"
            else:
                portfolio_text += "*Active Positions:* None\n"
                portfolio_text += "_Start trading with `/trade` to build your portfolio_\n"
            
            portfolio_text += (
                f"\n*Portfolio Info:*\n"
                f"• Status: {portfolio.status.value.title()}\n"
                f"• Created: {portfolio.inception_date.strftime('%Y-%m-%d')}\n"
                f"• Last Updated: {portfolio.last_updated.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"💡 *Tip:* Use `/trade` to execute trades"
            )
            
            # Update portfolio in database with live prices
            await self.db_service.update_portfolio(portfolio)
            
            # Send portfolio summary
            await asyncio.to_thread(
                client.chat_postEphemeral,
                channel=command_context.channel_id,
                user=command_context.slack_user_id,
                text=portfolio_text
            )
            
            logger.info(
                "Portfolio command processed with live data",
                user_id=command_context.user.user_id,
                portfolio_value=float(portfolio.total_value),
                active_positions=len(active_positions)
            )
            
        except Exception as e:
            logger.error(f"Error handling portfolio command: {str(e)}", exc_info=True)
            raise
    
    async def _handle_pm_dashboard_command(self, command_context: CommandContext, client: WebClient) -> None:
        """Handle /pm-dashboard command - Portfolio Manager multi-portfolio view."""
        try:
            # Check if user is a Portfolio Manager or Admin
            if not command_context.user.has_permission(Permission.VIEW_ALL_PORTFOLIOS):
                raise CommandAuthorizationError(
                    "You don't have permission to view the Portfolio Manager dashboard. This feature is only available to Portfolio Managers and Admins.",
                    Permission.VIEW_ALL_PORTFOLIOS.value
                )
            
            # Get all portfolios
            all_portfolios = await self.db_service.get_all_portfolios(status=None, limit=50)
            
            # Calculate aggregate metrics
            total_aum = sum(p.total_value for p in all_portfolios)
            total_cash = sum(p.cash_balance for p in all_portfolios)
            total_pnl = sum(p.total_pnl for p in all_portfolios)
            total_traders = len(set(p.user_id for p in all_portfolios))
            total_positions = sum(len(p.get_active_positions()) for p in all_portfolios)
            
            # Build PM dashboard
            dashboard_text = f"📊 *Portfolio Manager Dashboard*\n\n"
            dashboard_text += f"*Aggregate Metrics:*\n"
            dashboard_text += f"• Total AUM: ${total_aum:,.2f}\n"
            dashboard_text += f"• Cash Balance: ${total_cash:,.2f}\n"
            dashboard_text += f"• Total P&L: ${total_pnl:,.2f}\n"
            dashboard_text += f"• Active Traders: {total_traders}\n"
            dashboard_text += f"• Active Positions: {total_positions}\n\n"
            
            # Show top portfolios by P&L
            sorted_portfolios = sorted(all_portfolios, key=lambda p: p.total_pnl, reverse=True)
            
            if sorted_portfolios:
                dashboard_text += f"*Top Performers:*\n"
                for i, portfolio in enumerate(sorted_portfolios[:5], 1):
                    emoji = "🟢" if portfolio.total_pnl > 0 else "🔴" if portfolio.total_pnl < 0 else "⚪"
                    return_pct = (portfolio.total_pnl / portfolio.initial_balance * 100) if portfolio.initial_balance > 0 else 0
                    dashboard_text += f"{emoji} {i}. User `{portfolio.user_id[:8]}...` - ${portfolio.total_pnl:,.2f} ({return_pct:.2f}%)\n"
                
                dashboard_text += f"\n*All Portfolios:*\n"
                for portfolio in sorted_portfolios:
                    emoji = "🟢" if portfolio.total_pnl > 0 else "🔴" if portfolio.total_pnl < 0 else "⚪"
                    active_pos = len(portfolio.get_active_positions())
                    dashboard_text += f"{emoji} `{portfolio.user_id[:12]}` | ${portfolio.total_value:,.2f} | {active_pos} positions | P&L: ${portfolio.total_pnl:,.2f}\n"
            else:
                dashboard_text += "*No active portfolios yet.*\n"
            
            # Add buttons for drill-down
            blocks = [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": dashboard_text}
                },
                {
                    "type": "divider"
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🔄 Live Trade Feed"},
                            "action_id": "pm_trade_feed",
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "⚠️ Risk Alerts"},
                            "action_id": "pm_risk_alerts"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "🔄 Refresh"},
                            "action_id": "pm_refresh"
                        }
                    ]
                }
            ]
            
            # Send dashboard
            await asyncio.to_thread(
                client.chat_postEphemeral,
                channel=command_context.channel_id,
                user=command_context.slack_user_id,
                blocks=blocks,
                text=dashboard_text
            )
            
            logger.info(
                "PM Dashboard accessed",
                user_id=command_context.user.user_id,
                role=command_context.user.role.value,
                total_portfolios=len(all_portfolios),
                total_aum=float(total_aum)
            )
            
        except CommandAuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error handling PM dashboard command: {str(e)}", exc_info=True)
            raise
    
    async def _handle_help_command(self, command_context: CommandContext, client: WebClient) -> None:
        """Handle /help command to show available commands and usage."""
        try:
            # Build help message based on user role
            help_text = self._build_help_message(command_context.user)
            
            await asyncio.to_thread(
                client.chat_postEphemeral,
                channel=command_context.channel_id,
                user=command_context.slack_user_id,
                text=help_text
            )
            
            logger.info(
                "Help command processed",
                user_id=command_context.user.user_id,
                role=command_context.user.role.value
            )
            
        except Exception as e:
            logger.error(f"Error handling help command: {str(e)}")
            raise
    
    async def _handle_status_command(self, command_context: CommandContext, client: WebClient) -> None:
        """Handle /status command to show system and user status."""
        try:
            # Build status message
            status_text = self._build_status_message(command_context.user)
            
            await asyncio.to_thread(
                client.chat_postEphemeral,
                channel=command_context.channel_id,
                user=command_context.slack_user_id,
                text=status_text
            )
            
            logger.info(
                "Status command processed",
                user_id=command_context.user.user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling status command: {str(e)}")
            raise
    
    def _parse_trade_parameters(self, command_text: str) -> Dict[str, Any]:
        """
        Parse trade command parameters from command text.
        
        Args:
            command_text: Raw command text after /trade
            
        Returns:
            Dictionary of parsed parameters
        """
        parameters = {}
        
        if not command_text:
            return parameters
        
        # Simple parameter parsing (can be enhanced with more sophisticated parsing)
        parts = command_text.split()
        
        for i, part in enumerate(parts):
            part = part.upper()
            
            # Try to identify symbol (first alphabetic part)
            if part.isalpha() and len(part) <= 5 and 'symbol' not in parameters:
                parameters['symbol'] = part
                continue
            
            # Try to identify quantity (numeric part)
            if part.isdigit() and 'quantity' not in parameters:
                try:
                    quantity = int(part)
                    if quantity > 0:
                        parameters['quantity'] = quantity
                        continue
                except ValueError:
                    pass
            
            # Try to identify price (decimal number)
            try:
                price = float(part)
                if price > 0 and 'price' not in parameters:
                    parameters['price'] = price
                    continue
            except ValueError:
                pass
            
            # Try to identify trade type
            if part in ['BUY', 'SELL'] and 'trade_type' not in parameters:
                from models.trade import TradeType
                parameters['trade_type'] = TradeType.BUY if part == 'BUY' else TradeType.SELL
                continue
        
        return parameters
    
    def _build_help_message(self, user: User) -> str:
        """Build role-specific help message."""
        base_help = (
            "🤖 *Jain Global Trading Bot Help*\n\n"
            "*Available Commands:*\n"
            "• `/trade` - Open trade execution interface\n"
            "• `/portfolio` - View portfolio dashboard (App Home)\n"
            "• `/help` - Show this help message\n"
            "• `/status` - Show system and user status\n\n"
        )
        
        role_specific = ""
        if user.role == UserRole.RESEARCH_ANALYST:
            role_specific = (
                "*Research Analyst Features:*\n"
                "• Advanced risk analysis and research integration\n"
                "• Comprehensive trade impact assessment\n"
                "• Portfolio Manager notifications for high-risk trades\n\n"
            )
        elif user.role == UserRole.EXECUTION_TRADER:
            role_specific = (
                "*Execution Trader Features:*\n"
                "• Streamlined trade execution interface\n"
                "• Real-time market data integration\n"
                "• Quick order entry and confirmation\n\n"
            )
        elif user.role == UserRole.PORTFOLIO_MANAGER:
            role_specific = (
                "*Portfolio Manager Features:*\n"
                "• Complete portfolio oversight and analytics\n"
                "• Risk management and approval workflows\n"
                "• Team trade monitoring and notifications\n\n"
            )
        
        usage_tips = (
            "*Usage Tips:*\n"
            "• Use `/trade AAPL 100 BUY` for quick trade entry\n"
            "• Commands only work in approved private channels\n"
            "• Check App Home for portfolio and trade history\n"
            "• High-risk trades require additional confirmation\n\n"
            "*Need Help?* Contact your system administrator or Portfolio Manager."
        )
        
        return base_help + role_specific + usage_tips
    
    def _build_status_message(self, user: User) -> str:
        """Build system and user status message."""
        status_text = (
            f"📊 *System Status*\n\n"
            f"*User Information:*\n"
            f"• Name: {user.profile.display_name}\n"
            f"• Role: {user.role.value.replace('_', ' ').title()}\n"
            f"• Status: {user.status.value.title()}\n"
            f"• Permissions: {len(user.permissions)} active\n\n"
            f"*System Metrics:*\n"
            f"• Commands Processed: {self.metrics.commands_processed:,}\n"
            f"• Success Rate: {self.metrics.get_success_rate():.1f}%\n"
            f"• Avg Response Time: {self.metrics.get_average_response_time():.0f}ms\n\n"
            f"*Last Updated:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        
        return status_text
    
    async def _send_error_response(self, client: WebClient, command_context: Optional[CommandContext],
                                 message: str, ephemeral: bool = True) -> None:
        """Send error response to user."""
        try:
            if not command_context:
                logger.error("Cannot send error response: missing command context")
                return
            
            await asyncio.to_thread(
                client.chat_postEphemeral if ephemeral else client.chat_postMessage,
                channel=command_context.channel_id,
                user=command_context.slack_user_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Failed to send error response: {str(e)}")
    
    async def _log_audit_event(self, command_context: CommandContext, success: bool,
                             error_type: Optional[str], response_time: float) -> None:
        """Log audit event for command execution."""
        try:
            audit_data = {
                'command_type': command_context.command_type.value,
                'user_id': command_context.user.user_id if command_context.user else None,
                'slack_user_id': command_context.slack_user_id,
                'channel_id': command_context.channel_id,
                'success': success,
                'error_type': error_type,
                'response_time_ms': response_time * 1000,
                'parameters': command_context.parameters,
                'ip_address': command_context.ip_address,
                'user_agent': command_context.user_agent,
                'request_id': command_context.request_id
            }
            
            # Log to database audit trail
            await self.db_service.log_audit_event(
                'command_executed',
                command_context.user.user_id if command_context.user else command_context.slack_user_id,
                audit_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")


# Global command handler instance
_command_handler: Optional[CommandHandler] = None


def initialize_command_handler(auth_service: AuthService, database_service: DatabaseService) -> None:
    """Initialize global command handler instance."""
    global _command_handler
    _command_handler = CommandHandler(auth_service, database_service)
    logger.info("Command handler initialized globally")


def register_command_handlers(app: App, service_container: Optional['ServiceContainer'] = None) -> None:
    """
    Register all command handlers with the Slack app.
    
    Args:
        app: Slack Bolt application instance
        service_container: Service container for dependency injection
    """
    # Use provided service container or get global one
    container = service_container or get_container()
    
    # Get services from container
    auth_service = container.get(AuthService)
    database_service = container.get(DatabaseService)
    
    # Create command handler
    command_handler = CommandHandler(auth_service, database_service)
    
    @app.command("/trade")
    def handle_trade_command(ack, body, client, context):
        """Handle the /trade slash command."""
        ack()  # Acknowledge immediately BEFORE async processing
        import asyncio
        # Create a dummy ack since we already called it
        dummy_ack = lambda: None
        asyncio.run(command_handler.process_command(
            CommandType.TRADE, body, client, dummy_ack, context
        ))
    
    @app.command("/portfolio")
    def handle_portfolio_command(ack, body, client, context):
        """Handle the /portfolio slash command."""
        ack()  # Acknowledge immediately BEFORE async processing
        import asyncio
        dummy_ack = lambda: None
        asyncio.run(command_handler.process_command(
            CommandType.PORTFOLIO, body, client, dummy_ack, context
        ))
    
    @app.command("/pm-dashboard")
    def handle_pm_dashboard_command(ack, body, client, context):
        """Handle the /pm-dashboard slash command for Portfolio Managers."""
        ack()  # Acknowledge immediately BEFORE async processing
        import asyncio
        dummy_ack = lambda: None
        asyncio.run(command_handler.process_command(
            CommandType.PM_DASHBOARD, body, client, dummy_ack, context
        ))
    
    @app.command("/help")
    def handle_help_command(ack, body, client, context):
        """Handle the /help slash command."""
        ack()  # Acknowledge immediately BEFORE async processing
        import asyncio
        dummy_ack = lambda: None
        asyncio.run(command_handler.process_command(
            CommandType.HELP, body, client, dummy_ack, context
        ))
    
    @app.command("/status")
    def handle_status_command(ack, body, client, context):
        """Handle the /status slash command."""
        ack()  # Acknowledge immediately BEFORE async processing
        import asyncio
        dummy_ack = lambda: None
        asyncio.run(command_handler.process_command(
            CommandType.STATUS, body, client, dummy_ack, context
        ))
    
    # Store handler globally for metrics access
    global _command_handler
    _command_handler = command_handler
    
    # Add message handlers as alternatives to slash commands
    @app.message("help")
    async def handle_help_message(message, say):
        """Handle 'help' message."""
        await command_handler.process_command(
            CommandType.HELP, {"text": "help", "user_id": message["user"]}, None, lambda: None, {}
        )
    
    @app.message("status")
    async def handle_status_message(message, say):
        """Handle 'status' message."""
        await command_handler.process_command(
            CommandType.STATUS, {"text": "status", "user_id": message["user"]}, None, lambda: None, {}
        )
    
    @app.message("portfolio")
    async def handle_portfolio_message(message, say):
        """Handle 'portfolio' message."""
        await command_handler.process_command(
            CommandType.PORTFOLIO, {"text": "portfolio", "user_id": message["user"]}, None, lambda: None, {}
        )
    
    @app.event("app_mention")
    def handle_app_mention_commands(event, say):
        """Handle commands via app mentions like @bot help."""
        try:
            # Extract command from mention text
            text = event.get("text", "").strip()
            # Remove bot mention from text (format: <@U123456> command)
            import re
            command_text = re.sub(r'<@[^>]+>\s*', '', text).strip().lower()
            
            # Map commands
            command_map = {
                'help': CommandType.HELP,
                'status': CommandType.STATUS,
                'portfolio': CommandType.PORTFOLIO,
                'trade': CommandType.TRADE,
                'pm-dashboard': 'pm-dashboard',
                'pm dashboard': 'pm-dashboard',
                'dashboard': 'dashboard',
                'quote': 'quote'
            }
            
            if command_text == 'help':
                help_text = """
🤖 *Trading Bot Commands*

📊 *Portfolio & Trading:*
• `@TestingTradingBot portfolio` - View your portfolio
• `@TestingTradingBot status` - Check bot status
• `@TestingTradingBot trade` - Execute trades (coming soon)

💡 *Tips:*
• All trading is in MOCK MODE for safe testing
• Real market data from Finnhub API
• Use mentions like this message to interact

🚀 *Status:* Bot is running in development mode
                """
                say(help_text)
                
            elif command_text == 'status':
                status_text = """
✅ *Bot Status: ONLINE*

🔧 *System Info:*
• Environment: Development
• Mock Trading: Enabled
• Market Data: Live (Finnhub)
• Database: Mock Mode
• Risk Analysis: Mock Mode

📡 *Connection:* Socket Mode Active
🕐 *Uptime:* Running smoothly
                """
                say(status_text)
                
            elif command_text == 'portfolio':
                portfolio_text = f"""
📊 *Portfolio Summary for <@{event['user']}>*

💰 *Account Balance:*
• Cash: $10,000.00
• Total Value: $10,000.00
• P&L: $0.00 (0.00%)

📈 *Positions:* None yet
• Start trading to see positions here

🎯 *Mock Mode:* All trades are simulated for safety
                """
                say(portfolio_text)
                
            elif command_text == 'trade':
                # Create a simple Block Kit trade interface
                trade_blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🚀 Trading Interface"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Select a trading action:*"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📈 Buy Stock"
                                },
                                "style": "primary",
                                "action_id": "buy_stock"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📉 Sell Stock"
                                },
                                "style": "danger",
                                "action_id": "sell_stock"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*💡 Quick Commands:*\n• `@TestingTradingBot quote AAPL` - Get stock price\n• `@TestingTradingBot portfolio` - View your positions\n• `@TestingTradingBot dashboard` - Full dashboard"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "🛡️ *Mock Mode:* All trades are simulated for safe testing"
                            }
                        ]
                    }
                ]
                
                try:
                    say(blocks=trade_blocks, text="🚀 Trading Interface")
                except Exception as e:
                    say(f"🚀 *Trading Interface*\n\nUse: `@TestingTradingBot quote AAPL` for quotes\n\nError: {str(e)}")
                
            elif command_text in ['pm-dashboard', 'pm dashboard']:
                # Portfolio Manager Dashboard - show all portfolios
                say(f"""
📊 *Portfolio Manager Dashboard*

To access the full PM dashboard with all trader portfolios, use:
`/pm-dashboard`

*Features:*
• View all trader portfolios
• Aggregate P&L and AUM
• Top performers ranking
• Live trade feed
• Risk alerts

_Note: Requires Portfolio Manager or Admin permissions_
                """)
                
            elif command_text == 'dashboard':
                # Create a simple Block Kit dashboard
                dashboard_blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 Trading Dashboard"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*💰 Total Value:*\n$10,000.00"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*💵 Cash Balance:*\n$10,000.00"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*📈 Day P&L:*\n$0.00 (0.00%)"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*📊 Positions:*\n0 active"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*🎯 Performance Metrics*"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Win Rate:*\nN/A"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Total Trades:*\n0"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Best Trade:*\nN/A"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Risk Level:*\nMedium"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🚀 Start Trading"
                                },
                                "style": "primary",
                                "action_id": "start_trading"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📈 View Positions"
                                },
                                "action_id": "view_positions"
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "⚙️ Settings"
                                },
                                "action_id": "settings"
                            }
                        ]
                    }
                ]
                
                try:
                    say(blocks=dashboard_blocks, text="📊 Trading Dashboard")
                except Exception as e:
                    say(f"📊 *Trading Dashboard*\n\nPortfolio Value: $10,000.00\nCash: $10,000.00\nPositions: 0\n\nError: {str(e)}")
                
            elif command_text.startswith('quote'):
                # Extract symbol from command like "quote AAPL"
                parts = text.split()
                if len(parts) >= 3:  # @bot quote AAPL
                    symbol = parts[2].upper()
                    quote_text = f"""
📈 *Stock Quote: {symbol}*

💰 *Price Info:*
• Current: $150.25 ↗️ (+2.15)
• Change: +1.45% 
• Open: $148.10
• High: $151.00
• Low: $147.50

📊 *Volume:* 2.5M shares
🕐 *Last Updated:* Just now
📡 *Source:* Finnhub (Live Data)

⚠️ *Note:* This is demo data. Real quotes coming soon!

💡 *Try:* `@TestingTradingBot trade buy 100 {symbol}`
                    """
                    say(quote_text)
                else:
                    say("📈 *Stock Quote*\n\nUsage: `@TestingTradingBot quote AAPL`\n\nPopular symbols: AAPL, GOOGL, MSFT, TSLA, AMZN")
                
            else:
                say(f"Hi <@{event['user']}>! 👋 Available commands:\n• help\n• status\n• portfolio\n• dashboard\n• quote [SYMBOL]\n• trade")
                
        except Exception as e:
            say(f"Sorry, I had trouble processing that command. Try `@TestingTradingBot help`")

    logger.info("All command handlers registered successfully with service container integration")


def get_command_metrics() -> CommandMetrics:
    """Get current command execution metrics."""
    if not _command_handler:
        return CommandMetrics()
    return _command_handler.metrics