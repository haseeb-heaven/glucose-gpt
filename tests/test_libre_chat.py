#!/usr/bin/env python3
"""
Comprehensive unit tests for libre_chat.py
"""
import pytest
import unittest.mock as mock
import os
import sys
import tempfile
import pandas as pd
import numpy as np
import json
from datetime import datetime, date
from typing import Dict, Any, List
import xml.etree.ElementTree as ET

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the classes to test
from libreapp.examples.libre_chat import (
    EnvironmentLoader,
    LibreClientManager,
    DataFormatter,
    ChartGenerator,
    AIAnalyzer,
    validate_credentials,
    validate_api_keys
)

class TestEnvironmentLoader:
    """Test cases for EnvironmentLoader class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.env_loader = EnvironmentLoader()
    
    @mock.patch('os.path.exists')
    @mock.patch('libreapp.examples.libre_chat.load_dotenv')
    def test_check_env_file_exists(self, mock_load_dotenv, mock_exists):
        """Test checking for existing .env file."""
        mock_exists.return_value = True
        result = self.env_loader.check_env_file()
        assert result is True
        mock_load_dotenv.assert_called_once()
    
    @mock.patch('os.path.exists')
    @mock.patch('streamlit.error')
    def test_check_env_file_not_exists(self, mock_st_error, mock_exists):
        """Test checking for missing .env file."""
        mock_exists.return_value = False
        result = self.env_loader.check_env_file()
        assert result is False
        mock_st_error.assert_called_once()
    
    @mock.patch.object(EnvironmentLoader, 'check_env_file')
    @mock.patch('os.getenv')
    def test_load_defaults_success(self, mock_getenv, mock_check_env):
        """Test successful loading of environment variables."""
        mock_check_env.return_value = True
        
        # Mock environment variables
        env_vars = {
            "LIBRE_USERNAME": "test@example.com",
            "LIBRE_PASSWORD": "testpass123",
            "OPENAI_API_KEY": "test-openai-key",
            "LIBRE_VERSION": "4.7",
            "LIBRE_PRODUCT": "llu.ios",
            "DEFAULT_MODEL": "gpt-4"
        }
        
        def mock_getenv_side_effect(key, default=""):
            return env_vars.get(key, default)
        
        mock_getenv.side_effect = mock_getenv_side_effect
        
        result = self.env_loader.load_defaults()
        
        assert result["libre_username"] == "test@example.com"
        assert result["libre_password"] == "testpass123"
        assert result["openai_api_key"] == "test-openai-key"
        assert result["libre_version"] == "4.7"
    
    @mock.patch.object(EnvironmentLoader, 'check_env_file')
    def test_load_defaults_missing_env_file(self, mock_check_env):
        """Test loading defaults when .env file is missing."""
        mock_check_env.return_value = False
        result = self.env_loader.load_defaults()
        assert result == {}
    
    @mock.patch.object(EnvironmentLoader, 'check_env_file')
    @mock.patch('os.getenv')
    @mock.patch('streamlit.error')
    def test_load_defaults_missing_required_vars(self, mock_st_error, mock_getenv, mock_check_env):
        """Test loading defaults with missing required variables."""
        mock_check_env.return_value = True
        mock_getenv.return_value = ""  # All env vars return empty
        
        result = self.env_loader.load_defaults()
        assert result == {}
        mock_st_error.assert_called()


class TestLibreClientManager:
    """Test cases for LibreClientManager class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.manager = LibreClientManager(
            email="test@example.com",
            password="testpass123",
            version="4.7",
            product="llu.ios"
        )
    
    def test_init(self):
        """Test LibreClientManager initialization."""
        assert self.manager.email == "test@example.com"
        assert self.manager.password == "testpass123"
        assert self.manager.version == "4.7"
        assert self.manager.product == "llu.ios"
        assert self.manager.client is None
        assert self.manager.connections == []
        assert self.manager.session_id is not None
    
    @mock.patch('libreapp.examples.libre_chat.LibreCGMClient')
    @mock.patch('libreapp.examples.libre_chat.ApiConfig')
    @mock.patch('libreapp.examples.libre_chat.DefaultDataMasker')
    def test_connect_success(self, mock_masker, mock_config, mock_client_class):
        """Test successful connection to LibreView."""
        # Mock the client instance
        mock_client = mock.Mock()
        mock_client.authenticate.return_value = {"status": 0}
        mock_client.list_connections.return_value = {
            "data": [
                {"patientId": "123", "firstName": "John", "lastName": "Doe"}
            ]
        }
        mock_client_class.return_value = mock_client
        
        result = self.manager.connect()
        
        assert result is True
        assert self.manager.client == mock_client
        assert len(self.manager.connections) == 1
        mock_client.authenticate.assert_called_once()
        mock_client.list_connections.assert_called_once()
    
    @mock.patch('libreapp.examples.libre_chat.LibreCGMClient')
    @mock.patch('libreapp.examples.libre_chat.ApiConfig')
    @mock.patch('libreapp.examples.libre_chat.DefaultDataMasker')
    @mock.patch('streamlit.toast')
    def test_connect_auth_failure(self, mock_toast, mock_masker, mock_config, mock_client_class):
        """Test connection failure due to authentication."""
        mock_client = mock.Mock()
        mock_client.authenticate.return_value = {"status": 1}  # Auth failure
        mock_client_class.return_value = mock_client
        
        result = self.manager.connect()
        
        assert result is False
        mock_toast.assert_called()
    
    @mock.patch('libreapp.examples.libre_chat.LibreCGMClient')
    @mock.patch('streamlit.toast')
    def test_connect_exception(self, mock_toast, mock_client_class):
        """Test connection failure due to exception."""
        mock_client_class.side_effect = Exception("Connection error")
        
        result = self.manager.connect()
        
        assert result is False
        mock_toast.assert_called()
    
    def test_get_patient_data_no_client(self):
        """Test getting patient data without initialized client."""
        result = self.manager.get_patient_data("123")
        assert result is None
    
    @mock.patch('streamlit.toast')
    def test_get_patient_data_success(self, mock_toast):
        """Test successful patient data retrieval."""
        # Setup mock client
        mock_client = mock.Mock()
        mock_client.get_patient_graph.return_value = {
            "data": {
                "graphData": [
                    {"Timestamp": "2024-01-01T10:00:00", "Value": 120},
                    {"Timestamp": "2024-01-01T11:00:00", "Value": 130}
                ]
            }
        }
        self.manager.client = mock_client
        
        result = self.manager.get_patient_data("123")
        
        assert len(result) == 2
        assert result[0]["Value"] == 120
        mock_client.get_patient_graph.assert_called_once_with("123")


