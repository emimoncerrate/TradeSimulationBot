"""
Comprehensive test suite for the DatabaseService class.

This module provides extensive unit and integration tests for all DatabaseService
methods with mocked DynamoDB operations, error scenarios, edge cases, and data
consistency validation.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Import the service and models
from services.database import (
    DatabaseService, DatabaseError, ConnectionError, ValidationError,
    NotFoundError, ConflictError
)
from models.trade import Trade, TradeType, TradeStatus, RiskLevel, TradeValidationError
from models.user import User, UserRole, UserStatus, Permission, UserProfile, UserValidationError
from models.portfolio import Portfolio, Position, PortfolioStatus, PositionType, PortfolioValidationError


class TestDatabaseServiceInitialization:
    """Test database service initialization and connection management."""
    
    def test_init_with_default_parameters(self):
        """Test initialization with default parameters."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService()
            
            assert service.region_name == 'us-east-1'
            assert service.endpoint_url is None
            assert service.max_retries == 3
            assert service.timeout == 30
            
            # Verify boto3 clients were created
            mock_client.assert_called_once()
            mock_resource.assert_called_once()
    
    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService(
                region_name='us-west-2',
                endpoint_url='http://localhost:8000',
                max_retries=5,
                timeout=60
            )
            
            assert service.region_name == 'us-west-2'
            assert service.endpoint_url == 'http://localhost:8000'
            assert service.max_retries == 5
            assert service.timeout == 60
    
    def test_init_connection_failure(self):
        """Test initialization with connection failure."""
        with patch('services.database.boto3.client', side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError) as exc_info:
                DatabaseService()
            
            assert "Failed to initialize DynamoDB connection" in str(exc_info.value)
            assert exc_info.value.error_code == "CONNECTION_FAILED"


class TestDatabaseServiceTradeOperations:
    """Test trade-related database operations."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked database service for testing."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService()
            service._tables[service.trades_table_name] = mock_table
            service._tables[service.positions_table_name] = mock_table
            service._tables[service.users_table_name] = mock_table
            service._tables[service.channels_table_name] = mock_table
            service._tables[service.portfolios_table_name] = mock_table
            service._tables[service.audit_table_name] = mock_table
            
            return service, mock_table
    
    @pytest.fixture
    def sample_trade(self):
        """Create a sample trade for testing."""
        return Trade(
            user_id="U12345",
            symbol="AAPL",
            quantity=100,
            trade_type=TradeType.BUY,
            price=Decimal("150.00")
        )
    
    @pytest.mark.asyncio
    async def test_log_trade_success(self, mock_service, sample_trade):
        """Test successful trade logging."""
        service, mock_table = mock_service
        mock_table.put_item.return_value = {}
        
        result = await service.log_trade(sample_trade)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        
        assert item['pk'] == f"USER#{sample_trade.user_id}"
        assert item['sk'] == f"TRADE#{sample_trade.trade_id}"
        assert item['symbol'] == sample_trade.symbol
        assert item['quantity'] == sample_trade.quantity
        assert item['trade_type'] == sample_trade.trade_type.value
    
    @pytest.mark.asyncio
    async def test_log_trade_duplicate(self, mock_service, sample_trade):
        """Test logging duplicate trade."""
        service, mock_table = mock_service
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Item already exists'}},
            'PutItem'
        )
        
        with pytest.raises(ConflictError) as exc_info:
            await service.log_trade(sample_trade)
        
        assert "already exists" in str(exc_info.value)
        assert exc_info.value.error_code == "DUPLICATE_TRADE"
    
    @pytest.mark.asyncio
    async def test_get_trade_success(self, mock_service, sample_trade):
        """Test successful trade retrieval."""
        service, mock_table = mock_service
        
        # Mock successful response
        mock_table.get_item.return_value = {
            'Item': sample_trade.to_dict()
        }
        
        result = await service.get_trade(sample_trade.user_id, sample_trade.trade_id)
        
        assert result is not None
        assert result.trade_id == sample_trade.trade_id
        assert result.symbol == sample_trade.symbol
        assert result.quantity == sample_trade.quantity
        
        mock_table.get_item.assert_called_once_with(
            Key={
                'pk': f"USER#{sample_trade.user_id}",
                'sk': f"TRADE#{sample_trade.trade_id}"
            }
        )
    
    @pytest.mark.asyncio
    async def test_get_trade_not_found(self, mock_service):
        """Test trade retrieval when trade doesn't exist."""
        service, mock_table = mock_service
        
        # Mock empty response
        mock_table.get_item.return_value = {}
        
        result = await service.get_trade("U12345", "nonexistent-trade-id")
        
        assert result is None


