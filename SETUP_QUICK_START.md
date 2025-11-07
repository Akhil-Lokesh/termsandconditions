# 🚀 Quick Start Setup Guide

**Get the T&C Analysis System running in 10 minutes!**

---

## ⚡ 1-Minute Setup (For Developers)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd "Project T&C"

# 2. Setup backend environment
cd backend
cp .env.example .env

# 3. Add your API keys to backend/.env
# (See section below for where to get keys)

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start services
docker-compose up -d  # PostgreSQL + Redis

# 6. Run migrations
alembic upgrade head

# 7. Start backend
uvicorn app.main:app --reload

# 8. Setup frontend (new terminal)
cd ../frontend
npm install
npm run dev

# Done! Backend: http://localhost:8000, Frontend: http://localhost:5173
```

---

## 🔑 Getting API Keys (5 minutes)

### OpenAI API Key
1. Go to: https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy key (starts with `sk-proj-`)
4. Paste in `backend/.env`:
   ```
   OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
   ```

### Pinecone API Key
1. Go to: https://app.pinecone.io/
2. Sign up/login
3. Go to "API Keys"
4. Copy key (starts with `pcsk-`)
5. Paste in `backend/.env`:
   ```
   PINECONE_API_KEY=pcsk-YOUR-KEY-HERE
   ```

### JWT Secret Key
```bash
# Generate secure key
openssl rand -hex 32

# Paste in backend/.env
SECRET_KEY=<generated-key-here>
```

---

## 📋 Pre-flight Checklist

Before running the app:
- [ ] `backend/.env` exists (copied from `.env.example`)
- [ ] OpenAI API key added to `.env`
- [ ] Pinecone API key added to `.env`
- [ ] JWT secret key generated and added
- [ ] Docker is running (for PostgreSQL/Redis)
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
```bash
# Make sure you're in backend/ directory
cd backend
pip install -r requirements.txt
```

### "Connection refused: PostgreSQL"
```bash
# Start Docker services
docker-compose up -d

# Check services are running
docker-compose ps
```

### "Invalid API key" error
```bash
# Verify your keys in backend/.env
cat backend/.env | grep API_KEY

# Make sure there are no extra spaces or quotes
```

### Alembic migration errors
```bash
# Reset database (⚠️ deletes all data)
alembic downgrade base
alembic upgrade head
```

---

## 🔒 Security Reminder

**NEVER commit `backend/.env` to Git!**

✅ Verify before committing:
```bash
git status | grep "\.env"
# Should show nothing!
```

❌ If you see `.env` in `git status`:
```bash
git rm --cached backend/.env
git commit -m "Remove .env from tracking"
```

📖 **Read SECURITY.md for complete security guidelines**

---

## 🎯 Next Steps

1. **Test the system**:
   - Upload a sample T&C PDF
   - Ask questions about clauses
   - Check anomaly detection results

2. **Collect baseline corpus**:
   ```bash
   python scripts/collect_baseline_corpus.py
   python scripts/index_baseline_corpus.py
   ```

3. **Run tests**:
   ```bash
   cd backend
   pytest
   ```

4. **Deploy to production**:
   - Read `docs/DEPLOYMENT.md`
   - Set up environment variables on hosting platform
   - Configure CI/CD pipeline

---

## 📚 Documentation

- **Quick Start**: You are here!
- **Security Guide**: [SECURITY.md](SECURITY.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API Reference**: [docs/API.md](docs/API.md)
- **Deployment**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 🆘 Need Help?

1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Read [SECURITY.md](SECURITY.md) for API key issues
3. Review Git commit history for examples
4. Contact team lead

---

**Last Updated**: November 4, 2025
**Estimated Setup Time**: 10 minutes
**Difficulty**: Easy ⭐⭐☆☆☆
