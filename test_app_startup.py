#!/usr/bin/env python3
"""
Quick test to verify the Streamlit app can be imported without errors
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing Streamlit app import...")
    
    # Mock streamlit to avoid UI initialization
    import unittest.mock as mock
    
    # Test basic imports
    from glucosegpt.examples.glucose_chat import (
        ConfigurationLoader,
        LibreClientManager, 
        DataFormatter,
        ChartGenerator,
        AIAnalyzer,
        validate_credentials,
        validate_api_keys
    )
    
    print("✅ All imports successful")
    
    # Test basic class instantiation with mocked config
    with mock.patch('glucosegpt.examples.glucose_chat.config_manager'):
        config_loader = ConfigurationLoader()
        print("✅ ConfigurationLoader instantiated")
    
    # Test static methods
    assert DataFormatter.to_csv([]) == "No data available"
    print("✅ DataFormatter static methods work")
    
    result, msg = validate_credentials("test@example.com", "password123")
    assert result is True
    print("✅ Validation functions work")
    
    print("🎉 Streamlit app startup test passed!")
        
except Exception as e:
    print(f"❌ Error during app startup test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
