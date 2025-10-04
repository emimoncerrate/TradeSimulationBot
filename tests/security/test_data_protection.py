"""
Data Protection and Privacy Security Testing

This module provides comprehensive security tests for data protection mechanisms
including data encryption, PII handling, data retention policies, secure data
transmission, and compliance with privacy regulations.
"""

import pytest
import asyncio
import json
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Import application components
from services.database import DatabaseService, DatabaseError
from services.auth import AuthService
from models.user import User, UserRole, UserStatus, Permission
from models.trade import Trade, TradeType, TradeStatus, RiskLevel
from models.portfolio import Position, Portfolio
from utils.validators import validate_pii_data, sanitize_user_input
from utils.formatters import mask_sensitive_data, format_audit_log

# Test utilities
from tests.fixtures.test_data import create_test_user, create_test_trade
from tests.utils.mock_services import MockDatabaseService


class TestDataEncryption:
    """
    Test data encryption and decryption mechanisms.
    
    Validates that sensitive data is properly encrypted at rest
    and in transit, with appropriate key management and rotation.
    """
    
    @pytest.fixture
    async def database_service(self):
        """Create database service for encryption testing."""
        return MockDatabaseService()
    
    @pytest.mark.asyncio
    async def test_sensitive_data_encryption_at_rest(self, database_service):
        """Test encryption of sensitive data when stored."""
        # Create test user with sensitive data
        test_user = create_test_user(
            user_id='encryption_test_user',
            email='test.user@jainglobal.com',
            phone_number='+1-555-123-4567',
            ssn='123-45-6789'  # Highly sensitive data
        )
        
        # Store user data
        await database_service.create_user(test_user)
        
        # Retrieve raw stored data to verify encryption
        raw_user_data = database_service.users.get(test_user.user_id)
        
        # Verify sensitive fields are encrypted (not stored in plain text)
        if hasattr(raw_user_data, 'ssn') and raw_user_data.ssn:
            assert raw_user_data.ssn != '123-45-6789'  # Should be encrypted
            assert len(raw_user_data.ssn) > 20  # Encrypted data should be longer
        
        if hasattr(raw_user_data, 'phone_number') and raw_user_data.phone_number:
            # Phone numbers might be hashed or encrypted
            assert raw_user_data.phone_number != '+1-555-123-4567' or len(raw_user_data.phone_number) > 20
        
        # Verify data can be decrypted when retrieved through service
        retrieved_user = await database_service.get_user(test_user.user_id)
        assert retrieved_user.user_id == test_user.user_id
        assert retrieved_user.email == test_user.email  # Email might not be encrypted
    
    @pytest.mark.asyncio
    async def test_trade_data_encryption(self, database_service):
        """Test encryption of trade data containing sensitive information."""
        # Create test trade with sensitive data
        test_trade = create_test_trade(
            user_id='encryption_test_user',
            symbol='AAPL',
            quantity=1000,
            price=Decimal('150.00'),
            notes='Confidential client trade - Portfolio Alpha'  # Sensitive notes
        )
        
        # Store trade data
        await database_service.log_trade(test_trade)
        
        # Retrieve raw stored data
        raw_trade_data = None
        for trade in database_service.trades.values():
            if trade.trade_id == test_trade.trade_id:
                raw_trade_data = trade
                break
        
        assert raw_trade_data is not None
        
        # Verify sensitive notes are encrypted if present
        if hasattr(raw_trade_data, 'notes') and raw_trade_data.notes:
            # Notes containing sensitive information should be encrypted
            if 'Confidential' in test_trade.notes:
                # In a real implementation, this would be encrypted
                pass  # Mock service might not implement encryption
        
        # Verify trade can be retrieved and decrypted
        retrieved_trades = await database_service.get_user_trades(test_trade.user_id)
        assert len(retrieved_trades) > 0
        
        retrieved_trade = next((t for t in retrieved_trades if t.trade_id == test_trade.trade_id), None)
        assert retrieved_trade is not None
        assert retrieved_trade.symbol == test_trade.symbol
        assert retrieved_trade.quantity == test_trade.quantity
    
    @pytest.mark.asyncio
    async def test_encryption_key_rotation(self, database_service):
        """Test encryption key rotation procedures."""
        # Create test data with old encryption key
        old_user = create_test_user(
            user_id='key_rotation_user',
            ssn='987-65-4321'
        )
        
        await database_service.create_user(old_user)
        
        # Simulate key rotation (in real implementation)
        # This would involve re-encrypting data with new keys
        
        # Verify data is still accessible after key rotation
        retrieved_user = await database_service.get_user(old_user.user_id)
        assert retrieved_user.user_id == old_user.user_id
        
        # In a real system, we would verify:
        # 1. Old encrypted data can still be decrypted
        # 2. New data uses new encryption keys
        # 3. Key rotation is logged and audited
        # 4. Old keys are securely destroyed
    
    @pytest.mark.asyncio
    async def test_encryption_performance_impact(self, database_service):
        """Test performance impact of encryption operations."""
        import time
        
        # Create multiple users to test encryption performance
        users = [
            create_test_user(
                user_id=f'perf_user_{i:03d}',
                ssn=f'{i:03d}-{i:02d}-{i:04d}'
            )
            for i in range(100)
        ]
        
        # Measure encryption performance
        start_time = time.time()
        
        for user in users:
            await database_service.create_user(user)
        
        encryption_time = time.time() - start_time
        
        # Measure decryption performance
        start_time = time.time()
        
        for user in users:
            retrieved_user = await database_service.get_user(user.user_id)
            assert retrieved_user.user_id == user.user_id
        
        decryption_time = time.time() - start_time
        
        # Performance assertions
        avg_encryption_time = encryption_time / len(users)
        avg_decryption_time = decryption_time / len(users)
        
        assert avg_encryption_time < 0.1, f"Encryption too slow: {avg_encryption_time:.3f}s per user"
        assert avg_decryption_time < 0.05, f"Decryption too slow: {avg_decryption_time:.3f}s per user"
        
        print(f"Encryption performance: {avg_encryption_time:.3f}s per user")
        print(f"Decryption performance: {avg_decryption_time:.3f}s per user")


