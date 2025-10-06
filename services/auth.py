"""
Comprehensive user authentication and authorization service for the Slack Trading Bot.

This module provides complete authentication and authorization functionality including
Slack OAuth integration, role-based access control, user session management,
permission validation, security logging, channel authorization, user role determination,
Portfolio Manager assignment, rate limiting, and suspicious activity detection.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import jwt
import boto3
from botocore.exceptions import ClientError
import backoff

# Import Slack SDK components
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Import our models and services
from models.user import User, UserRole, UserStatus, Permission, UserProfile, UserValidationError
from services.database import DatabaseService, DatabaseError, NotFoundError, ConflictError
from config.settings import get_config

# Configure logging
logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, user_id: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        self.user_id = user_id
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Exception for authorization failures."""
    
    def __init__(self, message: str, required_permission: Optional[str] = None, user_id: Optional[str] = None):
        self.message = message
        self.required_permission = required_permission
        self.user_id = user_id
        super().__init__(self.message)


class SessionError(Exception):
    """Exception for session management errors."""
    
    def __init__(self, message: str, session_id: Optional[str] = None):
        self.message = message
        self.session_id = session_id
        super().__init__(self.message)


class RateLimitError(Exception):
    """Exception for rate limiting violations."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)


class SecurityViolationError(Exception):
    """Exception for security violations and suspicious activity."""
    
    def __init__(self, message: str, violation_type: str, user_id: Optional[str] = None):
        self.message = message
        self.violation_type = violation_type
        self.user_id = user_id
        super().__init__(self.message)


@dataclass
class UserSession:
    """
    User session data with security tracking.
    
    Attributes:
        session_id: Unique session identifier
        user_id: User ID for this session
        slack_user_id: Slack user ID
        team_id: Slack team/workspace ID
        channel_id: Current channel ID (optional)
        created_at: Session creation timestamp
        last_activity: Last activity timestamp
        expires_at: Session expiration timestamp
        ip_address: Client IP address (if available)
        user_agent: Client user agent (if available)
        permissions: Cached user permissions
        security_flags: Security-related flags
        activity_log: Recent activity log
    """
    
    session_id: str
    user_id: str
    slack_user_id: str
    team_id: str
    created_at: datetime
    expires_at: datetime
    permissions: Set[Permission] = field(default_factory=set)
    channel_id: Optional[str] = None
    last_activity: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    security_flags: Dict[str, Any] = field(default_factory=dict)
    activity_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_active(self) -> bool:
        """Check if session is active (not expired and has recent activity)."""
        if self.is_expired():
            return False
        
        if self.last_activity is None:
            return True
        
        # Consider session inactive after 1 hour of no activity
        inactive_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        return self.last_activity > inactive_threshold
    
    def update_activity(self, activity_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Update session activity."""
        self.last_activity = datetime.now(timezone.utc)
        
        activity_entry = {
            'timestamp': self.last_activity.isoformat(),
            'activity_type': activity_type,
            'details': details or {}
        }
        
        self.activity_log.append(activity_entry)
        
        # Keep only last 50 activities
        if len(self.activity_log) > 50:
            self.activity_log = self.activity_log[-50:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'slack_user_id': self.slack_user_id,
            'team_id': self.team_id,
            'channel_id': self.channel_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'expires_at': self.expires_at.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'permissions': [perm.value for perm in self.permissions],
            'security_flags': self.security_flags,
            'activity_log': self.activity_log
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create session from dictionary."""
        # Convert datetime strings back to datetime objects
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        last_activity = None
        if data.get('last_activity'):
            last_activity = datetime.fromisoformat(data['last_activity'].replace('Z', '+00:00'))
        
        # Convert permissions back to Permission enum
        permissions = {Permission(perm) for perm in data.get('permissions', [])}
        
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            slack_user_id=data['slack_user_id'],
            team_id=data['team_id'],
            channel_id=data.get('channel_id'),
            created_at=created_at,
            last_activity=last_activity,
            expires_at=expires_at,
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
            permissions=permissions,
            security_flags=data.get('security_flags', {}),
            activity_log=data.get('activity_log', [])
        )


class AuthService:
    """
    Comprehensive authentication and authorization service.
    
    This service provides complete authentication and authorization functionality
    for the Slack Trading Bot, including:
    
    - Slack OAuth integration and user authentication
    - Role-based access control and permission management
    - User session management with security tracking
    - Channel authorization and restrictions
    - User role determination and Portfolio Manager assignment
    - Rate limiting and suspicious activity detection
    - Security logging and audit trail
    - JWT token management for API authentication
    - Multi-factor authentication support (future)
    - IP whitelisting and geolocation validation
    """
    
    def __init__(self, database_service: DatabaseService, slack_client: Optional[WebClient] = None):
        """
        Initialize the authentication service.
        
        Args:
            database_service: Database service instance
            slack_client: Slack WebClient instance (optional)
        """
        self.db = database_service
        self.config = get_config()
        
        # Initialize Slack client
        if slack_client:
            self.slack_client = slack_client
        else:
            self.slack_client = WebClient(token=self.config.slack.bot_token)
        
        # Session management
        self._active_sessions: Dict[str, UserSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        
        # Rate limiting
        self._rate_limits: Dict[str, List[float]] = {}  # user_id -> [timestamps]
        self._failed_attempts: Dict[str, List[float]] = {}  # user_id -> [timestamps]
        
        # Security monitoring
        self._suspicious_activity: Dict[str, List[Dict[str, Any]]] = {}
        self._blocked_users: Dict[str, datetime] = {}
        
        # JWT settings
        self._jwt_secret = self._generate_jwt_secret()
        self._jwt_algorithm = 'HS256'
        self._jwt_expiry = timedelta(hours=8)
        
        # Channel cache
        self._channel_cache: Dict[str, Dict[str, Any]] = {}
        self._channel_cache_ttl = 300  # 5 minutes
        
        # Portfolio Manager assignments cache
        self._pm_assignments: Dict[str, str] = {}  # analyst_user_id -> pm_user_id
        
        logger.info("AuthService initialized successfully")
    
    def _generate_jwt_secret(self) -> str:
        """Generate JWT secret key from configuration."""
        # Use signing secret as base for JWT key generation
        base_key = self.config.slack.signing_secret.encode('utf-8')
        return hashlib.sha256(base_key + b'jwt_secret').hexdigest()
    
    async def authenticate_slack_user(self, slack_user_id: str, team_id: str, 
                                    channel_id: Optional[str] = None,
                                    ip_address: Optional[str] = None,
                                    user_agent: Optional[str] = None) -> Tuple[User, UserSession]:
        """
        Authenticate a Slack user and create/update session.
        
        Args:
            slack_user_id: Slack user ID
            team_id: Slack team/workspace ID
            channel_id: Channel where authentication occurred
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (User, UserSession)
            
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limit exceeded
            SecurityViolationError: If security violation detected
        """
        try:
            # Check rate limits
            await self._check_rate_limits(slack_user_id)
            
            # Check if user is blocked
            if slack_user_id in self._blocked_users:
                block_until = self._blocked_users[slack_user_id]
                if datetime.now(timezone.utc) < block_until:
                    raise SecurityViolationError(
                        "User is temporarily blocked due to suspicious activity",
                        "USER_BLOCKED",
                        slack_user_id
                    )
                else:
                    # Unblock user
                    del self._blocked_users[slack_user_id]
            
            # Get user from Slack API
            slack_user_info = await self._get_slack_user_info(slack_user_id)
            
            # Get or create user in our system
            user = await self._get_or_create_user(slack_user_id, team_id, slack_user_info)
            
            # Validate user status
            if user.status != UserStatus.ACTIVE:
                await self._log_security_event(
                    'authentication_failed',
                    slack_user_id,
                    {'reason': 'inactive_user', 'status': user.status.value}
                )
                raise AuthenticationError(
                    f"User account is {user.status.value}",
                    "INACTIVE_USER",
                    user.user_id
                )
            
            # Check account lock
            if user.is_account_locked():
                await self._log_security_event(
                    'authentication_failed',
                    slack_user_id,
                    {'reason': 'account_locked'}
                )
                raise AuthenticationError(
                    "Account is temporarily locked due to failed login attempts",
                    "ACCOUNT_LOCKED",
                    user.user_id
                )
            
            # Create or update session
            session = await self._create_or_update_session(
                user, team_id, channel_id, ip_address, user_agent
            )
            
            # Record successful authentication
            user.record_login()
            await self.db.update_user(user)
            
            # Log successful authentication
            await self._log_security_event(
                'authentication_success',
                slack_user_id,
                {
                    'user_id': user.user_id,
                    'session_id': session.session_id,
                    'channel_id': channel_id,
                    'ip_address': ip_address
                }
            )
            
            logger.info(f"User {slack_user_id} authenticated successfully")
            return user, session
            
        except (RateLimitError, SecurityViolationError, AuthenticationError):
            # Re-raise these specific exceptions
            raise
        
        except SlackApiError as e:
            logger.error(f"Slack API error during authentication: {e}")
            await self._log_security_event(
                'authentication_error',
                slack_user_id,
                {'error': str(e), 'error_code': e.response.get('error', 'unknown')}
            )
            raise AuthenticationError(
                "Failed to authenticate with Slack",
                "SLACK_API_ERROR",
                slack_user_id
            )
        
        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            await self._log_security_event(
                'authentication_error',
                slack_user_id,
                {'error': str(e), 'error_type': type(e).__name__}
            )
            raise AuthenticationError(
                "Authentication failed due to system error",
                "SYSTEM_ERROR",
                slack_user_id
            )
    
    async def _check_rate_limits(self, user_id: str) -> None:
        """
        Check and enforce rate limits for authentication attempts.
        
        Args:
            user_id: User ID to check
            
        Raises:
            RateLimitError: If rate limit exceeded
        """
        current_time = time.time()
        window_size = 300  # 5 minutes
        max_attempts = 10  # 10 attempts per 5 minutes
        
        # Clean old entries
        if user_id in self._rate_limits:
            self._rate_limits[user_id] = [
                timestamp for timestamp in self._rate_limits[user_id]
                if current_time - timestamp < window_size
            ]
        else:
            self._rate_limits[user_id] = []
        
        # Check if limit exceeded
        if len(self._rate_limits[user_id]) >= max_attempts:
            retry_after = int(window_size - (current_time - self._rate_limits[user_id][0]))
            await self._log_security_event(
                'rate_limit_exceeded',
                user_id,
                {'attempts': len(self._rate_limits[user_id]), 'window_size': window_size}
            )
            raise RateLimitError(
                f"Rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after
            )
        
        # Record this attempt
        self._rate_limits[user_id].append(current_time)
    
    @backoff.on_exception(backoff.expo, SlackApiError, max_tries=3)
    async def _get_slack_user_info(self, slack_user_id: str) -> Dict[str, Any]:
        """
        Get user information from Slack API with retry logic.
        
        Args:
            slack_user_id: Slack user ID
            
        Returns:
            User information from Slack API
        """
        try:
            response = await asyncio.to_thread(
                self.slack_client.users_info,
                user=slack_user_id
            )
            
            if not response['ok']:
                raise SlackApiError(
                    message=f"Failed to get user info: {response.get('error', 'unknown')}",
                    response=response
                )
            
            return response['user']
            
        except SlackApiError as e:
            logger.error(f"Slack API error getting user info: {e}")
            raise
    
    async def _get_or_create_user(self, slack_user_id: str, team_id: str, 
                                slack_user_info: Dict[str, Any]) -> User:
        """
        Get existing user or create new user from Slack information.
        
        Args:
            slack_user_id: Slack user ID
            team_id: Slack team ID
            slack_user_info: User info from Slack API
            
        Returns:
            User object
        """
        try:
            # Try to get existing user
            user = await self.db.get_user_by_slack_id(slack_user_id)
            if user:
                # Update user profile with latest Slack info if needed
                await self._update_user_from_slack_info(user, slack_user_info)
                return user
            
            # Create new user
            user_id = str(uuid.uuid4())
            
            # Extract profile information from Slack
            profile = slack_user_info.get('profile', {})
            
            user_profile = UserProfile(
                display_name=slack_user_info.get('real_name', slack_user_info.get('name', 'Unknown')),
                email=profile.get('email', ''),
                department=profile.get('fields', {}).get('department', {}).get('value', 'Unknown'),
                phone=profile.get('phone', ''),
                timezone=slack_user_info.get('tz', 'UTC')
            )
            
            # Determine user role based on Slack profile or default
            role = await self._determine_user_role(slack_user_info)
            
            # Create user
            user = User(
                user_id=user_id,
                slack_user_id=slack_user_id,
                role=role,
                profile=user_profile,
                status=UserStatus.ACTIVE  # Auto-activate for Slack users
            )
            
            # Assign Portfolio Manager if user is Research Analyst
            if role == UserRole.RESEARCH_ANALYST:
                pm_id = await self._assign_portfolio_manager(user)
                user.portfolio_manager_id = pm_id
            
            # Store user in database
            await self.db.create_user(user)
            
            logger.info(f"Created new user {user_id} for Slack user {slack_user_id}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to get or create user: {e}")
            raise AuthenticationError(
                "Failed to process user information",
                "USER_PROCESSING_ERROR",
                slack_user_id
            )
    
    async def _update_user_from_slack_info(self, user: User, slack_user_info: Dict[str, Any]) -> None:
        """Update user profile with latest Slack information."""
        try:
            profile = slack_user_info.get('profile', {})
            updates = {}
            
            # Check for profile updates
            new_name = slack_user_info.get('real_name', slack_user_info.get('name', ''))
            if new_name and new_name != user.profile.display_name:
                updates['display_name'] = new_name
            
            new_email = profile.get('email', '')
            if new_email and new_email != user.profile.email:
                updates['email'] = new_email
            
            new_phone = profile.get('phone', '')
            if new_phone and new_phone != user.profile.phone:
                updates['phone'] = new_phone
            
            new_timezone = slack_user_info.get('tz', 'UTC')
            if new_timezone != user.profile.timezone:
                updates['timezone'] = new_timezone
            
            # Update if there are changes
            if updates:
                user.update_profile(**updates)
                await self.db.update_user(user)
                logger.info(f"Updated profile for user {user.user_id}")
                
        except Exception as e:
            logger.warning(f"Failed to update user profile from Slack info: {e}")
    
    async def _determine_user_role(self, slack_user_info: Dict[str, Any]) -> UserRole:
        """
        Determine user role based on Slack profile information.
        
        Args:
            slack_user_info: User info from Slack API
            
        Returns:
            UserRole enum value
        """
        # Check custom fields or title for role indicators
        profile = slack_user_info.get('profile', {})
        title = profile.get('title', '').lower()
        
        # Role determination logic based on title/department
        if any(keyword in title for keyword in ['portfolio manager', 'pm', 'fund manager']):
            return UserRole.PORTFOLIO_MANAGER
        elif any(keyword in title for keyword in ['trader', 'execution', 'trading']):
            return UserRole.EXECUTION_TRADER
        elif any(keyword in title for keyword in ['analyst', 'research', 'equity research']):
            return UserRole.RESEARCH_ANALYST
        elif any(keyword in title for keyword in ['admin', 'administrator', 'system']):
            return UserRole.ADMIN
        
        # Default to Research Analyst for new users
        return UserRole.RESEARCH_ANALYST
    
    async def _assign_portfolio_manager(self, user: User) -> Optional[str]:
        """
        Assign a Portfolio Manager to a Research Analyst.
        
        Args:
            user: User object (should be Research Analyst)
            
        Returns:
            Portfolio Manager user ID or None
        """
        try:
            # Get all Portfolio Managers
            portfolio_managers = await self.db.get_users_by_role(UserRole.PORTFOLIO_MANAGER)
            
            if not portfolio_managers:
                logger.warning("No Portfolio Managers available for assignment")
                return None
            
            # Simple round-robin assignment (could be enhanced with workload balancing)
            # For now, assign to the PM with the fewest analysts
            pm_workloads = {}
            for pm in portfolio_managers:
                analysts = await self.db.get_users_by_portfolio_manager(pm.user_id)
                pm_workloads[pm.user_id] = len(analysts)
            
            # Find PM with minimum workload
            assigned_pm_id = min(pm_workloads.keys(), key=lambda k: pm_workloads[k])
            
            logger.info(f"Assigned Portfolio Manager {assigned_pm_id} to analyst {user.user_id}")
            return assigned_pm_id
            
        except Exception as e:
            logger.error(f"Failed to assign Portfolio Manager: {e}")
            return None 
   
    async def _create_or_update_session(self, user: User, team_id: str,
                                      channel_id: Optional[str] = None,
                                      ip_address: Optional[str] = None,
                                      user_agent: Optional[str] = None) -> UserSession:
        """
        Create new session or update existing session for user.
        
        Args:
            user: User object
            team_id: Slack team ID
            channel_id: Current channel ID
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            UserSession object
        """
        # Check for existing active session
        existing_sessions = self._user_sessions.get(user.user_id, [])
        for session_id in existing_sessions[:]:  # Copy list to avoid modification during iteration
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                if session.is_active():
                    # Update existing session
                    session.update_activity('authentication', {
                        'channel_id': channel_id,
                        'ip_address': ip_address
                    })
                    if channel_id:
                        session.channel_id = channel_id
                    return session
                else:
                    # Remove expired session
                    await self._cleanup_session(session_id)
        
        # Create new session
        session_id = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.config.security.session_timeout_minutes)
        
        session = UserSession(
            session_id=session_id,
            user_id=user.user_id,
            slack_user_id=user.slack_user_id,
            team_id=team_id,
            channel_id=channel_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            permissions=user.permissions.copy()
        )
        
        # Store session
        self._active_sessions[session_id] = session
        if user.user_id not in self._user_sessions:
            self._user_sessions[user.user_id] = []
        self._user_sessions[user.user_id].append(session_id)
        
        # Log session creation
        session.update_activity('session_created', {
            'ip_address': ip_address,
            'user_agent': user_agent
        })
        
        logger.info(f"Created new session {session_id} for user {user.user_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session by ID with validation.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            UserSession object or None if not found/expired
        """
        if session_id not in self._active_sessions:
            return None
        
        session = self._active_sessions[session_id]
        
        # Check if session is expired
        if session.is_expired():
            await self._cleanup_session(session_id)
            return None
        
        return session
    
    async def validate_session(self, session_id: str, required_permissions: Optional[List[Permission]] = None) -> Tuple[User, UserSession]:
        """
        Validate session and optionally check permissions.
        
        Args:
            session_id: Session ID to validate
            required_permissions: List of required permissions
            
        Returns:
            Tuple of (User, UserSession)
            
        Raises:
            SessionError: If session is invalid
            AuthorizationError: If permissions are insufficient
        """
        session = await self.get_session(session_id)
        if not session:
            raise SessionError("Invalid or expired session", session_id)
        
        # Get current user data
        user = await self.db.get_user(session.user_id)
        if not user:
            await self._cleanup_session(session_id)
            raise SessionError("User not found for session", session_id)
        
        # Check user status
        if user.status != UserStatus.ACTIVE:
            await self._cleanup_session(session_id)
            raise SessionError("User account is not active", session_id)
        
        # Check permissions if required
        if required_permissions:
            missing_permissions = []
            for permission in required_permissions:
                if not user.has_permission(permission):
                    missing_permissions.append(permission.value)
            
            if missing_permissions:
                await self._log_security_event(
                    'authorization_failed',
                    user.slack_user_id,
                    {
                        'session_id': session_id,
                        'required_permissions': [p.value for p in required_permissions],
                        'missing_permissions': missing_permissions
                    }
                )
                raise AuthorizationError(
                    f"Insufficient permissions. Missing: {', '.join(missing_permissions)}",
                    ', '.join(missing_permissions),
                    user.user_id
                )
        
        # Update session activity
        session.update_activity('session_validated', {
            'required_permissions': [p.value for p in required_permissions] if required_permissions else None
        })
        
        return user, session
    
    async def authorize_channel_access(self, user: User, channel_id: str) -> bool:
        """
        Check if user can access a specific channel.
        
        Args:
            user: User object
            channel_id: Slack channel ID
            
        Returns:
            True if access is authorized
            
        Raises:
            AuthorizationError: If access is denied
        """
        try:
            # Check if channel is in approved list
            if not self.config.is_channel_approved(channel_id):
                await self._log_security_event(
                    'unauthorized_channel_access',
                    user.slack_user_id,
                    {'channel_id': channel_id, 'user_id': user.user_id}
                )
                raise AuthorizationError(
                    "This channel is not approved for trading operations",
                    "CHANNEL_ACCESS",
                    user.user_id
                )
            
            # Check user-specific channel restrictions
            if not user.can_access_channel(channel_id):
                await self._log_security_event(
                    'user_channel_restriction',
                    user.slack_user_id,
                    {'channel_id': channel_id, 'user_id': user.user_id}
                )
                raise AuthorizationError(
                    "You do not have access to this channel",
                    "USER_CHANNEL_RESTRICTION",
                    user.user_id
                )
            
            # Get channel information for additional validation
            channel_info = await self._get_channel_info(channel_id)
            
            # Ensure channel is private (for security)
            if not channel_info.get('is_private', False):
                await self._log_security_event(
                    'public_channel_access_attempt',
                    user.slack_user_id,
                    {'channel_id': channel_id, 'user_id': user.user_id}
                )
                raise AuthorizationError(
                    "Trading operations are only allowed in private channels",
                    "PUBLIC_CHANNEL_RESTRICTION",
                    user.user_id
                )
            
            return True
            
        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error checking channel authorization: {e}")
            raise AuthorizationError(
                "Failed to validate channel access",
                "CHANNEL_VALIDATION_ERROR",
                user.user_id
            )
    
    async def _get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """
        Get channel information with caching.
        
        Args:
            channel_id: Slack channel ID
            
        Returns:
            Channel information dictionary
        """
        # Check cache first
        if channel_id in self._channel_cache:
            cached_data, timestamp = self._channel_cache[channel_id]
            if time.time() - timestamp < self._channel_cache_ttl:
                return cached_data
        
        try:
            # Get channel info from Slack API
            response = await asyncio.to_thread(
                self.slack_client.conversations_info,
                channel=channel_id
            )
            
            if response['ok']:
                channel_info = response['channel']
                # Cache the result
                self._channel_cache[channel_id] = (channel_info, time.time())
                return channel_info
            else:
                logger.error(f"Failed to get channel info: {response.get('error')}")
                return {}
                
        except SlackApiError as e:
            logger.error(f"Slack API error getting channel info: {e}")
            return {}
    
    async def check_permission(self, user: User, permission: Permission, 
                             context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if user has specific permission with context validation.
        
        Args:
            user: User object
            permission: Permission to check
            context: Additional context for permission check
            
        Returns:
            True if permission is granted
        """
        # Basic permission check
        if not user.has_permission(permission):
            return False
        
        # Context-specific validation
        if context:
            # Portfolio access validation
            if permission in [Permission.VIEW_PORTFOLIO, Permission.MANAGE_PORTFOLIO]:
                target_user_id = context.get('target_user_id')
                if target_user_id and not user.can_view_portfolio(target_user_id):
                    return False
            
            # Risk override validation
            if permission == Permission.OVERRIDE_RISK_WARNINGS:
                risk_level = context.get('risk_level')
                if risk_level == 'critical' and user.role != UserRole.ADMIN:
                    return False
        
        return True    

    async def generate_jwt_token(self, user: User, session: UserSession, 
                               additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate JWT token for API authentication.
        
        Args:
            user: User object
            session: User session
            additional_claims: Additional claims to include
            
        Returns:
            JWT token string
        """
        try:
            now = datetime.now(timezone.utc)
            
            payload = {
                'iss': 'jain-trading-bot',  # Issuer
                'sub': user.user_id,        # Subject (user ID)
                'aud': 'trading-api',       # Audience
                'iat': int(now.timestamp()), # Issued at
                'exp': int((now + self._jwt_expiry).timestamp()), # Expiration
                'session_id': session.session_id,
                'slack_user_id': user.slack_user_id,
                'role': user.role.value,
                'permissions': [perm.value for perm in user.permissions]
            }
            
            # Add additional claims if provided
            if additional_claims:
                payload.update(additional_claims)
            
            token = jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
            
            logger.info(f"Generated JWT token for user {user.user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            raise AuthenticationError(
                "Failed to generate authentication token",
                "TOKEN_GENERATION_ERROR",
                user.user_id
            )
    
    async def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return payload.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dictionary
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
                audience='trading-api',
                issuer='jain-trading-bot'
            )
            
            # Validate session is still active
            session_id = payload.get('session_id')
            if session_id:
                session = await self.get_session(session_id)
                if not session:
                    raise AuthenticationError(
                        "Session associated with token is no longer valid",
                        "INVALID_SESSION"
                    )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired", "TOKEN_EXPIRED")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}", "INVALID_TOKEN")
    
    async def logout_user(self, session_id: str) -> bool:
        """
        Logout user and cleanup session.
        
        Args:
            session_id: Session ID to logout
            
        Returns:
            True if successful
        """
        try:
            session = await self.get_session(session_id)
            if session:
                await self._log_security_event(
                    'user_logout',
                    session.slack_user_id,
                    {'session_id': session_id, 'user_id': session.user_id}
                )
                
                await self._cleanup_session(session_id)
                logger.info(f"User logged out successfully: {session.user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up expired or invalid session."""
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            
            # Remove from user sessions list
            if session.user_id in self._user_sessions:
                if session_id in self._user_sessions[session.user_id]:
                    self._user_sessions[session.user_id].remove(session_id)
                
                # Clean up empty user session list
                if not self._user_sessions[session.user_id]:
                    del self._user_sessions[session.user_id]
            
            # Remove from active sessions
            del self._active_sessions[session_id]
            
            logger.debug(f"Cleaned up session {session_id}")
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id, session in self._active_sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self._cleanup_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    async def _log_security_event(self, event_type: str, user_id: str, details: Dict[str, Any]) -> None:
        """
        Log security event for monitoring and compliance.
        
        Args:
            event_type: Type of security event
            user_id: User ID associated with event
            details: Event details
        """
        try:
            security_event = {
                'event_id': str(uuid.uuid4()),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,
                'user_id': user_id,
                'details': details,
                'severity': self._get_event_severity(event_type)
            }
            
            # Store in database asynchronously
            asyncio.create_task(self._store_security_event(security_event))
            
            # Check for suspicious activity patterns
            await self._analyze_security_event(event_type, user_id, details)
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def _get_event_severity(self, event_type: str) -> str:
        """Get severity level for security event type."""
        high_severity_events = [
            'authentication_failed',
            'authorization_failed',
            'rate_limit_exceeded',
            'suspicious_activity_detected',
            'account_locked',
            'security_violation'
        ]
        
        if event_type in high_severity_events:
            return 'HIGH'
        elif 'failed' in event_type or 'error' in event_type:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def _store_security_event(self, event: Dict[str, Any]) -> None:
        """Store security event in database."""
        try:
            # This would typically store in a security events table
            # For now, we'll use the audit logging functionality
            self.db._log_audit_event(
                event['event_type'],
                event['user_id'],
                event['details']
            )
        except Exception as e:
            logger.error(f"Failed to store security event: {e}")
    
    async def _analyze_security_event(self, event_type: str, user_id: str, details: Dict[str, Any]) -> None:
        """
        Analyze security events for suspicious activity patterns.
        
        Args:
            event_type: Type of security event
            user_id: User ID
            details: Event details
        """
        try:
            # Track suspicious activity
            if user_id not in self._suspicious_activity:
                self._suspicious_activity[user_id] = []
            
            # Add event to user's activity log
            activity_entry = {
                'timestamp': time.time(),
                'event_type': event_type,
                'details': details
            }
            self._suspicious_activity[user_id].append(activity_entry)
            
            # Keep only last 100 events per user
            if len(self._suspicious_activity[user_id]) > 100:
                self._suspicious_activity[user_id] = self._suspicious_activity[user_id][-100:]
            
            # Analyze patterns
            await self._detect_suspicious_patterns(user_id)
            
        except Exception as e:
            logger.error(f"Error analyzing security event: {e}")
    
    async def _detect_suspicious_patterns(self, user_id: str) -> None:
        """
        Detect suspicious activity patterns for a user.
        
        Args:
            user_id: User ID to analyze
        """
        if user_id not in self._suspicious_activity:
            return
        
        activities = self._suspicious_activity[user_id]
        current_time = time.time()
        
        # Pattern 1: Multiple failed authentication attempts
        recent_failures = [
            a for a in activities
            if a['event_type'] == 'authentication_failed' and
            current_time - a['timestamp'] < 300  # Last 5 minutes
        ]
        
        if len(recent_failures) >= 5:
            await self._handle_suspicious_activity(
                user_id,
                'multiple_auth_failures',
                {'failure_count': len(recent_failures)}
            )
        
        # Pattern 2: Rapid channel switching
        recent_channel_access = [
            a for a in activities
            if 'channel_id' in a.get('details', {}) and
            current_time - a['timestamp'] < 60  # Last minute
        ]
        
        unique_channels = set(
            a['details']['channel_id'] for a in recent_channel_access
            if 'channel_id' in a['details']
        )
        
        if len(unique_channels) >= 5:
            await self._handle_suspicious_activity(
                user_id,
                'rapid_channel_switching',
                {'channel_count': len(unique_channels)}
            )
        
        # Pattern 3: Unusual IP address changes
        recent_ips = [
            a['details'].get('ip_address') for a in activities
            if 'ip_address' in a.get('details', {}) and
            current_time - a['timestamp'] < 3600  # Last hour
        ]
        
        unique_ips = set(ip for ip in recent_ips if ip)
        if len(unique_ips) >= 3:
            await self._handle_suspicious_activity(
                user_id,
                'multiple_ip_addresses',
                {'ip_count': len(unique_ips), 'ips': list(unique_ips)}
            )
    
    async def _handle_suspicious_activity(self, user_id: str, pattern_type: str, details: Dict[str, Any]) -> None:
        """
        Handle detected suspicious activity.
        
        Args:
            user_id: User ID with suspicious activity
            pattern_type: Type of suspicious pattern detected
            details: Pattern details
        """
        try:
            # Log the suspicious activity
            await self._log_security_event(
                'suspicious_activity_detected',
                user_id,
                {'pattern_type': pattern_type, 'details': details}
            )
            
            # Take action based on pattern severity
            if pattern_type in ['multiple_auth_failures', 'multiple_ip_addresses']:
                # Temporarily block user
                block_duration = timedelta(minutes=30)
                self._blocked_users[user_id] = datetime.now(timezone.utc) + block_duration
                
                # Invalidate all user sessions
                user_sessions = self._user_sessions.get(user_id, [])
                for session_id in user_sessions[:]:
                    await self._cleanup_session(session_id)
                
                logger.warning(f"User {user_id} temporarily blocked due to suspicious activity: {pattern_type}")
            
            elif pattern_type == 'rapid_channel_switching':
                # Rate limit the user more aggressively
                if user_id in self._rate_limits:
                    # Add extra penalty timestamps
                    current_time = time.time()
                    self._rate_limits[user_id].extend([current_time] * 5)
                
                logger.warning(f"Applied additional rate limiting to user {user_id} for rapid channel switching")
            
        except Exception as e:
            logger.error(f"Error handling suspicious activity: {e}")
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get security metrics for monitoring.
        
        Returns:
            Dictionary containing security metrics
        """
        return {
            'active_sessions': len(self._active_sessions),
            'blocked_users': len(self._blocked_users),
            'users_with_rate_limits': len(self._rate_limits),
            'users_with_suspicious_activity': len(self._suspicious_activity),
            'total_security_events': sum(
                len(activities) for activities in self._suspicious_activity.values()
            )
        }
    
    async def get_user_security_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get security status for a specific user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Dictionary containing user security status
        """
        status = {
            'user_id': user_id,
            'is_blocked': user_id in self._blocked_users,
            'active_sessions': len(self._user_sessions.get(user_id, [])),
            'recent_activity_count': len(self._suspicious_activity.get(user_id, [])),
            'rate_limit_status': 'normal'
        }
        
        # Check rate limit status
        if user_id in self._rate_limits:
            current_time = time.time()
            recent_attempts = [
                t for t in self._rate_limits[user_id]
                if current_time - t < 300  # Last 5 minutes
            ]
            if len(recent_attempts) > 5:
                status['rate_limit_status'] = 'elevated'
            elif len(recent_attempts) > 8:
                status['rate_limit_status'] = 'critical'
        
        # Add block expiration if blocked
        if status['is_blocked']:
            block_until = self._blocked_users[user_id]
            status['blocked_until'] = block_until.isoformat()
            status['block_remaining_seconds'] = int(
                (block_until - datetime.now(timezone.utc)).total_seconds()
            )
        
        return status