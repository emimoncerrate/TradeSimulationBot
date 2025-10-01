#!/usr/bin/env python3
"""
TradeSimulator - Slack Webhook Connection Test
This script sends a test message to Slack using an Incoming Webhook URL.
"""

import requests
import json

# ============================================================================
# WEBHOOK URL CONFIGURATION
# ============================================================================
# TODO: Replace the placeholder below with your actual Incoming Webhook URL
# Your Webhook URL should look like:
# https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
# ============================================================================

WEBHOOK_URL = "https://hooks.slack.com/services/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"


def send_test_message(webhook_url):
    """
    Sends a test message to Slack via Incoming Webhook.
    
    Args:
        webhook_url (str): The Slack Incoming Webhook URL
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    # Define the JSON payload as a Python dictionary
    payload = {
        "text": "Maurice is cool too!",
        "username": "TradeBot",
        "icon_emoji": ":money_with_wings:"
    }
    
    # Convert the payload to JSON format
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Send POST request to Slack Webhook URL
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers=headers
        )
        
        # Check the HTTP status code
        if response.status_code == 200:
            print("✓ SUCCESS: Message sent to Slack successfully!")
            print(f"  Status Code: {response.status_code}")
            print(f"  Response: {response.text}")
            return True
        else:
            print("✗ ERROR: Failed to send message to Slack.")
            print(f"  Status Code: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print("✗ ERROR: An exception occurred while sending the request.")
        print(f"  Exception: {str(e)}")
        return False


def main():
    """
    Main function to execute the Slack connection test.
    """
    print("=" * 60)
    print("TradeSimulator - Slack Webhook Connection Test")
    print("=" * 60)
    print()
    
    # Validate that the webhook URL has been configured
    if WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
        print("⚠ WARNING: Please configure your Webhook URL first!")
        print("  Edit this script and replace 'YOUR_WEBHOOK_URL_HERE'")
        print("  with your actual Slack Incoming Webhook URL.")
        print()
        return
    
    print(f"Sending test message to Slack...")
    print(f"Webhook URL: {WEBHOOK_URL[:50]}...")
    print()
    
    # Send the test message
    success = send_test_message(WEBHOOK_URL)
    
    print()
    if success:
        print("Connection test completed successfully! 🎉")
    else:
        print("Connection test failed. Please check your Webhook URL and try again.")
    print("=" * 60)


if __name__ == "__main__":
    main()