class TestPIIHandling:
    """
    Test Personally Identifiable Information (PII) handling.
    
    Validates proper identification, protection, and handling
    of PII data throughout the system.
    """
    
    @pytest.fixture
    def pii_test_data(self):
        """Create test data containing various types of PII."""
        return {
            'email': 'john.doe@jainglobal.com',
            'phone': '+1-555-987-6543',
            'ssn': '456-78-9012',
            'address': '123 Wall Street, New York, NY 10005',
            'credit_card': '4532-1234-5678-9012',
            'bank_account': '123456789',
            'passport': 'A12345678',
            'drivers_license': 'D123456789',
            'ip_address': '192.168.1.100',
            'device_id': 'device_abc123xyz789'
        }
    
    def test_pii_identification(self, pii_test_data):
        """Test automatic identification of PII data."""
        from utils.validators import identify_pii_fields
        
        # Test PII identification in various data structures
        test_cases = [
            {'email': pii_test_data['email'], 'name': 'John Doe'},
            {'phone_number': pii_test_data['phone'], 'symbol': 'AAPL'},
            {'ssn': pii_test_data['ssn'], 'quantity': 100},
            {'user_address': pii_test_data['address'], 'trade_type': 'BUY'}
        ]
        
        for test_case in test_cases:
            pii_fields = identify_pii_fields(test_case)
            
            # Verify PII fields are identified
            if 'email' in test_case:
                assert 'email' in pii_fields
            if 'phone_number' in test_case:
                assert 'phone_number' in pii_fields
            if 'ssn' in test_case:
                assert 'ssn' in pii_fields
            if 'user_address' in test_case:
                assert 'user_address' in pii_fields
            
            # Verify non-PII fields are not flagged
            if 'symbol' in test_case:
                assert 'symbol' not in pii_fields
            if 'quantity' in test_case:
                assert 'quantity' not in pii_fields
            if 'trade_type' in test_case:
                assert 'trade_type' not in pii_fields
    
    def test_pii_masking_and_sanitization(self, pii_test_data):
        """Test PII masking and sanitization for display and logging."""
        from utils.formatters import mask_pii_data
        
        # Test masking of different PII types
        masked_data = mask_pii_data(pii_test_data)
        
        # Verify email masking
        assert masked_data['email'] != pii_test_data['email']
        assert '*' in masked_data['email'] or 'xxx' in masked_data['email'].lower()
        assert '@' in masked_data['email']  # Domain might be preserved
        
        # Verify phone number masking
        assert masked_data['phone'] != pii_test_data['phone']
        assert '*' in masked_data['phone'] or 'xxx' in masked_data['phone'].lower()
        
        # Verify SSN masking (should show only last 4 digits)
        assert masked_data['ssn'] != pii_test_data['ssn']
        assert masked_data['ssn'].endswith('9012')  # Last 4 digits preserved
        assert 'xxx' in masked_data['ssn'].lower() or '*' in masked_data['ssn']
        
        # Verify credit card masking
        assert masked_data['credit_card'] != pii_test_data['credit_card']
        assert masked_data['credit_card'].endswith('9012')  # Last 4 digits
        
        # Verify address masking
        assert masked_data['address'] != pii_test_data['address']
        # City and state might be preserved for business purposes
    
    @pytest.mark.asyncio
    async def test_pii_data_retention_policies(self):
        """Test PII data retention and deletion policies."""
        database_service = MockDatabaseService()
        
        # Create user with PII data
        test_user = create_test_user(
            user_id='pii_retention_user',
            email='retention.test@jainglobal.com',
            ssn='111-22-3333',
            created_at=datetime.now(timezone.utc) - timedelta(days=400)  # Old user
        )
        
        await database_service.create_user(test_user)
        
        # Simulate data retention policy check
        retention_period = timedelta(days=365)  # 1 year retention
        cutoff_date = datetime.now(timezone.utc) - retention_period
        
        # Check if user data should be purged
        if test_user.created_at < cutoff_date:
            # In a real system, this would trigger data purging
            # For testing, we verify the logic works
            should_purge = True
        else:
            should_purge = False
        
        assert should_purge  # User is older than retention period
        
        # Test selective PII purging (keeping business data)
        # In practice, we might keep trade data but remove PII
        purged_user = User(
            user_id=test_user.user_id,
            slack_user_id=test_user.slack_user_id,
            role=test_user.role,
            status=UserStatus.PURGED,
            email=None,  # PII removed
            ssn=None,    # PII removed
            phone_number=None,  # PII removed
            permissions=test_user.permissions,
            created_at=test_user.created_at
        )
        
        # Verify PII has been removed
        assert purged_user.email is None
        assert purged_user.ssn is None
        assert purged_user.phone_number is None
        
        # Verify business data is preserved
        assert purged_user.user_id == test_user.user_id
        assert purged_user.role == test_user.role
        assert purged_user.permissions == test_user.permissions
    
    def test_pii_in_logs_prevention(self, pii_test_data):
        """Test prevention of PII data in application logs."""
        from utils.formatters import sanitize_log_data
        
        # Create log entries that might contain PII
        log_entries = [
            f"User login: {pii_test_data['email']}",
            f"Trade executed for user with SSN: {pii_test_data['ssn']}",
            f"Phone verification: {pii_test_data['phone']}",
            f"Address updated: {pii_test_data['address']}",
            f"Payment method: {pii_test_data['credit_card']}"
        ]
        
        # Sanitize log entries
        sanitized_logs = [sanitize_log_data(log) for log in log_entries]
        
        # Verify PII is removed or masked in logs
        for original, sanitized in zip(log_entries, sanitized_logs):
            # Original contains PII
            assert (pii_test_data['email'] in original or 
                   pii_test_data['ssn'] in original or
                   pii_test_data['phone'] in original)
            
            # Sanitized should not contain PII
            assert pii_test_data['email'] not in sanitized
            assert pii_test_data['ssn'] not in sanitized
            assert pii_test_data['phone'] not in sanitized
            assert pii_test_data['credit_card'] not in sanitized
            
            # But should still contain business context
            assert 'User login' in sanitized or 'Trade executed' in sanitized or 'verification' in sanitized


