# T&C Analysis System - Backend

FastAPI-based backend for the AI-Powered Terms & Conditions Analysis System.

## Features

- 📄 **PDF Processing**: Extract text from T&C PDFs using pdfplumber/PyPDF2
- 🔍 **Structure Extraction**: Parse sections and clauses with regex patterns
- 🧩 **Legal Chunking**: Create semantic chunks for embeddings
- 🔐 **Authentication**: JWT-based user authentication
- 📊 **Database**: PostgreSQL with SQLAlchemy ORM
- ⚡ **Caching**: Redis for performance optimization
- 🧪 **Testing**: Pytest with async support

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: python-jose, passlib
- **PDF Processing**: PyPDF2, pdfplumber
- **Testing**: pytest, pytest-asyncio

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker & Docker Compose
- OpenAI API key
- Pinecone API key

### 2. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required:
# - OPENAI_API_KEY
# - PINECONE_API_KEY
# - SECRET_KEY (generate with: openssl rand -hex 32)
```

### 4. Start Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 5. Database Setup

```bash
# Run migrations
alembic upgrade head

# Verify database connection
python -c "from app.db.session import engine; print('✓ Database connected')"
```

### 6. Run Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the shortcut
python -m app.main
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/                   # API endpoints (v1)
│   ├── core/                  # Core business logic
│   │   ├── config.py          # Settings management
│   │   ├── document_processor.py
│   │   ├── structure_extractor.py
│   │   └── legal_chunker.py
│   ├── db/                    # Database configuration
│   │   ├── base.py
│   │   └── session.py
│   ├── models/                # SQLAlchemy models
│   │   ├── user.py
│   │   ├── document.py
│   │   ├── clause.py
│   │   └── anomaly.py
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # External service integrations
│   ├── utils/                 # Utility functions
│   └── main.py                # FastAPI app entry point
├── alembic/                   # Database migrations
├── tests/                     # Test suite
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── docker-compose.yml         # Docker services
├── alembic.ini               # Alembic configuration
└── README.md                 # This file
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_document_processor.py -v

# View coverage report
open htmlcov/index.html
```

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

## Development

### Code Quality

```bash
# Format code with black
black app/

# Lint with ruff
ruff check app/

# Type checking with mypy
mypy app/

# Run all quality checks
black app/ && ruff check app/ && mypy app/
```

### Adding New Features

1. **New Database Model**: Add to `app/models/`, create migration with Alembic
2. **New API Endpoint**: Add to `app/api/v1/`, create schema in `app/schemas/`
3. **New Business Logic**: Add to `app/core/`, write tests in `tests/`

## Environment Variables

See `.env.example` for all available configuration options.

### Required Variables

- `OPENAI_API_KEY`: OpenAI API key
- `PINECONE_API_KEY`: Pinecone API key
- `SECRET_KEY`: JWT secret key
- `DATABASE_URL`: PostgreSQL connection string

### Optional Variables

- `DEBUG`: Enable debug mode (default: False)
- `ENVIRONMENT`: development/production (default: development)
- `MAX_FILE_SIZE_MB`: Max upload size (default: 10)

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## Troubleshooting

### Database Connection Error

```bash
# Verify PostgreSQL is running
docker-compose ps

# Check connection string
echo $DATABASE_URL

# Test connection
psql postgresql://tcuser:tcpassword@localhost:5432/tcanalysis
```

### Module Not Found Error

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

## Week 2: Service Layer Integration ✅

Week 2 adds all external service integrations and completes the foundation for the full processing pipeline.

### What's New in Week 2

1. **OpenAI Service** ([app/services/openai_service.py](app/services/openai_service.py))
   - Embedding generation with caching
   - GPT-4/GPT-3.5-turbo completions
   - Batch operations for efficiency
   - Structured JSON responses
   - Retry logic with exponential backoff

2. **Pinecone Service** ([app/services/pinecone_service.py](app/services/pinecone_service.py))
   - Vector database operations
   - Dual-namespace strategy (`user_tcs` + `baseline`)
   - Batch vector upsert
   - Semantic search/retrieval
   - Index statistics

3. **Redis Cache Service** ([app/services/cache_service.py](app/services/cache_service.py))
   - Embedding caching (24h TTL)
   - Query result caching
   - JSON serialization
   - Cache statistics
   - Pattern-based deletion

4. **Metadata Extractor** ([app/core/metadata_extractor.py](app/core/metadata_extractor.py))
   - GPT-4 powered metadata extraction
   - Company name, jurisdiction, dates
   - Clause type classification
   - Structured output validation

