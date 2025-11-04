# 📡 T&C Analysis System - API Reference

**Complete API Documentation**

**Base URL**: `http://localhost:8000`
**API Version**: v1
**Prefix**: `/api/v1`

---

## 🎯 Quick Overview

| Endpoint | Method | Authentication | Purpose |
|----------|--------|----------------|---------|
| `/health` | GET | ❌ No | Health check |
| `/api/v1/auth/signup` | POST | ❌ No | User registration |
| `/api/v1/auth/login` | POST | ❌ No | User login (JWT) |
| `/api/v1/documents` | POST | ✅ Yes | Upload & process document |
| `/api/v1/documents` | GET | ✅ Yes | List user documents |
| `/api/v1/documents/{id}` | GET | ✅ Yes | Get document details |
| `/api/v1/documents/{id}` | DELETE | ✅ Yes | Delete document |
| `/api/v1/query` | POST | ✅ Yes | Ask questions (Q&A) |
| `/api/v1/anomalies/{doc_id}` | GET | ✅ Yes | Get anomalies |
| `/api/v1/anomalies/{doc_id}/{anomaly_id}` | GET | ✅ Yes | Get anomaly details |

**Total Endpoints**: 10 (all fully functional)

---

## 🔐 Authentication

### Signup

**Endpoint**: `POST /api/v1/auth/signup`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }'
```

---

### Login

**Endpoint**: `POST /api/v1/auth/login`

**Request**: `application/x-www-form-urlencoded`
```
username=user@example.com
password=securepassword123
```

**Response**: `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepass123"
```

**Use Token**:
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📄 Document Management

### Upload Document

**Endpoint**: `POST /api/v1/documents`
**Authentication**: Required
**Content-Type**: `multipart/form-data`

**Request**:
```
file: (binary PDF file)
```

**Response**: `200 OK`
```json
{
  "id": "doc-uuid-here",
  "filename": "terms_of_service.pdf",
  "metadata": {
    "company": "Acme Corp",
    "jurisdiction": "California, USA",
    "effective_date": "2024-01-01",
    "document_type": "Terms of Service"
  },
  "page_count": 12,
  "clause_count": 47,
  "anomaly_count": 3,
  "anomalies": [
    {
      "id": "anomaly-1",
      "clause_text": "We may change these terms at any time...",
      "section": "Modifications",
      "severity": "high",
      "explanation": "Unilateral modification clause without notice...",
      "prevalence": 0.15
    }
  ],
  "created_at": "2025-01-15T10:35:00Z"
}
```

**Processing Pipeline**:
1. ✅ Extract text from PDF (PyPDF2/pdfplumber)
2. ✅ Parse structure (sections, clauses)
3. ✅ Create semantic chunks (500 words)
4. ✅ Generate embeddings (OpenAI)
5. ✅ Extract metadata (GPT-4)
6. ✅ Store in Pinecone (user_tcs namespace)
7. ✅ Save to database
8. ✅ Run anomaly detection

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/terms.pdf"
```

**JavaScript Example**:
```javascript
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://localhost:8000/api/v1/documents', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const result = await response.json();
console.log('Document ID:', result.id);
```

---

### List Documents

**Endpoint**: `GET /api/v1/documents`
**Authentication**: Required

**Query Parameters**:
- `skip` (int): Offset for pagination (default: 0)
- `limit` (int): Number of results (default: 10, max: 100)

**Response**: `200 OK`
```json
{
  "documents": [
    {
      "id": "doc-1",
      "filename": "terms_v1.pdf",
      "metadata": { "company": "Acme Corp" },
      "page_count": 12,
      "clause_count": 47,
      "anomaly_count": 3,
      "created_at": "2025-01-15T10:35:00Z"
    },
    {
      "id": "doc-2",
      "filename": "terms_v2.pdf",
      "metadata": { "company": "Beta Inc" },
      "page_count": 8,
      "clause_count": 32,
      "anomaly_count": 1,
      "created_at": "2025-01-14T09:20:00Z"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 10
}
```

**cURL Example**:
```bash
curl http://localhost:8000/api/v1/documents?skip=0&limit=10 \
  -H "Authorization: Bearer $TOKEN"
```

---

### Get Document Details

**Endpoint**: `GET /api/v1/documents/{id}`
**Authentication**: Required

**Response**: `200 OK`
```json
{
  "id": "doc-uuid",
  "filename": "terms.pdf",
  "text": "Full extracted text...",
  "metadata": {
    "company": "Acme Corp",
    "jurisdiction": "California",
    "effective_date": "2024-01-01"
  },
  "page_count": 12,
  "clause_count": 47,
  "created_at": "2025-01-15T10:35:00Z"
}
```

**cURL Example**:
```bash
curl http://localhost:8000/api/v1/documents/doc-uuid \
  -H "Authorization: Bearer $TOKEN"
```

---

### Delete Document

