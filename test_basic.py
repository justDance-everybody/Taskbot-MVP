#!/usr/bin/env python3
"""
Basic test to verify the implementation works
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from app.config import get_settings
        print("✅ Config module imported successfully")
        
        from app.bitable import FieldType, TaskStatus, CIState
        print("✅ Bitable module imported successfully")
        print(f"   TaskStatus.DRAFT = {TaskStatus.DRAFT.value}")
        print(f"   CIState.SUCCESS = {CIState.SUCCESS.value}")
        
        from app.services.feishu import FeishuService, MessageType
        print("✅ Feishu service imported successfully")
        
        from app.services.llm import LLMService
        print("✅ LLM service imported successfully")
        
        from app.services.match import MatchingService
        print("✅ Matching service imported successfully")
        
        from app.services.ci import CIService
        print("✅ CI service imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration loading"""
    try:
        # Set minimal environment variables for testing
        os.environ.update({
            'FEISHU_APP_ID': 'test_app_id',
            'FEISHU_APP_SECRET': 'test_app_secret',
            'FEISHU_VERIFY_TOKEN': 'test_verify_token',
            'FEISHU_BITABLE_APP_TOKEN': 'test_bitable_token',
            'GITHUB_WEBHOOK_SECRET': 'test_github_secret'
        })
        
        from app.config import get_settings
        settings = get_settings()
        
        print("✅ Settings loaded successfully")
        print(f"   App ID: {settings.feishu.app_id}")
        print(f"   Debug mode: {settings.app.debug}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fastapi_app():
    """Test FastAPI app creation"""
    try:
        from app.main import app
        print("✅ FastAPI app created successfully")
        print(f"   App title: {app.title}")
        
        return True
        
    except Exception as e:
        print(f"❌ FastAPI app error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all basic tests"""
    print("🚀 Running basic functionality tests...\n")
    
    tests = [
        ("Import Tests", test_imports),
        ("Configuration Tests", test_config),
        ("FastAPI App Tests", test_fastapi_app),
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
        print("🎉 All basic tests passed! The implementation is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
