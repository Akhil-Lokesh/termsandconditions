# AI-Powered Terms & Conditions Analysis System - Claude Code Guide

## 🎯 Project Mission
Build an intelligent RAG system that analyzes T&C documents, answers questions with citations, and detects risky clauses by comparing against 100+ baseline T&Cs. **Timeline: 10 weeks to MVP.**

---

## 📁 Complete Project File Structure

```
Project-TC/
│
├── backend/                           # FastAPI Backend Application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point (CORS, routers, lifespan)
│   │   │
│   │   ├── core/                      # Core Business Logic
│   │   │   ├── __init__.py
│   │   │   ├── config.py              # Settings management (Pydantic BaseSettings)
│   │   │   ├── document_processor.py  # PDF text extraction (PyPDF2, pdfplumber)
│   │   │   ├── structure_extractor.py # Parse sections/clauses with regex
│   │   │   ├── legal_chunker.py       # Semantic chunking for embeddings
│   │   │   ├── metadata_extractor.py  # GPT-4 metadata extraction
│   │   │   ├── anomaly_detector.py    # Main anomaly detection orchestrator
│   │   │   ├── prevalence_calculator.py # Calculate clause prevalence in baseline
│   │   │   └── risk_assessor.py       # GPT-4 risk assessment
│   │   │
│   │   ├── services/                  # External Service Integrations
│   │   │   ├── __init__.py
│   │   │   ├── openai_service.py      # OpenAI API wrapper (embeddings, completions)
│   │   │   ├── pinecone_service.py    # Pinecone vector DB operations
│   │   │   └── cache_service.py       # Redis caching layer
│   │   │
│   │   ├── api/                       # API Layer
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # Dependency injection helpers
│   │   │   └── v1/                    # API Version 1
│   │   │       ├── __init__.py
│   │   │       ├── auth.py            # Authentication endpoints (login, signup)
│   │   │       ├── upload.py          # Document upload & processing
│   │   │       ├── documents.py       # Document CRUD operations
│   │   │       ├── query.py           # Q&A endpoint
│   │   │       ├── anomalies.py       # Anomaly detection & retrieval
│   │   │       └── compare.py         # Document comparison
│   │   │
│   │   ├── models/                    # Database Models (SQLAlchemy ORM)
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User model
│   │   │   ├── document.py            # Document model
│   │   │   ├── clause.py              # Clause model
│   │   │   └── anomaly.py             # Anomaly model
│   │   │
│   │   ├── schemas/                   # Pydantic Schemas (Request/Response)
│   │   │   ├── __init__.py
│   │   │   ├── user.py                # User schemas
│   │   │   ├── document.py            # Document schemas
│   │   │   ├── query.py               # Query request/response schemas
│   │   │   └── anomaly.py             # Anomaly schemas
│   │   │
│   │   ├── prompts/                   # LLM Prompt Templates
│   │   │   ├── __init__.py
│   │   │   ├── qa_prompts.py          # Q&A system prompts
│   │   │   ├── metadata_prompts.py    # Metadata extraction prompts
│   │   │   └── anomaly_prompts.py     # Risk assessment prompts
│   │   │
│   │   ├── utils/                     # Utility Functions
│   │   │   ├── __init__.py
│   │   │   ├── exceptions.py          # Custom exceptions
│   │   │   ├── security.py            # Password hashing, JWT tokens
│   │   │   └── validators.py          # Input validators
│   │   │
│   │   └── db/                        # Database Configuration
│   │       ├── __init__.py
│   │       ├── base.py                # SQLAlchemy base
│   │       └── session.py             # Database session management
│   │
│   ├── tests/                         # Backend Tests
│   │   ├── __init__.py
│   │   ├── conftest.py                # Pytest fixtures
│   │   ├── test_document_processor.py
│   │   ├── test_structure_extractor.py
│   │   ├── test_anomaly_detector.py
│   │   ├── test_api/
│   │   │   ├── test_upload.py
│   │   │   ├── test_query.py
│   │   │   └── test_anomalies.py
│   │   └── test_services/
│   │       ├── test_openai_service.py
│   │       └── test_pinecone_service.py
│   │
│   ├── alembic/                       # Database Migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   ├── alembic.ini
│   │   └── versions/
│   │       └── (migration files)
│   │
│   ├── requirements.txt               # Python dependencies
│   ├── requirements-dev.txt           # Development dependencies
│   ├── .env.example                   # Environment variables template
│   ├── .env                           # Environment variables (gitignored)
│   ├── docker-compose.yml             # Docker services (PostgreSQL, Redis)
│   ├── Dockerfile                     # Backend container
│   └── README.md                      # Backend documentation
│
├── frontend/                          # React Frontend Application
│   ├── public/
│   │   ├── index.html
│   │   └── vite.svg
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui Base Components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── textarea.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── badge.tsx
│   │   │   │   ├── tabs.tsx
│   │   │   │   ├── alert.tsx
│   │   │   │   ├── skeleton.tsx
│   │   │   │   └── toast.tsx
│   │   │   │
│   │   │   ├── layout/                # Layout Components
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   │   └── Layout.tsx
│   │   │   │
│   │   │   ├── document/              # Document-Related Components
│   │   │   │   ├── UploadDocument.tsx     # Drag-drop upload interface
│   │   │   │   ├── DocumentList.tsx       # List user's documents
│   │   │   │   ├── DocumentCard.tsx       # Document summary card
│   │   │   │   ├── DocumentViewer.tsx     # Full document view
│   │   │   │   └── DocumentStats.tsx      # Document statistics
│   │   │   │
│   │   │   ├── analysis/              # Analysis Components
│   │   │   │   ├── AnalysisResults.tsx    # Overall analysis summary
│   │   │   │   ├── MetadataPanel.tsx      # Company, jurisdiction display
│   │   │   │   ├── ClauseBreakdown.tsx    # Section/clause statistics
│   │   │   │   ├── RiskScore.tsx          # Overall risk visualization
│   │   │   │   └── ProcessingStatus.tsx   # Upload processing status
│   │   │   │
│   │   │   ├── anomaly/               # Anomaly Detection Components
│   │   │   │   ├── AnomalyList.tsx        # List of detected anomalies
│   │   │   │   ├── AnomalyCard.tsx        # Individual anomaly display
│   │   │   │   ├── SeverityBadge.tsx      # Color-coded severity badge
│   │   │   │   ├── AnomalyDetails.tsx     # Detailed anomaly view
│   │   │   │   └── AnomalyFilters.tsx     # Filter by severity/section
│   │   │   │
│   │   │   ├── query/                 # Q&A Components
│   │   │   │   ├── QueryInterface.tsx     # Q&A chat interface
│   │   │   │   ├── QueryInput.tsx         # Question input box
│   │   │   │   ├── QueryResponse.tsx      # Answer with citations
│   │   │   │   ├── CitationCard.tsx       # Citation details
│   │   │   │   └── QueryHistory.tsx       # Previous questions/answers
│   │   │   │
│   │   │   └── auth/                  # Authentication Components
│   │   │       ├── LoginForm.tsx
│   │   │       ├── SignupForm.tsx
│   │   │       ├── ProtectedRoute.tsx
│   │   │       └── AuthLayout.tsx
│   │   │
│   │   ├── pages/                     # Page Components
│   │   │   ├── HomePage.tsx           # Landing page
│   │   │   ├── DashboardPage.tsx      # User dashboard
│   │   │   ├── DocumentPage.tsx       # Single document view
│   │   │   ├── UploadPage.tsx         # Upload interface
│   │   │   ├── LoginPage.tsx          # Login page
│   │   │   ├── SignupPage.tsx         # Signup page
│   │   │   └── NotFoundPage.tsx       # 404 page
│   │   │
│   │   ├── services/                  # API & External Services
│   │   │   ├── api.ts                 # Axios client & API calls
│   │   │   ├── auth.ts                # Auth service
│   │   │   └── websocket.ts           # Real-time updates (optional)
│   │   │
│   │   ├── hooks/                     # Custom React Hooks
│   │   │   ├── useDocuments.ts        # Document CRUD operations
│   │   │   ├── useQuery.ts            # Q&A queries
│   │   │   ├── useAnomalies.ts        # Anomaly data fetching
│   │   │   ├── useAuth.ts             # Auth state management
│   │   │   └── useDebounce.ts         # Debounce utility hook
│   │   │
│   │   ├── types/                     # TypeScript Type Definitions
│   │   │   ├── index.ts               # Re-exports all types
│   │   │   ├── document.ts            # Document types
│   │   │   ├── anomaly.ts             # Anomaly types
│   │   │   ├── query.ts               # Query types
│   │   │   └── user.ts                # User types
│   │   │
│   │   ├── utils/                     # Utility Functions
│   │   │   ├── formatters.ts          # Date, number formatters
│   │   │   ├── validators.ts          # Form validation helpers
│   │   │   ├── constants.ts           # App constants
│   │   │   └── cn.ts                  # Tailwind class merger
│   │   │
│   │   ├── styles/
│   │   │   └── globals.css            # Global styles + Tailwind imports
│   │   │
│   │   ├── App.tsx                    # Root app component
│   │   ├── main.tsx                   # Entry point
│   │   └── router.tsx                 # React Router configuration
│   │
│   ├── .env.example                   # Frontend environment variables
│   ├── .env.local                     # Local environment (gitignored)
│   ├── .eslintrc.cjs                  # ESLint configuration
│   ├── index.html                     # HTML template
│   ├── package.json                   # Node dependencies
│   ├── postcss.config.js              # PostCSS configuration
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   ├── tsconfig.json                  # TypeScript configuration
│   ├── tsconfig.node.json             # TypeScript Node config
│   ├── vite.config.ts                 # Vite configuration
│   └── README.md                      # Frontend documentation
│
├── data/                              # Data Storage
│   ├── baseline_corpus/               # 100+ Standard T&Cs for Comparison
│   │   ├── tech/                      # Technology companies (20+ files)
│   │   │   ├── google_tos.pdf
│   │   │   ├── microsoft_tos.pdf
│   │   │   ├── apple_tos.pdf
│   │   │   ├── facebook_tos.pdf
│   │   │   ├── amazon_tos.pdf
│   │   │   └── ... (15+ more)
│   │   │
│   │   ├── ecommerce/                 # E-commerce platforms (20+ files)
│   │   │   ├── amazon_marketplace_tos.pdf
│   │   │   ├── ebay_tos.pdf
│   │   │   ├── etsy_tos.pdf
│   │   │   └── ... (17+ more)
│   │   │
│   │   ├── saas/                      # SaaS companies (20+ files)
│   │   │   ├── salesforce_tos.pdf
│   │   │   ├── slack_tos.pdf
│   │   │   ├── notion_tos.pdf
│   │   │   └── ... (17+ more)
│   │   │
│   │   ├── finance/                   # Financial services (20+ files)
│   │   │   ├── paypal_tos.pdf
│   │   │   ├── stripe_tos.pdf
│   │   │   ├── square_tos.pdf
│   │   │   └── ... (17+ more)
│   │   │
│   │   ├── general/                   # General services (20+ files)
│   │   │   ├── uber_tos.pdf
│   │   │   ├── airbnb_tos.pdf
│   │   │   ├── doordash_tos.pdf
│   │   │   └── ... (17+ more)
│   │   │
│   │   └── metadata.json              # Corpus metadata index
│   │
│   └── test_samples/                  # Test Documents for Development
│       ├── simple_tos.pdf             # Simple 4-section T&C
│       ├── complex_tos.pdf            # Complex T&C with risky clauses
│       └── edge_cases/                # Edge case documents
│           ├── scanned_doc.pdf        # Scanned document (OCR test)
│           ├── multi_language.pdf     # Multi-language document
│           └── corrupted.pdf          # Corrupted/malformed PDF
│
├── scripts/                           # Utility Scripts
│   ├── README.md                      # Scripts documentation
│   ├── collect_baseline_corpus.py     # Collect 100+ T&C documents
│   ├── index_baseline_corpus.py       # Index baseline corpus to Pinecone
│   ├── create_test_samples.py         # Generate test PDF samples
│   ├── validate_corpus.py             # Validate baseline corpus quality
│   ├── analyze_corpus_stats.py        # Generate corpus statistics
│   ├── backup_database.py             # Database backup utility
│   ├── migrate_pinecone_namespace.py  # Migrate vectors between namespaces
│   ├── benchmark_performance.py       # Performance benchmarking
│   ├── cleanup_temp_files.py          # Clean temporary uploads
│   └── export_anomalies.py            # Export anomalies to CSV
│
├── docs/                              # Documentation
│   ├── ARCHITECTURE.md                # System architecture & design
│   ├── API.md                         # API endpoint documentation
│   ├── DEVELOPMENT.md                 # Development setup guide
│   ├── DEPLOYMENT.md                  # Deployment instructions
│   ├── DATA_COLLECTION.md             # Baseline corpus collection guide
│   ├── TESTING.md                     # Testing strategy & guidelines
│   ├── TROUBLESHOOTING.md             # Common issues & solutions
│   ├── CONTRIBUTING.md                # Contribution guidelines
│   └── CHANGELOG.md                   # Version history
│
├── .github/                           # GitHub Configuration
│   ├── workflows/
│   │   ├── backend-tests.yml          # Backend CI/CD
│   │   ├── frontend-tests.yml         # Frontend CI/CD
│   │   └── deploy.yml                 # Deployment workflow
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
│
├── .gitignore                         # Git ignore rules
├── .dockerignore                      # Docker ignore rules
├── claude.md                          # This file - Claude Code guide
├── README.md                          # Project README
└── LICENSE                            # Project license

```

