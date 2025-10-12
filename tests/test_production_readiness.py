#!/usr/bin/env python3
"""
Production Readiness Test Suite
Tests all critical components for production deployment.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from decimal import Decimal
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.database import DatabaseService
from services.alpaca_service import AlpacaService
from services.market_data import MarketDataService
from models.user import User, UserRole, UserStatus, UserProfile
from models.trade import Trade, TradeType, TradeStatus
from utils.serializers import serialize_for_dynamodb, deserialize_from_dynamodb


class TestProductionReadiness:
    """Comprehensive production readiness tests."""
    
    @pytest.fixture
    async def database_service(self):
        """Create database service for testing."""
        return DatabaseService()
    
    @pytest.fixture
    async def test_user(self):
        """Create a test user."""
        return User(
            user_id="prod-test-user-001",
            slack_user_id="U123PROD456",
            role=UserRole.EXECUTION_TRADER,
            status=UserStatus.ACTIVE,
            profile=UserProfile(
                display_name="Production Test User",
                email="test@production.com",
                department="QA Testing"
            )
        )
    
    @pytest.fixture
    async def test_trade(self, test_user):
        """Create a test trade."""
        return Trade(
            trade_id="prod-trade-001",
            user_id=test_user.user_id,
            symbol="AAPL",
            trade_type=TradeType.BUY,
            quantity=100,
            price=Decimal("150.00"),
            status=TradeStatus.EXECUTED,
            timestamp=datetime.now(timezone.utc)
        )
    
    @pytest.mark.asyncio
    async def test_database_serialization(self, database_service, test_user):
        """Test database can handle complex model serialization."""
        try:
            # Test user creation with datetime fields
            success = await database_service.create_user(test_user)
            assert success, "User creation should succeed"
            
            # Test user retrieval
            retrieved_user = await database_service.get_user_by_id(test_user.user_id)
            assert retrieved_user is not None, "User should be retrievable"
            assert retrieved_user.user_id == test_user.user_id
            
            print("✅ Database serialization test passed")
            
        except Exception as e:
            pytest.fail(f"Database serialization failed: {e}")
    
    @pytest.mark.asyncio
    async def test_trade_logging(self, database_service, test_trade):
        """Test complete trade logging workflow."""
        try:
            # Log the trade
            success = await database_service.log_trade(test_trade)
            assert success, "Trade logging should succeed"
            
            # Retrieve the trade
            retrieved_trade = await database_service.get_trade(
                test_trade.user_id, 
                test_trade.trade_id
            )
            assert retrieved_trade is not None, "Trade should be retrievable"
            assert retrieved_trade.trade_id == test_trade.trade_id
            assert retrieved_trade.symbol == test_trade.symbol
            
            print("✅ Trade logging test passed")
            
        except Exception as e:
            pytest.fail(f"Trade logging failed: {e}")
    
    @pytest.mark.asyncio
    async def test_alpaca_integration(self):
        """Test Alpaca service integration."""
        try:
            alpaca = AlpacaService()
            await alpaca.initialize()
            
            if alpaca.is_available():
                # Test account access
                account = await alpaca.get_account()
                assert account is not None, "Should be able to get account info"
                assert 'cash' in account, "Account should have cash info"
                
                print(f"✅ Alpaca integration test passed - Account: {account['account_number']}")
            else:
                print("⚠️  Alpaca not configured - skipping integration test")
                
        except Exception as e:
            pytest.fail(f"Alpaca integration failed: {e}")
    
    @pytest.mark.asyncio
    async def test_market_data_integration(self):
        """Test market data service integration."""
        try:
            market_service = MarketDataService()
            await market_service.initialize()
            
            # Test getting a quote
            quote = await market_service.get_quote("AAPL")
            assert quote is not None, "Should be able to get market quote"
            assert quote.symbol == "AAPL"
            assert quote.current_price > 0
            
            print(f"✅ Market data integration test passed - AAPL: ${quote.current_price}")
            
        except Exception as e:
            pytest.fail(f"Market data integration failed: {e}")
    
    def test_serialization_utilities(self):
        """Test serialization utilities work correctly."""
        try:
            # Test datetime serialization
            test_data = {
                'timestamp': datetime.now(timezone.utc),
                'price': Decimal('150.50'),
                'status': TradeStatus.EXECUTED,
                'nested': {
                    'created_at': datetime.now(timezone.utc),
                    'values': [1, 2, 3]
                }
            }
            
            # Serialize
            serialized = serialize_for_dynamodb(test_data)
            assert isinstance(serialized['timestamp'], str)
            assert isinstance(serialized['price'], Decimal)
            assert serialized['status'] == 'executed'
            
            # Deserialize
            deserialized = deserialize_from_dynamodb(serialized)
            assert isinstance(deserialized['timestamp'], datetime)
            
            print("✅ Serialization utilities test passed")
            
        except Exception as e:
            pytest.fail(f"Serialization utilities failed: {e}")
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, database_service, test_user, test_trade):
        """Test complete end-to-end trading workflow."""
        try:
            # 1. Create user
            user_success = await database_service.create_user(test_user)
            assert user_success, "User creation should succeed"
            
            # 2. Log trade
            trade_success = await database_service.log_trade(test_trade)
            assert trade_success, "Trade logging should succeed"
            
            # 3. Get user trades
            user_trades = await database_service.get_user_trades(test_user.user_id)
            assert len(user_trades) > 0, "Should have at least one trade"
            assert any(t.trade_id == test_trade.trade_id for t in user_trades)
            
            # 4. Update trade status
            update_success = await database_service.update_trade_status(
                test_user.user_id,
                test_trade.trade_id,
                TradeStatus.SETTLED
            )
            assert update_success, "Trade status update should succeed"
            
            print("✅ End-to-end workflow test passed")
            
        except Exception as e:
            pytest.fail(f"End-to-end workflow failed: {e}")
    
    def test_environment_configuration(self):
        """Test all required environment variables are set."""
        required_vars = [
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_REGION',
            'DYNAMODB_TABLE_PREFIX',
            'FINNHUB_API_KEY',
            'SLACK_BOT_TOKEN',
            'SLACK_SIGNING_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            pytest.fail(f"Missing required environment variables: {missing_vars}")
        
        print("✅ Environment configuration test passed")
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test database connection and table access."""
        try:
            db = DatabaseService()
            
            # Test connection by listing a table
            import boto3
            if db.endpoint_url:
                dynamodb = boto3.resource(
                    'dynamodb',
                    endpoint_url=db.endpoint_url,
                    aws_access_key_id='local',
                    aws_secret_access_key='local',
                    region_name=db.region_name
                )
            else:
                dynamodb = boto3.resource('dynamodb', region_name=db.region_name)
            
            # Check if tables exist
            tables = list(dynamodb.tables.all())
            table_names = [table.name for table in tables]
            
            required_tables = [
                f"{os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')}-users",
                f"{os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')}-trades",
                f"{os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')}-positions",
            ]
            
            missing_tables = [table for table in required_tables if table not in table_names]
            if missing_tables:
                pytest.fail(f"Missing required tables: {missing_tables}")
            
            print(f"✅ Database connection test passed - {len(table_names)} tables found")
            
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")


async def run_production_tests():
    """Run all production readiness tests."""
    print("🚀 Running Production Readiness Tests")
    print("="*60)
    
    # Import pytest and run tests
    import subprocess
    import sys
    
    try:
        # Run the tests
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            __file__, 
            '-v', 
            '--tb=short'
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n🎉 All production readiness tests passed!")
            print("✅ Your bot is ready for production deployment")
        else:
            print("\n❌ Some tests failed")
            print("🔧 Please fix the issues before production deployment")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the tests
    success = asyncio.run(run_production_tests())
    sys.exit(0 if success else 1)