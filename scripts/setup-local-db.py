#!/usr/bin/env python3
"""
Setup script for local DynamoDB tables for development.
This script creates all required tables with proper indexes for the trading bot.
"""

import boto3
import json
import time
from botocore.exceptions import ClientError

# Local DynamoDB configuration
DYNAMODB_ENDPOINT = 'http://localhost:8001'
AWS_REGION = 'us-east-1'
TABLE_PREFIX = 'jain-trading-bot'

def create_dynamodb_client():
    """Create DynamoDB client for local development."""
    return boto3.client(
        'dynamodb',
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id='local',
        aws_secret_access_key='local'
    )

def wait_for_table_active(client, table_name, max_attempts=30):
    """Wait for table to become active."""
    for attempt in range(max_attempts):
        try:
            response = client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            print(f"Table {table_name} status: {status}")
            
            if status == 'ACTIVE':
                return True
            elif status == 'CREATING':
                time.sleep(2)
                continue
            else:
                print(f"Unexpected table status: {status}")
                return False
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Table {table_name} not found, waiting...")
                time.sleep(2)
                continue
            else:
                raise e
    
    print(f"Timeout waiting for table {table_name} to become active")
    return False

def create_users_table(client):
    """Create users table with GSI for Slack ID lookup."""
    table_name = f"{TABLE_PREFIX}-users"
    
    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'gsi1pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'gsi1sk',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'gsi1',
                    'KeySchema': [
                        {
                            'AttributeName': 'gsi1pk',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'gsi1sk',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table: {table_name}")
        return wait_for_table_active(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def create_trades_table(client):
    """Create trades table."""
    table_name = f"{TABLE_PREFIX}-trades"
    
    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'trade_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'trade_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table: {table_name}")
        return wait_for_table_active(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def create_positions_table(client):
    """Create positions table."""
    table_name = f"{TABLE_PREFIX}-positions"
    
    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'position_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'position_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table: {table_name}")
        return wait_for_table_active(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def create_channels_table(client):
    """Create channels table."""
    table_name = f"{TABLE_PREFIX}-channels"
    
    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'channel_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'channel_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table: {table_name}")
        return wait_for_table_active(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def create_portfolios_table(client):
    """Create portfolios table."""
    table_name = f"{TABLE_PREFIX}-portfolios"
    
    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'portfolio_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'portfolio_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table: {table_name}")
        return wait_for_table_active(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def create_audit_table(client):
    """Create audit table."""
    table_name = f"{TABLE_PREFIX}-audit"
    
    try:
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'audit_id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'audit_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'user-timestamp-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'user_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table: {table_name}")
        return wait_for_table_active(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Error creating table {table_name}: {e}")
            return False

def main():
    """Main setup function."""
    print("🚀 Setting up local DynamoDB tables for Jain Global Trading Bot...")
    print(f"📍 DynamoDB endpoint: {DYNAMODB_ENDPOINT}")
    print(f"🏷️  Table prefix: {TABLE_PREFIX}")
    print()
    
    try:
        # Create DynamoDB client
        client = create_dynamodb_client()
        
        # Test connection
        print("🔍 Testing DynamoDB connection...")
        client.list_tables()
        print("✅ DynamoDB connection successful")
        print()
        
        # Create tables
        tables_created = []
        
        print("📋 Creating users table...")
        if create_users_table(client):
            tables_created.append(f"{TABLE_PREFIX}-users")
        
        print("\n📋 Creating trades table...")
        if create_trades_table(client):
            tables_created.append(f"{TABLE_PREFIX}-trades")
        
        print("\n📋 Creating positions table...")
        if create_positions_table(client):
            tables_created.append(f"{TABLE_PREFIX}-positions")
        
        print("\n📋 Creating channels table...")
        if create_channels_table(client):
            tables_created.append(f"{TABLE_PREFIX}-channels")
        
        print("\n📋 Creating portfolios table...")
        if create_portfolios_table(client):
            tables_created.append(f"{TABLE_PREFIX}-portfolios")
        
        print("\n📋 Creating audit table...")
        if create_audit_table(client):
            tables_created.append(f"{TABLE_PREFIX}-audit")
        
        print("\n" + "="*60)
        print("🎉 Setup complete!")
        print(f"✅ Successfully created/verified {len(tables_created)} tables:")
        for table in tables_created:
            print(f"   • {table}")
        
        print("\n📝 Next steps:")
        print("1. Update your .env file to use local DynamoDB:")
        print("   DYNAMODB_LOCAL_ENDPOINT=http://localhost:8000")
        print("2. Start your application with: python3 app.py")
        print("3. Test the /trade command in your Slack workspace")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure Docker is running")
        print("2. Start DynamoDB Local: docker-compose up -d dynamodb-local")
        print("3. Wait a few seconds for DynamoDB to start")
        print("4. Run this script again")

if __name__ == "__main__":
    main()