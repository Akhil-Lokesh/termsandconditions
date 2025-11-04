# System Architecture

## Overview

The T&C Analysis System is a specialized RAG (Retrieval-Augmented Generation) application designed for analyzing Terms & Conditions documents. It uses a dual-namespace vector database strategy to compare user-uploaded T&Cs against a baseline corpus of 100+ standard T&Cs.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Netlify)                │
│  • Upload Interface                                          │
│  • Q&A Chat Interface                                        │
│  • Anomaly Report Viewer                                     │
│  • Comparison Tool                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (HTTPS)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND API (FastAPI)                      │
│  • POST /api/upload          - Upload T&C PDF               │
│  • GET  /api/analyze/:id     - Get analysis results         │
│  • POST /api/query           - Ask questions about T&C      │
│  • GET  /api/anomalies/:id   - Get anomaly report          │
│  • POST /api/compare         - Compare multiple T&Cs        │
└──────────┬──────────────────┬──────────────────┬───────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Document         │ │ Vector Database  │ │  OpenAI API      │
│ Processor        │ │  (Pinecone)      │ │                  │
│                  │ │                  │ │  Models:         │
│ • PDF Extraction │ │ TWO NAMESPACES:  │ │  • GPT-4         │
│ • Structure      │ │                  │ │  • GPT-3.5       │
│   Parsing        │ │ 1. user_tcs      │ │  • text-embed-3  │
│ • Legal Chunking │ │    (uploaded)    │ │                  │
│ • Metadata       │ │                  │ │  Uses:           │
│   Extraction     │ │ 2. baseline      │ │  • Classification│
│                  │ │    (100+ std)    │ │  • Risk Analysis │
└──────────────────┘ │                  │ │  • Q&A Generation│
                     │  Stores:         │ └──────────────────┘
                     │  • Embeddings    │
                     │  • Metadata      │
                     │  • Clause Info   │
                     └──────────────────┘
                              │
                              ▼
                     ┌──────────────────┐
                     │   PostgreSQL     │
                     │  • documents     │
                     │  • clauses       │
                     │  • anomalies     │
                     │  • users         │
                     └──────────────────┘
```

## Core Components

### 1. Document Processing Pipeline

**File**: `backend/app/core/document_processor.py`

Handles PDF extraction and initial processing:

```python
1. Upload PDF → Validate file type/size
2. Extract text using pdfplumber
3. Detect if it's a T&C document
4. Extract metadata (company name, effective date)
5. Pass to Structure Extractor
```

**Key Methods**:
- `process_document()` - Main entry point
- `_extract_text_pdfplumber()` - Text extraction
- `_is_tc_document()` - T&C validation
- `_extract_company_name()` - Company detection

### 2. Structure Extractor

**File**: `backend/app/core/structure_extractor.py`

Extracts legal structure from raw text:

```python
1. Try multiple section patterns:
   - "Section 1: Title"
   - "1. Title"
   - "Article I: Title"
2. Extract sections with titles
3. Parse clauses within sections (8.1, 8.2, 8.3)
4. Build hierarchical structure
```

**Key Methods**:
- `extract_structure()` - Main extraction
- `_extract_sections_with_pattern()` - Pattern matching
- `_extract_clauses()` - Clause parsing

### 3. Legal-Aware Chunker

**File**: `backend/app/core/legal_chunker.py`

Creates semantically meaningful chunks:

```python
For each clause:
    chunk = f"""
    Section {section_num}: {section_title}
    
    {clause_id}. {clause_text}
    
    [Context: This is clause {clause_id} from {section_title}]
    """
```

**Key Feature**: Never breaks clauses mid-sentence, preserves legal context.

### 4. Metadata Extractor

**File**: `backend/app/core/metadata_extractor.py`

Uses GPT-4 to extract structured metadata:

```python
For each clause:
    Extract:
    - clause_type (payment/privacy/liability/etc)
    - entities (time periods, amounts, parties)
    - risk_indicators (waive, binding, no refund)
    - user_obligations
    - company_rights
