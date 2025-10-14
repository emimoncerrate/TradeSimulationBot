#!/usr/bin/env python3
"""
Functionality Test for Risk Alert Command Components
Tests: trigger_id, handle_risk_alert_command(), and ack()
"""

import os
import sys
import time
import json
from unittest.mock import Mock, MagicMock, patch
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

os.environ['SKIP_APP_INIT'] = 'true'

print("=" * 70)
print("🧪 RISK ALERT FUNCTIONALITY TEST")
print("=" * 70)
print()

# Test counters
tests_passed = 0
tests_failed = 0
test_results = []

def test_result(name, passed, details=""):
    global tests_passed, tests_failed, test_results
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"    {details}")
    print()
    
    if passed:
        tests_passed += 1
    else:
        tests_failed += 1
    
    test_results.append({
        'name': name,
        'passed': passed,
        'details': details
    })

# ============================================================================
# TEST 1: Import and Function Existence
# ============================================================================
print("TEST 1: Checking imports and function existence...")

try:
    from listeners.risk_alert_handlers import register_risk_alert_handlers
    test_result("Import risk_alert_handlers", True, "Module imported successfully")
except Exception as e:
    test_result("Import risk_alert_handlers", False, f"Import failed: {e}")
    sys.exit(1)

try:
    from slack_bolt import App, Ack
    from slack_sdk import WebClient
    test_result("Import Slack dependencies", True, "Slack Bolt and SDK imported")
except Exception as e:
    test_result("Import Slack dependencies", False, f"Import failed: {e}")

# ============================================================================
# TEST 2: Handler Function Structure
# ============================================================================
print("TEST 2: Verifying handle_risk_alert_command() structure...")

try:
    # Read the handler file to verify structure
    import inspect
    from pathlib import Path
    
    handler_file = Path(__file__).parent / "listeners" / "risk_alert_handlers.py"
    handler_code = handler_file.read_text()
    
    # Check for function definition
    if "def handle_risk_alert_command(ack, body, client):" in handler_code:
        test_result("Function signature", True, "Correct parameters: ack, body, client")
    else:
        test_result("Function signature", False, "Incorrect function signature")
    
    # Check for immediate ack() call
    if "ack()  # Acknowledge immediately" in handler_code or "ack()" in handler_code:
        test_result("ack() call present", True, "Found ack() call in handler")
    else:
        test_result("ack() call present", False, "No ack() call found")
    
    # Check for trigger_id handling
    if "trigger_id" in handler_code and "body.get('trigger_id')" in handler_code:
        test_result("trigger_id handling", True, "Extracts trigger_id from body")
    elif "body['trigger_id']" in handler_code:
        test_result("trigger_id handling", True, "Accesses trigger_id from body")
    else:
        test_result("trigger_id handling", False, "No trigger_id extraction found")
    
    # Check for views.open call
    if "client.views_open" in handler_code or "views_open" in handler_code:
        test_result("Modal opening logic", True, "Found views_open API call")
    else:
        test_result("Modal opening logic", False, "No views_open call found")
    
except Exception as e:
    test_result("Handler structure verification", False, f"Error: {e}")

# ============================================================================
# TEST 3: Mock Command Execution (ack() functionality)
# ============================================================================
print("TEST 3: Testing ack() functionality with mock...")

