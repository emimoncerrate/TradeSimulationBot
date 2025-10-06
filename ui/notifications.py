"""
Comprehensive notification and messaging components for Jain Global Slack Trading Bot.

This module provides sophisticated message handling for high-risk trade notifications,
execution confirmations, error messaging, and user preference management. It implements
notification routing, delivery tracking, and rich message formatting with attachments,
buttons, and interactive elements.

The NotificationService class creates targeted, role-aware notifications that enhance
user experience and ensure critical information is communicated effectively.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio

from models.trade import Trade, TradeStatus, RiskLevel, TradeType
from models.user import User, UserRole, Permission
from models.portfolio import Portfolio, Position
from services.risk_analysis import RiskAnalysis, RiskFactor
from utils.formatters import (
    format_money, format_percent, 
    format_date
)

def format_number(value):
    """Simple number formatter with commas."""
    return f"{value:,}"

# Configure logging
logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Notification type enumeration."""
    TRADE_CONFIRMATION = "trade_confirmation"
    TRADE_EXECUTION = "trade_execution"
    HIGH_RISK_ALERT = "high_risk_alert"
    RISK_ANALYSIS_COMPLETE = "risk_analysis_complete"
    PORTFOLIO_ALERT = "portfolio_alert"
    MARKET_ALERT = "market_alert"
    SYSTEM_NOTIFICATION = "system_notification"
    ERROR_NOTIFICATION = "error_notification"
    APPROVAL_REQUEST = "approval_request"
    COMPLIANCE_ALERT = "compliance_alert"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class DeliveryChannel(Enum):
    """Notification delivery channels."""
    SLACK_DM = "slack_dm"
    SLACK_CHANNEL = "slack_channel"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class NotificationPreferences:
    """User notification preferences."""
    user_id: str
    
    # Channel preferences
    trade_confirmations: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.SLACK_DM])
    risk_alerts: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.SLACK_DM, DeliveryChannel.SLACK_CHANNEL])
    portfolio_updates: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.SLACK_DM])
    system_notifications: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.SLACK_DM])
    error_notifications: List[DeliveryChannel] = field(default_factory=lambda: [DeliveryChannel.SLACK_DM])
    
    # Timing preferences
    quiet_hours_start: Optional[str] = "22:00"  # 10 PM
    quiet_hours_end: Optional[str] = "08:00"    # 8 AM
    timezone: str = "UTC"
    
    # Frequency limits
    max_notifications_per_hour: int = 10
    max_notifications_per_day: int = 50
    
    # Content preferences
    include_charts: bool = True
    include_risk_details: bool = True
    compact_format: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            'user_id': self.user_id,
            'trade_confirmations': [ch.value for ch in self.trade_confirmations],
            'risk_alerts': [ch.value for ch in self.risk_alerts],
            'portfolio_updates': [ch.value for ch in self.portfolio_updates],
            'system_notifications': [ch.value for ch in self.system_notifications],
            'error_notifications': [ch.value for ch in self.error_notifications],
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end,
            'timezone': self.timezone,
            'max_notifications_per_hour': self.max_notifications_per_hour,
            'max_notifications_per_day': self.max_notifications_per_day,
            'include_charts': self.include_charts,
            'include_risk_details': self.include_risk_details,
            'compact_format': self.compact_format
        }


@dataclass
class NotificationMessage:
    """Individual notification message."""
    notification_id: str
    user_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    
    # Content
    title: str
    message: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Delivery
    channels: List[DeliveryChannel] = field(default_factory=list)
    status: NotificationStatus = NotificationStatus.PENDING
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Tracking
    delivery_attempts: int = 0
    last_attempt: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    # Context data
    context: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def should_deliver_now(self) -> bool:
        """Check if notification should be delivered now."""
        if self.is_expired():
            return False
        
        if self.scheduled_for is None:
            return True
        
        return datetime.utcnow() >= self.scheduled_for
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            'notification_id': self.notification_id,
            'user_id': self.user_id,
            'notification_type': self.notification_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'blocks': self.blocks,
            'attachments': self.attachments,
            'channels': [ch.value for ch in self.channels],
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'delivery_attempts': self.delivery_attempts,
            'last_attempt': self.last_attempt.isoformat() if self.last_attempt else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'context': self.context
        }


