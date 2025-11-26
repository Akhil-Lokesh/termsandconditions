# T&C Analysis Platform - Complete Project State

> **Last Updated:** November 26, 2025
> **Purpose:** This document provides the COMPLETE picture of the project for any AI assistant or developer to understand the current state, make informed changes, and debug issues.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Infrastructure & Deployment](#2-infrastructure--deployment)
3. [Database Schema (Supabase)](#3-database-schema-supabase)
4. [Backend Architecture](#4-backend-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [The 6-Stage Anomaly Detection Pipeline](#6-the-6-stage-anomaly-detection-pipeline)
7. [API Endpoints](#7-api-endpoints)
8. [Environment Variables](#8-environment-variables)
9. [What's Working ✅](#9-whats-working-)
10. [What's NOT Working ❌](#10-whats-not-working-)
11. [Known Bugs & Applied Fixes](#11-known-bugs--applied-fixes)
12. [Common Issues & Solutions](#12-common-issues--solutions)
13. [Making Changes - Workflow](#13-making-changes---workflow)

---

## 1. Project Overview

**T&C Analysis Platform** is a web application that analyzes Terms of Service, Privacy Policies, and other legal documents to detect potentially harmful or unusual clauses.

### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | React + TypeScript + Vite | User interface |
| Backend | FastAPI (Python 3.11) | REST API |
| Database | Supabase (PostgreSQL) | Data persistence |
| Vector DB | Pinecone | Semantic search & embeddings |
| LLM | OpenAI GPT-4 | Risk assessment & metadata extraction |
| Embeddings | OpenAI text-embedding-3-small | Document vectorization |
| Auth | JWT tokens | User authentication |

### Core Features

1. **Document Upload** - PDF parsing, text extraction, clause identification
2. **Anomaly Detection** - 6-stage ML pipeline to identify risky clauses
3. **Q&A Chat** - RAG-based question answering about uploaded documents
4. **Risk Assessment** - Severity scoring and recommendations

---

## 2. Infrastructure & Deployment

### 2.1 Railway (Backend)

- **URL:** `https://termsandconditions-production.up.railway.app`
- **Plan:** Hobby ($5/month)
- **Region:** US West
- **Auto-deploy:** From `main` branch on GitHub
- **Build:** Dockerfile-based (not Nixpacks)

**Railway Environment Variables:** (Set in Railway dashboard)
```
DATABASE_URL=postgresql://postgres.agmxvfkgupflvizimsxw:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://agmxvfkgupflvizimsxw.supabase.co
SUPABASE_ANON_KEY=[ANON_KEY]
SUPABASE_SERVICE_ROLE_KEY=[SERVICE_ROLE_KEY]
OPENAI_API_KEY=[OPENAI_KEY]
PINECONE_API_KEY=[PINECONE_KEY]
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=tc-analysis
JWT_SECRET_KEY=[JWT_SECRET]
ENVIRONMENT=production
```

### 2.2 Vercel (Frontend)

- **URL:** `https://termsandconditions-psi.vercel.app`
- **Framework:** Vite
- **Auto-deploy:** From `main` branch on GitHub
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

**Vercel Environment Variables:**
```
VITE_API_URL=https://termsandconditions-production.up.railway.app
```

### 2.3 Supabase (Database)

- **Project:** tc-analysis-prod
- **Region:** US West 1 (N. California)
- **URL:** `https://agmxvfkgupflvizimsxw.supabase.co`
- **Database Password:** `2ZvhqPbowF1bctBV`
- **Connection Pooler:** `aws-0-us-west-1.pooler.supabase.com:6543`

**Storage Buckets:**
- `documents` - For uploaded PDF files (public access)

### 2.4 Pinecone (Vector Database)

- **Index Name:** `tc-analysis`
- **Environment:** `us-east-1`
- **Dimensions:** 1536 (OpenAI embedding size)
- **Metric:** Cosine similarity
- **Current Vectors:** ~4000+
- **Namespaces:**
  - `baseline` - Reference corpus of standard T&C clauses
  - `user_tcs` - User-uploaded document vectors

### 2.5 GitHub Repository

- **URL:** `https://github.com/Akhil-Lokesh/termsandconditions`
- **Main Branch:** `main`
- **Structure:**
  ```
  /
  ├── backend/           # FastAPI application
  │   ├── app/
  │   │   ├── api/v1/    # API endpoints
  │   │   ├── core/      # Business logic (anomaly detection, etc.)
  │   │   ├── models/    # SQLAlchemy models
  │   │   ├── services/  # External service integrations
  │   │   └── db/        # Database configuration
  │   ├── Dockerfile
  │   ├── requirements.txt
  │   └── railway.json
  └── frontend/          # React application
      ├── src/
      │   ├── components/
      │   ├── pages/
      │   ├── services/  # API client
      │   └── contexts/
      ├── .env.production
      └── package.json
  ```

---

## 3. Database Schema (Supabase)

### 3.1 Tables

#### `users`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `documents`
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    file_size INTEGER,
    mime_type VARCHAR(100),
    page_count INTEGER,
    document_type VARCHAR(100),          -- 'terms_of_service', 'privacy_policy', 'eula', etc.
    company_name VARCHAR(255),
    jurisdiction VARCHAR(255),
    effective_date DATE,
    raw_text TEXT,
    processing_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed', 'anomaly_detection_failed'
    anomaly_count INTEGER DEFAULT 0,
    risk_score FLOAT DEFAULT 0.0,        -- 0-10 scale
    risk_level VARCHAR(50),              -- 'Low', 'Medium', 'High'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `clauses`
```sql
CREATE TABLE clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    section VARCHAR(500),
    subsection VARCHAR(500),             -- Added for detailed structure
    clause_number VARCHAR(100),
    clause_text TEXT NOT NULL,
    level INTEGER,                       -- Nesting level in document
    embedding_id VARCHAR(255),
    pinecone_id VARCHAR(255),            -- Reference to Pinecone vector
    clause_metadata JSONB,               -- Additional metadata as JSON
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `anomalies`
```sql
CREATE TABLE anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    section VARCHAR(500),
    clause_number VARCHAR(100),          -- Added for clause reference
    clause_text TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL,       -- 'low', 'medium', 'high'
    explanation TEXT,
    consumer_impact TEXT,                -- Added: Impact on consumers
    recommendation TEXT,                 -- Added: Recommended action
    risk_category VARCHAR(100),          -- Added: Category of risk
    prevalence FLOAT,                    -- How common this clause is (0-1)
    detected_indicators JSONB,           -- Added: List of detected risk indicators
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `chat_sessions`
```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### `chat_messages`
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,           -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.2 Indexes

```sql
-- Performance indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_clauses_document_id ON clauses(document_id);
CREATE INDEX idx_anomalies_document_id ON anomalies(document_id);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_document_id ON chat_sessions(document_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
```

### 3.3 RLS Policies

Row Level Security is enabled. Users can only access their own data:

```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomalies ENABLE ROW LEVEL SECURITY;

-- Policies (example for documents)
CREATE POLICY "Users can view own documents" ON documents
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own documents" ON documents
    FOR INSERT WITH CHECK (auth.uid() = user_id);
```

### 3.4 Adding New Columns

When you need to add columns to existing tables, use the Supabase SQL Editor:

```sql
-- Example: Adding a new column
ALTER TABLE table_name 
ADD COLUMN IF NOT EXISTS column_name DATA_TYPE;

-- Example with JSONB
ALTER TABLE anomalies 
ADD COLUMN IF NOT EXISTS detected_indicators JSONB;
```

---

## 4. Backend Architecture

### 4.1 Directory Structure

```
backend/app/
├── __init__.py
├── main.py                    # FastAPI app initialization
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── auth.py            # Authentication endpoints
│       ├── upload.py          # Document upload & processing
│       ├── documents.py       # Document CRUD
│       ├── anomalies.py       # Anomaly retrieval
│       ├── chat.py            # Q&A chat endpoints
│       └── users.py           # User management
├── core/
│   ├── anomaly_detector.py    # Main 6-stage pipeline (88KB, 2000+ lines)
│   ├── document_processor.py  # PDF text extraction
│   ├── document_type_detector.py
│   ├── legal_chunker.py       # Semantic chunking
│   ├── metadata_extractor.py  # GPT-4 metadata extraction
│   ├── prevalence_calculator.py
│   ├── risk_assessor.py       # GPT-4 risk assessment
│   ├── structure_extractor.py # Clause identification
│   │
│   │ # Stage 1: Multi-Method Detection
│   ├── semantic_risk_detector.py
│   ├── statistical_outlier_detector.py
│   ├── semantic_anomaly_detector.py
│   │
│   │ # Stage 2: Context Filtering
│   ├── industry_baseline_filter.py
│   ├── service_type_context_filter.py
│   ├── temporal_context_filter.py
│   │
│   │ # Stage 3: Clustering
│   ├── anomaly_clusterer.py
│   │
│   │ # Stage 4: Compound Risk
│   ├── compound_risk_detector.py
│   │
│   │ # Stage 5: Calibration
│   ├── confidence_calibrator.py
│   ├── active_learning_manager.py
│   │
│   │ # Stage 6: Alert Ranking
│   └── alert_ranker.py
├── models/
│   ├── user.py
│   ├── document.py
│   ├── clause.py
│   └── anomaly.py
├── services/
│   ├── openai_service.py      # OpenAI API wrapper
│   ├── pinecone_service.py    # Pinecone API wrapper
│   ├── cache_service.py       # Redis (optional)
│   └── analysis_cache_manager.py
└── db/
    ├── session.py             # SQLAlchemy session
    └── base.py
```

### 4.2 Key Services

#### OpenAI Service (`services/openai_service.py`)
- Embeddings: `text-embedding-3-small` (1536 dimensions)
- Chat: `gpt-4` for risk assessment and metadata extraction
- Batch processing for efficiency

#### Pinecone Service (`services/pinecone_service.py`)
- Index: `tc-analysis`
- Namespaces: `baseline` (reference corpus), `user_tcs` (user documents)
- Operations: upsert, query, delete

### 4.3 Document Processing Flow

```
1. Upload PDF
   ↓
2. Extract text (pdfplumber primary, PyPDF2 fallback)
   ↓
3. Detect document type (privacy_policy, terms_of_service, eula, etc.)
   ↓
4. Extract structure (sections → clauses)
   ↓
5. Create semantic chunks
   ↓
6. Generate embeddings (OpenAI)
   ↓
7. Extract metadata (company, jurisdiction, dates via GPT-4)
   ↓
8. Store vectors in Pinecone
   ↓
9. Save to database (document + clauses)
   ↓
10. Schedule background anomaly detection
```

---

## 5. Frontend Architecture

### 5.1 Key Files

```
frontend/src/
├── App.tsx                    # Main app with routing
├── main.tsx                   # Entry point
├── services/
│   └── api.ts                 # Axios API client (IMPORTANT)
├── pages/
│   ├── Dashboard.tsx
│   ├── DocumentView.tsx
│   ├── Upload.tsx
│   ├── Login.tsx
│   └── Register.tsx
├── components/
│   ├── DocumentList.tsx
│   ├── AnomalyList.tsx
│   ├── ChatInterface.tsx
│   └── RiskScore.tsx
└── contexts/
    └── AuthContext.tsx
```

### 5.2 API Client (`services/api.ts`)

**CRITICAL:** The API client has specific handling for FormData uploads:

```typescript
// Request interceptor removes Content-Type for FormData
// This allows browser to set proper multipart/form-data boundary
this.client.interceptors.request.use(
  (config) => {
    if (config.data instanceof FormData && config.headers) {
      delete config.headers['Content-Type'];
    }
    return config;
  }
);
```

---

## 6. The 6-Stage Anomaly Detection Pipeline

This is the core ML pipeline in `backend/app/core/anomaly_detector.py` (88KB, 2000+ lines).

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANOMALY DETECTION PIPELINE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Stage 1: Multi-Method Detection                                 │
│  ├── Pattern Detection (40% weight) - Keyword matching           │
│  ├── Semantic Detection (35% weight) - Embedding similarity      │
│  └── Statistical Detection (25% weight) - Outlier detection      │
│                           ↓                                      │
│  Stage 2: Context Filtering                                      │
│  ├── Industry Baseline Filter - Compare to industry norms        │
│  ├── Service Type Filter - Adjust for service category           │
│  └── Temporal Filter - Consider document age/updates             │
│                           ↓                                      │
│  Stage 3: Clustering & Deduplication                             │
│  └── Group similar anomalies, select representatives             │
│                           ↓                                      │
│  Stage 4: Compound Risk Detection                                │
│  └── Detect systemic patterns (6 compound risk types)            │
│                           ↓                                      │
│  Stage 5: Confidence Calibration                                 │
│  ├── Isotonic regression calibration                             │
│  └── Active learning feedback integration                        │
│                           ↓                                      │
│  Stage 6: Alert Ranking & Budget                                 │
│  └── Rank by severity, limit to MAX_ALERTS=10                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Stage Details

#### Stage 1: Multi-Method Detection
- **Pattern Detection:** Regex patterns for risky terms (arbitration, liability waiver, etc.)
- **Semantic Detection:** Uses sentence-transformers to find semantically similar risky clauses
- **Statistical Detection:** IsolationForest outlier detection on embeddings

#### Stage 2: Context Filtering
- Filters based on industry (SaaS, fintech, healthcare, etc.)
- Adjusts thresholds based on service type
- Considers document age (newer = more relevant)

#### Stage 3: Clustering
- Uses HDBSCAN or DBSCAN clustering
- Groups similar anomalies
- Selects representative from each cluster
- **CURRENT ISSUE:** Requires `sentence-transformers` which is not installed

#### Stage 4: Compound Risk Detection
Detects 6 systemic patterns:
1. Liability Shield Pattern
2. Data Exploitation Pattern
3. Exit Barrier Pattern
4. Unilateral Control Pattern
5. Consumer Rights Waiver Pattern
6. Hidden Costs Pattern

#### Stage 5: Confidence Calibration
- Isotonic regression for probability calibration
- Active learning manager for user feedback
- **CURRENT STATUS:** Calibrator not fitted (needs training data)

#### Stage 6: Alert Ranking
- Ranks anomalies by composite score
- Limits output to MAX_ALERTS=10
- Categorizes: HIGH, MEDIUM, LOW confidence

### Pipeline Return Format

The `detect_anomalies()` method returns a dict (NOT a list):

```python
{
    'document_id': 'uuid',
    'company_name': 'string',
    'analysis_date': 'ISO datetime',
    'overall_risk_score': float,  # 0-10
    'high_severity_alerts': [...],    # List of anomaly dicts
    'medium_severity_alerts': [...],
    'low_severity_alerts': [...],
    'suppressed_alerts_count': int,
    'total_anomalies_detected': int,
    'total_alerts_shown': int,
    'compound_risks': [...],
    'ranking_metadata': {...},
    'pipeline_performance': {
        'stage1_detections': int,
        'stage2_filtered': int,
        'stage3_clustered': int,
        'stage4_compounds': int,
        'stage5_calibrated': int,
        'stage6_ranked': int,
        'total_clauses_analyzed': int,
        'total_processing_time_ms': float
    }
}
```

---

## 7. API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create new user |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/auth/me` | Get current user |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/` | Upload document (multipart/form-data) |
| GET | `/api/v1/documents/` | List user's documents |
| GET | `/api/v1/documents/{id}` | Get document details |
| DELETE | `/api/v1/documents/{id}` | Delete document |

### Anomalies
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/anomalies/{document_id}` | Get anomalies for document |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/sessions` | Create chat session |
| GET | `/api/v1/chat/sessions` | List chat sessions |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message |
| GET | `/api/v1/chat/sessions/{id}/messages` | Get chat history |

---

## 8. Environment Variables

### Backend (Railway)

```env
# Database
DATABASE_URL=postgresql://postgres.agmxvfkgupflvizimsxw:[PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres

# Supabase
SUPABASE_URL=https://agmxvfkgupflvizimsxw.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI
OPENAI_API_KEY=sk-...

# Pinecone
PINECONE_API_KEY=pcsk_...
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=tc-analysis

# Auth
JWT_SECRET_KEY=[random-secret]
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=production
```

### Frontend (Vercel)

```env
VITE_API_URL=https://termsandconditions-production.up.railway.app
```

---

## 9. What's Working ✅

### Infrastructure
- ✅ Railway deployment (auto-deploy from main)
- ✅ Vercel deployment (auto-deploy from main)
- ✅ Supabase database connection
- ✅ Pinecone vector database
- ✅ OpenAI API integration

### Features
- ✅ User registration and login
- ✅ JWT authentication
- ✅ Document upload (PDF)
- ✅ Text extraction (pdfplumber)
- ✅ Document type detection
- ✅ Structure extraction (sections, clauses)
- ✅ Semantic chunking
- ✅ Embedding generation
- ✅ Metadata extraction (GPT-4)
- ✅ Vector storage in Pinecone
- ✅ Database persistence (documents, clauses)
- ✅ Document listing
- ✅ Background task scheduling

### Anomaly Detection Pipeline
- ✅ Stage 1: Pattern detection working
- ✅ Stage 2: Context filtering working (partial)
- ✅ Stage 3: Passes through (clustering disabled)
- ✅ Stage 4: Compound risk detection working
- ✅ Stage 5: Calibration passes (uncalibrated)
- ✅ Stage 6: Alert ranking working
- ✅ Pipeline completes and returns results

---

## 10. What's NOT Working ❌

### Critical Issues

1. **❌ Anomalies Not Saving to Database**
   - Pipeline completes successfully
   - Returns 4 anomalies
   - But database save fails with type error
   - **Root Cause:** `detect_anomalies()` returns dict, code expected list
   - **Status:** FIX DEPLOYED (commit 7bbc899) - NEEDS TESTING

2. **❌ Semantic Anomaly Detection Disabled**
   ```
   WARNING - sentence-transformers not available
   ```
   - Package not installed (too heavy for Railway)
   - Stage 1 semantic detection falls back to keyword-only

3. **❌ Anomaly Clusterer Disabled**
   ```
   ERROR - Failed to load SentenceTransformer: No module named 'sentence_transformers'
   ```
   - Stage 3 clustering skipped
   - All anomalies pass through without deduplication

4. **❌ Industry Baseline Filter Fails**
   ```
   WARNING - Failed to initialize industry filter: IndustryBaselineFilter.__init__() 
   got an unexpected keyword argument 'pinecone_index'
   ```
   - Constructor signature mismatch
   - Stage 2 industry filtering not working

5. **❌ Confidence Calibrator Not Fitted**
   ```
   WARNING - Calibrator not fitted, returning raw confidence
   ```
   - Needs training data from user feedback
   - Currently returns uncalibrated confidence scores

### Non-Critical Issues

6. **⚠️ Redis Not Connected**
   ```
   WARNING - Continuing without cache (degraded performance)
   ```
   - Redis not provisioned on Railway
   - Caching disabled, slightly slower performance

7. **⚠️ Section Names Missing**
   - Many clauses show as "Unknown Section"
   - Structure extractor not parsing headings correctly

8. **⚠️ Frontend Checks Too Early**
   - User sees "0 anomalies" while pipeline runs
   - No loading indicator or polling

---

## 11. Known Bugs & Applied Fixes

### Fix 1: FormData Upload (Commit c98f6f1)
**Problem:** File uploads showed 0.00MB - content not sent
**Cause:** Axios had default `Content-Type: application/json` which prevented browser from setting multipart boundary
**Solution:** Request interceptor removes Content-Type for FormData

### Fix 2: Database Schema Mismatch
**Problem:** `column "clause_metadata" does not exist`
**Solution:** Added columns via SQL Editor:
```sql
ALTER TABLE clauses 
ADD COLUMN IF NOT EXISTS clause_metadata JSONB,
ADD COLUMN IF NOT EXISTS pinecone_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS subsection VARCHAR(500),
ADD COLUMN IF NOT EXISTS level INTEGER;

ALTER TABLE anomalies 
ADD COLUMN IF NOT EXISTS clause_number VARCHAR(100),
ADD COLUMN IF NOT EXISTS consumer_impact TEXT,
ADD COLUMN IF NOT EXISTS recommendation TEXT,
ADD COLUMN IF NOT EXISTS risk_category VARCHAR(100),
ADD COLUMN IF NOT EXISTS prevalence FLOAT,
ADD COLUMN IF NOT EXISTS detected_indicators JSONB;
```

### Fix 3: Background Task DB Session (Commit ef3ef5d)
**Problem:** Background task used stale DB session from request
**Cause:** FastAPI background tasks run after request completes
**Solution:** Background task creates its own SessionLocal()

### Fix 4: Pipeline Return Format (Commit 7bbc899)
**Problem:** `TypeError: string indices must be integers, not 'str'`
**Cause:** `detect_anomalies()` returns dict, code treated it as list
**Solution:** Extract anomalies from `high_severity_alerts` + `medium_severity_alerts` + `low_severity_alerts`

### Fix 5: HTTPS Enforcement (Commit d22bce9)
**Problem:** Mixed content errors in production
**Solution:** Force HTTPS for API URL in production

---

## 12. Common Issues & Solutions

### Issue: Document upload fails with "Failed to extract text"
**Check:**
1. File is valid PDF
2. PDF has extractable text (not scanned image)
3. File size < 10MB

### Issue: Anomalies endpoint returns empty array
**Check:**
1. Wait 2-3 minutes for background task to complete
2. Check Railway logs for "ANOMALY DETECTION PIPELINE COMPLETE"
3. Check for errors in logs after pipeline completion

### Issue: 500 errors with CORS
**Check:**
1. Request includes proper headers
2. Backend CORS config allows frontend origin
3. Check Railway logs for actual error

### Issue: Database connection fails
**Check:**
1. DATABASE_URL uses connection pooler (port 6543)
2. Password is correct
3. IP not blocked (Railway uses IPv4)

### Issue: Pinecone errors
**Check:**
1. Index exists and is ready
2. API key has access
3. Dimension matches (1536 for OpenAI)

---

## 13. Making Changes - Workflow

### Backend Changes

1. **Edit files locally** in `/Users/akhil/Desktop/Project T&C/backend/`

2. **Test locally** (optional):
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

3. **Commit and push:**
   ```bash
   git add -A
   git commit -m "Description of change"
   git push origin main
   ```

4. **Railway auto-deploys** - check logs in Railway dashboard

### Frontend Changes

1. **Edit files** in `/Users/akhil/Desktop/Project T&C/frontend/`

2. **Test locally:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Commit and push** - Vercel auto-deploys

### Database Changes

1. **Go to Supabase SQL Editor:**
   `https://supabase.com/dashboard/project/agmxvfkgupflvizimsxw/sql`

2. **Run SQL commands** (always use `IF NOT EXISTS` for safety)

3. **Update SQLAlchemy models** to match schema

### Adding New Dependencies

**Backend:**
1. Add to `requirements.txt`
2. Note: Heavy ML packages may fail on Railway (limited memory)

**Frontend:**
1. `npm install package-name`
2. Update `package.json`

---

## Quick Reference

### URLs
- **Frontend:** https://termsandconditions-psi.vercel.app
- **Backend:** https://termsandconditions-production.up.railway.app
- **API Health:** https://termsandconditions-production.up.railway.app/health
- **Supabase:** https://supabase.com/dashboard/project/agmxvfkgupflvizimsxw
- **Railway:** https://railway.app (proactive-courtesy project)
- **GitHub:** https://github.com/Akhil-Lokesh/termsandconditions

### Key Commands
```bash
# Deploy backend
cd "/Users/akhil/Desktop/Project T&C"
git add -A && git commit -m "message" && git push origin main

# Check Railway logs
# Go to Railway dashboard → Logs tab

# Test API
curl https://termsandconditions-production.up.railway.app/health
```

---

## Next Steps (Priority Order)

1. **Verify anomaly saving works** - Upload document and check database
2. **Fix IndustryBaselineFilter** - Constructor argument mismatch
3. **Add loading indicator** - Show user that anomaly detection is in progress
4. **Consider sentence-transformers alternative** - Lighter weight model for semantic detection
5. **Add Redis** (optional) - For caching and performance

---

*This document should be updated whenever significant changes are made to the project.*
