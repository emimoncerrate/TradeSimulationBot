#!/usr/bin/env python3
"""
Test the full app startup without running the server.
"""

import os
from dotenv import load_dotenv
load_dotenv()

def test_full_app():
    """Test that the full app can initialize."""
    print("🧪 Testing Full App Initialization")
    print("=" * 50)
    
    try:
        # Test configuration
        from config.settings import get_config
        config = get_config()
        print("✅ Configuration loaded")
        
        # Test service container
        from services.service_container import get_container
        container = get_container()
        print("✅ Service container initialized")
        
        # Test Slack app creation (without starting)
        from app import create_slack_app
        app = create_slack_app()
        print("✅ Slack app created successfully")
        
        print("\n🎉 SUCCESS! Full app can initialize properly")
        print("🚀 Ready to run: python3 app.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_full_app()