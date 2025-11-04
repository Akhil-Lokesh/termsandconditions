# Quick Implementation Checklist - Week 3-5

**Use this checklist to track your implementation progress.**

Copy the code from `WEEK_3_5_COMPLETION_GUIDE.md` and check off as you go!

---

## 📋 Week 3: API Endpoints

### Upload Endpoint
- [x] POST /documents (upload)
- [x] GET /documents (list)
- [x] GET /documents/{id} (get details)
- [x] DELETE /documents/{id} (delete)
- [x] Error handling complete
- [x] OpenAPI documentation added

### Query Endpoint
- [ ] Copy code from completion guide → `backend/app/api/v1/query.py`
- [ ] Verify imports (OpenAI, Pinecone, schemas)
- [ ] Test with curl: `curl -X POST .../query -d '{"document_id":"...","question":"..."}'`
- [ ] Check response has answer + citations
- [ ] Test error: non-existent document
- [ ] Test error: empty question

### Auth Endpoint
- [ ] Copy code from completion guide → `backend/app/api/v1/auth.py`
- [ ] Verify security utils imported (get_password_hash, create_access_token)
- [ ] Test signup: `curl -X POST .../auth/signup -d '{"email":"test@ex.com",...}'`
- [ ] Test login: `curl -X POST .../auth/login -d 'username=test@ex.com&password=...'`
- [ ] Verify JWT token returned
- [ ] Test protected endpoint with token
- [ ] Test error: duplicate email
- [ ] Test error: wrong password

### Anomalies Endpoint
- [ ] Copy code from completion guide → `backend/app/api/v1/anomalies.py`
- [ ] Verify anomaly model/schema imports
- [ ] Test get anomalies: `curl .../anomalies/{doc_id}`
- [ ] Test filter by severity: `.../anomalies/{doc_id}?severity=high`
- [ ] Test get detail: `.../anomalies/detail/{anomaly_id}`
- [ ] Verify stats returned correctly
- [ ] Test error: non-existent document
- [ ] Test error: unauthorized access

### Main.py Integration
- [ ] Open `backend/app/main.py`
- [ ] Uncomment imports at top (auth, upload, query, anomalies)
- [ ] Add router includes (see guide for exact code)
- [ ] Save file
- [ ] Restart uvicorn: `uvicorn app.main:app --reload`
- [ ] Visit: http://localhost:8000/api/v1/docs
- [ ] Verify all endpoints visible in Swagger UI
- [ ] Test each endpoint from Swagger UI

### Service Cleanup
- [ ] Add close() to OpenAI service (`backend/app/services/openai_service.py`)
- [ ] Add close() to Pinecone service (`backend/app/services/pinecone_service.py`)
- [ ] Verify lifespan shutdown calls close() methods
- [ ] Test graceful shutdown: Ctrl+C and check logs

---

## 🧪 Week 4: Integration Testing

### Test Infrastructure
- [ ] Create directory: `backend/tests/integration/`
- [ ] Create `__init__.py`
- [ ] Copy test code from guide → `test_full_pipeline.py`
- [ ] Install pytest if needed: `pip install pytest pytest-asyncio`

### Test Fixtures
- [ ] Create auth_token fixture
- [ ] Create sample_pdf_path fixture
- [ ] Verify test database configuration

### Integration Tests
- [ ] Test: Full pipeline (upload → query → anomalies → delete)
- [ ] Test: Error handling (invalid file, non-existent doc)
- [ ] Test: Authentication flow (signup → login → protected endpoint)
- [ ] Run: `pytest tests/integration/ -v`
- [ ] All tests passing? ✓

---

## 📄 Week 5: Test Data & Validation

### Test PDF Generation
- [ ] Install reportlab: `pip install reportlab`
- [ ] Copy script from guide → `backend/scripts/create_test_pdfs.py`
- [ ] Run: `python scripts/create_test_pdfs.py`
- [ ] Verify created: `data/test_samples/simple_tos.pdf`
- [ ] Verify created: `data/test_samples/risky_tos.pdf`
- [ ] Open PDFs to inspect content

### Manual Testing with Real PDFs
- [ ] Upload simple_tos.pdf via API
- [ ] Check processing completed successfully
- [ ] Query: "What are the terms?"
- [ ] Verify answer with citations
- [ ] Upload risky_tos.pdf
- [ ] Check anomalies detected
- [ ] Verify high-severity anomalies present
- [ ] Test delete document

### Performance Validation
- [ ] Upload 20-page PDF
- [ ] Time: < 30 seconds?
- [ ] Query processing: < 2 seconds?
- [ ] Anomaly detection completed?
- [ ] Check logs for errors
- [ ] Memory usage acceptable?