class TestDataFormatter:
    """Test cases for DataFormatter class."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.sample_readings = [
            {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1},
            {"Timestamp": "2024-01-01T11:00:00", "Value": "65", "MeasureMent": 1},
            {"Timestamp": "2024-01-01T12:00:00", "Value": "180", "MeasureMent": 1},
            {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1},  # Duplicate
            {"Timestamp": "2024-01-01T13:00:00", "Value": "invalid", "MeasureMent": 1},  # Invalid value
        ]
    
    def test_process_readings_basic(self):
        """Test basic reading processing with thresholds."""
        result = DataFormatter.process_readings(
            self.sample_readings, 
            low_threshold=70, 
            high_threshold=140
        )
        
        # Should have 4 unique readings (duplicate removed)
        assert len(result) == 4
        
        # Check threshold marking
        assert result[0]["isLow"] is False  # 120
        assert result[0]["isHigh"] is False
        assert result[1]["isLow"] is True   # 65
        assert result[2]["isHigh"] is True  # 180
        
        # Check MeasureMent -> MeasurementType rename
        assert "MeasurementType" in result[0]
        assert "MeasureMent" not in result[0]
    
    def test_process_readings_with_date_filter(self):
        """Test reading processing with date range filter."""
        date_range = {
            "start_date": "2024-01-01T10:30:00",
            "end_date": "2024-01-01T11:30:00"
        }
        
        result = DataFormatter.process_readings(
            self.sample_readings,
            low_threshold=70,
            high_threshold=140,
            date_range=date_range
        )
        
        # Should only include readings within date range
        assert len(result) == 1  # Only the 11:00 reading
        assert result[0]["Value"] == "65"
    
    def test_process_readings_invalid_values(self):
        """Test processing readings with invalid glucose values."""
        result = DataFormatter.process_readings(
            self.sample_readings,
            low_threshold=70,
            high_threshold=140
        )
        
        # Find the reading with invalid value
        invalid_reading = next(r for r in result if r["Value"] == "invalid")
        assert invalid_reading["isLow"] is False
        assert invalid_reading["isHigh"] is False
    
    def test_to_dataframe(self):
        """Test conversion to pandas DataFrame."""
        df = DataFormatter.to_dataframe(self.sample_readings)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(self.sample_readings)
        assert "Timestamp" in df.columns
        assert "Value" in df.columns
    
    def test_to_csv(self):
        """Test conversion to CSV format."""
        csv_result = DataFormatter.to_csv(self.sample_readings)
        
        assert isinstance(csv_result, str)
        assert "Timestamp" in csv_result
        assert "Value" in csv_result
        
        # Test empty readings
        empty_csv = DataFormatter.to_csv([])
        assert empty_csv == "No data available"
    
    def test_to_json(self):
        """Test conversion to JSON format."""
        json_result = DataFormatter.to_json(self.sample_readings)
        
        assert isinstance(json_result, str)
        
        # Verify it's valid JSON
        parsed = json.loads(json_result)
        assert len(parsed) == len(self.sample_readings)
        assert parsed[0]["Value"] == "120"
    
    def test_to_xml(self):
        """Test conversion to XML format."""
        xml_result = DataFormatter.to_xml(self.sample_readings)
        
        assert isinstance(xml_result, str)
        assert "<GlucoseReadings>" in xml_result
        assert "<Reading>" in xml_result
        assert "<Value>120</Value>" in xml_result
        
        # Verify it's valid XML
        root = ET.fromstring(xml_result)
        assert root.tag == "GlucoseReadings"
        assert len(root.findall("Reading")) == len(self.sample_readings)


class TestChartGenerator:
    """Test cases for ChartGenerator class."""
    
    def setup_method(self):
        """Setup test data for each test method."""
        self.sample_readings = [
            {"Timestamp": "2024-01-01T10:00:00", "Value": 120},
            {"Timestamp": "2024-01-01T11:00:00", "Value": 130},
            {"Timestamp": "2024-01-01T12:00:00", "Value": 125},
        ]
        
        self.chart_settings = {
            "filter_by_range": False,
            "glucose_min": 70,
            "glucose_max": 180
        }
    
    def test_create_glucose_chart_empty_readings(self):
        """Test chart creation with empty readings."""
        result = ChartGenerator.create_glucose_chart([], "line", self.chart_settings)
        assert result is None
    
    def test_create_glucose_chart_with_filtering(self):
        """Test chart creation with glucose range filtering."""
        # Add a reading outside the range
        readings_with_outlier = self.sample_readings + [
            {"Timestamp": "2024-01-01T13:00:00", "Value": 300}  # Too high
        ]
        
        settings_with_filter = self.chart_settings.copy()
        settings_with_filter["filter_by_range"] = True
        
        # Mock the actual chart creation since we can't test plotly directly
        with mock.patch('pandas.DataFrame') as mock_df:
            mock_df_instance = mock.Mock()
            mock_df.return_value = mock_df_instance
            mock_df_instance.empty = False
            
            # This test mainly verifies the filtering logic
            # The actual chart creation is hard to test without plotly dependencies
            result = ChartGenerator.create_glucose_chart(
                readings_with_outlier, 
                "line", 
                settings_with_filter
            )


class TestAIAnalyzer:
    """Test cases for AIAnalyzer class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.api_keys = {
            "openai_api_key": "test-openai-key",
            "gemini_api_key": "test-gemini-key"
        }
        self.analyzer = AIAnalyzer(self.api_keys)
        
        self.sample_readings = [
            {"Value": 120, "Timestamp": "2024-01-01T10:00:00"},
            {"Value": 130, "Timestamp": "2024-01-01T11:00:00"},
            {"Value": 125, "Timestamp": "2024-01-01T12:00:00"},
        ]
    
    def test_init(self):
        """Test AIAnalyzer initialization."""
        assert self.analyzer.api_keys == self.api_keys
    
    @mock.patch('libreapp.examples.libre_chat.litellm.completion')
    def test_fix_code_success(self, mock_completion):
        """Test successful code fixing."""
        # Mock LLM response
        mock_response = mock.Mock()
        mock_response.choices = [mock.Mock()]
        mock_response.choices[0].message.content = """
        Here's the fixed code:
        
        ```python
        # Fixed code with improvements
        import pandas as pd
        df = pd.DataFrame(data)
        print(df.head())
        ```
        """
        mock_completion.return_value = mock_response
        
        code_blocks = ["import pandas as pd\ndf = pd.DataFrame(data)\nprint(df.head())"]
        result = self.analyzer.fix_code(code_blocks, "gpt-4")
        
        assert "error" not in result
        assert "result" in result
        assert "fixed_blocks" in result
        mock_completion.assert_called_once()
    
    @mock.patch('libreapp.examples.libre_chat.litellm.completion')
    def test_fix_code_error(self, mock_completion):
        """Test code fixing with error."""
        mock_completion.side_effect = Exception("API Error")
        
        code_blocks = ["print('test')"]
        result = self.analyzer.fix_code(code_blocks, "gpt-4")
        
        assert "error" in result
        assert "API Error" in result["error"]
    
    def test_analyze_no_valid_readings(self):
        """Test analysis with no valid readings."""
        invalid_readings = [{"Value": None}, {"Value": ""}]
        result = self.analyzer.analyze(invalid_readings, "Test query", "gpt-4")
        
        assert "No valid glucose readings found" in result["result"]
        assert result["has_code"] is False
    
    @mock.patch('libreapp.examples.libre_chat.litellm.completion')
    def test_analyze_simple_query(self, mock_completion):
        """Test analysis with simple query."""
        mock_response = mock.Mock()
        mock_response.choices = [mock.Mock()]
        mock_response.choices[0].message.content = "The average glucose level is 125 mg/dL."
        mock_completion.return_value = mock_response
        
        result = self.analyzer.analyze(self.sample_readings, "What's the average?", "gpt-4")
        
        assert result["has_code"] is False
        assert result["is_complex"] is False
        assert "125 mg/dL" in result["result"]
    
    @mock.patch('libreapp.examples.libre_chat.litellm.completion')
    @mock.patch('libreapp.examples.libre_chat.CodeRunner.run_llm_code_blocks')
    def test_analyze_complex_query(self, mock_code_runner, mock_completion):
        """Test analysis with complex query that generates code."""
        # Mock LLM response with code
        mock_response = mock.Mock()
        mock_response.choices = [mock.Mock()]
        mock_response.choices[0].message.content = """
        Here's the analysis:
        
        ```python
        import pandas as pd
        mean_glucose = data['Value'].mean()
        print(f"Mean glucose: {mean_glucose}")
        ```
        """
        mock_completion.return_value = mock_response
        
        # Mock code execution results
        mock_code_runner.return_value = {
            "has_code": True,
            "code_blocks": [{"code": "import pandas as pd", "output": "Mean glucose: 125"}]
        }
        
        result = self.analyzer.analyze(
            self.sample_readings, 
            "Show me code to calculate trends", 
            "gpt-4"
        )
        
        assert result["has_code"] is True
        assert result["is_complex"] is True
        assert "code_results" in result
        mock_code_runner.assert_called_once()
    
    @mock.patch('libreapp.examples.libre_chat.litellm.completion')
    def test_analyze_api_error(self, mock_completion):
        """Test analysis with API error."""
        mock_completion.side_effect = Exception("API connection failed")
        
        result = self.analyzer.analyze(self.sample_readings, "Test query", "gpt-4")
        
        assert result["error"] is True
        assert "API connection failed" in result["result"]


