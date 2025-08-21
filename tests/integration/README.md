# 🔗 Integration Tests

Integration tests for the Support Quality Intelligence Backend system.

## 📋 Available Tests

### 🤖 RAG Pipeline Tests
- **`test_rag_pipeline_comprehensive.py`** - Complete RAG workflow testing
- **`test_rag_verification_corrected.py`** - RAG verification with proper parameters

### 🌐 API Tests  
- **`test_actual_endpoints.py`** - All available API endpoints
- **`test_api_endpoints.py`** - Alert system API testing
- **`test_basic_functionality.py`** - Core system functionality

### 📊 System Tests
- **`test_api_only_alerts.py`** - Alert system without email notifications

## 🚀 Running Integration Tests

### Prerequisites
```bash
# Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001

# Verify system health
curl http://localhost:5001/health
```

### Run Individual Tests
```bash
cd tests/integration

# Test RAG pipeline
python test_rag_pipeline_comprehensive.py

# Test API endpoints
python test_actual_endpoints.py

# Test basic functionality
python test_basic_functionality.py
```

### Expected Test Duration
- **Basic functionality**: ~30 seconds
- **API endpoints**: ~60 seconds  
- **RAG pipeline**: ~3-5 minutes (comprehensive analysis)

## 📊 Test Coverage

### RAG Pipeline Testing
- ✅ Claim extraction from support responses
- ✅ Evidence retrieval from vector store
- ✅ Fact verification against evidence
- ✅ Compliance checking against guidelines
- ✅ Feedback generation and scoring
- ✅ Database storage of results

### API Testing
- ✅ All REST endpoints functionality
- ✅ Request/response validation
- ✅ Error handling and status codes
- ✅ Authentication and authorization
- ✅ Performance and response times

### System Integration
- ✅ Database connectivity
- ✅ Vector store operations
- ✅ OpenAI API integration
- ✅ Alert system functionality
- ✅ Email processing workflow

## 🔧 Test Configuration

Tests automatically use:
- **Server**: http://localhost:5001
- **Database**: MySQL (from .env)
- **Vector Store**: Qdrant Cloud
- **AI Models**: OpenAI GPT-4 series

## 📈 Performance Expectations

### Response Times
- **Health check**: <100ms
- **Simple API calls**: <500ms
- **RAG verification**: 30-180 seconds
- **Database operations**: <200ms

### Success Rates
- **API endpoints**: 100% success expected
- **RAG pipeline**: >90% success rate
- **Database operations**: 100% success expected

## ⚠️ Troubleshooting

### Common Issues
1. **Server not running**: Start with `uvicorn app.main:app --port 5001`
2. **Database connection**: Check MySQL service and .env configuration
3. **Vector store timeout**: Verify Qdrant Cloud connectivity
4. **OpenAI API limits**: Check API key and rate limits
5. **Long processing times**: RAG pipeline is computationally intensive

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python test_rag_pipeline_comprehensive.py
```

## 📊 Test Results

Tests generate detailed output including:
- ✅ Success/failure status for each component
- ⏱️ Processing times and performance metrics
- 📊 Quality scores and verification results
- 🔍 Detailed error messages and stack traces
- 💡 Recommendations for improvements

---

**Last Updated**: August 21, 2025  
**Test Environment**: Development/Staging
