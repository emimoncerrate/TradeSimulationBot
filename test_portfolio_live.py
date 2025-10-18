#!/usr/bin/env python3
"""
Test the portfolio command with current data
"""
import asyncio
import os
from dotenv import load_dotenv
from services.service_container import ServiceContainer

async def test_portfolio_live():
    """Test portfolio with current database state"""
    load_dotenv()
    
    print("🎯 Testing Live Portfolio Data")
    print("=" * 50)
    
    # Initialize services
    container = ServiceContainer()
    await container.startup()
    
    # Get database service
    db_service = container.get_service('DatabaseService')
    
    try:
        # Get positions for the test user
        user_id = "test-user-U08GVN6F4FQ"
        positions = await db_service.get_user_positions(user_id)
        
        print(f"📊 Positions for {user_id}:")
        print(f"Found {len(positions)} positions")
        
        total_value = 0
        for pos in positions:
            current_value = float(pos.quantity) * float(pos.current_price)
            total_value += current_value
            
            print(f"\n• {pos.symbol}:")
            print(f"  - Quantity: {pos.quantity}")
            print(f"  - Current Price: ${pos.current_price}")
            print(f"  - Average Cost: ${pos.average_cost}")
            print(f"  - Market Value: ${current_value:.2f}")
        
        print(f"\n💰 Total Portfolio Value: ${total_value:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await container.shutdown()

if __name__ == "__main__":
    asyncio.run(test_portfolio_live())