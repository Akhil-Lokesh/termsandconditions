# ⚡ START HERE - Quick Launch Guide

**Everything is ready! Just follow these 3 steps:**

---

## 🔴 STEP 1: Add Your API Keys (2 minutes)

### Open this file in any text editor:
```
/Users/akhil/Desktop/Project T&C/backend/.env
```

### Find these two lines and replace with your actual keys:

**Line 7:**
```env
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
```
Change to:
```env
OPENAI_API_KEY=sk-proj-your-actual-key
```

**Line 16:**
```env
PINECONE_API_KEY=YOUR_PINECONE_API_KEY_HERE
```
Change to:
```env
PINECONE_API_KEY=your-actual-pinecone-key
```

**💾 SAVE THE FILE**

---

## 🔴 STEP 2: Run Setup Script (10 minutes)

### Open Terminal and paste these commands:

```bash
cd "/Users/akhil/Desktop/Project T&C"
./setup_backend.sh
```

**This will automatically:**
- ✅ Check your API keys
- ✅ Install Python packages
- ✅ Start database
- ✅ Set up everything

**Wait for it to say "✅ BACKEND SETUP COMPLETE!"**

---

## 🔴 STEP 3: Start Backend (30 seconds)

### In the same Terminal, run:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Wait for:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## ✅ DONE! Open the App

### In your browser, go to:
```
http://localhost:5173
```

You should see the T&C Analysis homepage!

---

## 🧪 Test It

1. Click **"Get Started"**
2. Sign up with any email/password
3. Click **"Upload Document"**
4. Upload a PDF
5. Watch the AI analyze it! ✨

---

## 📍 File Locations Summary

| What | Where |
|------|-------|
| **Add API Keys** | `/Users/akhil/Desktop/Project T&C/backend/.env` |
| **Run Setup** | `/Users/akhil/Desktop/Project T&C/setup_backend.sh` |
| **Frontend** | Already running on http://localhost:5173 |
| **Backend** | Will run on http://localhost:8000 |

---

## 🆘 Problems?

### "API key not set" error?
- Open `backend/.env` file
- Make sure you pasted your ACTUAL keys (not the placeholder text)
- Keys should start with `sk-` for OpenAI

### "Docker not running" error?
- Open Docker Desktop app
- Wait for it to start
- Run setup script again

### Need more help?
- Open `COMPLETE_SETUP_GUIDE.md` for detailed instructions
- Open `API_KEYS_LOCATION.md` for help finding your keys

---

## 🎯 Current Status

✅ **Frontend**: Running on http://localhost:5173
⏳ **Backend**: Waiting for you to add API keys and run setup
⏳ **Database**: Will start automatically with setup script

**Total time to launch: ~15 minutes**

---

**Ready? Go to Step 1 above!** 🚀