class NotificationService:
    """
    Comprehensive notification and messaging service.
    
    Provides sophisticated message handling for trade notifications, risk alerts,
    execution confirmations, and system messages. Implements user preference
    management, delivery tracking, and rich message formatting.
    """
    
    def __init__(self):
        """Initialize notification service with configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Notification queue and tracking
        self.pending_notifications: List[NotificationMessage] = []
        self.notification_history: Dict[str, List[NotificationMessage]] = {}
        self.user_preferences: Dict[str, NotificationPreferences] = {}
        
        # Rate limiting tracking
        self.hourly_counts: Dict[str, Dict[str, int]] = {}  # user_id -> hour -> count
        self.daily_counts: Dict[str, Dict[str, int]] = {}   # user_id -> date -> count
        
        # Message templates
        self.message_templates = {
            NotificationType.TRADE_CONFIRMATION: self._create_trade_confirmation_template,
            NotificationType.TRADE_EXECUTION: self._create_trade_execution_template,
            NotificationType.HIGH_RISK_ALERT: self._create_high_risk_alert_template,
            NotificationType.RISK_ANALYSIS_COMPLETE: self._create_risk_analysis_template,
            NotificationType.PORTFOLIO_ALERT: self._create_portfolio_alert_template,
            NotificationType.ERROR_NOTIFICATION: self._create_error_notification_template,
            NotificationType.APPROVAL_REQUEST: self._create_approval_request_template,
            NotificationType.COMPLIANCE_ALERT: self._create_compliance_alert_template
        }
        
        # Color schemes for different notification types
        self.color_schemes = {
            NotificationPriority.LOW: "#36a64f",      # Green
            NotificationPriority.NORMAL: "#1264a3",   # Blue
            NotificationPriority.HIGH: "#ff8c00",     # Orange
            NotificationPriority.CRITICAL: "#e01e5a", # Red
            NotificationPriority.URGENT: "#8b0000"    # Dark Red
        }
        
        self.logger.info("NotificationService initialized")
    
    async def send_trade_confirmation(
        self, 
        user: User, 
        trade: Trade, 
        risk_analysis: Optional[RiskAnalysis] = None
    ) -> str:
        """
        Send trade confirmation notification.
        
        Args:
            user: User to notify
            trade: Trade that was executed
            risk_analysis: Optional risk analysis results
            
        Returns:
            Notification ID
        """
        try:
            # Determine priority based on trade characteristics
            priority = self._determine_trade_priority(trade, risk_analysis)
            
            # Get user preferences
            preferences = self._get_user_preferences(user.user_id)
            
            # Create notification
            notification = NotificationMessage(
                notification_id=f"trade_conf_{trade.trade_id}",
                user_id=user.user_id,
                notification_type=NotificationType.TRADE_CONFIRMATION,
                priority=priority,
                title=f"Trade Executed: {trade.symbol}",
                message=f"Your {trade.trade_type.value} order for {format_number(trade.quantity)} shares of {trade.symbol} has been executed.",
                channels=preferences.trade_confirmations,
                context={
                    'trade_id': trade.trade_id,
                    'symbol': trade.symbol,
                    'quantity': trade.quantity,
                    'price': float(trade.price),
                    'trade_type': trade.trade_type.value,
                    'risk_analysis': risk_analysis.to_dict() if risk_analysis else None
                }
            )
            
            # Generate rich message blocks
            notification.blocks = self._create_trade_confirmation_blocks(trade, risk_analysis, preferences)
            
            # Queue for delivery
            await self._queue_notification(notification)
            
            self.logger.info("Trade confirmation queued",
                           user_id=user.user_id,
                           trade_id=trade.trade_id,
                           priority=priority.value)
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send trade confirmation", error=str(e))
            raise e
    
    async def send_high_risk_alert(
        self, 
        user: User, 
        trade: Trade, 
        risk_analysis: RiskAnalysis,
        portfolio_manager: Optional[User] = None
    ) -> str:
        """
        Send high-risk trade alert notification.
        
        Args:
            user: User who initiated the trade
            trade: High-risk trade
            risk_analysis: Risk analysis results
            portfolio_manager: Portfolio manager to notify
            
        Returns:
            Notification ID
        """
        try:
            # Create notification for the trader
            trader_notification = NotificationMessage(
                notification_id=f"risk_alert_{trade.trade_id}",
                user_id=user.user_id,
                notification_type=NotificationType.HIGH_RISK_ALERT,
                priority=NotificationPriority.HIGH,
                title=f"⚠️ High-Risk Trade Alert: {trade.symbol}",
                message=f"Your proposed trade for {trade.symbol} has been flagged as high-risk and requires confirmation.",
                channels=self._get_user_preferences(user.user_id).risk_alerts,
                context={
                    'trade_id': trade.trade_id,
                    'risk_analysis': risk_analysis.to_dict(),
                    'requires_confirmation': True
                }
            )
            
            trader_notification.blocks = self._create_high_risk_alert_blocks(trade, risk_analysis, user)
            await self._queue_notification(trader_notification)
            
            # Create notification for portfolio manager if applicable
            if portfolio_manager and portfolio_manager.user_id != user.user_id:
                pm_notification = NotificationMessage(
                    notification_id=f"risk_alert_pm_{trade.trade_id}",
                    user_id=portfolio_manager.user_id,
                    notification_type=NotificationType.HIGH_RISK_ALERT,
                    priority=NotificationPriority.HIGH,
                    title=f"🚨 High-Risk Trade by {user.profile.display_name}",
                    message=f"{user.profile.display_name} is attempting a high-risk trade in {trade.symbol}.",
                    channels=self._get_user_preferences(portfolio_manager.user_id).risk_alerts,
                    context={
                        'trade_id': trade.trade_id,
                        'trader_id': user.user_id,
                        'trader_name': user.profile.display_name,
                        'risk_analysis': risk_analysis.to_dict()
                    }
                )
                
                pm_notification.blocks = self._create_portfolio_manager_alert_blocks(trade, risk_analysis, user)
                await self._queue_notification(pm_notification)
            
            self.logger.info("High-risk alert queued",
                           user_id=user.user_id,
                           trade_id=trade.trade_id,
                           risk_level=risk_analysis.overall_risk_level.value)
            
            return trader_notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send high-risk alert", error=str(e))
            raise e
    
    async def send_portfolio_alert(
        self, 
        user: User, 
        alert_type: str, 
        message: str, 
        portfolio: Optional[Portfolio] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send portfolio-related alert notification.
        
        Args:
            user: User to notify
            alert_type: Type of portfolio alert
            message: Alert message
            portfolio: Optional portfolio data
            context: Additional context data
            
        Returns:
            Notification ID
        """
        try:
            # Determine priority based on alert type
            priority_map = {
                'concentration_risk': NotificationPriority.HIGH,
                'large_loss': NotificationPriority.CRITICAL,
                'margin_call': NotificationPriority.URGENT,
                'rebalance_needed': NotificationPriority.NORMAL,
                'performance_milestone': NotificationPriority.LOW
            }
            
            priority = priority_map.get(alert_type, NotificationPriority.NORMAL)
            
            notification = NotificationMessage(
                notification_id=f"portfolio_alert_{user.user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=user.user_id,
                notification_type=NotificationType.PORTFOLIO_ALERT,
                priority=priority,
                title=f"📊 Portfolio Alert: {alert_type.replace('_', ' ').title()}",
                message=message,
                channels=self._get_user_preferences(user.user_id).portfolio_updates,
                context=context or {}
            )
            
            notification.blocks = self._create_portfolio_alert_blocks(alert_type, message, portfolio, context)
            await self._queue_notification(notification)
            
            self.logger.info("Portfolio alert queued",
                           user_id=user.user_id,
                           alert_type=alert_type,
                           priority=priority.value)
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send portfolio alert", error=str(e))
            raise e
    
    async def send_error_notification(
        self, 
        user: User, 
        error_type: str, 
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send error notification to user.
        
        Args:
            user: User to notify
            error_type: Type of error
            error_message: Error message
            context: Additional context data
            
        Returns:
            Notification ID
        """
        try:
            notification = NotificationMessage(
                notification_id=f"error_{user.user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=user.user_id,
                notification_type=NotificationType.ERROR_NOTIFICATION,
                priority=NotificationPriority.HIGH,
                title=f"❌ Error: {error_type.replace('_', ' ').title()}",
                message=error_message,
                channels=self._get_user_preferences(user.user_id).error_notifications,
                context=context or {}
            )
            
            notification.blocks = self._create_error_notification_blocks(error_type, error_message, context)
            await self._queue_notification(notification)
            
            self.logger.info("Error notification queued",
                           user_id=user.user_id,
                           error_type=error_type)
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send error notification", error=str(e))
            raise e    
   
    async def send_system_notification(
        self, 
        user: User, 
        title: str, 
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send system notification to user.
        
        Args:
            user: User to notify
            title: Notification title
            message: Notification message
            priority: Notification priority
            context: Additional context data
            
        Returns:
            Notification ID
        """
        try:
            notification = NotificationMessage(
                notification_id=f"system_{user.user_id}_{int(datetime.utcnow().timestamp())}",
                user_id=user.user_id,
                notification_type=NotificationType.SYSTEM_NOTIFICATION,
                priority=priority,
                title=title,
                message=message,
                channels=self._get_user_preferences(user.user_id).system_notifications,
                context=context or {}
            )
            
            notification.blocks = self._create_system_notification_blocks(title, message, context)
            await self._queue_notification(notification)
            
            self.logger.info("System notification queued",
                           user_id=user.user_id,
                           priority=priority.value)
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send system notification", error=str(e))
            raise e
    
    async def send_single_trade_alert(
        self,
        manager_id: str,
        alert: 'RiskAlertConfig',
        trade: Trade,
        metrics: Dict[str, Any]
    ) -> str:
        """
        Send alert notification for a single trade matching criteria.
        
        Args:
            manager_id: Manager's Slack user ID
            alert: Alert configuration
            trade: Trade that triggered the alert
            metrics: Trade metrics (size, loss, VIX, etc.)
            
        Returns:
            Notification ID
        """
        try:
            from ui.risk_alert_widget import create_alert_triggered_message
            
            # Create alert message
            message = create_alert_triggered_message(alert, trade, metrics)
            
            notification = NotificationMessage(
                notification_id=f"alert_{alert.alert_id}_{trade.trade_id}_{int(datetime.utcnow().timestamp())}",
                user_id=manager_id,
                notification_type=NotificationType.HIGH_RISK_ALERT,
                priority=NotificationPriority.URGENT,
                title=f"🚨 Risk Alert: {alert.name or 'Trade Alert'}",
                message=f"Trade {trade.symbol} matches your risk alert criteria",
                blocks=message['blocks'],
                channels=[DeliveryChannel.SLACK_DM],
                context={
                    'alert_id': alert.alert_id,
                    'trade_id': trade.trade_id,
                    'metrics': metrics
                }
            )
            
            await self._queue_notification(notification)
            
            self.logger.info("Risk alert notification queued",
                           manager_id=manager_id,
                           alert_id=alert.alert_id,
                           trade_id=trade.trade_id)
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send risk alert notification", error=str(e))
            raise e
    
    async def send_risk_alert_summary(
        self,
        manager_id: str,
        alert: 'RiskAlertConfig',
        trades: List[Trade],
        show_all: bool = False
    ) -> str:
        """
        Send summary of multiple trades matching alert criteria.
        
        Args:
            manager_id: Manager's Slack user ID
            alert: Alert configuration
            trades: List of matching trades
            show_all: Whether to show all trades or just summary
            
        Returns:
            Notification ID
        """
        try:
            from ui.risk_alert_widget import create_existing_trades_summary
            
            # Create summary message
            message = create_existing_trades_summary(alert, trades, show_all)
            
            notification = NotificationMessage(
                notification_id=f"alert_summary_{alert.alert_id}_{int(datetime.utcnow().timestamp())}",
                user_id=manager_id,
                notification_type=NotificationType.PORTFOLIO_ALERT,
                priority=NotificationPriority.HIGH,
                title=f"🔍 Risk Alert Scan: {alert.name or 'Alert'}",
                message=f"Found {len(trades)} trades matching your risk alert criteria",
                blocks=message['blocks'],
                channels=[DeliveryChannel.SLACK_DM],
                context={
                    'alert_id': alert.alert_id,
                    'trade_count': len(trades)
                }
            )
            
            await self._queue_notification(notification)
            
            self.logger.info("Risk alert summary notification queued",
                           manager_id=manager_id,
                           alert_id=alert.alert_id,
                           trade_count=len(trades))
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send risk alert summary", error=str(e))
            raise e
    
    async def send_alert_confirmation(
        self,
        manager_id: str,
        alert: 'RiskAlertConfig'
    ) -> str:
        """
        Send confirmation after alert creation.
        
        Args:
            manager_id: Manager's Slack user ID
            alert: Created alert configuration
            
        Returns:
            Notification ID
        """
        try:
            from ui.risk_alert_widget import create_alert_confirmation_message
            
            message = create_alert_confirmation_message(alert)
            
            notification = NotificationMessage(
                notification_id=f"alert_confirm_{alert.alert_id}_{int(datetime.utcnow().timestamp())}",
                user_id=manager_id,
                notification_type=NotificationType.SYSTEM_NOTIFICATION,
                priority=NotificationPriority.NORMAL,
                title="✅ Risk Alert Created",
                message=f"Your risk alert has been created successfully",
                blocks=message['blocks'],
                channels=[DeliveryChannel.SLACK_DM],
                context={'alert_id': alert.alert_id}
            )
            
            await self._queue_notification(notification)
            
            self.logger.info("Alert confirmation notification queued",
                           manager_id=manager_id,
                           alert_id=alert.alert_id)
            
            return notification.notification_id
            
        except Exception as e:
            self.logger.error("Failed to send alert confirmation", error=str(e))
            raise e
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any]
    ) -> None:
        """
        Update user notification preferences.
        
        Args:
            user_id: User ID
            preferences: Updated preferences
        """
        try:
            current_prefs = self._get_user_preferences(user_id)
            
            # Update preferences
            for key, value in preferences.items():
                if hasattr(current_prefs, key):
                    if key in ['trade_confirmations', 'risk_alerts', 'portfolio_updates', 
                              'system_notifications', 'error_notifications']:
                        # Convert string values to DeliveryChannel enums
                        if isinstance(value, list):
                            setattr(current_prefs, key, [DeliveryChannel(ch) for ch in value])
                    else:
                        setattr(current_prefs, key, value)
            
            self.user_preferences[user_id] = current_prefs
            
            self.logger.info(f"User preferences updated for user {user_id}")
            
        except Exception as e:
            self.logger.error("Failed to update user preferences", error=str(e))
            raise e
    
    async def get_notification_history(
        self, 
        user_id: str, 
        limit: int = 50,
        notification_type: Optional[NotificationType] = None
    ) -> List[NotificationMessage]:
        """
        Get notification history for user.
        
        Args:
            user_id: User ID
            limit: Maximum number of notifications to return
            notification_type: Optional filter by notification type
            
        Returns:
            List of notification messages
        """
        try:
            user_history = self.notification_history.get(user_id, [])
            
            # Filter by type if specified
            if notification_type:
                user_history = [n for n in user_history if n.notification_type == notification_type]
            
            # Sort by creation time (newest first) and limit
            sorted_history = sorted(user_history, key=lambda n: n.created_at, reverse=True)
            return sorted_history[:limit]
            
        except Exception as e:
            self.logger.error("Failed to get notification history", error=str(e))
            return []
    
    async def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """
        Mark notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            user_history = self.notification_history.get(user_id, [])
            
            for notification in user_history:
                if notification.notification_id == notification_id:
                    notification.read_at = datetime.utcnow()
                    notification.status = NotificationStatus.READ
                    
                    self.logger.info("Notification marked as read",
                                   notification_id=notification_id,
                                   user_id=user_id)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to mark notification as read", error=str(e))
            return False
    
    def _get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get user notification preferences with defaults."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = NotificationPreferences(user_id=user_id)
        
        return self.user_preferences[user_id]
    
    def _determine_trade_priority(
        self, 
        trade: Trade, 
        risk_analysis: Optional[RiskAnalysis] = None
    ) -> NotificationPriority:
        """Determine notification priority for a trade."""
        if risk_analysis and risk_analysis.overall_risk_level == RiskLevel.CRITICAL:
            return NotificationPriority.CRITICAL
        elif risk_analysis and risk_analysis.overall_risk_level == RiskLevel.HIGH:
            return NotificationPriority.HIGH
        elif trade.is_high_value_trade() or trade.is_large_quantity_trade():
            return NotificationPriority.HIGH
        else:
            return NotificationPriority.NORMAL
    
    async def _queue_notification(self, notification: NotificationMessage) -> None:
        """Queue notification for delivery."""
        # Check rate limits
        if not self._check_rate_limits(notification.user_id):
            self.logger.warning(f"Rate limit exceeded for user {notification.user_id}")
            return
        
        # Check quiet hours
        if self._is_quiet_hours(notification.user_id) and notification.priority != NotificationPriority.URGENT:
            # Schedule for after quiet hours
            notification.scheduled_for = self._get_next_active_time(notification.user_id)
        
        # Set expiration time
        if notification.expires_at is None:
            expiry_hours = {
                NotificationPriority.URGENT: 1,
                NotificationPriority.CRITICAL: 4,
                NotificationPriority.HIGH: 12,
                NotificationPriority.NORMAL: 24,
                NotificationPriority.LOW: 48
            }
            
            hours = expiry_hours.get(notification.priority, 24)
            notification.expires_at = datetime.utcnow() + timedelta(hours=hours)
        
        # Add to queue
        self.pending_notifications.append(notification)
        
        # Add to history
        if notification.user_id not in self.notification_history:
            self.notification_history[notification.user_id] = []
        
        self.notification_history[notification.user_id].append(notification)
        
        # Keep history limited to last 100 notifications per user
        if len(self.notification_history[notification.user_id]) > 100:
            self.notification_history[notification.user_id] = self.notification_history[notification.user_id][-100:]
    
    def _check_rate_limits(self, user_id: str) -> bool:
        """Check if user has exceeded rate limits."""
        preferences = self._get_user_preferences(user_id)
        current_time = datetime.utcnow()
        
        # Check hourly limit
        hour_key = current_time.strftime("%Y-%m-%d-%H")
        if user_id not in self.hourly_counts:
            self.hourly_counts[user_id] = {}
        
        hourly_count = self.hourly_counts[user_id].get(hour_key, 0)
        if hourly_count >= preferences.max_notifications_per_hour:
            return False
        
        # Check daily limit
        date_key = current_time.strftime("%Y-%m-%d")
        if user_id not in self.daily_counts:
            self.daily_counts[user_id] = {}
        
        daily_count = self.daily_counts[user_id].get(date_key, 0)
        if daily_count >= preferences.max_notifications_per_day:
            return False
        
        # Update counts
        self.hourly_counts[user_id][hour_key] = hourly_count + 1
        self.daily_counts[user_id][date_key] = daily_count + 1
        
        return True
    
    def _is_quiet_hours(self, user_id: str) -> bool:
        """Check if current time is within user's quiet hours."""
        preferences = self._get_user_preferences(user_id)
        
        if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False
        
        # This is a simplified implementation
        # In production, would need proper timezone handling
        current_hour = datetime.utcnow().hour
        start_hour = int(preferences.quiet_hours_start.split(':')[0])
        end_hour = int(preferences.quiet_hours_end.split(':')[0])
        
        if start_hour <= end_hour:
            return start_hour <= current_hour <= end_hour
        else:  # Quiet hours span midnight
            return current_hour >= start_hour or current_hour <= end_hour
    
    def _get_next_active_time(self, user_id: str) -> datetime:
        """Get next active time after quiet hours."""
        preferences = self._get_user_preferences(user_id)
        
        if not preferences.quiet_hours_end:
            return datetime.utcnow()
        
        # Simplified implementation
        end_hour = int(preferences.quiet_hours_end.split(':')[0])
        next_active = datetime.utcnow().replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        if next_active <= datetime.utcnow():
            next_active += timedelta(days=1)
        
        return next_active
    
    def _create_trade_confirmation_blocks(
        self, 
        trade: Trade, 
        risk_analysis: Optional[RiskAnalysis],
        preferences: NotificationPreferences
    ) -> List[Dict[str, Any]]:
        """Create blocks for trade confirmation notification."""
        blocks = []
        
        # Trade summary
        trade_emoji = "🟢" if trade.trade_type == TradeType.BUY else "🔴"
        status_emoji = "✅" if trade.status == TradeStatus.EXECUTED else "⏳"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{trade_emoji} *Trade Executed* {status_emoji}\n*{trade.trade_type.value.upper()}* {format_number(trade.quantity)} shares of *{trade.symbol}*"
            }
        })
        
        # Trade details
        trade_value = abs(trade.quantity * trade.price)
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Price:*\n{format_money(trade.price)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total Value:*\n{format_money(trade_value)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Time:*\n{format_datetime(trade.timestamp)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Trade ID:*\n`{trade.trade_id[:8]}...`"
                }
            ]
        })
        
        # Risk analysis summary if available and user wants details
        if risk_analysis and preferences.include_risk_details:
            risk_emoji = {
                RiskLevel.LOW: "🟢",
                RiskLevel.MEDIUM: "🟡",
                RiskLevel.HIGH: "🟠",
                RiskLevel.CRITICAL: "🔴"
            }.get(risk_analysis.overall_risk_level, "❓")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Risk Assessment:* {risk_emoji} {risk_analysis.overall_risk_level.value.upper()}\n{risk_analysis.analysis_summary}"
                }
            })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 View Portfolio"
                    },
                    "action_id": "view_portfolio",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📋 Trade History"
                    },
                    "action_id": "view_trade_history"
                }
            ]
        })
        
        return blocks
    
    def _create_high_risk_alert_blocks(
        self, 
        trade: Trade, 
        risk_analysis: RiskAnalysis,
        user: User
    ) -> List[Dict[str, Any]]:
        """Create blocks for high-risk alert notification."""
        blocks = []
        
        # Alert header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🚨 *HIGH-RISK TRADE ALERT*\n\nThe following trade requires your attention:"
            }
        })
        
        # Trade details
        trade_type_text = "Buy" if trade.trade_type == TradeType.BUY else "Sell"
        trade_value = abs(trade.quantity * trade.price)
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Symbol:*\n{trade.symbol}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Action:*\n{trade_type_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Quantity:*\n{format_number(trade.quantity)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total Value:*\n{format_money(trade_value)}"
                }
            ]
        })
        
        # Risk analysis
        risk_score_bar = "█" * int(risk_analysis.overall_risk_score * 10) + "░" * (10 - int(risk_analysis.overall_risk_score * 10))
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Risk Level:* 🔴 {risk_analysis.overall_risk_level.value.upper()}\n*Risk Score:* {risk_analysis.overall_risk_score:.1%} `{risk_score_bar}`"
            }
        })
        
        # Key risk factors
        if risk_analysis.risk_factors:
            high_risk_factors = [rf for rf in risk_analysis.risk_factors if rf.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]][:3]
            if high_risk_factors:
                risk_text = "\n".join([f"• *{rf.category.value.title()}:* {rf.description}" for rf in high_risk_factors])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Key Risk Factors:*\n{risk_text}"
                    }
                })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "⚠️ Review Trade"
                    },
                    "action_id": f"review_trade_{trade.trade_id}",
                    "style": "danger"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Full Analysis"
                    },
                    "action_id": f"full_analysis_{trade.trade_id}"
                }
            ]
        })
        
        return blocks
    
    def _create_portfolio_manager_alert_blocks(
        self, 
        trade: Trade, 
        risk_analysis: RiskAnalysis,
        trader: User
    ) -> List[Dict[str, Any]]:
        """Create blocks for portfolio manager alert notification."""
        blocks = []
        
        # Alert header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🚨 *HIGH-RISK TRADE BY TEAM MEMBER*\n\n*{trader.profile.display_name}* ({trader.role.value.replace('_', ' ').title()}) is attempting a high-risk trade:"
            }
        })
        
        # Trade summary
        trade_type_text = "Buy" if trade.trade_type == TradeType.BUY else "Sell"
        trade_value = abs(trade.quantity * trade.price)
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Symbol:*\n{trade.symbol}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Action:*\n{trade_type_text} {format_number(trade.quantity)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Value:*\n{format_money(trade_value)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Risk Level:*\n🔴 {risk_analysis.overall_risk_level.value.upper()}"
                }
            ]
        })
        
        # Risk summary
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Risk Summary:*\n{risk_analysis.analysis_summary}"
            }
        })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "👀 Monitor"
                    },
                    "action_id": f"monitor_trade_{trade.trade_id}",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🛑 Intervene"
                    },
                    "action_id": f"intervene_trade_{trade.trade_id}",
                    "style": "danger"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📞 Contact Trader"
                    },
                    "action_id": f"contact_trader_{trader.user_id}"
                }
            ]
        })
        
        return blocks
    
    def _create_portfolio_alert_blocks(
        self, 
        alert_type: str, 
        message: str,
        portfolio: Optional[Portfolio],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create blocks for portfolio alert notification."""
        blocks = []
        
        # Alert header with appropriate emoji
        alert_emojis = {
            'concentration_risk': '⚠️',
            'large_loss': '📉',
            'margin_call': '🚨',
            'rebalance_needed': '⚖️',
            'performance_milestone': '🎯'
        }
        
        emoji = alert_emojis.get(alert_type, '📊')
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *Portfolio Alert*\n{message}"
            }
        })
        
        # Portfolio summary if available
        if portfolio:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Portfolio Value:*\n{format_money(portfolio.total_value)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total P&L:*\n{format_money(portfolio.total_pnl)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Positions:*\n{len(portfolio.get_active_positions())}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Cash:*\n{format_money(portfolio.cash_balance)}"
                    }
                ]
            })
        
        # Context-specific information
        if context:
            if 'recommendations' in context:
                rec_text = "\n".join([f"• {rec}" for rec in context['recommendations']])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommendations:*\n{rec_text}"
                    }
                })
        
        # Action button
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 View Portfolio"
                    },
                    "action_id": "view_portfolio",
                    "style": "primary"
                }
            ]
        })
        
        return blocks
    
    def _create_error_notification_blocks(
        self, 
        error_type: str, 
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create blocks for error notification."""
        blocks = []
        
        # Error header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ *Error Occurred*\n*Type:* {error_type.replace('_', ' ').title()}\n*Message:* {error_message}"
            }
        })
        
        # Context information if available
        if context:
            if 'trade_id' in context:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Related Trade:* `{context['trade_id']}`"
                    }
                })
            
            if 'timestamp' in context:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Occurred at: {context['timestamp']}"
                        }
                    ]
                })
        
        # Action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔄 Retry"
                    },
                    "action_id": "retry_action",
                    "style": "primary"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🆘 Get Help"
                    },
                    "action_id": "get_help"
                }
            ]
        })
        
        return blocks
    
    def _create_system_notification_blocks(
        self, 
        title: str, 
        message: str,
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create blocks for system notification."""
        blocks = []
        
        # System notification header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔔 *{title}*\n{message}"
            }
        })
        
        # Additional context if available
        if context and 'details' in context:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Details:*\n{context['details']}"
                }
            })
        
        return blocks
    
    # Template methods for different notification types
    def _create_trade_confirmation_template(self, **kwargs) -> Dict[str, Any]:
        """Template for trade confirmation notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.NORMAL],
            "title": "Trade Confirmation",
            "fallback": "Your trade has been executed."
        }
    
    def _create_trade_execution_template(self, **kwargs) -> Dict[str, Any]:
        """Template for trade execution notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.NORMAL],
            "title": "Trade Executed",
            "fallback": "Trade execution notification."
        }
    
    def _create_high_risk_alert_template(self, **kwargs) -> Dict[str, Any]:
        """Template for high-risk alert notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.HIGH],
            "title": "High-Risk Trade Alert",
            "fallback": "High-risk trade requires attention."
        }
    
    def _create_risk_analysis_template(self, **kwargs) -> Dict[str, Any]:
        """Template for risk analysis notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.NORMAL],
            "title": "Risk Analysis Complete",
            "fallback": "Risk analysis has been completed."
        }
    
    def _create_portfolio_alert_template(self, **kwargs) -> Dict[str, Any]:
        """Template for portfolio alert notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.HIGH],
            "title": "Portfolio Alert",
            "fallback": "Portfolio alert notification."
        }
    
    def _create_error_notification_template(self, **kwargs) -> Dict[str, Any]:
        """Template for error notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.HIGH],
            "title": "Error Notification",
            "fallback": "An error has occurred."
        }
    
    def _create_approval_request_template(self, **kwargs) -> Dict[str, Any]:
        """Template for approval request notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.HIGH],
            "title": "Approval Required",
            "fallback": "Your approval is required."
        }
    
    def _create_compliance_alert_template(self, **kwargs) -> Dict[str, Any]:
        """Template for compliance alert notifications."""
        return {
            "color": self.color_schemes[NotificationPriority.CRITICAL],
            "title": "Compliance Alert",
            "fallback": "Compliance alert notification."
        }