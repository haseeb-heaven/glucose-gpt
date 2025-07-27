"""
Shared test fixtures and configuration for Glucose-GPT tests.
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Add the project root to Python path
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, PROJECT_ROOT)

@pytest.fixture
def sample_glucose_readings():
    """Fixture providing sample glucose readings for testing."""
    return [
        {
            "Timestamp": "2024-01-01T10:00:00",
            "Value": 120,
            "MeasureMent": 1,
            "RecordNumber": 1
        },
        {
            "Timestamp": "2024-01-01T11:00:00", 
            "Value": 65,
            "MeasureMent": 1,
            "RecordNumber": 2
        },
        {
            "Timestamp": "2024-01-01T12:00:00",
            "Value": 180,
            "MeasureMent": 1,
            "RecordNumber": 3
        },
        {
            "Timestamp": "2024-01-01T13:00:00",
            "Value": 125,
            "MeasureMent": 1,
            "RecordNumber": 4
        }
    ]

@pytest.fixture
def sample_api_keys():
    """Fixture providing sample API keys for testing."""
    return {
        "openai_api_key": "test-openai-key-12345",
        "anthropic_api_key": "test-anthropic-key-12345",
        "gemini_api_key": "test-gemini-key-12345",
        "cohere_api_key": "",
        "replicate_api_key": ""
    }

@pytest.fixture
def sample_env_vars():
    """Fixture providing sample environment variables."""
    return {
        "LIBRE_USERNAME": "test@example.com",
        "LIBRE_PASSWORD": "testpassword123",
        "OPENAI_API_KEY": "test-openai-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "LIBRE_VERSION": "4.7",
        "LIBRE_PRODUCT": "llu.ios",
        "DEFAULT_MODEL": "gemini/gemini-1.5-flash"
    }

@pytest.fixture
def mock_streamlit():
    """Fixture providing a mock streamlit module."""
    with patch('streamlit.error') as mock_error, \
         patch('streamlit.info') as mock_info, \
         patch('streamlit.warning') as mock_warning, \
         patch('streamlit.toast') as mock_toast:
        
        streamlit_mock = Mock()
        streamlit_mock.error = mock_error
        streamlit_mock.info = mock_info  
        streamlit_mock.warning = mock_warning
        streamlit_mock.toast = mock_toast
        
        yield streamlit_mock

@pytest.fixture
def mock_libre_client():
    """Fixture providing a mock LibreCGMClient."""
    client = Mock()
    client.authenticate.return_value = {"status": 0, "data": {"authTicket": {"token": "test-token"}}}
    client.list_connections.return_value = {
        "status": 0,
        "data": [
            {
                "patientId": "test-patient-123",
                "firstName": "John",
                "lastName": "Doe",
                "targetLow": 70,
                "targetHigh": 140
            }
        ]
    }
    client.get_patient_graph.return_value = {
        "status": 0,
        "data": {
            "graphData": [
                {"Timestamp": "2024-01-01T10:00:00", "Value": 120, "MeasureMent": 1},
                {"Timestamp": "2024-01-01T11:00:00", "Value": 130, "MeasureMent": 1}
            ]
        }
    }
    return client

@pytest.fixture
def mock_litellm_response():
    """Fixture providing a mock LiteLLM response."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "This is a mock AI response for testing."
    return response

@pytest.fixture
def temp_env_file():
    """Fixture creating a temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
LIBRE_USERNAME=test@example.com
LIBRE_PASSWORD=testpass123
OPENAI_API_KEY=test-openai-key
GEMINI_API_KEY=test-gemini-key
LIBRE_VERSION=4.7
LIBRE_PRODUCT=llu.ios
""")
        f.flush()
        yield f.name
    
    # Cleanup
    os.unlink(f.name)

@pytest.fixture(autouse=True)
def setup_logging():
    """Fixture to setup logging for tests."""
    # Mock the logger setup to avoid file creation during tests
    with patch('glucosegpt.examples.glucose_chat.setup_logger') as mock_setup:
        mock_logger = Mock()
        mock_setup.return_value = (mock_logger, mock_logger)
        yield mock_logger

@pytest.fixture
def mock_pandas_dataframe():
    """Fixture providing a mock pandas DataFrame."""
    import pandas as pd
    return pd.DataFrame([
        {"Timestamp": "2024-01-01T10:00:00", "Value": 120, "isLow": False, "isHigh": False},
        {"Timestamp": "2024-01-01T11:00:00", "Value": 65, "isLow": True, "isHigh": False},
        {"Timestamp": "2024-01-01T12:00:00", "Value": 180, "isLow": False, "isHigh": True}
    ])

@pytest.fixture
def mock_plotly_figure():
    """Fixture providing a mock Plotly figure."""
    fig = Mock()
    fig.data = []
    fig.layout = {}
    fig.show = Mock()
    return fig

class MockCodeRunner:
    """Mock version of CodeRunner for testing."""
    
    @staticmethod
    def extract_code_blocks(text: str) -> List[str]:
        """Mock code block extraction."""
        if "```python" in text:
            return ["import pandas as pd\nprint('test')"]
        return []
    
    @staticmethod
    def run_llm_code_blocks(response: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock code execution."""
        if "```python" in response:
            return {
                "has_code": True,
                "code_blocks": [
                    {
                        "code": "import pandas as pd\nprint('test')",
                        "output": "test",
                        "success": True
                    }
                ]
            }
        return {"has_code": False, "code_blocks": []}

@pytest.fixture
def mock_code_runner():
    """Fixture providing a mock CodeRunner."""
    with patch('glucosegpt.examples.glucose_chat.CodeRunner', MockCodeRunner):
        yield MockCodeRunner
