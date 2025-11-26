# 🚀 Deployment Guide: Supabase + Netlify + Railway

This guide covers deploying your T&C Analysis System to production:
- **Supabase**: PostgreSQL database
- **Netlify**: Frontend (React)
- **Railway**: Backend (FastAPI) - *Netlify can't host Python backends*

---

## 📋 Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Netlify      │────▶│    Railway      │────▶│   Supabase      │
│   (Frontend)    │     │   (Backend)     │     │  (PostgreSQL)   │
│   React App     │     │   FastAPI       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Pinecone      │
                        │  (Vector DB)    │
                        └─────────────────┘
```

---

## 🗄️ Part 1: Supabase Setup (Database)

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click **"New Project"**
3. Fill in:
   - **Name**: `tc-analysis`
   - **Database Password**: Generate a strong password (SAVE THIS!)
   - **Region**: Choose closest to your users
4. Click **"Create new project"** (takes ~2 minutes)

### Step 2: Get Database Connection String

1. In your Supabase dashboard, go to **Settings** → **Database**
2. Scroll to **"Connection string"** section
3. Select **"URI"** tab
4. Copy the connection string, it looks like:
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. Replace `[password]` with your actual database password

### Step 3: Configure Connection Pooling (Important!)

For production, use **connection pooling**:

1. In Supabase dashboard → **Settings** → **Database**
2. Find **"Connection Pooling"** section
3. Copy the **"Transaction"** mode connection string:
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true
   ```

### Step 4: Run Database Migrations

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Set the Supabase DATABASE_URL temporarily
export DATABASE_URL="postgresql://postgres.[your-project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"

# Activate virtual environment
source venv/bin/activate

# Run Alembic migrations
alembic upgrade head
```

---

## 🖥️ Part 2: Railway Setup (Backend)

### Step 1: Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub (recommended for auto-deploy)

### Step 2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Connect your GitHub account if needed
4. Select your repository (or create one first - see below)

### Step 3: Push Code to GitHub (if not already)

```bash
cd "/Users/akhil/Desktop/Project T&C"

# Initialize git if needed
git init

# Create .gitignore if not exists
cat >> .gitignore << 'EOF'
# Environment
.env
backend/.env
frontend/.env.local

# Python
__pycache__/
*.pyc
venv/
.pytest_cache/

# Node
node_modules/
dist/

# IDE
.vscode/
.idea/

# OS
.DS_Store
EOF

# Add and commit
git add .
git commit -m "Initial commit for deployment"

# Create GitHub repo and push
# Go to github.com/new, create repo named "tc-analysis"
git remote add origin https://github.com/YOUR_USERNAME/tc-analysis.git
git branch -M main
git push -u origin main
```

### Step 4: Configure Railway Service

1. In Railway, after connecting your repo:
2. Click on the service → **Settings**
3. Set **Root Directory**: `backend`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 5: Add Environment Variables in Railway

Go to **Variables** tab and add:

```env
# App Settings
APP_NAME=T&C Analysis API
DEBUG=false
ENVIRONMENT=production
API_V1_PREFIX=/api/v1

# Database (Supabase)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true

# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Pinecone
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=tc-analysis

# Auth
SECRET_KEY=your-super-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS (will update after Netlify deploy)
BACKEND_CORS_ORIGINS=["https://your-app.netlify.app","http://localhost:5173"]

# Redis (Optional - Railway Redis add-on or leave empty)
REDIS_URL=

# Rate Limiting
RATE_LIMIT_PER_HOUR=100
```

### Step 6: Add Redis (Optional but Recommended)

1. In Railway project, click **"+ New"**
2. Select **"Database"** → **"Redis"**
3. Copy the connection URL from Redis service variables
4. Add to your backend service variables:
   ```
   REDIS_URL=redis://default:password@containers-us-west-xxx.railway.app:6379
   ```

### Step 7: Deploy

Railway auto-deploys on git push. Check **Deployments** tab for status.

Your backend URL will be: `https://tc-analysis-production.up.railway.app`

---

## 🌐 Part 3: Netlify Setup (Frontend)

### Step 1: Update Frontend for Production

First, update the API configuration:

**Create/Update `frontend/.env.production`:**
```env
VITE_API_URL=https://your-railway-app.up.railway.app
```

### Step 2: Create Netlify Configuration

**Create `frontend/netlify.toml`:**
```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "18"

# Handle SPA routing - redirect all routes to index.html
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

# Proxy API calls to backend (alternative to CORS)
[[redirects]]
  from = "/api/*"
  to = "https://your-railway-app.up.railway.app/api/:splat"
  status = 200
  force = true
```

### Step 3: Update Vite Config for Production

**Update `frontend/vite.config.ts`:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  // Remove proxy in production - Netlify redirects handle it
})
```

### Step 4: Update API Service for Production

**Update `frontend/src/services/api.ts`:**
```typescript
import axios from 'axios';

// Use environment variable or fallback to relative URL (for Netlify proxy)
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ... rest of the file stays the same
```

### Step 5: Deploy to Netlify

**Option A: Netlify CLI (Recommended)**

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login to Netlify
netlify login

# Navigate to frontend
cd "/Users/akhil/Desktop/Project T&C/frontend"

# Initialize and deploy
netlify init

# Follow prompts:
# - Create & configure a new site
# - Team: Your team
# - Site name: tc-analysis (or auto-generate)
# - Build command: npm run build
# - Publish directory: dist

# Deploy
netlify deploy --prod
```