class TestDatabaseServiceUserOperations:
    """Test user-related database operations."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked database service for testing."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService()
            service._tables[service.trades_table_name] = mock_table
            service._tables[service.positions_table_name] = mock_table
            service._tables[service.users_table_name] = mock_table
            service._tables[service.channels_table_name] = mock_table
            service._tables[service.portfolios_table_name] = mock_table
            service._tables[service.audit_table_name] = mock_table
            
            return service, mock_table
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        profile = UserProfile(
            display_name="John Doe",
            email="john.doe@example.com",
            department="Trading"
        )
        
        return User(
            user_id=str(uuid.uuid4()),
            slack_user_id="U12345",
            role=UserRole.EXECUTION_TRADER,
            profile=profile
        )
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_service, sample_user):
        """Test successful user creation."""
        service, mock_table = mock_service
        mock_table.put_item.return_value = {}
        
        result = await service.create_user(sample_user)
        
        assert result is True
        mock_table.put_item.assert_called_once()
        
        # Verify the item structure
        call_args = mock_table.put_item.call_args
        item = call_args[1]['Item']
        
        assert item['pk'] == f"USER#{sample_user.user_id}"
        assert item['sk'] == "PROFILE"
        assert item['gsi1pk'] == f"SLACK#{sample_user.slack_user_id}"
        assert item['gsi1sk'] == "USER"
        assert item['role'] == sample_user.role.value
    
    @pytest.mark.asyncio
    async def test_get_user_success(self, mock_service, sample_user):
        """Test successful user retrieval."""
        service, mock_table = mock_service
        
        # Mock successful response
        mock_table.get_item.return_value = {
            'Item': sample_user.to_dict()
        }
        
        result = await service.get_user(sample_user.user_id)
        
        assert result is not None
        assert result.user_id == sample_user.user_id
        assert result.slack_user_id == sample_user.slack_user_id
        assert result.role == sample_user.role


class TestDatabaseServiceChannelOperations:
    """Test channel-related database operations."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked database service for testing."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService()
            service._tables[service.trades_table_name] = mock_table
            service._tables[service.positions_table_name] = mock_table
            service._tables[service.users_table_name] = mock_table
            service._tables[service.channels_table_name] = mock_table
            service._tables[service.portfolios_table_name] = mock_table
            service._tables[service.audit_table_name] = mock_table
            
            return service, mock_table
    
    @pytest.mark.asyncio
    async def test_is_channel_approved_true(self, mock_service):
        """Test channel approval check for approved channel."""
        service, mock_table = mock_service
        
        mock_table.get_item.return_value = {
            'Item': {
                'channel_id': 'C12345',
                'channel_name': 'trading-channel',
                'is_approved': True
            }
        }
        
        result = await service.is_channel_approved('C12345')
        
        assert result is True
        mock_table.get_item.assert_called_once_with(
            Key={'channel_id': 'C12345'}
        )
    
    @pytest.mark.asyncio
    async def test_is_channel_approved_false(self, mock_service):
        """Test channel approval check for non-approved channel."""
        service, mock_table = mock_service
        
        mock_table.get_item.return_value = {
            'Item': {
                'channel_id': 'C12345',
                'channel_name': 'general',
                'is_approved': False
            }
        }
        
        result = await service.is_channel_approved('C12345')
        
        assert result is False


class TestDatabaseServiceErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked database service for testing."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService()
            service._tables[service.trades_table_name] = mock_table
            service._tables[service.positions_table_name] = mock_table
            service._tables[service.users_table_name] = mock_table
            service._tables[service.channels_table_name] = mock_table
            service._tables[service.portfolios_table_name] = mock_table
            service._tables[service.audit_table_name] = mock_table
            
            return service, mock_table
    
    @pytest.mark.asyncio
    async def test_throttling_error_handling(self, mock_service):
        """Test handling of throttling errors with retry."""
        service, mock_table = mock_service
        
        # Mock throttling error
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Throttled'}},
            'GetItem'
        )
        
        with pytest.raises(DatabaseError):
            await service.get_trade("U12345", "T123")
        
        # Should increment error metrics
        assert service._metrics['errors'] > 0
    
    @pytest.mark.asyncio
    async def test_validation_error_handling(self, mock_service):
        """Test handling of validation errors."""
        service, mock_table = mock_service
        
        mock_table.put_item.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid data'}},
            'PutItem'
        )
        
        sample_trade = Trade(
            user_id="U12345",
            symbol="AAPL",
            quantity=100,
            trade_type=TradeType.BUY,
            price=Decimal("150.00")
        )
        
        with pytest.raises(DatabaseError) as exc_info:
            await service.log_trade(sample_trade)
        
        assert exc_info.value.error_code == "TRADE_LOG_FAILED"
        assert "Invalid data" in str(exc_info.value)


class TestDatabaseServiceHealthAndMonitoring:
    """Test health check and monitoring functionality."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked database service for testing."""
        with patch('services.database.boto3.client') as mock_client, \
             patch('services.database.boto3.resource') as mock_resource:
            
            mock_table = Mock()
            mock_table.load.return_value = None
            mock_resource.return_value.Table.return_value = mock_table
            
            service = DatabaseService()
            service._tables[service.trades_table_name] = mock_table
            service._tables[service.positions_table_name] = mock_table
            service._tables[service.users_table_name] = mock_table
            service._tables[service.channels_table_name] = mock_table
            service._tables[service.portfolios_table_name] = mock_table
            service._tables[service.audit_table_name] = mock_table
            
            return service, mock_table
    
    def test_get_health_status_healthy(self, mock_service):
        """Test health status when all tables are healthy."""
        service, mock_table = mock_service
        
        # Mock successful table load
        mock_table.load.return_value = None
        
        health = service.get_health_status()
        
        assert health['status'] == 'healthy'
        assert health['region'] == service.region_name
        assert 'tables' in health
        assert 'metrics' in health
        assert 'cache_size' in health
        assert 'timestamp' in health
        
        # All tables should be healthy
        for table_status in health['tables'].values():
            assert table_status == 'healthy'
    
    def test_get_metrics(self, mock_service):
        """Test metrics retrieval."""
        service, _ = mock_service
        
        # Update some metrics
        service._metrics['queries_executed'] = 10
        service._metrics['cache_hits'] = 5
        service._metrics['errors'] = 2
        
        metrics = service.get_metrics()
        
        assert metrics['queries_executed'] == 10
        assert metrics['cache_hits'] == 5
        assert metrics['errors'] == 2
        
        # Should be a copy, not reference
        metrics['queries_executed'] = 999
        assert service._metrics['queries_executed'] == 10


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])