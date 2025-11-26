# 🚀 Quick Deployment Checklist

Use this checklist to deploy your T&C Analysis System to production.

---

## ✅ Pre-Deployment (One-Time Setup)

### 1. Supabase Setup (15 min)
- [ ] Create Supabase account at https://supabase.com
- [ ] Create new project
- [ ] Save database password
- [ ] Copy connection strings
  - [ ] SUPABASE_URL
  - [ ] SUPABASE_ANON_KEY  
  - [ ] SUPABASE_SERVICE_ROLE_KEY
  - [ ] DATABASE_URL

### 2. Run Database Schema (5 min)
- [ ] Open Supabase SQL Editor
- [ ] Copy SQL from SUPABASE_DEPLOYMENT_GUIDE.md (Step 1.3)
- [ ] Run the SQL
- [ ] Verify tables created in Table Editor

### 3. Create Storage Bucket (5 min)
- [ ] Go to Storage in Supabase
- [ ] Create bucket named "documents"
- [ ] Set to Private
- [ ] Add storage policies (from guide Step 1.4)

### 4. External Services (10 min)
- [ ] Create Upstash Redis account (optional)
  - [ ] Create database
  - [ ] Copy REDIS_URL
- [ ] Verify Pinecone account
  - [ ] Check index exists
  - [ ] Copy PINECONE_API_KEY
- [ ] Verify OpenAI account
  - [ ] Check API key is active
  - [ ] Copy OPENAI_API_KEY

---

## ✅ Backend Deployment (15 min)

### 1. Update Backend Code
- [ ] Install Supabase dependency:
  ```bash
  cd backend
  source venv/bin/activate
  pip install supabase storage3
  ```
- [ ] Update requirements.txt (already done ✓)
- [ ] Verify Procfile exists (already done ✓)
- [ ] Verify railway.json exists (already done ✓)

### 2. Deploy to Railway
- [ ] Go to https://railway.app
- [ ] Sign up with GitHub
- [ ] Create new project
- [ ] Connect GitHub repository
- [ ] Set root directory to "backend"
- [ ] Add all environment variables (see template below)
- [ ] Deploy
- [ ] Copy Railway URL

### 3. Test Backend
- [ ] Visit: https://your-backend.railway.app/health
- [ ] Should return: `{"status": "healthy"}`
- [ ] Check logs in Railway dashboard

---

## ✅ Frontend Deployment (10 min)

### 1. Update Frontend Environment
- [ ] Edit `frontend/.env.local`:
  ```env
  VITE_API_URL=https://your-backend.railway.app/api/v1
  VITE_SUPABASE_URL=https://your-project.supabase.co
  VITE_SUPABASE_ANON_KEY=your-anon-key
  ```

### 2. Deploy to Vercel
- [ ] Go to https://vercel.com
- [ ] Sign up with GitHub
- [ ] Import repository
- [ ] Set root directory to "frontend"
- [ ] Framework: Vite
- [ ] Add environment variables
- [ ] Deploy
- [ ] Copy Vercel URL

### 3. Update CORS
- [ ] Go back to Railway
- [ ] Update BACKEND_CORS_ORIGINS:
  ```env
  BACKEND_CORS_ORIGINS=["https://your-frontend.vercel.app"]
  ```
- [ ] Redeploy backend

---

## ✅ Final Testing (10 min)

### Test Full Flow
- [ ] Open frontend URL
- [ ] Sign up for account
- [ ] Upload a test PDF
- [ ] Wait for processing
- [ ] View analysis results
- [ ] Check anomalies section
- [ ] Ask a question in Q&A
- [ ] Verify response with citations

### Verify Services
- [ ] Check backend logs (Railway)
- [ ] Check database (Supabase Table Editor)
- [ ] Check file storage (Supabase Storage)
- [ ] Check API usage (OpenAI dashboard)
- [ ] Check vector count (Pinecone console)

---

## 📋 Environment Variables Template

Copy this template and fill in your values:

### Backend (Railway)
```env
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres
STORAGE_BUCKET_NAME=documents

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_MODEL_GPT4=gpt-4
OPENAI_MODEL_GPT35=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Pinecone
PINECONE_API_KEY=xxxxx
PINECONE_ENVIRONMENT=xxxxx
PINECONE_INDEX_NAME=xxxxx
PINECONE_USER_NAMESPACE=user_tcs
PINECONE_BASELINE_NAMESPACE=baseline

# Redis (Optional - Upstash)
REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6379

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App Config
APP_NAME=T&C Analysis API
ENVIRONMENT=production
DEBUG=False
API_V1_PREFIX=/api/v1
RATE_LIMIT_PER_HOUR=100

# CORS (Update with your Vercel URL)
BACKEND_CORS_ORIGINS=["https://your-app.vercel.app"]
```

### Frontend (Vercel)
```env
VITE_API_URL=https://your-backend.railway.app/api/v1
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 🐛 Common Issues

### "Supabase client not initialized"
**Fix**: Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set

### "Database connection failed"
**Fix**: Verify DATABASE_URL format and password

### "CORS error" in browser
**Fix**: Add your Vercel URL to BACKEND_CORS_ORIGINS

### "File upload failed"
**Fix**: Check storage bucket exists and policies are set

### Backend won't start
**Fix**: Check Railway logs for missing environment variables

---

## 💰 Expected Costs

| Service | Tier | Cost |
|---------|------|------|
| Supabase | Free | $0/month |
| Railway | Hobby | $5/month |
| Vercel | Free | $0/month |
| Upstash Redis | Free | $0/month |
| Pinecone | Free | $0/month |
| OpenAI | Pay-as-go | ~$0.60/doc |

**Total Fixed**: $5/month
**Variable**: OpenAI usage based on document volume

---

## 🎯 Success Criteria

Your deployment is successful when:

✅ Backend health endpoint returns `{"status": "healthy"}`
✅ Frontend loads without errors
✅ User can sign up
✅ User can upload PDF
✅ Document is processed
✅ Anomalies are detected (if applicable)
✅ Q&A works with citations
✅ Files appear in Supabase Storage
✅ Records appear in Supabase Database

---

## 📚 Additional Resources

- **Full Guide**: SUPABASE_DEPLOYMENT_GUIDE.md
- **API Reference**: API_REFERENCE.md
- **Troubleshooting**: Check service logs first
- **Supabase Docs**: https://supabase.com/docs
- **Railway Docs**: https://docs.railway.app
- **Vercel Docs**: https://vercel.com/docs

---

## ⏱️ Estimated Time

- **Pre-Deployment Setup**: 30 minutes
- **Backend Deployment**: 15 minutes
- **Frontend Deployment**: 10 minutes
- **Testing**: 10 minutes
- **Total**: ~65 minutes

---

## 🎉 Next Steps After Deployment

1. **Monitor Usage**: 
   - Check Railway metrics
   - Monitor Supabase database size
   - Track OpenAI costs

2. **Set Up Backups**:
   - Enable Supabase point-in-time recovery
   - Export data regularly

3. **Add Custom Domain** (Optional):
   - Configure in Vercel settings
   - Update CORS in backend

4. **Collect User Feedback**:
   - Share with test users
   - Iterate based on feedback

5. **Scale as Needed**:
   - Upgrade Railway if needed
   - Increase Supabase limits
   - Optimize OpenAI usage

---

**Ready to deploy? Start with Step 1! 🚀**
