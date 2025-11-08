# Pre-Launch Checklist

## Security ✓
- [ ] API keys regenerated and not in Git history
- [ ] .env files in .gitignore
- [ ] JWT SECRET_KEY is strong (64+ chars)
- [ ] Rate limiting enabled
- [ ] CORS configured for production domains

## Infrastructure ✓
- [ ] PostgreSQL running and migrated
- [ ] Redis running (optional but recommended)
- [ ] Pinecone index created
- [ ] Baseline corpus indexed (1000+ vectors)
- [ ] Docker Compose configured

## Functionality ✓
- [ ] Document upload works end-to-end
- [ ] Anomaly detection completes
- [ ] Q&A queries return answers
- [ ] Comparison feature works
- [ ] Background tasks process correctly

## Testing ✓
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Diagnostic script shows all green
- [ ] Uploaded test document analyzed successfully

## Performance ✓
- [ ] Upload completes in <10 seconds
- [ ] Anomaly detection completes in <60 seconds
- [ ] Queries return in <3 seconds
- [ ] Baseline corpus has 100+ documents

## Documentation ✓
- [ ] README.md updated
- [ ] API documentation complete
- [ ] Environment setup guide written
- [ ] Troubleshooting guide created

## Deployment ✓
- [ ] Backend deployed (Railway/Render/etc)
- [ ] Frontend deployed (Netlify)
- [ ] Environment variables configured in production
- [ ] Database backups configured
- [ ] Monitoring/logging set up

---

## Quick Verification Commands

### Check Services
```bash
python scripts/diagnose_system.py
```

### Run Tests
```bash
pytest
```

### Test Upload Manually
```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/test.pdf"
```

### Check Baseline Corpus
```bash
python -c "
from app.services.pinecone_service import PineconeService
import asyncio

async def check():
    p = PineconeService()
    await p.initialize()
    stats = p.index.describe_index_stats()
    print(f\"Baseline: {stats['namespaces'].get('baseline', {}).get('vector_count', 0)} vectors\")

asyncio.run(check())
"
```

---

## Current System Status (Auto-Generated)

Run `python scripts/diagnose_system.py` to get current status.

### Known Issues to Fix Before Launch

1. **PostgreSQL**: Start Docker or local PostgreSQL service
   ```bash
   # Option 1: Docker
   docker-compose up -d postgres redis

   # Option 2: Local
   brew services start postgresql@15
   ```

2. **Database Tables**: Run migrations
   ```bash
   cd backend
   alembic upgrade head
   ```

3. **Test Data**: Upload at least one test document to verify pipeline

---

## Post-Launch Monitoring

### Health Check Endpoints
- Backend: `https://your-api.com/health`
- Frontend: Check app loads without errors

### Key Metrics to Monitor
- **Upload Success Rate**: Should be >95%
- **Average Processing Time**: <30s per document
- **API Response Times**:
  - Upload: <10s
  - Query: <3s
  - Anomaly Detection: <60s
- **Error Rate**: <1%

### Alerts to Set Up
- Database connection failures
- OpenAI API rate limits exceeded
- Pinecone query failures
- High error rate (>5% in 5 minutes)
- Slow response times (>10s average)

---

## Rollback Plan

If critical issues occur post-launch:

1. **Frontend**: Revert to previous Netlify deploy (one-click)
2. **Backend**: Revert to previous commit and redeploy
3. **Database**: Restore from backup
   ```bash
   pg_restore -d tcanalysis backup_file.sql
   ```

---

## Launch Day Tasks

### Morning (Pre-Launch)
- [ ] Run full diagnostic: `python scripts/diagnose_system.py`
- [ ] Run all tests: `pytest`
- [ ] Verify baseline corpus: Should have 1000+ vectors
- [ ] Test upload with sample PDF
- [ ] Check all environment variables in production
- [ ] Verify CORS settings

### Deployment
- [ ] Deploy backend to production
- [ ] Run database migrations in production
- [ ] Deploy frontend to production
- [ ] Update environment variables to production URLs
- [ ] Test end-to-end flow in production

### Post-Launch (Monitoring)
- [ ] Monitor error logs for 1 hour
- [ ] Test upload from production frontend
- [ ] Verify anomaly detection works
- [ ] Check Q&A queries
- [ ] Monitor API response times
- [ ] Check database connection pool usage

---

## Success Criteria

### Minimum Viable Product (MVP)
- ✅ Users can upload PDF T&C documents
- ✅ System extracts text and structure
- ✅ Anomaly detection identifies risky clauses
- ✅ Users can ask questions about documents
- ✅ System compares multiple documents
- ✅ Results display in friendly UI

### Performance Targets
- Upload + Analysis: <30 seconds
- Q&A Query: <3 seconds
- Uptime: >99%
- Error Rate: <1%

### Security Requirements
- ✅ Authentication required for all endpoints
- ✅ Rate limiting prevents abuse
- ✅ Sensitive data encrypted at rest
- ✅ API keys not exposed in frontend
- ✅ CORS properly configured

---

## Contact for Issues

- **Technical Issues**: Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **GitHub Issues**: [Project Issues](https://github.com/your-repo/issues)
- **Emergency**: Contact project maintainer

---

## Version History

- **v1.0.0** - Initial MVP Launch
  - Document upload and analysis
  - Anomaly detection with baseline corpus
  - Q&A functionality
  - Document comparison
  - Rate limiting
  - Docker support
  - Integration tests
