# 🚀 Complete Setup Guide - T&C Analysis System

**Last Updated**: November 1, 2024
**Status**: Ready for Setup

---

## 📋 Prerequisites Check

Before starting, make sure you have:

- [ ] **OpenAI API Key** (from https://platform.openai.com/api-keys)
- [ ] **Pinecone API Key** (from https://app.pinecone.io/)
- [ ] **Docker Desktop** installed and running
- [ ] **Python 3.9+** installed
- [ ] **Node.js 18+** installed (already have this ✅)

---

## 🎯 Quick Start (3 Steps)

### Step 1: Add Your API Keys (2 minutes)

**Open this file in your editor:**
```
/Users/akhil/Desktop/Project T&C/backend/.env
```

**Edit lines 7 and 16:**

```env
# Line 7 - Add your OpenAI API key
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Line 16 - Add your Pinecone API key
PINECONE_API_KEY=your-actual-pinecone-key-here
```

**Save the file** and continue to Step 2.

---

### Step 2: Run Automated Setup (10 minutes)

**Open Terminal and run:**

```bash
cd "/Users/akhil/Desktop/Project T&C"
./setup_backend.sh
```

**This script will automatically:**
1. ✅ Verify your API keys are set
2. ✅ Create Python virtual environment
3. ✅ Install all Python dependencies (~350 packages)
4. ✅ Start Docker services (PostgreSQL + Redis)
5. ✅ Run database migrations
6. ✅ Verify backend can import successfully

**If the script shows any errors**, see the [Troubleshooting](#-troubleshooting) section below.

---

### Step 3: Start Backend Server (30 seconds)

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"
source venv/bin/activate
uvicorn app.main:app --reload
```

**You should see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

---

## ✅ Verify Everything is Working

### Check All Services

**Terminal 1 - Backend:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

**Terminal 2 - Frontend** (already running):
```
Frontend running on: http://localhost:5173
```

**Terminal 3 - Database:**
```bash
docker ps
# Should show PostgreSQL and Redis containers running
```

### Open the Application

```bash
open http://localhost:5173
```

You should see the beautiful landing page!

---

## 🧪 Test the Complete Flow

### 1. Sign Up
- Click "Get Started"
- Email: `test@example.com`
- Password: `testpass123`
- Click "Sign up"
- Should redirect to Dashboard ✅

### 2. Upload a Test Document
- Click "Upload Document"
- Upload any PDF with text
- Wait ~30 seconds for processing
- Should see analysis results ✅

### 3. View Anomalies
- Click "Anomalies" tab
- Should see detected issues (if any) ✅

### 4. Ask Questions
- Click "Q&A" tab
- Type a question: "What is the refund policy?"
- Should get an answer with citations ✅

---

## 📁 What Was Created

```
Project T&C/
├── backend/
│   ├── .env                    ✅ Created (with YOUR API keys)
│   ├── venv/                   ✅ Created (Python environment)
│   ├── app/                    ✅ All code ready
│   └── requirements.txt        ✅ All dependencies
│
├── frontend/
│   ├── node_modules/           ✅ Installed (388 packages)
│   ├── src/                    ✅ All components ready
│   ├── dist/                   ✅ Production build ready
│   └── Running on :5173        ✅ Dev server active
│
├── data/
│   └── test_samples/           ✅ Ready for PDFs
│
└── Docker Services:
    ├── PostgreSQL              ✅ Running on :5432
    └── Redis                   ✅ Running on :6379
```

---

## 🔧 Optional: Create Test PDF

If you need a sample PDF to test with:

```bash
cd "/Users/akhil/Desktop/Project T&C/backend"
source venv/bin/activate
python scripts/create_test_pdf.py
```

This creates: `data/test_samples/sample_terms.pdf`

---

## 🔍 Service URLs

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | http://localhost:5173 | ✅ Running |
| **Backend API** | http://localhost:8000 | ⏳ After Step 3 |
| **API Docs** | http://localhost:8000/api/v1/docs | ⏳ After Step 3 |
| **PostgreSQL** | localhost:5432 | ⏳ After Step 2 |
| **Redis** | localhost:6379 | ⏳ After Step 2 |

---

## 🆘 Troubleshooting

### Issue: "OpenAI API key not set" error

**Solution:**
```bash
# Open .env file
open "/Users/akhil/Desktop/Project T&C/backend/.env"

# Make sure line 7 has your actual key (starts with sk-)
OPENAI_API_KEY=sk-proj-xxxxx...

# Save and run setup again
```

---

### Issue: "Docker daemon not running"

**Solution:**
1. Open Docker Desktop application
2. Wait for it to say "Docker Desktop is running"
3. Run setup script again

---

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --reload --port 8001
```

---

### Issue: "Module not found" errors

**Solution:**
```bash
cd "/Users/akhil/Desktop/Project T&C/backend"
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

---

### Issue: Frontend can't reach backend

**Solution:**
1. Check backend is running: `curl http://localhost:8000/health`
2. Check CORS settings in `backend/.env`
3. Restart both frontend and backend

---

### Issue: Pinecone connection fails

**Solution:**
1. Check your Pinecone dashboard: https://app.pinecone.io/
2. Verify you have an index named `tc-analysis`
3. If not, create one:
   - Name: `tc-analysis`
   - Dimensions: `1536`
   - Metric: `cosine`
   - Region: Match your .env PINECONE_ENVIRONMENT

---

## 🎯 What Each Terminal Should Show

### Terminal 1 (Backend):
```
INFO:     Will watch for changes in these directories: ['/Users/akhil/Desktop/Project T&C/backend']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
✓ OpenAI service initialized
✓ Pinecone service initialized
✓ Database connected
✓ Redis cache connected
INFO:     Application startup complete.
```

### Terminal 2 (Frontend - Already Running):
```
VITE v5.4.21  ready in 141 ms
➜  Local:   http://localhost:5173/
```

### Terminal 3 (Docker):
```bash
$ docker ps
CONTAINER ID   IMAGE         STATUS         PORTS                    NAMES
abc123...      postgres:15   Up 2 minutes   0.0.0.0:5432->5432/tcp   backend-db-1
def456...      redis:7       Up 2 minutes   0.0.0.0:6379->6379/tcp   backend-redis-1
```

---

## 📊 Success Checklist

After completing all steps, verify:

- [ ] ✅ Backend .env file has your API keys
- [ ] ✅ Python venv created and activated
- [ ] ✅ All dependencies installed
- [ ] ✅ Docker containers running
- [ ] ✅ Database migrations complete
- [ ] ✅ Backend server running on :8000
- [ ] ✅ Frontend running on :5173
- [ ] ✅ Can sign up for account
- [ ] ✅ Can upload PDF document
- [ ] ✅ Can view analysis results
- [ ] ✅ Can ask questions

---

## 🎉 You're All Set!

**Your complete T&C Analysis System is now running!**

**Next Steps:**
1. Upload a Terms & Conditions PDF
2. View the AI-powered analysis
3. Check detected anomalies
4. Ask questions about the document

**Need Help?**
- Check [SYSTEM_VERIFICATION_REPORT.md](SYSTEM_VERIFICATION_REPORT.md) for detailed status
- See [API_KEYS_LOCATION.md](API_KEYS_LOCATION.md) for API key help
- Review [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues

---

## 🔄 To Stop/Restart Services

### Stop Everything:
```bash
# Stop backend (Ctrl+C in backend terminal)
# Stop frontend (Ctrl+C in frontend terminal)
# Stop Docker
docker-compose down
```

### Restart Everything:
```bash
# Terminal 1: Start Docker
cd "/Users/akhil/Desktop/Project T&C/backend"
docker-compose up -d

# Terminal 2: Start Backend
cd "/Users/akhil/Desktop/Project T&C/backend"
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 3: Start Frontend (if stopped)
cd "/Users/akhil/Desktop/Project T&C/frontend"
npm run dev
```

---

**🚀 Ready to analyze Terms & Conditions with AI!**
