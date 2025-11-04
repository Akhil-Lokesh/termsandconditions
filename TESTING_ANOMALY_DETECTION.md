# Testing the Fixed Anomaly Detection System

**Quick guide to test that anomaly detection now works correctly.**

---

## ✅ Prerequisites

Before testing, ensure:
1. ✅ Backend is running (`uvicorn app.main:app --reload`)
2. ✅ Frontend is running (`npm run dev` in frontend/)
3. ✅ You have OpenAI API key configured in `.env`
4. ✅ You have Pinecone API key configured in `.env`
5. ✅ Database migration run: `alembic upgrade head`

---

## 🧪 Quick Test (5 minutes)

### Step 1: Create a Test T&C Document

Save this as `test_hostile_tc.txt`:

```text
TERMS OF SERVICE

1. ACCOUNT TERMINATION
We may suspend or terminate your account at any time, for any reason or no reason,
with or without notice. You are not entitled to any refund upon termination.

2. PAYMENT TERMS
Your subscription will automatically renew and your payment method will be charged
without notice. We may increase our prices at any time without prior notification.
We reserve the right to automatically update your payment information through our
payment partners.

3. CONTENT RIGHTS
By posting content, you grant us a perpetual, irrevocable, worldwide, royalty-free
license to use, reproduce, modify, and distribute your content for any purpose.
We may sell or license your content to third parties without compensation to you.

4. LIMITATION OF LIABILITY
You waive all rights to pursue any legal claims against us. You agree to unlimited
liability for any claims arising from your use of the service. You waive your right
to participate in any class action lawsuit and agree to binding arbitration.

5. MODIFICATIONS
We may change these terms at any time without notice. Your continued use of the
service constitutes acceptance of the modified terms.

6. USER OBLIGATIONS
You are solely responsible for all content you post and any consequences arising from it.
We may monitor all your activity on the service and share this information with third
parties for any purpose.

7. NO WARRANTY
THE SERVICE IS PROVIDED "AS IS" WITHOUT ANY WARRANTY. WE ARE NOT LIABLE FOR ANY
DATA LOSS OR DAMAGES. You use the service at your own risk.
```

Convert to PDF:
- **macOS**: Open in TextEdit, File → Export as PDF
- **Windows**: Open in Word, Save as PDF
- **Linux**: Use `libreoffice --headless --convert-to pdf test_hostile_tc.txt`

### Step 2: Upload via Frontend

1. Go to http://localhost:5173
2. Login (or signup if needed)
3. Click "Upload Document"
4. Select `test_hostile_tc.pdf`
5. Click "Upload & Analyze"
6. **Wait 20-30 seconds** (processing + anomaly detection)

### Step 3: Check Results

**You should see:**
- ✅ **Anomaly Count**: 10-15 anomalies detected (NOT 0!)
- ✅ **Risk Score**: 8-10/10
- ✅ **Risk Level**: High Risk

**Anomalies should include:**
- 🔴 HIGH: Unilateral termination (Section 1)
- 🔴 HIGH: Price increases without notice (Section 2)
- 🔴 HIGH: Automatic payment updates (Section 2)
- 🔴 HIGH: Broad content rights (Section 3)
- 🔴 HIGH: Rights waiver / class action waiver (Section 4)
- 🔴 HIGH: Unlimited liability (Section 4)
- 🟡 MEDIUM: Auto-renewal (Section 2)
- 🟡 MEDIUM: No refunds (Section 1)
- 🟡 MEDIUM: Unilateral changes (Section 5)
- 🟡 MEDIUM: Monitoring/surveillance (Section 6)

---

## 📊 Expected Results by Document Type

### Test Case 1: Hostile T&C (Above)
```
Anomalies: 10-15
Risk Score: 8-10/10
Risk Level: High
Severity: Mostly HIGH + some MEDIUM
```

### Test Case 2: Standard Fair T&C
Create a document with standard terms like:
- Clear refund policy
- Reasonable usage limits
- Standard warranty disclaimers
- No unusual clauses

```
Anomalies: 1-3
Risk Score: 1-3/10
Risk Level: Low
Severity: Mostly LOW
```

### Test Case 3: Mixed T&C (Typical Company)
Standard terms + auto-renewal + some data sharing

```
Anomalies: 5-8
Risk Score: 4-6/10
Risk Level: Medium
Severity: Mix of MEDIUM + some LOW
```

---

## 🔍 Debugging (If Issues Occur)

### Issue 1: Still Returns 0 Anomalies

**Check Backend Logs:**
```bash
# In backend terminal, look for:
"Starting anomaly detection for document..."
"Total sections to analyze: X"
"Analyzing section 'SECTION_NAME' with X clauses"
"Clause X.X: Found X risk indicators"
"Clause X.X: Prevalence = X%"
"GPT-4 risk level = high/medium/low"
"Anomaly detection complete: X anomalies found"
```

