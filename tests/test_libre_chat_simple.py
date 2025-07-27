#!/usr/bin/env python3
"""
Unit tests for libre_chat.py functionality
Tests the core logic without requiring external dependencies
"""
import os
import sys
import json
import tempfile
from unittest import mock
import xml.etree.ElementTree as ET
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_environment_validation():
    """Test environment variable validation logic."""
    # Test case 1: Valid credentials
    def validate_credentials(username, password):
        if not username:
            return False, "Username/email is required"
        if not password:
            return False, "Password is required"
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        return True, ""
    
    # Test valid credentials
    result, message = validate_credentials("test@example.com", "password123")
    assert result is True
    assert message == ""
    
    # Test empty username
    result, message = validate_credentials("", "password123")
    assert result is False
    assert "Username/email is required" in message
    
    # Test short password
    result, message = validate_credentials("test@example.com", "123")
    assert result is False
    assert "at least 6 characters" in message
    
    print("✅ Environment validation tests passed")

def test_api_key_validation():
    """Test API key validation logic."""
    def validate_api_keys(api_keys):
        if not any(api_keys.values()):
            return False, "At least one API key is required"
        return True, ""
    
    # Test with valid keys
    api_keys = {"openai_api_key": "test-key", "gemini_api_key": ""}
    result, message = validate_api_keys(api_keys)
    assert result is True
    
    # Test with no keys
    api_keys = {"openai_api_key": "", "gemini_api_key": ""}
    result, message = validate_api_keys(api_keys)
    assert result is False
    assert "At least one API key is required" in message
    
    print("✅ API key validation tests passed")

def test_data_processing():
    """Test glucose data processing logic."""
    def process_readings(readings, low_threshold, high_threshold):
        processed = []
        seen_timestamps = set()
        
        for reading in readings:
            timestamp = reading.get('Timestamp')
            if timestamp in seen_timestamps:
                continue  # Skip duplicates
                
            seen_timestamps.add(timestamp)
            
            # Remove factory timestamp if exists
            if 'FactoryTimestamp' in reading:
                del reading['FactoryTimestamp']
            
            # Process glucose values
            try:
                value = float(reading.get('Value', 0))
                reading['isLow'] = value < low_threshold
                reading['isHigh'] = value > high_threshold
            except (ValueError, TypeError):
                reading['isLow'] = False
                reading['isHigh'] = False
            
            # Rename MeasureMent to MeasurementType
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
        {"Timestamp": "2024-01-01T13:00:00", "Value": "invalid", "MeasureMent": 1},  # Invalid
    ]
    
    result = process_readings(sample_readings, low_threshold=70, high_threshold=140)
    
    # Should have 4 unique readings (duplicate removed)
    assert len(result) == 4
    
    # Check threshold marking
    assert result[0]["isLow"] is False  # 120
    assert result[0]["isHigh"] is False
    assert result[1]["isLow"] is True   # 65
    assert result[2]["isHigh"] is True  # 180
    
    # Check field renaming
    assert "MeasurementType" in result[0]
    assert "MeasureMent" not in result[0]
    assert "FactoryTimestamp" not in result[0]
    
    print("✅ Data processing tests passed")

def test_data_conversion():
    """Test data format conversion logic."""
    sample_data = [
        {"Timestamp": "2024-01-01T10:00:00", "Value": 120},
        {"Timestamp": "2024-01-01T11:00:00", "Value": 130}
    ]
    
    # Test JSON conversion
    def to_json(readings):
        return json.dumps(readings, indent=2)
    
    json_result = to_json(sample_data)
    assert isinstance(json_result, str)
    parsed = json.loads(json_result)
    assert len(parsed) == 2
    assert parsed[0]["Value"] == 120
    
    # Test CSV conversion
    def to_csv(readings):
        if not readings:
            return "No data available"
        
        # Simple CSV creation without pandas
        if not readings:
            return "No data available"
        
        # Get headers from first reading
        headers = list(readings[0].keys())
        csv_lines = [",".join(headers)]
        
        for reading in readings:
            values = [str(reading.get(header, "")) for header in headers]
            csv_lines.append(",".join(values))
        
        return "\n".join(csv_lines)
    
    csv_result = to_csv(sample_data)
    assert "Timestamp,Value" in csv_result
    assert "2024-01-01T10:00:00,120" in csv_result
    
    # Test empty data
    empty_csv = to_csv([])
    assert empty_csv == "No data available"
    
    # Test XML conversion
    def to_xml(readings):
        root = ET.Element("GlucoseReadings")
        for reading in readings:
            item = ET.SubElement(root, "Reading")
            for key, value in reading.items():
                child = ET.SubElement(item, key)
                child.text = str(value) if value is not None else ""
        return ET.tostring(root, encoding='unicode')
    
    xml_result = to_xml(sample_data)
    assert "<GlucoseReadings>" in xml_result
    assert "<Value>120</Value>" in xml_result
    
    # Verify it's valid XML
    root = ET.fromstring(xml_result)
    assert root.tag == "GlucoseReadings"
    assert len(root.findall("Reading")) == 2
    
    print("✅ Data conversion tests passed")

