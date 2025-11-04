# Week 3-5 Completion Guide

**Status**: In Progress
**Target**: Complete all API endpoints, testing, and Week 5 deliverables

---

## 🎯 Overview

This guide provides step-by-step instructions to complete Weeks 3-5 with perfection:

- **Week 3**: Complete all API endpoints (upload ✓, query, auth, anomalies, compare)
- **Week 4**: Full integration testing and anomaly detection refinement
- **Week 5**: Comprehensive testing, error handling, and validation

---

## ✅ Week 3: API Endpoints - COMPLETION STATUS

### 1. Upload Endpoint ✅ COMPLETE
**File**: `backend/app/api/v1/upload.py`

**Status**: ✅ Fully implemented with:
- Complete processing pipeline (8 steps)
- Text extraction (pdfplumber + PyPDF2 fallback)
- Structure extraction
- Embedding generation
- Metadata extraction
- Pinecone storage
- Anomaly detection
- Comprehensive error handling
- OpenAPI documentation

**Endpoints**:
- `POST /api/v1/upload` - Upload document
- `GET /api/v1/upload` - List documents
- `GET /api/v1/upload/{id}` - Get document details
- `DELETE /api/v1/upload/{id}` - Delete document

---

### 2. Query Endpoint ⚠️ NEEDS COMPLETION
**File**: `backend/app/api/v1/query.py`

**Current Status**: Skeleton exists, needs full RAG implementation

**Required Changes**:

```python
# backend/app/api/v1/query.py

"""
Q&A query endpoints with RAG implementation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_openai_service,
    get_pinecone_service,
    get_cache_service,
)
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.schemas.query import QueryRequest, QueryResponse, Citation
from app.services.openai_service import OpenAIService
from app.services.pinecone_service import PineconeService
from app.services.cache_service import CacheService
from app.prompts.qa_prompts import QA_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Ask Question About Document",
    description="""
    Ask a question about a T&C document and receive an answer with citations.

    **Pipeline:**
    1. Generate embedding for question
    2. Search Pinecone for relevant clauses (top 5)
    3. Build context with citations
    4. Generate answer with GPT-4
    5. Return answer with source citations and confidence score

    **Example Questions:**
    - "What is the refund policy?"
    - "Can the company change the terms without notice?"
    - "What personal data is collected?"
    """,
)
async def query_document(
    request: Request,
    query_data: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    openai_service: OpenAIService = Depends(get_openai_service),
    pinecone_service: PineconeService = Depends(get_pinecone_service),
    cache_service: CacheService = Depends(get_cache_service),
):
    """
    Ask a question about a document and get an AI-generated answer with citations.
    """
    logger.info(f"Query from {current_user.email}: {query_data.question[:100]}")

    # Verify document exists and user has access
    document = db.query(Document).filter(
        Document.id == query_data.document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {query_data.document_id}",
        )

    # Check cache first (optional)
    cache_key = f"query:{query_data.document_id}:{hash(query_data.question)}"
    if cache_service:
        cached = await cache_service.get(cache_key)
        if cached:
            logger.info("Returning cached query response")
            return QueryResponse(**cached)

    try:
        # Step 1: Generate question embedding
        question_embedding = await openai_service.create_embedding(query_data.question)

        logger.info(f"Generated embedding for question")

        # Step 2: Search Pinecone for relevant clauses
        results = await pinecone_service.query(
            query_embedding=question_embedding,
            namespace=settings.PINECONE_USER_NAMESPACE,
            top_k=5,
            filter={"document_id": query_data.document_id},
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant clauses found in document. Try rephrasing your question.",
            )

        logger.info(f"Found {len(results)} relevant clauses")

        # Step 3: Build context from retrieved clauses
        context_parts = []
        citations = []

        for idx, match in enumerate(results):
            metadata = match["metadata"]
            context_parts.append(
                f"[{idx + 1}] Section: {metadata['section']}, "
                f"Clause: {metadata.get('clause_number', 'N/A')}\n"
                f"{metadata['text']}"
            )

            citations.append(
                Citation(
                    index=idx + 1,
                    section=metadata["section"],
                    clause_number=metadata.get("clause_number", ""),
                    text=metadata["text"][:300],  # Preview only
                    relevance_score=match["score"],
                )
            )

        context = "\n\n".join(context_parts)

        # Step 4: Generate answer with GPT-4
        prompt = QA_SYSTEM_PROMPT.format(
            context=context,
            question=query_data.question,
        )

        answer = await openai_service.create_completion(
            prompt=prompt,
            model=settings.OPENAI_MODEL_GPT4,
            temperature=0.0,
            max_tokens=500,
        )

        logger.info("Answer generated successfully")

        # Step 5: Build response
        response = QueryResponse(
            question=query_data.question,
            answer=answer,
            citations=citations,
            confidence=results[0]["score"] if results else 0.0,
        )

        # Cache response (optional)
        if cache_service:
            await cache_service.set(cache_key, response.dict(), ttl=3600)  # 1 hour

        return response

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}",
        )
```

