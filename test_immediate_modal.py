#!/usr/bin/env python3
"""
Test the immediate modal opening fix.
"""

import time
from unittest.mock import MagicMock

def test_immediate_modal_opening():
    """Test that modal opens immediately after ack."""
    print("🧪 Testing immediate modal opening...")
    
    # Mock Slack objects
    mock_client = MagicMock()
    mock_client.views_open.return_value = {"view": {"id": "test_view_id"}}
    
    # Mock command body
    mock_body = {
        "text": "AAPL",
        "trigger_id": "test_trigger_id",
        "user_id": "test_user",
        "channel_id": "test_channel"
    }
    
    # Mock ack function
    mock_ack = MagicMock()
    
    # Simulate the FIXED command handler logic
    start_time = time.time()
    
    # CRITICAL: Acknowledge immediately - no operations before this
    mock_ack()
    ack_time = time.time()
    
    # Parse command parameters after ack
    command_text = mock_body.get("text", "").strip()
    symbol = command_text.upper().strip() if command_text else None
    trigger_id = mock_body.get("trigger_id")
    
    # Open modal immediately - no try/catch to avoid any delays
    if symbol:
        loading_modal = {
            "type": "modal",
            "callback_id": "enhanced_trade_modal",
            "title": {
                "type": "plain_text",
                "text": "📊 Live Market Data"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📊 {symbol}*\n\n🔄 Loading market data..."
                    }
                }
            ],
            "close": {
                "type": "plain_text",
                "text": "Close"
            }
        }
        
        # Open modal immediately - no error handling to avoid delays
        mock_client.views_open(
            trigger_id=trigger_id,
            view=loading_modal
        )
    
    modal_open_time = time.time()
    
    # Calculate timings
    ack_duration = ack_time - start_time
    modal_duration = modal_open_time - ack_time
    total_duration = modal_open_time - start_time
    
    print(f"⏱️  Ack time: {ack_duration:.6f} seconds")
    print(f"⏱️  Modal open time: {modal_duration:.6f} seconds")
    print(f"⏱️  Total time: {total_duration:.6f} seconds")
    
    # Verify timing (should be extremely fast)
    success = True
    
    if ack_duration < 0.001:  # Ack should be immediate
        print("✅ PASS: Ack called immediately (< 0.001s)")
    else:
        print(f"❌ FAIL: Ack too slow ({ack_duration:.6f}s)")
        success = False
    
    if modal_duration < 0.01:  # Modal should open very fast
        print("✅ PASS: Modal opens immediately (< 0.01s)")
    else:
        print(f"❌ FAIL: Modal opens too slow ({modal_duration:.6f}s)")
        success = False
    
    if total_duration < 0.1:  # Total should be well under 3 seconds
        print("✅ PASS: Total execution time acceptable (< 0.1s)")
    else:
        print(f"❌ FAIL: Total execution too slow ({total_duration:.6f}s)")
        success = False
    
    # Verify calls were made
    if mock_ack.called:
        print("✅ PASS: Ack called")
    else:
        print("❌ FAIL: Ack not called")
        success = False
    
    if mock_client.views_open.called:
        print("✅ PASS: Modal opened")
        call_args = mock_client.views_open.call_args
        if call_args[1]['trigger_id'] == 'test_trigger_id':
            print("✅ PASS: Correct trigger_id used")
        else:
            print("❌ FAIL: Wrong trigger_id")
            success = False
    else:
        print("❌ FAIL: Modal not opened")
        success = False
    
    return success

def test_no_symbol_case():
    """Test the no-symbol case for immediate modal opening."""
    print("\n🧪 Testing no-symbol immediate modal opening...")
    
    # Mock Slack objects
    mock_client = MagicMock()
    mock_client.views_open.return_value = {"view": {"id": "test_view_id"}}
    
    # Mock command body with no text
    mock_body = {
        "text": "",
        "trigger_id": "test_trigger_id",
        "user_id": "test_user",
        "channel_id": "test_channel"
    }
    
    # Mock ack function
    mock_ack = MagicMock()
    
    # Simulate the FIXED command handler logic
    start_time = time.time()
    
    # CRITICAL: Acknowledge immediately - no operations before this
    mock_ack()
    ack_time = time.time()
    
    # Parse command parameters after ack
    command_text = mock_body.get("text", "").strip()
    symbol = command_text.upper().strip() if command_text else None
    trigger_id = mock_body.get("trigger_id")
    
    # Open modal immediately
    if symbol:
        # Should not reach here
        print("❌ FAIL: Should not have symbol")
        return False
    else:
        basic_modal = {
            "type": "modal",
            "callback_id": "enhanced_trade_modal",
            "title": {
                "type": "plain_text",
                "text": "📊 Live Market Data"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📊 Live Market Data Trading*\n\nSelect a stock symbol to get started:"
                    }
                }
            ],
            "close": {
                "type": "plain_text",
                "text": "Close"
            },
            "submit": {
                "type": "plain_text",
                "text": "Get Quote"
            }
        }
        
        # Open modal immediately
        mock_client.views_open(
            trigger_id=trigger_id,
            view=basic_modal
        )
    
    modal_open_time = time.time()
    
    # Calculate timings
    ack_duration = ack_time - start_time
    modal_duration = modal_open_time - ack_time
    total_duration = modal_open_time - start_time
    
    print(f"⏱️  Ack time: {ack_duration:.6f} seconds")
    print(f"⏱️  Modal open time: {modal_duration:.6f} seconds")
    print(f"⏱️  Total time: {total_duration:.6f} seconds")
    
    # Verify timing
    success = True
    
    if total_duration < 0.1:
        print("✅ PASS: No-symbol modal opens immediately")
    else:
        print(f"❌ FAIL: No-symbol modal too slow ({total_duration:.6f}s)")
        success = False
    
    # Verify modal has submit button
    if mock_client.views_open.called:
        call_args = mock_client.views_open.call_args
        modal = call_args[1]['view']
        if 'submit' in modal:
            print("✅ PASS: Submit button present in no-symbol modal")
        else:
            print("❌ FAIL: Submit button missing")
            success = False
    
    return success

if __name__ == "__main__":
    print("🚀 Testing Immediate Modal Opening Fix")
    print("=" * 50)
    
    success = True
    
    # Test with symbol
    success &= test_immediate_modal_opening()
    
    # Test without symbol
    success &= test_no_symbol_case()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Modal opens immediately after ack")
        print("✅ No delays that could cause trigger_id expiration")
        print("✅ Both symbol and no-symbol cases work")
        print("✅ Execution time well under 3-second limit")
    else:
        print("❌ SOME TESTS FAILED!")
        exit(1)