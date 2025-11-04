# 🔍 System Validation & Testing Guide

**Before Frontend Development - Complete System Check**

This guide provides step-by-step instructions to validate every component of the T&C Analysis System before moving to frontend development.

---

## 📋 Pre-Validation Checklist

Before running validations, ensure:

- [ ] Python 3.11+ installed
- [ ] PostgreSQL installed and running
- [ ] Redis installed (optional but recommended)
- [ ] OpenAI API key obtained
- [ ] Pinecone account created and API key obtained

---

## 🚀 Quick Validation (5 Minutes)

### Step 1: Install Dependencies

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Install all Python dependencies
pip install -r requirements.txt

# Install Playwright browsers (for data collection)
playwright install chromium
```

### Step 2: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set your API keys
nano .env  # or use your favorite editor

# Required settings:
# - OPENAI_API_KEY=sk-your-actual-key
# - PINECONE_API_KEY=your-actual-key
# - SECRET_KEY=generate-with-openssl-rand-hex-32
# - DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

Generate SECRET_KEY:
```bash
openssl rand -hex 32
```

### Step 3: Start Services

```bash
# Start PostgreSQL and Redis (using Docker)
cd "/Users/akhil/Desktop/Project T&C/backend"
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected output:
# NAME                COMMAND                  STATUS              PORTS
# tc-postgres        "docker-entrypoint.s…"   Up                  5432->5432
# tc-redis           "docker-entrypoint.s…"   Up                  6379->6379
```

### Step 4: Run Database Migrations

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Initialize alembic (if not already done)
alembic upgrade head

# Should see:
# INFO  [alembic.runtime.migration] Running upgrade -> <revision>, create initial tables
```

### Step 5: Run System Validation

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Run complete validation
python scripts/validate_system.py

# Expected output:
# ============================================================
# 1. ENVIRONMENT CONFIGURATION
# ============================================================
# ✓ .env.example found
# ✓ .env file found
# ✓ OPENAI_API_KEY configured
# ✓ PINECONE_API_KEY configured
# ...
# ✅ SYSTEM FULLY OPERATIONAL
```

---

## 🧪 Comprehensive Testing (30 Minutes)

### Phase 1: Environment & Configuration (2 minutes)

```bash
# Test 1: Verify configuration loads
python -c "from app.core.config import settings; print(f'Environment: {settings.ENVIRONMENT}')"

# Test 2: Check all required settings
python -c "
from app.core.config import settings
required = ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'DATABASE_URL', 'SECRET_KEY']
for key in required:
    val = getattr(settings, key)
    status = '✓' if val and not val.startswith('your-') else '✗'
    print(f'{status} {key}')
"
```

**Expected Output**:
```
✓ OPENAI_API_KEY
✓ PINECONE_API_KEY
✓ DATABASE_URL
✓ SECRET_KEY
```

---

### Phase 2: Database Connectivity (3 minutes)

```bash
# Test 1: Database connection
python -c "
from app.db.session import engine
with engine.connect() as conn:
    print('✓ Database connection successful')
"

# Test 2: Check tables exist
python -c "
from sqlalchemy import inspect
from app.db.session import engine
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Tables found: {tables}')
expected = ['users', 'documents', 'anomalies']
for table in expected:
    status = '✓' if table in tables else '✗'
    print(f'{status} Table {table}')
"

# Test 3: Test CRUD operations
python -c "
from app.db.session import SessionLocal
from app.models.user import User
from app.utils.security import get_password_hash

db = SessionLocal()

# Create test user
test_user = User(
    email='test@example.com',
    hashed_password=get_password_hash('testpass123'),
    full_name='Test User'
)
db.add(test_user)
db.commit()
print(f'✓ Created test user: {test_user.email}')

# Query test user
user = db.query(User).filter(User.email == 'test@example.com').first()
print(f'✓ Retrieved user: {user.email}')

# Delete test user
db.delete(user)
db.commit()
print('✓ Deleted test user')

db.close()
"
```

---

### Phase 3: External Services (10 minutes)

#### OpenAI Service

```bash
# Test 1: Embedding generation
python -c "
import asyncio
from app.services.openai_service import OpenAIService

async def test():
    service = OpenAIService()
    embedding = await service.create_embedding('test text')
    print(f'✓ Generated embedding with dimension: {len(embedding)}')
    await service.close()

asyncio.run(test())
"

# Test 2: GPT-4 completion
python -c "
import asyncio
from app.services.openai_service import OpenAIService

async def test():
    service = OpenAIService()
    response = await service.create_completion(
        prompt='Say hello in one word',
        model='gpt-3.5-turbo',
        max_tokens=10
    )
    print(f'✓ GPT response: {response}')
    await service.close()

asyncio.run(test())
"

# Test 3: Batch embeddings
python -c "
import asyncio
from app.services.openai_service import OpenAIService

async def test():
    service = OpenAIService()
    texts = ['text 1', 'text 2', 'text 3']
    embeddings = await service.batch_create_embeddings(texts)
    print(f'✓ Generated {len(embeddings)} embeddings')
    await service.close()

