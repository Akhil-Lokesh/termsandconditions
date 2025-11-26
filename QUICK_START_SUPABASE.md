# 🚀 SUPABASE DEPLOYMENT - QUICK START

**Deploy your T&C Analysis System in 1 hour**

---

## 📋 What You'll Need

- [ ] GitHub account
- [ ] Supabase account (free)
- [ ] Railway account (free trial, then $5/mo)
- [ ] Vercel account (free)
- [ ] OpenAI API key ($$$)
- [ ] Pinecone API key (free tier)

---

## ⚡ 3-Step Deployment

### **STEP 1: Set Up Supabase (20 min)**

#### 1.1 Create Project
1. Go to https://supabase.com → Sign up
2. Create New Project:
   - Name: `tc-analysis`
   - Database Password: **SAVE THIS!**
   - Region: Closest to you

#### 1.2 Run Database Schema
1. Go to **SQL Editor**
2. Open file: `supabase_schema.sql`
3. Copy ENTIRE contents
4. Paste in SQL Editor
5. Click **Run**
6. Verify: Go to **Table Editor** → See 5 tables

#### 1.3 Create Storage
1. Go to **Storage**
2. Create bucket: `documents`
3. Settings:
   - Public: **OFF**
   - Size limit: 50MB
   - MIME types: `application/pdf`

#### 1.4 Copy Credentials
Go to **Settings** → **API**

```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG... (secret!)
```

Go to **Settings** → **Database**

```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres
```

✅ **Supabase Done!**

---

### **STEP 2: Deploy Backend (20 min)**

#### 2.1 Prepare Code
```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Install Supabase (if not already done)
source venv/bin/activate
pip install supabase storage3
```

#### 2.2 Deploy to Railway
1. Go to https://railway.app → Sign up with GitHub
2. Click **New Project** → **Deploy from GitHub**
3. Select your repository
4. Settings:
   - Root Directory: `backend`
   - Build Command: (auto)
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

#### 2.3 Add Environment Variables

Click **Variables** → **RAW Editor** → Paste:

```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
STORAGE_BUCKET_NAME=documents

# OpenAI
OPENAI_API_KEY=sk-proj-xxx
OPENAI_MODEL_GPT4=gpt-4
OPENAI_MODEL_GPT35=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Pinecone
PINECONE_API_KEY=your-key
PINECONE_ENVIRONMENT=your-env
PINECONE_INDEX_NAME=your-index
PINECONE_USER_NAMESPACE=user_tcs
PINECONE_BASELINE_NAMESPACE=baseline

# Redis (Optional - leave blank to skip)
REDIS_URL=

# Security
SECRET_KEY=change-this-to-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Config
APP_NAME=T&C Analysis API
ENVIRONMENT=production
DEBUG=False
API_V1_PREFIX=/api/v1
RATE_LIMIT_PER_HOUR=100
BACKEND_CORS_ORIGINS=["http://localhost:5173"]
```

#### 2.4 Deploy & Test
1. Railway auto-deploys
2. Copy your URL: `https://tc-analysis-production-xxx.railway.app`
3. Test: Visit `https://your-url.railway.app/health`
   - Should show: `{"status": "healthy"}`

✅ **Backend Done!**

---

### **STEP 3: Deploy Frontend (20 min)**

#### 3.1 Update Environment
Edit `frontend/.env.local`:

```env
VITE_API_URL=https://your-backend.railway.app/api/v1
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

#### 3.2 Deploy to Vercel
1. Go to https://vercel.com → Sign up with GitHub
2. Click **Add New** → **Project**
3. Import your repository
4. Settings:
   - Framework: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

#### 3.3 Add Environment Variables

```env
VITE_API_URL=https://your-backend.railway.app/api/v1
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

#### 3.4 Deploy & Test
1. Click **Deploy**
2. Wait 2-3 minutes
3. Copy URL: `https://your-app.vercel.app`
4. Visit URL → Should load homepage

#### 3.5 Fix CORS
Go back to **Railway** → **Variables** → Update:

```env
BACKEND_CORS_ORIGINS=["https://your-app.vercel.app"]
```

✅ **Frontend Done!**

---

## ✅ Test Full System

1. Open: `https://your-app.vercel.app`
2. Click **Sign Up** → Create account
3. Click **Upload Document** → Upload a PDF
4. Wait for processing (30-60 seconds)
5. View analysis results
6. Check anomalies (if any)
7. Ask a question in Q&A

**If all works → 🎉 SUCCESS!**

---

## 🐛 Troubleshooting

### Backend Error: "Supabase client not initialized"
**Fix**: Check all SUPABASE_* variables are set in Railway

### Frontend Error: "CORS"
**Fix**: Add your Vercel URL to BACKEND_CORS_ORIGINS in Railway

### Upload Error: "Storage bucket not found"
**Fix**: 
1. Check bucket named "documents" exists in Supabase
2. Add storage policies (see guide Step 1.3)

### Database Error: "Connection refused"
**Fix**: Verify DATABASE_URL has correct password

---

## 💰 Costs

| Service | Cost |
|---------|------|
| Supabase | Free |
| Railway | $5/month |
| Vercel | Free |
| Pinecone | Free |
| OpenAI | ~$0.60/document |

**Total**: $5/month + usage

---

## 📚 Full Guides

- **Detailed Guide**: `SUPABASE_DEPLOYMENT_GUIDE.md`
- **Checklist**: `DEPLOYMENT_CHECKLIST.md`
- **SQL Schema**: `supabase_schema.sql`

---

## 🎯 Your Deployment URLs

Fill these in as you deploy:

```
Backend:  https://________________________.railway.app
Frontend: https://________________________.vercel.app
Database: https://________________________.supabase.co
```

---

## ⏱️ Time Breakdown

- Supabase Setup: 20 min
- Backend Deploy: 20 min
- Frontend Deploy: 20 min
- **Total: ~1 hour**

---

## 🎉 Next Steps

After deployment:
1. ✅ Share URL with users
2. ✅ Monitor Railway usage
3. ✅ Track OpenAI costs
4. ✅ Add custom domain (optional)
5. ✅ Enable Supabase backups

---

**Questions? Check the full guide or service documentation!**
