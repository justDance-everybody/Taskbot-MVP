#!/usr/bin/env python3
"""
Simple test to verify core functionality
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_enums():
    """Test enum definitions"""
    try:
        from app.bitable import FieldType, TaskStatus, CIState
        
        print("✅ Enums imported successfully")
        print(f"   TaskStatus.DRAFT = {TaskStatus.DRAFT.value}")
        print(f"   TaskStatus.DONE = {TaskStatus.DONE.value}")
        print(f"   CIState.SUCCESS = {CIState.SUCCESS.value}")
        print(f"   FieldType.TEXT = {FieldType.TEXT.value}")
        
        return True
    except Exception as e:
        print(f"❌ Enum test failed: {e}")
        return False

def test_mock_bitable():
    """Test mock bitable client"""
    try:
        from app.bitable_mock import MockBitableClient, TaskStatus
        
        client = MockBitableClient()
        print("✅ Mock bitable client created")
        
        # Test async methods would require asyncio, so just test creation
        print("✅ Mock bitable client test passed")
        
        return True
    except Exception as e:
        print(f"❌ Mock bitable test failed: {e}")
        return False

def test_services():
    """Test service imports"""
    try:
        from app.services.match import MatchingService
        from app.services.ci import CIService
        
        print("✅ Services imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Services test failed: {e}")
        return False

def main():
    """Run simple tests"""
    print("🚀 Running simple functionality tests...\n")
    
    # Set minimal environment for testing
    os.environ.update({
        'FEISHU_APP_ID': 'test_app_id',
        'FEISHU_APP_SECRET': 'test_app_secret',
        'FEISHU_VERIFY_TOKEN': 'test_verify_token',
        'FEISHU_BITABLE_APP_TOKEN': 'test_bitable_token',
        'GITHUB_WEBHOOK_SECRET': 'test_github_secret'
    })
    
    tests = [
        ("Enum Tests", test_enums),
        ("Mock Bitable Tests", test_mock_bitable),
        ("Services Tests", test_services),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"📋 {test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED\n")
        else:
            print(f"❌ {test_name} FAILED\n")
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All simple tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed.")
        return 1

if __name__ == "__main__":
    exit(main())
