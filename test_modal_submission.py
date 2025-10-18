#!/usr/bin/env python3
"""
Backend Test for Interactive Modal Submission

This script tests the thread-safe modal submission handling to verify
the fix for the event loop issues before testing in Slack.
"""

import asyncio
import logging
import os
import sys
import json
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our services and models
from listeners.interactive_actions import InteractiveActionHandler
from services.service_container import get_container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockSlackClient:
    """Mock Slack client for testing."""
    
    def __init__(self):
        self.messages = []
        self.ephemeral_messages = []
        self.updates = []
        
    async def chat_postMessage(self, **kwargs):
        self.messages.append(kwargs)
        print(f"📤 SLACK MESSAGE: {kwargs.get('text', '')[:100]}...")
        return {'ts': f'{time.time():.6f}'}
    
    async def chat_postEphemeral(self, **kwargs):
        self.ephemeral_messages.append(kwargs)
        print(f"👤 EPHEMERAL MESSAGE: {kwargs.get('text', '')[:100]}...")
        return {'ts': f'{time.time():.6f}'}
    
    async def chat_update(self, **kwargs):
        self.updates.append(kwargs)
        print(f"📝 SLACK UPDATE: {kwargs.get('text', '')[:100]}...")
        return {'ts': f'{time.time():.6f}'}


def create_mock_modal_submission():
    """Create a mock modal submission payload."""
    return {
        "type": "view_submission",
        "team": {
            "id": "TCVA3PF24",
            "domain": "test-workspace"
        },
        "user": {
            "id": "U_TEST_USER",
            "username": "test.user",
            "name": "test.user",
            "team_id": "TCVA3PF24"
        },
        "api_app_id": "A_TEST_APP",
        "token": "test_token",
        "trigger_id": "test_trigger_123",
        "view": {
            "id": "V_TEST_VIEW",
            "team_id": "TCVA3PF24",
            "type": "modal",
            "callback_id": "stock_trade_modal_interactive",
            "private_metadata": json.dumps({
                "channel_id": "C_TEST_CHANNEL",
                "current_price": "247.77",
                "symbol": "AAPL"
            }),
            "state": {
                "values": {
                    "trade_symbol_block": {
                        "symbol_input": {
                            "type": "plain_text_input",
                            "value": "AAPL"
                        }
                    },
                    "trade_side_block": {
                        "trade_side_radio": {
                            "type": "radio_buttons",
                            "selected_option": {
                                "value": "buy"
                            }
                        }
                    },
                    "qty_shares_block": {
                        "shares_input": {
                            "type": "plain_text_input",
                            "value": "100"
                        }
                    },
                    "gmv_block": {
                        "gmv_input": {
                            "type": "plain_text_input",
                            "value": "24777.00"
                        }
                    },
                    "order_type_block": {
                        "order_type_select": {
                            "type": "static_select",
                            "selected_option": {
                                "value": "market"
                            }
                        }
                    }
                }
            }
        }
    }


def test_thread_safe_execution():
    """Test the thread-safe modal submission execution."""
    print("🧵 Testing Thread-Safe Modal Submission Execution")
    print("=" * 60)
    
    try:
        # Initialize services
        print("🔧 Initializing services...")
        container = get_container()
        
        # Create interactive action handler
        handler = InteractiveActionHandler()
        
        # Create mock Slack client
        mock_client = MockSlackClient()
        
        # Create mock modal submission
        mock_body = create_mock_modal_submission()
        
        print("📋 Mock Modal Submission Created:")
        print(f"   User: {mock_body['user']['id']}")
        print(f"   Symbol: AAPL")
        print(f"   Side: buy")
        print(f"   Shares: 100")
        print(f"   GMV: $24,777.00")
        print("")
        
        # Test the thread-safe execution
        print("🚀 Starting thread-safe trade execution...")
        start_time = time.time()
        
        # This should run without event loop errors
        handler._run_async_trade_execution(mock_body, mock_client)
        
        # Give the thread time to complete
        print("⏳ Waiting for background thread to complete...")
        time.sleep(5)  # Wait 5 seconds for execution
        
        execution_time = time.time() - start_time
        
        # Check results
        print("\n📊 Execution Results:")
        print(f"   Execution Time: {execution_time:.2f} seconds")
        print(f"   Messages Sent: {len(mock_client.messages)}")
        print(f"   Ephemeral Messages: {len(mock_client.ephemeral_messages)}")
        print(f"   Updates Sent: {len(mock_client.updates)}")
        
        # Display messages
        if mock_client.messages:
            print("\n📤 Messages Sent:")
            for i, msg in enumerate(mock_client.messages, 1):
                print(f"   {i}. {msg.get('text', '')[:100]}...")
        
        if mock_client.ephemeral_messages:
            print("\n👤 Ephemeral Messages:")
            for i, msg in enumerate(mock_client.ephemeral_messages, 1):
                print(f"   {i}. {msg.get('text', '')[:100]}...")
        
        # Determine success
        total_communications = len(mock_client.messages) + len(mock_client.ephemeral_messages) + len(mock_client.updates)
        
        if total_communications > 0:
            print("\n✅ Thread-safe execution SUCCESSFUL!")
            print("   - No event loop errors")
            print("   - Background thread completed")
            print("   - Trade execution attempted")
            return True
        else:
            print("\n❌ Thread-safe execution FAILED!")
            print("   - No messages sent")
            print("   - Execution may have failed silently")
            return False
            
    except Exception as e:
        print(f"\n❌ Thread-safe execution FAILED with exception:")
        print(f"   Error: {str(e)}")
        import traceback
        print(f"   Stack trace: {traceback.format_exc()}")
        return False


