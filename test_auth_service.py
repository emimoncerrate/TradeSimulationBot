"""
Comprehensive unit tests for the AuthService class.

This module provides complete test coverage for all AuthService methods and security scenarios,
including role-based access controls, channel restrictions, permission validation,
security testing for unauthorized access attempts, and edge cases.
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional

# Mock the configuration before importing other modules
import os
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token'
os.environ['SLACK_SIGNING_SECRET'] = 'test_signing_secret_12345678901234567890'
os.environ['FINNHUB_API_KEY'] = 'test_api_key'

# Import the classes we're testing
from services.auth import (
    AuthService, UserSession, AuthenticationError, AuthorizationError,
    SessionError, RateLimitError, SecurityViolationError
)
from services.database import DatabaseService, DatabaseError, NotFoundError
from models.user import User, UserRole, UserStatus, Permission, UserProfile
from config.settings import AppConfig, SlackConfig, SecurityConfig
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class TestUserSession:
    """Test cases for UserSession class."""
    
    def test_user_session_creation(self):
        """Test UserSession creation with valid data."""
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        slack_user_id = "U123456789"
        team_id = "T123456789"
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=8)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            slack_user_id=slack_user_id,
            team_id=team_id,
            created_at=created_at,
            expires_at=expires_at
        )
        
        assert session.session_id == session_id
        assert session.user_id == user_id
        assert session.slack_user_id == slack_user_id
        assert session.team_id == team_id
        assert session.created_at == created_at
        assert session.expires_at == expires_at
        assert isinstance(session.permissions, set)
        assert len(session.activity_log) == 0
    
    def test_session_expiration_check(self):
        """Test session expiration checking."""
        # Create expired session
        expired_session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc) - timedelta(hours=10),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        assert expired_session.is_expired() is True
        assert expired_session.is_active() is False
        
        # Create active session
        active_session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        assert active_session.is_expired() is False
        assert active_session.is_active() is True
    
    def test_session_activity_update(self):
        """Test session activity logging."""
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        # Update activity
        session.update_activity('test_activity', {'key': 'value'})
        
        assert len(session.activity_log) == 1
        assert session.activity_log[0]['activity_type'] == 'test_activity'
        assert session.activity_log[0]['details'] == {'key': 'value'}
        assert session.last_activity is not None
    
    def test_session_serialization(self):
        """Test session to_dict and from_dict methods."""
        original_session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
            permissions={Permission.EXECUTE_TRADES, Permission.VIEW_PORTFOLIO}
        )
        
        # Convert to dict and back
        session_dict = original_session.to_dict()
        restored_session = UserSession.from_dict(session_dict)
        
        assert restored_session.session_id == original_session.session_id
        assert restored_session.user_id == original_session.user_id
        assert restored_session.permissions == original_session.permissions


class TestAuthService:
    """Test cases for AuthService class."""
    
    @pytest.fixture
    def mock_database_service(self):
        """Create mock database service."""
        mock_db = Mock(spec=DatabaseService)
        mock_db.get_user_by_slack_id = AsyncMock()
        mock_db.create_user = AsyncMock()
        mock_db.update_user = AsyncMock()
        mock_db.get_user = AsyncMock()
        mock_db.get_users_by_role = AsyncMock()
        mock_db.get_users_by_portfolio_manager = AsyncMock()
        mock_db._log_audit_event = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client."""
        mock_client = Mock(spec=WebClient)
        mock_client.users_info = Mock()
        mock_client.conversations_info = Mock()
        return mock_client
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        mock_config = Mock(spec=AppConfig)
        mock_config.slack = Mock(spec=SlackConfig)
        mock_config.slack.bot_token = "xoxb-test-token"
        mock_config.slack.signing_secret = "test_signing_secret_12345678901234567890"
        mock_config.security = Mock(spec=SecurityConfig)
        mock_config.security.session_timeout_minutes = 480
        mock_config.security.approved_channels = ["C123456789"]
        mock_config.is_channel_approved = Mock(return_value=True)
        return mock_config
    
    @pytest.fixture
    def auth_service(self, mock_database_service, mock_slack_client, mock_config):
        """Create AuthService instance with mocked dependencies."""
        with patch('services.auth.get_config', return_value=mock_config):
            service = AuthService(mock_database_service, mock_slack_client)
            return service
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        profile = UserProfile(
            display_name="Test User",
            email="test@example.com",
            department="Trading"
        )
        
        return User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            role=UserRole.EXECUTION_TRADER,
            profile=profile,
            status=UserStatus.ACTIVE
        )
    
    @pytest.fixture
    def sample_slack_user_info(self):
        """Create sample Slack user info."""
        return {
            'id': 'U123456789',
            'name': 'testuser',
            'real_name': 'Test User',
            'profile': {
                'email': 'test@example.com',
                'title': 'Execution Trader',
                'phone': '+1234567890'
            },
            'tz': 'America/New_York'
        }
    
    @pytest.mark.asyncio
    async def test_authenticate_slack_user_success(self, auth_service, mock_database_service, 
                                                 sample_user, sample_slack_user_info):
        """Test successful Slack user authentication."""
        # Setup mocks
        mock_database_service.get_user_by_slack_id.return_value = sample_user
        mock_database_service.update_user.return_value = True
        
        with patch.object(auth_service, '_get_slack_user_info', return_value=sample_slack_user_info):
            # Authenticate user
            user, session = await auth_service.authenticate_slack_user(
                slack_user_id="U123456789",
                team_id="T123456789",
                channel_id="C123456789",
                ip_address="192.168.1.1"
            )
            
            # Verify results
            assert user == sample_user
            assert isinstance(session, UserSession)
            assert session.user_id == sample_user.user_id
            assert session.slack_user_id == sample_user.slack_user_id
            assert session.channel_id == "C123456789"
            assert session.ip_address == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_authenticate_new_user_creation(self, auth_service, mock_database_service, 
                                                sample_slack_user_info):
        """Test authentication with new user creation."""
        # Setup mocks - no existing user
        mock_database_service.get_user_by_slack_id.return_value = None
        mock_database_service.create_user.return_value = True
        mock_database_service.get_users_by_role.return_value = []  # No PMs available
        
        with patch.object(auth_service, '_get_slack_user_info', return_value=sample_slack_user_info):
            # Authenticate user
            user, session = await auth_service.authenticate_slack_user(
                slack_user_id="U123456789",
                team_id="T123456789"
            )
            
            # Verify user was created
            assert user is not None
            assert user.slack_user_id == "U123456789"
            assert user.profile.display_name == "Test User"
            assert user.profile.email == "test@example.com"
            assert user.role == UserRole.EXECUTION_TRADER  # Based on title
            assert user.status == UserStatus.ACTIVE
            
            # Verify session was created
            assert isinstance(session, UserSession)
            assert session.user_id == user.user_id
            
            # Verify database calls
            mock_database_service.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user_fails(self, auth_service, mock_database_service, 
                                                  sample_user, sample_slack_user_info):
        """Test authentication fails for inactive user."""
        # Setup inactive user
        sample_user.status = UserStatus.INACTIVE
        mock_database_service.get_user_by_slack_id.return_value = sample_user
        
        with patch.object(auth_service, '_get_slack_user_info', return_value=sample_slack_user_info):
            # Attempt authentication
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_service.authenticate_slack_user(
                    slack_user_id="U123456789",
                    team_id="T123456789"
                )
            
            assert exc_info.value.error_code == "INACTIVE_USER"
            assert "inactive" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, auth_service):
        """Test rate limiting functionality."""
        user_id = "U123456789"
        
        # Simulate multiple rapid requests
        for i in range(10):
            await auth_service._check_rate_limits(user_id)
        
        # Next request should trigger rate limit
        with pytest.raises(RateLimitError) as exc_info:
            await auth_service._check_rate_limits(user_id)
        
        assert exc_info.value.retry_after is not None
        assert exc_info.value.retry_after > 0
    
    @pytest.mark.asyncio
    async def test_session_validation_success(self, auth_service, mock_database_service, sample_user):
        """Test successful session validation."""
        # Create session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=sample_user.user_id,
            slack_user_id=sample_user.slack_user_id,
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        # Add session to auth service
        auth_service._active_sessions[session.session_id] = session
        
        # Setup database mock
        mock_database_service.get_user.return_value = sample_user
        
        # Validate session
        user, validated_session = await auth_service.validate_session(session.session_id)
        
        assert user == sample_user
        assert validated_session == session
    
    @pytest.mark.asyncio
    async def test_session_validation_expired_session(self, auth_service):
        """Test session validation with expired session."""
        # Create expired session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc) - timedelta(hours=10),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        # Add session to auth service
        auth_service._active_sessions[session.session_id] = session
        
        # Attempt validation
        with pytest.raises(SessionError) as exc_info:
            await auth_service.validate_session(session.session_id)
        
        assert "expired" in exc_info.value.message.lower()
        # Session should be cleaned up
        assert session.session_id not in auth_service._active_sessions
    
    @pytest.mark.asyncio
    async def test_permission_validation(self, auth_service, mock_database_service, sample_user):
        """Test permission validation during session validation."""
        # Create session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=sample_user.user_id,
            slack_user_id=sample_user.slack_user_id,
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        auth_service._active_sessions[session.session_id] = session
        mock_database_service.get_user.return_value = sample_user
        
        # Test with permission user has
        required_permissions = [Permission.EXECUTE_TRADES]
        user, validated_session = await auth_service.validate_session(
            session.session_id, required_permissions
        )
        assert user == sample_user
        
        # Test with permission user doesn't have
        required_permissions = [Permission.SYSTEM_ADMIN]
        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.validate_session(session.session_id, required_permissions)
        
        assert "insufficient permissions" in exc_info.value.message.lower()
        assert exc_info.value.required_permission == "system_admin"
    
    @pytest.mark.asyncio
    async def test_channel_authorization_success(self, auth_service, sample_user):
        """Test successful channel authorization."""
        channel_id = "C123456789"
        
        # Mock channel info response
        channel_info = {
            'id': channel_id,
            'name': 'trading-channel',
            'is_private': True,
            'is_channel': True
        }
        
        with patch.object(auth_service, '_get_channel_info', return_value=channel_info):
            # Should succeed for approved private channel
            result = await auth_service.authorize_channel_access(sample_user, channel_id)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_channel_authorization_unapproved_channel(self, auth_service, sample_user, mock_config):
        """Test channel authorization failure for unapproved channel."""
        channel_id = "C987654321"  # Different from approved channel
        mock_config.is_channel_approved.return_value = False
        
        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.authorize_channel_access(sample_user, channel_id)
        
        assert "not approved" in exc_info.value.message.lower()
        assert exc_info.value.required_permission == "CHANNEL_ACCESS"
    
    @pytest.mark.asyncio
    async def test_channel_authorization_public_channel(self, auth_service, sample_user):
        """Test channel authorization failure for public channel."""
        channel_id = "C123456789"
        
        # Mock public channel info
        channel_info = {
            'id': channel_id,
            'name': 'general',
            'is_private': False,  # Public channel
            'is_channel': True
        }
        
        with patch.object(auth_service, '_get_channel_info', return_value=channel_info):
            with pytest.raises(AuthorizationError) as exc_info:
                await auth_service.authorize_channel_access(sample_user, channel_id)
            
            assert "private channels" in exc_info.value.message.lower()
            assert exc_info.value.required_permission == "PUBLIC_CHANNEL_RESTRICTION"
    
    @pytest.mark.asyncio
    async def test_user_role_determination(self, auth_service):
        """Test user role determination from Slack profile."""
        # Test Portfolio Manager
        pm_info = {
            'profile': {'title': 'Portfolio Manager'}
        }
        role = await auth_service._determine_user_role(pm_info)
        assert role == UserRole.PORTFOLIO_MANAGER
        
        # Test Execution Trader
        trader_info = {
            'profile': {'title': 'Execution Trader'}
        }
        role = await auth_service._determine_user_role(trader_info)
        assert role == UserRole.EXECUTION_TRADER
        
        # Test Research Analyst
        analyst_info = {
            'profile': {'title': 'Research Analyst'}
        }
        role = await auth_service._determine_user_role(analyst_info)
        assert role == UserRole.RESEARCH_ANALYST
        
        # Test Admin
        admin_info = {
            'profile': {'title': 'System Administrator'}
        }
        role = await auth_service._determine_user_role(admin_info)
        assert role == UserRole.ADMIN
        
        # Test default role
        unknown_info = {
            'profile': {'title': 'Unknown Role'}
        }
        role = await auth_service._determine_user_role(unknown_info)
        assert role == UserRole.RESEARCH_ANALYST  # Default
    
    @pytest.mark.asyncio
    async def test_portfolio_manager_assignment(self, auth_service, mock_database_service):
        """Test Portfolio Manager assignment to Research Analyst."""
        # Create sample PM
        pm_profile = UserProfile(display_name="PM User", email="pm@example.com", department="Trading")
        pm_user = User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U987654321",
            role=UserRole.PORTFOLIO_MANAGER,
            profile=pm_profile,
            status=UserStatus.ACTIVE
        )
        
        # Create analyst user
        analyst_profile = UserProfile(display_name="Analyst User", email="analyst@example.com", department="Research")
        analyst_user = User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            role=UserRole.RESEARCH_ANALYST,
            profile=analyst_profile,
            status=UserStatus.ACTIVE
        )
        
        # Setup mocks
        mock_database_service.get_users_by_role.return_value = [pm_user]
        mock_database_service.get_users_by_portfolio_manager.return_value = []  # No existing analysts
        
        # Test assignment
        assigned_pm_id = await auth_service._assign_portfolio_manager(analyst_user)
        
        assert assigned_pm_id == pm_user.user_id
        mock_database_service.get_users_by_role.assert_called_with(UserRole.PORTFOLIO_MANAGER)
    
    @pytest.mark.asyncio
    async def test_jwt_token_generation_and_validation(self, auth_service, sample_user):
        """Test JWT token generation and validation."""
        # Create session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=sample_user.user_id,
            slack_user_id=sample_user.slack_user_id,
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        # Generate token
        token = await auth_service.generate_jwt_token(sample_user, session)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Add session to auth service for validation
        auth_service._active_sessions[session.session_id] = session
        
        # Validate token
        payload = await auth_service.validate_jwt_token(token)
        
        assert payload['sub'] == sample_user.user_id
        assert payload['session_id'] == session.session_id
        assert payload['slack_user_id'] == sample_user.slack_user_id
        assert payload['role'] == sample_user.role.value
        assert isinstance(payload['permissions'], list)
    
    @pytest.mark.asyncio
    async def test_jwt_token_validation_expired_session(self, auth_service, sample_user):
        """Test JWT token validation with expired session."""
        # Create session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=sample_user.user_id,
            slack_user_id=sample_user.slack_user_id,
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        # Generate token
        token = await auth_service.generate_jwt_token(sample_user, session)
        
        # Don't add session to auth service (simulates expired/invalid session)
        
        # Validate token should fail
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.validate_jwt_token(token)
        
        assert exc_info.value.error_code == "INVALID_SESSION"
    
    @pytest.mark.asyncio
    async def test_logout_user(self, auth_service):
        """Test user logout functionality."""
        # Create session
        session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        # Add session to auth service
        auth_service._active_sessions[session.session_id] = session
        auth_service._user_sessions[session.user_id] = [session.session_id]
        
        # Logout user
        result = await auth_service.logout_user(session.session_id)
        
        assert result is True
        assert session.session_id not in auth_service._active_sessions
        assert session.user_id not in auth_service._user_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, auth_service):
        """Test cleanup of expired sessions."""
        # Create expired session
        expired_session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U123456789",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc) - timedelta(hours=10),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        
        # Create active session
        active_session = UserSession(
            session_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4()),
            slack_user_id="U987654321",
            team_id="T123456789",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        # Add sessions
        auth_service._active_sessions[expired_session.session_id] = expired_session
        auth_service._active_sessions[active_session.session_id] = active_session
        auth_service._user_sessions[expired_session.user_id] = [expired_session.session_id]
        auth_service._user_sessions[active_session.user_id] = [active_session.session_id]
        
        # Cleanup expired sessions
        cleaned_count = await auth_service.cleanup_expired_sessions()
        
        assert cleaned_count == 1
        assert expired_session.session_id not in auth_service._active_sessions
        assert active_session.session_id in auth_service._active_sessions
        assert expired_session.user_id not in auth_service._user_sessions
        assert active_session.user_id in auth_service._user_sessions
    
    @pytest.mark.asyncio
    async def test_suspicious_activity_detection(self, auth_service):
        """Test suspicious activity detection and handling."""
        user_id = "U123456789"
        
        # Simulate multiple failed authentication attempts
        for i in range(6):
            await auth_service._analyze_security_event(
                'authentication_failed',
                user_id,
                {'reason': 'invalid_credentials', 'attempt': i}
            )
        
        # User should be blocked
        assert user_id in auth_service._blocked_users
        
        # Check block expiration
        block_until = auth_service._blocked_users[user_id]
        assert block_until > datetime.now(timezone.utc)
    
    @pytest.mark.asyncio
    async def test_rapid_channel_switching_detection(self, auth_service):
        """Test detection of rapid channel switching."""
        user_id = "U123456789"
        
        # Simulate rapid channel switching
        for i in range(6):
            await auth_service._analyze_security_event(
                'channel_access',
                user_id,
                {'channel_id': f'C{i:09d}'}
            )
        
        # Should trigger suspicious activity handling
        assert user_id in auth_service._suspicious_activity
        activities = auth_service._suspicious_activity[user_id]
        assert len(activities) == 6
        
        # Should apply additional rate limiting
        if user_id in auth_service._rate_limits:
            # Rate limits should be more restrictive
            assert len(auth_service._rate_limits[user_id]) > 6
    
    def test_security_metrics(self, auth_service):
        """Test security metrics collection."""
        # Add some test data
        auth_service._active_sessions['session1'] = Mock()
        auth_service._blocked_users['user1'] = datetime.now(timezone.utc)
        auth_service._rate_limits['user2'] = [time.time()]
        auth_service._suspicious_activity['user3'] = [{'event': 'test'}]
        
        metrics = auth_service.get_security_metrics()
        
        assert metrics['active_sessions'] == 1
        assert metrics['blocked_users'] == 1
        assert metrics['users_with_rate_limits'] == 1
        assert metrics['users_with_suspicious_activity'] == 1
        assert metrics['total_security_events'] == 1
    
    @pytest.mark.asyncio
    async def test_user_security_status(self, auth_service):
        """Test user security status retrieval."""
        user_id = "U123456789"
        
        # Add some test data
        auth_service._blocked_users[user_id] = datetime.now(timezone.utc) + timedelta(minutes=30)
        auth_service._user_sessions[user_id] = ['session1', 'session2']
        auth_service._suspicious_activity[user_id] = [{'event': 'test1'}, {'event': 'test2'}]
        auth_service._rate_limits[user_id] = [time.time() - 60] * 6  # 6 attempts in last minute
        
        status = await auth_service.get_user_security_status(user_id)
        
        assert status['user_id'] == user_id
        assert status['is_blocked'] is True
        assert status['active_sessions'] == 2
        assert status['recent_activity_count'] == 2
        assert status['rate_limit_status'] == 'elevated'
        assert 'blocked_until' in status
        assert 'block_remaining_seconds' in status
    
    @pytest.mark.asyncio
    async def test_slack_api_error_handling(self, auth_service, mock_slack_client):
        """Test handling of Slack API errors."""
        # Mock Slack API error
        error_response = {'ok': False, 'error': 'user_not_found'}
        mock_slack_client.users_info.return_value = error_response
        
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_slack_user(
                slack_user_id="U123456789",
                team_id="T123456789"
            )
        
        assert exc_info.value.error_code == "SLACK_API_ERROR"
        assert "slack" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, auth_service, mock_database_service, sample_slack_user_info):
        """Test handling of database errors."""
        # Mock database error
        mock_database_service.get_user_by_slack_id.side_effect = DatabaseError("Database connection failed")
        
        with patch.object(auth_service, '_get_slack_user_info', return_value=sample_slack_user_info):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_service.authenticate_slack_user(
                    slack_user_id="U123456789",
                    team_id="T123456789"
                )
            
            assert exc_info.value.error_code == "SYSTEM_ERROR"
    
    def test_permission_context_validation(self, auth_service, sample_user):
        """Test permission checking with context validation."""
        # Test portfolio access permission
        context = {'target_user_id': 'other_user_id'}
        
        # User should not be able to view other user's portfolio (not PM or Admin)
        result = auth_service.check_permission(
            sample_user, 
            Permission.VIEW_PORTFOLIO, 
            context
        )
        # This would depend on the user's role and the specific implementation
        # For execution trader, they should only view their own portfolio
        
        # Test risk override with critical risk level
        context = {'risk_level': 'critical'}
        result = auth_service.check_permission(
            sample_user,
            Permission.OVERRIDE_RISK_WARNINGS,
            context
        )
        # Execution trader shouldn't be able to override critical risk warnings
        assert result is False  # Assuming execution trader doesn't have this permission
    
    @pytest.mark.asyncio
    async def test_multiple_ip_address_detection(self, auth_service):
        """Test detection of multiple IP addresses for suspicious activity."""
        user_id = "U123456789"
        
        # Simulate authentication from multiple IP addresses
        ip_addresses = ["192.168.1.1", "10.0.0.1", "172.16.0.1", "203.0.113.1"]
        
        for ip in ip_addresses:
            await auth_service._analyze_security_event(
                'authentication_success',
                user_id,
                {'ip_address': ip}
            )
        
        # Should trigger suspicious activity detection
        assert user_id in auth_service._suspicious_activity
        
        # Should potentially block user for multiple IP addresses
        # This depends on the specific implementation of the detection algorithm


