#!/usr/bin/env python3
"""
Create DynamoDB Tables for TradeSimulator
This script creates all necessary DynamoDB tables for local development or AWS deployment.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError
import time

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_tables(endpoint_url=None, table_prefix='jain-trading-bot'):
    """
    Create all DynamoDB tables.
    
    Args:
        endpoint_url: DynamoDB endpoint (None for AWS, http://localhost:8000 for local)
        table_prefix: Prefix for table names
    """
    
    # Initialize DynamoDB client
    if endpoint_url:
        dynamodb = boto3.client('dynamodb', 
                               endpoint_url=endpoint_url, 
                               region_name='us-east-1',
                               aws_access_key_id='local',
                               aws_secret_access_key='local')
        print(f"🔧 Using Local DynamoDB at {endpoint_url}")
    else:
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        print("☁️  Using AWS DynamoDB")
    
    print("\n" + "="*60)
    print("📊 Creating DynamoDB Tables")
    print("="*60 + "\n")
    
    tables_created = []
    tables_exist = []
    
    # -------------------------------------------------------------------------
    # 1. TRADES TABLE
    # -------------------------------------------------------------------------
    trades_table_name = f"{table_prefix}-trades"
    print(f"Creating {trades_table_name}...")
    
    try:
        dynamodb.create_table(
            TableName=trades_table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'trade_id', 'KeyType': 'RANGE'}  # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'trade_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'symbol-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
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
        tables_created.append(trades_table_name)
        print(f"  ✅ {trades_table_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            tables_exist.append(trades_table_name)
            print(f"  ℹ️  {trades_table_name} already exists")
        else:
            print(f"  ❌ Error creating {trades_table_name}: {e}")
    
    # -------------------------------------------------------------------------
    # 2. POSITIONS TABLE
    # -------------------------------------------------------------------------
    positions_table_name = f"{table_prefix}-positions"
    print(f"Creating {positions_table_name}...")
    
    try:
        dynamodb.create_table(
            TableName=positions_table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'symbol', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        tables_created.append(positions_table_name)
        print(f"  ✅ {positions_table_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            tables_exist.append(positions_table_name)
            print(f"  ℹ️  {positions_table_name} already exists")
        else:
            print(f"  ❌ Error creating {positions_table_name}: {e}")
    
    # -------------------------------------------------------------------------
    # 3. USERS TABLE
    # -------------------------------------------------------------------------
    users_table_name = f"{table_prefix}-users"
    print(f"Creating {users_table_name}...")
    
    try:
        dynamodb.create_table(
            TableName=users_table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'slack_user_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'slack_user_id-index',
                    'KeySchema': [
                        {'AttributeName': 'slack_user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
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
        tables_created.append(users_table_name)
        print(f"  ✅ {users_table_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            tables_exist.append(users_table_name)
            print(f"  ℹ️  {users_table_name} already exists")
        else:
            print(f"  ❌ Error creating {users_table_name}: {e}")
    
    # -------------------------------------------------------------------------
    # 4. CHANNELS TABLE
    # -------------------------------------------------------------------------
    channels_table_name = f"{table_prefix}-channels"
    print(f"Creating {channels_table_name}...")
    
    try:
        dynamodb.create_table(
            TableName=channels_table_name,
            KeySchema=[
                {'AttributeName': 'channel_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'channel_id', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        tables_created.append(channels_table_name)
        print(f"  ✅ {channels_table_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            tables_exist.append(channels_table_name)
            print(f"  ℹ️  {channels_table_name} already exists")
        else:
            print(f"  ❌ Error creating {channels_table_name}: {e}")
    
    # -------------------------------------------------------------------------
    # 5. PORTFOLIOS TABLE
    # -------------------------------------------------------------------------
    portfolios_table_name = f"{table_prefix}-portfolios"
    print(f"Creating {portfolios_table_name}...")
    
    try:
        dynamodb.create_table(
            TableName=portfolios_table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'portfolio_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'portfolio_id', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        tables_created.append(portfolios_table_name)
        print(f"  ✅ {portfolios_table_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            tables_exist.append(portfolios_table_name)
            print(f"  ℹ️  {portfolios_table_name} already exists")
        else:
            print(f"  ❌ Error creating {portfolios_table_name}: {e}")
    
    # -------------------------------------------------------------------------
    # 6. AUDIT TABLE
    # -------------------------------------------------------------------------
    audit_table_name = f"{table_prefix}-audit"
    print(f"Creating {audit_table_name}...")
    
    try:
        dynamodb.create_table(
            TableName=audit_table_name,
            KeySchema=[
                {'AttributeName': 'audit_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'audit_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        tables_created.append(audit_table_name)
        print(f"  ✅ {audit_table_name} created successfully")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            tables_exist.append(audit_table_name)
            print(f"  ℹ️  {audit_table_name} already exists")
        else:
            print(f"  ❌ Error creating {audit_table_name}: {e}")
    
    # Wait for tables to be active
    if tables_created:
        print("\n⏳ Waiting for tables to become active...")
        time.sleep(5)
        
        for table_name in tables_created:
            try:
                waiter = dynamodb.get_waiter('table_exists')
                waiter.wait(TableName=table_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 10})
                print(f"  ✅ {table_name} is now active")
            except Exception as e:
                print(f"  ⚠️  Could not verify {table_name} status: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 Table Creation Summary")
    print("="*60)
    print(f"✅ Tables created: {len(tables_created)}")
    for table in tables_created:
        print(f"   - {table}")
    print(f"ℹ️  Tables already exist: {len(tables_exist)}")
    for table in tables_exist:
        print(f"   - {table}")
    print(f"\n🎉 Total tables: {len(tables_created) + len(tables_exist)}")
    print("="*60 + "\n")


def list_tables(endpoint_url=None):
    """List all DynamoDB tables."""
    if endpoint_url:
        dynamodb = boto3.client('dynamodb', 
                               endpoint_url=endpoint_url, 
                               region_name='us-east-1',
                               aws_access_key_id='local',
                               aws_secret_access_key='local')
    else:
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
    try:
        response = dynamodb.list_tables()
        tables = response.get('TableNames', [])
        
        print("\n📋 Existing DynamoDB Tables:")
        print("="*60)
        if tables:
            for i, table in enumerate(tables, 1):
                print(f"  {i}. {table}")
        else:
            print("  No tables found")
        print("="*60 + "\n")
        
        return tables
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return []


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create DynamoDB tables for TradeSimulator')
    parser.add_argument('--local', action='store_true', help='Use local DynamoDB')
    parser.add_argument('--endpoint', default='http://localhost:8000', help='Local DynamoDB endpoint')
    parser.add_argument('--prefix', default='jain-trading-bot', help='Table name prefix')
    parser.add_argument('--list', action='store_true', help='List existing tables')
    
    args = parser.parse_args()
    
    endpoint = args.endpoint if args.local else None
    
    if args.list:
        list_tables(endpoint)
    else:
        create_tables(endpoint, args.prefix)
        list_tables(endpoint)