#!/usr/bin/env python3
"""
Quick script to check user positions in the database.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.service_container import get_database_service

async def check_positions():
    """Check positions for the test user."""
    try:
        db_service = get_database_service()
        
        # Your user ID from the logs
        user_id = "test-user-U08GVN6F4FQ"
        
        print(f"📊 Checking positions for user: {user_id}")
        
        positions = await db_service.get_user_positions(user_id)
        
        if positions:
            print(f"\n✅ Found {len(positions)} positions:")
            total_value = 0
            
            for pos in positions:
                current_value = float(pos.quantity) * float(pos.current_price)
                total_value += current_value
                
                print(f"   • {pos.symbol}: {pos.quantity} shares @ ${pos.current_price:.2f}")
                print(f"     Value: ${current_value:,.2f}")
                print()
            
            print(f"💰 Total Portfolio Value: ${total_value:,.2f}")
        else:
            print("📭 No positions found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_positions())