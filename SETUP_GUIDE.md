# 🚀 T&C Analysis System - Complete Setup Guide

**From Zero to Running System in 30 Minutes**

---

## 📋 Prerequisites

### Required Software

| Software | Version | Purpose | Installation |
|----------|---------|---------|--------------|
| **Python** | 3.11+ | Backend runtime | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | Frontend (Week 8+) | [nodejs.org](https://nodejs.org/) |
| **Docker** | 20+ | Services (PostgreSQL, Redis) | [docker.com](https://www.docker.com/get-started) |
| **Git** | Latest | Version control | [git-scm.com](https://git-scm.com/) |

### Required API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| **OpenAI** | Embeddings & GPT-4 | [platform.openai.com](https://platform.openai.com/api-keys) |
| **Pinecone** | Vector database | [pinecone.io](https://app.pinecone.io/) |

### System Requirements

- **OS**: macOS, Linux, or Windows (WSL2)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 5GB free space
- **Network**: Internet connection for API calls

---

## 🎯 Quick Setup (15 Minutes)

### Step 1: Clone Repository (1 min)

```bash
# Navigate to your projects directory
cd ~/Desktop

# If using Git
git clone <repository-url> "Project T&C"
cd "Project T&C"

# Or if you already have the files
cd "/Users/akhil/Desktop/Project T&C"
```

### Step 2: Install Python Dependencies (3 min)

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers (for data collection)
playwright install chromium
```

**Expected output**:
```
Successfully installed fastapi-0.109.0 uvicorn-0.27.0 ...
Playwright browsers installed successfully
```

### Step 3: Configure Environment (2 min)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or use your favorite editor
```

**Required settings** in `.env`:

```bash
# OpenAI (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Pinecone (get from https://app.pinecone.io)
PINECONE_API_KEY=your-actual-pinecone-key-here
PINECONE_INDEX_NAME=tc-analysis  # Create this index in Pinecone

# Generate secret key
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database (use defaults or customize)
DATABASE_URL=postgresql://tcuser:tcpassword@localhost:5432/tcanalysis
```

**Generate SECRET_KEY**:
```bash
openssl rand -hex 32
# Copy output and paste into .env
```

### Step 4: Create Pinecone Index (2 min)

1. Visit [https://app.pinecone.io](https://app.pinecone.io)
2. Click "Create Index"
3. Settings:
   - **Name**: `tc-analysis`
   - **Dimensions**: `1536`
   - **Metric**: `cosine`
   - **Cloud**: AWS
   - **Region**: `us-east-1` (or your preferred region)
4. Click "Create Index"
5. Copy API key to `.env` file

### Step 5: Start Services (2 min)

```bash
# Start PostgreSQL and Redis using Docker
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME                    STATUS              PORTS
# tc-analysis-postgres    Up 10 seconds       0.0.0.0:5432->5432/tcp
# tc-analysis-redis       Up 10 seconds       0.0.0.0:6379->6379/tcp
```

**Troubleshooting**:
```bash
# If Docker not running
docker ps  # Should list containers

# If ports already in use
docker-compose down
# Change ports in docker-compose.yml if needed

# View logs
docker-compose logs postgres
docker-compose logs redis
```

### Step 6: Initialize Database (2 min)

```bash
# Run database migrations
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade  -> <revision>
# INFO  [alembic.runtime.migration] Running upgrade <revision> -> <revision>
```

**Verify database**:
```bash
# Check tables were created
python -c "
from sqlalchemy import inspect
from app.db.session import engine
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Tables created: {tables}')
"

# Expected: ['users', 'documents', 'anomalies']
```

### Step 7: Validate System (3 min)

```bash
# Run comprehensive system validation
python scripts/validate_system.py

# Expected output:
# ============================================================
# 1. ENVIRONMENT CONFIGURATION
# ============================================================
# ✓ .env.example found
# ✓ .env file found
# ✓ OPENAI_API_KEY configured
# ✓ PINECONE_API_KEY configured
# ✓ DATABASE_URL configured
# ✓ SECRET_KEY configured
# ...
# ============================================================
# 📊 VALIDATION SUMMARY
# ============================================================
# OVERALL: 25 passed, 0 failed, 0 warnings
# ✅ SYSTEM FULLY OPERATIONAL
```

**If validation fails**, check the log file:
```bash
cat backend/system_validation.log
```

### Step 8: Start API Server (1 min)

```bash
# Start FastAPI server
uvicorn app.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

**Test API**:
```bash
# In a new terminal
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"1.0.0"}

# Open Swagger UI in browser
open http://localhost:8000/api/v1/docs
```

---

## ✅ Verification Steps

After setup, verify everything works:

### 1. Health Check

```bash
curl http://localhost:8000/health
# ✓ Should return {"status":"healthy"}
```

### 2. Signup Test

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

# ✓ Should return user object with ID
```

### 3. Login Test

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123"

# ✓ Should return JWT token
```

### 4. Document Upload Test

```bash
# Generate test PDF first
python scripts/create_test_pdfs.py

# Get token from login response above
TOKEN="<your-token-here>"

# Upload document
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/test_samples/simple_tos.pdf"

# ✓ Should return document object with analysis results
```

### 5. Integration Tests

```bash
# Run all tests
pytest tests/integration/ -v

# ✓ Should pass 17 tests
```

---

## 🔧 Detailed Setup (Full Configuration)

### Python Virtual Environment (Recommended)

```bash
cd backend

# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Your prompt should now show (venv)
```

**Benefits**:
- Isolated dependencies
- No conflicts with system Python
- Easy to reset

**Deactivate**:
```bash
deactivate
```

### Database Configuration Options

#### Option 1: Docker (Recommended - Already Set Up)

```yaml
# docker-compose.yml already configured
POSTGRES_USER: tcuser
POSTGRES_PASSWORD: tcpassword
POSTGRES_DB: tcanalysis
```

#### Option 2: Local PostgreSQL

If you have PostgreSQL installed locally:

```bash
# Create database
createdb tcanalysis

# Create user
createuser tcuser -P  # Enter password: tcpassword

# Grant privileges
psql -c "GRANT ALL PRIVILEGES ON DATABASE tcanalysis TO tcuser;"

# Update .env
DATABASE_URL=postgresql://tcuser:tcpassword@localhost:5432/tcanalysis
```

#### Option 3: Cloud Database (Production)

For production, use managed PostgreSQL:

- **Heroku Postgres**: Free tier available
- **AWS RDS**: PostgreSQL instances
- **Supabase**: Free PostgreSQL with extras

Update `.env` with connection string:
```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### Redis Configuration Options

#### Option 1: Docker (Recommended - Already Set Up)

```bash
docker-compose up -d redis
```

#### Option 2: Local Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis

# Update .env
REDIS_URL=redis://localhost:6379/0
```

#### Option 3: Skip Redis (Optional)

Redis is optional. System works without it (but slower):

```bash
# In .env, comment out or leave as default
# REDIS_URL=redis://localhost:6379/0

# System will log warning but continue
```

---

## 📊 Environment Variables Reference

### Complete `.env` Template

```bash
# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
APP_NAME="T&C Analysis API"
ENVIRONMENT=development  # development | staging | production
DEBUG=True               # Set to False in production

# =============================================================================
# OPENAI CONFIGURATION
# =============================================================================
OPENAI_API_KEY=sk-proj-...your-key-here...
OPENAI_MODEL_GPT4=gpt-4
OPENAI_MODEL_GPT35=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT=60

# =============================================================================
# PINECONE CONFIGURATION
# =============================================================================
PINECONE_API_KEY=...your-key-here...
PINECONE_ENVIRONMENT=us-east-1  # or your region
PINECONE_INDEX_NAME=tc-analysis
PINECONE_USER_NAMESPACE=user_tcs
PINECONE_BASELINE_NAMESPACE=baseline

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE_URL=postgresql://tcuser:tcpassword@localhost:5432/tcanalysis
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# =============================================================================
# REDIS CONFIGURATION (Optional)
# =============================================================================
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600  # 1 hour in seconds
REDIS_MAX_CONNECTIONS=10

# =============================================================================
# JWT AUTHENTICATION
# =============================================================================
SECRET_KEY=your-secret-key-generate-with-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# =============================================================================
# API SETTINGS
# =============================================================================
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:8000"]

# =============================================================================
# FILE UPLOAD SETTINGS
# =============================================================================
MAX_FILE_SIZE_MB=10
ALLOWED_FILE_TYPES=[".pdf"]

# =============================================================================
# ANOMALY DETECTION SETTINGS
# =============================================================================
PREVALENCE_THRESHOLD=0.30      # Clauses with < 30% prevalence flagged
SIMILARITY_THRESHOLD=0.85       # Similarity score threshold
BASELINE_SAMPLE_SIZE=50         # Number of baseline examples to check

# =============================================================================
# RATE LIMITING
# =============================================================================
RATE_LIMIT_PER_HOUR=100        # API calls per hour per user
```

### Environment-Specific Settings

#### Development
```bash
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=DEBUG
```

#### Production
```bash
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
DATABASE_URL=<production-db-url>
BACKEND_CORS_ORIGINS=["https://your-frontend-domain.com"]
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "Module 'app' has no attribute..."

**Cause**: Python not finding modules

**Solution**:
```bash
# Make sure you're in backend directory
cd backend

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with python -m
python -m app.main
```

### Issue 2: "Port 8000 already in use"

**Cause**: Another process using port 8000

**Solution**:
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --port 8001
```

### Issue 3: "Database connection refused"

**Cause**: PostgreSQL not running

**Solution**:
```bash
# Check Docker container
docker-compose ps

# Restart if needed
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Issue 4: "OpenAI API error 401"

**Cause**: Invalid or missing API key

**Solution**:
```bash
# Verify key in .env
cat .env | grep OPENAI_API_KEY

# Test key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Should list available models
```

### Issue 5: "Pinecone index not found"

**Cause**: Index not created or wrong name

**Solution**:
1. Check index name in Pinecone dashboard
2. Update `PINECONE_INDEX_NAME` in `.env`
3. Restart API server

### Issue 6: "Alembic command not found"

**Cause**: Not in virtual environment or not installed

**Solution**:
```bash
# Activate venv
source venv/bin/activate

# Install alembic
pip install alembic

# Run migration
alembic upgrade head
```

---

## 🎯 Next Steps

### After Successful Setup:

1. **✅ Run System Validation**
   ```bash
   python scripts/validate_system.py
   ```

2. **✅ Test API Endpoints**
   - Open http://localhost:8000/api/v1/docs
   - Try signup, login, upload

3. **✅ Collect Baseline Corpus** (Optional - for anomaly detection)
   ```bash
   python scripts/collect_baseline_corpus.py --category tech
   python scripts/index_baseline_corpus.py --category tech
   ```

4. **✅ Run Integration Tests**
   ```bash
   pytest tests/integration/ -v
   ```

5. **✅ Ready for Frontend!**
   - See [Frontend Development Guide](FRONTEND_GUIDE.md) (Week 8-10)

---

## 📚 Additional Resources

### Documentation
- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Data Collection Guide](docs/DATA_COLLECTION_GUIDE.md)
- [System Validation Guide](SYSTEM_VALIDATION_GUIDE.md)

### Scripts
- `scripts/validate_system.py` - Complete system check
- `scripts/create_test_pdfs.py` - Generate test documents
- `scripts/collect_baseline_corpus.py` - Collect T&Cs
- `scripts/index_baseline_corpus.py` - Index to Pinecone

### Support
- Check logs: `backend/*.log`
- GitHub Issues: [Create issue](https://github.com/your-repo/issues)
- Documentation: `docs/` directory

---

## ✅ Setup Complete Checklist

- [ ] Python 3.11+ installed
- [ ] Docker installed and running
- [ ] OpenAI API key obtained and configured
- [ ] Pinecone account created and index set up
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Playwright browsers installed
- [ ] `.env` file configured
- [ ] Docker services started (`docker-compose up -d`)
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] System validation passed (`python scripts/validate_system.py`)
- [ ] API server starts successfully
- [ ] Health check returns success
- [ ] Can signup/login via API
- [ ] Can upload test document
- [ ] Integration tests pass
- [ ] **Ready to start frontend development!**

---

**Estimated Setup Time**: 15-30 minutes
**Support**: Check documentation or create GitHub issue
**Next**: [Frontend Development Guide](FRONTEND_GUIDE.md)
