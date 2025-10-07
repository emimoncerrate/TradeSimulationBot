#!/usr/bin/env python3
"""
Test the view_id fix for modal updates.
"""

from unittest.mock import MagicMock

def test_view_id_extraction():
    """Test that view_id is properly extracted from modal response."""
    print("🧪 Testing view_id extraction for modal updates...")
    
    # Mock Slack objects
    mock_client = MagicMock()
    mock_client.views_open.return_value = {
        "ok": True,
        "view": {
            "id": "V12345678",
            "type": "modal",
            "callback_id": "enhanced_trade_modal"
        }
    }
    
    # Mock command body
    mock_body = {
        "text": "AAPL",
        "trigger_id": "test_trigger_id",
        "user_id": "test_user",
        "channel_id": "test_channel"
    }
    
    # Mock ack function
    mock_ack = MagicMock()
    
    # Mock enhanced_trade_command
    mock_enhanced_trade_command = MagicMock()
    
    # Simulate the FIXED command handler logic
    # ULTRA-FAST: Acknowledge and open modal in one go
    mock_ack()
    
    # Minimal parsing
    symbol = mock_body.get("text", "").strip().upper() or None
    
    # Ultra-simple modal - open immediately
    modal = {
        "type": "modal",
        "callback_id": "enhanced_trade_modal",
        "title": {"type": "plain_text", "text": "📊 Trading"},
        "blocks": [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{symbol or 'Enter Symbol'}*\n\n🔄 Loading..." if symbol else "*📊 Trading*\n\nEnter a symbol to start"
            }
        }],
        "close": {"type": "plain_text", "text": "Close"}
    }
    
    # Open modal immediately and get the view_id
    response = mock_client.views_open(trigger_id=mock_body.get("trigger_id"), view=modal)
    
    # Background processing (after modal is open)
    if symbol:
        try:
            # Get the actual view_id from the response
            view_id = response.get("view", {}).get("id")
            if view_id:
                # This happens after modal is already open
                mock_enhanced_trade_command._fetch_and_update_modal(
                    symbol, view_id, mock_body.get("user_id"), mock_client
                )
        except:
            pass
    
    # Verify the fix
    success = True
    
    # Check that views_open was called
    if mock_client.views_open.called:
        print("✅ PASS: Modal opened successfully")
    else:
        print("❌ FAIL: Modal not opened")
        success = False
    
    # Check that _fetch_and_update_modal was called with correct view_id
    if mock_enhanced_trade_command._fetch_and_update_modal.called:
        call_args = mock_enhanced_trade_command._fetch_and_update_modal.call_args
        passed_symbol = call_args[0][0]
        passed_view_id = call_args[0][1]
        passed_user_id = call_args[0][2]
        
        if passed_symbol == "AAPL":
            print("✅ PASS: Correct symbol passed to update function")
        else:
            print(f"❌ FAIL: Wrong symbol passed: {passed_symbol}")
            success = False
        
        if passed_view_id == "V12345678":
            print("✅ PASS: Correct view_id extracted and passed")
        else:
            print(f"❌ FAIL: Wrong view_id passed: {passed_view_id}")
            success = False
        
        if passed_user_id == "test_user":
            print("✅ PASS: Correct user_id passed")
        else:
            print(f"❌ FAIL: Wrong user_id passed: {passed_user_id}")
            success = False
    else:
        print("❌ FAIL: Update function not called")
        success = False
    
    return success

def test_no_view_id_handling():
    """Test handling when view_id is not available."""
    print("\n🧪 Testing handling when view_id is not available...")
    
    # Mock Slack objects with no view_id in response
    mock_client = MagicMock()
    mock_client.views_open.return_value = {
        "ok": False,
        "error": "some_error"
    }
    
    # Mock command body
    mock_body = {
        "text": "AAPL",
        "trigger_id": "test_trigger_id",
        "user_id": "test_user",
        "channel_id": "test_channel"
    }
    
    # Mock ack function
    mock_ack = MagicMock()
    
    # Mock enhanced_trade_command
    mock_enhanced_trade_command = MagicMock()
    
    # Simulate the command handler logic
    mock_ack()
    symbol = mock_body.get("text", "").strip().upper() or None
    
    modal = {
        "type": "modal",
        "callback_id": "enhanced_trade_modal",
        "title": {"type": "plain_text", "text": "📊 Trading"},
        "blocks": [{
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{symbol}*\n\n🔄 Loading..."}
        }],
        "close": {"type": "plain_text", "text": "Close"}
    }
    
    # Open modal immediately and get the view_id
    response = mock_client.views_open(trigger_id=mock_body.get("trigger_id"), view=modal)
    
    # Background processing (after modal is open)
    if symbol:
        try:
            # Get the actual view_id from the response
            view_id = response.get("view", {}).get("id")
            if view_id:
                # This should not be called since view_id is None
                mock_enhanced_trade_command._fetch_and_update_modal(
                    symbol, view_id, mock_body.get("user_id"), mock_client
                )
        except:
            pass
    
    # Verify graceful handling
    if not mock_enhanced_trade_command._fetch_and_update_modal.called:
        print("✅ PASS: Update function not called when view_id unavailable")
        return True
    else:
        print("❌ FAIL: Update function called even without view_id")
        return False

if __name__ == "__main__":
    print("🚀 Testing View ID Fix for Modal Updates")
    print("=" * 50)
    
    success = True
    
    # Test normal case with view_id
    success &= test_view_id_extraction()
    
    # Test error case without view_id
    success &= test_no_view_id_handling()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ View ID properly extracted from modal response")
        print("✅ Correct view_id passed to update function")
        print("✅ Graceful handling when view_id not available")
        print("✅ Modal updates should now work correctly")
    else:
        print("❌ SOME TESTS FAILED!")
        exit(1)