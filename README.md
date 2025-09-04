# 🤖 Support Quality Intelligence Backend

A production-grade RAG-powered system for automated support quality verification and real-time alerts.

## 🎯 **Overview**

This system provides comprehensive support response quality analysis using:
- **RAG Pipeline**: Fact verification against knowledge base
- **AI Agent**: Automated email classification and analysis
- **Real-time Alerts**: Quality issue detection and notifications
- **API-First Design**: Complete REST API for frontend integration

## ✨ **Key Features**

### 🔍 **RAG Verification Pipeline**
- **Claim Extraction**: AI-powered identification of verifiable statements
- **Evidence Retrieval**: Multi-collection vector search with semantic reranking
- **Fact Verification**: Claims verified against authoritative sources
- **Compliance Checking**: Policy and guideline adherence validation
- **Quality Scoring**: Comprehensive accuracy and compliance metrics

### 🚨 **Real-time Alert System**
- **SLA Monitoring**: Response time breach detection
- **Quality Alerts**: Factual errors and negative sentiment detection
- **Aging Query Tracking**: Unresponded query identification
- **API-Only Mode**: No email notifications, pure API integration

### 🤖 **AI Agent Orchestration**
- **Email Classification**: Automated inbound/outbound processing
- **Priority Detection**: Urgency and importance assessment
- **Category Assignment**: Intelligent topic classification
- **Quality Analysis**: Automated response evaluation

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Email Input   │───▶│   AI Agent      │───▶│  RAG Pipeline   │
│                 │    │  Orchestration   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Alert System  │◀───│    Database      │◀───│ Quality Scoring │
│                 │    │    Storage       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.9+
- MySQL 8.0+
- Qdrant Cloud account
- OpenAI API key

### **Installation**
```bash
# Clone repository
git clone <repository-url>
cd support-quality-intelligence-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### **Configuration**
```bash
# Required environment variables
OPENAI_API_KEY=your_openai_api_key
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_URL=your_qdrant_cloud_url
DATABASE_URL=mysql://user:password@localhost/dbname
```

### **Database Setup**
```bash
# Initialize database
python scripts/create_database.py

# Embed training data
python scripts/embed_data.py

# Validate setup
python scripts/validate_setup.py
```

### **Run Application**
```bash
# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001

# Verify health
curl http://localhost:5001/health
```

## 📊 **API Endpoints**

### **Core Verification**
- `POST /api/v1/verify-support-response` - RAG verification
- `GET /health` - System health check
- `GET /` - API information

### **Alert System**
- `GET /alerts/dashboard` - Real-time dashboard data
- `GET /alerts/active` - Active alerts list
- `GET /alerts/statistics` - Analytics and metrics
- `POST /alerts/{id}/acknowledge` - Acknowledge alert
- `POST /alerts/{id}/resolve` - Resolve alert

### **System Monitoring**
- `GET /alerts/scheduler/status` - Background job status
- `POST /alerts/scheduler/trigger/{type}` - Manual checks

## 🧪 **Testing**

### **Run Tests**
```bash
# Integration tests
cd tests/integration
python test_rag_pipeline_comprehensive.py
python test_actual_endpoints.py

# All tests
pytest tests/ -v
```

### **Test Categories**
- **Integration**: End-to-end workflow testing
- **Unit**: Component-specific testing
- **Performance**: Load and benchmark testing

## 📁 **Project Structure**

```
├── app/                    # Main application code
│   ├── api/               # FastAPI routes and models
│   ├── services/          # Business logic services
│   ├── db/                # Database models and operations
│   └── core/              # Core functionality
├── tests/                 # All test files (organized by type)
├── docs/                  # Documentation and API guides
├── scripts/               # Setup and utility scripts
├── data/                  # Training and reference data
└── config/                # Configuration files
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed organization.

## 📚 **Documentation**

- **[API Documentation](docs/FRONTEND_API_DOCUMENTATION.md)** - Complete API reference
- **[Quick Reference](docs/API_QUICK_REFERENCE.md)** - Developer quick guide
- **[Integration Guide](docs/FRONTEND_INTEGRATION_SUMMARY.md)** - Frontend integration
- **[Project Structure](PROJECT_STRUCTURE.md)** - Codebase organization

## 🔧 **Development**

### **Adding Features**
1. Business logic in `app/services/`
2. API routes in `app/api/`
3. Tests in `tests/` (never root!)
4. Documentation in `docs/`

### **Code Standards**
- **Clean Architecture**: Separation of concerns
- **Type Hints**: Full type annotation
- **Documentation**: Comprehensive docstrings
- **Testing**: Unit and integration coverage
- **Security**: Proper credential handling

## 🚨 **Production Deployment**

### **Docker**
```bash
# Build image
docker build -t support-quality-backend .

# Run with compose
docker-compose up -d
```

### **Environment Setup**
- **Database**: MySQL 8.0+ with proper indexing
- **Vector Store**: Qdrant Cloud with 3 collections
- **API Keys**: OpenAI GPT-4 access
- **Monitoring**: Health checks and logging

## 📈 **Performance**

### **Current Metrics**
- **API Response**: <500ms for simple endpoints
- **RAG Verification**: 30-180 seconds (comprehensive analysis)
- **Alert Processing**: <100ms
- **Database Operations**: <200ms

### **Optimization Opportunities**
- Parallel processing for RAG pipeline
- Caching for repeated queries
- Connection pooling for external APIs

## 🤝 **Contributing**

1. **Follow project structure** - No test files in root
2. **Add comprehensive tests** - Unit and integration
3. **Update documentation** - Keep docs current
4. **Security first** - Never commit credentials

## 📄 **License**

[Add your license information here]

---

**Status**: ✅ Production Ready (with optimizations recommended)
**Last Updated**: August 21, 2025
**Version**: 1.0.0