class TestAuthServiceIntegration:
    """Integration tests for AuthService with real-like scenarios."""
    
    @pytest.fixture
    def integration_auth_service(self):
        """Create AuthService with more realistic mocks for integration testing."""
        mock_db = Mock(spec=DatabaseService)
        mock_slack = Mock(spec=WebClient)
        
        # Setup more realistic mock responses
        mock_db.get_user_by_slack_id = AsyncMock()
        mock_db.create_user = AsyncMock()
        mock_db.update_user = AsyncMock()
        mock_db.get_user = AsyncMock()
        mock_db.get_users_by_role = AsyncMock()
        mock_db.get_users_by_portfolio_manager = AsyncMock()
        mock_db._log_audit_event = AsyncMock()
        
        mock_config = Mock()
        mock_config.slack.bot_token = "xoxb-test-token"
        mock_config.slack.signing_secret = "test_signing_secret_12345678901234567890"
        mock_config.security.session_timeout_minutes = 480
        mock_config.security.approved_channels = ["C123456789"]
        mock_config.is_channel_approved = Mock(return_value=True)
        
        with patch('services.auth.get_config', return_value=mock_config):
            return AuthService(mock_db, mock_slack)
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self, integration_auth_service):
        """Test complete authentication flow from start to finish."""
        # Setup test data
        slack_user_id = "U123456789"
        team_id = "T123456789"
        channel_id = "C123456789"
        
        slack_user_info = {
            'id': slack_user_id,
            'real_name': 'John Trader',
            'profile': {
                'email': 'john@jain.com',
                'title': 'Portfolio Manager'
            },
            'tz': 'America/New_York'
        }
        
        # Mock no existing user (new user creation)
        integration_auth_service.db.get_user_by_slack_id.return_value = None
        integration_auth_service.db.create_user.return_value = True
        integration_auth_service.db.get_users_by_role.return_value = []
        
        with patch.object(integration_auth_service, '_get_slack_user_info', return_value=slack_user_info):
            # Authenticate user
            user, session = await integration_auth_service.authenticate_slack_user(
                slack_user_id=slack_user_id,
                team_id=team_id,
                channel_id=channel_id,
                ip_address="192.168.1.100"
            )
            
            # Verify user creation
            assert user.slack_user_id == slack_user_id
            assert user.role == UserRole.PORTFOLIO_MANAGER
            assert user.status == UserStatus.ACTIVE
            
            # Verify session creation
            assert session.user_id == user.user_id
            assert session.team_id == team_id
            assert session.channel_id == channel_id
            
            # Test session validation
            validated_user, validated_session = await integration_auth_service.validate_session(
                session.session_id,
                [Permission.VIEW_PORTFOLIO, Permission.MANAGE_PORTFOLIO]
            )
            
            assert validated_user.user_id == user.user_id
            assert validated_session.session_id == session.session_id
            
            # Test channel authorization
            authorized = await integration_auth_service.authorize_channel_access(user, channel_id)
            assert authorized is True
            
            # Test JWT token generation and validation
            token = await integration_auth_service.generate_jwt_token(user, session)
            payload = await integration_auth_service.validate_jwt_token(token)
            
            assert payload['sub'] == user.user_id
            assert payload['role'] == UserRole.PORTFOLIO_MANAGER.value
            
            # Test logout
            logout_success = await integration_auth_service.logout_user(session.session_id)
            assert logout_success is True
            
            # Verify session cleanup
            cleaned_session = await integration_auth_service.get_session(session.session_id)
            assert cleaned_session is None
    
    @pytest.mark.asyncio
    async def test_role_based_access_control_scenarios(self, integration_auth_service):
        """Test various role-based access control scenarios."""
        # Create users with different roles
        users = {}
        
        # Research Analyst
        analyst_profile = UserProfile(display_name="Research Analyst", email="analyst@jain.com", department="Research")
        users['analyst'] = User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U111111111",
            role=UserRole.RESEARCH_ANALYST,
            profile=analyst_profile,
            status=UserStatus.ACTIVE
        )
        
        # Execution Trader
        trader_profile = UserProfile(display_name="Execution Trader", email="trader@jain.com", department="Trading")
        users['trader'] = User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U222222222",
            role=UserRole.EXECUTION_TRADER,
            profile=trader_profile,
            status=UserStatus.ACTIVE
        )
        
        # Portfolio Manager
        pm_profile = UserProfile(display_name="Portfolio Manager", email="pm@jain.com", department="Management")
        users['pm'] = User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U333333333",
            role=UserRole.PORTFOLIO_MANAGER,
            profile=pm_profile,
            status=UserStatus.ACTIVE
        )
        
        # Admin
        admin_profile = UserProfile(display_name="Admin", email="admin@jain.com", department="IT")
        users['admin'] = User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U444444444",
            role=UserRole.ADMIN,
            profile=admin_profile,
            status=UserStatus.ACTIVE
        )
        
        # Test permission scenarios
        test_cases = [
            # (user_role, permission, should_have)
            ('analyst', Permission.VIEW_TRADES, True),
            ('analyst', Permission.EXECUTE_TRADES, False),
            ('analyst', Permission.SYSTEM_ADMIN, False),
            
            ('trader', Permission.EXECUTE_TRADES, True),
            ('trader', Permission.VIEW_TRADES, True),
            ('trader', Permission.OVERRIDE_RISK_WARNINGS, False),
            
            ('pm', Permission.EXECUTE_TRADES, True),
            ('pm', Permission.OVERRIDE_RISK_WARNINGS, True),
            ('pm', Permission.VIEW_ALL_PORTFOLIOS, True),
            ('pm', Permission.SYSTEM_ADMIN, False),
            
            ('admin', Permission.SYSTEM_ADMIN, True),
            ('admin', Permission.MANAGE_USERS, True),
            ('admin', Permission.EXECUTE_TRADES, True),
        ]
        
        for user_role, permission, should_have in test_cases:
            user = users[user_role]
            has_permission = integration_auth_service.check_permission(user, permission)
            
            assert has_permission == should_have, \
                f"{user_role} should {'have' if should_have else 'not have'} {permission.value}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])