**Test**:
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "<doc_id>",
    "question": "What is the refund policy?"
  }'
```

---

### 3. Auth Endpoint ⚠️ NEEDS COMPLETION
**File**: `backend/app/api/v1/auth.py`

**Current Status**: Basic structure, needs JWT implementation

**Required Implementation**:

```python
# backend/app/api/v1/auth.py

"""
Authentication endpoints.

Provides user registration, login, and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.api.deps import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Create a new user account.",
)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password strength (basic)
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Login with email and password to receive access token.",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login and receive JWT access token.

    **Note**: username field should contain email address.
    """
    # Find user by email (form_data.username contains email)
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires,
    )

    logger.info(f"User logged in: {user.email}")

    return Token(
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh Token",
    description="Refresh access token (future enhancement).",
)
async def refresh_token():
    """
    Refresh access token.

    **Note**: Not yet implemented. Use login to get new token.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh not yet implemented. Please login again.",
    )
```

**Test**:
```bash
# Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword",
    "full_name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=securepassword"
```

---

### 4. Anomalies Endpoint ⚠️ NEEDS COMPLETION
**File**: `backend/app/api/v1/anomalies.py`

**Required Implementation**:

```python
# backend/app/api/v1/anomalies.py

"""
Anomaly detection endpoints.

Provides access to detected anomalies with filtering and details.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.document import Document
from app.models.anomaly import Anomaly
from app.schemas.anomaly import AnomalyResponse, AnomalyListResponse, AnomalyStats

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{document_id}",
    response_model=AnomalyListResponse,
    summary="Get Document Anomalies",
    description="Retrieve all anomalies detected in a document with optional filtering.",
)
async def get_anomalies(
    document_id: str,
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high"),
    section: Optional[str] = Query(None, description="Filter by section name"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all anomalies for a document with optional filters.
    """
    # Verify document access
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    # Build query
    query = db.query(Anomaly).filter(Anomaly.document_id == document_id)

    # Apply filters
    if severity:
        query = query.filter(Anomaly.severity == severity.lower())

    if section:
        query = query.filter(Anomaly.section.ilike(f"%{section}%"))

    # Get total count
    total = query.count()

    # Get anomalies with pagination
    anomalies = query.order_by(
        Anomaly.severity.desc(),  # High severity first
        Anomaly.prevalence.asc(),  # Rarest first
    ).offset(skip).limit(limit).all()

    # Calculate stats
    stats = db.query(
        Anomaly.severity,
        db.func.count(Anomaly.id).label("count")
    ).filter(
        Anomaly.document_id == document_id
    ).group_by(Anomaly.severity).all()

    severity_counts = {severity: count for severity, count in stats}

    return AnomalyListResponse(
        anomalies=[
            AnomalyResponse(
                id=a.id,
                document_id=a.document_id,
                clause_text=a.clause_text[:500],  # Truncate for list view
                section=a.section,
                clause_number=a.clause_number,
                severity=a.severity,
                explanation=a.explanation,
                prevalence=a.prevalence,
                risk_flags=a.risk_flags,
                created_at=a.created_at,
            )
            for a in anomalies
        ],
        total=total,
        skip=skip,
        limit=limit,
        stats=AnomalyStats(
            total=total,
            high=severity_counts.get("high", 0),
            medium=severity_counts.get("medium", 0),
            low=severity_counts.get("low", 0),
        ),
    )


@router.get(
    "/detail/{anomaly_id}",
    response_model=AnomalyResponse,
    summary="Get Anomaly Details",
    description="Get full details of a specific anomaly.",
)
async def get_anomaly_detail(
    anomaly_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get detailed information about a specific anomaly.
    """
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly not found: {anomaly_id}",
        )

    # Verify user has access to this document
    document = db.query(Document).filter(
        Document.id == anomaly.document_id,
        Document.user_id == current_user.id,
    ).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this anomaly",
        )

    return AnomalyResponse(
        id=anomaly.id,
        document_id=anomaly.document_id,
        clause_text=anomaly.clause_text,  # Full text for detail view
        section=anomaly.section,
        clause_number=anomaly.clause_number,
        severity=anomaly.severity,
        explanation=anomaly.explanation,
        prevalence=anomaly.prevalence,
        risk_flags=anomaly.risk_flags,
        created_at=anomaly.created_at,
    )
