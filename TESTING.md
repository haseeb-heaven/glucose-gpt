# Testing Guide for Glucose-GPT

## 🚀 Quick Start

### Run All Tests
```bash
python run_tests.py
```

### Run Tests with pytest
```bash
python -m pytest tests/test_libre_chat_simple.py -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ --cov=glucosegpt --cov-report=html
```

## 📁 Test Structure

```
tests/
├── __init__.py                     # Test package marker
├── conftest.py                     # Shared fixtures and config
├── test_libre_chat_simple.py       # Core unit tests
├── test_libre_chat_integration.py  # Integration tests
└── test_libre_chat.py              # Full pytest test suite

pytest.ini                          # pytest configuration
run_tests.py                        # Test runner script
TEST_SUMMARY.md                     # Detailed test documentation
```

## 🧪 Test Categories

### Unit Tests (`test_libre_chat_simple.py`)
- Environment validation
- API key validation  
- Data processing logic
- Format conversions
- Error handling
- Date filtering

### Integration Tests (`test_libre_chat_integration.py`)
- Component interactions
- Mocked external dependencies
- End-to-end workflows

## 🔧 Dependencies

The following packages are required for testing:
- `pytest>=7.4.0`
- `pytest-cov>=4.0.0`
- `pytest-mock>=3.10.0`
- `pytest-asyncio>=0.21.0`
- `xmltodict>=0.13.0`

Install with:
```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio xmltodict
```

## 📊 Expected Output

### Successful Test Run
```
🧪 Running Glucose-GPT Unit Tests
==================================================
✅ Environment validation tests passed
✅ API key validation tests passed
✅ Data processing tests passed
✅ Data conversion tests passed
✅ Client manager logic tests passed
✅ AI analyzer logic tests passed
✅ Error handling tests passed
✅ Date filtering tests passed
==================================================
🎉 All tests passed successfully!
```

### pytest Output
```
=============== 8 passed in 2.03s ===============
```

## 🐛 Troubleshooting

### Common Issues

**matplotlib backend error**:
```bash
export MPLBACKEND=Agg
python run_tests.py
```

**Import errors**:
- Ensure you're in the project root directory
- Check that all dependencies are installed
- Verify Python path is correct

**Permission errors**:
- Ensure write permissions for test output files
- Check temporary file creation permissions

## 📈 Coverage Reports

After running tests with coverage:
- HTML report: `htmlcov/index.html`
- Terminal output shows coverage percentages
- XML report: `coverage.xml` (for CI/CD)

## 🔄 CI/CD Integration

Tests are designed for continuous integration:
- No external network dependencies
- Fast execution (< 5 seconds)
- Clear exit codes (0 = success, 1 = failure)
- Detailed logging and reporting
