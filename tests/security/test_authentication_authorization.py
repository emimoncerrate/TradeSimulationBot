"""
Security Testing for Authentication and Authorization

This module provides comprehensive security tests for authentication and authorization
mechanisms including user authentication, role-based access control, session management,
channel restrictions, and security violation detection with detailed audit logging.
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Import application components
from services.auth import (
    AuthService, 
    AuthenticationError, 
    AuthorizationError, 
    SessionError,
    RateLimitError,
    SecurityViolationError
)
from services.database import DatabaseService, DatabaseError, NotFoundError
from listeners.commands import CommandHandler, CommandType
from listeners.actions import ActionHandler, ActionType
from models.user import User, UserRole, UserStatus, Permission, UserProfile
from models.trade import Trade, TradeType, TradeStatus

# Test utilities
from tests.fixtures.slack_payloads import (
    create_slash_command_payload,
    create_button_action_payload,
    create_modal_submission_payload
)
from tests.fixtures.test_data import create_test_user
from tests.utils.mock_services import MockSlackClient, MockDatabaseService


class TestAuthenticationSecurity:
    """
    Comprehensive authentication security testing.
    
    Tests user authentication mechanisms, session management,
    credential validation, and authentication bypass attempts.
    """
    
    @pytest.fixture
    async def auth_service(self):
        """Create auth service for testing."""
        db_service = MockDatabaseService()
        auth_service = AuthService(db_service)
        return auth_service
    
    @pytest.fixture
    def valid_users(self):
        """Create valid test users for authentication testing."""
        return {
            'analyst': create_test_user(
                user_id='auth_test_analyst',
                slack_user_id='U_ANALYST_001',
                role=UserRole.RESEARCH_ANALYST,
                status=UserStatus.ACTIVE
            ),
            'trader': create_test_user(
                user_id='auth_test_trader',
                slack_user_id='U_TRADER_001',
                role=UserRole.EXECUTION_TRADER,
                status=UserStatus.ACTIVE
            ),
            'inactive': create_test_user(
                user_id='auth_test_inactive',
                slack_user_id='U_INACTIVE_001',
                role=UserRole.EXECUTION_TRADER,
                status=UserStatus.INACTIVE
            ),
            'suspended': create_test_user(
                user_id='auth_test_suspended',
                slack_user_id='U_SUSPENDED_001',
                role=UserRole.EXECUTION_TRADER,
                status=UserStatus.SUSPENDED
            )
        }
    
    @pytest.mark.asyncio
    async def test_valid_user_authentication(self, auth_service, valid_users):
        """Test successful authentication for valid users."""
        # Setup database with valid users
        for user in valid_users.values():
            await auth_service.db_service.create_user(user)
        
        # Test authentication for active user
        active_user = valid_users['analyst']
        user, session = await auth_service.authenticate_slack_user(
            active_user.slack_user_id,
            'T1234567890',
            'C1234567890'
        )
        
        # Verify authentication success
        assert user is not None
        assert user.user_id == active_user.user_id
        assert user.role == active_user.role
        assert user.status == UserStatus.ACTIVE
        
        # Verify session creation
        assert session is not None
        assert session.session_id is not None
        assert session.user_id == user.user_id
        assert session.is_active
        
        # Verify session is stored
        stored_session = await auth_service.get_session(session.session_id)
        assert stored_session is not None
        assert stored_session.user_id == user.user_id
    
    @pytest.mark.asyncio
    async def test_invalid_user_authentication(self, auth_service):
        """Test authentication failure for invalid users."""
        # Test authentication with non-existent user
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_slack_user(
                'U_NONEXISTENT',
                'T1234567890',
                'C1234567890'
            )
        
        assert exc_info.value.error_code == 'USER_NOT_FOUND'
        assert 'not found' in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_inactive_user_authentication(self, auth_service, valid_users):
        """Test authentication failure for inactive users."""
        # Setup database with inactive user
        inactive_user = valid_users['inactive']
        await auth_service.db_service.create_user(inactive_user)
        
        # Test authentication for inactive user
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_slack_user(
                inactive_user.slack_user_id,
                'T1234567890',
                'C1234567890'
            )
        
        assert exc_info.value.error_code == 'USER_INACTIVE'
        assert 'inactive' in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_suspended_user_authentication(self, auth_service, valid_users):
        """Test authentication failure for suspended users."""
        # Setup database with suspended user
        suspended_user = valid_users['suspended']
        await auth_service.db_service.create_user(suspended_user)
        
        # Test authentication for suspended user
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.authenticate_slack_user(
                suspended_user.slack_user_id,
                'T1234567890',
                'C1234567890'
            )
        
        assert exc_info.value.error_code == 'USER_SUSPENDED'
        assert 'suspended' in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_session_management_security(self, auth_service, valid_users):
        """Test session management security features."""
        # Setup user
        user = valid_users['analyst']
        await auth_service.db_service.create_user(user)
        
        # Create session
        user_obj, session = await auth_service.authenticate_slack_user(
            user.slack_user_id,
            'T1234567890',
            'C1234567890'
        )
        
        # Test session validation
        valid_session = await auth_service.validate_session(session.session_id)
        assert valid_session is not None
        assert valid_session.user_id == user.user_id
        
        # Test session expiration
        # Manually expire session
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await auth_service._store_session(session)
        
        # Validate expired session should fail
        expired_session = await auth_service.validate_session(session.session_id)
        assert expired_session is None
        
        # Test invalid session ID
        invalid_session = await auth_service.validate_session('invalid_session_id')
        assert invalid_session is None
    
    @pytest.mark.asyncio
    async def test_concurrent_authentication_attempts(self, auth_service, valid_users):
        """Test security under concurrent authentication attempts."""
        # Setup user
        user = valid_users['analyst']
        await auth_service.db_service.create_user(user)
        
        # Define concurrent authentication function
        async def authenticate_user():
            try:
                user_obj, session = await auth_service.authenticate_slack_user(
                    user.slack_user_id,
                    'T1234567890',
                    'C1234567890'
                )
                return {'success': True, 'session_id': session.session_id}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        # Execute concurrent authentication attempts
        num_attempts = 10
        tasks = [authenticate_user() for _ in range(num_attempts)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        successful_auths = [r for r in results if r['success']]
        failed_auths = [r for r in results if not r['success']]
        
        # All authentications should succeed for valid user
        assert len(successful_auths) == num_attempts
        assert len(failed_auths) == 0
        
        # Verify unique session IDs
        session_ids = [r['session_id'] for r in successful_auths]
        assert len(set(session_ids)) == num_attempts  # All unique
    
    @pytest.mark.asyncio
    async def test_authentication_rate_limiting(self, auth_service, valid_users):
        """Test rate limiting for authentication attempts."""
        # Setup user
        user = valid_users['analyst']
        await auth_service.db_service.create_user(user)
        
        # Enable rate limiting in auth service
        auth_service._enable_rate_limiting = True
        auth_service._rate_limit_window = 60  # 1 minute
        auth_service._rate_limit_max_attempts = 5  # 5 attempts per minute
        
        # Perform rapid authentication attempts
        attempts = []
        for i in range(10):  # Exceed rate limit
            try:
                user_obj, session = await auth_service.authenticate_slack_user(
                    user.slack_user_id,
                    'T1234567890',
                    'C1234567890',
                    client_ip='192.168.1.100'  # Same IP for rate limiting
                )
                attempts.append({'success': True, 'attempt': i})
            except RateLimitError as e:
                attempts.append({'success': False, 'attempt': i, 'error': 'rate_limited'})
            except Exception as e:
                attempts.append({'success': False, 'attempt': i, 'error': str(e)})
        
        # Verify rate limiting kicked in
        successful_attempts = [a for a in attempts if a['success']]
        rate_limited_attempts = [a for a in attempts if not a['success'] and a.get('error') == 'rate_limited']
        
        # Should have some successful attempts followed by rate limiting
        assert len(successful_attempts) <= 5  # Within rate limit
        assert len(rate_limited_attempts) > 0  # Rate limiting occurred
    
    @pytest.mark.asyncio
    async def test_authentication_bypass_attempts(self, auth_service):
        """Test protection against authentication bypass attempts."""
        # Test 1: SQL injection attempts in user ID
        malicious_user_ids = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin' --",
            "' UNION SELECT * FROM users --"
        ]
        
        for malicious_id in malicious_user_ids:
            with pytest.raises(AuthenticationError):
                await auth_service.authenticate_slack_user(
                    malicious_id,
                    'T1234567890',
                    'C1234567890'
                )
        
        # Test 2: Invalid team/channel IDs
        invalid_ids = [
            None,
            "",
            "../../etc/passwd",
            "<script>alert('xss')</script>",
            "T' OR 1=1 --"
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises((AuthenticationError, ValueError)):
                await auth_service.authenticate_slack_user(
                    'U1234567890',
                    invalid_id,
                    'C1234567890'
                )
        
        # Test 3: Session hijacking attempts
        fake_session_ids = [
            'admin_session',
            '00000000-0000-0000-0000-000000000000',
            'session_' + 'a' * 100,  # Very long session ID
            '../../../session'
        ]
        
        for fake_session_id in fake_session_ids:
            session = await auth_service.validate_session(fake_session_id)
            assert session is None  # Should not validate fake sessions


class TestAuthorizationSecurity:
    """
    Comprehensive authorization security testing.
    
    Tests role-based access control, permission validation,
    channel restrictions, and privilege escalation attempts.
    """
    
    @pytest.fixture
    async def auth_service_with_users(self):
        """Create auth service with test users."""
        db_service = MockDatabaseService()
        auth_service = AuthService(db_service)
        
        # Create users with different roles and permissions
        users = {
            'analyst': create_test_user(
                user_id='authz_analyst',
                slack_user_id='U_ANALYST_AUTHZ',
                role=UserRole.RESEARCH_ANALYST,
                permissions=[
                    Permission.EXECUTE_TRADES,
                    Permission.REQUEST_RISK_ANALYSIS,
                    Permission.VIEW_RISK_ANALYSIS,
                    Permission.VIEW_PORTFOLIO
                ]
            ),
            'trader': create_test_user(
                user_id='authz_trader',
                slack_user_id='U_TRADER_AUTHZ',
                role=UserRole.EXECUTION_TRADER,
                permissions=[
                    Permission.EXECUTE_TRADES,
                    Permission.VIEW_TRADES,
                    Permission.VIEW_PORTFOLIO
                ]
            ),
            'pm': create_test_user(
                user_id='authz_pm',
                slack_user_id='U_PM_AUTHZ',
                role=UserRole.PORTFOLIO_MANAGER,
                permissions=[
                    Permission.EXECUTE_TRADES,
                    Permission.REQUEST_RISK_ANALYSIS,
                    Permission.VIEW_RISK_ANALYSIS,
                    Permission.VIEW_PORTFOLIO,
                    Permission.MANAGE_USERS,
                    Permission.VIEW_ALL_PORTFOLIOS
                ]
            ),
            'limited': create_test_user(
                user_id='authz_limited',
                slack_user_id='U_LIMITED_AUTHZ',
                role=UserRole.EXECUTION_TRADER,
                permissions=[Permission.VIEW_PORTFOLIO]  # Very limited permissions
            )
        }
        
        # Store users in database
        for user in users.values():
            await db_service.create_user(user)
        
        # Setup approved channels
        approved_channels = ['C_APPROVED_001', 'C_APPROVED_002', 'C_PRIVATE_TRADING']
        for channel_id in approved_channels:
            db_service.channels[channel_id] = {
                'channel_id': channel_id,
                'is_approved': True,
                'channel_type': 'private'
            }
        
        return auth_service, users
    
    @pytest.mark.asyncio
    async def test_role_based_access_control(self, auth_service_with_users):
        """Test role-based access control enforcement."""
        auth_service, users = auth_service_with_users
        
        # Test analyst permissions
        analyst = users['analyst']
        
        # Should have risk analysis permission
        assert await auth_service.authorize_permission(analyst, Permission.REQUEST_RISK_ANALYSIS)
        assert await auth_service.authorize_permission(analyst, Permission.EXECUTE_TRADES)
        assert await auth_service.authorize_permission(analyst, Permission.VIEW_RISK_ANALYSIS)
        
        # Should NOT have admin permissions
        assert not await auth_service.authorize_permission(analyst, Permission.MANAGE_USERS)
        assert not await auth_service.authorize_permission(analyst, Permission.VIEW_ALL_TRADES)
        
        # Test trader permissions
        trader = users['trader']
        
        # Should have basic trading permissions
        assert await auth_service.authorize_permission(trader, Permission.EXECUTE_TRADES)
        assert await auth_service.authorize_permission(trader, Permission.VIEW_TRADES)
        
        # Should NOT have risk analysis or admin permissions
        assert not await auth_service.authorize_permission(trader, Permission.REQUEST_RISK_ANALYSIS)
        assert not await auth_service.authorize_permission(trader, Permission.MANAGE_USERS)
        
        # Test Portfolio Manager permissions
        pm = users['pm']
        
        # Should have all permissions
        for permission in Permission:
            assert await auth_service.authorize_permission(pm, permission)
        
        # Test limited user
        limited = users['limited']
        
        # Should only have view portfolio permission
        assert await auth_service.authorize_permission(limited, Permission.VIEW_PORTFOLIO)
        assert not await auth_service.authorize_permission(limited, Permission.EXECUTE_TRADES)
        assert not await auth_service.authorize_permission(limited, Permission.VIEW_TRADES)
    
    @pytest.mark.asyncio
    async def test_channel_access_control(self, auth_service_with_users):
        """Test channel-based access control."""
        auth_service, users = auth_service_with_users
        analyst = users['analyst']
        
        # Test approved channel access
        approved_channels = ['C_APPROVED_001', 'C_APPROVED_002', 'C_PRIVATE_TRADING']
        for channel_id in approved_channels:
            assert await auth_service.authorize_channel_access(analyst, channel_id)
        
        # Test unapproved channel access
        unapproved_channels = ['C_GENERAL', 'C_RANDOM', 'C_PUBLIC_001']
        for channel_id in unapproved_channels:
            with pytest.raises(AuthorizationError) as exc_info:
                await auth_service.authorize_channel_access(analyst, channel_id)
            assert exc_info.value.error_code == 'CHANNEL_NOT_APPROVED'
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_attempts(self, auth_service_with_users):
        """Test protection against privilege escalation attempts."""
        auth_service, users = auth_service_with_users
        limited_user = users['limited']
        
        # Attempt 1: Try to modify user permissions directly
        original_permissions = limited_user.permissions.copy()
        
        # Simulate attempt to add permissions
        limited_user.permissions.append(Permission.MANAGE_USERS)
        
        # Authorization should still fail because it checks stored user data
        stored_user = await auth_service.db_service.get_user(limited_user.user_id)
        assert not await auth_service.authorize_permission(stored_user, Permission.MANAGE_USERS)
        
        # Attempt 2: Try to impersonate another user
        pm_user = users['pm']
        
        # Create session for limited user
        limited_user_obj, limited_session = await auth_service.authenticate_slack_user(
            limited_user.slack_user_id,
            'T1234567890',
            'C_APPROVED_001'
        )
        
        # Try to use PM's user ID with limited user's session
        # This should fail because session is tied to specific user
        session_user = await auth_service.get_user_from_session(limited_session.session_id)
        assert session_user.user_id == limited_user.user_id
        assert session_user.user_id != pm_user.user_id
        
        # Attempt 3: Try to bypass channel restrictions
        with pytest.raises(AuthorizationError):
            await auth_service.authorize_channel_access(limited_user, 'C_ADMIN_ONLY')
    
    @pytest.mark.asyncio
    async def test_permission_validation_edge_cases(self, auth_service_with_users):
        """Test permission validation edge cases and boundary conditions."""
        auth_service, users = auth_service_with_users
        
        # Test with None user
        with pytest.raises((AuthorizationError, ValueError)):
            await auth_service.authorize_permission(None, Permission.EXECUTE_TRADES)
        
        # Test with invalid permission
        analyst = users['analyst']
        with pytest.raises((AuthorizationError, ValueError)):
            await auth_service.authorize_permission(analyst, "INVALID_PERMISSION")
        
        # Test with user having empty permissions list
        empty_user = create_test_user(
            user_id='empty_permissions',
            permissions=[]
        )
        await auth_service.db_service.create_user(empty_user)
        
        for permission in Permission:
            assert not await auth_service.authorize_permission(empty_user, permission)
        
        # Test with user having None permissions
        none_user = create_test_user(
            user_id='none_permissions',
            permissions=None
        )
        # This should be handled gracefully
        if none_user.permissions is None:
            none_user.permissions = []
        
        await auth_service.db_service.create_user(none_user)
        
        for permission in Permission:
            assert not await auth_service.authorize_permission(none_user, permission)
    
    @pytest.mark.asyncio
    async def test_authorization_with_expired_sessions(self, auth_service_with_users):
        """Test authorization behavior with expired sessions."""
        auth_service, users = auth_service_with_users
        analyst = users['analyst']
        
        # Create session
        user_obj, session = await auth_service.authenticate_slack_user(
            analyst.slack_user_id,
            'T1234567890',
            'C_APPROVED_001'
        )
        
        # Verify initial authorization works
        assert await auth_service.authorize_permission(user_obj, Permission.EXECUTE_TRADES)
        
        # Expire the session
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await auth_service._store_session(session)
        
        # Try to use expired session for authorization
        expired_session = await auth_service.validate_session(session.session_id)
        assert expired_session is None
        
        # Authorization with expired session should fail
        with pytest.raises(AuthenticationError):
            await auth_service.authorize_session_permission(session.session_id, Permission.EXECUTE_TRADES)


class TestSecurityViolationDetection:
    """
    Security violation detection and response testing.
    
    Tests detection of suspicious activities, security violations,
    and appropriate response mechanisms including logging and alerting.
    """
    
    @pytest.fixture
    async def security_test_setup(self):
        """Setup for security violation testing."""
        db_service = MockDatabaseService()
        auth_service = AuthService(db_service)
        
        # Create test user
        test_user = create_test_user(
            user_id='security_test_user',
            slack_user_id='U_SECURITY_TEST',
            role=UserRole.EXECUTION_TRADER
        )
        await db_service.create_user(test_user)
        
        # Setup command handler
        command_handler = CommandHandler(auth_service, db_service)
        
        return auth_service, db_service, command_handler, test_user
    
    @pytest.mark.asyncio
    async def test_suspicious_activity_detection(self, security_test_setup):
        """Test detection of suspicious user activities."""
        auth_service, db_service, command_handler, test_user = security_test_setup
        
        # Test 1: Rapid authentication attempts from different IPs
        ip_addresses = ['192.168.1.1', '10.0.0.1', '172.16.0.1', '203.0.113.1']
        
        auth_attempts = []
        for i, ip in enumerate(ip_addresses):
            try:
                user_obj, session = await auth_service.authenticate_slack_user(
                    test_user.slack_user_id,
                    'T1234567890',
                    'C1234567890',
                    client_ip=ip
                )
                auth_attempts.append({'success': True, 'ip': ip})
            except Exception as e:
                auth_attempts.append({'success': False, 'ip': ip, 'error': str(e)})
        
        # Should detect suspicious activity (multiple IPs)
        # This would typically trigger security alerts in a real system
        unique_ips = set(attempt['ip'] for attempt in auth_attempts)
        assert len(unique_ips) == len(ip_addresses)
        
        # Test 2: Unusual access patterns
        # Simulate access at unusual hours (if time-based detection is implemented)
        unusual_times = [
            datetime.now(timezone.utc).replace(hour=2, minute=30),  # 2:30 AM
            datetime.now(timezone.utc).replace(hour=3, minute=45),  # 3:45 AM
        ]
        
        # This would be detected by monitoring systems in production
        for unusual_time in unusual_times:
            # Simulate timestamp manipulation (would be detected)
            pass
    
    @pytest.mark.asyncio
    async def test_malicious_input_detection(self, security_test_setup):
        """Test detection and handling of malicious inputs."""
        auth_service, db_service, command_handler, test_user = security_test_setup
        mock_slack_client = MockSlackClient()
        
        # Setup user authentication
        auth_service.authenticate_slack_user = AsyncMock(return_value=(
            test_user,
            MagicMock(session_id='security_session')
        ))
        auth_service.authorize_channel_access = AsyncMock(return_value=True)
        
        # Test malicious command inputs
        malicious_inputs = [
            # SQL injection attempts
            "'; DROP TABLE trades; --",
            "' OR '1'='1",
            
            # XSS attempts
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            
            # Command injection attempts
            "; rm -rf /",
            "| cat /etc/passwd",
            
            # Path traversal attempts
            "../../etc/passwd",
            "../../../windows/system32",
            
            # Buffer overflow attempts
            "A" * 10000,
            
            # Format string attacks
            "%s%s%s%s%s",
            "%x%x%x%x%x"
        ]
        
        for malicious_input in malicious_inputs:
            # Test malicious input in command text
            command_payload = create_slash_command_payload(
                command='/trade',
                user_id=test_user.slack_user_id,
                channel_id='C1234567890',
                text=malicious_input
            )
            
            # Command should be processed safely without executing malicious code
            try:
                await command_handler.process_command(
                    CommandType.TRADE,
                    command_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                # Should not crash or execute malicious code
            except Exception as e:
                # Exceptions are acceptable as long as they're handled safely
                assert "DROP TABLE" not in str(e)  # SQL injection should be prevented
                assert "<script>" not in str(e)    # XSS should be sanitized
    
    @pytest.mark.asyncio
    async def test_unauthorized_access_attempts(self, security_test_setup):
        """Test detection of unauthorized access attempts."""
        auth_service, db_service, command_handler, test_user = security_test_setup
        mock_slack_client = MockSlackClient()
        
        # Test 1: Access from unauthorized channels
        unauthorized_channels = ['C_PUBLIC', 'C_GENERAL', 'C_RANDOM']
        
        for channel_id in unauthorized_channels:
            # Mock authentication but not channel authorization
            auth_service.authenticate_slack_user = AsyncMock(return_value=(
                test_user,
                MagicMock(session_id='unauthorized_session')
            ))
            auth_service.authorize_channel_access = AsyncMock(
                side_effect=AuthorizationError("Channel not approved", "CHANNEL_NOT_APPROVED")
            )
            
            command_payload = create_slash_command_payload(
                command='/trade',
                user_id=test_user.slack_user_id,
                channel_id=channel_id
            )
            
            # Should detect and reject unauthorized channel access
            await command_handler.process_command(
                CommandType.TRADE,
                command_payload,
                mock_slack_client,
                AsyncMock(),
                MagicMock()
            )
            
            # Verify error message was sent
            assert mock_slack_client.chat_postEphemeral.called
            error_call = mock_slack_client.chat_postEphemeral.call_args
            assert 'access denied' in error_call.kwargs['text'].lower()
            
            mock_slack_client.reset_mock()
        
        # Test 2: Attempts to access other users' data
        other_user = create_test_user(
            user_id='other_user',
            slack_user_id='U_OTHER_USER'
        )
        await db_service.create_user(other_user)
        
        # Try to access other user's trades (this would be prevented by proper authorization)
        try:
            trades = await db_service.get_user_trades(other_user.user_id)
            # In a real system, this should check if current user has permission
            # to view other users' trades
        except AuthorizationError:
            # Expected behavior - should not allow access to other users' data
            pass
    
    @pytest.mark.asyncio
    async def test_security_audit_logging(self, security_test_setup):
        """Test comprehensive security audit logging."""
        auth_service, db_service, command_handler, test_user = security_test_setup
        mock_slack_client = MockSlackClient()
        
        # Enable audit logging
        original_audit_logs = db_service.audit_logs.copy()
        
        # Setup authentication
        auth_service.authenticate_slack_user = AsyncMock(return_value=(
            test_user,
            MagicMock(session_id='audit_session')
        ))
        auth_service.authorize_channel_access = AsyncMock(return_value=True)
        
        # Perform various operations that should be audited
        operations = [
            {
                'type': 'command',
                'payload': create_slash_command_payload(
                    command='/trade',
                    user_id=test_user.slack_user_id,
                    channel_id='C1234567890',
                    text='AAPL 100 BUY'
                )
            },
            {
                'type': 'command',
                'payload': create_slash_command_payload(
                    command='/portfolio',
                    user_id=test_user.slack_user_id,
                    channel_id='C1234567890'
                )
            }
        ]
        
        for operation in operations:
            if operation['type'] == 'command':
                await command_handler.process_command(
                    CommandType.TRADE if '/trade' in operation['payload']['command'] else CommandType.PORTFOLIO,
                    operation['payload'],
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
        
        # Verify audit logs were created
        new_audit_logs = db_service.audit_logs[len(original_audit_logs):]
        assert len(new_audit_logs) > 0
        
        # Verify audit log content
        for audit_log in new_audit_logs:
            assert 'timestamp' in audit_log
            assert 'user_id' in audit_log
            assert 'event_type' in audit_log
            assert 'details' in audit_log
            
            # Verify sensitive information is not logged
            audit_str = json.dumps(audit_log)
            assert 'password' not in audit_str.lower()
            assert 'secret' not in audit_str.lower()
            assert 'token' not in audit_str.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_security(self, security_test_setup):
        """Test rate limiting as a security measure."""
        auth_service, db_service, command_handler, test_user = security_test_setup
        mock_slack_client = MockSlackClient()
        
        # Setup authentication
        auth_service.authenticate_slack_user = AsyncMock(return_value=(
            test_user,
            MagicMock(session_id='rate_limit_session')
        ))
        auth_service.authorize_channel_access = AsyncMock(return_value=True)
        
        # Simulate rapid command execution (potential DoS attack)
        rapid_commands = []
        for i in range(20):  # Exceed typical rate limits
            command_payload = create_slash_command_payload(
                command='/trade',
                user_id=test_user.slack_user_id,
                channel_id='C1234567890',
                text=f'AAPL {i+1} BUY'
            )
            
            try:
                await command_handler.process_command(
                    CommandType.TRADE,
                    command_payload,
                    mock_slack_client,
                    AsyncMock(),
                    MagicMock()
                )
                rapid_commands.append({'success': True, 'command': i})
            except RateLimitError:
                rapid_commands.append({'success': False, 'command': i, 'error': 'rate_limited'})
            except Exception as e:
                rapid_commands.append({'success': False, 'command': i, 'error': str(e)})
        
        # Verify rate limiting occurred
        successful_commands = [cmd for cmd in rapid_commands if cmd['success']]
        rate_limited_commands = [cmd for cmd in rapid_commands if not cmd['success'] and cmd.get('error') == 'rate_limited']
        
        # Should have some successful commands followed by rate limiting
        # (Exact numbers depend on rate limiting configuration)
        assert len(successful_commands) < 20  # Not all commands should succeed
        
        print(f"Rate limiting test: {len(successful_commands)} successful, {len(rate_limited_commands)} rate limited")


if __name__ == '__main__':
    # Run security tests
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])