```

**Test**:
```bash
# Get all anomalies for document
curl -X GET "http://localhost:8000/api/v1/anomalies/<doc_id>" \
  -H "Authorization: Bearer <token>"

# Filter by severity
curl -X GET "http://localhost:8000/api/v1/anomalies/<doc_id>?severity=high" \
  -H "Authorization: Bearer <token>"

# Get anomaly details
curl -X GET "http://localhost:8000/api/v1/anomalies/detail/<anomaly_id>" \
  -H "Authorization: Bearer <token>"
```

---

### 5. Main.py Router Integration ⚠️ NEEDS UPDATE
**File**: `backend/app/main.py`

**Change Lines 138-144**:

```python
# Include routers
from app.api.v1 import auth, upload, query, anomalies, compare

app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    upload.router,
    prefix=f"{settings.API_V1_PREFIX}/documents",
    tags=["Documents"],
)

app.include_router(
    query.router,
    prefix=f"{settings.API_V1_PREFIX}/query",
    tags=["Q&A"],
)

app.include_router(
    anomalies.router,
    prefix=f"{settings.API_V1_PREFIX}/anomalies",
    tags=["Anomalies"],
)

# Compare endpoint - future enhancement
# app.include_router(
#     compare.router,
#     prefix=f"{settings.API_V1_PREFIX}/compare",
#     tags=["Comparison"],
# )
```

---

### 6. Service Shutdown Methods ⚠️ NEEDS ADDITION

**OpenAI Service** (`backend/app/services/openai_service.py`):
```python
async def close(self):
    """Close OpenAI client connection."""
    if hasattr(self.client, 'close'):
        await self.client.close()
    logger.info("OpenAI client closed")
```

**Pinecone Service** (`backend/app/services/pinecone_service.py`):
```python
async def close(self):
    """Close Pinecone connection."""
    # Pinecone doesn't require explicit closing
    logger.info("Pinecone service closed")