---

## ✅ Final Verification

### API Completeness
- [ ] All endpoints return correct status codes
- [ ] Error responses are descriptive
- [ ] OpenAPI docs complete and accurate
- [ ] All endpoints require authentication (except auth endpoints)

### Data Quality
- [ ] Documents stored in database correctly
- [ ] Vectors stored in Pinecone (check index stats)
- [ ] Clauses extracted accurately
- [ ] Metadata extraction works
- [ ] Anomalies detected for risky clauses

### Code Quality
- [ ] No syntax errors
- [ ] All imports resolve
- [ ] Type hints present
- [ ] Docstrings complete
- [ ] Logging comprehensive
- [ ] No hardcoded secrets

### System Health
- [ ] Health check endpoint responds
- [ ] Services initialize on startup
- [ ] Services cleanup on shutdown
- [ ] No connection leaks
- [ ] Logs are clean (no critical errors)

---

## 🚀 Quick Test Sequence

**Copy-paste these commands to test everything:**

```bash
# 1. Start services
cd "Project T&C"
docker-compose up -d

# 2. Check services
docker ps  # Should see postgres + redis

# 3. Start API
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload

# 4. Test health (in another terminal)
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0"...}

# 5. Test signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123456","full_name":"Test User"}'
# Expected: 201 Created with user data

# 6. Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123456"
# Expected: {"access_token":"...","token_type":"bearer"}

# 7. Save token (replace YOUR_TOKEN_HERE with actual token from step 6)
export TOKEN="YOUR_TOKEN_HERE"

# 8. Test upload
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data/test_samples/simple_tos.pdf"
# Expected: 201 Created with document details
# Save document_id from response

# 9. Test query (replace DOC_ID)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id":"DOC_ID","question":"What are the main terms?"}'
# Expected: Answer with citations

# 10. Test anomalies (replace DOC_ID)
curl -X GET "http://localhost:8000/api/v1/anomalies/DOC_ID" \
  -H "Authorization: Bearer $TOKEN"
# Expected: List of anomalies with stats

# 11. Test list documents
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"
# Expected: List of uploaded documents

# 12. Visit Swagger UI
# Open: http://localhost:8000/api/v1/docs
# Test all endpoints interactively
```

---

## 🎯 Success Criteria

### Must Have (Critical)
- [x] Upload endpoint works end-to-end
- [ ] Query returns answers with citations
- [ ] Authentication (signup/login) works
- [ ] Anomalies are detected and listed
- [ ] All integration tests pass

### Should Have (Important)
- [ ] Error handling comprehensive
- [ ] Services shut down gracefully
- [ ] Test PDFs generate correctly
- [ ] Performance meets targets (< 30s upload, < 2s query)
- [ ] OpenAPI docs complete

### Nice to Have (Optional)
- [ ] Query results cached (Redis)
- [ ] Anomaly filtering by section
- [ ] Document comparison endpoint
- [ ] Rate limiting configured

---

## 📊 Time Estimate

- Query endpoint: **30-45 minutes**
- Auth endpoint: **30-45 minutes**
- Anomalies endpoint: **30-45 minutes**
- Router integration: **15 minutes**
- Service cleanup: **15 minutes**
- Integration tests: **45-60 minutes**
- Test PDFs: **15 minutes**
- Manual testing: **30-45 minutes**

**Total: 4-5 hours of focused work**

---

## 💡 Tips

### If Stuck:
1. Check `WEEK_3_5_COMPLETION_GUIDE.md` for exact code
2. Review error messages carefully
3. Check logs: `docker-compose logs -f` (services) or terminal output (API)
4. Verify services running: `docker ps`
5. Test with Postman/Swagger UI instead of curl

### Common Issues:
- **Import errors**: Run `pip install -r requirements.txt` again
- **Connection refused**: Check Docker services running
- **401 Unauthorized**: Verify token in Authorization header
- **404 Not found**: Check router is included in main.py
- **422 Validation error**: Check request body matches schema

### Best Practices:
- Test each endpoint immediately after implementation
- Use Swagger UI for interactive testing
- Check logs after each request
- Commit after each working endpoint
- Keep terminal output visible for errors

---

## 🏁 Done?

When all checkboxes are checked:

✅ **Week 3-5 COMPLETE!**

You now have:
- Full API with all endpoints working
- Comprehensive testing suite
- Test data for development
- Production-ready error handling
- Complete OpenAPI documentation

**Next:** Week 6 - Data Collection (100+ baseline T&Cs)

---

**Print this checklist and check off items as you complete them!**

**Estimated completion time**: 4-5 hours

**You've got this! 🚀**