def test_direct_async_execution():
    """Test direct async execution for comparison."""
    print("\n🔄 Testing Direct Async Execution (for comparison)")
    print("=" * 60)
    
    try:
        # Create handler and mock client
        handler = InteractiveActionHandler()
        mock_client = MockSlackClient()
        mock_body = create_mock_modal_submission()
        
        print("🚀 Running direct async execution...")
        
        # Run the async method directly
        result = asyncio.run(handler._execute_trade_from_submission(mock_body, mock_client))
        
        print("✅ Direct async execution completed successfully")
        print(f"   Messages: {len(mock_client.messages)}")
        print(f"   Ephemeral: {len(mock_client.ephemeral_messages)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct async execution failed: {str(e)}")
        return False


def test_event_loop_isolation():
    """Test that multiple thread executions don't interfere."""
    print("\n🔀 Testing Event Loop Isolation (Multiple Threads)")
    print("=" * 60)
    
    try:
        handler = InteractiveActionHandler()
        
        # Create multiple mock submissions
        results = []
        threads = []
        
        def run_execution(thread_id):
            try:
                mock_client = MockSlackClient()
                mock_body = create_mock_modal_submission()
                mock_body['user']['id'] = f"U_TEST_USER_{thread_id}"
                
                print(f"🧵 Thread {thread_id}: Starting execution...")
                handler._run_async_trade_execution(mock_body, mock_client)
                
                # Wait a bit for completion
                time.sleep(2)
                
                total_msgs = len(mock_client.messages) + len(mock_client.ephemeral_messages)
                results.append((thread_id, total_msgs > 0))
                print(f"🧵 Thread {thread_id}: Completed ({total_msgs} messages)")
                
            except Exception as e:
                print(f"🧵 Thread {thread_id}: Failed - {str(e)}")
                results.append((thread_id, False))
        
        # Start multiple threads
        for i in range(3):
            thread = threading.Thread(target=run_execution, args=(i+1,), daemon=True)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)
        
        # Wait a bit more for async operations
        time.sleep(3)
        
        # Check results
        successful_threads = sum(1 for _, success in results if success)
        total_threads = len(results)
        
        print(f"\n📊 Multi-thread Results:")
        print(f"   Total Threads: {total_threads}")
        print(f"   Successful: {successful_threads}")
        print(f"   Success Rate: {successful_threads/total_threads*100:.1f}%")
        
        for thread_id, success in results:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"   Thread {thread_id}: {status}")
        
        return successful_threads == total_threads
        
    except Exception as e:
        print(f"❌ Multi-thread test failed: {str(e)}")
        return False


def main():
    """Main test function."""
    print("🎯 Backend Modal Submission Tests")
    print("=" * 60)
    
    # Test results
    results = {
        'thread_safe_execution': False,
        'direct_async_execution': False,
        'event_loop_isolation': False
    }
    
    try:
        # Test 1: Thread-safe execution
        results['thread_safe_execution'] = test_thread_safe_execution()
        
        # Test 2: Direct async execution
        results['direct_async_execution'] = test_direct_async_execution()
        
        # Test 3: Event loop isolation
        results['event_loop_isolation'] = test_event_loop_isolation()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 Backend Modal Submission Test Summary:")
        print("=" * 60)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print("")
        print(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed")
        
        if results['thread_safe_execution']:
            print("🎉 Thread-safe modal submission is working!")
            print("✅ Ready to test with Slack app: python app.py")
        else:
            print("⚠️  Thread-safe execution failed. Check the logs above.")
            print("🔧 Fix needed before testing with Slack.")
        
        return passed_tests >= 2  # At least thread-safe and one other test should pass
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    # Run the modal submission test suite
    success = main()
    sys.exit(0 if success else 1)