# 🚀 Supabase Deployment Guide - T&C Analysis System

Complete guide to deploy your T&C Analysis System using Supabase + Railway/Render.

---

## 📋 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│                    (Vercel/Netlify)                          │
│                   React + TypeScript                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND API                             │
│                   (Railway/Render)                           │
│                    FastAPI + Python                          │
└──┬──────────┬──────────┬──────────┬─────────┬──────────────┘
   │          │          │          │         │
   ▼          ▼          ▼          ▼         ▼
┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│Supa- │ │Supa-   │ │Pinecone│ │OpenAI  │ │ Upstash  │
│base  │ │base    │ │Vector  │ │API     │ │ Redis    │
│DB    │ │Storage │ │DB      │ │        │ │ (Cache)  │
└──────┘ └────────┘ └────────┘ └────────┘ └──────────┘
```

---

## 🎯 PHASE 1: Set Up Supabase (15 minutes)

### Step 1.1: Create Supabase Project

1. **Go to**: https://supabase.com
2. **Click**: "Start your project"
3. **Sign up** with GitHub/Google
4. **Create New Project**:
   - Organization: Create new or select existing
   - Name: `tc-analysis`
   - Database Password: Generate strong password (SAVE THIS!)
   - Region: Choose closest to you
   - Pricing Plan: Free

5. **Wait 2-3 minutes** for project initialization

### Step 1.2: Get Supabase Credentials

Once project is ready:

1. Go to **Settings** → **API**
2. Copy these values:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbG...long-key
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...longer-key (keep secret!)
```

3. Go to **Settings** → **Database**
4. Copy:

```env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
```

### Step 1.3: Set Up Database Schema

1. Go to **SQL Editor** in Supabase dashboard
2. Click **New Query**
3. Paste this SQL:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (Supabase handles auth, but we need user metadata)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status TEXT DEFAULT 'pending',
    
    -- Metadata extracted from document
    company_name TEXT,
    jurisdiction TEXT,
    effective_date DATE,
    document_type TEXT,
    
    -- Processing results
    total_sections INTEGER DEFAULT 0,
    total_clauses INTEGER DEFAULT 0,
    risk_score FLOAT,
    
    -- Pinecone reference
    pinecone_namespace TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Clauses table
CREATE TABLE clauses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    section TEXT NOT NULL,
    subsection TEXT,
    clause_number TEXT,
    text TEXT NOT NULL,
    level INTEGER DEFAULT 0,
    chunk_index INTEGER DEFAULT 0,
    
    -- Vector reference
    vector_id TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Anomalies table
CREATE TABLE anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    clause_id UUID REFERENCES clauses(id) ON DELETE CASCADE,
    
    -- Anomaly details
    anomaly_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
    description TEXT NOT NULL,
    explanation TEXT,
    
    -- Scoring
    prevalence_score FLOAT,
    risk_flags TEXT[],
    
    -- Context
    section TEXT,
    clause_text TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Queries table (optional - for analytics)
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence FLOAT,
    sources JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_clauses_document_id ON clauses(document_id);
