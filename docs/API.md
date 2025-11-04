# API Documentation

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.yourdomain.com`

## API Version

Current version: `v1`

All endpoints are prefixed with `/api/v1`

## Authentication

Most endpoints require JWT authentication.

### Get Access Token

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "username": "user@example.com",
  "password": "your_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Usage**: Include token in Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Endpoints

### Authentication

#### Register User

**Endpoint**: `POST /api/v1/auth/register`

**Description**: Create a new user account

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

**Response**: `201 Created`
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors**:
- `400 Bad Request`: Email already registered
- `422 Unprocessable Entity`: Invalid email format

---

#### Login

**Endpoint**: `POST /api/v1/auth/login`

**Description**: Authenticate user and receive JWT token

**Request Body**:
```json
{
  "username": "user@example.com",
  "password": "your_password"
}
```

**Response**: `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401 Unauthorized`: Incorrect email or password
- `400 Bad Request`: Inactive user

---

### Document Upload

#### Upload T&C Document

**Endpoint**: `POST /api/v1/upload`

**Description**: Upload a Terms & Conditions PDF for analysis

**Authentication**: Required

**Request**: `multipart/form-data`

**Parameters**:
- `file` (file, required): PDF file to upload

**cURL Example**:
```bash
curl -X POST \
  http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@spotify_tos.pdf"
```

**Response**: `201 Created`
```json
{
  "id": 42,
  "user_id": 1,
  "filename": "spotify_tos.pdf",
  "company_name": "Spotify",
  "effective_date": "2024-01-01T00:00:00Z",
  "num_sections": 12,
  "num_clauses": 45,
  "processing_status": "completed",
  "created_at": "2024-01-15T10:35:00Z"
}
```

**Errors**:
- `400 Bad Request`: Invalid file type (not PDF)
- `400 Bad Request`: File too large (>10MB)
- `400 Bad Request`: Not a T&C document
- `500 Internal Server Error`: Processing failed

**Notes**:
- Max file size: 10MB
- Only PDF files accepted
- Document must be a Terms & Conditions document

---

#### Get Document

**Endpoint**: `GET /api/v1/upload/{document_id}`

**Description**: Get document metadata

**Authentication**: Required

**Path Parameters**:
- `document_id` (integer): ID of the document

**Response**: `200 OK`
```json
{
  "id": 42,
  "user_id": 1,
  "filename": "spotify_tos.pdf",
  "company_name": "Spotify",
  "effective_date": "2024-01-01T00:00:00Z",
  "num_sections": 12,
  "num_clauses": 45,
  "processing_status": "completed",
  "created_at": "2024-01-15T10:35:00Z"
}
```

**Errors**:
- `404 Not Found`: Document not found or unauthorized

---

### Query & Q&A

#### Ask Question

**Endpoint**: `POST /api/v1/query`

**Description**: Ask a question about a T&C document

**Authentication**: Required

**Request Body**:
```json
{
  "document_id": 42,
  "question": "Can I cancel my subscription anytime?"
}
```

**Response**: `200 OK`
```json
{
  "question": "Can I cancel my subscription anytime?",
  "answer": "Yes, you can cancel your subscription at any time according to Section 3.6. However, cancellation takes effect at the end of your current billing period, and you won't receive a refund for the remaining time.",
  "sources": [
    {
      "clause_id": "3.6",
      "section": "Subscription & Billing",
      "text": "You may cancel your subscription at any time through your account settings. Cancellation will take effect at the end of the current billing period."
    }
  ],
  "warnings": [
    "⚠️ The company can terminate your account immediately without refund (Section 9.1), but you must wait until the end of your billing period."
  ],
  "related_anomalies": [15, 23]
}
```

**Errors**:
- `404 Not Found`: Document not found
- `500 Internal Server Error`: Query processing failed

**Notes**:
- Responses are cached for 30 days
- Check `related_anomalies` for risk warnings

---

### Anomaly Detection

#### Get Anomaly Report

**Endpoint**: `GET /api/v1/anomalies/{document_id}`

**Description**: Get comprehensive anomaly detection report

**Authentication**: Required

**Path Parameters**:
- `document_id` (integer): ID of the document

**Response**: `200 OK`
```json
{
  "document_id": 42,
  "company_name": "Spotify",
  "overall_risk_score": 6.5,
  "risk_level": "medium",
  "high_risk_anomalies": [
    {
      "id": 15,
      "clause_id": "9.1",
      "section": "Termination Rights",
      "clause_text": "We may terminate your account at any time for any reason without notice or refund.",
      "risk_level": "high",
      "prevalence": "31%",
      "explanation": "This clause gives the company unilateral termination rights without requiring cause or providing refunds. This is found in only 31% of similar services, making it unusually restrictive.",
      "affected_rights": [
        "Right to continued service",
        "Right to refund for unused time"
      ],
      "recommendation": "Users should be aware they may lose access without warning or compensation."
    }
  ],
  "medium_risk_anomalies": [
    {
      "id": 23,
      "clause_id": "6.2",
      "section": "Data Usage",
      "clause_text": "We may share your data with third-party partners for marketing purposes.",
      "risk_level": "medium",
      "prevalence": "45%",
      "explanation": "This allows broad data sharing for marketing. While present in 45% of services, users should be aware of the extent of data sharing.",
      "affected_rights": ["Privacy rights"],
      "recommendation": "Review privacy settings to limit data sharing."
    }
  ],
  "missing_clauses": [
    {
      "clause_type": "data_breach_notification",
      "importance": "high",
      "explanation": "No clear policy for notifying users in case of data breaches. This is a standard consumer protection."
    }
  ],
  "summary": "This Terms & Conditions document contains 2 high-risk and 3 medium-risk clauses. Key concerns include asymmetric termination rights and broad data sharing permissions."
}
```

**Errors**:
- `404 Not Found`: Document not found
- `500 Internal Server Error`: Report generation failed

---

### Comparison

#### Compare Documents

**Endpoint**: `POST /api/v1/compare`

**Description**: Compare multiple T&C documents side-by-side

**Authentication**: Required

**Request Body**:
```json
{
  "document_ids": [42, 43, 44]
}
```

**Response**: `200 OK`
```json
{
  "documents": [
    {
      "id": 42,
      "company_name": "Spotify",
      "overall_risk_score": 6.5
    },
    {
      "id": 43,
      "company_name": "Netflix",
      "overall_risk_score": 4.2
    },
    {
      "id": 44,
      "company_name": "Hulu",
      "overall_risk_score": 5.8
    }
  ],
  "comparison": {
    "cancellation_policy": [
      {
        "company": "Spotify",
        "clause_text": "Cancel anytime, effective end of billing period",
        "risk_level": "low",
        "is_best": false
      },
      {
        "company": "Netflix",
        "clause_text": "Cancel anytime, effective immediately",
        "risk_level": "low",
        "is_best": true
      },
      {
        "company": "Hulu",
        "clause_text": "Cancel anytime, effective end of billing period",
        "risk_level": "low",
        "is_best": false
      }
    ],
    "privacy_policy": [...],
    "termination_rights": [...],
    "refund_policy": [...]
  },
  "recommendations": "Netflix has the most user-friendly terms overall with immediate cancellation and clear refund policies. Spotify has more restrictive termination rights.",
  "most_user_friendly": "Netflix"
}
```

**Errors**:
- `400 Bad Request`: Less than 2 documents provided
- `404 Not Found`: One or more documents not found

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (invalid input) |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Not Found |
| 422 | Unprocessable Entity (validation error) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error |

---

## Rate Limiting

**Limit**: 100 requests per hour per user

**Headers**:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

**Response when exceeded**:
```json
{
  "detail": "Rate limit exceeded. Try again in 45 minutes."
}
```

---

## Error Response Format

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

Validation errors (422) include field details:

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

## Webhooks (Future)

*Not yet implemented*

Webhooks will notify your application when:
- Document processing completes
- Anomaly detection finishes
- High-risk clauses detected

---

## API Client Examples

### Python (requests)

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={
        "username": "user@example.com",
        "password": "password"
    }
)
token = response.json()["access_token"]

# Upload document
with open("spotify_tos.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": f}
    )
document = response.json()

# Ask question
response = requests.post(
    "http://localhost:8000/api/v1/query",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "document_id": document["id"],
        "question": "Can I cancel anytime?"
    }
)
answer = response.json()
print(answer["answer"])

# Get anomaly report
response = requests.get(
    f"http://localhost:8000/api/v1/anomalies/{document['id']}",
    headers={"Authorization": f"Bearer {token}"}
)
report = response.json()
print(f"Risk Score: {report['overall_risk_score']}")
```

