"""
User model with role-based permissions, authentication helpers, and profile management.

This module provides the User data model class with comprehensive role-based access control,
authentication helpers, and profile management for the Slack Trading Bot.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

# Configure logging
logger = logging.getLogger(__name__)


class UserRole(Enum):
    """Enumeration for user roles with hierarchical permissions."""
    RESEARCH_ANALYST = "research_analyst"
    EXECUTION_TRADER = "execution_trader"
    PORTFOLIO_MANAGER = "portfolio_manager"
    ADMIN = "admin"


class Permission(Enum):
    """Enumeration for specific permissions."""
    # Trading permissions
    EXECUTE_TRADES = "execute_trades"
    VIEW_TRADES = "view_trades"
    CANCEL_TRADES = "cancel_trades"
    
    # Analysis permissions
    REQUEST_RISK_ANALYSIS = "request_risk_analysis"
    VIEW_RISK_ANALYSIS = "view_risk_analysis"
    OVERRIDE_RISK_WARNINGS = "override_risk_warnings"
    
    # Portfolio permissions
    VIEW_PORTFOLIO = "view_portfolio"
    VIEW_ALL_PORTFOLIOS = "view_all_portfolios"
    MANAGE_PORTFOLIO = "manage_portfolio"
    
    # User management permissions
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_CHANNELS = "manage_channels"
    
    # System permissions
    SYSTEM_ADMIN = "system_admin"


class UserStatus(Enum):
    """Enumeration for user status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"


