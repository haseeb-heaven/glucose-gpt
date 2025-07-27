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
from glucosegpt.examples.glucose_chat import (
    ConfigurationLoader,
    LibreClientManager,
    DataFormatter,
    ChartGenerator,
    AIAnalyzer,
    validate_credentials,
    validate_api_keys
)

class TestConfigurationLoader:
    """Test cases for ConfigurationLoader class."""
    
    def setup_method(self):
        """Setup for each test method."""
        with mock.patch('glucosegpt.examples.glucose_chat.config_manager'):
            self.config_loader = ConfigurationLoader()
    
    @mock.patch('glucosegpt.examples.glucose_chat.config_manager')
    def test_load_defaults_success(self, mock_config_manager):
        """Test successful configuration loading."""
        mock_config_manager.has_required_credentials.return_value = True
        mock_config_manager.get_libre_config.return_value = {
            'username': 'test@example.com',
            'password': 'testpass123',
            'version': '4.9.0',
            'product': 'llu.android'
        }
        mock_config_manager.get_api_keys.return_value = {
            'openai_api_key': 'test-key',
            'gemini_api_key': '',
            'anthropic_api_key': '',
            'cohere_api_key': '',
            'replicate_api_key': ''
        }
        mock_config_manager.get.return_value = 'gemini/gemini-1.5-flash'
        
        result = self.config_loader.load_defaults()
        assert result['libre_username'] == 'test@example.com'
        assert result['openai_api_key'] == 'test-key'
    
    @mock.patch('streamlit.error')
    @mock.patch('glucosegpt.examples.glucose_chat.config_manager')
    def test_load_defaults_missing_credentials(self, mock_config_manager, mock_st_error):
        """Test configuration loading with missing credentials."""
        mock_config_manager.has_required_credentials.return_value = False
        mock_config_manager.get_missing_credentials.return_value = {
            'libre': ['LIBRE_USERNAME'],
            'ai': []
        }
        
        result = self.config_loader.load_defaults()
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
    
    @mock.patch('glucosegpt.examples.glucose_chat.LibreCGMClient')
    @mock.patch('glucosegpt.examples.glucose_chat.ApiConfig')
    @mock.patch('glucosegpt.examples.glucose_chat.DefaultDataMasker')
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
    
    @mock.patch('glucosegpt.examples.glucose_chat.LibreCGMClient')
    @mock.patch('glucosegpt.examples.glucose_chat.ApiConfig')
    @mock.patch('glucosegpt.examples.glucose_chat.DefaultDataMasker')
    @mock.patch('streamlit.toast')
    def test_connect_auth_failure(self, mock_toast, mock_masker, mock_config, mock_client_class):
        """Test connection failure due to authentication."""
        mock_client = mock.Mock()
        mock_client.authenticate.return_value = {"status": 1}  # Auth failure
        mock_client_class.return_value = mock_client
        
        result = self.manager.connect()
        
        assert result is False
        mock_toast.assert_called()
    
    @mock.patch('glucosegpt.examples.glucose_chat.LibreCGMClient')
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
        
        # Mock all the dependencies more comprehensively
        with mock.patch('glucosegpt.examples.glucose_chat.pd.DataFrame') as mock_df_class, \
             mock.patch('glucosegpt.examples.glucose_chat.pd.to_datetime') as mock_to_datetime, \
             mock.patch('glucosegpt.examples.glucose_chat.px.line') as mock_line:
            
            # Create a mock DataFrame instance
            mock_df_instance = mock.Mock()
            mock_df_class.return_value = mock_df_instance
            
            # Mock DataFrame properties and methods
            mock_df_instance.empty = False
            mock_df_instance.shape = (3, 2)
            
            # Mock series for subscripting behavior
            mock_timestamp_series = mock.Mock()
            mock_value_series = mock.Mock()
            
            # Mock comparison operations to return boolean masks
            mock_mask = mock.Mock()
            mock_value_series.__ge__ = mock.Mock(return_value=mock_mask)
            mock_value_series.__le__ = mock.Mock(return_value=mock_mask)
            mock_mask.__and__ = mock.Mock(return_value=mock_mask)
            
            mock_df_instance.__getitem__ = mock.Mock(side_effect=lambda key: {
                'Timestamp': mock_timestamp_series,
                'Value': mock_value_series
            }.get(key, mock_df_instance))  # Return df for filtering operations
            
            # Mock item assignment (df['column'] = value)
            mock_df_instance.__setitem__ = mock.Mock()
            
            # Mock the filtering operations
            mock_df_instance.__len__ = mock.Mock(return_value=3)
            mock_df_instance.sort_values = mock.Mock(return_value=mock_df_instance)
            
            # Mock to_datetime
            mock_to_datetime.return_value = mock_timestamp_series
            
            # Mock plotly.express
            mock_fig = mock.Mock()
            mock_line.return_value = mock_fig
            mock_fig.update_traces = mock.Mock()
            mock_fig.update_layout = mock.Mock()
            
            # This test mainly verifies the filtering logic
            # The actual chart creation is hard to test without plotly dependencies
            result = ChartGenerator.create_glucose_chart(
                readings_with_outlier, 
                "line", 
                settings_with_filter
            )
            
            # Verify that a figure was returned
            assert result is not None


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
    
    @mock.patch('glucosegpt.examples.glucose_chat.litellm.completion')
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
    
    @mock.patch('glucosegpt.examples.glucose_chat.litellm.completion')
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
    
    @mock.patch('glucosegpt.examples.glucose_chat.litellm.completion')
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
    
    @mock.patch('glucosegpt.examples.glucose_chat.litellm.completion')
    @mock.patch('glucosegpt.examples.glucose_chat.CodeRunner.run_llm_code_blocks')
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
    
    @mock.patch('glucosegpt.examples.glucose_chat.litellm.completion')
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
    
    def test_environment_to_client_flow(self):
        """Test the flow from configuration loading to client creation."""
        # Load configuration using mocked config manager
        with mock.patch('glucosegpt.examples.glucose_chat.config_manager') as mock_config_manager:
            mock_config_manager.has_required_credentials.return_value = True
            mock_config_manager.get_libre_config.return_value = {
                'username': 'test@example.com',
                'password': 'testpass123',
                'version': '4.7',
                'product': 'llu.ios'
            }
            mock_config_manager.get_api_keys.return_value = {
                'openai_api_key': 'test-key',
                'gemini_api_key': '',
                'anthropic_api_key': '',
                'cohere_api_key': '',
                'replicate_api_key': ''
            }
            mock_config_manager.get.return_value = 'gemini/gemini-1.5-flash'
            
            config_loader = ConfigurationLoader()
            defaults = config_loader.load_defaults()
        
        # Create client manager
        manager = LibreClientManager(
            email=defaults["libre_username"],
            password=defaults["libre_password"],
            version=defaults["libre_version"],
            product=defaults["libre_product"]
        )
        
        assert manager.email == "test@example.com"
        assert manager.version == "4.7"
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
    pytest.main([__file__, "-v", "--cov=glucosegpt.examples.glucose_chat", "--cov-report=html"])