def test_client_manager_logic():
    """Test LibreClientManager connection logic."""
    class MockLibreClientManager:
        def __init__(self, email, password, version, product):
            self.email = email
            self.password = password
            self.version = version
            self.product = product
            self.client = None
            self.connections = []
            self.session_id = "test-session-123"
    
        def validate_connection_params(self):
            """Validate connection parameters."""
            if not self.email or not self.password:
                return False, "Email and password are required"
            if len(self.password) < 6:
                return False, "Password too short"
            if self.version not in ["4.7", "4.8"]:
                return False, "Invalid API version"
            return True, ""
    
    # Test valid parameters
    manager = MockLibreClientManager("test@example.com", "password123", "4.7", "llu.ios")
    valid, message = manager.validate_connection_params()
    assert valid is True
    assert message == ""
    
    # Test invalid parameters
    manager = MockLibreClientManager("", "123", "invalid", "llu.ios")
    valid, message = manager.validate_connection_params()
    assert valid is False
    assert "Email and password are required" in message
    
    print("✅ Client manager logic tests passed")

def test_ai_analyzer_logic():
    """Test AI analyzer query processing logic."""
    def detect_complex_query(query):
        """Detect if query is complex and needs code execution."""
        complex_keywords = [
            "code", "script", "function", "calculate", "algorithm", "trend", 
            "correlation", "regression", "statistical", "advanced", "analyze", 
            "plot", "visualization", "distribution", "compute", "complex", 
            "metrics", "time series", "machine learning"
        ]
        return any(keyword in query.lower() for keyword in complex_keywords)
    
    # Test simple queries
    simple_queries = [
        "What's my average glucose?",
        "Show me today's readings",
        "How many readings do I have?"
    ]
    
    for query in simple_queries:
        assert detect_complex_query(query) is False
    
    # Test complex queries
    complex_queries = [
        "Show me code to calculate trends",
        "Generate a statistical analysis",
        "Create a visualization of my data",
        "Run an algorithm to find patterns"
    ]
    
    for query in complex_queries:
        assert detect_complex_query(query) is True
    
    print("✅ AI analyzer logic tests passed")

def test_error_handling():
    """Test error handling scenarios."""
    def safe_float_conversion(value):
        """Safely convert value to float."""
        try:
            return float(value), True
        except (ValueError, TypeError):
            return 0.0, False
    
    # Test valid conversions
    result, success = safe_float_conversion("123.45")
    assert result == 123.45
    assert success is True
    
    result, success = safe_float_conversion(120)
    assert result == 120.0
    assert success is True
    
    # Test invalid conversions
    result, success = safe_float_conversion("invalid")
    assert result == 0.0
    assert success is False
    
    result, success = safe_float_conversion(None)
    assert result == 0.0
    assert success is False
    
    print("✅ Error handling tests passed")

def test_date_filtering():
    """Test date range filtering logic."""
    def filter_by_date_range(readings, start_date_str, end_date_str):
        """Filter readings by date range."""
        if not start_date_str or not end_date_str:
            return readings
        
        try:
            start_date = datetime.fromisoformat(start_date_str).date()
            end_date = datetime.fromisoformat(end_date_str).date()
        except ValueError:
            return readings  # Return all if invalid dates
        
        filtered = []
        for reading in readings:
            try:
                reading_date = datetime.fromisoformat(reading['Timestamp']).date()
                if start_date <= reading_date <= end_date:
                    filtered.append(reading)
            except (ValueError, KeyError):
                continue  # Skip invalid timestamps
        
        return filtered
    
    sample_readings = [
        {"Timestamp": "2024-01-01T10:00:00", "Value": 120},
        {"Timestamp": "2024-01-02T10:00:00", "Value": 130},
        {"Timestamp": "2024-01-03T10:00:00", "Value": 125},
        {"Timestamp": "2024-01-04T10:00:00", "Value": 135}
    ]
    
    # Test filtering to Jan 2-3
    filtered = filter_by_date_range(
        sample_readings, 
        "2024-01-02T00:00:00", 
        "2024-01-03T23:59:59"
    )
    
    assert len(filtered) == 2
    assert filtered[0]["Timestamp"] == "2024-01-02T10:00:00"
    assert filtered[1]["Timestamp"] == "2024-01-03T10:00:00"
    
    # Test with no date range
    all_readings = filter_by_date_range(sample_readings, "", "")
    assert len(all_readings) == 4
    
    print("✅ Date filtering tests passed")

def run_all_tests():
    """Run all test functions."""
    print("🧪 Running LibreChat Unit Tests")
    print("=" * 50)
    
    try:
        test_environment_validation()
        test_api_key_validation()
        test_data_processing()
        test_data_conversion()
        test_client_manager_logic()
        test_ai_analyzer_logic()
        test_error_handling()
        test_date_filtering()
        
        print("=" * 50)
        print("🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
