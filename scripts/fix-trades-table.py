#!/usr/bin/env python3
"""
Fix the trades table GSI structure to match what the application expects.
"""

import boto3
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

def wait_for_table_deletion(client, table_name, max_attempts=30):
    """Wait for table to be deleted."""
    for attempt in range(max_attempts):
        try:
            client.describe_table(TableName=table_name)
            print(f"Waiting for table {table_name} to be deleted... (attempt {attempt+1}/{max_attempts})")
            time.sleep(2)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"✅ Table {table_name} deleted successfully")
                return True
            else:
                raise e
    
    print(f"Timeout waiting for table {table_name} to be deleted")
    return False

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

def delete_trades_table(client):
    """Delete the existing trades table."""
    table_name = f"{TABLE_PREFIX}-trades"
    
    try:
        print(f"🗑️  Deleting table: {table_name}")
        client.delete_table(TableName=table_name)
        return wait_for_table_deletion(client, table_name)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"⚠️  Table {table_name} doesn't exist")
            return True
        else:
            print(f"❌ Error deleting table {table_name}: {e}")
            return False

def create_trades_table_fixed(client):
    """Create trades table with correct GSI structure."""
    table_name = f"{TABLE_PREFIX}-trades"
    
    try:
        print(f"📋 Creating table with correct GSI: {table_name}")
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'sk',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sk',
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
        print(f"❌ Error creating table {table_name}: {e}")
        return False

def main():
    """Main function to fix the trades table."""
    print("🔧 Fixing trades table GSI structure...")
    print(f"📍 DynamoDB endpoint: {DYNAMODB_ENDPOINT}")
    print()
    
    try:
        # Create DynamoDB client
        client = create_dynamodb_client()
        
        # Test connection
        print("🔍 Testing DynamoDB connection...")
        client.list_tables()
        print("✅ DynamoDB connection successful")
        print()
        
        # Delete existing trades table
        if not delete_trades_table(client):
            print("❌ Failed to delete trades table")
            return False
        
        print()
        
        # Create new trades table with correct GSI
        if not create_trades_table_fixed(client):
            print("❌ Failed to create trades table")
            return False
        
        print("\n" + "="*60)
        print("🎉 Trades table fixed successfully!")
        print("✅ GSI now uses gsi1pk (HASH) + gsi1sk (RANGE)")
        print("✅ Application should now be able to query trades by symbol")
        print("\n📝 Next step: Test the /trade command in Slack")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)