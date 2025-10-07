#!/usr/bin/env python3
"""
Test to verify there are no duplicate /trade command registrations.
"""

import re

def test_no_duplicate_registrations():
    """Test that there's only one /trade command registration."""
    print("🧪 Testing for duplicate /trade command registrations...")
    
    # Read the commands.py file
    with open('listeners/commands.py', 'r') as f:
        content = f.read()
    
    # Find all /trade command registrations
    pattern = r'@app\.command\("/trade"\)'
    matches = re.findall(pattern, content)
    
    print(f"Found {len(matches)} /trade command registrations")
    
    if len(matches) == 1:
        print("✅ PASS: Only one /trade command registration found")
        return True
    elif len(matches) == 0:
        print("❌ FAIL: No /trade command registrations found")
        return False
    else:
        print(f"❌ FAIL: Multiple /trade command registrations found ({len(matches)})")
        print("This causes conflicts and unpredictable behavior")
        return False

def test_command_handler_structure():
    """Test that the command handler has the correct structure."""
    print("\n🧪 Testing command handler structure...")
    
    with open('listeners/commands.py', 'r') as f:
        content = f.read()
    
    # Check for ultra-fast acknowledgment
    if 'ack()' in content and 'ULTRA-FAST' in content:
        print("✅ PASS: Ultra-fast acknowledgment pattern found")
    else:
        print("❌ FAIL: Ultra-fast acknowledgment pattern missing")
        return False
    
    # Check for proper error handling
    if 'try:' in content and 'client.views_open' in content:
        print("✅ PASS: Error handling for modal opening found")
    else:
        print("❌ FAIL: Error handling for modal opening missing")
        return False
    
    # Check for debug logging
    if 'logger.info' in content and 'Command acknowledged' in content:
        print("✅ PASS: Debug logging found")
    else:
        print("❌ FAIL: Debug logging missing")
        return False
    
    return True

def test_no_fallback_conflicts():
    """Test that there are no conflicting fallback registrations."""
    print("\n🧪 Testing for fallback registration conflicts...")
    
    with open('listeners/commands.py', 'r') as f:
        content = f.read()
    
    # Check that fallback doesn't register another command
    if 'handle_fallback_trade_command' in content:
        if '@app.command("/trade")' in content.split('handle_fallback_trade_command')[0]:
            print("❌ FAIL: Fallback command registration still present")
            return False
    
    print("✅ PASS: No conflicting fallback registrations")
    return True

if __name__ == "__main__":
    print("🚀 Testing Command Registration Fix")
    print("=" * 50)
    
    success = True
    
    # Test for duplicate registrations
    success &= test_no_duplicate_registrations()
    
    # Test command handler structure
    success &= test_command_handler_structure()
    
    # Test for fallback conflicts
    success &= test_no_fallback_conflicts()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ No duplicate command registrations")
        print("✅ Proper command handler structure")
        print("✅ No conflicting fallback registrations")
        print("✅ Command registration conflicts resolved")
    else:
        print("❌ SOME TESTS FAILED!")
        exit(1)