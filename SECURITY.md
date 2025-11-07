# Security Guidelines 🔒

**Project**: AI-Powered Terms & Conditions Analysis System
**Last Updated**: November 4, 2025

---

## 🚨 Critical Security Rules

### 1. Never Commit API Keys ❌

**NEVER commit these files**:
- `backend/.env` - Contains real API keys
- `frontend/.env.local` - Contains frontend secrets
- Any file with real credentials

**These are already in .gitignore**:
```
.env
.env.local
backend/.env
frontend/.env.local
**/.env
```

### 2. Use .env.example as Template ✅

**Always use placeholders** in `.env.example`:
```bash
# ❌ WRONG - Real API key
OPENAI_API_KEY=sk-proj-abc123xyz789realkey

# ✅ CORRECT - Placeholder
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
```

---

## 🔑 API Keys Setup

### Step 1: Copy Template
```bash
cp backend/.env.example backend/.env
```

### Step 2: Get API Keys

#### OpenAI API Key
1. Visit: https://platform.openai.com/api-keys
2. Create new secret key
3. Copy key (starts with `sk-proj-`)
4. Paste in `backend/.env`:
   ```
   OPENAI_API_KEY=sk-proj-YOUR-REAL-KEY-HERE
   ```

#### Pinecone API Key
1. Visit: https://app.pinecone.io/
2. Go to API Keys section
3. Create new API key
4. Copy key (starts with `pcsk-`)
5. Paste in `backend/.env`:
   ```
   PINECONE_API_KEY=pcsk-YOUR-REAL-KEY-HERE
   ```

#### JWT Secret Key
Generate a secure random key:
```bash
openssl rand -hex 32
```
Paste in `backend/.env`:
```
SECRET_KEY=your-generated-hex-key-here
```

### Step 3: Verify .env is Ignored
```bash
# Check .env is NOT tracked
git status

# Should NOT show backend/.env
# If it does, run:
git rm --cached backend/.env
```

---

## 🛡️ Security Checklist

### Before Every Commit:
- [ ] Check `git status` - no .env files listed
- [ ] Verify API keys are not in code
- [ ] Check .env.example has placeholders only
- [ ] No hardcoded secrets in Python files

### If You Accidentally Commit API Keys:

#### Option 1: If Not Pushed Yet (EASY)
```bash
# Remove from last commit
git reset HEAD~1

# Remove .env from staging
git rm --cached backend/.env

# Update .gitignore if needed
git add .gitignore

# Commit again (without .env)
git commit -m "your message"
```

#### Option 2: If Already Pushed (NUCLEAR)
```bash
# ⚠️ WARNING: This rewrites Git history!
# ⚠️ Coordinate with team before running!

# Remove .env from all history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (rewrites remote history)
git push origin --force --all

# ⚠️ IMPORTANT: Rotate ALL exposed API keys immediately!
```

#### Option 3: Safest (RECOMMENDED)
1. **Rotate ALL exposed API keys immediately**
   - OpenAI: Delete old key, create new one
   - Pinecone: Regenerate API key
   - JWT: Generate new secret

2. **Revert the commit**:
   ```bash
   git revert <commit-hash>
   ```

3. **Update .gitignore** and commit properly

---

## 🔐 Environment Variables Reference

### Required Variables:

| Variable | Type | Example | Where to Get |
|----------|------|---------|--------------|
| `OPENAI_API_KEY` | Secret | `sk-proj-...` | https://platform.openai.com/api-keys |
| `PINECONE_API_KEY` | Secret | `pcsk-...` | https://app.pinecone.io/ |
| `SECRET_KEY` | Secret | `hex-string` | `openssl rand -hex 32` |
| `DATABASE_URL` | Config | `postgresql://...` | Local/Cloud database |
| `REDIS_URL` | Config | `redis://localhost:6379` | Local/Cloud Redis |

### Optional Variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode |
| `ENVIRONMENT` | `production` | Environment name |
| `OPENAI_MODEL_GPT4` | `gpt-4` | GPT-4 model name |
| `CACHE_TTL` | `3600` | Cache TTL (seconds) |

---

## 📋 Security Best Practices

### 1. Principle of Least Privilege
- Only share API keys with team members who need them
- Use separate keys for development/production
- Rotate keys regularly (every 90 days)

### 2. Key Storage
- **Development**: Use `.env` file (gitignored)
- **Production**: Use environment variables or secret manager:
  - Railway: Environment Variables
  - Render: Environment Variables
  - AWS: AWS Secrets Manager
  - Azure: Azure Key Vault
  - GCP: Secret Manager

### 3. Key Rotation Schedule
- OpenAI API Key: Rotate every 90 days
- Pinecone API Key: Rotate every 90 days
- JWT Secret: Rotate every 180 days
- Database Password: Rotate every 90 days

### 4. Monitoring
- Enable OpenAI usage alerts
- Monitor Pinecone API usage
- Set up billing alerts
- Review access logs monthly

---

## 🚀 Production Deployment

### Environment Variables Setup:

#### Railway:
```bash
railway variables set OPENAI_API_KEY=sk-proj-...
railway variables set PINECONE_API_KEY=pcsk-...
railway variables set SECRET_KEY=$(openssl rand -hex 32)
```

#### Render:
1. Go to Dashboard → Environment
2. Add each variable:
   - `OPENAI_API_KEY` = `sk-proj-...`
   - `PINECONE_API_KEY` = `pcsk-...`
   - `SECRET_KEY` = (generated value)

#### Docker:
```bash
# Use .env file
docker-compose --env-file backend/.env up

# Or pass as arguments
docker run -e OPENAI_API_KEY=sk-proj-... app
```

---

## 🆘 Emergency Procedures

### If API Keys Are Exposed:

1. **Immediate Action** (within 5 minutes):
   - Delete exposed OpenAI key: https://platform.openai.com/api-keys
   - Regenerate Pinecone key: https://app.pinecone.io/

2. **Update Application** (within 15 minutes):
   - Generate new keys
   - Update `backend/.env`
   - Restart backend server
   - Test API connectivity

3. **Clean Git History** (within 1 hour):
   - Follow "Option 3: Safest" above
   - Verify keys are removed from history
   - Notify team members

4. **Post-Incident** (within 24 hours):
   - Review how exposure occurred
   - Update .gitignore if needed
   - Document lessons learned
   - Implement additional safeguards

---

## 📞 Support & Questions

### Where to Get Help:
- **OpenAI Issues**: https://help.openai.com/
- **Pinecone Issues**: https://support.pinecone.io/
- **Git Security**: https://docs.github.com/en/code-security

### Internal Contacts:
- Security Lead: [Add contact]
- DevOps Team: [Add contact]
- Project Manager: [Add contact]

---

## ✅ Quick Security Check

Run this before every commit:
```bash
# 1. Check no .env files are staged
git status | grep -i "\.env"

# 2. Check no API keys in code
grep -r "sk-proj-" backend/app/ || echo "✅ No OpenAI keys"
grep -r "pcsk-" backend/app/ || echo "✅ No Pinecone keys"

# 3. Verify .gitignore is working
git check-ignore backend/.env && echo "✅ .env is ignored"
```

---

**Remember**: Security is everyone's responsibility! 🔒

When in doubt, ask before committing!