**If you see:**
- `"TypeError: __init__() takes 1 positional argument but 4 were given"` → Migration not applied, restart server
- `"No sections to analyze: 0"` → Structure extraction failed, check PDF text extraction
- `"Prevalence calculation failed"` → Pinecone baseline namespace empty (expected, still works)
- `"Risk assessment failed"` → OpenAI API issue, check API key and rate limits

### Issue 2: Database Error

**Run Migration:**
```bash
cd "/Users/akhil/Desktop/Project T&C/backend"
source venv/bin/activate
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade None -> add_risk_fields_001, add risk assessment fields
```

### Issue 3: GPT-4 Not Running

**Check `.env` file:**
```bash
cat backend/.env | grep OPENAI_API_KEY
```

Should show your actual API key (starts with `sk-proj-...` or `sk-...`)

**Check OpenAI Service:**
```bash
# In Python
cd backend
source venv/bin/activate
python

>>> from app.services.openai_service import OpenAIService
>>> service = OpenAIService()
>>> import asyncio
>>> result = asyncio.run(service.chat_completion(
...     messages=[{"role": "user", "content": "Test"}],
...     max_tokens=10
... ))
>>> print(result)
```

Should return a response (not an error).

---

## 📝 Checking Logs for Success

**Successful anomaly detection logs look like:**

```
INFO: Starting anomaly detection for document abc-123
INFO: Company: Unknown, Service Type: general
INFO: Total sections to analyze: 7
INFO: Analyzing section 'ACCOUNT TERMINATION' with 2 clauses
INFO: Analyzing section 'PAYMENT TERMS' with 3 clauses
DEBUG: Clause 2.1: Found 3 risk indicators
DEBUG: Clause 2.1: Prevalence = 15%
INFO: Clause 2.1: GPT-4 risk level = high
INFO: ✓ Anomaly detected: 2.1 (high risk)
...
INFO: Anomaly detection complete: 12 anomalies found out of 25 clauses
INFO: Document risk score: 8.5/10 (High)
INFO: Anomaly detection complete: 12 anomalies, Risk Score: 8.5/10 (High)
```

---

## 🎯 Validation Checklist

After uploading test document:

### Database Checks:
```sql
-- Check document
SELECT id, filename, anomaly_count, risk_score, risk_level
FROM documents
ORDER BY created_at DESC
LIMIT 1;
```
**Expected**: `anomaly_count > 0`, `risk_score > 0`, `risk_level = 'High'`

```sql
-- Check anomalies
SELECT COUNT(*), severity
FROM anomalies
WHERE document_id = 'YOUR_DOC_ID'
GROUP BY severity;
```
**Expected**: Multiple rows with high/medium counts

```sql
-- Check anomaly details
SELECT clause_number, section, severity, risk_category, explanation
FROM anomalies
WHERE document_id = 'YOUR_DOC_ID'
ORDER BY
  CASE severity
    WHEN 'high' THEN 1
    WHEN 'medium' THEN 2
  END;
```
**Expected**: Detailed explanations, consumer_impact, recommendations

### Frontend Checks:
1. ✅ Document detail page shows "Risk Score: X/10"
2. ✅ Anomalies tab shows list of detected issues
3. ✅ Each anomaly has:
   - Section name
   - Clause number
   - Severity badge (color-coded)
   - Explanation
   - Consumer impact
   - Recommendation
4. ✅ Can filter by severity (High/Medium/Low tabs)

---

## 🚀 Production Testing

### Test with Real T&Cs:

**Download sample T&Cs from:**
- Facebook: https://www.facebook.com/legal/terms
- Twitter: https://twitter.com/en/tos
- Netflix: https://help.netflix.com/legal/termsofuse
- Amazon: https://www.amazon.com/gp/help/customer/display.html?nodeId=508088
- Google: https://policies.google.com/terms

**Upload each and verify:**
1. Processing completes successfully
2. Anomaly count is reasonable (5-15 for most)
3. Risk score reflects actual terms (social media = higher, utilities = lower)
4. Explanations are consumer-focused (not legal jargon)
5. Recommendations are actionable

---

## ✅ Success Criteria

The fix is successful if:

- [x] Test document detects **10+ anomalies** (not 0)
- [x] Risk score is **8-10/10** for hostile terms
- [x] HIGH severity flags on obviously unfair clauses
- [x] Explanations are **consumer-focused** ("this is risky because...")
- [x] Processing completes without errors
- [x] Database contains all anomaly details
- [x] Frontend displays anomalies correctly

---

## 🆘 Getting Help

If you encounter issues:

1. **Check Backend Logs**: Full error messages with stack traces
2. **Check Database**: Verify migration applied, data saved
3. **Check API Keys**: OpenAI and Pinecone keys valid
4. **Check ANOMALY_DETECTION_FIX_COMPLETE.md**: Full technical details

**Error still occurring?** Share:
- Backend error logs (full stack trace)
- Document metadata (sections, clause count)
- Database query results (anomalies table)

---

**Last Updated**: November 1, 2024
**Status**: ✅ Ready for Testing