```

**API Strategy**: One GPT-4 call per clause with JSON response format.

### 5. Anomaly Detector

**File**: `backend/app/core/anomaly_detector.py`

Core anomaly detection logic:

```python
def detect_anomaly(clause):
    # Step 1: Query baseline corpus
    similar = pinecone.query(
        embedding=embed(clause),
        namespace="baseline_corpus",
        top_k=50
    )
    
    # Step 2: Calculate prevalence
    prevalence = count_similar(similar) / 100
    
    # Step 3: Check if unusual (<30%)
    if prevalence < 0.30 or has_risk_indicators(clause):
        # Step 4: GPT-4 risk assessment
        risk = assess_with_gpt4(clause, prevalence)
        return create_anomaly_record(risk)
```

**Key Components**:
- Prevalence calculation
- Risk indicator detection
- GPT-4 risk assessment
- Report generation

### 6. Vector Database Strategy

**Service**: `backend/app/services/pinecone_service.py`

**Two Namespaces**:

1. **`user_tcs`**: User-uploaded documents
   - Indexed after processing
   - Used for Q&A retrieval
   - Per-user/per-document

2. **`baseline_corpus`**: 100+ standard T&Cs
   - Pre-indexed (one-time setup)
   - Used for anomaly detection
   - Shared across all users

**Key Operations**:
- `upsert_document()` - Store clauses
- `search()` - Semantic search
- `delete_document()` - Cleanup

### 7. OpenAI Service

**File**: `backend/app/services/openai_service.py`

Wraps all OpenAI API calls:

```python
- create_embedding(text) → vector
- generate_qa_response(question, context) → answer
- classify_clause(clause) → metadata
- assess_risk(clause, prevalence) → risk_level
```

**Features**:
- Retry logic with exponential backoff
- Error handling
- Rate limit management
- Cost tracking (optional)

## Data Flow

### Upload Flow

```
1. User uploads PDF
   ↓
2. Document Processor extracts text
   ↓
3. Structure Extractor parses sections/clauses
   ↓
4. Legal Chunker creates chunks
   ↓
5. Metadata Extractor enriches each clause
   ↓
6. Generate embeddings (OpenAI)
   ↓
7. Store in Pinecone (user_tcs namespace)
   ↓
8. Store metadata in PostgreSQL
   ↓
9. Anomaly Detector runs:
   - Query baseline corpus
   - Calculate prevalence
   - Assess risk
   - Generate report
   ↓
10. Return document_id to user
```

### Query Flow

```
1. User asks question
   ↓
2. Check Redis cache
   ↓
3. Generate query embedding
   ↓
4. Search Pinecone (user_tcs namespace)
   ↓
5. Retrieve top-k clauses
   ↓
6. Check for anomalies in retrieved clauses
   ↓
7. Generate answer with GPT-4:
   - Context: retrieved clauses
   - Anomalies: detected risks
   - System prompt: T&C analyst
   ↓
8. Format response with:
   - Direct answer
   - Explanation
   - Risk warnings
   - Section citations
   ↓
9. Cache response in Redis
   ↓
10. Return to user
```

### Anomaly Detection Flow

```
For each clause in document:
    ↓
1. Query baseline corpus (Pinecone)
   Filter: same clause_type
   Top-K: 50 similar clauses
   ↓
2. Calculate prevalence
   Count: similarity > 0.85
   Prevalence = count / 100
   ↓
3. Check risk indicators
   Keywords: waive, binding, etc.
   ↓
4. If unusual OR risky:
   ↓
5. GPT-4 risk assessment:
   Input: clause + prevalence
   Output: risk_level + explanation
   ↓
6. If risk_level in [high, medium]:
   Create anomaly record
   ↓
