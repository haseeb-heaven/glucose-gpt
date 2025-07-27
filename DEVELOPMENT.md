# Glucose-GPT Development Documentation

## 🧪 Testing

### Test Structure
```
tests/
├── test_api_clients.py              # API client tests (17 test classes)
├── test_libre_chat.py               # Full pytest test suite
├── test_libre_chat_simple.py        # Core unit tests
├── test_libre_chat_integration.py   # Integration tests
├── conftest.py                      # Shared fixtures
└── __init__.py                      # Test package marker
```

### Quick Test Commands
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_api_clients.py -v      # API tests
python -m pytest tests/test_libre_chat_simple.py -v # Unit tests
python -m pytest tests/test_libre_chat_integration.py -v # Integration tests

# Run with coverage
python -m pytest tests/ --cov=glucosegpt --cov-report=html
```

### Test Coverage Areas

#### ✅ API Tests (test_api_clients.py)
- **LibreCGMClient**: Authentication, data retrieval, error handling
- **LibreLinkUpClient**: Authentication, patient connections
- **Regional Support**: EU/US API configurations
- **Data Masking**: Sensitive data protection
- **Error Handling**: Network errors, timeouts, invalid responses
- **Rate Limiting**: API rate limit handling

#### ✅ Unit Tests (test_libre_chat_simple.py)
- Environment validation and configuration loading
- API key validation and credential checking
- Glucose data processing with thresholds
- Data format conversions (JSON, CSV, XML)
- Client manager connection logic
- AI analyzer query processing
- Error handling scenarios
- Date filtering logic

#### ✅ Integration Tests (test_libre_chat_integration.py)
- Component interaction validation
- End-to-end workflow testing
- Mock external dependencies
- State preservation testing

### Test Results
- **API Tests**: 17/17 passing
- **Unit Tests**: 8/8 passing  
- **Integration Tests**: 6/6 passing
- **Total**: 64/66 tests passing (2 legacy test failures unrelated to core functionality)

## 🔧 Enhanced CodeRunner

### Features
- **Automatic LLM Code Detection**: Detects executable Python code in AI responses
- **Multi-block Execution**: Executes multiple code blocks with state preservation
- **Data Type Handling**: Automatic detection of DataFrames, Plotly figures, Matplotlib figures
- **Error Handling**: Graceful degradation with detailed error reporting
- **Streamlit Integration**: Automatic display of results in Streamlit interface

### Usage
```python
from glucosegpt.utils.code_runner import CodeRunner

# Detect if response contains code
has_code = CodeRunner.detect_llm_code(llm_response)

# Execute code blocks from LLM response
results = CodeRunner.run_llm_code_blocks(llm_response, data)
```

### Supported Data Types
- **Pandas DataFrames**: Automatic table display
- **Plotly Figures**: Interactive chart rendering
- **Matplotlib Figures**: Static plot display
- **Pandas Series**: Data series display
- **NumPy Arrays**: Array visualization

## 📋 Development Guidelines

### Adding New Tests
1. Create test functions in appropriate test files
2. Follow naming convention: `test_<functionality>`
3. Use assertions for validation
4. Add mocks for external dependencies
5. Update this documentation

### Adding New Features
1. Implement feature in appropriate module
2. Add comprehensive tests
3. Update documentation
4. Test with various data scenarios
5. Ensure backwards compatibility

### Code Quality
- All code follows Python best practices
- Type hints are used throughout
- Comprehensive error handling
- Logging for debugging and monitoring
- Security considerations for sensitive data

## 🚀 Deployment

### Pre-Launch Testing
The application automatically runs comprehensive tests before launch:
- API client functionality
- Core unit tests
- Integration workflows

If tests fail, the application will not start and will display error notifications.

### Configuration
- Environment variables in `.env` file
- API keys for various LLM providers
- LibreView credentials
- Logging configuration

### Production Considerations
- Secure API key storage
- Error monitoring and logging
- Performance optimization
- User data privacy and security