```

---

## 🧪 Week 4: Integration Testing

### Create Integration Test Suite
**File**: `backend/tests/integration/test_full_pipeline.py`

```python
"""
Integration tests for full document processing pipeline.

Tests the complete flow from upload to anomaly detection.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)


@pytest.fixture
def auth_token(test_db):
    """Get authentication token for tests."""
    # Create test user
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/signup",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201

    # Login
    response = client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        data={
            "username": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.mark.integration
def test_full_document_pipeline(auth_token, sample_pdf_path):
    """Test complete pipeline from upload to query."""

    # Step 1: Upload document
    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            f"{settings.API_V1_PREFIX}/documents",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

    assert response.status_code == 201
    data = response.json()
    document_id = data["id"]

    assert data["filename"] == "test.pdf"
    assert data["page_count"] > 0
    assert data["clause_count"] > 0
    assert data["processing_status"] == "completed"

    # Step 2: Query document
    response = client.post(
        f"{settings.API_V1_PREFIX}/query",
        json={
            "document_id": document_id,
            "question": "What is the refund policy?",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "answer" in data
    assert "citations" in data
    assert len(data["citations"]) > 0

    # Step 3: Get anomalies
    response = client.get(
        f"{settings.API_V1_PREFIX}/anomalies/{document_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "anomalies" in data
    assert "stats" in data

    # Step 4: Delete document
    response = client.delete(
        f"{settings.API_V1_PREFIX}/documents/{document_id}",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 204


@pytest.mark.integration
def test_error_handling(auth_token):
    """Test error handling for invalid inputs."""

    # Test invalid file type
    response = client.post(
        f"{settings.API_V1_PREFIX}/documents",
        files={"file": ("test.txt", b"not a pdf", "text/plain")},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 400

    # Test non-existent document query
    response = client.post(
        f"{settings.API_V1_PREFIX}/query",
        json={
            "document_id": "nonexistent-id",
            "question": "Test question",
        },
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == 404
```

---

## 📄 Week 5: Test PDF Generation

### Create Test PDF Generator
**File**: `backend/scripts/create_test_pdfs.py`

```python
"""
Generate test PDF samples for development and testing.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_simple_tos():
    """Create a simple T&C document for testing."""
    output = project_root / "data" / "test_samples" / "simple_tos.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Terms of Service - Simple Example")

    # Company info
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, "Example Corporation")
    c.drawString(50, height - 95, "Effective Date: January 1, 2024")

    # Content
    c.setFont("Helvetica", 12)
    y = height - 130

    sections = [
        (
            "1. ACCEPTANCE OF TERMS",
            "By using this service, you agree to be bound by these terms and conditions. "
            "If you do not agree, you must not use the service."
        ),
        (
            "2. USER OBLIGATIONS",
            "You agree to use the service responsibly and in accordance with all applicable "
            "laws and regulations. You must not engage in any prohibited activities."
        ),
        (
            "3. LIMITATION OF LIABILITY",
            "We are not liable for any damages arising from your use of the service, "
            "including but not limited to direct, indirect, or consequential damages."
        ),
        (
            "4. TERMINATION",
            "We may terminate your access at any time for any reason without notice. "
            "Upon termination, all rights granted to you will immediately cease."
        ),
    ]

    for title, content in sections:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, title)
        y -= 25

        c.setFont("Helvetica", 10)
        # Wrap text
        words = content.split()
        line = ""
        for word in words:
            if len(line + word) < 80:
                line += word + " "
            else:
                c.drawString(50, y, line)
                y -= 15
                line = word + " "
        if line:
            c.drawString(50, y, line)
            y -= 35

    c.save()
    print(f"✓ Created: {output}")


