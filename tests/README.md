# 🧪 Test Suite

This directory contains all test files for the Support Quality Intelligence Backend.

## 📁 Directory Structure

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for full workflows
├── performance/    # Performance and load tests
└── temp/          # Temporary test files (ignored by git)
```

## 🚀 Running Tests

### Prerequisites
```bash
# Ensure server is running
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001

# Install test dependencies
pip install pytest pytest-asyncio requests
```

### Run Integration Tests
```bash
# From project root
cd tests/integration
python test_rag_pipeline_comprehensive.py
python test_actual_endpoints.py
python test_basic_functionality.py
```

### Run All Tests
```bash
# From project root
pytest tests/ -v
```

## 📋 Test Categories

### Integration Tests (`integration/`)
- **RAG Pipeline Tests**: End-to-end RAG verification workflow
- **API Endpoint Tests**: REST API functionality
- **Database Integration**: Database operations and storage
- **Email Processing**: Complete email classification workflow

### Unit Tests (`unit/`)
- Component-specific tests
- Mock-based testing
- Fast execution tests

### Performance Tests (`performance/`)
- Load testing
- Response time benchmarks
- Memory usage analysis
- Concurrent request handling

## 🔧 Test Configuration

Tests use the same configuration as the main application:
- Database: MySQL connection
- Vector Store: Qdrant Cloud
- APIs: OpenAI GPT-4 models
- Environment: `.env` file settings

## 📊 Test Reports

Test results and reports are automatically generated in:
- `tests/temp/` - Temporary test outputs
- Console output with detailed logging
- Performance metrics and timing data

## ⚠️ Important Notes

1. **Never commit test files to root directory**
2. **All test scripts belong in appropriate subdirectories**
3. **Use `tests/temp/` for temporary test data**
4. **Clean up test data after test completion**
5. **Mock external services when possible**

## 🎯 Best Practices

- **Descriptive test names**: `test_rag_pipeline_with_course_inquiry`
- **Proper setup/teardown**: Clean state between tests
- **Isolated tests**: No dependencies between test cases
- **Comprehensive coverage**: Test both success and failure paths
- **Performance awareness**: Monitor test execution times

---

**Last Updated**: August 21, 2025  
**Test Framework**: Custom integration tests + pytest for unit tests
