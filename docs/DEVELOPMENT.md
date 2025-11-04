# Development Setup Guide

## Prerequisites

Before starting development, ensure you have:

- **Python 3.10+** (Check: `python --version`)
- **Node.js 18+** (Check: `node --version`)
- **Docker & Docker Compose** (Check: `docker --version`)
- **Git** (Check: `git --version`)
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **Pinecone API Key** ([Sign up here](https://www.pinecone.io/))

## Initial Setup

### 1. Clone Repository

```bash
cd ~/Desktop
cd "Project T&C"
git init
git add .
git commit -m "Initial commit"
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Create .env file
cp .env.example .env
```

Edit `.env` file with your credentials:

```env
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX_USER=tc-analysis-user
PINECONE_INDEX_BASELINE=tc-analysis-baseline

# Database
DATABASE_URL=postgresql://tcuser:tcpassword@localhost:5432/tcanalysis

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=development
DEBUG=True
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
```

Edit `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_APP_TITLE=T&C Analysis System
```

### 4. Start Database Services

```bash
# From project root
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see:
- PostgreSQL running on port 5432
- Redis running on port 6379

### 5. Initialize Database

```bash
cd backend

# Run migrations
alembic upgrade head

# Verify database connection
python -c "from app.services.database import engine; print('Database connected!' if engine else 'Connection failed')"
```

### 6. Set Up Pinecone Indexes

```bash
# From backend directory with venv activated
python

# In Python shell:
from app.services.pinecone_service import PineconeService
pinecone_service = PineconeService()
pinecone_service.create_indexes()
print("Pinecone indexes created successfully!")
```

## Running the Application

### Start Backend

```bash
cd backend
source venv/bin/activate  # Activate venv
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at:
- App: http://localhost:5173

## Development Workflow

### Phase 1: Foundation (Weeks 1-3)

**Week 1: Core Setup**

```bash
# 1. Create project structure
mkdir -p backend/app/{api,core,models,schemas,services,prompts,utils}
mkdir -p backend/tests
mkdir -p frontend/src/{components,pages,hooks,services,types}

# 2. Implement document processor
touch backend/app/core/document_processor.py
# Start coding: PDF extraction, text processing

# 3. Test with sample PDF
# Place test PDF in data/test_samples/
python backend/app/core/document_processor.py data/test_samples/sample_tc.pdf
```

**Week 2: Structure Extraction**

```bash
# 1. Implement structure extractor
touch backend/app/core/structure_extractor.py

# 2. Test extraction
python -m pytest backend/tests/test_structure_extractor.py -v

# 3. Implement legal chunker
touch backend/app/core/legal_chunker.py
```

**Week 3: Basic RAG**

```bash
# 1. Set up OpenAI service
touch backend/app/services/openai_service.py

# 2. Set up Pinecone service
touch backend/app/services/pinecone_service.py

# 3. Create API endpoints
touch backend/app/api/v1/upload.py
touch backend/app/api/v1/query.py

# 4. Test end-to-end
# Upload document → Ask question → Verify answer
```

### Phase 2: Specialization (Weeks 4-5)

**Week 4: Metadata Extraction**

```bash
# 1. Implement metadata extractor
touch backend/app/core/metadata_extractor.py

# 2. Create classification prompts
touch backend/app/prompts/classification.py

# 3. Test metadata extraction
python -m pytest backend/tests/test_metadata_extractor.py -v
```

**Week 5: Enhanced Q&A**

```bash
# 1. Create Q&A prompts
touch backend/app/prompts/qa_prompts.py

# 2. Enhance query endpoint with metadata
# Edit backend/app/api/v1/query.py

# 3. Test answer quality
# Ask 20 test questions, verify accuracy
```

### Phase 3: Anomaly Detection (Weeks 6-7)

**Week 6: Baseline Corpus**

```bash
# 1. Collect 100+ T&C PDFs
# Save in data/baseline_corpus/{streaming,saas,ecommerce,social_media}/

# 2. Create baseline corpus script
touch scripts/build_baseline_corpus.py

# 3. Process baseline corpus
python scripts/build_baseline_corpus.py

# 4. Verify baseline indexed
# Check Pinecone dashboard for "baseline" namespace
```

**Week 7: Anomaly Detection**

```bash
# 1. Implement anomaly detector
touch backend/app/core/anomaly_detector.py
touch backend/app/core/prevalence_calculator.py
touch backend/app/core/risk_assessor.py

# 2. Create risk assessment prompts
touch backend/app/prompts/risk_assessment.py

# 3. Create anomaly endpoint
touch backend/app/api/v1/anomalies.py

# 4. Test detection
python -m pytest backend/tests/test_anomaly_detector.py -v
```

### Phase 4: Frontend & Deployment (Weeks 8-10)

**Week 8: Backend Deployment**

```bash
# 1. Create Dockerfile
touch backend/Dockerfile

# 2. Test Docker build
docker build -t tc-analysis-backend backend/

# 3. Deploy to Railway/Render
# Follow DEPLOYMENT.md guide

# 4. Implement caching
touch backend/app/services/cache_service.py
```

**Week 9: Frontend Development**

```bash
# 1. Create React components
cd frontend/src/components

mkdir common upload analysis qa
touch common/{Header,Footer,LoadingSpinner}.tsx
touch upload/{UploadArea,UploadProgress}.tsx
touch analysis/{AnomalyReport,RiskScore}.tsx
touch qa/ChatInterface.tsx

# 2. Create pages
cd ../pages
touch Home.tsx Upload.tsx Analysis.tsx

# 3. Implement API integration
cd ../services
touch api.ts documentService.ts queryService.ts

# 4. Test locally
npm run dev
```

**Week 10: Integration & Polish**

```bash
# 1. Deploy frontend to Netlify
npm run build
# Upload dist/ to Netlify

# 2. End-to-end testing
# Test all user flows

# 3. Performance optimization
# Check Lighthouse scores

# 4. Write documentation
# Update README, API docs
```

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_document_processor.py -v

# Run tests matching pattern
pytest -k "test_extract" -v

# View coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

### Integration Tests

```bash
# Start all services
docker-compose up -d
cd backend && uvicorn app.main:app &
cd frontend && npm run dev &

# Run integration tests
pytest tests/integration/ -v
```

## Code Quality

### Backend

```bash
# Format code
black backend/app

# Lint code
ruff check backend/app

# Type checking
mypy backend/app

# Run all checks
black backend/app && ruff check backend/app && mypy backend/app
```

### Frontend

```bash
# Lint
npm run lint

# Format
npm run format

# Type check
npm run type-check
```

## Database Management

### Create Migration

```bash
cd backend

# Auto-generate migration
alembic revision --autogenerate -m "Add new table"

# Edit migration file in alembic/versions/

# Apply migration
alembic upgrade head
```

### Rollback Migration

```bash
# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Rollback all
alembic downgrade base
```

### View Migration History

```bash
# Current version
alembic current

# Migration history
alembic history

# Show SQL for migration
alembic upgrade head --sql
```

## Debugging

### Backend Debugging

Add breakpoint in code:
```python
import ipdb; ipdb.set_trace()
```

Or use VS Code debugger:

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload"
      ],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

### Frontend Debugging

Use React DevTools browser extension and:
```typescript
console.log('Debug:', data);
debugger;
```

### Pinecone Debugging

```python
# Check index stats
from app.services.pinecone_service import PineconeService
service = PineconeService()
stats = service.index.describe_index_stats()
print(stats)

# Query directly
results = service.index.query(
    vector=[0.1] * 1536,
    top_k=5,
    namespace="user_tcs"
)
print(results)
```

## Common Issues

### "Module not found" Error
```bash
# Ensure you're in the correct directory
cd backend
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database Connection Error
```bash
# Verify PostgreSQL is running
docker-compose ps

# Check connection string in .env
echo $DATABASE_URL

# Test connection
psql postgresql://tcuser:tcpassword@localhost:5432/tcanalysis
```

### Pinecone Connection Error
```bash
# Verify API key
echo $PINECONE_API_KEY

# Check index exists
# Login to Pinecone dashboard and verify indexes
```

### Frontend Build Error
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf .vite
npm run dev
```

## Development Tools Recommendations

### VS Code Extensions
- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- Docker
- GitLens

### Browser Extensions
- React Developer Tools
- Redux DevTools (if using Redux)
- JSON Viewer

### CLI Tools
- `httpie` - Better curl: `pip install httpie`
- `jq` - JSON processor: `brew install jq`
- `pgcli` - Better psql: `pip install pgcli`

## Next Steps

After completing setup:

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand system design
2. Review [API.md](API.md) for API documentation
3. Start with Phase 1 implementation (Week 1)
4. Join development chat/Discord for questions

## Getting Help

- Documentation: Check docs/ folder
- Issues: Create GitHub issue
- Questions: Email or Discord
- API Docs: http://localhost:8000/api/v1/docs

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LangChain Documentation](https://python.langchain.com/)