### JavaScript (fetch)

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user@example.com',
    password: 'password'
  })
});
const { access_token } = await loginResponse.json();

// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadResponse = await fetch('http://localhost:8000/api/v1/upload', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${access_token}` },
  body: formData
});
const document = await uploadResponse.json();

// Ask question
const queryResponse = await fetch('http://localhost:8000/api/v1/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    document_id: document.id,
    question: 'Can I cancel anytime?'
  })
});
const answer = await queryResponse.json();
console.log(answer.answer);
```

### cURL

```bash
# Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}' \
  | jq -r '.access_token')

# Upload document
DOC_ID=$(curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@spotify_tos.pdf" \
  | jq -r '.id')

# Ask question
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":$DOC_ID,\"question\":\"Can I cancel anytime?\"}" \
  | jq '.answer'

# Get anomaly report
curl -X GET http://localhost:8000/api/v1/anomalies/$DOC_ID \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.overall_risk_score'
```

---

## OpenAPI Specification

Full OpenAPI (Swagger) specification available at:

**Development**: http://localhost:8000/api/v1/docs

**Interactive API Testing**: http://localhost:8000/api/v1/docs

---

## Changelog

### v1.0.0 (2024-01-15)
- Initial release
- Document upload and processing
- Q&A functionality
- Anomaly detection
- Comparison tool

---

## Support

For API questions or issues:
- Email: api-support@yourdomain.com
- Documentation: https://docs.yourdomain.com
- Status Page: https://status.yourdomain.com