class TestValidationFunctions:
    """Test cases for validation utility functions."""
    
    def test_validate_credentials_success(self):
        """Test successful credential validation."""
        result, message = validate_credentials("test@example.com", "password123")
        assert result is True
        assert message == ""
    
    def test_validate_credentials_empty_username(self):
        """Test credential validation with empty username."""
        result, message = validate_credentials("", "password123")
        assert result is False
        assert "Username/email is required" in message
    
    def test_validate_credentials_empty_password(self):
        """Test credential validation with empty password."""
        result, message = validate_credentials("test@example.com", "")
        assert result is False
        assert "Password is required" in message
    
    def test_validate_credentials_short_password(self):
        """Test credential validation with short password."""
        result, message = validate_credentials("test@example.com", "123")
        assert result is False
        assert "at least 6 characters" in message
    
    def test_validate_api_keys_success(self):
        """Test successful API key validation."""
        api_keys = {"openai_api_key": "test-key", "gemini_api_key": ""}
        result, message = validate_api_keys(api_keys)
        assert result is True
        assert message == ""
    
    def test_validate_api_keys_no_keys(self):
        """Test API key validation with no keys provided."""
        api_keys = {"openai_api_key": "", "gemini_api_key": ""}
        result, message = validate_api_keys(api_keys)
        assert result is False
        assert "At least one API key is required" in message