7. Store in PostgreSQL
```

## Database Schema

### documents
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(255),
    company_name VARCHAR(255),
    effective_date TIMESTAMP,
    num_sections INTEGER,
    num_clauses INTEGER,
    processing_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### clauses
```sql
CREATE TABLE clauses (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    clause_id VARCHAR(50),
    section_title VARCHAR(255),
    clause_text TEXT,
    clause_type VARCHAR(50),
    metadata JSONB,
    pinecone_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### anomalies
```sql
CREATE TABLE anomalies (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    clause_id INTEGER REFERENCES clauses(id) ON DELETE CASCADE,
    risk_level VARCHAR(20),
    prevalence FLOAT,
    explanation TEXT,
    affected_rights JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Caching Strategy

**Service**: `backend/app/services/cache_service.py`

### What to Cache

1. **Query Responses** (TTL: 30 days)
   - Key: `query:{document_id}:{question_hash}`
   - Value: Full QueryResponse JSON

2. **Embeddings** (TTL: 90 days)
   - Key: `embed:{text_hash}`
   - Value: Vector array

3. **Analysis Results** (TTL: 30 days)
   - Key: `analysis:{document_id}`
   - Value: Complete analysis JSON

### Cache Invalidation

- Document deleted → Delete all keys with `document_id`
- Document reprocessed → Delete `analysis:{document_id}`
- Manual: Provide admin endpoint

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login (returns JWT)

### Document Operations
- `POST /api/v1/upload` - Upload T&C PDF
- `GET /api/v1/upload/{document_id}` - Get document metadata

### Analysis
- `GET /api/v1/anomalies/{document_id}` - Get anomaly report
- `POST /api/v1/compare` - Compare multiple T&Cs

### Q&A
- `POST /api/v1/query` - Ask question about document

## Security

### Authentication
- JWT tokens with HS256 algorithm
- 30-minute token expiration
- Refresh token support (optional)

### Authorization
- Users can only access their own documents
- Document ownership verified on every request

### Rate Limiting
- 100 requests per hour per user
- Implemented with slowapi

### Input Validation
- File type validation (PDF only)
- File size limit (10MB)
- Query length limits
- SQL injection prevention (SQLAlchemy)
- XSS prevention (Pydantic validation)

## Deployment Architecture

### Development
```
Local Machine:
- Backend: uvicorn on localhost:8000
- Frontend: Vite dev server on localhost:5173
- Services: Docker Compose (PostgreSQL + Redis)
```

### Production
```
Frontend (Netlify):
- Static React build
- CDN distribution
- HTTPS enabled

Backend (Railway/Render):
- Docker container
- Auto-scaling
- HTTPS enabled
- Environment variables

Database (Managed):
- PostgreSQL (Railway/Render)
- Redis (Upstash/Redis Cloud)

Vector DB:
- Pinecone (managed service)
```

## Performance Considerations

### Document Processing
- **Target**: <30 seconds per T&C
- **Optimization**: Parallel clause processing
- **Monitoring**: Log processing times

### Query Response
- **Target**: <3 seconds
- **Optimization**: Redis caching
- **Monitoring**: Track cache hit rate

### Anomaly Detection
- **Target**: <60 seconds per document
- **Optimization**: Batch Pinecone queries
- **Monitoring**: Track detection accuracy

### Cost Optimization
- Cache embeddings (expensive)
- Use GPT-3.5 for development
- Limit GPT-4 calls to production
- Monitor OpenAI API usage

## Monitoring & Logging

### Logging Strategy
- Structured logging with Python `logging` module
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log to file + stdout

### Key Metrics
- Document processing time
- Query response time
- Cache hit rate
- API error rate
- OpenAI API costs

### Error Tracking
- Sentry integration (optional)
- Email alerts for critical errors
- Error dashboard in admin panel

## Development Timeline

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed phase breakdown.

**Summary**:
- Phase 1 (Weeks 1-3): Foundation & Basic RAG
- Phase 2 (Weeks 4-5): T&C Specialization
- Phase 3 (Weeks 6-7): Anomaly Detection
- Phase 4 (Weeks 8-10): Frontend & Deployment