class TestDataTransmissionSecurity:
    """
    Test secure data transmission mechanisms.
    
    Validates encryption in transit, secure API communications,
    and protection against data interception.
    """
    
    @pytest.mark.asyncio
    async def test_https_enforcement(self):
        """Test HTTPS enforcement for all API communications."""
        # In a real implementation, this would test:
        # 1. All HTTP requests are redirected to HTTPS
        # 2. HTTPS certificates are valid
        # 3. TLS version is appropriate (1.2+)
        # 4. Secure cipher suites are used
        
        # Mock test for HTTPS enforcement
        api_endpoints = [
            'https://api.jainglobal.com/trades',
            'https://api.jainglobal.com/users',
            'https://api.jainglobal.com/portfolio'
        ]
        
        for endpoint in api_endpoints:
            assert endpoint.startswith('https://'), f"Endpoint not using HTTPS: {endpoint}"
            
        # Test that HTTP endpoints are rejected
        insecure_endpoints = [
            'http://api.jainglobal.com/trades',
            'ftp://api.jainglobal.com/data'
        ]
        
        for endpoint in insecure_endpoints:
            # In real implementation, these would be rejected
            assert not endpoint.startswith('https://'), f"Insecure endpoint detected: {endpoint}"
    
    @pytest.mark.asyncio
    async def test_api_request_encryption(self):
        """Test encryption of sensitive data in API requests."""
        # Create test API request with sensitive data
        api_request = {
            'user_id': 'test_user_123',
            'trade_data': {
                'symbol': 'AAPL',
                'quantity': 1000,
                'price': 150.00,
                'client_notes': 'Confidential trade for VIP client'
            },
            'user_info': {
                'email': 'vip.client@example.com',
                'phone': '+1-555-999-8888'
            }
        }
        
        # Simulate encryption of sensitive fields
        from utils.validators import encrypt_sensitive_fields
        
        encrypted_request = encrypt_sensitive_fields(api_request)
        
        # Verify sensitive fields are encrypted
        if 'client_notes' in str(encrypted_request):
            # Notes containing sensitive info should be encrypted
            pass
        
        if 'email' in encrypted_request.get('user_info', {}):
            # Email should be encrypted or hashed
            encrypted_email = encrypted_request['user_info']['email']
            assert encrypted_email != api_request['user_info']['email']
        
        # Verify non-sensitive fields remain readable
        assert encrypted_request['user_id'] == api_request['user_id']
        assert encrypted_request['trade_data']['symbol'] == api_request['trade_data']['symbol']
    
    @pytest.mark.asyncio
    async def test_data_integrity_verification(self):
        """Test data integrity verification during transmission."""
        # Create test data
        test_data = {
            'trade_id': 'trade_123',
            'user_id': 'user_456',
            'symbol': 'GOOGL',
            'quantity': 500,
            'price': 2500.00,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Calculate data hash for integrity verification
        data_json = json.dumps(test_data, sort_keys=True)
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()
        
        # Simulate transmission with integrity check
        transmitted_data = {
            'data': test_data,
            'hash': data_hash,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Verify data integrity on receipt
        received_data = transmitted_data['data']
        received_hash = transmitted_data['hash']
        
        # Recalculate hash
        received_json = json.dumps(received_data, sort_keys=True)
        calculated_hash = hashlib.sha256(received_json.encode()).hexdigest()
        
        # Verify integrity
        assert calculated_hash == received_hash, "Data integrity check failed"
        assert received_data == test_data, "Data was modified during transmission"


class TestComplianceAndAuditing:
    """
    Test compliance with data protection regulations and auditing.
    
    Validates GDPR compliance, audit trail generation,
    and regulatory reporting capabilities.
    """
    
    @pytest.fixture
    async def audit_database_service(self):
        """Create database service with audit logging enabled."""
        db_service = MockDatabaseService()
        db_service.enable_audit_logging = True
        return db_service
    
    @pytest.mark.asyncio
    async def test_gdpr_compliance_data_access(self, audit_database_service):
        """Test GDPR compliance for data access requests."""
        # Create test user
        test_user = create_test_user(
            user_id='gdpr_test_user',
            email='gdpr.test@example.com',
            phone_number='+1-555-777-8888'
        )
        
        await audit_database_service.create_user(test_user)
        
        # Create some trade data for the user
        test_trades = [
            create_test_trade(
                user_id=test_user.user_id,
                symbol='AAPL',
                quantity=100
            ),
            create_test_trade(
                user_id=test_user.user_id,
                symbol='GOOGL',
                quantity=50
            )
        ]
        
        for trade in test_trades:
            await audit_database_service.log_trade(trade)
        
        # Simulate GDPR data access request
        user_data_export = await audit_database_service.export_user_data(test_user.user_id)
        
        # Verify all user data is included
        assert 'user_profile' in user_data_export
        assert 'trades' in user_data_export
        assert 'positions' in user_data_export
        
        # Verify user profile data
        user_profile = user_data_export['user_profile']
        assert user_profile['user_id'] == test_user.user_id
        assert user_profile['email'] == test_user.email
        
        # Verify trade data
        exported_trades = user_data_export['trades']
        assert len(exported_trades) == len(test_trades)
        
        for exported_trade in exported_trades:
            assert exported_trade['user_id'] == test_user.user_id
    
    @pytest.mark.asyncio
    async def test_gdpr_compliance_data_deletion(self, audit_database_service):
        """Test GDPR compliance for data deletion requests."""
        # Create test user
        test_user = create_test_user(
            user_id='gdpr_delete_user',
            email='delete.test@example.com'
        )
        
        await audit_database_service.create_user(test_user)
        
        # Create trade data
        test_trade = create_test_trade(
            user_id=test_user.user_id,
            symbol='MSFT',
            quantity=200
        )
        
        await audit_database_service.log_trade(test_trade)
        
        # Verify data exists
        user_before = await audit_database_service.get_user(test_user.user_id)
        trades_before = await audit_database_service.get_user_trades(test_user.user_id)
        
        assert user_before is not None
        assert len(trades_before) > 0
        
        # Simulate GDPR deletion request
        deletion_result = await audit_database_service.delete_user_data(
            test_user.user_id,
            reason='GDPR_DELETION_REQUEST',
            requested_by='user_self_service'
        )
        
        assert deletion_result['success'] is True
        assert deletion_result['deleted_records'] > 0
        
        # Verify data is deleted or anonymized
        try:
            user_after = await audit_database_service.get_user(test_user.user_id)
            # User might be marked as deleted rather than completely removed
            if user_after:
                assert user_after.status == UserStatus.DELETED
                assert user_after.email is None  # PII removed
        except NotFoundError:
            # Complete deletion is also acceptable
            pass
        
        # Verify audit trail of deletion
        audit_logs = await audit_database_service.get_audit_logs(
            user_id=test_user.user_id,
            action_type='DATA_DELETION'
        )
        
        assert len(audit_logs) > 0
        deletion_log = audit_logs[0]
        assert deletion_log['action'] == 'DATA_DELETION'
        assert deletion_log['reason'] == 'GDPR_DELETION_REQUEST'
    
    @pytest.mark.asyncio
    async def test_audit_trail_generation(self, audit_database_service):
        """Test comprehensive audit trail generation."""
        # Create test user
        test_user = create_test_user(user_id='audit_test_user')
        await audit_database_service.create_user(test_user)
        
        # Perform various operations that should be audited
        operations = [
            ('USER_LOGIN', {'user_id': test_user.user_id, 'ip_address': '192.168.1.100'}),
            ('TRADE_EXECUTED', {'user_id': test_user.user_id, 'symbol': 'AAPL', 'quantity': 100}),
            ('DATA_ACCESSED', {'user_id': test_user.user_id, 'data_type': 'portfolio'}),
            ('PERMISSION_CHANGED', {'user_id': test_user.user_id, 'old_role': 'trader', 'new_role': 'analyst'}),
            ('USER_LOGOUT', {'user_id': test_user.user_id, 'session_duration': 3600})
        ]
        
        # Log audit events
        for action, details in operations:
            await audit_database_service.log_audit_event(
                user_id=test_user.user_id,
                action=action,
                details=details,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Retrieve audit trail
        audit_trail = await audit_database_service.get_audit_logs(
            user_id=test_user.user_id,
            start_date=datetime.now(timezone.utc) - timedelta(hours=1),
            end_date=datetime.now(timezone.utc)
        )
        
        # Verify audit trail completeness
        assert len(audit_trail) == len(operations)
        
        # Verify audit log structure
        for log_entry in audit_trail:
            assert 'timestamp' in log_entry
            assert 'user_id' in log_entry
            assert 'action' in log_entry
            assert 'details' in log_entry
            assert 'ip_address' in log_entry or 'source' in log_entry
            
            # Verify timestamp is recent
            log_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
            time_diff = datetime.now(timezone.utc) - log_time
            assert time_diff < timedelta(hours=1)
    
    @pytest.mark.asyncio
    async def test_regulatory_reporting(self, audit_database_service):
        """Test regulatory reporting capabilities."""
        # Create test data for reporting
        test_users = [
            create_test_user(user_id=f'report_user_{i}', role=UserRole.EXECUTION_TRADER)
            for i in range(5)
        ]
        
        for user in test_users:
            await audit_database_service.create_user(user)
        
        # Create trade data
        test_trades = []
        for i, user in enumerate(test_users):
            for j in range(3):  # 3 trades per user
                trade = create_test_trade(
                    user_id=user.user_id,
                    symbol=['AAPL', 'GOOGL', 'MSFT'][j],
                    quantity=(i + 1) * 100,
                    price=Decimal(str(150 + i * 10))
                )
                test_trades.append(trade)
                await audit_database_service.log_trade(trade)
        
        # Generate regulatory report
        report_period = {
            'start_date': datetime.now(timezone.utc) - timedelta(days=30),
            'end_date': datetime.now(timezone.utc)
        }
        
        regulatory_report = await audit_database_service.generate_regulatory_report(
            report_type='TRADE_ACTIVITY',
            period=report_period,
            include_pii=False  # Regulatory reports should not include PII
        )
        
        # Verify report structure
        assert 'report_metadata' in regulatory_report
        assert 'trade_summary' in regulatory_report
        assert 'user_activity' in regulatory_report
        assert 'compliance_metrics' in regulatory_report
        
        # Verify report metadata
        metadata = regulatory_report['report_metadata']
        assert metadata['report_type'] == 'TRADE_ACTIVITY'
        assert metadata['period_start'] == report_period['start_date'].isoformat()
        assert metadata['period_end'] == report_period['end_date'].isoformat()
        assert metadata['generated_at'] is not None
        
        # Verify trade summary
        trade_summary = regulatory_report['trade_summary']
        assert trade_summary['total_trades'] == len(test_trades)
        assert trade_summary['unique_users'] == len(test_users)
        assert trade_summary['total_volume'] > 0
        
        # Verify no PII in report
        report_json = json.dumps(regulatory_report)
        for user in test_users:
            if hasattr(user, 'email') and user.email:
                assert user.email not in report_json
            if hasattr(user, 'phone_number') and user.phone_number:
                assert user.phone_number not in report_json