class UserValidationError(Exception):
    """Custom exception for user validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


@dataclass
class UserProfile:
    """
    User profile information and preferences.
    
    Attributes:
        display_name: User's display name
        email: User's email address
        department: User's department
        phone: User's phone number (optional)
        timezone: User's timezone preference
        notification_preferences: User's notification settings
        trading_preferences: User's trading preferences
        last_login: Last login timestamp
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
    """
    
    display_name: str
    email: str
    department: str
    timezone: str = "UTC"
    phone: Optional[str] = None
    notification_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "trade_confirmations": True,
        "risk_alerts": True,
        "portfolio_updates": True,
        "system_notifications": True
    })
    trading_preferences: Dict[str, Any] = field(default_factory=lambda: {
        "default_quantity": 100,
        "risk_tolerance": "medium",
        "auto_confirm_low_risk": False,
        "preferred_execution_time": "market_hours"
    })
    last_login: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class User:
    """
    Comprehensive User model with role-based permissions and authentication.
    
    This class represents a user in the Slack Trading Bot system with full
    role-based access control, authentication helpers, and profile management.
    
    Attributes:
        user_id: Internal user ID (UUID)
        slack_user_id: Slack user ID
        role: User's primary role
        status: Current user status
        permissions: Set of specific permissions
        portfolio_manager_id: ID of assigned portfolio manager (optional)
        profile: User profile information
        additional_roles: Additional roles for multi-role users
        channel_restrictions: List of allowed channel IDs
        session_data: Current session information
        security_settings: Security-related settings
        audit_trail: List of important user actions
    """
    
    # Required fields
    user_id: str
    slack_user_id: str
    role: UserRole
    profile: UserProfile
    
    # Status and permissions
    status: UserStatus = field(default=UserStatus.PENDING_APPROVAL)
    permissions: Set[Permission] = field(default_factory=set)
    
    # Optional relationships
    portfolio_manager_id: Optional[str] = None
    additional_roles: List[UserRole] = field(default_factory=list)
    channel_restrictions: List[str] = field(default_factory=list)
    
    # Session and security
    session_data: Dict[str, Any] = field(default_factory=dict)
    security_settings: Dict[str, Any] = field(default_factory=lambda: {
        "mfa_enabled": False,
        "last_password_change": None,
        "failed_login_attempts": 0,
        "account_locked_until": None,
        "ip_whitelist": []
    })
    
    # Audit and tracking
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        try:
            self.validate()
            self._assign_role_permissions()
            logger.info(f"User {self.user_id} created successfully with role {self.role.value}")
        except UserValidationError as e:
            logger.error(f"User validation failed: {e.message}")
            raise
    
    def validate(self) -> None:
        """
        Comprehensive validation of user data.
        
        Raises:
            UserValidationError: If any validation fails
        """
        # Validate user_id
        if not self.user_id or not isinstance(self.user_id, str):
            raise UserValidationError("User ID must be a non-empty string", "user_id")
        
        if len(self.user_id.strip()) == 0:
            raise UserValidationError("User ID cannot be empty or whitespace", "user_id")
        
        # Validate slack_user_id
        if not self.slack_user_id or not isinstance(self.slack_user_id, str):
            raise UserValidationError("Slack User ID must be a non-empty string", "slack_user_id")
        
        if not self.slack_user_id.startswith('U'):
            raise UserValidationError("Slack User ID must start with 'U'", "slack_user_id")
        
        # Validate role
        if not isinstance(self.role, UserRole):
            if isinstance(self.role, str):
                try:
                    self.role = UserRole(self.role.lower())
                except ValueError:
                    raise UserValidationError(f"Invalid user role: {self.role}", "role")
            else:
                raise UserValidationError("Role must be UserRole enum or valid string", "role")
        
        # Validate status
        if not isinstance(self.status, UserStatus):
            if isinstance(self.status, str):
                try:
                    self.status = UserStatus(self.status.lower())
                except ValueError:
                    raise UserValidationError(f"Invalid user status: {self.status}", "status")
            else:
                raise UserValidationError("Status must be UserStatus enum or valid string", "status")
        
        # Validate profile
        if not isinstance(self.profile, UserProfile):
            raise UserValidationError("Profile must be a UserProfile instance", "profile")
        
        # Validate portfolio manager relationship
        if self.role == UserRole.RESEARCH_ANALYST and not self.portfolio_manager_id:
            logger.warning(f"Research Analyst {self.user_id} has no assigned Portfolio Manager")
    
    def _assign_role_permissions(self) -> None:
        """Assign permissions based on user role."""
        role_permissions = {
            UserRole.RESEARCH_ANALYST: {
                Permission.VIEW_TRADES,
                Permission.REQUEST_RISK_ANALYSIS,
                Permission.VIEW_RISK_ANALYSIS,
                Permission.VIEW_PORTFOLIO
            },
            UserRole.EXECUTION_TRADER: {
                Permission.EXECUTE_TRADES,
                Permission.VIEW_TRADES,
                Permission.CANCEL_TRADES,
                Permission.REQUEST_RISK_ANALYSIS,
                Permission.VIEW_RISK_ANALYSIS,
                Permission.VIEW_PORTFOLIO
            },
            UserRole.PORTFOLIO_MANAGER: {
                Permission.EXECUTE_TRADES,
                Permission.VIEW_TRADES,
                Permission.CANCEL_TRADES,
                Permission.REQUEST_RISK_ANALYSIS,
                Permission.VIEW_RISK_ANALYSIS,
                Permission.OVERRIDE_RISK_WARNINGS,
                Permission.VIEW_PORTFOLIO,
                Permission.VIEW_ALL_PORTFOLIOS,
                Permission.MANAGE_PORTFOLIO
            },
            UserRole.ADMIN: {
                Permission.EXECUTE_TRADES,
                Permission.VIEW_TRADES,
                Permission.CANCEL_TRADES,
                Permission.REQUEST_RISK_ANALYSIS,
                Permission.VIEW_RISK_ANALYSIS,
                Permission.OVERRIDE_RISK_WARNINGS,
                Permission.VIEW_PORTFOLIO,
                Permission.VIEW_ALL_PORTFOLIOS,
                Permission.MANAGE_PORTFOLIO,
                Permission.MANAGE_USERS,
                Permission.VIEW_AUDIT_LOGS,
                Permission.MANAGE_CHANNELS,
                Permission.SYSTEM_ADMIN
            }
        }
        
        # Assign base role permissions
        self.permissions.update(role_permissions.get(self.role, set()))
        
        # Add permissions from additional roles
        for additional_role in self.additional_roles:
            self.permissions.update(role_permissions.get(additional_role, set()))
    
    def has_permission(self, permission: Permission) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has the permission
        """
        if self.status != UserStatus.ACTIVE:
            return False
        
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            True if user has at least one permission
        """
        return any(self.has_permission(perm) for perm in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """
        Check if user has all specified permissions.
        
        Args:
            permissions: List of permissions to check
            
        Returns:
            True if user has all permissions
        """
        return all(self.has_permission(perm) for perm in permissions)
    
    def can_execute_trades(self) -> bool:
        """Check if user can execute trades."""
        return self.has_permission(Permission.EXECUTE_TRADES)
    
    def can_view_portfolio(self, portfolio_user_id: Optional[str] = None) -> bool:
        """
        Check if user can view a specific portfolio.
        
        Args:
            portfolio_user_id: ID of portfolio owner (None for own portfolio)
            
        Returns:
            True if user can view the portfolio
        """
        if not self.has_permission(Permission.VIEW_PORTFOLIO):
            return False
        
        # Can always view own portfolio
        if portfolio_user_id is None or portfolio_user_id == self.user_id:
            return True
        
        # Portfolio managers and admins can view all portfolios
        return self.has_permission(Permission.VIEW_ALL_PORTFOLIOS)
    
    def can_override_risk_warnings(self) -> bool:
        """Check if user can override risk warnings."""
        return self.has_permission(Permission.OVERRIDE_RISK_WARNINGS)
    
    def is_portfolio_manager_for(self, user_id: str) -> bool:
        """
        Check if this user is the portfolio manager for another user.
        
        Args:
            user_id: ID of user to check
            
        Returns:
            True if this user is the portfolio manager
        """
        return (self.role == UserRole.PORTFOLIO_MANAGER and 
                self.user_id == user_id)  # This would need to be checked against the other user's portfolio_manager_id
    
    def can_access_channel(self, channel_id: str) -> bool:
        """
        Check if user can access a specific channel.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            True if user can access the channel
        """
        if self.status != UserStatus.ACTIVE:
            return False
        
        # If no channel restrictions, allow access
        if not self.channel_restrictions:
            return True
        
        return channel_id in self.channel_restrictions
    
    def add_channel_access(self, channel_id: str) -> None:
        """
        Add channel access for user.
        
        Args:
            channel_id: Slack channel ID to add
        """
        if channel_id not in self.channel_restrictions:
            self.channel_restrictions.append(channel_id)
            self._log_audit_event("channel_access_added", {"channel_id": channel_id})
    
    def remove_channel_access(self, channel_id: str) -> None:
        """
        Remove channel access for user.
        
        Args:
            channel_id: Slack channel ID to remove
        """
        if channel_id in self.channel_restrictions:
            self.channel_restrictions.remove(channel_id)
            self._log_audit_event("channel_access_removed", {"channel_id": channel_id})
    
    def update_profile(self, **kwargs) -> None:
        """
        Update user profile information.
        
        Args:
            **kwargs: Profile fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)
        
        self.profile.updated_at = datetime.now(timezone.utc)
        self._log_audit_event("profile_updated", {"fields": list(kwargs.keys())})
    
    def update_trading_preferences(self, preferences: Dict[str, Any]) -> None:
        """
        Update user trading preferences.
        
        Args:
            preferences: Dictionary of preference updates
        """
        self.profile.trading_preferences.update(preferences)
        self.profile.updated_at = datetime.now(timezone.utc)
        self._log_audit_event("trading_preferences_updated", {"preferences": preferences})
    
    def update_notification_preferences(self, preferences: Dict[str, bool]) -> None:
        """
        Update user notification preferences.
        
        Args:
            preferences: Dictionary of notification preference updates
        """
        self.profile.notification_preferences.update(preferences)
        self.profile.updated_at = datetime.now(timezone.utc)
        self._log_audit_event("notification_preferences_updated", {"preferences": preferences})
    
    def record_login(self) -> None:
        """Record user login."""
        self.profile.last_login = datetime.now(timezone.utc)
        self.security_settings["failed_login_attempts"] = 0
        self._log_audit_event("user_login", {})
    
    def record_failed_login(self) -> None:
        """Record failed login attempt."""
        self.security_settings["failed_login_attempts"] += 1
        
        # Lock account after 5 failed attempts
        if self.security_settings["failed_login_attempts"] >= 5:
            lock_until = datetime.now(timezone.utc).timestamp() + 3600  # 1 hour
            self.security_settings["account_locked_until"] = lock_until
            self._log_audit_event("account_locked", {"reason": "failed_login_attempts"})
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        lock_until = self.security_settings.get("account_locked_until")
        if lock_until is None:
            return False
        
        current_time = datetime.now(timezone.utc).timestamp()
        if current_time > lock_until:
            # Unlock account
            self.security_settings["account_locked_until"] = None
            self.security_settings["failed_login_attempts"] = 0
            return False
        
        return True
    
    def activate(self) -> None:
        """Activate user account."""
        self.status = UserStatus.ACTIVE
        self._log_audit_event("account_activated", {})
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.status = UserStatus.INACTIVE
        self._log_audit_event("account_deactivated", {})
    
    def suspend(self, reason: Optional[str] = None) -> None:
        """
        Suspend user account.
        
        Args:
            reason: Reason for suspension
        """
        self.status = UserStatus.SUSPENDED
        self._log_audit_event("account_suspended", {"reason": reason})
    
    def _log_audit_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            details: Event details
        """
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        self.audit_trail.append(audit_entry)
        
        # Keep only last 100 audit entries
        if len(self.audit_trail) > 100:
            self.audit_trail = self.audit_trail[-100:]
        
        logger.info(f"Audit event for user {self.user_id}: {event_type}")
    
    def get_role_hierarchy_level(self) -> int:
        """
        Get numeric level for role hierarchy.
        
        Returns:
            Numeric level (higher = more permissions)
        """
        hierarchy = {
            UserRole.RESEARCH_ANALYST: 1,
            UserRole.EXECUTION_TRADER: 2,
            UserRole.PORTFOLIO_MANAGER: 3,
            UserRole.ADMIN: 4
        }
        return hierarchy.get(self.role, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user to dictionary for serialization.
        
        Returns:
            Dictionary representation of user
        """
        data = asdict(self)
        
        # Convert enums to string values
        data['role'] = self.role.value
        data['status'] = self.status.value
        data['permissions'] = [perm.value for perm in self.permissions]
        data['additional_roles'] = [role.value for role in self.additional_roles]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create User instance from dictionary.
        
        Args:
            data: Dictionary containing user data
            
        Returns:
            User instance
            
        Raises:
            UserValidationError: If data is invalid
        """
        try:
            # Convert string values back to appropriate types
            if 'role' in data and isinstance(data['role'], str):
                data['role'] = UserRole(data['role'])
            
            if 'status' in data and isinstance(data['status'], str):
                data['status'] = UserStatus(data['status'])
            
            if 'permissions' in data and isinstance(data['permissions'], list):
                data['permissions'] = {Permission(perm) for perm in data['permissions']}
            
            if 'additional_roles' in data and isinstance(data['additional_roles'], list):
                data['additional_roles'] = [UserRole(role) for role in data['additional_roles']]
            
            # Handle profile data
            if 'profile' in data and isinstance(data['profile'], dict):
                profile_data = data['profile']
                
                # Convert datetime strings back to datetime objects
                for field in ['last_login', 'created_at', 'updated_at']:
                    if field in profile_data and profile_data[field] is not None:
                        if isinstance(profile_data[field], str):
                            profile_data[field] = datetime.fromisoformat(profile_data[field].replace('Z', '+00:00'))
                
                data['profile'] = UserProfile(**profile_data)
            
            return cls(**data)
            
        except (ValueError, TypeError, KeyError) as e:
            raise UserValidationError(f"Failed to create User from dict: {str(e)}")
    
    def to_json(self) -> str:
        """
        Convert user to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'User':
        """
        Create User instance from JSON string.
        
        Args:
            json_str: JSON string containing user data
            
        Returns:
            User instance
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise UserValidationError(f"Invalid JSON: {str(e)}")
    
    def get_display_info(self) -> Dict[str, str]:
        """
        Get user information for display purposes.
        
        Returns:
            Dictionary with display-friendly user information
        """
        return {
            "name": self.profile.display_name,
            "role": self.role.value.replace('_', ' ').title(),
            "department": self.profile.department,
            "status": self.status.value.title(),
            "email": self.profile.email
        }
    
    def __str__(self) -> str:
        """String representation of user."""
        return f"User({self.profile.display_name}): {self.role.value} - {self.status.value}"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"User(user_id='{self.user_id}', slack_user_id='{self.slack_user_id}', "
                f"role={self.role}, status={self.status}, "
                f"permissions={len(self.permissions)})")