asyncio.run(test())
"
```

#### Pinecone Service

```bash
# Test 1: Initialize and get stats
python -c "
import asyncio
from app.services.pinecone_service import PineconeService
from app.core.config import settings

async def test():
    service = PineconeService()
    await service.initialize()

    stats = service.index.describe_index_stats()
    print(f'✓ Pinecone connected')
    print(f'   Index: {settings.PINECONE_INDEX_NAME}')
    print(f'   Total vectors: {stats.get(\"total_vector_count\", 0):,}')

    namespaces = stats.get('namespaces', {})
    for ns_name, ns_stats in namespaces.items():
        print(f'   {ns_name}: {ns_stats.get(\"vector_count\", 0):,} vectors')

    await service.close()

asyncio.run(test())
"

# Test 2: Upsert and query
python -c "
import asyncio
from app.services.pinecone_service import PineconeService
from app.services.openai_service import OpenAIService
from app.core.config import settings

async def test():
    openai = OpenAIService()
    pinecone = PineconeService()
    await pinecone.initialize()

    # Create test chunk
    test_text = 'This is a test clause for validation'
    embedding = await openai.create_embedding(test_text)

    chunks = [{
        'text': test_text,
        'embedding': embedding,
        'metadata': {
            'section': 'Test',
            'clause_number': '1',
            'document_id': 'test_validation'
        }
    }]

    # Upsert to user namespace
    await pinecone.upsert_chunks(
        chunks=chunks,
        namespace=settings.PINECONE_USER_NAMESPACE,
        document_id='test_validation'
    )
    print('✓ Upserted test vector')

    # Query it back
    results = await pinecone.query(
        query_embedding=embedding,
        namespace=settings.PINECONE_USER_NAMESPACE,
        top_k=1,
        filter={'document_id': 'test_validation'}
    )
    print(f'✓ Retrieved {len(results)} results')

    # Clean up
    await pinecone.delete_document('test_validation', settings.PINECONE_USER_NAMESPACE)
    print('✓ Cleaned up test data')

    await openai.close()
    await pinecone.close()

asyncio.run(test())
"
```

#### Redis Cache Service

```bash
# Test 1: Connect and basic operations
python -c "
import asyncio
from app.services.cache_service import CacheService

async def test():
    cache = CacheService()
    await cache.connect()

    # Set
    await cache.set('test_key', {'data': 'test'}, ttl=60)
    print('✓ Set cache value')

    # Get
    value = await cache.get('test_key')
    print(f'✓ Retrieved value: {value}')

    # Delete
    await cache.delete('test_key')
    print('✓ Deleted cache value')

    await cache.disconnect()

asyncio.run(test())
"
```

---

### Phase 4: Core Processing Modules (5 minutes)

#### Document Processor

```bash
# Test 1: Create test PDF
python scripts/create_test_pdfs.py

# Test 2: Extract text from test PDF
python -c "
import asyncio
from app.core.document_processor import DocumentProcessor
from pathlib import Path

async def test():
    processor = DocumentProcessor()
    pdf_path = 'data/test_samples/simple_tos.pdf'

    if Path(pdf_path).exists():
        extracted = await processor.extract_text(pdf_path)
        print(f'✓ Extracted {len(extracted[\"text\"])} characters')
        print(f'   Pages: {extracted[\"page_count\"]}')
        print(f'   Method: {extracted[\"extraction_method\"]}')
    else:
        print('✗ Test PDF not found. Run: python scripts/create_test_pdfs.py')

asyncio.run(test())
"
```

#### Structure Extractor

```bash
python -c "
import asyncio
from app.core.structure_extractor import StructureExtractor

async def test():
    extractor = StructureExtractor()

    test_text = '''
    1. ACCEPTANCE OF TERMS
    By accessing this service, you agree to be bound by these terms.

    2. USER OBLIGATIONS
    You agree to use the service responsibly and comply with all applicable laws.

    3. LIMITATION OF LIABILITY
    The service is provided as-is without warranties of any kind.
    '''

    clauses = await extractor.extract_structure(test_text)
    print(f'✓ Extracted {len(clauses)} clauses')
    for clause in clauses[:3]:
        print(f'   - {clause.section}: {clause.text[:50]}...')

asyncio.run(test())
"
```

#### Legal Chunker

```bash
python -c "
import asyncio
from app.core.legal_chunker import LegalChunker
from app.core.structure_extractor import Clause

async def test():
    chunker = LegalChunker(max_chunk_size=500, overlap=50)

    test_clauses = [
        Clause(
            section='Test Section',
            subsection='',
            clause_number='1',
            text='This is a test clause. ' * 100,
            level=0
        )
    ]

    chunks = await chunker.create_chunks(test_clauses)
    print(f'✓ Created {len(chunks)} chunks')
    print(f'   Chunk 1 length: {len(chunks[0][\"text\"])} chars')
    print(f'   Metadata keys: {list(chunks[0][\"metadata\"].keys())}')

asyncio.run(test())
"
```

---

### Phase 5: API Endpoints (5 minutes)

#### Start API Server

```bash
# Terminal 1: Start server
cd "/Users/akhil/Desktop/Project T&C/backend"
uvicorn app.main:app --reload --port 8000

