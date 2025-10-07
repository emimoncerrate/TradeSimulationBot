#!/usr/bin/env python3
"""
View Database Contents
Quick script to see what's stored in DynamoDB
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def view_database():
    """View all data in DynamoDB tables."""
    
    # Set credentials
    os.environ['AWS_ACCESS_KEY_ID'] = 'local'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'local'
    
    endpoint_url = 'http://localhost:8000'
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name='us-east-1')
    
    tables = [
        'slack-trading-bot-users',
        'slack-trading-bot-trades',
        'slack-trading-bot-positions',
        'slack-trading-bot-portfolios',
        'slack-trading-bot-channels',
        'slack-trading-bot-audit'
    ]
    
    print("\n" + "="*70)
    print("📊 DynamoDB Database Contents")
    print("="*70 + "\n")
    
    total_items = 0
    
    for table_name in tables:
        try:
            table = dynamodb.Table(table_name)
            response = table.scan()
            items = response.get('Items', [])
            count = len(items)
            total_items += count
            
            print(f"📋 {table_name}")
            print(f"   Items: {count}")
            
            if count > 0:
                print(f"   Data:")
                for i, item in enumerate(items[:3], 1):  # Show first 3 items
                    print(f"      {i}. {dict(item)}")
                if count > 3:
                    print(f"      ... and {count - 3} more")
            else:
                print(f"   (empty)")
            
            print()
            
        except ClientError as e:
            print(f"❌ Error accessing {table_name}: {e}")
            print()
    
    print("="*70)
    print(f"📊 Total Items Across All Tables: {total_items}")
    print("="*70 + "\n")

if __name__ == "__main__":
    view_database()