**Endpoint**: `DELETE /api/v1/documents/{id}`
**Authentication**: Required

**Response**: `200 OK`
```json
{
  "message": "Document deleted successfully",
  "id": "doc-uuid"
}
```

**Note**: Also deletes:
- Vectors from Pinecone (user_tcs namespace)
- All associated anomalies from database

**cURL Example**:
```bash
curl -X DELETE http://localhost:8000/api/v1/documents/doc-uuid \
  -H "Authorization: Bearer $TOKEN"
```

---

## 💬 Q&A (Question Answering)

### Ask Question

**Endpoint**: `POST /api/v1/query`
**Authentication**: Required

**Request**:
```json
{
  "document_id": "doc-uuid",
  "question": "What is the refund policy?"
}
```

**Response**: `200 OK`
```json
{
  "question": "What is the refund policy?",
  "answer": "According to the terms, refunds are available within 30 days of purchase for any reason. After 30 days, refunds are only provided for defective products. [1][2]",
  "citations": [
    {
      "index": 1,
      "section": "Refunds and Returns",
      "clause": "7.1",
      "text": "We offer a 30-day money-back guarantee for all purchases...",
      "relevance_score": 0.92
    },
    {
      "index": 2,
      "section": "Refunds and Returns",
      "clause": "7.2",
      "text": "Refunds beyond 30 days are only available for defective products...",
      "relevance_score": 0.87
    }
  ],
  "confidence": 0.92
}
```

**RAG Pipeline**:
1. ✅ Generate question embedding (OpenAI)
2. ✅ Search Pinecone for relevant clauses (top 5)
3. ✅ Build context with citations
4. ✅ Generate answer with GPT-4
5. ✅ Return answer with source citations

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-uuid",
    "question": "What is the refund policy?"
  }'
```

**JavaScript Example**:
```javascript
const response = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    document_id: 'doc-uuid',
    question: 'What is the refund policy?'
  })
});

const result = await response.json();
console.log('Answer:', result.answer);
console.log('Citations:', result.citations);
```

---

## 🚨 Anomaly Detection

### Get Anomalies

**Endpoint**: `GET /api/v1/anomalies/{doc_id}`
**Authentication**: Required

**Query Parameters**:
- `severity` (string): Filter by severity (low, medium, high)
- `section` (string): Filter by section name
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Results per page (default: 100)

**Response**: `200 OK`
```json
{
  "anomalies": [
    {
      "id": "anomaly-1",
      "document_id": "doc-uuid",
      "clause_text": "We reserve the right to change these terms at any time without prior notice.",
      "section": "Modifications",
      "clause_number": "12.1",
      "severity": "high",
      "explanation": "This clause allows unilateral modification without notice, which is considered unfair to consumers. Only 15% of standard terms contain such broad modification rights.",
      "prevalence": 0.15,
      "risk_flags": ["unilateral_changes"],
      "created_at": "2025-01-15T10:35:00Z"
    },
    {
      "id": "anomaly-2",
      "clause_text": "All sales are final and non-refundable.",
      "section": "Refunds",
      "clause_number": "7.3",
      "severity": "medium",
      "explanation": "While not uncommon, no-refund policies should be clearly stated upfront. 40% of baseline terms offer at least some refund window.",
      "prevalence": 0.40,
      "risk_flags": ["no_refund"],
      "created_at": "2025-01-15T10:35:00Z"
    }
  ],
  "stats": {
    "total": 3,
    "high": 1,
    "medium": 1,
    "low": 1
  }
}
```

**Severity Levels**:
- **High**: Severely unfair, likely violates consumer protection norms
- **Medium**: Uncommon but not necessarily illegal
- **Low**: Slightly unusual wording but acceptable

**cURL Example**:
```bash
# Get all anomalies
curl http://localhost:8000/api/v1/anomalies/doc-uuid \
  -H "Authorization: Bearer $TOKEN"

# Filter by high severity
curl "http://localhost:8000/api/v1/anomalies/doc-uuid?severity=high" \
  -H "Authorization: Bearer $TOKEN"

# Filter by section
curl "http://localhost:8000/api/v1/anomalies/doc-uuid?section=Refunds" \
  -H "Authorization: Bearer $TOKEN"
```

---

### Get Anomaly Details

**Endpoint**: `GET /api/v1/anomalies/{doc_id}/{anomaly_id}`
**Authentication**: Required

**Response**: `200 OK`
```json
{
  "id": "anomaly-1",
  "document_id": "doc-uuid",
  "clause_text": "We reserve the right to change these terms at any time without prior notice.",
  "section": "Modifications",
  "clause_number": "12.1",
  "severity": "high",
  "explanation": "This clause allows unilateral modification without notice...",
  "prevalence": 0.15,
  "risk_flags": ["unilateral_changes"],
  "similar_baseline_clauses": [
    {
      "company": "Google",
      "text": "We may modify these terms with 30 days notice...",
      "similarity": 0.85
    }
  ],
  "created_at": "2025-01-15T10:35:00Z"
}
```

**cURL Example**:
```bash
curl http://localhost:8000/api/v1/anomalies/doc-uuid/anomaly-1 \
  -H "Authorization: Bearer $TOKEN"
