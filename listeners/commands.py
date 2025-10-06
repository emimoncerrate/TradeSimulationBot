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
            # Acknowledge command immediately (within 3 seconds)
            ack()
            
            # Create command context
            command_context = self._create_command_context(command_type, body, context)
            
            logger.info(
                "Processing command",
                command_type=command_type.value,
                user_id=command_context.slack_user_id,
                channel_id=command_context.channel_id,
                request_id=command_context.request_id
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
                "Command processed successfully",
                command_type=command_type.value,
                user_id=command_context.slack_user_id,
                request_id=command_context.request_id,
                response_time=f"{(time.time() - start_time) * 1000:.2f}ms"
            )
            
        except RateLimitError as e:
            error_type = "RATE_LIMIT"
            self.metrics.authentication_failures += 1
            await self._send_error_response(
                client, command_context, 
                f"⏱️ Rate limit exceeded. {e.message}",
                ephemeral=True
            )
            logger.warning(
                "Rate limit exceeded",
                user_id=command_context.slack_user_id if command_context else "unknown",
                error=str(e)
            )
            
        except AuthenticationError as e:
            error_type = "AUTHENTICATION"
            self.metrics.authentication_failures += 1
            await self._send_error_response(
                client, command_context,
                f"🔐 Authentication failed: {e.message}",
                ephemeral=True
            )
            logger.warning(
                "Authentication failed",
                user_id=command_context.slack_user_id if command_context else "unknown",
                error=str(e)
            )
            
        except AuthorizationError as e:
            error_type = "AUTHORIZATION"
            self.metrics.authorization_failures += 1
            await self._send_error_response(
                client, command_context,
                f"🚫 Access denied: {e.message}",
                ephemeral=True
            )
            logger.warning(
                "Authorization failed",
                user_id=command_context.slack_user_id if command_context else "unknown",
                error=str(e)
            )
            
        except CommandValidationError as e:
            error_type = "VALIDATION"
            self.metrics.validation_failures += 1
            await self._send_error_response(
                client, command_context,
                f"❌ Invalid command: {e.message}",
                ephemeral=True
            )
            logger.warning(
                "Command validation failed",
                user_id=command_context.slack_user_id if command_context else "unknown",
                error=str(e)
            )
            
        except SecurityViolationError as e:
            error_type = "SECURITY_VIOLATION"
            await self._send_error_response(
                client, command_context,
                "🚨 Security violation detected. This incident has been logged.",
                ephemeral=True
            )
            logger.error(
                "Security violation detected",
                user_id=command_context.slack_user_id if command_context else "unknown",
                violation_type=e.violation_type,
                error=str(e)
            )
            
        except SlackApiError as e:
            error_type = "SLACK_API"
            await self._send_error_response(
                client, command_context,
                "📡 Communication error with Slack. Please try again.",
                ephemeral=True
            )
            logger.error(
                "Slack API error",
                user_id=command_context.slack_user_id if command_context else "unknown",
                error=str(e)
            )
            
        except Exception as e:
            error_type = "SYSTEM"
            await self._send_error_response(
                client, command_context,
                "⚠️ System error occurred. Please try again or contact support.",
                ephemeral=True
            )
            logger.error(
                "Unexpected error processing command",
                command_type=command_type.value if command_type else "unknown",
                user_id=command_context.slack_user_id if command_context else "unknown",
                error=str(e),
                exc_info=True
            )
            
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
        
        # Validate channel access
        await self._validate_channel_access(command_context)
        
        # Authenticate user and create session
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
                None,  # We don't have user yet, so pass None
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
        """Handle /portfolio command to show portfolio dashboard."""
        try:
            # Validate user has portfolio viewing permissions
            if not command_context.user.has_permission(Permission.VIEW_PORTFOLIO):
                raise CommandAuthorizationError(
                    "You don't have permission to view portfolio information.",
                    Permission.VIEW_PORTFOLIO.value
                )
            
            # Send message directing user to App Home
            await asyncio.to_thread(
                client.chat_postEphemeral,
                channel=command_context.channel_id,
                user=command_context.slack_user_id,
                text="📊 *Portfolio Dashboard*\n\n"
                     "Your portfolio information is available in the *App Home* tab. "
                     "Click on the bot name in the sidebar or search for 'Jain Global Trading Bot' "
                     "to access your personalized dashboard with positions, P&L, and trade history."
            )
            
            logger.info(
                "Portfolio command processed",
                user_id=command_context.user.user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling portfolio command: {str(e)}")
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
    
    # Create command handler for non-trade commands
    command_handler = CommandHandler(auth_service, database_service)
    
    # ========================================
    # ENHANCED /TRADE COMMAND WITH LIVE MARKET DATA
    # ========================================
    try:
        from services.market_data import MarketDataService
        from listeners.enhanced_trade_command import EnhancedTradeCommand
        from listeners.enhanced_market_actions import EnhancedMarketActions
        
        # Get market data service
        market_data_service = container.get(MarketDataService)
        
        # Create enhanced trade command
        enhanced_trade_command = EnhancedTradeCommand(market_data_service, auth_service)
        
        logger.info("✅ Enhanced trade command created successfully")
        
        # Register the enhanced trade command
        @app.command("/trade")
        def handle_enhanced_trade_command(ack, body, client, context):
            """Handle the enhanced /trade slash command with live market data."""
            ack()  # Acknowledge immediately
            
            # Run the async command in a thread
            import threading
            import asyncio
            
            def run_async_command():
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Create a mock ack function since we already acknowledged
                    def mock_ack():
                        pass
                    
                    # Run the async command
                    loop.run_until_complete(
                        enhanced_trade_command.handle_trade_command(mock_ack, body, client, context)
                    )
                except Exception as e:
                    logger.error(f"Enhanced trade command error: {e}")
                finally:
                    loop.close()
            
            # Start the async command in a separate thread
            thread = threading.Thread(target=run_async_command)
            thread.start()
        
    except Exception as e:
        logger.error(f"❌ Failed to create enhanced trade command: {e}")
        # Fall back to original trade command
        @app.command("/trade")
        async def handle_fallback_trade_command(ack, body, client, context):
            """Fallback trade command handler."""
            await command_handler.process_command(
                CommandType.TRADE, body, client, ack, context
            )
        logger.info("⚠️ Using fallback trade command")
        return
    
    # Register enhanced market data action handlers using the dedicated registration function
    from listeners.enhanced_market_actions import register_enhanced_market_actions
    register_enhanced_market_actions(app, enhanced_trade_command)
    
    logger.info("✅ Enhanced /trade command with live market data registered successfully")
    logger.info("🎯 Enhanced features available: live market data, auto-refresh, interactive controls")
    
    @app.command("/portfolio")
    async def handle_portfolio_command(ack, body, client, context):
        """Handle the /portfolio slash command."""
        await command_handler.process_command(
            CommandType.PORTFOLIO, body, client, ack, context
        )
    
    @app.command("/help")
    async def handle_help_command(ack, body, client, context):
        """Handle the /help slash command."""
        await command_handler.process_command(
            CommandType.HELP, body, client, ack, context
        )
    
    @app.command("/status")
    async def handle_status_command(ack, body, client, context):
        """Handle the /status slash command."""
        await command_handler.process_command(
            CommandType.STATUS, body, client, ack, context
        )
    
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