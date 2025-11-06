#!/usr/bin/env python3
"""
Test script for extract_json_from_response function to verify it handles empty arrays.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from utils import extract_json_from_response

def test_json_extraction():
    """Test various JSON extraction scenarios."""
    
    test_cases = [
        # Empty array cases
        ("[]", []),
        ("[ ]", []),
        (" [] ", []),
        ("No security issues found: []", []),
        ("The result is: [ ]", []),
        
        # Object cases
        ('{"category": "test"}', {"category": "test"}),
        ('Result: {"finding": "issue"}', {"finding": "issue"}),
        
        # Array with objects
        ('[{"category": "A01", "finding": "test"}]', [{"category": "A01", "finding": "test"}]),
        
        # Multiple objects in array
        ('[{"category": "A01"}, {"category": "A02"}]', [{"category": "A01"}, {"category": "A02"}]),
        
        # No JSON
        ("No JSON here", None),
        ("", None),
        
        # Invalid JSON
        ("{invalid}", None),
        ("[invalid]", None),
    ]
    
    print("🧪 Testing extract_json_from_response function...")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = extract_json_from_response(input_text)
        
        if result == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        print(f"Test {i:2d}: {status}")
        print(f"  Input:    {repr(input_text[:50])}{'...' if len(input_text) > 50 else ''}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()
    
    print("=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("💥 Some tests failed!")
        return False

if __name__ == "__main__":
    success = test_json_extraction()
    sys.exit(0 if success else 1)
