#!/usr/bin/env python3
"""
Test Quick Command Performance

This script tests the optimized command to ensure it responds quickly.
"""

import os
import sys
import asyncio
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


async def test_quick_command():
    """Test the quick command performance."""
    print("⚡ Testing Quick Command Performance")
    print("=" * 50)
    
    try:
        # Initialize services
        from services.service_container import get_container
        from services.auth import AuthService
        from listeners.multi_account_trade_command import MultiAccountTradeCommand
        
        container = get_container()
        auth_service = container.get(AuthService)
        
        # Create command instance
        multi_command = MultiAccountTradeCommand(auth_service)
        
        # Test quick parameter parsing
        start_time = time.time()
        
        test_commands = [
            "2 aapl buy",
            "100 TSLA",
            "sell 50 NVDA"
        ]
        
        for cmd in test_commands:
            params = multi_command._parse_trade_parameters(cmd)
            print(f"✅ '{cmd}' → {params}")
        
        parse_time = time.time() - start_time
        print(f"⚡ Parsing time: {parse_time:.3f}s")
        
        # Test quick modal creation
        start_time = time.time()
        
        class QuickContext:
            def __init__(self):
                self.account_id = "primary"
                self.symbol = "AAPL"
                self.quantity = 2
                self.action = "buy"
                self.gmv = None
                self.trigger_id = "test_trigger"
        
        context = QuickContext()
        
        # Test quick modal creation
        modal = await multi_command._create_quick_modal_with_symbol("AAPL", context)
        
        modal_time = time.time() - start_time
        print(f"⚡ Modal creation time: {modal_time:.3f}s")
        
        # Verify modal structure
        print(f"✅ Modal created:")
        print(f"   Title: {modal['title']['text']}")
        print(f"   Blocks: {len(modal['blocks'])}")
        
        # Check pre-filled values
        for block in modal['blocks']:
            if block.get('type') == 'input':
                element = block.get('element', {})
                if 'initial_value' in element:
                    print(f"   ✅ {block['block_id']}: {element['initial_value']}")
                elif 'initial_option' in element:
                    print(f"   ✅ {block['block_id']}: {element['initial_option']['value']}")
        
        total_time = parse_time + modal_time
        print(f"\n⚡ Total time: {total_time:.3f}s")
        
        if total_time < 1.0:
            print(f"🎉 FAST ENOUGH! Should avoid Slack timeout.")
        else:
            print(f"⚠️  Still might be slow for Slack (target: <1s)")
        
        return total_time < 2.0  # Allow 2s buffer
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_quick_command())
    
    if success:
        print(f"\n🎯 Quick command test PASSED!")
        print(f"   The optimized command should avoid timeout.")
        print(f"   Restart your Slack app and try: /trade 2 aapl buy")
    else:
        print(f"\n💥 Quick command test FAILED!")
    
    sys.exit(0 if success else 1)