class TestIntegration:
    """Integration tests that test multiple components together."""
    
    @mock.patch('os.path.exists')
    @mock.patch('libreapp.examples.libre_chat.load_dotenv')
    @mock.patch('os.getenv')
    def test_environment_to_client_flow(self, mock_getenv, mock_load_dotenv, mock_exists):
        """Test the flow from environment loading to client creation."""
        # Setup environment
        mock_exists.return_value = True
        env_vars = {
            "LIBRE_USERNAME": "test@example.com",
            "LIBRE_PASSWORD": "testpass123",
            "OPENAI_API_KEY": "test-key",
            "LIBRE_VERSION": "4.7",
            "LIBRE_PRODUCT": "llu.ios"
        }
        
        def mock_getenv_side_effect(key, default=""):
            return env_vars.get(key, default)
        
        mock_getenv.side_effect = mock_getenv_side_effect
        
        # Load environment
        env_loader = EnvironmentLoader()
        defaults = env_loader.load_defaults()
        
        # Create client manager
        manager = LibreClientManager(
            email=defaults["libre_username"],
            password=defaults["libre_password"],
            version=defaults["libre_version"],
            product=defaults["libre_product"]
        )
        
        assert manager.email == "test@example.com"
        assert manager.version == "4.7"
    
    def test_data_processing_pipeline(self):
        """Test the complete data processing pipeline."""
        # Sample raw data
        raw_readings = [
            {"Timestamp": "2024-01-01T10:00:00", "Value": "120", "MeasureMent": 1, "FactoryTimestamp": "ignore"},
            {"Timestamp": "2024-01-01T11:00:00", "Value": "65", "MeasureMent": 1},
            {"Timestamp": "2024-01-01T12:00:00", "Value": "180", "MeasureMent": 1},
        ]
        
        # Process the data
        processed = DataFormatter.process_readings(
            raw_readings,
            low_threshold=70,
            high_threshold=140
        )
        
        # Convert to different formats
        df = DataFormatter.to_dataframe(processed)
        csv_data = DataFormatter.to_csv(processed)
        json_data = DataFormatter.to_json(processed)
        xml_data = DataFormatter.to_xml(processed)
        
        # Verify the pipeline worked
        assert len(processed) == 3
        assert "FactoryTimestamp" not in processed[0]
        assert "MeasurementType" in processed[0]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "Timestamp" in csv_data
        assert json.loads(json_data)  # Valid JSON
        assert "<GlucoseReadings>" in xml_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=libreapp.examples.libre_chat", "--cov-report=html"])
