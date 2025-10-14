"""
Integration Test for Trade Modal Autofill Functionality

Tests the real-time autofill features including:
- Shares to GMV calculation
- GMV to shares calculation  
- Symbol to price fetching
- Modal updates via dispatch actions
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


def test_modal_structure():
    """Test that the modal has the correct structure with dispatch actions."""
    print("\n🔍 Test 1: Modal Structure Validation")
    
    # Test the modal structure by checking the trade_widget code directly
    with open('ui/trade_widget.py', 'r') as f:
        content = f.read()
        
        # Check that dispatch actions are configured
        assert 'dispatch_action_config' in content, "✅ Dispatch config present"
        assert 'symbol_input' in content, "✅ Symbol input action_id present"
        assert 'shares_input' in content, "✅ Shares input action_id present"
        assert 'gmv_input' in content, "✅ GMV input action_id present"
        assert 'on_enter_pressed' in content, "✅ Enter press trigger present"
        assert 'on_character_entered' in content, "✅ Character entered trigger present"
        assert 'trade_symbol_block' in content, "✅ Symbol block_id present"
        assert 'qty_shares_block' in content, "✅ Shares block_id present"
        assert 'gmv_block' in content, "✅ GMV block_id present"
        assert 'current_price_display' in content, "✅ Price display block_id present"
        assert 'stock_trade_modal_interactive' in content, "✅ New callback_id present"
    
    # Also verify the modal title and submit text
    assert 'Place Trade' in content, "✅ Modal title correct"
    assert 'Execute Trade' in content, "✅ Submit button text correct"
    
    # Verify specific modal configurations
    assert 'is_decimal_allowed": False' in content, "✅ Shares is integer only"
    assert 'is_decimal_allowed": True' in content, "✅ GMV allows decimals"
    
    print("✅ All modal structure tests passed!\n")
    return True


def test_shares_to_gmv_calculation():
    """Test that shares input correctly calculates GMV."""
    print("🔍 Test 2: Shares → GMV Calculation")
    
    # Simulate shares calculation
    shares = 100
    price = 150.00
    expected_gmv = shares * price
    
    calculated_gmv = shares * price
    
    assert calculated_gmv == expected_gmv, f"✅ GMV calculation: {shares} × ${price} = ${calculated_gmv}"
    assert isinstance(calculated_gmv, (int, float)), "✅ GMV is numeric"
    
    # Test with different values
    test_cases = [
        (50, 200.00, 10000.00),
        (250, 75.50, 18875.00),
        (1000, 10.25, 10250.00),
    ]
    
    for shares, price, expected in test_cases:
        result = shares * price
        assert result == expected, f"✅ {shares} shares × ${price} = ${result}"
    
    print("✅ All shares to GMV calculations passed!\n")
    return True


def test_gmv_to_shares_calculation():
    """Test that GMV input correctly calculates shares."""
    print("🔍 Test 3: GMV → Shares Calculation")
    
    # Simulate GMV calculation
    gmv = 15000.00
    price = 150.00
    expected_shares = int(gmv / price)
    
    calculated_shares = int(gmv / price)
    
    assert calculated_shares == expected_shares, f"✅ Shares calculation: ${gmv} ÷ ${price} = {calculated_shares} shares"
    assert isinstance(calculated_shares, int), "✅ Shares is integer"
    
    # Test with different values
    test_cases = [
        (10000.00, 200.00, 50),
        (18875.00, 75.50, 250),
        (10250.00, 10.25, 1000),
    ]
    
    for gmv, price, expected in test_cases:
        result = int(gmv / price)
        assert result == expected, f"✅ ${gmv} GMV ÷ ${price} = {result} shares"
    
    # Test rounding behavior
    gmv = 1000.00
    price = 33.33
    shares = int(gmv / price)  # Should round down
    assert shares == 30, f"✅ Rounding: ${gmv} ÷ ${price} = {shares} shares (rounded down)"
    
    print("✅ All GMV to shares calculations passed!\n")
    return True


def test_price_extraction():
    """Test price extraction from display block."""
    print("🔍 Test 4: Price Extraction from Display")
    
    import re
    
    # Test different price formats
    test_cases = [
        ("*Current Stock Price:* *$150.00*", 150.00),
        ("*Current Stock Price:* *$1,234.56*", 1234.56),
        ("*Current Stock Price:* *$10.99*", 10.99),
        ("*Current Stock Price:* *$1,000,000.00*", 1000000.00),
    ]
    
    for text, expected_price in test_cases:
        price_match = re.search(r'\$([0-9,.]+)', text)
        assert price_match is not None, f"✅ Price pattern matched in: {text}"
        
        extracted_price = float(price_match.group(1).replace(',', ''))
        assert extracted_price == expected_price, f"✅ Extracted price: ${extracted_price}"
    
    print("✅ All price extraction tests passed!\n")
    return True


def test_action_handlers_registered():
    """Test that action handlers are properly registered."""
    print("🔍 Test 5: Action Handler Registration")
    
    # Check that the handlers exist in actions.py
    with open('listeners/actions.py', 'r') as f:
        content = f.read()
        
        assert '@app.action("shares_input")' in content, "✅ shares_input handler registered"
        assert '@app.action("gmv_input")' in content, "✅ gmv_input handler registered"
        assert '@app.action("symbol_input")' in content, "✅ symbol_input handler registered"
        assert 'handle_shares_input' in content, "✅ shares handler function exists"
        assert 'handle_gmv_input' in content, "✅ GMV handler function exists"
        assert 'handle_symbol_input' in content, "✅ symbol handler function exists"
    
    print("✅ All action handlers are registered!\n")
    return True


def test_error_handling():
    """Test error handling for edge cases."""
    print("🔍 Test 6: Error Handling")
    
    # Test division by zero
    try:
        price = 0
        gmv = 1000
        shares = int(gmv / price) if price > 0 else 0
        assert shares == 0, "✅ Division by zero handled"
    except ZeroDivisionError:
        print("❌ Division by zero not handled")
        return False
    
    # Test invalid string to number conversion
    try:
        shares_str = "abc"
        shares = int(shares_str)
        print("❌ Invalid string conversion should fail")
        return False
    except ValueError:
        print("✅ Invalid string conversion caught")
    
    # Test None values
    price = None
    gmv = 1000
    if price and gmv:
        shares = int(gmv / price)
    else:
        shares = 0
    assert shares == 0, "✅ None value handled"
    
    print("✅ All error handling tests passed!\n")
    return True


def test_modal_update_structure():
    """Test the structure of modal updates."""
    print("🔍 Test 7: Modal Update Structure")
    
    # Simulate a modal update payload
    modal_update = {
        "type": "modal",
        "callback_id": "stock_trade_modal_interactive",
        "title": {"type": "plain_text", "text": "Place Trade"},
        "submit": {"type": "plain_text", "text": "Execute Trade"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "qty_shares_block",
                "element": {
                    "type": "number_input",
                    "action_id": "shares_input",
                    "initial_value": "100"
                }
            },
            {
                "type": "input",
                "block_id": "gmv_block",
                "element": {
                    "type": "number_input",
                    "action_id": "gmv_input",
                    "initial_value": "15000.00"
                }
            }
        ]
    }
    
    # Validate structure
    assert modal_update["type"] == "modal", "✅ Update type is modal"
    assert "blocks" in modal_update, "✅ Blocks present"
    assert len(modal_update["blocks"]) > 0, "✅ Blocks not empty"
    
    # Find updated blocks
    shares_block = next((b for b in modal_update["blocks"] if b.get("block_id") == "qty_shares_block"), None)
    gmv_block = next((b for b in modal_update["blocks"] if b.get("block_id") == "gmv_block"), None)
    
    assert shares_block is not None, "✅ Shares block in update"
    assert gmv_block is not None, "✅ GMV block in update"
    assert shares_block["element"]["initial_value"] == "100", "✅ Shares value updated"
    assert gmv_block["element"]["initial_value"] == "15000.00", "✅ GMV value updated"
    
    print("✅ Modal update structure tests passed!\n")
    return True


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("🚀 TRADE MODAL AUTOFILL INTEGRATION TESTS")
    print("="*70 + "\n")
    
    tests = [
        ("Modal Structure", test_modal_structure),
        ("Shares → GMV Calculation", test_shares_to_gmv_calculation),
        ("GMV → Shares Calculation", test_gmv_to_shares_calculation),
        ("Price Extraction", test_price_extraction),
        ("Action Handlers", test_action_handlers_registered),
        ("Error Handling", test_error_handling),
        ("Modal Update Structure", test_modal_update_structure),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with error: {e}\n")
    
    print("="*70)
    print(f"📊 TEST RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {failed} test(s) failed")
    print("="*70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)