**Option B: Netlify Dashboard**

1. Go to [app.netlify.com](https://app.netlify.com)
2. Click **"Add new site"** → **"Import an existing project"**
3. Connect to GitHub
4. Select your repository
5. Configure build settings:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
6. Click **"Deploy site"**

### Step 6: Add Environment Variables in Netlify

1. Go to **Site settings** → **Environment variables**
2. Add:
   ```
   VITE_API_URL = https://your-railway-app.up.railway.app
   ```
3. Trigger redeploy: **Deploys** → **Trigger deploy** → **Deploy site**

---

## 🔄 Part 4: Connect Everything

### Step 1: Update CORS in Railway

After getting your Netlify URL (e.g., `https://tc-analysis.netlify.app`):

1. Go to Railway → Your backend service → **Variables**
2. Update `BACKEND_CORS_ORIGINS`:
   ```
   BACKEND_CORS_ORIGINS=["https://tc-analysis.netlify.app","https://your-custom-domain.com"]
   ```
3. Railway will auto-redeploy

### Step 2: Update Netlify Redirects

Update `frontend/netlify.toml` with your actual Railway URL:
```toml
[[redirects]]
  from = "/api/*"
  to = "https://tc-analysis-production.up.railway.app/api/:splat"
  status = 200
  force = true
```

Commit and push - Netlify will auto-redeploy.

### Step 3: Run Database Migrations (Final)

```bash
# Connect to Railway backend shell or run locally with production DATABASE_URL
cd "/Users/akhil/Desktop/Project T&C/backend"
export DATABASE_URL="your-supabase-connection-string"
source venv/bin/activate
alembic upgrade head
```

---

## ✅ Part 5: Verification Checklist

### Test Backend (Railway)
```bash
# Health check
curl https://your-railway-app.up.railway.app/health

# Expected response:
# {"status":"healthy","version":"1.0.0","environment":"production"}

# Services health
curl https://your-railway-app.up.railway.app/health/services
```

### Test Frontend (Netlify)
1. Open `https://your-app.netlify.app`
2. Try signing up
3. Upload a test PDF
4. Verify analysis works

### Test Database (Supabase)
1. Go to Supabase dashboard → **Table Editor**
2. Check if tables were created (users, documents, clauses, anomalies)

---

## 🔧 Part 6: Troubleshooting

### Common Issues

**1. CORS Errors**
```
Access to XMLHttpRequest blocked by CORS policy
```
**Fix**: Ensure `BACKEND_CORS_ORIGINS` in Railway includes your Netlify URL exactly.

**2. Database Connection Errors**
```
connection refused / timeout
```
**Fix**: 
- Use the connection pooler URL (port 6543, not 5432)
- Add `?pgbouncer=true` to connection string
- Check Supabase dashboard for connection limits

**3. 404 on Page Refresh (Netlify)**
```
Page not found
```
**Fix**: Ensure `netlify.toml` has the SPA redirect rule.

**4. Environment Variables Not Working**
**Fix**: 
- Netlify: Prefix with `VITE_` for client-side access
- Redeploy after adding variables

**5. Build Fails on Netlify**
```
npm ERR! code ERESOLVE
```
**Fix**: Add to `netlify.toml`:
```toml
[build.environment]
  NPM_FLAGS = "--legacy-peer-deps"
```

---

## 💰 Cost Breakdown

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| **Supabase** | 500MB DB, 1GB storage | $25/mo (8GB DB) |
| **Railway** | $5 free credits/mo | ~$5-20/mo |
| **Netlify** | 100GB bandwidth | $19/mo |
| **Pinecone** | 100K vectors | $70/mo (1M vectors) |
| **OpenAI** | Pay per use | ~$0.50/document |

**Estimated Monthly Cost**: $5-30 for moderate usage

---

## 🚀 Quick Deploy Commands Summary

```bash
# 1. Push to GitHub
cd "/Users/akhil/Desktop/Project T&C"
git add .
git commit -m "Deploy to production"
git push origin main

# 2. Run migrations (one-time)
cd backend
export DATABASE_URL="your-supabase-url"
source venv/bin/activate
alembic upgrade head

# 3. Deploy frontend manually (if needed)
cd frontend
netlify deploy --prod
```

---

## 📝 Environment Variables Summary

### Railway (Backend)
```env
APP_NAME=T&C Analysis API
DEBUG=false
ENVIRONMENT=production
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql://postgres.[ref]:[pass]@aws-0-[region].pooler.supabase.com:6543/postgres?pgbouncer=true
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...
PINECONE_INDEX_NAME=tc-analysis
SECRET_KEY=your-32-char-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BACKEND_CORS_ORIGINS=["https://your-app.netlify.app"]
REDIS_URL=redis://...
RATE_LIMIT_PER_HOUR=100
```

### Netlify (Frontend)
```env
VITE_API_URL=https://your-railway-app.up.railway.app
```

---

## 🎉 Done!

Your T&C Analysis System is now deployed:
- **Frontend**: `https://your-app.netlify.app`
- **Backend API**: `https://your-app.up.railway.app`
- **Database**: Supabase PostgreSQL

Next steps:
1. Set up custom domain (optional)
2. Configure CI/CD for auto-deploys
3. Set up monitoring (Railway metrics, Netlify Analytics)
4. Index baseline corpus for anomaly detection