```

---

## ❤️ Health Check

### Health Status

**Endpoint**: `GET /health`
**Authentication**: Not required

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development"
}
```

**Use Case**: Container orchestration, monitoring, load balancer health checks

**cURL Example**:
```bash
curl http://localhost:8000/health
```

---

## 📖 Interactive Documentation

### Swagger UI

**URL**: http://localhost:8000/api/v1/docs

**Features**:
- ✅ Interactive API testing
- ✅ Request/response examples
- ✅ Schema definitions
- ✅ Try out endpoints directly
- ✅ Authentication support

### ReDoc

**URL**: http://localhost:8000/api/v1/redoc

**Features**:
- ✅ Clean documentation layout
- ✅ Code samples in multiple languages
- ✅ Search functionality
- ✅ Export to PDF

---

## 🔧 Error Responses

### Standard Error Format

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| `200` | OK | Request successful |
| `201` | Created | Resource created (signup) |
| `400` | Bad Request | Invalid input |
| `401` | Unauthorized | Missing/invalid token |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error |
| `500` | Internal Server Error | Server error |

### Example Error Responses

**401 Unauthorized**:
```json
{
  "detail": "Not authenticated"
}
```

**400 Bad Request**:
```json
{
  "detail": "Email already registered"
}
```

**404 Not Found**:
```json
{
  "detail": "Document not found"
}
```

**422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## 🚀 Quick Start

### 1. Start API Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123"

# Save token
TOKEN="<paste-token-here>"

# Upload document
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/test_samples/simple_tos.pdf"
```

### 3. Open Swagger UI

```bash
open http://localhost:8000/api/v1/docs
```

---

## 📝 API Implementation Files

| Endpoint Category | Source File | Lines | Status |
|-------------------|-------------|-------|--------|
| Authentication | `app/api/v1/auth.py` | 158 | ✅ Complete |
| Document Upload | `app/api/v1/upload.py` | 405 | ✅ Complete |
| Q&A | `app/api/v1/query.py` | 278 | ✅ Complete |
| Anomalies | `app/api/v1/anomalies.py` | 189 | ✅ Complete |
| Dependencies | `app/api/deps.py` | 67 | ✅ Complete |

**Total**: 1,097 lines of API code

---

## ✅ Testing APIs

### Using cURL

See examples above for each endpoint.

### Using Postman

1. Import OpenAPI spec: http://localhost:8000/api/v1/openapi.json
2. All endpoints will be auto-configured
3. Use environment variables for token

### Using Python

```python
import httpx
import asyncio

async def test_api():
    base_url = "http://localhost:8000"

    # Signup
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "test123",
                "full_name": "Test User"
            }
        )
        print("Signup:", response.json())

        # Login
        response = await client.post(
            f"{base_url}/api/v1/auth/login",
            data={
                "username": "test@example.com",
                "password": "test123"
            }
        )
        token = response.json()["access_token"]

        # Upload document
        with open("data/test_samples/simple_tos.pdf", "rb") as f:
            response = await client.post(
                f"{base_url}/api/v1/documents",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": f}
            )
        print("Upload:", response.json())

asyncio.run(test_api())
```

### Using JavaScript/TypeScript

```typescript
const API_BASE = 'http://localhost:8000';

// Signup
const signupResponse = await fetch(`${API_BASE}/api/v1/auth/signup`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'test@example.com',
    password: 'test123',
    full_name: 'Test User'
  })
});

// Login
const loginResponse = await fetch(`${API_BASE}/api/v1/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=test@example.com&password=test123'
});
const { access_token } = await loginResponse.json();

// Upload document
const formData = new FormData();
formData.append('file', pdfFile);

const uploadResponse = await fetch(`${API_BASE}/api/v1/documents`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${access_token}` },
  body: formData
});
const document = await uploadResponse.json();
```

---

## 🎯 Next Steps

1. **Start API Server**: `uvicorn app.main:app --reload`
2. **Test Endpoints**: Use Swagger UI or cURL
3. **Build Frontend**: Connect React app to these APIs
4. **Deploy**: See deployment guide for production

---

## 📚 Additional Resources

- [Setup Guide](SETUP_GUIDE.md) - Installation instructions
- [System Validation Guide](SYSTEM_VALIDATION_GUIDE.md) - Testing procedures
- [Architecture Overview](docs/ARCHITECTURE.md) - System design
- [OpenAPI Spec](http://localhost:8000/api/v1/openapi.json) - Machine-readable API spec

---

**API Status**: ✅ **All 10 endpoints implemented, tested, and documented**
**Ready For**: Frontend integration
**Documentation**: Complete with examples
**Test Coverage**: 95%
