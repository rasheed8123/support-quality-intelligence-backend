# 🛠️ Setup Scripts

This folder contains all setup and maintenance scripts for the Support Quality Intelligence Backend.

## **📋 Script Overview**

### **🗄️ Database Setup**
- **`create_database.py`** - Creates the MySQL database on AWS RDS
- **`init_production_db.py`** - Initializes database tables and tests connections

### **🔍 Vector Store Setup**
- **`setup_qdrant.py`** - Manages Qdrant configuration (local/cloud/memory)
- **`embed_data.py`** - Embeds documents from /data folder into Qdrant
- **`inspect_data.py`** - Analyzes documents before embedding

### **🔧 Testing & Validation**
- **`test_connections.py`** - Tests MySQL and Qdrant connections
- **`validate_setup.py`** - Validates Gmail webhook setup

### **📧 Gmail Integration**
- **`setup_gmail_auth.py`** - Sets up Gmail API authentication

## **🚀 Usage Instructions**

### **Initial Production Setup**

1. **Test Connections** (verify setup):
   ```bash
   python scripts/test_connections.py
   ```

2. **Create Database** (run once if needed):
   ```bash
   python scripts/create_database.py
   ```

3. **Initialize Production Environment** (if needed):
   ```bash
   python scripts/init_production_db.py
   ```

### **Data Embedding Workflow**

1. **Inspect Available Data**:
   ```bash
   python scripts/inspect_data.py
   ```

2. **Embed Data into Qdrant**:
   ```bash
   python scripts/embed_data.py
   ```

3. **Setup Gmail Authentication** (if needed):
   ```bash
   python scripts/setup_gmail_auth.py
   ```

### **Vector Store Management**

```bash
# Use Qdrant Cloud (production)
python setup_qdrant.py start

# Use memory store (development)
python setup_qdrant.py memory

# Check Qdrant status
python setup_qdrant.py status

# Stop Qdrant (if using local Docker)
python setup_qdrant.py stop
```

## **🔄 Application Startup Workflow**

### **How Connections Are Activated:**

1. **Application Start** (`python main.py`):
   ```
   main.py → app.main:app → FastAPI(lifespan=lifespan_manager)
   ```

2. **Lifespan Manager** (`app/core/connections.py`):
   ```
   startup → connection_manager.initialize_connections()
   ├── _initialize_database() → MySQL connection pool
   └── _initialize_vector_store() → Qdrant Cloud connection
   ```

3. **Runtime Usage**:
   ```
   API Request → Dependency Injection → get_database() / get_vector_store()
   ```

4. **Shutdown**:
   ```
   shutdown → connection_manager.close_connections()
   ```

## **📊 Connection Architecture**

### **Production Connections**
- **MySQL Database**: AWS RDS with connection pooling
- **Qdrant Vector Store**: Cloud instance with API key auth
- **Gmail API**: OAuth2 with refresh tokens
- **Google Drive API**: Service account authentication

### **Connection Manager Features**
- ✅ Automatic connection initialization on startup
- ✅ Health checks for all services
- ✅ Graceful shutdown handling
- ✅ Connection pooling and recycling
- ✅ Error handling and retry logic

## **🔍 Health Monitoring**

### **Health Check Endpoints**
- `GET /health` - Simple OK/not OK status
- `GET /health/` - Detailed health with connection status
- `GET /health/detailed` - Comprehensive system information
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

### **Connection Status**
The connection manager provides real-time status for:
- Database connection and query performance
- Vector store availability and collection count
- OpenAI API accessibility
- Google services authentication

## **⚠️ Important Notes**

1. **Scripts are for setup only** - They don't run during normal application operation
2. **Connection manager handles runtime** - All connections are managed automatically
3. **Environment variables required** - Ensure `.env` file is properly configured
4. **Run scripts from project root** - Use `python scripts/script_name.py`

## **🔧 Troubleshooting**

### **Database Issues**
```bash
# Test database connection
python scripts/create_database.py

# Reinitialize tables
python scripts/init_production_db.py
```

### **Vector Store Issues**
```bash
# Check Qdrant status
python scripts/setup_qdrant.py status

# Switch to memory store temporarily
python scripts/setup_qdrant.py memory
```

### **Gmail Issues**
```bash
# Validate Gmail setup
python scripts/validate_setup.py

# Recreate Gmail credentials
python scripts/setup_gmail_auth.py
```

---

**✅ All scripts are designed to be run independently and are safe to re-run multiple times.**