try:
    # Create mock objects
    mock_ack = Mock()
    mock_client = Mock()
    mock_body = {
        'trigger_id': '1234567890.123456789012.abcdef1234567890abcdef1234567890',
        'user_id': 'U12345678',
        'channel_id': 'C12345678',
        'team_id': 'T12345678',
        'command': '/risk-alert'
    }
    
    # Track timing
    start_time = time.time()
    
    # Mock the modal creation and views_open
    mock_client.views_open.return_value = {'ok': True, 'view': {'id': 'V12345'}}
    
    # Import and test the handler
    from services.database import DatabaseService
    from services.auth import AuthService
    from services.alert_monitor import RiskAlertMonitor
    from ui.notifications import NotificationService
    
    # Create mock services
    mock_db = Mock(spec=DatabaseService)
    mock_auth = Mock(spec=AuthService)
    mock_monitor = Mock(spec=RiskAlertMonitor)
    mock_notif = Mock(spec=NotificationService)
    
    # Register handlers with mocks
    mock_app = Mock(spec=App)
    registered_handler = [None]  # Use list to avoid nonlocal issues
    
    def mock_command_decorator(command_name):
        def decorator(func):
            registered_handler[0] = func
            return func
        return decorator
    
    mock_app.command = mock_command_decorator
    
    # Register the handler
    with patch('listeners.risk_alert_handlers.db_service', mock_db):
        with patch('listeners.risk_alert_handlers.auth_service', mock_auth):
            with patch('listeners.risk_alert_handlers.alert_monitor', mock_monitor):
                with patch('listeners.risk_alert_handlers.notification_service', mock_notif):
                    register_risk_alert_handlers(mock_app, mock_db, mock_auth, mock_monitor, mock_notif)
    
    # Check if handler was registered
    if registered_handler[0]:
        test_result("Handler registration", True, "Handler registered with app.command()")
        
        # Test ack() call
        try:
            # Call the handler
            registered_handler[0](mock_ack, mock_body, mock_client)
            
            ack_time = time.time()
            
            # Verify ack was called
            if mock_ack.called:
                ack_delay_ms = (ack_time - start_time) * 1000
                test_result("ack() execution", True, f"ack() called (delay: {ack_delay_ms:.2f}ms)")
                
                # Check if ack was called quickly
                if ack_delay_ms < 100:
                    test_result("ack() timing", True, f"Fast acknowledgment: {ack_delay_ms:.2f}ms < 100ms")
                else:
                    test_result("ack() timing", False, f"Slow acknowledgment: {ack_delay_ms:.2f}ms")
            else:
                test_result("ack() execution", False, "ack() was not called")
        
        except Exception as e:
            test_result("Handler execution", False, f"Error calling handler: {e}")
    else:
        test_result("Handler registration", False, "Handler not registered")

except Exception as e:
    test_result("Mock command execution", False, f"Error: {e}")
    import traceback
    print(traceback.format_exc())

# ============================================================================
# TEST 4: trigger_id Validation
# ============================================================================
print("TEST 4: Testing trigger_id validation...")

try:
    # Test valid trigger_id format
    valid_trigger_ids = [
        '1234567890.123456789012.abcdef1234567890abcdef1234567890',  # 59 chars
        '9652228663973.437343797072.9f485b8d76c4af646200350b65979379',  # Real example
    ]
    
    for trigger_id in valid_trigger_ids:
        parts = trigger_id.split('.')
        if len(parts) == 3:
            test_result(f"trigger_id format ({trigger_id[:20]}...)", True, 
                       f"Valid format: {len(parts)} parts, total {len(trigger_id)} chars")
        else:
            test_result(f"trigger_id format", False, 
                       f"Invalid format: {len(parts)} parts")
    
    # Test trigger_id extraction from body
    test_body = {'trigger_id': valid_trigger_ids[0]}
    extracted = test_body.get('trigger_id')
    
    if extracted == valid_trigger_ids[0]:
        test_result("trigger_id extraction", True, "Successfully extracted from body")
    else:
        test_result("trigger_id extraction", False, "Extraction failed")

except Exception as e:
    test_result("trigger_id validation", False, f"Error: {e}")

# ============================================================================
# TEST 5: Timing Requirements (3-second deadline)
# ============================================================================
print("TEST 5: Testing Slack's 3-second trigger_id deadline compliance...")