# Wait for: "Application startup complete"
```

#### Test Endpoints (in new terminal)

```bash
# Test 1: Health check
curl http://localhost:8000/health

# Expected:
# {"status":"healthy","version":"1.0.0","environment":"development"}

# Test 2: Root endpoint
curl http://localhost:8000/

# Test 3: OpenAPI docs
open http://localhost:8000/api/v1/docs
# Should open Swagger UI in browser

# Test 4: Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com","password":"testpass123","full_name":"Test User"}'

# Expected:
# {"id":"...","email":"testuser@example.com","full_name":"Test User",...}

# Test 5: Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser@example.com&password=testpass123"

# Expected:
# {"access_token":"eyJ...","token_type":"bearer"}

# Save token for next tests
TOKEN="<paste-token-here>"

# Test 6: Upload document
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/test_samples/simple_tos.pdf"

# Expected:
# {"id":"...","filename":"simple_tos.pdf","page_count":2,...}

# Test 7: Query document
DOC_ID="<paste-document-id-here>"

curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOC_ID\",\"question\":\"What are the terms of service?\"}"

# Expected:
# {"question":"...","answer":"...","citations":[...],"confidence":0.9}

# Test 8: Get anomalies
curl http://localhost:8000/api/v1/anomalies/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"

# Expected:
# {"anomalies":[...],"stats":{"total":0,"high":0,"medium":0,"low":0}}
```

---

### Phase 6: Integration Tests (5 minutes)

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Run all integration tests
pytest tests/integration/ -v

# Expected:
# tests/integration/test_full_pipeline.py::TestFullPipeline::test_signup PASSED
# tests/integration/test_full_pipeline.py::TestFullPipeline::test_login PASSED
# tests/integration/test_full_pipeline.py::TestFullPipeline::test_upload_document PASSED
# ... 17 tests total

# Run specific test
pytest tests/integration/test_full_pipeline.py::TestFullPipeline::test_full_workflow -v

# Run with coverage
pytest tests/integration/ --cov=app --cov-report=html
```

---

## 📊 Validation Results

After running all tests, you should have:

### ✅ Passing Criteria

- [x] **Environment**: All API keys configured
- [x] **Database**: PostgreSQL connected, tables created
- [x] **Services**: OpenAI, Pinecone, Redis all working
- [x] **Core Modules**: Document processor, structure extractor, chunker working
- [x] **API**: All endpoints responding correctly
- [x] **Tests**: Integration tests passing

### ⚠️ Common Warnings (Non-Critical)

- Redis not running → System works without cache (slower)
- Test PDF not found → Generate with `create_test_pdfs.py`
- Baseline corpus empty → Run data collection scripts

### ❌ Critical Issues (Must Fix)

- API keys not set → Update `.env` file
- Database connection failed → Start PostgreSQL
- OpenAI API errors → Check API key and quota
- Pinecone connection failed → Check API key and index name
- Import errors → Reinstall dependencies

---

## 🎯 Final Validation Checklist

Before moving to frontend, confirm:

- [ ] `python scripts/validate_system.py` passes with 0 errors
- [ ] API server starts without errors
- [ ] Can signup/login via API
- [ ] Can upload document via API
- [ ] Can query document via API
- [ ] Integration tests pass (pytest)
- [ ] Database migrations complete
- [ ] All required services running

---

## 🐛 Troubleshooting

### Issue: "Module not found"

**Solution**:
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "Database connection failed"

**Solution**:
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Check it's running
docker-compose ps

# Run migrations
alembic upgrade head
```

### Issue: "OpenAI API key invalid"

**Solution**:
```bash
# Check your .env file
cat .env | grep OPENAI_API_KEY

# Verify on OpenAI dashboard
open https://platform.openai.com/api-keys
```

### Issue: "Pinecone index not found"

**Solution**:
```bash
# Log into Pinecone and create index
open https://app.pinecone.io/

# Index settings:
# Name: tc-analysis
# Dimensions: 1536
# Metric: cosine
# Environment: us-east-1 (or your region)
```

### Issue: "Redis connection failed"

**Solution**:
```bash
# Start Redis
docker-compose up -d redis

# Or skip Redis (system will work without cache)
# Just ignore the warning
```

---

## 📈 Performance Benchmarks

After validation, expected performance:

| Operation | Target | Acceptable |
|-----------|--------|----------|
| **Document Upload** | < 30s | < 60s |
| **Q&A Query** | < 2s | < 5s |
| **Anomaly Detection** | < 45s | < 90s |
| **Health Check** | < 100ms | < 500ms |

---

## 🎉 Success!

If all validations pass, you have:

✅ **Fully operational backend**
✅ **All services integrated**
✅ **API endpoints working**
✅ **Tests passing**
✅ **Ready for frontend development!**

---

## 🚀 Next: Frontend Development

With backend validated, proceed to:

1. **Week 8-9**: React + TypeScript frontend
2. **Week 10**: Deployment and final testing

---

**Validation Report**: Check `backend/validation_report.json` for detailed results
**Log Files**: Check `backend/system_validation.log` for full logs