def create_risky_tos():
    """Create a T&C with risky clauses for anomaly detection testing."""
    output = project_root / "data" / "test_samples" / "risky_tos.pdf"

    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Terms of Service - Risky Clauses Example")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, "Risky Corporation Inc.")
    c.drawString(50, height - 95, "Effective Date: October 1, 2024")

    y = height - 130
    c.setFont("Helvetica", 10)

    # Risky clauses
    risky_clauses = [
        "1. CHANGES TO TERMS\nWe may change these terms at any time at our sole discretion without notice to you. Your continued use constitutes acceptance of all changes.",

        "2. UNLIMITED LIABILITY\nYou agree to unlimited liability for any claims arising from your use of our service. You waive all rights to dispute liability amounts.",

        "3. CLASS ACTION WAIVER\nYou waive your right to participate in class action lawsuits. All disputes must be resolved through binding arbitration on an individual basis.",

        "4. DATA SHARING\nWe may share your personal data with third parties for any purpose without restriction or notice. This includes selling your data to advertisers.",

        "5. AUTOMATIC RENEWAL\nYour subscription automatically renews and charges your payment method without notice. Cancellation requests may be denied at our discretion.",

        "6. NO REFUNDS\nAll payments are final and non-refundable under any circumstances, including service outages, dissatisfaction, or account termination.",
    ]

    for clause in risky_clauses:
        lines = clause.split('\n')
        for line in lines:
            c.drawString(50, y, line)
            y -= 15
        y -= 20

        if y < 100:
            c.showPage()
            y = height - 50

    c.save()
    print(f"✓ Created: {output}")


if __name__ == "__main__":
    print("Generating test PDF samples...")
    create_simple_tos()
    create_risky_tos()
    print("\n✓ Test PDFs created successfully!")
    print("\nGenerated files:")
    print("  - data/test_samples/simple_tos.pdf (standard T&C)")
    print("  - data/test_samples/risky_tos.pdf (with risky clauses)")
```

**Run**:
```bash
cd backend
python scripts/create_test_pdfs.py
```

---

## 🚀 Quick Start Commands

### 1. Complete API Endpoints
```bash
# Apply all changes from this guide
# Update query.py, auth.py, anomalies.py, main.py

# Add service shutdown methods
# Update openai_service.py and pinecone_service.py
```

### 2. Generate Test PDFs
```bash
cd backend
pip install reportlab
python scripts/create_test_pdfs.py
```

### 3. Run Integration Tests
```bash
cd backend
pytest tests/integration/ -v --tb=short
```

### 4. Test Full Pipeline
```bash
# Start services
docker-compose up -d

# Start API
cd backend
uvicorn app.main:app --reload

# In another terminal, test with curl or Postman
curl http://localhost:8000/health
```

---

## ✅ Completion Checklist

### Week 3: API Endpoints
- [x] Upload endpoint (complete with full pipeline)
- [ ] Query endpoint (RAG implementation)
- [ ] Auth endpoint (JWT authentication)
- [ ] Anomalies endpoint (filtering and details)
- [ ] Update main.py with all routers
- [ ] Add service shutdown methods

### Week 4: Integration
- [ ] Create integration test suite
- [ ] Test full upload-to-query pipeline
- [ ] Test error handling
- [ ] Test authentication flow

### Week 5: Testing & Validation
- [ ] Generate test PDF samples
- [ ] Test with real PDFs
- [ ] Performance benchmarking
- [ ] Error scenario testing
- [ ] API documentation complete

---

## 📊 Success Criteria

### Functionality
- ✅ Upload and process PDF documents
- ⏳ Answer questions with citations
- ⏳ Detect and list anomalies
- ⏳ User authentication works
- ⏳ All endpoints documented

### Quality
- ⏳ All integration tests pass
- ⏳ Error handling covers edge cases
- ⏳ Services shut down gracefully
- ⏳ API responses follow schemas
- ⏳ Logging comprehensive

### Performance
- ⏳ Upload processing < 30 seconds
- ⏳ Query response < 2 seconds
- ⏳ Anomaly detection completes
- ⏳ No memory leaks
- ⏳ Graceful degradation

---

## 🎯 Next Steps After Completion

1. **Week 6-7**: Data collection (100+ baseline T&Cs)
2. **Week 8-10**: Frontend development
3. **Production**: Deployment and monitoring

---

**Status**: Week 3 (Upload ✓, Query/Auth/Anomalies in progress)
**Updated**: October 30, 2024
