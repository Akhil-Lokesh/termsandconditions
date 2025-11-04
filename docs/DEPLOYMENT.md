# Deployment Guide

## Overview

This guide covers deploying the T&C Analysis System to production.

**Architecture**:
- Frontend: Netlify (static React app)
- Backend: Railway or Render (FastAPI + Docker)
- Database: Managed PostgreSQL (Railway/Render)
- Cache: Upstash Redis or Redis Cloud
- Vector DB: Pinecone (managed)

---

## Prerequisites

Before deploying:

- [ ] GitHub repository set up
- [ ] OpenAI API key
- [ ] Pinecone account and API key
- [ ] Domain name (optional)
- [ ] Payment method for hosting services

---

## Backend Deployment

### Option 1: Deploy to Railway

#### 1. Create Railway Account

Sign up at [railway.app](https://railway.app)

#### 2. Create New Project

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
cd backend
railway init
```

#### 3. Add PostgreSQL

In Railway dashboard:
1. Click "New"
2. Select "Database" → "PostgreSQL"
3. Note connection string

#### 4. Add Redis

1. Click "New"
2. Select "Database" → "Redis"
3. Note connection string

#### 5. Configure Environment Variables

In Railway dashboard, add:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX_USER=tc-analysis-user
PINECONE_INDEX_BASELINE=tc-analysis-baseline
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
SECRET_KEY=<generate-new-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
DEBUG=False
BACKEND_CORS_ORIGINS=["https://yourdomain.netlify.app"]
```

#### 6. Deploy

```bash
# Deploy backend
railway up

# Run migrations
railway run alembic upgrade head
```

#### 7. Get Backend URL

```bash
railway domain
# Note: https://your-project.up.railway.app
```

---

### Option 2: Deploy to Render

#### 1. Create Render Account

Sign up at [render.com](https://render.com)

#### 2. Create New Web Service

1. Click "New +"
2. Select "Web Service"
3. Connect GitHub repository
4. Select `backend` directory

#### 3. Configure Service

**Settings**:
- Name: `tc-analysis-backend`
- Environment: `Docker`
- Region: Choose closest to users
- Branch: `main`
- Dockerfile Path: `backend/Dockerfile`

**Build Command**: (leave blank for Docker)

**Start Command**: (leave blank for Docker)

#### 4. Add PostgreSQL

1. Click "New +"
2. Select "PostgreSQL"
3. Choose plan (free for dev)
4. Note internal connection string

#### 5. Add Redis

1. Sign up for [Upstash](https://upstash.com/)
2. Create Redis database
3. Note connection string

#### 6. Configure Environment Variables

In Render dashboard:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX_USER=tc-analysis-user
PINECONE_INDEX_BASELINE=tc-analysis-baseline
DATABASE_URL=<from-render-postgres>
REDIS_URL=<from-upstash>
SECRET_KEY=<generate-new-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
DEBUG=False
BACKEND_CORS_ORIGINS=["https://yourdomain.netlify.app"]
```

#### 7. Deploy

Render will auto-deploy from GitHub.

#### 8. Run Migrations

In Render dashboard:
1. Go to "Shell"
2. Run: `alembic upgrade head`

---

## Frontend Deployment

### Deploy to Netlify

#### 1. Create Netlify Account

Sign up at [netlify.com](https://netlify.com)

#### 2. Prepare Frontend

Update environment variables:

```bash
cd frontend

# Create .env.production
cat > .env.production << EOF
VITE_API_URL=https://your-backend.railway.app
VITE_APP_TITLE=T&C Analysis System
EOF
```

#### 3. Build Locally (Test)

```bash
npm run build

# Test production build
npm run preview
```

#### 4. Deploy via Netlify CLI

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Initialize
netlify init

# Deploy
netlify deploy --prod
```

#### 5. Or Deploy via GitHub

1. In Netlify dashboard, click "Add new site"
2. Select "Import from Git"
3. Choose GitHub repository
4. Configure build settings:
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/dist`

#### 6. Add Environment Variables

In Netlify dashboard:
1. Go to "Site settings" → "Environment variables"
2. Add:
   ```
   VITE_API_URL=https://your-backend.railway.app
   ```

#### 7. Configure Redirects

Create `frontend/public/_redirects`:

```
/*    /index.html   200
```

This enables client-side routing.

#### 8. Deploy

Netlify will auto-deploy from GitHub.

---

## Database Setup

### Initialize Production Database

```bash
# Via Railway CLI
railway run alembic upgrade head

# Or via Render Shell
# Go to Render dashboard → Shell
alembic upgrade head
```

---

## Pinecone Setup

### Create Production Indexes

```python
# Run locally with production credentials
from pinecone import Pinecone

pc = Pinecone(api_key="your-pinecone-key")

# Create user index
pc.create_index(
    name="tc-analysis-user-prod",
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)

# Create baseline index
pc.create_index(
    name="tc-analysis-baseline-prod",
    dimension=1536,
    metric="cosine",
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    )
)
```

### Build Baseline Corpus

```bash
# Run baseline corpus script
python scripts/build_baseline_corpus.py --env production

# This will:
# 1. Process all PDFs in data/baseline_corpus/
# 2. Generate embeddings
# 3. Upload to Pinecone baseline namespace
```

---

## Domain Configuration

### Custom Domain (Optional)

#### Backend Domain

**Railway**:
1. Go to project settings
2. Click "Generate Domain"
3. Or add custom domain: `api.yourdomain.com`

**Render**:
1. Go to service settings
2. Click "Custom Domain"
3. Add: `api.yourdomain.com`
4. Update DNS records

#### Frontend Domain

**Netlify**:
1. Go to "Domain settings"
2. Click "Add custom domain"
3. Follow DNS configuration steps

---

## SSL/TLS Certificates

### Automatic (Recommended)

Both Railway, Render, and Netlify provide automatic SSL certificates via Let's Encrypt.

### Custom Certificate

If using custom domain:
1. Obtain certificate from provider
2. Upload to hosting platform
3. Configure in platform settings

---

## Environment-Specific Configuration

### Development

```env
ENVIRONMENT=development
DEBUG=True
DATABASE_URL=postgresql://localhost:5432/tcanalysis
REDIS_URL=redis://localhost:6379
```

### Staging (Optional)

```env
ENVIRONMENT=staging
DEBUG=True
DATABASE_URL=<staging-db-url>
REDIS_URL=<staging-redis-url>
PINECONE_INDEX_USER=tc-analysis-user-staging
```

### Production

```env
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=<production-db-url>
REDIS_URL=<production-redis-url>
PINECONE_INDEX_USER=tc-analysis-user-prod
```

---

## Monitoring & Logging

### Backend Logging

Railway/Render provide built-in log viewing:

```bash
# Railway
railway logs

# Render
# View in dashboard → Logs tab
```

### Application Performance Monitoring

#### Option 1: Sentry

```bash
# Install Sentry SDK
pip install sentry-sdk[fastapi]

# Add to app/main.py
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    environment="production",
)
```

#### Option 2: New Relic

```bash
pip install newrelic

# Add to start command
newrelic-admin run-program uvicorn app.main:app
```

### Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake

Configure to ping:
- `https://api.yourdomain.com/health`

---

## Backup Strategy

### Database Backups

**Railway**: Automatic daily backups (paid plans)

**Render**: Automatic daily backups

**Manual Backup**:
```bash
# Export database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20240115.sql
```

### Pinecone Backups

Pinecone is managed - backups handled automatically.

**Export vectors** (optional):
```python
# Export all vectors
results = index.query(
    vector=[0]*1536,
    top_k=10000,
    include_values=True,
    include_metadata=True
)
# Save to file
```

---

## CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Railway
        run: |
          npm i -g @railway/cli
          railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Build
        working-directory: ./frontend
        run: npm run build
        env:
          VITE_API_URL: ${{ secrets.API_URL }}
      
      - name: Deploy to Netlify
        uses: netlify/actions/cli@master
        with:
          args: deploy --prod --dir=frontend/dist
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
```

---

## Security Checklist

- [ ] HTTPS enabled on all endpoints
- [ ] Environment variables not committed to Git
- [ ] Secret keys are strong and unique
- [ ] Database credentials are secure
- [ ] API rate limiting enabled
- [ ] CORS configured correctly
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using ORM)
- [ ] XSS prevention (sanitized inputs)
- [ ] Authentication required for sensitive endpoints
- [ ] JWT tokens expire properly
- [ ] File upload size limits enforced
- [ ] File type validation enabled
- [ ] Error messages don't leak sensitive info

---

## Cost Estimation

### Monthly Costs (Estimated)

**Backend (Railway/Render)**:
- Hobby plan: $5-10/month
- Starter plan: $20/month

**Database (PostgreSQL)**:
- Free tier: 0.5GB (Railway/Render)
- Paid: $10/month for 10GB

**Redis**:
- Upstash free: 10K commands/day
- Paid: $10/month

**Pinecone**:
- Starter: $70/month (1 pod)
- Serverless: Pay per request (~$20-40/month)

**OpenAI API**:
- Development: ~$10-30/month
- Production: $50-200/month (depends on usage)

**Netlify**:
- Free for personal projects
- Pro: $19/month

**Total Estimate**: $100-400/month depending on usage

---

## Scaling Considerations

### Backend Scaling

**Horizontal Scaling**:
- Railway/Render auto-scale with traffic
- Use managed load balancer

**Vertical Scaling**:
- Upgrade plan for more CPU/RAM
- Monitor resource usage

### Database Scaling

- Use connection pooling (SQLAlchemy)
- Add read replicas for high read load
- Implement query caching (Redis)

### Vector Database Scaling

- Pinecone auto-scales
- Use namespaces for organization
- Monitor query performance

### Caching Strategy

- Cache query responses (30 days)
- Cache embeddings (90 days)
- Monitor cache hit rate
- Increase Redis memory if needed

---

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
railway logs  # or Render logs

# Common issues:
# - Missing environment variables
# - Database connection failed
# - Dependency installation failed
```

### Database Migration Failed

```bash
# Check migration files
alembic history

# Rollback and retry
alembic downgrade -1
alembic upgrade head
```

### Frontend Build Failed

```bash
# Check Netlify logs
# Common issues:
# - Missing environment variables
# - Build command incorrect
# - Node version mismatch
```

### CORS Errors

Update `BACKEND_CORS_ORIGINS` in backend `.env`:

```env
BACKEND_CORS_ORIGINS=["https://yourdomain.netlify.app","https://custom-domain.com"]
```

---

## Post-Deployment

### 1. Verify Deployment

```bash
# Test health endpoint
curl https://api.yourdomain.com/health

# Test frontend
open https://yourdomain.netlify.app
```

### 2. Test Upload Flow

1. Register user
2. Upload test PDF
3. Verify processing completes
4. Check anomaly report
5. Test Q&A

### 3. Monitor Logs

- Check for errors
- Monitor response times
- Track OpenAI API usage

### 4. Set Up Monitoring

- Configure uptime monitoring
- Set up error alerts (Sentry)
- Create status page

---

## Rollback Procedure

### Backend Rollback

**Railway**:
```bash
railway rollback
```

**Render**:
1. Go to "Deploys" tab
2. Find previous deploy
3. Click "Rollback"

### Frontend Rollback

**Netlify**:
1. Go to "Deploys" tab
2. Find previous deploy
3. Click "Publish deploy"

### Database Rollback

```bash
# Rollback migration
alembic downgrade -1
```

---

## Support

For deployment issues:
- Railway: [railway.app/help](https://railway.app/help)
- Render: [render.com/docs](https://render.com/docs)
- Netlify: [docs.netlify.com](https://docs.netlify.com)

---

## Maintenance

### Weekly

- Review error logs
- Check API usage
- Monitor costs

### Monthly

- Review security updates
- Update dependencies
- Backup database

### Quarterly

- Performance optimization
- Security audit
- Cost optimization review
