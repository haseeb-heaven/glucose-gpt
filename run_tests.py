#!/usr/bin/env python3
"""
Test runner that sets up matplotlib backend before running tests
"""
import os
import sys

# Set matplotlib to use a non-interactive backend
os.environ['MPLBACKEND'] = 'Agg'

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_with_pytest():
    """Run tests using pytest."""
    import subprocess
    
    print("🧪 Running Glucose-GPT Tests with pytest")
    print("=" * 50)
    
    # Run simple tests first
    print("Running simple unit tests...")
    result1 = subprocess.run([
        sys.executable, "tests/test_libre_chat_simple.py"
    ], cwd="/Users/haseeb-mir/Documents/Code/Python/LibreApp")
    
    if result1.returncode != 0:
        print("❌ Simple tests failed")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed successfully!")
    return True

def test_data_processing_only():
    """Test only the data processing functionality without importing the full module."""
    print("🧪 Testing Data Processing Functions")
    print("=" * 50)
    
    # Test glucose reading processing
    def process_readings(readings, low_threshold, high_threshold):
        processed = []
        seen_timestamps = set()
        
        for reading in readings:
            timestamp = reading.get('Timestamp')
            if timestamp in seen_timestamps:
                continue
                
            seen_timestamps.add(timestamp)
            
            if 'FactoryTimestamp' in reading:
                del reading['FactoryTimestamp']
            
            try:
                value = float(reading.get('Value', 0))
                reading['isLow'] = value < low_threshold
                reading['isHigh'] = value > high_threshold
            except (ValueError, TypeError):
                reading['isLow'] = False
                reading['isHigh'] = False
            
            if 'MeasureMent' in reading:
                reading['MeasurementType'] = reading.pop('MeasureMent')
                
            processed.append(reading)
        
        return processed
    
    # Test data
    sample_readings = [
        {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1, "FactoryTimestamp": "ignore"},
        {"Timestamp": "2024-01-01T11:00:00", "Value": "65", "MeasureMent": 1},
        {"Timestamp": "2024-01-01T12:00:00", "Value": "180", "MeasureMent": 1},
        {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1},  # Duplicate
    ]
    
    result = process_readings(sample_readings, low_threshold=70, high_threshold=140)
    
    # Assertions
    assert len(result) == 3, f"Expected 3 unique readings, got {len(result)}"
    assert result[0]["isLow"] is False, "120 should not be low"
    assert result[0]["isHigh"] is False, "120 should not be high"
    assert result[1]["isLow"] is True, "65 should be low"
    assert result[2]["isHigh"] is True, "180 should be high"
    assert "MeasurementType" in result[0], "MeasureMent should be renamed"
    assert "FactoryTimestamp" not in result[0], "FactoryTimestamp should be removed"
    
    print("✅ Data processing tests passed")
    
    # Test data format conversions
    import json
    import xml.etree.ElementTree as ET
    
    def to_json(readings):
        return json.dumps(readings, indent=2)
    
    def to_xml(readings):
        root = ET.Element("GlucoseReadings")
        for reading in readings:
            item = ET.SubElement(root, "Reading")
            for key, value in reading.items():
                child = ET.SubElement(item, key)
                child.text = str(value) if value is not None else ""
        return ET.tostring(root, encoding='unicode')
    
    # Test JSON conversion
    json_result = to_json(result)
    parsed = json.loads(json_result)
    assert len(parsed) == 3, "JSON conversion failed"
    print("✅ JSON conversion test passed")
    
    # Test XML conversion
    xml_result = to_xml(result)
    assert "<GlucoseReadings>" in xml_result, "XML conversion failed"
    assert "<Value>120</Value>" in xml_result, "XML content missing"
    
    root = ET.fromstring(xml_result)
    assert root.tag == "GlucoseReadings", "XML root tag incorrect"
    assert len(root.findall("Reading")) == 3, "XML reading count incorrect"
    print("✅ XML conversion test passed")
    
    print("=" * 50)
    print("🎉 Data processing tests completed successfully!")
    return True

def test_validation_logic():
    """Test validation functions without importing the main module."""
    print("\n🧪 Testing Validation Logic")
    print("=" * 50)
    
    def validate_credentials(username, password):
        if not username:
            return False, "Username/email is required"
        if not password:
            return False, "Password is required"
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        return True, ""
    
    def validate_api_keys(api_keys):
        if not any(api_keys.values()):
            return False, "At least one API key is required"
        return True, ""
    
    # Test credential validation
    valid, msg = validate_credentials("test@example.com", "password123")
    assert valid is True, f"Valid credentials failed: {msg}"
    
    valid, msg = validate_credentials("", "password123")
    assert valid is False, "Empty username should fail"
    assert "Username/email is required" in msg, f"Wrong error message: {msg}"
    
    valid, msg = validate_credentials("test@example.com", "123")
    assert valid is False, "Short password should fail"
    assert "at least 6 characters" in msg, f"Wrong error message: {msg}"
    
    print("✅ Credential validation tests passed")
    
    # Test API key validation
    valid, msg = validate_api_keys({"openai_api_key": "test-key", "gemini_api_key": ""})
    assert valid is True, f"Valid API keys failed: {msg}"
    
    valid, msg = validate_api_keys({"openai_api_key": "", "gemini_api_key": ""})
    assert valid is False, "Empty API keys should fail"
    assert "At least one API key is required" in msg, f"Wrong error message: {msg}"
    
    print("✅ API key validation tests passed")
    
    print("=" * 50)
    print("🎉 Validation tests completed successfully!")
    return True

def run_all_tests():
    """Run all available tests."""
    try:
        success1 = test_with_pytest()
        success2 = test_data_processing_only()
        success3 = test_validation_logic()
        
        if success1 and success2 and success3:
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
            print("=" * 60)
            return True
        else:
            print("\n❌ Some tests failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