CREATE INDEX idx_anomalies_document_id ON anomalies(document_id);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);
CREATE INDEX idx_queries_document_id ON queries(document_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

4. **Click "Run"**
5. Verify: Go to **Table Editor** → You should see all tables

### Step 1.4: Set Up Storage for PDFs

1. Go to **Storage** in Supabase dashboard
2. Click **Create a new bucket**
3. Settings:
   - Name: `documents`
   - Public: OFF (private)
   - File size limit: 50MB
   - Allowed MIME types: `application/pdf`
4. Click **Create bucket**

5. **Set Storage Policies**:
   - Click on `documents` bucket
   - Go to **Policies** tab
   - Add these policies:

**Policy 1: Users can upload their own files**
```sql
CREATE POLICY "Users can upload documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
```

**Policy 2: Users can read their own files**
```sql
CREATE POLICY "Users can view their documents"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
```

**Policy 3: Users can delete their own files**
```sql
CREATE POLICY "Users can delete their documents"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
```

### Step 1.5: Configure Authentication

1. Go to **Authentication** → **Providers**
2. Enable **Email** provider (already enabled)
3. Optional: Enable **Google**, **GitHub** for social login
4. Go to **Authentication** → **URL Configuration**
   - Site URL: `http://localhost:5173` (change later to production URL)
   - Redirect URLs: Add `http://localhost:5173/**`

---

## 🎯 PHASE 2: Set Up External Services (10 minutes)

### Step 2.1: Upstash Redis (Optional - for caching)

1. **Go to**: https://upstash.com
2. **Sign up** with GitHub
3. **Create Redis Database**:
   - Name: `tc-analysis-cache`
   - Type: Regional
   - Region: Choose closest
   - TLS: Enabled
4. **Copy credentials**:

```env
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
```

**Alternative**: Skip Redis, remove caching from code (app will still work)

### Step 2.2: Verify Pinecone Setup

You already have Pinecone configured. Just verify:

1. Go to: https://app.pinecone.io
2. Check your index exists
3. Note your credentials (already in `.env`)

### Step 2.3: Verify OpenAI Setup

1. Go to: https://platform.openai.com/api-keys
2. Verify API key is active
3. Check usage limits

---

## 🎯 PHASE 3: Update Backend for Supabase (20 minutes)

### Step 3.1: Update Backend Dependencies

Add Supabase client to requirements:

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"
```

Add to `requirements.txt`:
```txt
supabase==2.3.0
storage3==0.7.0
```

Install:
```bash
source venv/bin/activate
pip install supabase storage3
```

### Step 3.2: Update Environment Variables

Update `backend/.env`:

```env
# App Settings
APP_NAME=T&C Analysis API
ENVIRONMENT=production
DEBUG=False

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres

# OpenAI (keep existing)
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL_GPT4=gpt-4
OPENAI_MODEL_GPT35=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Pinecone (keep existing)
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=your-index-name

# Redis (Upstash or remove if skipping cache)
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# JWT (keep existing)
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (update with your frontend URL)
BACKEND_CORS_ORIGINS=["http://localhost:5173","https://your-app.vercel.app"]

# Storage
STORAGE_BUCKET_NAME=documents
```

### Step 3.3: Create Supabase Service

Create `backend/app/services/supabase_service.py`:

```python
"""
Supabase client service for database and storage operations.
"""

from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseService:
    """Supabase client wrapper."""
    
    def __init__(self):
        self.client: Client = None
    
    async def initialize(self):
        """Initialize Supabase client."""
        try:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
            raise
    
    async def close(self):
        """Cleanup Supabase client."""
        # Supabase client doesn't need explicit cleanup
        pass
    
    def get_client(self) -> Client:
        """Get Supabase client instance."""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        return self.client
    
    async def upload_file(self, user_id: str, file_path: str, file_data: bytes) -> str:
        """
        Upload file to Supabase Storage.
        
        Args:
            user_id: User ID for folder organization
            file_path: Original filename
            file_data: File bytes
        
        Returns:
            Storage path of uploaded file
        """
        try:
            storage_path = f"{user_id}/{file_path}"
            
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "application/pdf"}
            )
            
            logger.info(f"File uploaded to Supabase Storage: {storage_path}")
            return storage_path
        
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    async def download_file(self, storage_path: str) -> bytes:
        """Download file from Supabase Storage."""
        try:
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).download(storage_path)
            return result
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise
    
    async def delete_file(self, storage_path: str):
        """Delete file from Supabase Storage."""
        try:
            self.client.storage.from_(settings.STORAGE_BUCKET_NAME).remove([storage_path])
            logger.info(f"File deleted: {storage_path}")
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise
    
    async def get_file_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Get signed URL for file download.
        
        Args:
            storage_path: Path in storage
            expires_in: URL expiration in seconds (default 1 hour)
        
        Returns:
            Signed URL
        """
        try:
            result = self.client.storage.from_(settings.STORAGE_BUCKET_NAME).create_signed_url(
                storage_path,
                expires_in
            )
            return result["signedURL"]
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            raise
```

### Step 3.4: Update Config

Update `backend/app/core/config.py`:

```python
# Add Supabase settings
SUPABASE_URL: str
SUPABASE_ANON_KEY: str
SUPABASE_SERVICE_ROLE_KEY: str
STORAGE_BUCKET_NAME: str = "documents"
```

### Step 3.5: Update Main App

Update `backend/app/main.py` lifespan to include Supabase:

```python
from app.services.supabase_service import SupabaseService

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up T&C Analysis API...")
    
    init_failures = []
    
    # Initialize Supabase (REQUIRED)
    try:
        app.state.supabase = SupabaseService()
        await app.state.supabase.initialize()
        logger.info("✓ Supabase initialized")
    except Exception as e:
        logger.error(f"✗ Supabase initialization failed: {e}")
        init_failures.append(f"Supabase: {e}")
        app.state.supabase = None
    
    # ... rest of initialization (cache, pinecone, openai)
    
    # FAIL FAST if required services failed
    if init_failures:
        error_msg = "Critical services failed to initialize:\n" + "\n".join(
            f"  - {err}" for err in init_failures
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("✓ All services initialized successfully!")
    
    yield
    
    # Shutdown
    if app.state.supabase:
        await app.state.supabase.close()
        logger.info("✓ Supabase disconnected")
    
    # ... rest of shutdown
```

---

## 🎯 PHASE 4: Deploy Backend to Railway (15 minutes)

Railway is the easiest way to deploy FastAPI with PostgreSQL.

### Step 4.1: Prepare Backend for Deployment

1. **Create `Procfile`** in `backend/`:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

2. **Update `Dockerfile`** (if it exists) or create:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

3. **Create `.railwayignore`**:

```
venv/
__pycache__/
*.pyc
.env
.env.local
tests/
.pytest_cache/
*.db
data/
scripts/
```

### Step 4.2: Deploy to Railway

1. **Go to**: https://railway.app
2. **Sign up** with GitHub
3. **Click**: "New Project"
4. **Select**: "Deploy from GitHub repo"
5. **Connect** your GitHub account
6. **Select** your repository
7. **Configure**:
   - Root Directory: `backend`
   - Build Command: (leave default)
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

8. **Add Environment Variables**:

Click **Variables** → **Raw Editor** → Paste:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL_GPT4=gpt-4
OPENAI_MODEL_GPT35=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=your-index-name
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
SECRET_KEY=your-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
DEBUG=False
BACKEND_CORS_ORIGINS=["https://your-frontend.vercel.app"]
STORAGE_BUCKET_NAME=documents
```

9. **Deploy**: Railway will auto-deploy
10. **Get URL**: Copy your deployment URL (e.g., `https://your-app.railway.app`)

---

## 🎯 PHASE 5: Deploy Frontend (10 minutes)

### Step 5.1: Update Frontend Environment

Update `frontend/.env.local`:

```env
VITE_API_URL=https://your-backend.railway.app/api/v1
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Step 5.2: Deploy to Vercel

1. **Go to**: https://vercel.com
2. **Sign up** with GitHub
3. **Click**: "Add New Project"
4. **Import** your GitHub repository
5. **Configure**:
   - Framework Preset: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

6. **Add Environment Variables**:

```env
VITE_API_URL=https://your-backend.railway.app/api/v1
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

7. **Deploy**: Click "Deploy"
8. **Get URL**: Copy your Vercel URL

### Step 5.3: Update CORS in Backend

Go back to Railway → Update `BACKEND_CORS_ORIGINS`:

```env
BACKEND_CORS_ORIGINS=["https://your-frontend.vercel.app"]
```

---

## ✅ PHASE 6: Test Deployment

### Test Checklist:

1. **Backend Health**:
   - Visit: `https://your-backend.railway.app/health`
   - Should return: `{"status": "healthy"}`

2. **Frontend Access**:
   - Visit: `https://your-frontend.vercel.app`
   - Should load homepage

3. **End-to-End Test**:
   - Sign up for account
   - Upload a PDF
   - View analysis results
   - Check anomalies
   - Ask a question

---

## 💰 Cost Breakdown

| Service | Plan | Cost | What You Get |
|---------|------|------|--------------|
| **Supabase** | Free | $0 | 500MB DB, 1GB storage, 2GB bandwidth |
| **Railway** | Free Trial | $5/month after | 512MB RAM, 1GB storage |
| **Vercel** | Free | $0 | Unlimited deployments |
| **Upstash Redis** | Free | $0 | 10K commands/day |
| **Pinecone** | Free | $0 | 100K vectors |
| **OpenAI** | Pay-as-go | ~$0.60/doc | Embeddings + GPT-4 |

**Total**: ~$5/month + OpenAI usage

---

## 🔧 Troubleshooting

### Backend won't start on Railway

**Check logs**: Railway Dashboard → Logs

Common issues:
- Missing environment variables
- Database connection failed
- Port binding (use `$PORT` not hardcoded)

**Solution**:
```bash
# Verify all env vars are set
# Check DATABASE_URL format
# Ensure uvicorn binds to $PORT
```

### Frontend can't connect to backend

**Check**:
1. CORS settings in backend
2. API URL in frontend env
3. Backend is running

**Solution**:
```bash
# Update BACKEND_CORS_ORIGINS
# Clear browser cache
# Check network tab in browser DevTools
```

### Database migrations

If you need to run migrations:

```bash
# Connect to Railway
railway login
railway link

# Run migrations
railway run alembic upgrade head
```

### File uploads fail

**Check**:
1. Supabase storage bucket exists
2. Storage policies are set
3. File size < 50MB

---

## 🚀 Going to Production

### Before launch:

1. **Update secrets**:
   - Generate strong SECRET_KEY
   - Rotate API keys
   - Enable 2FA on all services

2. **Add custom domain**:
   - Vercel: Settings → Domains
   - Railway: Settings → Domains
   - Update CORS accordingly

3. **Enable monitoring**:
   - Railway: Built-in metrics
   - Supabase: Database metrics
   - Add Sentry for error tracking

4. **Set up backups**:
   - Supabase: Enable point-in-time recovery
   - Weekly database backups

5. **Load testing**:
   - Test with multiple users
   - Check API rate limits
   - Monitor costs

---

## 📚 Useful Commands

```bash
# Railway CLI
npm install -g @railway/cli
railway login
railway link
railway logs

# Check backend logs
railway logs --service backend

# SSH into backend
railway shell

# Redeploy
git push origin main  # Auto-deploys

# Vercel CLI
npm install -g vercel
vercel login
vercel
vercel --prod
```

---

## ✅ Deployment Checklist

- [ ] Supabase project created
- [ ] Database schema created
- [ ] Storage bucket configured
- [ ] Backend updated for Supabase
- [ ] Backend deployed to Railway
- [ ] Environment variables set
- [ ] Frontend updated with API URL
- [ ] Frontend deployed to Vercel
- [ ] CORS configured
- [ ] End-to-end test passed
- [ ] Custom domain added (optional)
- [ ] Monitoring enabled
- [ ] Backups configured

---

## 🎉 Success!

Your T&C Analysis System is now live!

**URLs**:
- Frontend: `https://your-app.vercel.app`
- Backend: `https://your-backend.railway.app`
- Database: Supabase Dashboard

**Next Steps**:
1. Share with users
2. Collect feedback
3. Monitor usage
4. Scale as needed

---

## 📞 Support

- Supabase: https://supabase.com/docs
- Railway: https://docs.railway.app
- Vercel: https://vercel.com/docs

For issues with this guide, check the logs in each service dashboard.
