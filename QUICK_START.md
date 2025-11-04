# Quick Start Guide - Launch in 10 Minutes

**Get your T&C Analysis System running in 3 simple steps.**

---

## Step 1: Start Backend (2 minutes)

```bash
# Navigate to backend
cd "/Users/akhil/Desktop/Project T&C/backend"

# Activate virtual environment
source venv/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ Backend is running at: http://localhost:8000
✅ API docs available at: http://localhost:8000/api/v1/docs

---

## Step 2: Install & Start Frontend (8 minutes)

Open a **new terminal window**:

```bash
# Navigate to frontend
cd "/Users/akhil/Desktop/Project T&C/frontend"

# Install dependencies (~3 min)
npm install

# Initialize shadcn/ui (~2 min)
npx shadcn-ui@latest init
```

**When prompted, answer**:
- TypeScript: **Yes**
- Style: **Default**
- Base color: **Slate**
- CSS variables: **Yes**
- Import alias: **@/***
- React Server Components: **No**
- Write config files: **Yes**

```bash
# Add UI components (~2 min)
npx shadcn-ui@latest add button card input textarea label badge alert dialog tabs separator alert-dialog

# Start dev server (~1 min)
npm run dev
```

**Expected output**:
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

✅ Frontend is running at: http://localhost:5173

---

## Step 3: Test the Application

Open your browser to: **http://localhost:5173**

### Test Flow (5 minutes)

1. **Homepage**
   - Click "Get Started"

2. **Sign Up**
   - Email: `test@example.com`
   - Password: `testpass123`
   - Click "Sign up"
   - Should redirect to dashboard

3. **Dashboard**
   - See empty state (0 documents)
   - Click "Upload Document"

4. **Upload**
   - Drag & drop a PDF file (or click to browse)
   - Click "Upload & Analyze"
   - Wait 20-30 seconds for processing
   - Should redirect to document detail page

5. **Document Detail**
   - See overall risk assessment
   - View document statistics
   - Check "Anomalies" tab
   - Try "Q&A" tab
   - Ask a question (e.g., "What is the refund policy?")

---

## Troubleshooting

### Backend won't start
```bash
# Check if PostgreSQL is running
docker ps

# If not, start it
cd "/Users/akhil/Desktop/Project T&C/backend"
docker-compose up -d
```

### Frontend install fails
```bash
# Clear cache and retry
rm -rf node_modules package-lock.json
npm install
```

### Port already in use
```bash
# Kill existing process
lsof -ti:5173 | xargs kill -9  # Frontend
lsof -ti:8000 | xargs kill -9  # Backend
```

### API calls fail (Network Error)
- Make sure backend is running (check Terminal 1)
- Verify backend URL in `.env.local`: `VITE_API_BASE_URL=http://localhost:8000/api/v1`

---

## What's Next?

### For Full Anomaly Detection
Run data collection scripts to populate baseline corpus:

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"

# Collect 100+ T&C documents
python scripts/collect_baseline_corpus.py

# Index to Pinecone
python scripts/index_baseline_corpus.py
```

### For Production Deployment
See `docs/DEPLOYMENT.md` (coming in Week 9-10)

---

## Quick Reference

| Service | URL | Status Check |
|---------|-----|--------------|
| Frontend | http://localhost:5173 | Open in browser |
| Backend API | http://localhost:8000 | Open in browser |
| API Docs | http://localhost:8000/api/v1/docs | Interactive docs |
| PostgreSQL | localhost:5432 | `docker ps` |
| Redis | localhost:6379 | `docker ps` |

---

**That's it! You're now running a complete AI-powered T&C Analysis System.** 🎉

For detailed documentation, see:
- `FRONTEND_IMPLEMENTATION_COMPLETE.md` - Frontend guide
- `PROJECT_STATUS_WEEK_8.md` - Full project status
- `API_REFERENCE.md` - API documentation
- `SETUP_GUIDE.md` - Detailed setup instructions