---

## 🗺️ File Navigation Quick Reference

### Backend Core Files (Start Here)
```
backend/app/main.py                    → Application entry point
backend/app/core/config.py             → Settings & environment variables
backend/app/core/document_processor.py → PDF extraction
backend/app/core/structure_extractor.py → Section/clause parsing
backend/app/core/anomaly_detector.py   → Main anomaly detection logic
backend/app/services/openai_service.py → OpenAI integration
backend/app/services/pinecone_service.py → Vector database
```

### Frontend Core Files (Start Here)
```
frontend/src/main.tsx                  → Entry point
frontend/src/router.tsx                → Route configuration
frontend/src/services/api.ts           → API client
frontend/src/components/document/UploadDocument.tsx → Upload UI
frontend/src/components/query/QueryInterface.tsx    → Q&A UI
frontend/src/components/anomaly/AnomalyList.tsx    → Anomaly display
```

### Configuration Files
```
backend/.env                           → Backend environment variables
backend/requirements.txt               → Python dependencies
backend/docker-compose.yml             → Docker services setup
frontend/.env.local                    → Frontend environment variables
frontend/package.json                  → Node dependencies
frontend/vite.config.ts                → Vite configuration
```

### Data Files
```
data/baseline_corpus/                  → 100+ standard T&Cs (organized by category)
data/baseline_corpus/metadata.json     → Corpus index
data/test_samples/                     → Test PDFs for development
```

### Utility Scripts
```
scripts/collect_baseline_corpus.py     → Scrape T&Cs from web
scripts/index_baseline_corpus.py       → Upload corpus to Pinecone
scripts/create_test_samples.py         → Generate test PDFs
scripts/validate_corpus.py             → Check corpus quality
scripts/benchmark_performance.py       → Performance testing
```

### Documentation
```
docs/ARCHITECTURE.md                   → System design overview
docs/API.md                            → API reference
docs/DEVELOPMENT.md                    → Setup instructions
docs/TROUBLESHOOTING.md                → Common issues & fixes
docs/DATA_COLLECTION.md                → Corpus collection guide
```

---

## 🎯 File Creation Priority (Week by Week)

### Week 1: Core Backend Setup
```
Priority 1 (Critical):
✓ backend/app/main.py
✓ backend/app/core/config.py
✓ backend/requirements.txt
✓ backend/.env
✓ backend/docker-compose.yml

Priority 2 (High):
✓ backend/app/core/document_processor.py
✓ backend/app/core/structure_extractor.py
✓ backend/app/db/base.py
✓ backend/app/db/session.py
✓ backend/app/models/user.py
✓ backend/app/models/document.py
```

### Week 2: Services & Processing
```
✓ backend/app/services/openai_service.py
✓ backend/app/services/pinecone_service.py
✓ backend/app/services/cache_service.py
✓ backend/app/core/legal_chunker.py
✓ backend/app/core/metadata_extractor.py
✓ backend/app/prompts/metadata_prompts.py
```

### Week 3: API Endpoints
```
✓ backend/app/api/deps.py
✓ backend/app/api/v1/auth.py
✓ backend/app/api/v1/upload.py
✓ backend/app/api/v1/query.py
✓ backend/app/schemas/document.py
✓ backend/app/schemas/query.py
✓ backend/app/prompts/qa_prompts.py
```

### Week 4-5: Anomaly Detection
```
✓ backend/app/core/anomaly_detector.py
✓ backend/app/core/prevalence_calculator.py
✓ backend/app/core/risk_assessor.py
✓ backend/app/api/v1/anomalies.py
✓ backend/app/models/anomaly.py
✓ backend/app/prompts/anomaly_prompts.py
```

### Week 6-7: Data Collection & Testing
```
✓ scripts/collect_baseline_corpus.py
✓ scripts/index_baseline_corpus.py
✓ scripts/validate_corpus.py
✓ data/baseline_corpus/ (collect 100+ PDFs)
✓ backend/tests/test_document_processor.py
✓ backend/tests/test_anomaly_detector.py
```

### Week 8-10: Frontend & Deployment
```
✓ frontend/src/services/api.ts
✓ frontend/src/router.tsx
✓ frontend/src/components/document/UploadDocument.tsx
✓ frontend/src/components/query/QueryInterface.tsx
✓ frontend/src/components/anomaly/AnomalyList.tsx
✓ frontend/src/pages/DashboardPage.tsx
✓ frontend/src/pages/DocumentPage.tsx
✓ docs/DEPLOYMENT.md
```

---

## 🔍 How to Find What You Need

### "I need to understand how X works"
- **PDF extraction** → `backend/app/core/document_processor.py`
- **Structure parsing** → `backend/app/core/structure_extractor.py`
- **Anomaly detection** → `backend/app/core/anomaly_detector.py`
- **Q&A system** → `backend/app/api/v1/query.py` + `backend/app/prompts/qa_prompts.py`
- **Vector search** → `backend/app/services/pinecone_service.py`

### "I need to configure X"
- **Backend settings** → `backend/app/core/config.py` + `backend/.env`
- **Frontend settings** → `frontend/vite.config.ts` + `frontend/.env.local`
- **Database** → `backend/docker-compose.yml`
- **API endpoints** → `backend/app/api/v1/`
- **Dependencies** → `backend/requirements.txt` or `frontend/package.json`

### "I need to add X feature"
- **New API endpoint** → Create in `backend/app/api/v1/`
- **New component** → Create in `frontend/src/components/`
- **New page** → Create in `frontend/src/pages/` + update `router.tsx`
- **New database model** → Create in `backend/app/models/` + run Alembic migration
- **New utility** → Create in `backend/app/utils/` or `frontend/src/utils/`

### "I need to fix X"
- **Bug in processing** → Check `backend/app/core/`
- **API error** → Check `backend/app/api/v1/`
- **UI issue** → Check `frontend/src/components/`
- **Data issue** → Check `data/` and scripts
- **Common problems** → Check `docs/TROUBLESHOOTING.md`

### "I need to deploy X"
- **Backend** → See `docs/DEPLOYMENT.md` + `backend/Dockerfile`
- **Frontend** → See `docs/DEPLOYMENT.md` + `frontend/vite.config.ts`
- **Database** → See `backend/docker-compose.yml` + `backend/alembic/`
- **Baseline corpus** → Run `scripts/index_baseline_corpus.py`

---



### When starting fresh or resuming:

1. **Check what exists first**:
   ```bash
   ls -la backend/app/
   ls -la backend/app/core/
   cat backend/app/main.py  # See if file exists
   ```

2. **Look for TODOs/stubs in existing files**:
   ```python
   # Many files have placeholder implementations
   # Example: backend/app/core/metadata_extractor.py might have:
   async def extract_metadata(text: str) -> dict:
       # TODO: Implement GPT-4 extraction
       return {}
   ```

3. **Check dependencies**:
   ```bash
   cat backend/requirements.txt  # Does it exist?
   cat backend/.env.example      # What config is needed?
   ```

---

## 📝 How to Implement Each Component

### 1. Core Configuration (`backend/app/core/config.py`)

**Purpose**: Centralized settings management using Pydantic.

**Implementation Pattern**:
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    APP_NAME: str = "T&C Analysis API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL_GPT4: str = "gpt-4"
    OPENAI_MODEL_GPT35: str = "gpt-3.5-turbo"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str
    PINECONE_USER_NAMESPACE: str = "user_tcs"
    PINECONE_BASELINE_NAMESPACE: str = "baseline"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600  # 1 hour
    
    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Decision Rules**:
- Use environment variables for secrets (never hardcode)
- Provide sensible defaults for non-sensitive configs
- Use `Optional[str]` only for truly optional settings

---

### 2. FastAPI Application (`backend/app/main.py`)

**Purpose**: Application entry point with CORS, middleware, routers.

