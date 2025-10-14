#!/usr/bin/env python3
"""
Database Viewer - View your DynamoDB data without running the app
"""

import boto3
import json
from datetime import datetime

def view_database():
    """View all tables and their data."""
    print("🗄️ DynamoDB Database Viewer")
    print("="*60)
    
    # Connect to local DynamoDB
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        aws_access_key_id='local',
        aws_secret_access_key='local',
        region_name='us-east-1'
    )
    
    # Get all tables
    tables = list(dynamodb.tables.all())
    table_names = [table.name for table in tables]
    
    print(f"📊 Found {len(table_names)} tables:")
    for i, name in enumerate(table_names, 1):
        print(f"   {i}. {name}")
    
    print("\n" + "="*60)
    
    # View each table
    for table_name in table_names:
        print(f"\n📋 Table: {table_name}")
        print("-" * 40)
        
        table = dynamodb.Table(table_name)
        
        try:
            # Scan table (limit to 10 items)
            response = table.scan(Limit=10)
            items = response.get('Items', [])
            
            if items:
                print(f"   Items: {len(items)} (showing max 10)")
                for i, item in enumerate(items, 1):
                    print(f"\n   Item {i}:")
                    for key, value in item.items():
                        # Format the value nicely
                        if isinstance(value, dict):
                            value_str = json.dumps(value, indent=6, default=str)
                        else:
                            value_str = str(value)
                        
                        # Truncate long values
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        
                        print(f"     {key}: {value_str}")
            else:
                print("   No items found")
                
        except Exception as e:
            print(f"   Error reading table: {e}")
    
    print("\n" + "="*60)
    print("✅ Database view complete!")
    print("\n💡 Useful Commands:")
    print("   View specific table:")
    print("   AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local \\")
    print("   aws dynamodb scan --table-name jain-trading-bot-users \\")
    print("   --endpoint-url http://localhost:8000 --region us-east-1")
    print("\n   List all tables:")
    print("   AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local \\")
    print("   aws dynamodb list-tables \\")
    print("   --endpoint-url http://localhost:8000 --region us-east-1")

if __name__ == "__main__":
    try:
        view_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure DynamoDB is running: docker ps | grep dynamodb")