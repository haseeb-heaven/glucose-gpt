#!/usr/bin/env python3
"""
Integration tests for libre_chat.py using mocks for external dependencies
"""
import os
import sys
import tempfile
from unittest import mock
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_environment_loader_integration():
    """Test EnvironmentLoader with mocked dependencies."""
    print("Testing EnvironmentLoader integration...")
    
    # Create a temporary .env file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
LIBRE_USERNAME=test@example.com
LIBRE_PASSWORD=testpassword123
OPENAI_API_KEY=test-openai-key
GEMINI_API_KEY=test-gemini-key
LIBRE_VERSION=4.7
LIBRE_PRODUCT=llu.ios
""")
        f.flush()
        temp_env_path = f.name
    
    try:
        # Mock streamlit and load_dotenv
        with mock.patch('streamlit.error') as mock_st_error, \
             mock.patch('streamlit.info') as mock_st_info, \
             mock.patch('os.path.exists', return_value=True), \
             mock.patch('glucosegpt.examples.glucose_chat.load_dotenv') as mock_load_dotenv:
            
            # Mock environment variables
            env_vars = {
                "LIBRE_USERNAME": "test@example.com",
                "LIBRE_PASSWORD": "testpassword123",
                "OPENAI_API_KEY": "test-openai-key",
                "GEMINI_API_KEY": "test-gemini-key",
                "LIBRE_VERSION": "4.7",
                "LIBRE_PRODUCT": "llu.ios",
                "DEFAULT_MODEL": "gemini/gemini-1.5-flash"
            }
            
            with mock.patch('os.getenv', side_effect=lambda key, default="": env_vars.get(key, default)):
                # Import and test
                from glucosegpt.examples.glucose_chat import EnvironmentLoader
                
                env_loader = EnvironmentLoader()
                result = env_loader.load_defaults()
                
                assert result["libre_username"] == "test@example.com"
                assert result["libre_password"] == "testpassword123"
                assert result["openai_api_key"] == "test-openai-key"
                assert result["libre_version"] == "4.7"
                
                print("✅ EnvironmentLoader integration test passed")
    
    finally:
        # Cleanup
        os.unlink(temp_env_path)

def test_data_formatter_integration():
    """Test DataFormatter with real pandas operations."""
    print("Testing DataFormatter integration...")
    
    with mock.patch('glucosegpt.examples.glucose_chat.file_log') as mock_logger:
        from glucosegpt.examples.glucose_chat import DataFormatter
        
        # Test data
        sample_readings = [
            {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1, "FactoryTimestamp": "ignore"},
            {"Timestamp": "2024-01-01T11:00:00", "Value": "65", "MeasureMent": 1},
            {"Timestamp": "2024-01-01T12:00:00", "Value": "180", "MeasureMent": 1},
            {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1},  # Duplicate
        ]
        
        # Test processing
        processed = DataFormatter.process_readings(
            sample_readings,
            low_threshold=70,
            high_threshold=140
        )
        
        assert len(processed) == 3  # Duplicate removed
        assert "MeasurementType" in processed[0]
        assert "FactoryTimestamp" not in processed[0]
        
        # Test DataFrame conversion
        df = DataFormatter.to_dataframe(processed)
        assert len(df) == 3
        assert "Timestamp" in df.columns
        
        # Test CSV conversion
        csv_data = DataFormatter.to_csv(processed)
        assert "Timestamp" in csv_data
        assert "Value" in csv_data
        
        # Test JSON conversion
        json_data = DataFormatter.to_json(processed)
        parsed = json.loads(json_data)
        assert len(parsed) == 3
        
        # Test XML conversion
        xml_data = DataFormatter.to_xml(processed)
        assert "<GlucoseReadings>" in xml_data
        assert "<Value>120</Value>" in xml_data
        
        print("✅ DataFormatter integration test passed")

def test_libre_client_manager_integration():
    """Test LibreClientManager with mocked dependencies."""
    print("Testing LibreClientManager integration...")
    
    with mock.patch('glucosegpt.examples.glucose_chat.file_log') as mock_logger, \
         mock.patch('streamlit.toast') as mock_toast, \
         mock.patch('glucosegpt.examples.glucose_chat.LibreCGMClient') as mock_client_class, \
         mock.patch('glucosegpt.examples.glucose_chat.ApiConfig') as mock_config, \
         mock.patch('glucosegpt.examples.glucose_chat.DefaultDataMasker'):
        
        from glucosegpt.examples.glucose_chat import LibreClientManager
        
        # Setup mock client
        mock_client = mock.Mock()
        mock_client.authenticate.return_value = {"status": 0}
        mock_client.list_connections.return_value = {
            "data": [
                {"patientId": "123", "firstName": "John", "lastName": "Doe"}
            ]
        }
        mock_client.get_patient_graph.return_value = {
            "data": {
                "graphData": [
                    {"Timestamp": "2024-01-01T10:00:00", "Value": 120},
                    {"Timestamp": "2024-01-01T11:00:00", "Value": 130}
                ]
            }
        }
        mock_client_class.return_value = mock_client
        
        # Test client manager
        manager = LibreClientManager(
            email="test@example.com",
            password="testpass123",
            version="4.7",
            product="llu.ios"
        )
        
        # Test connection
        result = manager.connect()
        assert result is True
        assert len(manager.connections) == 1
        
        # Test getting patient data
        patient_data = manager.get_patient_data("123")
        assert len(patient_data) == 2
        assert patient_data[0]["Value"] == 120
        
        print("✅ LibreClientManager integration test passed")

def test_ai_analyzer_integration():
    """Test AIAnalyzer with mocked LiteLLM."""
    print("Testing AIAnalyzer integration...")
    
    with mock.patch('glucosegpt.examples.glucose_chat.file_log') as mock_logger, \
         mock.patch('glucosegpt.examples.glucose_chat.litellm.completion') as mock_completion, \
         mock.patch('glucosegpt.examples.glucose_chat.CodeRunner') as mock_code_runner:
        
        from glucosegpt.examples.glucose_chat import AIAnalyzer
        
        # Setup mocks
        mock_response = mock.Mock()
        mock_response.choices = [mock.Mock()]
        mock_response.choices[0].message.content = "The average glucose is 125 mg/dL"
        mock_completion.return_value = mock_response
        
        mock_code_runner.run_llm_code_blocks.return_value = {"has_code": False}
        
        # Test analyzer
        api_keys = {"openai_api_key": "test-key"}
        analyzer = AIAnalyzer(api_keys)
        
        sample_readings = [
            {"Value": 120, "Timestamp": "2024-01-01T10:00:00"},
            {"Value": 130, "Timestamp": "2024-01-01T11:00:00"}
        ]
        
        # Test simple query
        result = analyzer.analyze(sample_readings, "What's the average?", "gpt-4")
        assert result["has_code"] is False
        assert "125 mg/dL" in result["result"]
        
        # Test with no valid readings
        invalid_readings = [{"Value": None}, {"Value": ""}]
        result = analyzer.analyze(invalid_readings, "Test", "gpt-4")
        assert "No valid glucose readings" in result["result"]
        
        print("✅ AIAnalyzer integration test passed")

def test_validation_functions_integration():
    """Test validation functions."""
    print("Testing validation functions...")
    
    with mock.patch('glucosegpt.examples.glucose_chat.file_log'):
        from glucosegpt.examples.glucose_chat import validate_credentials, validate_api_keys
        
        # Test credential validation
        result, message = validate_credentials("test@example.com", "password123")
        assert result is True
        assert message == ""
        
        result, message = validate_credentials("", "")
        assert result is False
        assert "Username/email is required" in message
        
        # Test API key validation
        api_keys = {"openai_api_key": "test-key", "gemini_api_key": ""}
        result, message = validate_api_keys(api_keys)
        assert result is True
        
        api_keys = {"openai_api_key": "", "gemini_api_key": ""}
        result, message = validate_api_keys(api_keys)
        assert result is False
        assert "At least one API key is required" in message
        
        print("✅ Validation functions integration test passed")

def test_complete_workflow_integration():
    """Test a complete workflow from environment loading to data analysis."""
    print("Testing complete workflow integration...")
    
    with mock.patch('glucosegpt.examples.glucose_chat.file_log') as mock_logger, \
         mock.patch('streamlit.error') as mock_st_error, \
         mock.patch('os.path.exists', return_value=True), \
         mock.patch('glucosegpt.examples.glucose_chat.load_dotenv'), \
         mock.patch('streamlit.toast'), \
         mock.patch('glucosegpt.examples.glucose_chat.LibreCGMClient') as mock_client_class, \
         mock.patch('glucosegpt.examples.glucose_chat.ApiConfig'), \
         mock.patch('glucosegpt.examples.glucose_chat.DefaultDataMasker'), \
         mock.patch('glucosegpt.examples.glucose_chat.litellm.completion') as mock_completion:
        
        from glucosegpt.examples.glucose_chat import (
            EnvironmentLoader, LibreClientManager, DataFormatter, AIAnalyzer
        )
        
        # Mock environment variables
        env_vars = {
            "LIBRE_USERNAME": "test@example.com",
            "LIBRE_PASSWORD": "testpassword123",
            "OPENAI_API_KEY": "test-openai-key",
            "LIBRE_VERSION": "4.7",
            "LIBRE_PRODUCT": "llu.ios"
        }
        
        with mock.patch('os.getenv', side_effect=lambda key, default="": env_vars.get(key, default)):
            # Step 1: Load environment
            env_loader = EnvironmentLoader()
            defaults = env_loader.load_defaults()
            assert defaults["libre_username"] == "test@example.com"
            
            # Step 2: Setup client manager
            manager = LibreClientManager(
                email=defaults["libre_username"],
                password=defaults["libre_password"],
                version=defaults["libre_version"],
                product=defaults["libre_product"]
            )
            
            # Mock client behavior
            mock_client = mock.Mock()
            mock_client.authenticate.return_value = {"status": 0}
            mock_client.list_connections.return_value = {
                "data": [{"patientId": "123", "firstName": "John", "lastName": "Doe"}]
            }
            mock_client.get_patient_graph.return_value = {
                "data": {
                    "graphData": [
                        {"Timestamp": "2024-01-01T10:00:00", "Value": 120, "MeasureMent": 1},
                        {"Timestamp": "2024-01-01T11:00:00", "Value": 65, "MeasureMent": 1},
                        {"Timestamp": "2024-01-01T12:00:00", "Value": 180, "MeasureMent": 1}
                    ]
                }
            }
            mock_client_class.return_value = mock_client
            
            # Step 3: Connect and get data
            assert manager.connect() is True
            patient_data = manager.get_patient_data("123")
            assert len(patient_data) == 3
            
            # Step 4: Process data
            processed_data = DataFormatter.process_readings(
                patient_data,
                low_threshold=70,
                high_threshold=140
            )
            assert len(processed_data) == 3
            assert processed_data[1]["isLow"] is True  # 65 < 70
            assert processed_data[2]["isHigh"] is True  # 180 > 140
            
            # Step 5: Convert to different formats
            df = DataFormatter.to_dataframe(processed_data)
            csv_data = DataFormatter.to_csv(processed_data)
            json_data = DataFormatter.to_json(processed_data)
            
            assert len(df) == 3
            assert "Timestamp" in csv_data
            assert json.loads(json_data)  # Valid JSON
            
            # Step 6: AI Analysis
            mock_response = mock.Mock()
            mock_response.choices = [mock.Mock()]
            mock_response.choices[0].message.content = "Analysis complete. Average glucose: 121.7 mg/dL"
            mock_completion.return_value = mock_response
            
            analyzer = AIAnalyzer({"openai_api_key": "test-key"})
            analysis_result = analyzer.analyze(processed_data, "Analyze my glucose data", "gpt-4")
            
            assert "Analysis complete" in analysis_result["result"]
            assert analysis_result["has_code"] is False
            
            print("✅ Complete workflow integration test passed")

def run_integration_tests():
    """Run all integration tests."""
    print("🧪 Running Glucose-GPT Integration Tests")
    print("=" * 60)
    
    try:
        test_environment_loader_integration()
        test_data_formatter_integration()
        test_libre_client_manager_integration()
        test_ai_analyzer_integration()
        test_validation_functions_integration()
        test_complete_workflow_integration()
        
        print("=" * 60)
        print("🎉 All integration tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
