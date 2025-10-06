"""
Comprehensive Slack Event Handlers for Jain Global Trading Bot

This module provides complete event handling functionality for App Home tab rendering,
workspace events, user onboarding, preference management, real-time updates, data
refresh mechanisms, user activity tracking, and comprehensive event processing with
error recovery and state management.

The EventHandler class manages complex App Home workflows including dashboard rendering,
portfolio displays, trade history, performance metrics, user preferences, and real-time
data updates while maintaining detailed audit trails and providing rich user experiences.
"""

import asyncio
from utils.async_compat import to_thread
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
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
from services.auth import AuthService, AuthenticationError, AuthorizationError, SessionError
from services.database import DatabaseService, DatabaseError, NotFoundError
from services.market_data import MarketDataService, MarketDataError
from services.service_container import ServiceContainer, get_container
from models.user import User, UserRole, Permission
from models.trade import Trade, TradeStatus
from models.portfolio import Position
from ui.dashboard import Dashboard, DashboardContext, DashboardTheme
from ui.notifications import NotificationService
from utils.formatters import format_money, format_percent

def format_number(value):
    """Simple number formatter with commas."""
    return f"{value:,}"
from config.settings import get_config

# Configure logging
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enumeration of supported event types."""
    APP_HOME_OPENED = "app_home_opened"
    USER_CHANGE = "user_change"
    TEAM_JOIN = "team_join"
    MEMBER_JOINED_CHANNEL = "member_joined_channel"
    MEMBER_LEFT_CHANNEL = "member_left_channel"
    MESSAGE = "message"
    REACTION_ADDED = "reaction_added"
    REACTION_REMOVED = "reaction_removed"


class EventError(Exception):
    """Base exception for event handling errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, user_friendly: bool = True):
        self.message = message
        self.error_code = error_code
        self.user_friendly = user_friendly
        super().__init__(self.message)


class EventProcessingError(EventError):
    """Exception for event processing errors."""
    pass


@dataclass
class EventContext:
    """Context information for event processing."""
    event_type: EventType
    event_id: str
    event_time: datetime
    user_id: Optional[str]
    team_id: str
    channel_id: Optional[str]
    
    # Event-specific data
    event_data: Dict[str, Any]
    
    # Request metadata
    request_id: str
    
    # Authentication context
    user: Optional[User] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


class EventMetrics:
    """Event processing metrics tracking."""
    
    def __init__(self):
        self.events_processed = 0
        self.events_successful = 0
        self.events_failed = 0
        self.app_home_opens = 0
        self.dashboard_renders = 0
        self.user_onboardings = 0
        self.preference_updates = 0
        self.response_times = {}
        self.error_counts = {}
        
    def record_event(self, event_type: EventType, success: bool, response_time: float,
                    error_type: Optional[str] = None):
        """Record event processing metrics."""
        self.events_processed += 1
        if success:
            self.events_successful += 1
        else:
            self.events_failed += 1
            if error_type:
                self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Track response times by event type
        if event_type.value not in self.response_times:
            self.response_times[event_type.value] = []
        self.response_times[event_type.value].append(response_time)
        
        # Keep only last 100 response times per event type
        if len(self.response_times[event_type.value]) > 100:
            self.response_times[event_type.value] = self.response_times[event_type.value][-100:]
        
        # Track specific event types
        if event_type == EventType.APP_HOME_OPENED:
            self.app_home_opens += 1
    
    def get_average_response_time(self, event_type: Optional[EventType] = None) -> float:
        """Get average response time in milliseconds."""
        if event_type:
            times = self.response_times.get(event_type.value, [])
            return sum(times) / len(times) * 1000 if times else 0.0
        else:
            all_times = []
            for times in self.response_times.values():
                all_times.extend(times)
            return sum(all_times) / len(all_times) * 1000 if all_times else 0.0
    
    def get_success_rate(self) -> float:
        """Get event success rate as percentage."""
        return (self.events_successful / self.events_processed * 100) if self.events_processed > 0 else 0.0