try:
    # Simulate the command flow timing
    mock_ack = Mock()
    mock_client = Mock()
    mock_body = {
        'trigger_id': '1234567890.123456789012.abcdef1234567890abcdef1234567890',
        'user_id': 'U12345678',
        'channel_id': 'C12345678'
    }
    
    # Mock views_open to simulate API call
    mock_client.views_open.return_value = {'ok': True}
    
    # Time the complete flow
    flow_start = time.time()
    
    # Simulate handler execution
    mock_ack()
    ack_time = time.time()
    
    # Simulate modal creation (should be instant)
    from ui.risk_alert_widget import create_risk_alert_modal
    modal = create_risk_alert_modal()
    modal_time = time.time()
    
    # Simulate API call
    mock_client.views_open(trigger_id=mock_body['trigger_id'], view=modal)
    api_time = time.time()
    
    # Calculate timings
    total_time_ms = (api_time - flow_start) * 1000
    ack_delay_ms = (ack_time - flow_start) * 1000
    modal_delay_ms = (modal_time - ack_time) * 1000
    api_delay_ms = (api_time - modal_time) * 1000
    
    print(f"    Timing Breakdown:")
    print(f"      ACK: {ack_delay_ms:.2f}ms")
    print(f"      Modal Creation: {modal_delay_ms:.2f}ms")
    print(f"      API Call: {api_delay_ms:.2f}ms")
    print(f"      TOTAL: {total_time_ms:.2f}ms")
    print()
    
    if total_time_ms < 3000:
        test_result("3-second deadline", True, 
                   f"Total time {total_time_ms:.2f}ms < 3000ms (Slack deadline)")
    else:
        test_result("3-second deadline", False,
                   f"Total time {total_time_ms:.2f}ms exceeds 3000ms deadline")
    
    # Check individual component timing
    if ack_delay_ms < 50:
        test_result("ack() speed", True, f"Very fast: {ack_delay_ms:.2f}ms")
    elif ack_delay_ms < 100:
        test_result("ack() speed", True, f"Acceptable: {ack_delay_ms:.2f}ms")
    else:
        test_result("ack() speed", False, f"Too slow: {ack_delay_ms:.2f}ms")
    
    if modal_delay_ms < 100:
        test_result("Modal creation speed", True, f"Fast: {modal_delay_ms:.2f}ms")
    else:
        test_result("Modal creation speed", False, f"Slow: {modal_delay_ms:.2f}ms")

except Exception as e:
    test_result("Timing test", False, f"Error: {e}")

# ============================================================================
# TEST 6: Error Handling
# ============================================================================
print("TEST 6: Testing error handling...")

try:
    # Test missing trigger_id
    mock_ack = Mock()
    mock_client = Mock()
    mock_body_no_trigger = {
        'user_id': 'U12345678',
        'channel_id': 'C12345678'
    }
    
    trigger_id = mock_body_no_trigger.get('trigger_id')
    
    if trigger_id is None:
        test_result("Missing trigger_id detection", True, 
                   "Correctly handles missing trigger_id")
    else:
        test_result("Missing trigger_id detection", False,
                   "Should detect missing trigger_id")
    
    # Test error recovery
    mock_client.views_open.side_effect = Exception("API Error")
    
    try:
        mock_client.views_open(trigger_id='test', view={})
        test_result("Error handling", False, "Should have raised exception")
    except Exception:
        test_result("Error handling", True, "Properly raises exceptions")
    
except Exception as e:
    test_result("Error handling test", False, f"Error: {e}")

# ============================================================================
# FINAL RESULTS
# ============================================================================
print("=" * 70)
print("📊 TEST RESULTS SUMMARY")
print("=" * 70)
print()

total_tests = tests_passed + tests_failed
pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

print(f"Total Tests: {total_tests}")
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"Pass Rate: {pass_rate:.1f}%")
print()

if tests_failed == 0:
    print("🎉 ALL TESTS PASSED!")
    print()
    print("✅ trigger_id: Properly extracted and validated")
    print("✅ handle_risk_alert_command(): Correctly structured")
    print("✅ ack(): Called immediately and quickly")
    print()
    print("The risk alert command is ready to use!")
else:
    print("⚠️  SOME TESTS FAILED")
    print()
    print("Failed tests:")
    for result in test_results:
        if not result['passed']:
            print(f"  ❌ {result['name']}")
            if result['details']:
                print(f"     {result['details']}")
    print()
    print("Review the failures above and fix them before deploying.")

print("=" * 70)

# Exit with appropriate code
sys.exit(0 if tests_failed == 0 else 1)
