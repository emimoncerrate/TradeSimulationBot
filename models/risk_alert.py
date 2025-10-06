"""
Risk Alert model for manager-configured trade monitoring and notifications.

This module provides the data model for risk alerts that allow Portfolio Managers
to set criteria for trade monitoring. When trades match the configured criteria
(trade size, loss percentage, and VIX level), managers are notified automatically.
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertStatus(Enum):
    """Status of a risk alert."""
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"
    DELETED = "deleted"


class AlertTriggerType(Enum):
    """Type of alert trigger."""
    EXISTING_TRADES = "existing_trades"  # Scan existing trades
    NEW_TRADES = "new_trades"  # Monitor new trades
    BOTH = "both"


class RiskAlertValidationError(Exception):
    """Exception raised for risk alert validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


@dataclass
class RiskAlertConfig:
    """
    Risk alert configuration set by Portfolio Managers.
    
    This model represents a risk alert that monitors trades based on configurable
    criteria: trade size (in dollars), loss percentage, and VIX volatility level.
    When trades match these criteria, the manager is notified.
    
    Attributes:
        alert_id: Unique identifier for the alert
        manager_id: Slack user ID of the Portfolio Manager
        trade_size_threshold: Minimum trade size in dollars to trigger alert
        loss_percent_threshold: Minimum loss percentage to trigger alert
        vix_threshold: Minimum VIX level to trigger alert
        status: Current status of the alert (active/paused/expired)
        created_at: When the alert was created
        updated_at: When the alert was last updated
        expires_at: Optional expiration date for the alert
        name: Optional descriptive name for the alert
        notes: Optional notes about the alert
        notify_on_existing: Whether to scan existing trades when alert is created
        notify_on_new: Whether to monitor new trades
        notification_channel: Where to send notifications (DM or channel ID)
        trigger_count: Number of times this alert has been triggered
        last_triggered_at: Last time this alert was triggered
    """
    
    # Required fields
    manager_id: str
    trade_size_threshold: Decimal
    loss_percent_threshold: Decimal
    vix_threshold: Decimal
    
    # Auto-generated fields
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: AlertStatus = field(default=AlertStatus.ACTIVE)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Optional configuration
    expires_at: Optional[datetime] = None
    name: Optional[str] = None
    notes: Optional[str] = None
    
    # Notification settings
    notify_on_existing: bool = True
    notify_on_new: bool = True
    notification_channel: str = "dm"  # "dm" or channel_id
    
    # Tracking
    trigger_count: int = 0
    last_triggered_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate alert configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """
        Validate the risk alert configuration.
        
        Raises:
            RiskAlertValidationError: If validation fails
        """
        # Validate manager ID
        if not self.manager_id or not isinstance(self.manager_id, str):
            raise RiskAlertValidationError("Manager ID is required", "manager_id")
        
        # Validate trade size threshold
        if self.trade_size_threshold <= 0:
            raise RiskAlertValidationError(
                "Trade size threshold must be positive",
                "trade_size_threshold"
            )
        
        if self.trade_size_threshold > Decimal('100000000'):  # 100M limit
            raise RiskAlertValidationError(
                "Trade size threshold cannot exceed $100M",
                "trade_size_threshold"
            )
        
        # Validate loss percent threshold
        if self.loss_percent_threshold < 0:
            raise RiskAlertValidationError(
                "Loss percentage threshold must be non-negative",
                "loss_percent_threshold"
            )
        
        if self.loss_percent_threshold > 100:
            raise RiskAlertValidationError(
                "Loss percentage threshold cannot exceed 100%",
                "loss_percent_threshold"
            )
        
        # Validate VIX threshold
        if self.vix_threshold < 0:
            raise RiskAlertValidationError(
                "VIX threshold must be non-negative",
                "vix_threshold"
            )
        
        if self.vix_threshold > 100:
            raise RiskAlertValidationError(
                "VIX threshold cannot exceed 100",
                "vix_threshold"
            )
        
        # Validate notification settings
        if not self.notify_on_existing and not self.notify_on_new:
            raise RiskAlertValidationError(
                "Alert must monitor existing trades, new trades, or both",
                "notification_settings"
            )
        
        # Validate expiration
        if self.expires_at and self.expires_at < self.created_at:
            raise RiskAlertValidationError(
                "Expiration date must be in the future",
                "expires_at"
            )
    
    def is_active(self) -> bool:
        """Check if alert is currently active."""
        if self.status != AlertStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if alert has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def pause(self) -> None:
        """Pause the alert."""
        if self.status == AlertStatus.ACTIVE:
            self.status = AlertStatus.PAUSED
            self.updated_at = datetime.now(timezone.utc)
            logger.info(f"Alert {self.alert_id} paused")
    
    def resume(self) -> None:
        """Resume a paused alert."""
        if self.status == AlertStatus.PAUSED:
            self.status = AlertStatus.ACTIVE
            self.updated_at = datetime.now(timezone.utc)
            logger.info(f"Alert {self.alert_id} resumed")
    
    def expire(self) -> None:
        """Mark alert as expired."""
        self.status = AlertStatus.EXPIRED
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Alert {self.alert_id} expired")
    
    def delete(self) -> None:
        """Soft delete the alert."""
        self.status = AlertStatus.DELETED
        self.updated_at = datetime.now(timezone.utc)
        logger.info(f"Alert {self.alert_id} deleted")
    
    def record_trigger(self) -> None:
        """Record that this alert was triggered."""
        self.trigger_count += 1
        self.last_triggered_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def matches_criteria(self, trade_size: Decimal, loss_percent: Decimal, 
                        vix_level: Decimal) -> bool:
        """
        Check if given metrics match this alert's criteria.
        
        Args:
            trade_size: Trade size in dollars
            loss_percent: Loss percentage
            vix_level: Current VIX level
            
        Returns:
            True if all criteria are met
        """
        return (
            trade_size >= self.trade_size_threshold and
            abs(loss_percent) >= self.loss_percent_threshold and
            vix_level >= self.vix_threshold
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert alert to dictionary for database storage.
        
        Returns:
            Dictionary representation of the alert
        """
        return {
            'alert_id': self.alert_id,
            'manager_id': self.manager_id,
            'trade_size_threshold': str(self.trade_size_threshold),
            'loss_percent_threshold': str(self.loss_percent_threshold),
            'vix_threshold': str(self.vix_threshold),
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'name': self.name,
            'notes': self.notes,
            'notify_on_existing': self.notify_on_existing,
            'notify_on_new': self.notify_on_new,
            'notification_channel': self.notification_channel,
            'trigger_count': self.trigger_count,
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskAlertConfig':
        """
        Create alert from dictionary (e.g., from database).
        
        Args:
            data: Dictionary containing alert data
            
        Returns:
            RiskAlertConfig instance
        """
        return cls(
            alert_id=data['alert_id'],
            manager_id=data['manager_id'],
            trade_size_threshold=Decimal(data['trade_size_threshold']),
            loss_percent_threshold=Decimal(data['loss_percent_threshold']),
            vix_threshold=Decimal(data['vix_threshold']),
            status=AlertStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            name=data.get('name'),
            notes=data.get('notes'),
            notify_on_existing=data.get('notify_on_existing', True),
            notify_on_new=data.get('notify_on_new', True),
            notification_channel=data.get('notification_channel', 'dm'),
            trigger_count=data.get('trigger_count', 0),
            last_triggered_at=datetime.fromisoformat(data['last_triggered_at']) if data.get('last_triggered_at') else None
        )
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of the alert configuration.
        
        Returns:
            Summary string
        """
        name_part = f"'{self.name}'" if self.name else f"Alert {self.alert_id[:8]}"
        return (
            f"{name_part}: "
            f"Trade ≥ ${self.trade_size_threshold:,.0f}, "
            f"Loss ≥ {self.loss_percent_threshold}%, "
            f"VIX ≥ {self.vix_threshold}"
        )


@dataclass
class AlertTriggerEvent:
    """
    Record of an alert being triggered by a matching trade.
    
    This model tracks when an alert is triggered, which trade triggered it,
    and the metrics at the time of the trigger.
    """
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    alert_id: str = None
    trade_id: str = None
    manager_id: str = None
    
    # Metrics at time of trigger
    trade_size: Decimal = None
    loss_percent: Decimal = None
    vix_level: Decimal = None
    
    # Timing
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trigger event to dictionary."""
        return {
            'event_id': self.event_id,
            'alert_id': self.alert_id,
            'trade_id': self.trade_id,
            'manager_id': self.manager_id,
            'trade_size': str(self.trade_size) if self.trade_size else None,
            'loss_percent': str(self.loss_percent) if self.loss_percent else None,
            'vix_level': str(self.vix_level) if self.vix_level else None,
            'triggered_at': self.triggered_at.isoformat(),
            'notification_sent': self.notification_sent,
            'notification_sent_at': self.notification_sent_at.isoformat() if self.notification_sent_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertTriggerEvent':
        """Create trigger event from dictionary."""
        return cls(
            event_id=data['event_id'],
            alert_id=data['alert_id'],
            trade_id=data['trade_id'],
            manager_id=data['manager_id'],
            trade_size=Decimal(data['trade_size']) if data.get('trade_size') else None,
            loss_percent=Decimal(data['loss_percent']) if data.get('loss_percent') else None,
            vix_level=Decimal(data['vix_level']) if data.get('vix_level') else None,
            triggered_at=datetime.fromisoformat(data['triggered_at']),
            notification_sent=data.get('notification_sent', False),
            notification_sent_at=datetime.fromisoformat(data['notification_sent_at']) if data.get('notification_sent_at') else None
        )

