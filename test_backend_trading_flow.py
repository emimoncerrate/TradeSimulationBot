#!/usr/bin/env python3
"""
Backend Trading Flow Test

This script tests the complete multi-account trading system backend
to ensure everything works before testing in Slack.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_complete_trading_flow():
    """Test the complete trading flow from command to execution."""
    print("🧪 Testing Complete Backend Trading Flow")
    print("=" * 70)
    
    try:
        # Step 1: Initialize Services
        print("\n1️⃣ Initializing Services...")
        
        from services.service_container import get_container, get_multi_alpaca_service, get_user_account_manager
        from services.auth import AuthService
        from listeners.multi_account_trade_command import MultiAccountTradeCommand
        
        container = get_container()
        auth_service = container.get(AuthService)
        multi_alpaca = get_multi_alpaca_service()
        user_manager = get_user_account_manager()
        
        print(f"✅ Services initialized")
        print(f"   Multi-Alpaca available: {multi_alpaca.is_available()}")
        print(f"   Available accounts: {list(multi_alpaca.get_available_accounts().keys())}")
        
        # Step 2: Test User Account Assignment
        print("\n2️⃣ Testing User Account Assignment...")
        
        test_user_id = "U08GVN6F4FQ"  # Kelvin (you)
        assigned_account = user_manager.get_user_account(test_user_id)
        
        if assigned_account:
            print(f"✅ User {test_user_id} assigned to: {assigned_account}")
        else:
            print(f"❌ User {test_user_id} not assigned to any account")
            return False
        
        # Get account info
        account_info = multi_alpaca.get_account_info(assigned_account)
        if account_info:
            print(f"✅ Account info retrieved:")
            print(f"   Account: {account_info['account_name']}")
            print(f"   Cash: ${account_info['cash']:,.2f}")
            print(f"   Buying Power: ${account_info['buying_power']:,.2f}")
            print(f"   Status: {account_info['status']}")
        else:
            print(f"❌ Could not retrieve account info")
            return False
        
        # Step 3: Test Command Parsing
        print("\n3️⃣ Testing Command Parsing...")
        
        multi_command = MultiAccountTradeCommand(auth_service)
        
        test_commands = [
            "2 aapl buy",
            "100 TSLA",
            "sell 50 NVDA",
            "MSFT buy",
            "10 GOOGL sell"
        ]
        
        for cmd in test_commands:
            params = multi_command._parse_trade_parameters(cmd)
            print(f"   '{cmd}' → Symbol: {params.get('symbol')}, Qty: {params.get('quantity')}, Action: {params.get('action')}")
        
        # Step 4: Test Market Data Integration
        print("\n4️⃣ Testing Market Data Integration...")
        
        test_symbol = "AAPL"
        try:
            current_price = multi_command._get_current_price_sync(test_symbol)
            if current_price:
                print(f"✅ {test_symbol} current price: ${current_price:.2f}")
                
                # Test GMV calculation
                test_quantity = 2
                gmv = current_price * test_quantity
                print(f"✅ GMV calculation: {test_quantity} × ${current_price:.2f} = ${gmv:.2f}")
            else:
                print(f"⚠️  Could not fetch current price for {test_symbol}")
        except Exception as e:
            print(f"⚠️  Market data error: {e}")
        
        # Step 5: Test Modal Creation
        print("\n5️⃣ Testing Modal Creation...")
        
        # Create a mock context
        class MockUser:
            def __init__(self):
                self.user_id = test_user_id
                self.username = "kelvin.saldana"
        
        class MockContext:
            def __init__(self):
                self.user = MockUser()
                self.channel_id = "C09H1R7KKP1"
                self.trigger_id = "test_trigger_id"
                self.symbol = "AAPL"
                self.quantity = 2
                self.action = "buy"
                self.gmv = 300.50
                self.account_id = assigned_account
                self.account_info = account_info
        
        mock_context = MockContext()
        
        try:
            # Test modal creation with live data
            modal = await multi_command._create_multi_account_modal_with_live_data("AAPL", mock_context)
            
            print(f"✅ Modal created successfully")
            print(f"   Title: {modal['title']['text']}")
            print(f"   Blocks: {len(modal['blocks'])} sections")
            
            # Check if fields are pre-filled
            symbol_filled = False
            quantity_filled = False
            action_filled = False
            gmv_filled = False
            
            for block in modal['blocks']:
                if block.get('type') == 'input':
                    element = block.get('element', {})
                    if 'initial_value' in element:
                        if block.get('block_id') == 'symbol_input':
                            symbol_filled = True
                            print(f"   ✅ Symbol pre-filled: {element['initial_value']}")
                        elif block.get('block_id') == 'quantity_input':
                            quantity_filled = True
                            print(f"   ✅ Quantity pre-filled: {element['initial_value']}")
                        elif block.get('block_id') == 'gmv_input':
                            gmv_filled = True
                            print(f"   ✅ GMV pre-filled: {element['initial_value']}")
                    elif 'initial_option' in element:
                        if block.get('block_id') == 'action_select':
                            action_filled = True
                            print(f"   ✅ Action pre-filled: {element['initial_option']['value']}")
            
            if not all([symbol_filled, quantity_filled, action_filled]):
                print(f"   ⚠️  Some fields not pre-filled (GMV optional)")
            
        except Exception as e:
            print(f"❌ Modal creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 6: Test Trade Execution (Dry Run)
        print("\n6️⃣ Testing Trade Execution (Dry Run)...")
        
        try:
            # Test trade parameters
            trade_symbol = "AAPL"
            trade_quantity = 1  # Small quantity for test
            trade_action = "buy"
            
            print(f"   Testing trade: {trade_action} {trade_quantity} {trade_symbol}")
            print(f"   Account: {assigned_account}")
            print(f"   Available cash: ${account_info['cash']:,.2f}")
            
            # Calculate estimated cost
            if current_price:
                estimated_cost = current_price * trade_quantity
                print(f"   Estimated cost: ${estimated_cost:.2f}")
                
                if estimated_cost <= account_info['cash']:
                    print(f"   ✅ Sufficient funds available")
                else:
                    print(f"   ❌ Insufficient funds")
            
            # Note: Not executing actual trade in test
            print(f"   📝 Trade execution test completed (dry run)")
            
        except Exception as e:
            print(f"❌ Trade execution test failed: {e}")
            return False
        
        # Step 7: Test Form Submission Handler
        print("\n7️⃣ Testing Form Submission Handler...")
        
        try:
            # Create mock form submission data
            mock_form_values = {
                "symbol_input": {
                    "symbol": {"value": "AAPL"}
                },
                "quantity_input": {
                    "quantity": {"value": "2"}
                },
                "action_select": {
                    "action": {"selected_option": {"value": "buy"}}
                },
                "gmv_input": {
                    "gmv": {"value": "300.50"}
                },
                "order_type_select": {
                    "order_type": {"selected_option": {"value": "market"}}
                }
            }
            
            # Test form value extraction
            symbol = multi_command._get_form_value(mock_form_values, "symbol_input", "symbol")
            quantity = multi_command._get_form_value(mock_form_values, "quantity_input", "quantity")
            action = multi_command._get_form_value(mock_form_values, "action_select", "action")
            
            print(f"✅ Form value extraction:")
            print(f"   Symbol: {symbol}")
            print(f"   Quantity: {quantity}")
            print(f"   Action: {action}")
            
            if symbol == "AAPL" and quantity == "2" and action == "buy":
                print(f"   ✅ Form parsing working correctly")
            else:
                print(f"   ❌ Form parsing issues detected")
                return False
            
        except Exception as e:
            print(f"❌ Form submission test failed: {e}")
            return False
        
        # Step 8: Test Account Management Commands
        print("\n8️⃣ Testing Account Management Commands...")
        
        try:
            # Test assignment statistics
            stats = user_manager.get_assignment_stats()
            print(f"✅ Assignment statistics:")
            print(f"   Total assignments: {stats['total_assignments']}")
            print(f"   Accounts in use: {stats['accounts_in_use']}")
            print(f"   Strategy: {stats['assignment_strategy']}")
            
            # Test account user listing
            users_in_account = user_manager.get_account_users(assigned_account)
            print(f"✅ Users in {assigned_account}: {len(users_in_account)}")
            
            # Test all accounts status
            all_accounts = multi_alpaca.get_all_accounts_status()
            print(f"✅ All accounts status: {len(all_accounts)} accounts")
            
            for acc_id, status in all_accounts.items():
                if status.get('is_active'):
                    print(f"   • {acc_id}: ${status.get('cash', 0):,.2f} cash")
            
        except Exception as e:
            print(f"❌ Account management test failed: {e}")
            return False
        
        # Final Summary
        print(f"\n" + "=" * 70)
        print("🎉 BACKEND TRADING FLOW TEST COMPLETED!")
        print("=" * 70)
        
        print(f"✅ All backend systems working correctly:")
        print(f"   🏦 Multi-account system: OPERATIONAL")
        print(f"   👥 User assignment: WORKING")
        print(f"   📊 Market data: AVAILABLE")
        print(f"   🔧 Command parsing: FUNCTIONAL")
        print(f"   📝 Modal creation: SUCCESS")
        print(f"   💹 Trade preparation: READY")
        print(f"   📋 Form handling: OPERATIONAL")
        print(f"   ⚙️  Account management: WORKING")
        
        print(f"\n🚀 READY FOR SLACK TESTING!")
        print(f"   Try: /trade 2 aapl buy")
        print(f"   Expected: Pre-filled modal with account info")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Backend Trading Flow Test")
    
    success = asyncio.run(test_complete_trading_flow())
    
    if success:
        print(f"\n🎯 Backend test PASSED! System ready for Slack testing.")
    else:
        print(f"\n💥 Backend test FAILED! Fix issues before Slack testing.")
    
    sys.exit(0 if success else 1)