class EventHandler:
    """
    Comprehensive event handler with dashboard rendering and user management.
    
    This class provides complete event processing functionality including:
    - App Home tab rendering and dashboard management
    - User onboarding and preference management
    - Real-time data updates and refresh mechanisms
    - User activity tracking and analytics
    - Workspace event processing and notifications
    - Comprehensive error handling and recovery
    - Performance metrics and monitoring
    - State management and caching
    """
    
    def __init__(self, auth_service: AuthService, database_service: DatabaseService,
                 market_data_service: MarketDataService):
        """
        Initialize event handler with required services.
        
        Args:
            auth_service: Authentication service instance
            database_service: Database service instance
            market_data_service: Market data service instance
        """
        self.auth_service = auth_service
        self.db_service = database_service
        self.market_data_service = market_data_service
        self.config = get_config()
        
        # Initialize UI components
        self.dashboard = Dashboard()
        self.notification_service = NotificationService()
        
        # Metrics tracking
        self.metrics = EventMetrics()
        
        # Event routing table
        self.event_routes = {
            EventType.APP_HOME_OPENED: self._handle_app_home_opened,
            EventType.USER_CHANGE: self._handle_user_change,
            EventType.TEAM_JOIN: self._handle_team_join,
            EventType.MEMBER_JOINED_CHANNEL: self._handle_member_joined_channel,
            EventType.MEMBER_LEFT_CHANNEL: self._handle_member_left_channel,
            EventType.MESSAGE: self._handle_message,
            EventType.REACTION_ADDED: self._handle_reaction_added,
            EventType.REACTION_REMOVED: self._handle_reaction_removed
        }
        
        # Dashboard cache for performance
        self._dashboard_cache = {}  # user_id -> (dashboard_data, timestamp)
        self._cache_ttl = 300  # 5 minutes
        
        # User activity tracking
        self._user_activity = {}  # user_id -> last_activity_time
        
        # Real-time update subscriptions
        self._update_subscriptions = {}  # user_id -> subscription_data
        
        logger.info("EventHandler initialized with comprehensive dashboard and user management")
    
    async def process_event(self, event_type: EventType, event_data: Dict[str, Any],
                          client: WebClient, context: BoltContext) -> None:
        """
        Process Slack event with comprehensive validation and error handling.
        
        Args:
            event_type: Type of event being processed
            event_data: Slack event payload
            client: Slack WebClient instance
            context: Bolt context
        """
        start_time = time.time()
        event_context = None
        success = False
        error_type = None
        
        try:
            # Create event context
            event_context = self._create_event_context(event_type, event_data, context)
            
            logger.info(
                "Processing event",
                event_type=event_type.value,
                user_id=event_context.user_id,
                team_id=event_context.team_id,
                request_id=event_context.request_id
            )
            
            # Authenticate user if user_id is present
            if event_context.user_id:
                await self._authenticate_user(event_context)
            
            # Route to specific event handler
            handler = self.event_routes.get(event_type)
            if not handler:
                logger.warning(f"No handler for event type: {event_type.value}")
                return
            
            # Execute event handler
            await handler(event_context, client)
            
            success = True
            logger.info(
                "Event processed successfully",
                event_type=event_type.value,
                user_id=event_context.user_id,
                request_id=event_context.request_id,
                response_time=f"{(time.time() - start_time) * 1000:.2f}ms"
            )
            
        except AuthenticationError as e:
            error_type = "AUTHENTICATION"
            logger.warning(
                "Authentication failed for event",
                user_id=event_context.user_id if event_context else "unknown",
                error=str(e)
            )
            
        except AuthorizationError as e:
            error_type = "AUTHORIZATION"
            logger.warning(
                "Authorization failed for event",
                user_id=event_context.user_id if event_context else "unknown",
                error=str(e)
            )
            
        except SlackApiError as e:
            error_type = "SLACK_API"
            logger.error(
                "Slack API error",
                user_id=event_context.user_id if event_context else "unknown",
                error=str(e)
            )
            
        except Exception as e:
            error_type = "SYSTEM"
            logger.error(
                "Unexpected error processing event",
                event_type=event_type.value if event_type else "unknown",
                user_id=event_context.user_id if event_context else "unknown",
                error=str(e),
                exc_info=True
            )
            
        finally:
            # Record metrics
            response_time = time.time() - start_time
            self.metrics.record_event(event_type, success, response_time, error_type)
            
            # Log audit event
            if event_context:
                await self._log_audit_event(event_context, success, error_type, response_time)
    
    def _create_event_context(self, event_type: EventType, event_data: Dict[str, Any],
                             context: BoltContext) -> EventContext:
        """Create event context from Slack payload."""
        return EventContext(
            event_type=event_type,
            event_id=event_data.get('event_id', str(uuid.uuid4())),
            event_time=datetime.fromtimestamp(event_data.get('event_ts', time.time()), tz=timezone.utc),
            user_id=event_data.get('user'),
            team_id=event_data.get('team', ''),
            channel_id=event_data.get('channel'),
            event_data=event_data,
            request_id=str(uuid.uuid4())
        )
    
    async def _authenticate_user(self, event_context: EventContext) -> None:
        """Authenticate user for event processing."""
        try:
            user, session = await self.auth_service.authenticate_slack_user(
                event_context.user_id,
                event_context.team_id,
                event_context.channel_id
            )
            
            event_context.user = user
            event_context.session_id = session.session_id
            
            # Update user activity tracking
            self._user_activity[event_context.user_id] = datetime.now(timezone.utc)
            
        except AuthenticationError:
            # Some events don't require authentication, so we'll continue without user context
            logger.debug(f"Could not authenticate user {event_context.user_id} for event processing")
        except Exception as e:
            logger.warning(f"Unexpected error during user authentication: {str(e)}")
    
    async def _handle_app_home_opened(self, event_context: EventContext, client: WebClient) -> None:
        """Handle App Home tab opened event."""
        try:
            if not event_context.user:
                logger.warning("App Home opened but user not authenticated")
                return
            
            # Check if user has permission to view dashboard
            if not event_context.user.has_permission(Permission.VIEW_PORTFOLIO):
                await self._render_access_denied_home(client, event_context)
                return
            
            # Check dashboard cache
            cached_dashboard = self._get_cached_dashboard(event_context.user.user_id)
            if cached_dashboard:
                await self._publish_app_home(client, event_context.user_id, cached_dashboard)
                return
            
            # Create dashboard context
            dashboard_context = await self._create_dashboard_context(event_context.user)
            
            # Render dashboard
            dashboard_view = await self.dashboard.create_dashboard_view(dashboard_context)
            
            # Cache dashboard
            self._cache_dashboard(event_context.user.user_id, dashboard_view)
            
            # Publish to App Home
            await self._publish_app_home(client, event_context.user_id, dashboard_view)
            
            # Track dashboard render
            self.metrics.dashboard_renders += 1
            
            # Check if this is first time opening (onboarding)
            if await self._is_first_app_home_visit(event_context.user):
                await self._handle_user_onboarding(client, event_context)
            
            logger.info(
                "App Home dashboard rendered",
                user_id=event_context.user.user_id,
                role=event_context.user.role.value
            )
            
        except Exception as e:
            logger.error(f"Error handling App Home opened: {str(e)}")
            await self._render_error_home(client, event_context, str(e))
    
    async def _handle_user_change(self, event_context: EventContext, client: WebClient) -> None:
        """Handle user profile change event."""
        try:
            if not event_context.user:
                return
            
            # Update user profile from Slack data
            slack_user_data = event_context.event_data.get('user', {})
            if slack_user_data:
                await self._update_user_profile(event_context.user, slack_user_data)
            
            # Invalidate dashboard cache
            self._invalidate_dashboard_cache(event_context.user.user_id)
            
            logger.info(
                "User profile updated",
                user_id=event_context.user.user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling user change: {str(e)}")
    
    async def _handle_team_join(self, event_context: EventContext, client: WebClient) -> None:
        """Handle new team member join event."""
        try:
            new_user_id = event_context.event_data.get('user', {}).get('id')
            if not new_user_id:
                return
            
            # Send welcome message to new user
            await self._send_welcome_message(client, new_user_id)
            
            # Log new user join
            logger.info(
                "New team member joined",
                new_user_id=new_user_id,
                team_id=event_context.team_id
            )
            
        except Exception as e:
            logger.error(f"Error handling team join: {str(e)}")
    
    async def _handle_member_joined_channel(self, event_context: EventContext, client: WebClient) -> None:
        """Handle member joined channel event."""
        try:
            # Check if this is an approved trading channel
            if event_context.channel_id:
                is_approved = await self.db_service.is_channel_approved(event_context.channel_id)
                if is_approved and event_context.user:
                    # Send channel welcome message
                    await self._send_channel_welcome_message(client, event_context)
            
            logger.info(
                "Member joined channel",
                user_id=event_context.user_id,
                channel_id=event_context.channel_id
            )
            
        except Exception as e:
            logger.error(f"Error handling member joined channel: {str(e)}")
    
    async def _handle_member_left_channel(self, event_context: EventContext, client: WebClient) -> None:
        """Handle member left channel event."""
        try:
            logger.info(
                "Member left channel",
                user_id=event_context.user_id,
                channel_id=event_context.channel_id
            )
            
        except Exception as e:
            logger.error(f"Error handling member left channel: {str(e)}")
    
    async def _handle_message(self, event_context: EventContext, client: WebClient) -> None:
        """Handle message event for activity tracking."""
        try:
            # Update user activity if user is authenticated
            if event_context.user:
                self._user_activity[event_context.user.user_id] = datetime.now(timezone.utc)
            
            # Check for mentions or specific keywords that might need responses
            message_text = event_context.event_data.get('text', '').lower()
            if 'help' in message_text and event_context.user:
                # Could trigger help response in DM
                pass
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    async def _handle_reaction_added(self, event_context: EventContext, client: WebClient) -> None:
        """Handle reaction added event."""
        try:
            # Track user engagement
            if event_context.user:
                self._user_activity[event_context.user.user_id] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error handling reaction added: {str(e)}")
    
    async def _handle_reaction_removed(self, event_context: EventContext, client: WebClient) -> None:
        """Handle reaction removed event."""
        try:
            # Track user engagement
            if event_context.user:
                self._user_activity[event_context.user.user_id] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error handling reaction removed: {str(e)}")
    
    async def _create_dashboard_context(self, user: User) -> DashboardContext:
        """Create dashboard context for user."""
        try:
            # Get user's positions
            positions = await self.db_service.get_user_positions(user.user_id)
            
            # Get recent trades
            recent_trades = await self.db_service.get_user_trades(user.user_id, limit=10)
            
            # Calculate portfolio metrics
            total_value = sum(pos.current_value for pos in positions)
            total_pnl = sum(pos.unrealized_pnl for pos in positions)
            
            # Get market data for positions
            position_quotes = {}
            for position in positions:
                try:
                    quote = await self.market_data_service.get_quote(position.symbol)
                    position_quotes[position.symbol] = quote
                except MarketDataError:
                    # Continue without market data for this position
                    pass
            
            return DashboardContext(
                user=user,
                positions=positions,
                recent_trades=recent_trades,
                total_portfolio_value=total_value,
                total_unrealized_pnl=total_pnl,
                market_quotes=position_quotes,
                theme=DashboardTheme.STANDARD
            )
            
        except Exception as e:
            logger.error(f"Error creating dashboard context: {str(e)}")
            # Return minimal context
            return DashboardContext(
                user=user,
                positions=[],
                recent_trades=[],
                total_portfolio_value=0,
                total_unrealized_pnl=0,
                market_quotes={},
                theme=DashboardTheme.STANDARD
            )
    
    def _get_cached_dashboard(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached dashboard if not expired."""
        if user_id in self._dashboard_cache:
            dashboard_data, timestamp = self._dashboard_cache[user_id]
            if time.time() - timestamp < self._cache_ttl:
                return dashboard_data
            else:
                # Remove expired cache
                del self._dashboard_cache[user_id]
        return None
    
    def _cache_dashboard(self, user_id: str, dashboard_data: Dict[str, Any]) -> None:
        """Cache dashboard data."""
        self._dashboard_cache[user_id] = (dashboard_data, time.time())
        
        # Simple cache cleanup
        if len(self._dashboard_cache) > 100:
            oldest_user = min(self._dashboard_cache.keys(), 
                            key=lambda k: self._dashboard_cache[k][1])
            del self._dashboard_cache[oldest_user]
    
    def _invalidate_dashboard_cache(self, user_id: str) -> None:
        """Invalidate cached dashboard for user."""
        if user_id in self._dashboard_cache:
            del self._dashboard_cache[user_id]
    
    async def _publish_app_home(self, client: WebClient, user_id: str, view: Dict[str, Any]) -> None:
        """Publish view to App Home."""
        try:
            await to_thread(
                client.views_publish,
                user_id=user_id,
                view=view
            )
        except SlackApiError as e:
            logger.error(f"Failed to publish App Home: {str(e)}")
            raise
    
    async def _render_access_denied_home(self, client: WebClient, event_context: EventContext) -> None:
        """Render access denied App Home."""
        try:
            view = {
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🚫 *Access Denied*\n\nYou don't have permission to view the trading dashboard. Please contact your administrator for access."
                        }
                    }
                ]
            }
            
            await self._publish_app_home(client, event_context.user_id, view)
            
        except Exception as e:
            logger.error(f"Error rendering access denied home: {str(e)}")
    
    async def _render_error_home(self, client: WebClient, event_context: EventContext, error_message: str) -> None:
        """Render error App Home."""
        try:
            view = {
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"⚠️ *Dashboard Error*\n\nSorry, there was an error loading your dashboard. Please try again later.\n\n*Error:* {error_message}"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "🔄 Refresh"
                                },
                                "action_id": "refresh_dashboard"
                            }
                        ]
                    }
                ]
            }
            
            await self._publish_app_home(client, event_context.user_id, view)
            
        except Exception as e:
            logger.error(f"Error rendering error home: {str(e)}")
    
    async def _is_first_app_home_visit(self, user: User) -> bool:
        """Check if this is user's first App Home visit."""
        try:
            # Check user's last login or app home visit timestamp
            # This is a simplified check - could be enhanced with more sophisticated tracking
            return user.created_at and (datetime.now(timezone.utc) - user.created_at).days < 1
        except Exception:
            return False
    
    async def _handle_user_onboarding(self, client: WebClient, event_context: EventContext) -> None:
        """Handle user onboarding process."""
        try:
            # Send onboarding welcome message
            welcome_message = self._build_onboarding_message(event_context.user)
            
            await to_thread(
                client.chat_postMessage,
                channel=event_context.user_id,  # DM to user
                text=welcome_message
            )
            
            # Track onboarding
            self.metrics.user_onboardings += 1
            
            logger.info(
                "User onboarding completed",
                user_id=event_context.user.user_id
            )
            
        except Exception as e:
            logger.error(f"Error handling user onboarding: {str(e)}")
    
    def _build_onboarding_message(self, user: User) -> str:
        """Build personalized onboarding message."""
        role_specific = ""
        if user.role == UserRole.RESEARCH_ANALYST:
            role_specific = (
                "\n*As a Research Analyst, you can:*\n"
                "• Execute trades with comprehensive risk analysis\n"
                "• Access advanced research tools and market data\n"
                "• Collaborate with your assigned Portfolio Manager\n"
            )
        elif user.role == UserRole.EXECUTION_TRADER:
            role_specific = (
                "\n*As an Execution Trader, you can:*\n"
                "• Execute trades quickly with streamlined interface\n"
                "• Access real-time market data and execution tools\n"
                "• Monitor trade execution and confirmations\n"
            )
        elif user.role == UserRole.PORTFOLIO_MANAGER:
            role_specific = (
                "\n*As a Portfolio Manager, you can:*\n"
                "• Oversee portfolio performance and risk metrics\n"
                "• Review and approve high-risk trades\n"
                "• Monitor team trading activity and compliance\n"
            )
        
        return (
            f"🎉 *Welcome to Jain Global Trading Bot, {user.profile.display_name}!*\n\n"
            f"Your trading command center is now ready. Here's what you can do:\n\n"
            f"📊 *Dashboard:* View your portfolio, positions, and P&L in the App Home tab\n"
            f"💼 *Trading:* Use `/trade` in approved channels to execute trades\n"
            f"🔍 *Risk Analysis:* Get AI-powered risk assessments for all trades\n"
            f"📈 *Market Data:* Access real-time market information\n"
            f"{role_specific}\n"
            f"*Need help?* Use `/help` for commands or contact your administrator.\n\n"
            f"Happy trading! 🚀"
        )
    
    async def _send_welcome_message(self, client: WebClient, user_id: str) -> None:
        """Send welcome message to new team member."""
        try:
            message = (
                "👋 *Welcome to Jain Global!*\n\n"
                "You now have access to our Slack Trading Bot. To get started:\n\n"
                "1. Visit the *App Home* tab to see your dashboard\n"
                "2. Use `/trade` in approved channels to execute trades\n"
                "3. Use `/help` to see all available commands\n\n"
                "Your account will be set up shortly. Contact your administrator if you need immediate access."
            )
            
            await to_thread(
                client.chat_postMessage,
                channel=user_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error sending welcome message: {str(e)}")
    
    async def _send_channel_welcome_message(self, client: WebClient, event_context: EventContext) -> None:
        """Send welcome message when user joins approved trading channel."""
        try:
            message = (
                f"👋 Welcome to this trading channel, <@{event_context.user_id}>!\n\n"
                f"This channel is approved for trading commands. You can:\n"
                f"• Use `/trade` to execute trades\n"
                f"• Get real-time market data and risk analysis\n"
                f"• Collaborate with your team on trading decisions\n\n"
                f"Use `/help` for more information about available commands."
            )
            
            await to_thread(
                client.chat_postMessage,
                channel=event_context.channel_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error sending channel welcome message: {str(e)}")
    
    async def _update_user_profile(self, user: User, slack_user_data: Dict[str, Any]) -> None:
        """Update user profile with latest Slack data."""
        try:
            profile = slack_user_data.get('profile', {})
            updates = {}
            
            # Check for profile updates
            new_name = slack_user_data.get('real_name', slack_user_data.get('name', ''))
            if new_name and new_name != user.profile.display_name:
                updates['display_name'] = new_name
            
            new_email = profile.get('email', '')
            if new_email and new_email != user.profile.email:
                updates['email'] = new_email
            
            # Update if there are changes
            if updates:
                user.update_profile(**updates)
                await self.db_service.update_user(user)
                logger.info(f"Updated profile for user {user.user_id}")
                
        except Exception as e:
            logger.warning(f"Failed to update user profile: {str(e)}")
    
    async def _log_audit_event(self, event_context: EventContext, success: bool,
                             error_type: Optional[str], response_time: float) -> None:
        """Log audit event for event processing."""
        try:
            audit_data = {
                'event_type': event_context.event_type.value,
                'event_id': event_context.event_id,
                'user_id': event_context.user.user_id if event_context.user else None,
                'slack_user_id': event_context.user_id,
                'team_id': event_context.team_id,
                'channel_id': event_context.channel_id,
                'success': success,
                'error_type': error_type,
                'response_time_ms': response_time * 1000,
                'request_id': event_context.request_id
            }
            
            # Log to database audit trail
            await self.db_service.log_audit_event(
                'event_processed',
                event_context.user.user_id if event_context.user else event_context.user_id,
                audit_data
            )
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
    
    def get_user_activity_status(self, user_id: str) -> Optional[datetime]:
        """Get last activity time for user."""
        return self._user_activity.get(user_id)
    
    def get_active_users(self, since: Optional[datetime] = None) -> List[str]:
        """Get list of active users since specified time."""
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=1)
        
        return [
            user_id for user_id, last_activity in self._user_activity.items()
            if last_activity > since
        ]


# Global event handler instance
_event_handler: Optional[EventHandler] = None


def initialize_event_handler(auth_service: AuthService, database_service: DatabaseService,
                           market_data_service: MarketDataService) -> None:
    """Initialize global event handler instance."""
    global _event_handler
    _event_handler = EventHandler(auth_service, database_service, market_data_service)
    logger.info("Event handler initialized globally")


def register_event_handlers(app: App, service_container: Optional['ServiceContainer'] = None) -> None:
    """
    Register all event handlers with the Slack app.
    
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
    
    # Create event handler
    event_handler = EventHandler(auth_service, database_service, market_data_service)
    
    @app.event("app_home_opened")
    async def handle_app_home_opened(event, client, context):
        """Handle when a user opens the App Home tab."""
        await event_handler.process_event(
            EventType.APP_HOME_OPENED, event, client, context
        )
    
    @app.event("user_change")
    async def handle_user_change(event, client, context):
        """Handle user profile change events."""
        await event_handler.process_event(
            EventType.USER_CHANGE, event, client, context
        )
    
    @app.event("team_join")
    async def handle_team_join(event, client, context):
        """Handle new team member join events."""
        await event_handler.process_event(
            EventType.TEAM_JOIN, event, client, context
        )
    
    @app.event("member_joined_channel")
    async def handle_member_joined_channel(event, client, context):
        """Handle member joined channel events."""
        await event_handler.process_event(
            EventType.MEMBER_JOINED_CHANNEL, event, client, context
        )
    
    @app.event("member_left_channel")
    async def handle_member_left_channel(event, client, context):
        """Handle member left channel events."""
        await event_handler.process_event(
            EventType.MEMBER_LEFT_CHANNEL, event, client, context
        )
    
    @app.event("message")
    async def handle_message(event, client, context):
        """Handle message events for activity tracking."""
        # Only process messages in channels (not DMs) and ignore bot messages
        if event.get('channel_type') == 'channel' and not event.get('bot_id'):
            await event_handler.process_event(
                EventType.MESSAGE, event, client, context
            )
    
    @app.event("reaction_added")
    async def handle_reaction_added(event, client, context):
        """Handle reaction added events."""
        await event_handler.process_event(
            EventType.REACTION_ADDED, event, client, context
        )
    
    @app.event("reaction_removed")
    async def handle_reaction_removed(event, client, context):
        """Handle reaction removed events."""
        await event_handler.process_event(
            EventType.REACTION_REMOVED, event, client, context
        )
    
    # Dashboard refresh action handler
    @app.action("refresh_dashboard")
    async def handle_refresh_dashboard(ack, body, client, context):
        """Handle dashboard refresh button click."""
        ack()
        
        user_id = body['user']['id']
        
        # Invalidate cache and trigger App Home refresh
        event_handler._invalidate_dashboard_cache(user_id)
        
        # Simulate app_home_opened event to refresh
        fake_event = {
            'user': user_id,
            'team': body.get('team', {}).get('id', ''),
            'event_ts': time.time()
        }
        
        await event_handler.process_event(
            EventType.APP_HOME_OPENED, fake_event, client, context
        )
    
    # Store handler globally for metrics access
    global _event_handler
    _event_handler = event_handler
    
    logger.info("All event handlers registered successfully with service container integration")


def get_event_metrics() -> EventMetrics:
    """Get current event processing metrics."""
    if not _event_handler:
        return EventMetrics()
    return _event_handler.metrics


def get_user_activity_status(user_id: str) -> Optional[datetime]:
    """Get last activity time for user."""
    if not _event_handler:
        return None
    return _event_handler.get_user_activity_status(user_id)


def get_active_users(since: Optional[datetime] = None) -> List[str]:
    """Get list of active users since specified time."""
    if not _event_handler:
        return []
    return _event_handler.get_active_users(since)