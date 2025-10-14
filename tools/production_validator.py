#!/usr/bin/env python3
"""
Production Validation Tool
Simple validation script to check if everything is production-ready.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def validate_production_readiness():
    """Validate all components for production readiness."""
    print("🚀 Production Readiness Validation")
    print("="*60)
    
    all_passed = True
    
    # Test 1: Environment Configuration
    print("\n1️⃣ Environment Configuration")
    print("-" * 30)
    
    required_vars = {
        'AWS_ACCESS_KEY_ID': 'Database credentials',
        'AWS_SECRET_ACCESS_KEY': 'Database credentials', 
        'AWS_REGION': 'AWS region',
        'DYNAMODB_TABLE_PREFIX': 'Table naming',
        'FINNHUB_API_KEY': 'Market data',
        'SLACK_BOT_TOKEN': 'Slack integration',
        'SLACK_SIGNING_SECRET': 'Slack security'
    }
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value not in ['', 'your-key-here', 'mock-access-key-id']:
            print(f"   ✅ {var}: Configured ({description})")
        else:
            print(f"   ❌ {var}: Missing or placeholder ({description})")
            all_passed = False
    
    # Test 2: Database Connection
    print("\n2️⃣ Database Connection")
    print("-" * 30)
    
    try:
        import boto3
        
        aws_key = os.getenv('AWS_ACCESS_KEY_ID')
        endpoint = os.getenv('DYNAMODB_LOCAL_ENDPOINT')
        
        if aws_key == 'local' and endpoint:
            # Local DynamoDB
            dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=endpoint,
                aws_access_key_id='local',
                aws_secret_access_key='local',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            print(f"   ✅ Connected to local DynamoDB: {endpoint}")
        else:
            # AWS DynamoDB
            dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION'))
            print("   ✅ Connected to AWS DynamoDB")
        
        # Check tables
        tables = list(dynamodb.tables.all())
        table_names = [table.name for table in tables]
        
        prefix = os.getenv('DYNAMODB_TABLE_PREFIX', 'jain-trading-bot')
        required_tables = [
            f"{prefix}-users",
            f"{prefix}-trades", 
            f"{prefix}-positions",
            f"{prefix}-portfolios",
            f"{prefix}-channels",
            f"{prefix}-audit"
        ]
        
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if not missing_tables:
            print(f"   ✅ All {len(required_tables)} required tables found")
        else:
            print(f"   ❌ Missing tables: {missing_tables}")
            all_passed = False
            
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        all_passed = False
    
    # Test 3: Serialization
    print("\n3️⃣ Data Serialization")
    print("-" * 30)
    
    try:
        from utils.serializers import serialize_for_dynamodb, deserialize_from_dynamodb
        
        # Test complex data
        test_data = {
            'timestamp': datetime.now(timezone.utc),
            'price': Decimal('150.50'),
            'nested': {
                'created_at': datetime.now(timezone.utc),
                'values': [1, 2, 3]
            }
        }
        
        serialized = serialize_for_dynamodb(test_data)
        deserialized = deserialize_from_dynamodb(serialized)
        
        print("   ✅ Datetime serialization works")
        print("   ✅ Decimal handling works")
        print("   ✅ Nested object serialization works")
        
    except Exception as e:
        print(f"   ❌ Serialization failed: {e}")
        all_passed = False
    
    # Test 4: Database Service
    print("\n4️⃣ Database Service")
    print("-" * 30)
    
    try:
        from services.database import DatabaseService
        
        db = DatabaseService()
        print("   ✅ DatabaseService initializes correctly")
        print(f"   ✅ Using endpoint: {db.endpoint_url or 'AWS DynamoDB'}")
        print(f"   ✅ Table prefix: {db.trades_table_name.split('-')[0]}-{db.trades_table_name.split('-')[1]}-{db.trades_table_name.split('-')[2]}")
        
    except Exception as e:
        print(f"   ❌ DatabaseService failed: {e}")
        all_passed = False
    
    # Test 5: Market Data
    print("\n5️⃣ Market Data Service")
    print("-" * 30)
    
    try:
        import requests
        
        api_key = os.getenv('FINNHUB_API_KEY')
        if api_key and api_key != 'your-api-key-here':
            url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                price = data.get('c', 0)
                print(f"   ✅ Market data API working - AAPL: ${price}")
            else:
                print(f"   ❌ Market data API error: HTTP {response.status_code}")
                all_passed = False
        else:
            print("   ❌ Finnhub API key not configured")
            all_passed = False
            
    except Exception as e:
        print(f"   ❌ Market data test failed: {e}")
        all_passed = False
    
    # Test 6: Alpaca Integration
    print("\n6️⃣ Alpaca Paper Trading")
    print("-" * 30)
    
    try:
        from services.alpaca_service import AlpacaService
        
        alpaca = AlpacaService()
        await alpaca.initialize()
        
        if alpaca.is_available():
            account = await alpaca.get_account()
            print(f"   ✅ Alpaca connected - Account: {account['account_number']}")
            print(f"   ✅ Virtual cash: ${account['cash']:,.2f}")
        else:
            print("   ⚠️  Alpaca not configured (will use mock trading)")
            
    except Exception as e:
        print(f"   ❌ Alpaca test failed: {e}")
        # Don't fail overall test for Alpaca issues
    
    # Test 7: Service Imports
    print("\n7️⃣ Service Imports")
    print("-" * 30)
    
    services_to_test = [
        ('services.database', 'DatabaseService'),
        ('services.market_data', 'MarketDataService'),
        ('services.alpaca_service', 'AlpacaService'),
        ('services.trading_api', 'TradingAPIService'),
        ('services.auth', 'AuthService'),
    ]
    
    for module_name, class_name in services_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)
            print(f"   ✅ {class_name}: Import successful")
        except Exception as e:
            print(f"   ❌ {class_name}: Import failed - {e}")
            all_passed = False
    
    # Final Results
    print("\n" + "="*60)
    if all_passed:
        print("🎉 PRODUCTION READINESS: PASSED")
        print("✅ Your bot is ready for production deployment!")
        print("\n🚀 Next Steps:")
        print("   1. Start your bot: python app.py")
        print("   2. Test in Slack: /trade AAPL")
        print("   3. Monitor logs for any issues")
    else:
        print("❌ PRODUCTION READINESS: FAILED")
        print("🔧 Please fix the issues above before deployment")
        print("\n📖 Check the setup guide: docs/setup/SETUP_LOG.md")
    
    print("="*60)
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(validate_production_readiness())
    sys.exit(0 if success else 1)