5. **LLM Prompts** ([app/prompts/](app/prompts/))
   - Metadata extraction prompts
   - Q&A system prompts
   - Anomaly detection prompts
   - Consistent prompt templates

6. **Service Lifecycle** ([app/main.py](app/main.py))
   - Service initialization in lifespan
   - Graceful startup/shutdown
   - Error handling and fallbacks
   - Health check updates

7. **Dependency Injection** ([app/api/deps.py](app/api/deps.py))
   - Service dependency helpers
   - Type-safe service retrieval
   - Request-scoped access

### Testing Week 2

Run the comprehensive integration test:

```bash
# Test all services with a sample PDF
python backend/test_week2_integration.py data/test_samples/simple_tos.pdf
```

This tests:
- ✅ Redis cache operations
- ✅ OpenAI embeddings (single + batch)
- ✅ OpenAI completions (text + JSON)
- ✅ Pinecone index initialization
- ✅ Vector upsert and retrieval
- ✅ Metadata extraction
- ✅ Complete document processing pipeline

### Week 2 Architecture

```
Document Upload
    ↓
Extract Text (Week 1: DocumentProcessor)
    ↓
Parse Structure (Week 1: StructureExtractor)
    ↓
Create Chunks (Week 1: LegalChunker)
    ↓
Generate Embeddings (Week 2: OpenAI Service) ← Cache with Redis
    ↓
Extract Metadata (Week 2: Metadata Extractor + GPT-4)
    ↓
Store Vectors (Week 2: Pinecone Service)
    ↓
Save to Database (Week 1: PostgreSQL models)
    ↓
[Week 3: Anomaly Detection]
```

### Service Configuration

All services are configured via environment variables in `.env`:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL_GPT4=gpt-4
OPENAI_MODEL_GPT35=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT=60

# Pinecone Configuration
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east-1
PINECONE_CLOUD=aws
PINECONE_INDEX_NAME=tc-analysis
PINECONE_USER_NAMESPACE=user_tcs
PINECONE_BASELINE_NAMESPACE=baseline

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
REDIS_MAX_CONNECTIONS=10
```

### Using Services in Endpoints (Week 3 Preview)

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_openai_service, get_pinecone_service
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService

router = APIRouter()

@router.post("/process")
async def process_document(
    openai: OpenAIService = Depends(get_openai_service),
    pinecone: PineconeService = Depends(get_pinecone_service),
):
    # Services are automatically injected and ready to use
    embedding = await openai.create_embedding("test text")
    await pinecone.upsert_chunks(chunks, namespace="user_tcs", document_id="123")
    return {"status": "success"}
```

### Week 2 File Manifest

New files added:

```
backend/
├── app/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── openai_service.py       (242 lines)
│   │   ├── pinecone_service.py     (285 lines)
│   │   └── cache_service.py        (230 lines)
│   ├── core/
│   │   └── metadata_extractor.py   (172 lines)
│   └── prompts/
│       ├── __init__.py
│       ├── metadata_prompts.py     (60 lines)
│       ├── qa_prompts.py           (52 lines)
│       └── anomaly_prompts.py      (82 lines)
└── test_week2_integration.py       (350 lines)

Total: ~1,473 lines of new code
```

### Cost Estimates (Week 2)

Per document processing:
- **Embeddings**: ~$0.001 per document (text-embedding-3-small)
- **Metadata Extraction**: ~$0.01 per document (GPT-4)
- **Pinecone Storage**: Included in free tier (100K vectors)
- **Redis**: Free (self-hosted)

**Total**: ~$0.011 per document

### Performance Benchmarks (Week 2)

Expected processing times for typical T&C document (10 pages, 50 clauses):

| Operation | Target | Notes |
|-----------|--------|-------|
| PDF Extraction | < 2s | Week 1 |
| Structure Parsing | < 1s | Week 1 |
| Chunking | < 0.5s | Week 1 |
| Embeddings (50 chunks) | ~5s | OpenAI API |
| Metadata Extraction | ~3s | GPT-4 |
| Pinecone Upsert | ~1s | Batch operation |
| **Total Pipeline** | **~12s** | Without cache |

With caching:
- Repeated embeddings: ~0.1s (from Redis)
- 10x speedup on re-processing

## Next Steps

1. ✅ **Completed**: Week 1 - Core document processing pipeline
2. ✅ **Completed**: Week 2 - Service layer integration
3. 🔄 **Next**: Week 3 - API endpoints (upload, query, anomaly detection)
3. ⏳ **Upcoming**: Week 3 - API endpoints and authentication

See `claude.md` in the project root for the complete implementation guide.

## License

MIT License - See LICENSE file for details
