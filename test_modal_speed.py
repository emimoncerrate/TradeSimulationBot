#!/usr/bin/env python3
"""
Test modal opening speed
This adds a /test-modal command that opens a simple modal immediately
"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from slack_bolt import App

# Create minimal app
app = App(
    token=os.getenv('SLACK_BOT_TOKEN'),
    signing_secret=os.getenv('SLACK_SIGNING_SECRET')
)

@app.command("/test-modal")
def handle_test_modal(ack, body, client):
    """Ultra-fast modal test - opens immediately"""
    import time
    start = time.time()
    
    ack()
    ack_time = time.time()
    
    # Simplest possible modal
    modal = {
        "type": "modal",
        "title": {"type": "plain_text", "text": "Test Modal"},
        "close": {"type": "plain_text", "text": "Close"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "plain_text", "text": "✅ Modal opened successfully!"}
            }
        ]
    }
    
    modal_time = time.time()
    
    try:
        client.views_open(
            trigger_id=body['trigger_id'],
            view=modal
        )
        open_time = time.time()
        
        print(f"✅ SUCCESS!")
        print(f"  ACK: {(ack_time-start)*1000:.1f}ms")
        print(f"  Modal create: {(modal_time-ack_time)*1000:.1f}ms")
        print(f"  API call: {(open_time-modal_time)*1000:.1f}ms")
        print(f"  TOTAL: {(open_time-start)*1000:.1f}ms")
        
    except Exception as e:
        error_time = time.time()
        print(f"❌ FAILED after {(error_time-start)*1000:.1f}ms")
        print(f"  Error: {e}")
        if hasattr(e, 'response'):
            print(f"  Response: {e.response}")

if __name__ == "__main__":
    print("🧪 Starting test modal server...")
    print("Use /test-modal in Slack to test")
    print("Press Ctrl+C to stop")
    
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    handler = SocketModeHandler(app, os.getenv('SLACK_APP_TOKEN'))
    handler.start()