**Implementation Pattern**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1 import auth, upload, query, anomalies, compare
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    app.state.pinecone = PineconeService()
    await app.state.pinecone.initialize()
    
    app.state.cache = CacheService()
    await app.state.cache.connect()
    
    yield
    
    # Shutdown: Cleanup
    await app.state.cache.disconnect()

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(anomalies.router, prefix="/api/v1/anomalies", tags=["anomalies"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["compare"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Decision Rules**:
- Use `lifespan` for async resource management (not `@app.on_event`)
- Initialize heavy services (Pinecone, Redis) in lifespan startup
- Store service instances in `app.state` for dependency injection
- Always include health check endpoint

---

### 3. Document Processor (`backend/app/core/document_processor.py`)

**Purpose**: Extract text from PDF files using PyPDF2 and pdfplumber.

**Implementation Pattern**:
```python
import PyPDF2
import pdfplumber
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Extracts text from PDF documents."""
    
    async def extract_text(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract text from PDF using fallback strategy.
        
        Returns:
            {
                "text": str,
                "page_count": int,
                "extraction_method": str,
                "metadata": dict
            }
        """
        try:
            # Try pdfplumber first (better formatting)
            text = await self._extract_with_pdfplumber(pdf_path)
            method = "pdfplumber"
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, falling back to PyPDF2")
            text = await self._extract_with_pypdf2(pdf_path)
            method = "pypdf2"
        
        # Get metadata
        metadata = await self._extract_pdf_metadata(pdf_path)
        
        return {
            "text": text,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": method,
            "metadata": metadata
        }
    
    async def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber (preserves layout)."""
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)
    
    async def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """Fallback: Extract text using PyPDF2."""
        text_parts = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
        return "\n\n".join(text_parts)
    
    async def _extract_pdf_metadata(self, pdf_path: str) -> dict:
        """Extract PDF metadata (author, creation date, etc.)."""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata = pdf_reader.metadata
            return {
                "page_count": len(pdf_reader.pages),
                "author": metadata.get("/Author", ""),
                "title": metadata.get("/Title", ""),
                "creation_date": metadata.get("/CreationDate", "")
            }
```

**Decision Rules**:
- Always use fallback strategy (pdfplumber → PyPDF2)
- Preserve page boundaries with `\n\n`
- Return structured dict with extraction metadata
- Log extraction method for debugging
- Handle corrupted PDFs gracefully

**When Stuck**:
- Test with multiple PDF samples (scanned vs text-based)
- Check if text is empty → might need OCR (future enhancement)
- Compare pdfplumber vs PyPDF2 output quality

---

### 4. Structure Extractor (`backend/app/core/structure_extractor.py`)

**Purpose**: Parse T&C document structure (sections, subsections, clauses).

**Implementation Pattern**:
```python
import re
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Clause:
    section: str
    subsection: str
    clause_number: str
    text: str
    level: int

class StructureExtractor:
    """Extracts hierarchical structure from T&C documents."""
    
    # Regex patterns for common T&C structures
    SECTION_PATTERNS = [
        r'^(\d+)\.\s+([A-Z][^\n]+)',           # "1. SECTION TITLE"
        r'^([A-Z]+)\.\s+([A-Z][^\n]+)',        # "A. SECTION TITLE"
        r'^Section\s+(\d+)\s*[:\-]?\s*([^\n]+)',  # "Section 1: Title"
    ]
    
    CLAUSE_PATTERNS = [
        r'^(\d+\.\d+)\s+(.+)',                 # "1.1 Clause text"
        r'^([a-z])\)\s+(.+)',                   # "a) Clause text"
        r'^\(([a-z])\)\s+(.+)',                 # "(a) Clause text"
    ]
    
    async def extract_structure(self, text: str) -> List[Clause]:
        """
        Parse document into structured clauses.
        
        Strategy:
        1. Split into lines
        2. Identify sections/subsections
        3. Group text into clauses
        4. Track hierarchy
        """
        lines = text.split('\n')
        clauses = []
        
        current_section = "Preamble"
        current_subsection = ""
        current_clause_num = ""
        clause_text_buffer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            section_match = self._match_section(line)
            if section_match:
                # Save previous clause if exists
                if clause_text_buffer:
                    clauses.append(Clause(
                        section=current_section,
                        subsection=current_subsection,
                        clause_number=current_clause_num,
                        text=" ".join(clause_text_buffer),
                        level=self._determine_level(current_section, current_subsection)
                    ))
                    clause_text_buffer = []
                
                current_section = section_match
                current_subsection = ""
                current_clause_num = ""
                continue
            
            # Check if line is a clause start
            clause_match = self._match_clause(line)
            if clause_match:
                # Save previous clause
                if clause_text_buffer:
                    clauses.append(Clause(
                        section=current_section,
                        subsection=current_subsection,
                        clause_number=current_clause_num,
                        text=" ".join(clause_text_buffer),
                        level=self._determine_level(current_section, current_subsection)
                    ))
                
                current_clause_num = clause_match[0]
                clause_text_buffer = [clause_match[1]]
                continue
            
            # Otherwise, accumulate text
            clause_text_buffer.append(line)
        
        # Don't forget last clause
        if clause_text_buffer:
            clauses.append(Clause(
                section=current_section,
                subsection=current_subsection,
                clause_number=current_clause_num,
                text=" ".join(clause_text_buffer),
                level=self._determine_level(current_section, current_subsection)
            ))
        
        return clauses
    
    def _match_section(self, line: str) -> str | None:
        """Check if line matches section pattern."""
        for pattern in self.SECTION_PATTERNS:
            match = re.match(pattern, line)
            if match:
                return match.group(2).strip()
        return None
    
    def _match_clause(self, line: str) -> tuple | None:
        """Check if line matches clause pattern. Returns (number, text)."""
        for pattern in self.CLAUSE_PATTERNS:
            match = re.match(pattern, line)
            if match:
                return (match.group(1), match.group(2).strip())
        return None
    
    def _determine_level(self, section: str, subsection: str) -> int:
        """Determine hierarchy level (0=section, 1=subsection, 2=clause)."""
        if subsection:
            return 2
        elif section != "Preamble":
            return 1
        else:
            return 0
```

**Decision Rules**:
- Start with common T&C patterns, expand as you see more documents
- Keep state (current_section, etc.) while iterating
- Buffer text until you hit next section/clause
- Return structured dataclasses (easier to work with)
- Handle edge cases (documents without clear structure)

**When Stuck**:
- Print intermediate results to see where parsing breaks
- Test on sample T&C PDFs with different formats
- Consider ML-based structure detection if regex fails too often (future)

---

### 5. Legal Chunker (`backend/app/core/legal_chunker.py`)

**Purpose**: Split clauses into semantic chunks for embedding.

**Implementation Pattern**:
```python
from typing import List
from app.core.structure_extractor import Clause

class LegalChunker:
    """Creates semantic chunks for embedding generation."""
    
    def __init__(self, max_chunk_size: int = 500, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    async def create_chunks(self, clauses: List[Clause]) -> List[Dict]:
        """
        Convert clauses into embeddable chunks with metadata.
        
        Strategy:
        - Keep clauses together if < max_chunk_size
        - Split long clauses with overlap
        - Include context (section, clause number) in metadata
        """
        chunks = []
        
        for clause in clauses:
            # If clause is small enough, keep it as one chunk
            if len(clause.text) <= self.max_chunk_size:
                chunks.append(self._create_chunk(clause, clause.text, 0))
            else:
                # Split large clauses
                sub_chunks = self._split_text(clause.text)
                for idx, sub_text in enumerate(sub_chunks):
                    chunks.append(self._create_chunk(clause, sub_text, idx))
        
        return chunks
    
    def _create_chunk(self, clause: Clause, text: str, chunk_idx: int) -> Dict:
        """Create chunk dict with metadata."""
        return {
            "text": text,
            "metadata": {
                "section": clause.section,
                "subsection": clause.subsection,
                "clause_number": clause.clause_number,
                "level": clause.level,
                "chunk_index": chunk_idx,
                # Full context for better retrieval
                "context": f"{clause.section} - {clause.clause_number}"
            }
        }
    
    def _split_text(self, text: str) -> List[str]:
        """Split text with overlap for large clauses."""
        words = text.split()
        chunks = []
        
        start = 0
        while start < len(words):
            # Take max_chunk_size words
            end = min(start + self.max_chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.overlap if end < len(words) else end
        
        return chunks
```

**Decision Rules**:
- Respect clause boundaries (don't split mid-clause unless necessary)
- Include rich metadata (section, clause number, context)
- Use word-based splitting (not character) for cleaner breaks
- Add overlap to maintain context in adjacent chunks
- Keep chunk size reasonable for embedding quality (300-500 words)

**When Stuck**:
- Check chunk distribution (are most chunks too small/large?)
- Verify metadata is complete (needed for citation)
- Test retrieval: can you find specific clauses?

---

### 6. OpenAI Service (`backend/app/services/openai_service.py`)

**Purpose**: Wrapper for OpenAI API calls with retry logic and caching.

**Implementation Pattern**:
```python
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Dict
import logging

from app.core.config import settings
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class OpenAIService:
    """OpenAI API client with retry and caching."""
    
    def __init__(self, cache: CacheService = None):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.cache = cache
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_embedding(self, text: str) -> List[float]:
        """Generate embedding for text with caching."""
        # Check cache first
        if self.cache:
            cache_key = f"embedding:{hash(text)}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        # Call OpenAI
        response = await self.client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text
        )
        embedding = response.data[0].embedding
        
        # Cache result
        if self.cache:
            await self.cache.set(cache_key, embedding, ttl=86400)  # 24h
        
        return embedding
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_completion(
        self,
        prompt: str,
        model: str = None,
        temperature: float = 0.0,
        max_tokens: int = 1000
    ) -> str:
        """Generate completion with GPT-4."""
        model = model or settings.OPENAI_MODEL_GPT4
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    async def batch_create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings in batch (up to 100 at a time)."""
        BATCH_SIZE = 100
        all_embeddings = []
        
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            response = await self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=batch
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)
        
        return all_embeddings
```

**Decision Rules**:
- Always use retry decorator for API calls
- Cache embeddings (they're deterministic)
- Use batch API for multiple embeddings (more efficient)
- Set temperature=0.0 for consistent outputs
- Use GPT-4 for complex reasoning (metadata, risk assessment)
- Use GPT-3.5-turbo for simple tasks (cost savings)

**When Stuck**:
- Check rate limits (429 errors) → add exponential backoff
- Verify API key is loaded correctly
- Test with simple prompt first
- Monitor costs (embeddings are cheap, GPT-4 completions are expensive)

---

### 7. Pinecone Service (`backend/app/services/pinecone_service.py`)

**Purpose**: Vector database operations with dual-namespace strategy.

**Implementation Pattern**:
```python
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class PineconeService:
    """Pinecone vector database client."""
    
    def __init__(self):
        self.client = None
        self.index = None
    
    async def initialize(self):
        """Initialize Pinecone client and index."""
        self.client = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        # Create index if doesn't exist
        if settings.PINECONE_INDEX_NAME not in self.client.list_indexes().names():
            self.client.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=1536,  # OpenAI text-embedding-3-small
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            logger.info(f"Created Pinecone index: {settings.PINECONE_INDEX_NAME}")
        
        self.index = self.client.Index(settings.PINECONE_INDEX_NAME)
    
    async def upsert_chunks(
        self,
        chunks: List[Dict],
        namespace: str,
        document_id: str
    ):
        """
        Insert chunks into Pinecone.
        
        Args:
            chunks: List of {text, embedding, metadata}
            namespace: "user_tcs" or "baseline"
            document_id: Unique document ID
        """
        vectors = []
        for idx, chunk in enumerate(chunks):
            vector_id = f"{document_id}_chunk_{idx}"
            vectors.append({
                "id": vector_id,
                "values": chunk["embedding"],
                "metadata": {
                    **chunk["metadata"],
                    "document_id": document_id,
                    "text": chunk["text"][:1000]  # Pinecone metadata limit
                }
            })
        
        # Upsert in batches
        BATCH_SIZE = 100
        for i in range(0, len(vectors), BATCH_SIZE):
            batch = vectors[i:i + BATCH_SIZE]
            self.index.upsert(vectors=batch, namespace=namespace)
        
        logger.info(f"Upserted {len(vectors)} vectors to namespace '{namespace}'")
    
    async def query(
        self,
        query_embedding: List[float],
        namespace: str,
        top_k: int = 5,
        filter: Dict = None
    ) -> List[Dict]:
        """
        Query Pinecone for similar vectors.
        
        Returns: List of matches with metadata
        """
        results = self.index.query(
            vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )
        
        return [
            {
                "id": match["id"],
                "score": match["score"],
                "metadata": match["metadata"]
            }
            for match in results["matches"]
        ]
    
    async def delete_document(self, document_id: str, namespace: str):
        """Delete all chunks for a document."""
        self.index.delete(
            filter={"document_id": document_id},
            namespace=namespace
        )
```

**Decision Rules**:
- Use **dual-namespace strategy**:
  - `user_tcs`: User-uploaded documents
  - `baseline`: Standard T&Cs for comparison
- Include document_id in metadata for filtering
- Batch upsert operations (100 vectors at a time)
- Store truncated text in metadata (1000 char limit)
- Use cosine similarity for semantic search
- Create index on first initialization

**When Stuck**:
- Verify API key and environment are correct
- Check index dimensions match embedding model
- Test query with known document first
- Use `filter` to narrow search by document_id

---

### 8. Upload Endpoint (`backend/app/api/v1/upload.py`)

**Purpose**: Handle PDF upload and orchestrate full processing pipeline.

**Implementation Pattern**:
```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import os

from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker
from app.core.metadata_extractor import MetadataExtractor
from app.core.anomaly_detector import AnomalyDetector
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.post("/", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    openai_service: OpenAIService = Depends(),
    pinecone_service: PineconeService = Depends()
):
    """
    Upload and process T&C document.
    
    Pipeline:
    1. Save PDF to temp location
    2. Extract text
    3. Parse structure
    4. Create chunks
    5. Generate embeddings
    6. Extract metadata
    7. Store in Pinecone
    8. Save to database
    9. Run anomaly detection
    """
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")
    
    # Generate document ID
    doc_id = str(uuid.uuid4())
    
    # Save uploaded file temporarily
    temp_path = f"/tmp/{doc_id}.pdf"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        # Step 1: Extract text
        processor = DocumentProcessor()
        extracted = await processor.extract_text(temp_path)
        text = extracted["text"]
        
        # Step 2: Parse structure
        extractor = StructureExtractor()
        clauses = await extractor.extract_structure(text)
        
        # Step 3: Create chunks
        chunker = LegalChunker()
        chunks = await chunker.create_chunks(clauses)
        
        # Step 4: Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = await openai_service.batch_create_embeddings(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        
        # Step 5: Extract metadata
        metadata_extractor = MetadataExtractor(openai_service)
        metadata = await metadata_extractor.extract(text)
        
        # Step 6: Store in Pinecone (user_tcs namespace)
        await pinecone_service.upsert_chunks(
            chunks=chunks,
            namespace="user_tcs",
            document_id=doc_id
        )
        
        # Step 7: Save to database
        document = Document(
            id=doc_id,
            user_id=current_user.id,
            filename=file.filename,
            text=text,
            metadata=metadata,
            page_count=extracted["page_count"],
            clause_count=len(clauses)
        )
        db.add(document)
        db.commit()
        
        # Step 8: Run anomaly detection (async task in production)
        detector = AnomalyDetector(openai_service, pinecone_service, db)
        anomalies = await detector.detect_anomalies(doc_id, clauses)
        
        return DocumentResponse(
            id=doc_id,
            filename=file.filename,
            metadata=metadata,
            page_count=extracted["page_count"],
            clause_count=len(clauses),
            anomaly_count=len(anomalies),
            anomalies=anomalies[:5]  # Return top 5 for preview
        )
    
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
```

**Decision Rules**:
- Generate UUID for document ID (unique, URL-safe)
- Use temp file storage for upload (clean up after)
- Batch embeddings for efficiency
- Store raw text in database (for re-processing)
- Run anomaly detection synchronously for MVP (make async later with Celery)
- Return preview of anomalies (not all, frontend can fetch more)
- Rollback database if any step fails

**When Stuck**:
- Test each step independently first
- Check file upload limits (FastAPI default: 1MB, increase if needed)
- Verify Pinecone namespace is correct
- Monitor processing time (should be < 30s for typical T&C)

---

### 9. Query Endpoint (`backend/app/api/v1/query.py`)

**Purpose**: Answer questions about T&C documents with citations.

**Implementation Pattern**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.schemas.query import QueryRequest, QueryResponse
from app.api.deps import get_db, get_current_user
from app.prompts.qa_prompts import QA_SYSTEM_PROMPT

router = APIRouter()

@router.post("/", response_model=QueryResponse)
async def query_document(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    openai_service: OpenAIService = Depends(),
    pinecone_service: PineconeService = Depends()
):
    """
    Answer questions about T&C documents.
    
    Pipeline:
    1. Generate embedding for question
    2. Search Pinecone for relevant clauses
    3. Build context from retrieved clauses
    4. Generate answer with GPT-4
    5. Return answer with citations
    """
    
    # Step 1: Generate question embedding
    question_embedding = await openai_service.create_embedding(request.question)
    
    # Step 2: Search Pinecone
    results = await pinecone_service.query(
        query_embedding=question_embedding,
        namespace="user_tcs",
        top_k=5,
        filter={"document_id": request.document_id}
    )
    
    if not results:
        raise HTTPException(404, "No relevant clauses found")
    
    # Step 3: Build context
    context_parts = []
    citations = []
    
    for idx, match in enumerate(results):
        metadata = match["metadata"]
        context_parts.append(
            f"[{idx + 1}] Section: {metadata['section']}, "
            f"Clause: {metadata.get('clause_number', 'N/A')}\n"
            f"{metadata['text']}"
        )
        citations.append({
            "index": idx + 1,
            "section": metadata["section"],
            "clause": metadata.get("clause_number", "N/A"),
            "text": metadata["text"][:200] + "...",  # Preview
            "relevance_score": match["score"]
        })
    
    context = "\n\n".join(context_parts)
    
    # Step 4: Generate answer
    prompt = QA_SYSTEM_PROMPT.format(
        context=context,
        question=request.question
    )
    
    answer = await openai_service.create_completion(
        prompt=prompt,
        temperature=0.0,
        max_tokens=500
    )
    
    # Step 5: Return response
    return QueryResponse(
        question=request.question,
        answer=answer,
        citations=citations,
        confidence=results[0]["score"]  # Use top result's score
    )
```

**Prompt Template** (`backend/app/prompts/qa_prompts.py`):
```python
QA_SYSTEM_PROMPT = """You are a legal assistant analyzing Terms & Conditions documents.

Context from the document:
{context}

User Question: {question}

Instructions:
1. Answer the question based ONLY on the provided context
2. Cite specific sections using [1], [2], etc.
3. If the context doesn't contain the answer, say "I cannot find this information in the provided Terms & Conditions"
4. Use clear, plain language (avoid legalese when possible)
5. Be concise but complete

Answer:"""
```

**Decision Rules**:
- Filter by document_id to only search relevant document
- Retrieve top 5 clauses (balance relevance vs context size)
- Include citation indexes in prompt ([1], [2], etc.)
- Use temperature=0 for consistent answers
- Validate that retrieved clauses are actually relevant (check score > 0.7)
- Return confidence score (based on top match)

**When Stuck**:
- If no results → check if document was indexed correctly
- If answer is irrelevant → adjust top_k or prompt
- If citations are wrong → verify metadata structure

---

### 10. Anomaly Detection (`backend/app/core/anomaly_detector.py`)

**Purpose**: Detect risky clauses by comparing against baseline corpus.

**Implementation Pattern**:
```python
from typing import List, Dict
from app.core.structure_extractor import Clause
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.core.prevalence_calculator import PrevalenceCalculator
from app.core.risk_assessor import RiskAssessor
from app.prompts.anomaly_prompts import RISK_ASSESSMENT_PROMPT

class AnomalyDetector:
    """Detects unusual/risky clauses in T&C documents."""
    
    def __init__(
        self,
        openai_service: OpenAIService,
        pinecone_service: PineconeService,
        db
    ):
        self.openai = openai_service
        self.pinecone = pinecone_service
        self.db = db
        self.prevalence_calc = PrevalenceCalculator(openai_service, pinecone_service)
        self.risk_assessor = RiskAssessor(openai_service)
    
    async def detect_anomalies(
        self,
        document_id: str,
        clauses: List[Clause]
    ) -> List[Dict]:
        """
        Detect anomalies for all clauses in document.
        
        Pipeline:
        1. For each clause, generate embedding
        2. Query baseline corpus for similar clauses
        3. Calculate prevalence score
        4. Check risk indicators
        5. If suspicious, run GPT-4 risk assessment
        6. Flag high-risk clauses
        """
        
        anomalies = []
        
        for clause in clauses:
            # Step 1: Generate embedding
            clause_embedding = await self.openai.create_embedding(clause.text)
            
            # Step 2: Query baseline corpus
            baseline_matches = await self.pinecone.query(
                query_embedding=clause_embedding,
                namespace="baseline",  # ⚠️ Critical: use baseline namespace
                top_k=10
            )
            
            # Step 3: Calculate prevalence
            prevalence = await self.prevalence_calc.calculate(
                clause.text,
                baseline_matches
            )
            
            # Step 4: Check risk indicators
            risk_flags = self._check_risk_indicators(clause.text)
            
            # Step 5: Determine if suspicious
            is_suspicious = (
                prevalence < 0.3 or  # Rare clause
                len(risk_flags) > 0  # Has risk keywords
            )
            
            if is_suspicious:
                # Step 6: GPT-4 risk assessment
                risk_assessment = await self.risk_assessor.assess(
                    clause.text,
                    baseline_matches,
                    risk_flags
                )
                
                if risk_assessment["severity"] in ["medium", "high"]:
                    anomalies.append({
                        "clause": clause.text,
                        "section": clause.section,
                        "clause_number": clause.clause_number,
                        "prevalence": prevalence,
                        "severity": risk_assessment["severity"],
                        "explanation": risk_assessment["explanation"],
                        "risk_flags": risk_flags
                    })
        
        return anomalies
    
    def _check_risk_indicators(self, text: str) -> List[str]:
        """Check for risky keywords/patterns."""
        risk_keywords = {
            "unlimited liability": ["unlimited", "liability"],
            "arbitration": ["arbitration", "class action waiver"],
            "data_sharing": ["sell", "share", "third party", "data"],
            "auto_renewal": ["auto-renew", "automatically renew"],
            "no_refund": ["no refund", "non-refundable"],
            "unilateral_changes": ["change at any time", "sole discretion"]
        }
        
        flags = []
        text_lower = text.lower()
        
        for flag_name, keywords in risk_keywords.items():
            if all(kw in text_lower for kw in keywords):
                flags.append(flag_name)
        
        return flags
```

**Prevalence Calculator** (`backend/app/core/prevalence_calculator.py`):
```python
class PrevalenceCalculator:
    """Calculates how common a clause is in baseline corpus."""
    
    async def calculate(
        self,
        clause_text: str,
        baseline_matches: List[Dict]
    ) -> float:
        """
        Calculate prevalence score (0-1).
        
        Logic:
        - If top match has score > 0.9 → high prevalence (common clause)
        - If no matches > 0.7 → low prevalence (rare clause)
        - Weighted average of top 10 matches
        """
        if not baseline_matches:
            return 0.0
        
        # Weighted average of top matches
        weights = [1.0, 0.8, 0.6, 0.4, 0.2] + [0.1] * 5  # Top 5 weighted higher
        total_weight = sum(weights[:len(baseline_matches)])
        
        weighted_score = sum(
            match["score"] * weight
            for match, weight in zip(baseline_matches, weights)
        )
        
        prevalence = weighted_score / total_weight
        return prevalence
```

**Risk Assessor** (`backend/app/core/risk_assessor.py`):
```python
class RiskAssessor:
    """GPT-4 powered risk assessment."""
    
    async def assess(
        self,
        clause_text: str,
        baseline_matches: List[Dict],
        risk_flags: List[str]
    ) -> Dict:
        """
        Use GPT-4 to assess risk level.
        
        Returns: {
            "severity": "low" | "medium" | "high",
            "explanation": str
        }
        """
        # Build context of similar baseline clauses
        baseline_examples = "\n".join([
            f"- {match['metadata']['text'][:200]}"
            for match in baseline_matches[:3]
        ])
        
        prompt = RISK_ASSESSMENT_PROMPT.format(
            clause=clause_text,
            baseline_examples=baseline_examples,
            risk_flags=", ".join(risk_flags) if risk_flags else "None"
        )
        
        response = await self.openai.create_completion(
            prompt=prompt,
            temperature=0.0,
            max_tokens=300
        )
        
        # Parse response (expect JSON or structured text)
        severity = self._extract_severity(response)
        
        return {
            "severity": severity,
            "explanation": response
        }
    
    def _extract_severity(self, response: str) -> str:
        """Extract severity from GPT-4 response."""
        response_lower = response.lower()
        if "high" in response_lower[:50]:
            return "high"
        elif "medium" in response_lower[:50]:
            return "medium"
        else:
            return "low"
```

**Prompt** (`backend/app/prompts/anomaly_prompts.py`):
```python
RISK_ASSESSMENT_PROMPT = """You are a consumer protection expert analyzing Terms & Conditions clauses.

Clause to analyze:
{clause}

Similar clauses from standard T&Cs:
{baseline_examples}

Detected risk flags: {risk_flags}

Assess the risk level of this clause for consumers:
1. Compare it to standard T&C clauses
2. Consider consumer protection concerns
3. Evaluate fairness and transparency

Respond in this format:
Severity: [low/medium/high]
Explanation: [2-3 sentences explaining why this is risky or not]

Assessment:"""
```

**Decision Rules**:
- **Prevalence threshold**: < 0.3 = rare, flag for review
- **Risk keywords**: Maintain list of concerning patterns
- Only run GPT-4 on suspicious clauses (cost optimization)
- Severity levels:
  - **High**: Severely unfair, hidden costs, liability waivers
  - **Medium**: Uncommon but not necessarily unfair
  - **Low**: Common clause, no concerns
- Store anomalies in database for user review

**When Stuck**:
- Test with known risky clauses (arbitration, auto-renewal)
- Verify baseline corpus is populated (need 100+ T&Cs)
- If too many false positives → adjust prevalence threshold
- If missing real issues → expand risk keywords

---

## 🧩 Database Models & Schemas

### Models (`backend/app/models/`)

**User Model**:
```python
from sqlalchemy import Column, String, DateTime
from app.db.base import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Document Model**:
```python
from sqlalchemy import Column, String, Integer, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    text = Column(String)  # Full extracted text
    metadata = Column(JSON)  # {company, jurisdiction, effective_date, etc.}
    page_count = Column(Integer)
    clause_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="documents")
    anomalies = relationship("Anomaly", back_populates="document")
```

**Anomaly Model**:
```python
class Anomaly(Base):
    __tablename__ = "anomalies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"))
    clause_text = Column(String)
    section = Column(String)
    clause_number = Column(String)
    severity = Column(String)  # low, medium, high
    explanation = Column(String)
    prevalence = Column(Float)
    risk_flags = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="anomalies")
```

### Schemas (`backend/app/schemas/`)

Use Pydantic for request/response validation:
```python
from pydantic import BaseModel
from typing import List, Optional

class DocumentResponse(BaseModel):
    id: str
    filename: str
    metadata: dict
    page_count: int
    clause_count: int
    anomaly_count: int
    anomalies: List[dict]
    
    class Config:
        from_attributes = True
```

---

## 🎨 Frontend Implementation (React + TypeScript)

### Complete Frontend Structure
```
frontend/
├── public/
│   └── vite.svg
├── src/
│   ├── components/
│   │   ├── ui/                      # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── tabs.tsx
│   │   │   └── alert.tsx
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── document/
│   │   │   ├── UploadDocument.tsx   # Drag-drop upload interface
│   │   │   ├── DocumentList.tsx     # List user's documents
│   │   │   ├── DocumentCard.tsx     # Document summary card
│   │   │   └── DocumentViewer.tsx   # Full document view
│   │   ├── analysis/
│   │   │   ├── AnalysisResults.tsx  # Overall analysis summary
│   │   │   ├── MetadataPanel.tsx    # Company, jurisdiction, etc.
│   │   │   ├── ClauseBreakdown.tsx  # Section/clause stats
│   │   │   └── RiskScore.tsx        # Overall risk visualization
│   │   ├── anomaly/
│   │   │   ├── AnomalyList.tsx      # List of detected anomalies
│   │   │   ├── AnomalyCard.tsx      # Individual anomaly display
│   │   │   ├── SeverityBadge.tsx    # Color-coded severity
│   │   │   └── AnomalyDetails.tsx   # Detailed anomaly view
│   │   ├── query/
│   │   │   ├── QueryInterface.tsx   # Q&A chat interface
│   │   │   ├── QueryInput.tsx       # Question input box
│   │   │   ├── QueryResponse.tsx    # Answer with citations
│   │   │   └── CitationCard.tsx     # Citation details
│   │   └── auth/
│   │       ├── LoginForm.tsx
│   │       ├── SignupForm.tsx
│   │       └── ProtectedRoute.tsx
│   ├── pages/
│   │   ├── HomePage.tsx             # Landing page
│   │   ├── DashboardPage.tsx        # User dashboard
│   │   ├── DocumentPage.tsx         # Single document view
│   │   ├── UploadPage.tsx           # Upload interface
│   │   ├── LoginPage.tsx            # Auth pages
│   │   └── SignupPage.tsx
│   ├── services/
│   │   ├── api.ts                   # Axios client
│   │   ├── auth.ts                  # Auth service
│   │   └── websocket.ts             # Real-time updates (optional)
│   ├── hooks/
│   │   ├── useDocuments.ts          # Document CRUD
│   │   ├── useQuery.ts              # Q&A queries
│   │   ├── useAnomalies.ts          # Anomaly data
│   │   └── useAuth.ts               # Auth state
│   ├── types/
│   │   ├── index.ts                 # All TypeScript types
│   │   ├── document.ts
│   │   ├── anomaly.ts
│   │   └── query.ts
│   ├── utils/
│   │   ├── formatters.ts            # Date, number formatters
│   │   ├── validators.ts            # Form validation
│   │   └── constants.ts             # App constants
│   ├── styles/
│   │   └── globals.css              # Global styles + Tailwind
│   ├── App.tsx                      # Main app component
│   ├── main.tsx                     # Entry point
│   └── router.tsx                   # React Router config
├── .env.example
├── .eslintrc.cjs
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

---

### 1. Setup & Configuration

#### `package.json`:
```json
{
  "name": "tc-analysis-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.14.0",
    "axios": "^1.6.2",
    "lucide-react": "^0.294.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.1.0",
    "date-fns": "^2.30.0",
    "react-hook-form": "^7.48.2",
    "zod": "^3.22.4",
    "@hookform/resolvers": "^3.3.2"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@typescript-eslint/eslint-plugin": "^6.13.2",
    "@typescript-eslint/parser": "^6.13.2",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.55.0",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.3",
    "vite": "^5.0.7"
  }
}
```

#### `vite.config.ts`:
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

#### `tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

#### `.env.example`:
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_NAME="T&C Analysis"
```

---

### 2. TypeScript Types (`src/types/`)

#### `src/types/document.ts`:
```typescript
export interface Document {
  id: string;
  user_id: string;
  filename: string;
  metadata: DocumentMetadata;
  page_count: number;
  clause_count: number;
  anomaly_count: number;
  created_at: string;
}

export interface DocumentMetadata {
  company?: string;
  jurisdiction?: string;
  effective_date?: string;
  document_type?: string;
  version?: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  metadata: DocumentMetadata;
  page_count: number;
  clause_count: number;
  anomaly_count: number;
  anomalies: Anomaly[];
}
```

#### `src/types/anomaly.ts`:
```typescript
export interface Anomaly {
  id: string;
  document_id: string;
  clause_text: string;
  section: string;
  clause_number: string;
  severity: 'low' | 'medium' | 'high';
  explanation: string;
  prevalence: number;
  risk_flags: string[];
  created_at: string;
}

export interface AnomalyStats {
  total: number;
  high: number;
  medium: number;
  low: number;
}
```

#### `src/types/query.ts`:
```typescript
export interface QueryRequest {
  document_id: string;
  question: string;
}

export interface Citation {
  index: number;
  section: string;
  clause: string;
  text: string;
  relevance_score: number;
}

export interface QueryResponse {
  question: string;
  answer: string;
  citations: Citation[];
  confidence: number;
}
```

---

### 3. API Service (`src/services/api.ts`)

```typescript
import axios, { AxiosInstance } from 'axios';
import type { Document, DocumentUploadResponse } from '@/types/document';
import type { Anomaly } from '@/types/anomaly';
import type { QueryRequest, QueryResponse } from '@/types/query';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor: Add auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Response interceptor: Handle 401s
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(email: string, password: string) {
    const response = await this.client.post('/auth/login', { email, password });
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  }

  async signup(email: string, password: string) {
    const response = await this.client.post('/auth/signup', { email, password });
    return response.data;
  }

  async logout() {
    localStorage.removeItem('access_token');
  }

  // Documents
  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.client.post<DocumentUploadResponse>('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    return response.data;
  }

  async getDocuments(): Promise<Document[]> {
    const response = await this.client.get<Document[]>('/documents');
    return response.data;
  }

  async getDocument(id: string): Promise<Document> {
    const response = await this.client.get<Document>(`/documents/${id}`);
    return response.data;
  }

  async deleteDocument(id: string): Promise<void> {
    await this.client.delete(`/documents/${id}`);
  }

  // Anomalies
  async getAnomalies(documentId: string): Promise<Anomaly[]> {
    const response = await this.client.get<Anomaly[]>(`/anomalies/${documentId}`);
    return response.data;
  }

  // Queries
  async queryDocument(request: QueryRequest): Promise<QueryResponse> {
    const response = await this.client.post<QueryResponse>('/query', request);
    return response.data;
  }
}

export const api = new ApiService();
```

---

### 4. React Query Hooks (`src/hooks/`)

#### `src/hooks/useDocuments.ts`:
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { toast } from 'sonner';

export const useDocuments = () => {
  return useQuery({
    queryKey: ['documents'],
    queryFn: () => api.getDocuments(),
  });
};

export const useDocument = (id: string) => {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: () => api.getDocument(id),
    enabled: !!id,
  });
};

export const useUploadDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => api.uploadDocument(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document uploaded and analyzed successfully!');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Upload failed');
    },
  });
};

export const useDeleteDocument = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      toast.success('Document deleted');
    },
  });
};
```

#### `src/hooks/useAnomalies.ts`:
```typescript
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';

export const useAnomalies = (documentId: string) => {
  return useQuery({
    queryKey: ['anomalies', documentId],
    queryFn: () => api.getAnomalies(documentId),
    enabled: !!documentId,
  });
};
```

#### `src/hooks/useQuery.ts`:
```typescript
import { useMutation } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { QueryRequest } from '@/types/query';

export const useDocumentQuery = () => {
  return useMutation({
    mutationFn: (request: QueryRequest) => api.queryDocument(request),
  });
};
```

---

### 5. Key Components

#### `src/components/document/UploadDocument.tsx`:
```typescript
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Loader2 } from 'lucide-react';
import { useUploadDocument } from '@/hooks/useDocuments';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useNavigate } from 'react-router-dom';

export const UploadDocument = () => {
  const navigate = useNavigate();
  const uploadMutation = useUploadDocument();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    multiple: false,
  });

  const handleUpload = () => {
    if (selectedFile) {
      uploadMutation.mutate(selectedFile, {
        onSuccess: (data) => {
          navigate(`/documents/${data.id}`);
        },
      });
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <Card className="p-8">
        <h2 className="text-2xl font-bold mb-4">Upload Terms & Conditions</h2>
        
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
            ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          
          {selectedFile ? (
            <div className="flex items-center justify-center gap-2">
              <FileText className="h-5 w-5" />
              <span className="font-medium">{selectedFile.name}</span>
            </div>
          ) : (
            <>
              <p className="text-lg mb-2">Drop your PDF here, or click to browse</p>
              <p className="text-sm text-gray-500">Only PDF files are supported</p>
            </>
          )}
        </div>

        {selectedFile && (
          <div className="mt-6 flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={() => setSelectedFile(null)}
              disabled={uploadMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUpload}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                'Upload & Analyze'
              )}
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
};
```

#### `src/components/anomaly/AnomalyList.tsx`:
```typescript
import { useAnomalies } from '@/hooks/useAnomalies';
import { AnomalyCard } from './AnomalyCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface AnomalyListProps {
  documentId: string;
}

export const AnomalyList = ({ documentId }: AnomalyListProps) => {
  const { data: anomalies, isLoading, error } = useAnomalies(documentId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Failed to load anomalies</AlertDescription>
      </Alert>
    );
  }

  if (!anomalies || anomalies.length === 0) {
    return (
      <Alert>
        <AlertDescription>No anomalies detected. This document looks good!</AlertDescription>
      </Alert>
    );
  }

  const highSeverity = anomalies.filter(a => a.severity === 'high');
  const mediumSeverity = anomalies.filter(a => a.severity === 'medium');
  const lowSeverity = anomalies.filter(a => a.severity === 'low');

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2">Detected Anomalies</h2>
        <p className="text-gray-600">
          Found {anomalies.length} potential issues in this document
        </p>
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">All ({anomalies.length})</TabsTrigger>
          <TabsTrigger value="high">High ({highSeverity.length})</TabsTrigger>
          <TabsTrigger value="medium">Medium ({mediumSeverity.length})</TabsTrigger>
          <TabsTrigger value="low">Low ({lowSeverity.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4 mt-6">
          {anomalies.map((anomaly) => (
            <AnomalyCard key={anomaly.id} anomaly={anomaly} />
          ))}
        </TabsContent>

        <TabsContent value="high" className="space-y-4 mt-6">
          {highSeverity.map((anomaly) => (
            <AnomalyCard key={anomaly.id} anomaly={anomaly} />
          ))}
        </TabsContent>

        <TabsContent value="medium" className="space-y-4 mt-6">
          {mediumSeverity.map((anomaly) => (
            <AnomalyCard key={anomaly.id} anomaly={anomaly} />
          ))}
        </TabsContent>

        <TabsContent value="low" className="space-y-4 mt-6">
          {lowSeverity.map((anomaly) => (
            <AnomalyCard key={anomaly.id} anomaly={anomaly} />
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
};
```

#### `src/components/query/QueryInterface.tsx`:
```typescript
import { useState } from 'react';
import { useDocumentQuery } from '@/hooks/useQuery';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { QueryResponse } from './QueryResponse';
import { Loader2, Send } from 'lucide-react';

interface QueryInterfaceProps {
  documentId: string;
}

export const QueryInterface = ({ documentId }: QueryInterfaceProps) => {
  const [question, setQuestion] = useState('');
  const queryMutation = useDocumentQuery();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      queryMutation.mutate({ document_id: documentId, question });
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Ask Questions</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <Textarea
            placeholder="What questions do you have about this document? (e.g., 'What is the refund policy?')"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            className="resize-none"
          />
          
          <div className="flex justify-end">
            <Button
              type="submit"
              disabled={!question.trim() || queryMutation.isPending}
            >
              {queryMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Ask Question
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>

      {queryMutation.data && (
        <QueryResponse response={queryMutation.data} />
      )}
    </div>
  );
};
```

---

### 6. Router Setup (`src/router.tsx`)

```typescript
import { createBrowserRouter } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { HomePage } from '@/pages/HomePage';
import { DashboardPage } from '@/pages/DashboardPage';
import { DocumentPage } from '@/pages/DocumentPage';
import { UploadPage } from '@/pages/UploadPage';
import { LoginPage } from '@/pages/LoginPage';
import { SignupPage } from '@/pages/SignupPage';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <HomePage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/signup',
    element: <SignupPage />,
  },
  {
    element: <ProtectedRoute><Layout /></ProtectedRoute>,
    children: [
      {
        path: '/dashboard',
        element: <DashboardPage />,
      },
      {
        path: '/upload',
        element: <UploadPage />,
      },
      {
        path: '/documents/:id',
        element: <DocumentPage />,
      },
    ],
  },
]);
```

---

### 7. Main Entry (`src/main.tsx`)

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { router } from './router';
import './styles/globals.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

---

### Frontend Decision Rules

1. **State Management**: Use React Query for server state, useState for UI state
2. **Styling**: Tailwind + shadcn/ui for consistency
3. **Forms**: react-hook-form + zod for validation
4. **Navigation**: React Router v6 with nested routes
5. **Auth**: JWT stored in localStorage, interceptor adds to requests
6. **Error Handling**: Toast notifications for user feedback
7. **Loading States**: Skeleton loaders for better UX
8. **Responsive**: Mobile-first approach

**When Stuck**:
- Check shadcn/ui docs for component examples
- Use React Query DevTools for debugging
- Test API calls in browser network tab first
- Verify types match backend schemas

---

## 🚨 Error Handling Strategy

### Custom Exceptions (`backend/app/utils/exceptions.py`):
```python
class DocumentProcessingError(Exception):
    """Raised when document processing fails."""
    pass

class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass

class PineconeError(Exception):
    """Raised when Pinecone operations fail."""
    pass
```

### FastAPI Error Handler:
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(DocumentProcessingError)
async def document_error_handler(request: Request, exc: DocumentProcessingError):
    return JSONResponse(
        status_code=400,
        content={"error": "Document processing failed", "detail": str(exc)}
    )
```

---

## ⚡ Performance Optimization

### 1. Redis Caching

**What to cache**:
- Embeddings (keyed by hash of text)
- Metadata extraction results
- Frequently queried clauses

**Example**:
```python
async def get_embedding_cached(text: str) -> List[float]:
    cache_key = f"emb:{hash(text)}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    embedding = await openai_service.create_embedding(text)
    await redis.set(cache_key, json.dumps(embedding), ex=86400)
    return embedding
```

### 2. Batch Operations

Always batch when possible:
- Embeddings: 100 per request
- Pinecone upserts: 100 vectors per request
- Database inserts: Bulk insert with `db.bulk_insert_mappings()`

### 3. Async Background Tasks

For production, move slow operations to background:
```python
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    # Process immediately
    doc_id = await quick_upload(file)
    
    # Run anomaly detection in background
    background_tasks.add_task(detect_anomalies_task, doc_id)
    
    return {"id": doc_id, "status": "processing"}
```

---

## 🧪 Testing Strategy

### Unit Tests (`backend/tests/test_structure_extractor.py`):
```python
import pytest
from app.core.structure_extractor import StructureExtractor

@pytest.mark.asyncio
async def test_extract_sections():
    extractor = StructureExtractor()
    text = """
    1. TERMS OF SERVICE
    This agreement governs your use...
    
    2. USER OBLIGATIONS
    You agree to...
    """
    
    clauses = await extractor.extract_structure(text)
    assert len(clauses) == 2
    assert clauses[0].section == "TERMS OF SERVICE"
    assert clauses[1].section == "USER OBLIGATIONS"
```

### Integration Tests:
```python
@pytest.mark.asyncio
async def test_upload_flow(client, test_pdf):
    response = await client.post(
        "/api/v1/upload",
        files={"file": ("test.pdf", test_pdf, "application/pdf")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["clause_count"] > 0
```

---

## 🐛 Debugging & Troubleshooting

### Common Issues & Solutions

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| PDF extraction returns empty text | Scanned PDF (no text layer) | Add OCR support (pytesseract) |
| Embeddings too slow | Too many API calls | Batch embeddings (100 at once) |
| Pinecone query returns no results | Wrong namespace or index empty | Verify namespace, check index stats |
| GPT-4 costs too high | Calling too frequently | Cache results, use GPT-3.5 when possible |
| Database connection timeout | Connection not closed | Use context managers, connection pooling |
| Frontend can't reach backend | CORS or wrong URL | Check CORS settings, verify backend URL |

### Logging Best Practices:
```python
import logging

logger = logging.getLogger(__name__)

# Use structured logging
logger.info("Processing document", extra={
    "document_id": doc_id,
    "page_count": page_count,
    "extraction_method": "pdfplumber"
})

# Log errors with context
try:
    await process()
except Exception as e:
    logger.error(f"Processing failed for {doc_id}", exc_info=True)
```

---

## 📊 Data Collection & Management

### Data Directory Structure
```
data/
├── baseline_corpus/           # 100+ standard T&Cs for comparison
│   ├── tech/
│   │   ├── google_tos.pdf
│   │   ├── facebook_tos.pdf
│   │   ├── apple_tos.pdf
│   │   └── ... (20+ files)
│   ├── ecommerce/
│   │   ├── amazon_tos.pdf
│   │   ├── ebay_tos.pdf
│   │   └── ... (20+ files)
│   ├── saas/
│   │   ├── salesforce_tos.pdf
│   │   ├── slack_tos.pdf
│   │   └── ... (20+ files)
│   ├── finance/
│   │   ├── paypal_tos.pdf
│   │   ├── stripe_tos.pdf
│   │   └── ... (20+ files)
│   └── general/
│       └── ... (20+ files)
├── test_samples/              # Test documents for development
│   ├── simple_tos.pdf
│   ├── complex_tos.pdf
│   └── edge_cases/
│       ├── scanned_doc.pdf
│       ├── multi_language.pdf
│       └── corrupted.pdf
└── metadata.json              # Corpus metadata index
```

---

### Baseline Corpus Collection Strategy

#### Target: 100+ Standard T&C Documents

**Categories to Cover** (20+ documents each):
1. **Technology**: Google, Microsoft, Apple, Meta, Amazon, Twitter, LinkedIn, GitHub, Zoom, Dropbox
2. **E-commerce**: Amazon, eBay, Etsy, Walmart, Target, Shopify
3. **SaaS**: Salesforce, Slack, Notion, Asana, Trello, Monday.com
4. **Finance**: PayPal, Stripe, Square, Venmo, Cash App, Wise
5. **General Services**: Uber, Airbnb, DoorDash, Hotels.com

**Collection Script** (`scripts/collect_baseline_corpus.py`):
```python
"""
Collect baseline T&C corpus from public sources.

Usage:
    python scripts/collect_baseline_corpus.py --output data/baseline_corpus
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict
import httpx
import logging

logger = logging.getLogger(__name__)

# List of T&C URLs to scrape (examples)
BASELINE_SOURCES = {
    "tech": [
        {"name": "Google", "url": "https://policies.google.com/terms", "type": "web"},
        {"name": "Microsoft", "url": "https://www.microsoft.com/en-us/servicesagreement", "type": "web"},
        {"name": "Apple", "url": "https://www.apple.com/legal/internet-services/terms/site.html", "type": "web"},
        # Add more sources...
    ],
    "ecommerce": [
        {"name": "Amazon", "url": "https://www.amazon.com/gp/help/customer/display.html?nodeId=508088", "type": "web"},
        # Add more...
    ],
    "saas": [
        {"name": "Salesforce", "url": "https://www.salesforce.com/company/legal/agreements/", "type": "web"},
        # Add more...
    ],
}

async def download_pdf(url: str, output_path: Path) -> bool:
    """Download PDF from URL."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            logger.info(f"Downloaded: {output_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

async def convert_web_to_pdf(url: str, output_path: Path) -> bool:
    """
    Convert web page to PDF.
    
    Note: This requires a headless browser or API service.
    Options:
    - Playwright (recommended)
    - Selenium
    - API service (e.g., api2pdf.com, pdfcrowd.com)
    """
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            await page.pdf(path=str(output_path))
            
            await browser.close()
            logger.info(f"Converted to PDF: {output_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to convert {url} to PDF: {e}")
        return False

async def collect_corpus(output_dir: Path):
    """Collect baseline corpus."""
    metadata = []
    
    for category, sources in BASELINE_SOURCES.items():
        category_dir = output_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        for source in sources:
            filename = f"{source['name'].lower().replace(' ', '_')}_tos.pdf"
            output_path = category_dir / filename
            
            # Skip if already exists
            if output_path.exists():
                logger.info(f"Skipping (already exists): {filename}")
                continue
            
            # Download/convert based on type
            if source['type'] == 'pdf':
                success = await download_pdf(source['url'], output_path)
            else:  # web
                success = await convert_web_to_pdf(source['url'], output_path)
            
            if success:
                metadata.append({
                    "filename": filename,
                    "category": category,
                    "company": source['name'],
                    "source_url": source['url'],
                    "collected_at": str(datetime.now())
                })
            
            # Rate limiting
            await asyncio.sleep(2)
    
    # Save metadata
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    
    logger.info(f"Collected {len(metadata)} documents")
    logger.info(f"Metadata saved to: {metadata_path}")

if __name__ == "__main__":
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/baseline_corpus"))
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    asyncio.run(collect_corpus(args.output))
```

**Manual Collection Process**:
1. Visit company websites
2. Navigate to Terms of Service / Terms & Conditions
3. Save as PDF (Print → Save as PDF) or download if available
4. Name consistently: `{company_name}_tos.pdf`
5. Organize by category
6. Update `metadata.json`

---

### Indexing Baseline Corpus

**Script** (`scripts/index_baseline_corpus.py`):
```python
"""
Index baseline corpus into Pinecone.

This script:
1. Processes all PDFs in baseline_corpus/
2. Extracts text and structure
3. Generates embeddings
4. Uploads to Pinecone (baseline namespace)

Usage:
    python scripts/index_baseline_corpus.py
"""

import asyncio
import sys
from pathlib import Path
from tqdm import tqdm

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService

async def index_baseline_corpus():
    """Index all baseline documents."""
    
    # Initialize services
    openai_service = OpenAIService()
    pinecone_service = PineconeService()
    await pinecone_service.initialize()
    
    processor = DocumentProcessor()
    extractor = StructureExtractor()
    chunker = LegalChunker()
    
    # Get all PDFs
    baseline_dir = Path("data/baseline_corpus")
    pdf_files = list(baseline_dir.rglob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDFs to index")
    
    for pdf_path in tqdm(pdf_files, desc="Indexing baseline corpus"):
        try:
            # Generate document ID
            doc_id = f"baseline_{pdf_path.stem}"
            
            # Process document
            extracted = await processor.extract_text(str(pdf_path))
            clauses = await extractor.extract_structure(extracted["text"])
            chunks = await chunker.create_chunks(clauses)
            
            # Generate embeddings
            texts = [chunk["text"] for chunk in chunks]
            embeddings = await openai_service.batch_create_embeddings(texts)
            
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding
            
            # Upload to Pinecone (baseline namespace)
            await pinecone_service.upsert_chunks(
                chunks=chunks,
                namespace="baseline",  # ⚠️ Critical: use baseline namespace
                document_id=doc_id
            )
            
            print(f"✓ Indexed: {pdf_path.name}")
            
        except Exception as e:
            print(f"✗ Failed to index {pdf_path.name}: {e}")
            continue
    
    print("\n✅ Baseline corpus indexing complete!")

if __name__ == "__main__":
    asyncio.run(index_baseline_corpus())
```

---

### Test Samples

**Create Test Documents** (`scripts/create_test_samples.py`):
```python
"""
Generate test T&C samples for development.

Creates PDFs with:
- Simple structure (3-5 sections)
- Complex structure (10+ sections, nested clauses)
- Edge cases (unusual formatting)
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

def create_simple_tos():
    """Create a simple T&C document."""
    output = Path("data/test_samples/simple_tos.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    
    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Terms of Service - Simple Example")
    
    # Content
    c.setFont("Helvetica", 12)
    y = height - 100
    
    sections = [
        ("1. ACCEPTANCE OF TERMS", 
         "By using this service, you agree to be bound by these terms."),
        
        ("2. USER OBLIGATIONS",
         "You agree to use the service responsibly and not engage in prohibited activities."),
        
        ("3. LIMITATION OF LIABILITY",
         "We are not liable for any damages arising from your use of the service."),
        
        ("4. TERMINATION",
         "We may terminate your access at any time for any reason."),
    ]
    
    for title, content in sections:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, title)
        y -= 20
        
        c.setFont("Helvetica", 10)
        c.drawString(50, y, content)
        y -= 30
    
    c.save()
    print(f"Created: {output}")

def create_complex_tos():
    """Create a complex T&C with risky clauses."""
    output = Path("data/test_samples/complex_tos.pdf")
    
    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Terms of Service - Complex Example")
    
    y = height - 100
    c.setFont("Helvetica", 10)
    
    # Add sections with risky clauses
    risky_clauses = [
        "We may change these terms at any time at our sole discretion without notice.",
        "You agree to unlimited liability for any claims arising from your use.",
        "By using this service, you waive your right to participate in class action lawsuits.",
        "We may share your data with third parties for any purpose without restriction.",
        "This service automatically renews and charges your payment method without notice.",
        "All payments are non-refundable under any circumstances.",
    ]
    
    for idx, clause in enumerate(risky_clauses, 1):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"{idx}. CLAUSE {idx}")
        y -= 20
        
        c.setFont("Helvetica", 10)
        c.drawString(50, y, clause)
        y -= 30
        
        if y < 100:
            c.showPage()
            y = height - 50
    
    c.save()
    print(f"Created: {output}")

if __name__ == "__main__":
    create_simple_tos()
    create_complex_tos()
    print("\n✅ Test samples created!")
```

---

## 🛠️ Scripts Directory

### Script Organization
```
scripts/
├── README.md                          # Documentation
├── collect_baseline_corpus.py         # Collect 100+ T&Cs
├── index_baseline_corpus.py           # Index to Pinecone
├── create_test_samples.py             # Generate test PDFs
├── validate_corpus.py                 # Check corpus quality
├── analyze_corpus_stats.py            # Corpus statistics
├── backup_database.py                 # Database backup
├── migrate_pinecone_namespace.py      # Move vectors between namespaces
└── benchmark_performance.py           # Performance testing
```

---

### Key Scripts

#### `scripts/README.md`:
```markdown
# Utility Scripts

## Data Collection

### `collect_baseline_corpus.py`
Collects 100+ standard T&C documents from public sources.

**Prerequisites**:
- `pip install playwright httpx`
- `playwright install chromium`

**Usage**:
```bash
python scripts/collect_baseline_corpus.py --output data/baseline_corpus
```

**What it does**:
1. Downloads/converts T&Cs from list of sources
2. Organizes by category (tech, ecommerce, saas, etc.)
3. Saves metadata.json with source info

---

### `index_baseline_corpus.py`
Indexes baseline corpus into Pinecone.

**Prerequisites**:
- Baseline corpus collected
- Pinecone API key configured
- OpenAI API key configured

**Usage**:
```bash
python scripts/index_baseline_corpus.py
```

**What it does**:
1. Processes all PDFs in baseline_corpus/
2. Extracts text, structure, generates embeddings
3. Uploads to Pinecone (baseline namespace)

**Time**: ~2-3 minutes per document (depends on length)

---

## Testing

### `create_test_samples.py`
Generates test T&C PDFs for development.

**Usage**:
```bash
python scripts/create_test_samples.py
```

**Creates**:
- `simple_tos.pdf` - 4 sections, clean structure
- `complex_tos.pdf` - 10+ sections with risky clauses

---

### `validate_corpus.py`
Validates baseline corpus quality.

**Usage**:
```bash
python scripts/validate_corpus.py
```

**Checks**:
- PDFs are readable
- Text extraction works
- Minimum page count (2 pages)
- No duplicate documents
- Metadata completeness

---

## Maintenance

### `backup_database.py`
Backs up PostgreSQL database.

**Usage**:
```bash
python scripts/backup_database.py --output backups/
```

### `migrate_pinecone_namespace.py`
Moves vectors between Pinecone namespaces.

**Usage**:
```bash
python scripts/migrate_pinecone_namespace.py \
    --from-namespace user_tcs \
    --to-namespace user_tcs_v2
```

### `benchmark_performance.py`
Tests system performance.

**Usage**:
```bash
python scripts/benchmark_performance.py
```

**Measures**:
- Document processing time
- Embedding generation time
- Vector search latency
- End-to-end upload time
```

---

#### `scripts/validate_corpus.py`:
```python
"""
Validate baseline corpus quality.

Checks:
- All PDFs are readable
- Text extraction works
- Minimum content length
- No duplicates
- Metadata completeness
"""

import sys
from pathlib import Path
from collections import defaultdict
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.document_processor import DocumentProcessor

async def validate_corpus():
    """Run validation checks."""
    
    processor = DocumentProcessor()
    baseline_dir = Path("data/baseline_corpus")
    
    if not baseline_dir.exists():
        print("❌ Baseline corpus directory not found!")
        return False
    
    pdf_files = list(baseline_dir.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files\n")
    
    issues = []
    hashes = defaultdict(list)
    
    for pdf_path in pdf_files:
        print(f"Checking: {pdf_path.name}")
        
        try:
            # Test extraction
            extracted = await processor.extract_text(str(pdf_path))
            text = extracted["text"]
            
            # Check 1: Minimum content
            if len(text) < 500:
                issues.append(f"  ⚠️ Too short ({len(text)} chars): {pdf_path.name}")
            
            # Check 2: Minimum pages
            if extracted["page_count"] < 2:
                issues.append(f"  ⚠️ Only {extracted['page_count']} page(s): {pdf_path.name}")
            
            # Check 3: Detect duplicates
            file_hash = hashlib.md5(text.encode()).hexdigest()
            hashes[file_hash].append(pdf_path.name)
            
            print(f"  ✓ {extracted['page_count']} pages, {len(text)} chars")
            
        except Exception as e:
            issues.append(f"  ❌ Failed to process: {pdf_path.name} - {e}")
    
    # Check for duplicates
    duplicates = {k: v for k, v in hashes.items() if len(v) > 1}
    if duplicates:
        print("\n⚠️ Duplicate documents found:")
        for files in duplicates.values():
            print(f"  - {', '.join(files)}")
    
    # Summary
    print(f"\n{'='*60}")
    if issues:
        print(f"❌ Found {len(issues)} issues:")
        for issue in issues:
            print(issue)
        return False
    else:
        print("✅ All validation checks passed!")
        print(f"   Total documents: {len(pdf_files)}")
        print(f"   Unique documents: {len(hashes)}")
        return True

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(validate_corpus())
    sys.exit(0 if result else 1)
```

---

#### `scripts/benchmark_performance.py`:
```python
"""
Benchmark system performance.

Tests:
- Document processing speed
- Embedding generation
- Vector search latency
- End-to-end upload
"""

import time
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.document_processor import DocumentProcessor
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService

async def benchmark():
    """Run performance benchmarks."""
    
    test_pdf = Path("data/test_samples/simple_tos.pdf")
    
    if not test_pdf.exists():
        print("❌ Test sample not found. Run create_test_samples.py first.")
        return
    
    print("🚀 Starting benchmarks...\n")
    
    # 1. Document Processing
    print("1. Document Processing")
    processor = DocumentProcessor()
    start = time.time()
    extracted = await processor.extract_text(str(test_pdf))
    processing_time = time.time() - start
    print(f"   Time: {processing_time:.2f}s")
    print(f"   Pages: {extracted['page_count']}")
    print(f"   Characters: {len(extracted['text'])}\n")
    
    # 2. Embedding Generation
    print("2. Embedding Generation")
    openai_service = OpenAIService()
    texts = [extracted["text"][:500]]  # First 500 chars
    start = time.time()
    embeddings = await openai_service.batch_create_embeddings(texts)
    embedding_time = time.time() - start
    print(f"   Time: {embedding_time:.2f}s")
    print(f"   Texts: {len(texts)}\n")
    
    # 3. Vector Search
    print("3. Vector Search")
    pinecone_service = PineconeService()
    await pinecone_service.initialize()
    start = time.time()
    results = await pinecone_service.query(
        query_embedding=embeddings[0],
        namespace="baseline",
        top_k=5
    )
    search_time = time.time() - start
    print(f"   Time: {search_time:.2f}s")
    print(f"   Results: {len(results)}\n")
    
    # Summary
    print("="*60)
    print("📊 Summary")
    print(f"   Document Processing: {processing_time:.2f}s")
    print(f"   Embedding Generation: {embedding_time:.2f}s")
    print(f"   Vector Search: {search_time:.2f}s")
    print(f"   Total: {processing_time + embedding_time + search_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(benchmark())
```

---

## 📚 Documentation Directory

### Documentation Structure
```
docs/
├── ARCHITECTURE.md            # System design & architecture
├── API.md                     # API endpoint documentation
├── DEVELOPMENT.md             # Development setup guide
├── DEPLOYMENT.md              # Deployment guide
├── DATA_COLLECTION.md         # Baseline corpus collection
├── TESTING.md                 # Testing strategy
├── TROUBLESHOOTING.md         # Common issues & solutions
└── CONTRIBUTING.md            # Contribution guidelines
```

---

### Key Documentation Files

#### `docs/ARCHITECTURE.md`:
```markdown
# System Architecture

## Overview
This document describes the architecture of the T&C Analysis system.

## High-Level Architecture

```
┌─────────────────┐
│   React SPA     │
│   (Frontend)    │
└────────┬────────┘
         │ HTTPS/REST
         ▼
┌─────────────────┐
│   FastAPI       │
│   (Backend)     │
└────────┬────────┘
         │
    ┌────┴────┬───────────┬──────────┐
    ▼         ▼           ▼          ▼
┌───────┐ ┌────────┐ ┌─────────┐ ┌──────┐
│OpenAI │ │Pinecone│ │PostgreSQL│ │Redis │
│  API  │ │Vector  │ │ Database │ │Cache │
└───────┘ └────────┘ └─────────┘ └──────┘
```

## Component Details

### Frontend (React + TypeScript)
- **Purpose**: User interface for upload, analysis, Q&A
- **Tech**: React, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **State**: React Query for server state
- **Routing**: React Router v6
- **Auth**: JWT stored in localStorage

### Backend (FastAPI)
- **Purpose**: API server, business logic orchestration
- **Tech**: FastAPI, Python 3.11+, async/await
- **Architecture**: Service layer pattern
- **Auth**: JWT with passlib bcrypt

### Document Processing Pipeline
```
PDF Upload
  ↓
Extract Text (PyPDF2/pdfplumber)
  ↓
Parse Structure (regex patterns)
  ↓
Create Chunks (semantic chunking)
  ↓
Generate Embeddings (OpenAI)
  ↓
Store Vectors (Pinecone) + Metadata (PostgreSQL)
  ↓
Anomaly Detection (compare to baseline)
  ↓
Return Results
```

### Vector Database (Pinecone)
- **Purpose**: Semantic search over T&C clauses
- **Strategy**: Dual-namespace approach
  - `user_tcs`: User-uploaded documents
  - `baseline`: 100+ standard T&Cs
- **Index**: 1536 dimensions (OpenAI embeddings), cosine similarity

### Relational Database (PostgreSQL)
- **Purpose**: Store documents, users, anomalies
- **Tables**:
  - `users` - User accounts
  - `documents` - Document metadata
  - `anomalies` - Detected risky clauses
- **ORM**: SQLAlchemy with Alembic migrations

### Cache (Redis)
- **Purpose**: Cache expensive operations
- **Cached Data**:
  - Embeddings (24h TTL)
  - Metadata extractions (1h TTL)
  - Frequent queries (1h TTL)

## Data Flow

### 1. Upload Flow
```python
1. User uploads PDF via frontend
2. Backend saves to temp storage
3. Extract text from PDF
4. Parse into sections/clauses
5. Generate embeddings for each chunk
6. Store in Pinecone (user_tcs namespace)
7. Save metadata to PostgreSQL
8. Run anomaly detection
9. Return analysis results
```

### 2. Q&A Flow
```python
1. User asks question
2. Generate embedding for question
3. Search Pinecone (user_tcs namespace)
4. Retrieve top 5 relevant clauses
5. Build context with citations
6. GPT-4 generates answer
7. Return answer + citations
```

### 3. Anomaly Detection Flow
```python
For each clause:
1. Generate clause embedding
2. Search baseline corpus (Pinecone baseline namespace)
3. Calculate prevalence score
4. Check risk keywords
5. If suspicious:
   - GPT-4 risk assessment
   - Assign severity (low/medium/high)
6. Store anomaly in database
```

## Security

### Authentication & Authorization
- JWT tokens with 30-minute expiration
- Refresh tokens (future enhancement)
- Password hashing with bcrypt
- Role-based access control (RBAC) planned

### API Security
- CORS configured for frontend domain
- Rate limiting on expensive endpoints
- Input validation with Pydantic
- SQL injection prevention (SQLAlchemy ORM)
- File upload validation (PDF only, max size)

### Data Security
- API keys in environment variables
- Encrypted connections (HTTPS in production)
- User data isolation (filter by user_id)
- Regular security audits planned

## Scalability Considerations

### Current (MVP)
- Single-server deployment
- Synchronous processing
- In-memory rate limiting

### Future Enhancements
- Background task processing (Celery)
- Horizontal scaling (load balancer)
- Database read replicas
- CDN for frontend assets
- Distributed caching (Redis Cluster)

## Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Document Upload | < 30s | TBD |
| Q&A Query | < 2s | TBD |
| Anomaly Detection | < 45s | TBD |
| Vector Search | < 500ms | TBD |
```

---

#### `docs/DATA_COLLECTION.md`:
```markdown
# Baseline Corpus Collection Guide

## Overview
The baseline corpus consists of 100+ standard Terms & Conditions documents used for anomaly detection.

## Collection Strategy

### Target Categories
1. **Technology** (20+ docs)
   - Social media: Facebook, Twitter, LinkedIn, Instagram
   - Cloud services: Google, Microsoft, Amazon, Dropbox
   - Developer platforms: GitHub, GitLab, Stack Overflow

2. **E-commerce** (20+ docs)
   - Marketplaces: Amazon, eBay, Etsy
   - Retailers: Walmart, Target, Best Buy
   - Fashion: Nike, Adidas, Zara

3. **SaaS** (20+ docs)
   - Productivity: Slack, Notion, Asana, Trello
   - CRM: Salesforce, HubSpot
   - Communication: Zoom, Microsoft Teams

4. **Finance** (20+ docs)
   - Payments: PayPal, Stripe, Square
   - Banking: Chase, Bank of America
   - Crypto: Coinbase, Binance

5. **General Services** (20+ docs)
   - Ride-sharing: Uber, Lyft
   - Food delivery: DoorDash, Uber Eats
   - Travel: Airbnb, Booking.com

## Collection Process

### Manual Collection
1. Visit company website
2. Navigate to footer → "Terms of Service" or "Terms & Conditions"
3. Save as PDF:
   - Chrome: Print → Save as PDF
   - Firefox: Print → Save to PDF
   - Safari: File → Export as PDF
4. Name file: `{company_name}_tos.pdf` (lowercase, underscores)
5. Place in appropriate category folder

### Automated Collection
Use `scripts/collect_baseline_corpus.py`:
```bash
python scripts/collect_baseline_corpus.py --output data/baseline_corpus
```

**Prerequisites**:
- Install Playwright: `pip install playwright && playwright install`
- Update `BASELINE_SOURCES` dict in script with URLs

## Quality Criteria

### Document Requirements
- ✅ Minimum 2 pages
- ✅ Minimum 500 characters of content
- ✅ Clean text extraction (not scanned images)
- ✅ Recent version (within 2 years)
- ✅ English language

### Validation
Run validation script:
```bash
python scripts/validate_corpus.py
```

Checks:
- Readability
- Text extraction quality
- Duplicate detection
- Metadata completeness

## Indexing

After collection, index documents to Pinecone:
```bash
python scripts/index_baseline_corpus.py
```

**Time**: ~2-3 minutes per document
**Cost**: ~$0.10 per 100 documents (OpenAI embeddings)

## Maintenance

### Quarterly Updates
- Re-collect T&Cs from major companies
- Check for significant changes
- Re-index updated documents

### Expansion
- Add new categories as needed
- Increase diversity (different jurisdictions, industries)
- Target 200+ documents for better anomaly detection
```

---

#### `docs/TROUBLESHOOTING.md`:
```markdown
# Troubleshooting Guide

## Common Issues

### 1. PDF Extraction Returns Empty Text

**Symptoms**: `extracted["text"]` is empty or very short

**Causes**:
- Scanned PDF (images, no text layer)
- Corrupted PDF
- Unsupported encoding

**Solutions**:
```python
# Check extraction method
if extracted["extraction_method"] == "pypdf2":
    # pdfplumber failed, might be problematic PDF
    
# Option 1: Try OCR (for scanned PDFs)
pip install pytesseract
# Implement OCR fallback in document_processor.py

# Option 2: Manual inspection
pdfplumber open <file>.pdf
```

---

### 2. Pinecone Query Returns No Results

**Symptoms**: `results` is empty or has very low scores

**Causes**:
- Wrong namespace
- Document not indexed yet
- Embedding dimension mismatch
- Index empty

**Solutions**:
```python
# Check namespace
print(f"Querying namespace: {namespace}")  # Should match upload

# Check index stats
stats = pinecone_service.index.describe_index_stats()
print(stats)  # Should show vector count

# Verify document was indexed
filter = {"document_id": doc_id}
results = await pinecone_service.query(embedding, namespace, top_k=1, filter=filter)
```

---

### 3. OpenAI Rate Limit Errors

**Symptoms**: `429 Too Many Requests`

**Causes**:
- Too many concurrent requests
- Exceeded quota

**Solutions**:
```python
# Check retry logic is enabled
@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))

# Reduce concurrency
# Use batch operations
embeddings = await openai_service.batch_create_embeddings(texts)

# Check quotas
# Visit https://platform.openai.com/account/limits
```

---

### 4. Database Connection Timeout

**Symptoms**: `sqlalchemy.exc.TimeoutError`

**Causes**:
- Connection pool exhausted
- Long-running queries
- Database overload

**Solutions**:
```python
# Increase pool size (config.py)
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40
)

# Use connection context managers
async with db.begin():
    # Your queries here

# Add indexes to slow queries
# Check PostgreSQL logs for slow queries
```

---

### 5. Frontend Can't Reach Backend

**Symptoms**: Network errors, CORS errors

**Causes**:
- Backend not running
- Wrong URL
- CORS misconfigured

**Solutions**:
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS settings (main.py)
allow_origins=["http://localhost:5173"]  # Must match frontend URL

# Check .env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Performance Issues

### Slow Document Processing

**Target**: < 30s per document

**Optimization**:
```python
# 1. Batch embeddings
embeddings = await openai_service.batch_create_embeddings(texts)

# 2. Use pdfplumber (faster than PyPDF2)
text = await self._extract_with_pdfplumber(pdf_path)

# 3. Parallelize independent operations
import asyncio
results = await asyncio.gather(
    extract_metadata(text),
    generate_embeddings(chunks)
)

# 4. Cache aggressively
# Cache embeddings, metadata extractions
```

### Slow Q&A Queries

**Target**: < 2s

**Optimization**:
```python
# 1. Reduce top_k (less context to process)
top_k=3 instead of 5

# 2. Use GPT-3.5-turbo for simple queries
model=settings.OPENAI_MODEL_GPT35

# 3. Cache common queries
cache_key = f"qa:{doc_id}:{hash(question)}"

# 4. Add Pinecone metadata filters
filter={"section": "Payment Terms"}  # Narrow search space
```

---

## Development Issues

### Alembic Migration Conflicts

**Symptoms**: `alembic upgrade head` fails

**Solutions**:
```bash
# Check current revision
alembic current

# Reset database (⚠️ destructive)
alembic downgrade base
alembic upgrade head

# Or: manually fix migration files
# Edit alembic/versions/<revision>.py
```

### Docker Compose Services Won't Start

**Solutions**:
```bash
# Check logs
docker-compose logs postgres

# Reset volumes
docker-compose down -v
docker-compose up -d

# Check ports not already in use
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
```

---

## Getting Help

1. **Check logs**: Look for error messages and stack traces
2. **Search issues**: Check GitHub issues for similar problems
3. **Ask in Discord**: Join project Discord for real-time help
4. **File a bug**: Create GitHub issue with reproduction steps
```

---

### Documentation Decision Rules

1. **Keep docs updated**: Update when architecture changes
2. **Be specific**: Provide exact commands, not just concepts
3. **Include examples**: Real code snippets, not pseudocode
4. **Version control**: Track major changes in docs/CHANGELOG.md
5. **Link between docs**: Cross-reference related sections

**When Stuck**:
- Read ARCHITECTURE.md for system overview
- Check TROUBLESHOOTING.md for common issues
- Refer to API.md for endpoint details
- Follow DEVELOPMENT.md for setup steps

---

### For MVP:
- Processing time per document (target: < 30s)
- Anomaly detection accuracy (manual review needed)
- API response times (target: < 2s for Q&A)
- Cost per document (OpenAI + Pinecone)

### Use logging:
```python
import time

start = time.time()
await process_document()
duration = time.time() - start

logger.info(f"Document processed", extra={
    "duration": duration,
    "document_id": doc_id
})
```

---

## 🎯 Development Priorities (Next Steps)

### Week 1 Focus:
1. ✅ Create `main.py`, `config.py`, `requirements.txt`
2. ✅ Implement `DocumentProcessor.extract_text()`
3. ✅ Implement `StructureExtractor.extract_structure()`
4. Test with 3-5 sample PDFs
5. Fix any parsing issues

### Week 2 Focus:
1. Implement `LegalChunker.create_chunks()`
2. Set up OpenAI service
3. Test embedding generation
4. Set up Pinecone index
5. Test vector storage

### Week 3 Focus:
1. Implement upload endpoint (full pipeline)
2. Implement query endpoint
3. Test end-to-end Q&A flow
4. Set up database migrations
5. Add authentication

**Current week**: Week 1
**Next file to work on**: `backend/app/main.py`

---

## 💡 Decision Framework (When Stuck)

### Ask yourself:

1. **Does this file already exist?**
   - Yes → Read it first, understand existing structure
   - No → Create following established patterns

2. **Is this following the 10-week timeline?**
   - Yes → Proceed
   - No → Simplify or defer

3. **Does this need external services?**
   - OpenAI → Use retry logic, cache results
   - Pinecone → Batch operations, check namespace
   - Database → Use SQLAlchemy, add indexes

4. **How complex is this feature?**
   - Simple (< 50 lines) → Implement directly
   - Medium (50-200 lines) → Break into functions
   - Complex (> 200 lines) → Break into classes/modules

5. **Can this be tested easily?**
   - Yes → Write test first (TDD)
   - No → Refactor to make testable

6. **Will this scale?**
   - Need caching? → Add Redis
   - Need async? → Use async/await
   - Need batching? → Implement batch operations

7. **Is error handling adequate?**
   - Add try/except blocks
   - Use custom exceptions
   - Log errors with context
   - Return meaningful messages

---

## 🔐 Security Checklist

- [ ] API keys in environment variables (never in code)
- [ ] JWT tokens for authentication
- [ ] Input validation on all endpoints (Pydantic)
- [ ] File upload size limits
- [ ] PDF sanitization (check for malicious content)
- [ ] SQL injection prevention (use ORM)
- [ ] Rate limiting on expensive endpoints
- [ ] HTTPS in production
- [ ] CORS configured correctly

---

## 📦 Deployment Checklist

### Backend (Railway/Render):
- [ ] `requirements.txt` with pinned versions
- [ ] `Procfile`: `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Health check endpoint working
- [ ] Logging configured

### Frontend (Netlify):
- [ ] Build command: `npm run build`
- [ ] Publish directory: `dist`
- [ ] Environment variables (API URL)
- [ ] Redirects for SPA routing: `_redirects` file
- [ ] HTTPS enabled

---

**Remember**: This is a guide, not a rigid spec. Adapt as you learn. Focus on MVP first, then optimize.
