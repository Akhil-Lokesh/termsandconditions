# 🚀 GPT-5 Two-Stage System - Quick Start Guide

Get the GPT-5 two-stage analysis system running in 5 minutes.

---

## ⚡ Quick Setup (5 Steps)

### 1. Database Migration ✅ (Already Done)
```bash
cd backend
source venv/bin/activate
alembic current
# Should show: add_analysis_logs_002 (head)
```

### 2. Verify System
```bash
cd backend
source venv/bin/activate
python3 scripts/verify_gpt5_system.py
```

**Expected**: All checks pass ✅

### 3. Start Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Check**: Visit http://localhost:8000/docs for API documentation

### 4. Start Frontend (Already Running)
The frontend is already running at http://localhost:5173

### 5. Test the System

#### Option A: Via API (cURL)

**Step 1**: Login to get JWT token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'
```

**Step 2**: Upload a document (get document_id)
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@path/to/document.pdf"
```

**Step 3**: Analyze with GPT-5 two-stage system
```bash
curl -X POST http://localhost:8000/api/v1/gpt5/documents/DOCUMENT_ID/analyze \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Step 4**: Check cost summary
```bash
curl http://localhost:8000/api/v1/gpt5/analytics/cost-summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Option B: Via Frontend (Recommended)

1. Go to http://localhost:5173
2. Login with your credentials
3. Upload a T&C document
4. Click "Analyze with GPT-5" (new button)
5. View results with cost breakdown

---

## 📊 What to Expect

### Sample Output

**Stage 1 Only (High Confidence)**:
```json
{
  "document_id": "abc123",
  "overall_risk": "low",
  "confidence": 0.87,
  "stage": 1,
  "escalated": false,
  "cost": 0.0006,
  "processing_time": 2.3,
  "summary": "Standard terms and conditions...",
  "anomalies_detected": 0
}
```

**Stage 2 Escalation (Low Confidence)**:
```json
{
  "document_id": "xyz789",
  "overall_risk": "medium",
  "confidence": 0.45,
  "stage": 2,
  "escalated": true,
  "cost": 0.0156,
  "processing_time": 12.8,
  "summary": "Multiple concerning clauses detected...",
  "anomalies_detected": 5
}
```

**Cache Hit (Duplicate Document)**:
```json
{
  "document_id": "def456",
  "overall_risk": "low",
  "confidence": 0.87,
  "stage": 1,
  "escalated": false,
  "cost": 0.0000,  // ← $0 cost!
  "processing_time": 0.3,
  "summary": "Standard terms and conditions...",
  "anomalies_detected": 0
}
```

---

## 🎯 Expected Metrics

After analyzing 10-20 documents:

| Metric | Target | What It Means |
|--------|--------|---------------|
| Average Cost | $0.0039 | Blended cost per document |
| Escalation Rate | ~24% | % of docs going to Stage 2 |
| Cache Hit Rate | 0% initially | Will increase with duplicate uploads |
| Processing Time | 2-15s | Depends on stage and document size |

---

## 🧪 Test Documents

### Test Case 1: Simple T&C (Expect Stage 1 Only)
- Upload a standard, well-known T&C (e.g., Google, Microsoft)
- **Expected**: High confidence (>0.55), Stage 1 only, cost ~$0.0006

### Test Case 2: Complex T&C (Expect Stage 2 Escalation)
- Upload a complex or unusual T&C
- **Expected**: Low confidence (<0.55), escalates to Stage 2, cost ~$0.0156

### Test Case 3: Duplicate Upload (Expect Cache Hit)
- Upload the same document twice
- **Expected**: Second upload returns instantly, cost $0.00

---

## 📈 Monitoring

### Check Analysis Logs
```bash
cd backend
source venv/bin/activate
psql $DATABASE_URL -c "
  SELECT
    document_id,
    stage_reached,
    escalated,
    final_confidence,
    total_cost,
    created_at
  FROM analysis_logs
  ORDER BY created_at DESC
  LIMIT 10;
"
```

### Check Cache Hit Rate
```bash
# In Python console
from app.services.analysis_cache_manager import AnalysisCacheManager
cache = AnalysisCacheManager()
print(f"Hit rate: {cache.get_hit_rate():.1%}")
```

### Check Redis Cache
```bash
redis-cli
> KEYS gpt5:analysis:*
> GET gpt5:analysis:SOME_HASH
```

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process if needed
kill -9 PID

# Check logs
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --log-level debug
```

### API returns 500 errors
```bash
# Check backend logs for details
# Common issues:
# 1. OpenAI API key not configured
# 2. Redis not running
# 3. Database connection failed

# Verify configuration
cd backend && source venv/bin/activate
python3 -c "from app.core.config import settings; print(settings.OPENAI_API_KEY[:10])"
```

### Cache not working
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server
```

### "Document not found" error
Make sure to:
1. Upload document first (POST /api/v1/upload)
2. Use the returned document_id
3. Use the same authenticated user

---

## 📝 Quick Reference

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/login` | POST | Get JWT token |
| `/api/v1/upload` | POST | Upload document |
| `/api/v1/gpt5/documents/{id}/analyze` | POST | Run GPT-5 analysis |
| `/api/v1/gpt5/analytics/cost-summary` | GET | View cost metrics |
| `/api/v1/gpt5/documents/{id}/analysis-history` | GET | View analysis logs |

### Cost Reference

| Scenario | Cost | Stage | Time |
|----------|------|-------|------|
| Stage 1 only | $0.0006 | 1 | ~2-3s |
| Stage 1 + Stage 2 | $0.0156 | 2 | ~10-15s |
| Cache hit | $0.0000 | N/A | ~0.5s |
| **Blended average** | **$0.0039** | Mixed | Varies |

### Confidence Threshold

- **≥ 0.55**: Stage 1 result returned (high confidence)
- **< 0.55**: Escalates to Stage 2 (low confidence)

---

## 🎉 Success Indicators

✅ **System is working correctly if**:
- Backend starts without errors
- API documentation loads at http://localhost:8000/docs
- Verification script passes all checks
- First document analysis completes successfully
- Costs are tracked in database
- Duplicate uploads show $0.00 cost (cache hit)

⚠️ **Something is wrong if**:
- All documents escalate to Stage 2 (>50%)
- No cache hits after 5+ duplicate uploads
- Costs are significantly higher than $0.0039 average
- API returns 500 errors

---

## 📚 Documentation

- **Full Implementation**: `GPT5_COMPLETE_IMPLEMENTATION.md`
- **Deployment Guide**: `GPT5_DEPLOYMENT_CHECKLIST.md`
- **Completion Summary**: `GPT5_IMPLEMENTATION_COMPLETE.md`
- **This Guide**: `QUICKSTART_GPT5.md`

---

## 🚀 You're Ready!

The GPT-5 two-stage system is fully operational. Start testing with your T&C documents and monitor the metrics to verify the 73-80% cost savings!

**Questions?** Check the comprehensive documentation files listed above.

---

**Last Updated**: November 2, 2025
**Status**: Production Ready ✅
