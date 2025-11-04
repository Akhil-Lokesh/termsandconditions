# 🔑 API Keys Configuration Guide

## 📍 WHERE TO ADD YOUR API KEYS

### File Location:
```
/Users/akhil/Desktop/Project T&C/backend/.env
```

---

## 🔴 STEP 1: Add OpenAI API Key (Line 7)

**Current:**
```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
```

**Replace with your actual key:**
```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Where to get it:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-proj-` or `sk-`)
4. Paste it in line 7 of the .env file

**Important:** Your key should start with `sk-`

---

## 🔴 STEP 2: Add Pinecone API Key (Line 16)

**Current:**
```
PINECONE_API_KEY=YOUR_PINECONE_API_KEY_HERE
```

**Replace with your actual key:**
```
PINECONE_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

**Where to get it:**
1. Go to https://app.pinecone.io/
2. Click on "API Keys" in the left sidebar
3. Copy your API key
4. Paste it in line 16 of the .env file

**Also check line 17 (PINECONE_ENVIRONMENT):**
- Make sure it matches your Pinecone environment
- Common values: `us-east-1`, `us-west-2`, `eu-west-1`
- Check your Pinecone dashboard for the correct value

---

## ✅ STEP 3: Verify Configuration

After adding both keys, your .env file should look like:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-abc123...  # Your actual key
...

# Pinecone Configuration
PINECONE_API_KEY=12345678-abcd-...  # Your actual key
PINECONE_ENVIRONMENT=us-east-1  # Match your Pinecone region
```

---

## 🚀 STEP 4: What Happens After Adding Keys

Once you add the keys and save the file, you can:

1. **Create Pinecone Index** (if not exists):
   ```bash
   # Login to https://app.pinecone.io/
   # Create a new index with:
   # - Name: tc-analysis
   # - Dimensions: 1536
   # - Metric: cosine
   # - Region: same as PINECONE_ENVIRONMENT
   ```

2. **Continue with Setup**:
   - Python virtual environment
   - Install dependencies
   - Start Docker services
   - Run database migrations
   - Start backend server

---

## 📋 Quick Checklist

- [ ] Added OpenAI API key to line 7
- [ ] Added Pinecone API key to line 16
- [ ] Verified Pinecone environment matches your account
- [ ] Saved the .env file
- [ ] Created Pinecone index (if not exists)

---

## 🔐 Security Notes

**IMPORTANT:**
- ✅ The .env file is in .gitignore (won't be committed)
- ❌ NEVER share your .env file
- ❌ NEVER commit API keys to git
- ✅ Keep your keys secure

---

## 🆘 If Keys Don't Work

### OpenAI API Key Issues:
1. **Invalid Key Format**
   - Must start with `sk-`
   - Check for extra spaces or quotes

2. **No Credits**
   - Check billing at https://platform.openai.com/account/billing
   - Add payment method if needed

3. **Rate Limits**
   - New accounts have lower limits
   - Check usage at https://platform.openai.com/usage

### Pinecone API Key Issues:
1. **Invalid Key**
   - Copy key again from dashboard
   - Remove any spaces/quotes

2. **Wrong Environment**
   - Check your Pinecone project settings
   - Update PINECONE_ENVIRONMENT to match

3. **Index Not Found**
   - Create index manually at https://app.pinecone.io/
   - Name must be: `tc-analysis`
   - Dimensions: 1536
   - Metric: cosine

---

## ✨ Ready for Next Steps

After adding your API keys, continue with:

```bash
# See COMPLETE_SETUP_GUIDE.md for full instructions
cd "/Users/akhil/Desktop/Project T&C"
open COMPLETE_SETUP_GUIDE.md
```

Or follow the automated setup script (coming next).

---

**Current Status:**
- ✅ .env file created at: `/Users/akhil/Desktop/Project T&C/backend/.env`
- ✅ SECRET_KEY generated automatically
- ⏳ Waiting for you to add OpenAI and Pinecone API keys
- ⏳ Then we can start the backend

**Edit the file now, then tell me when you're ready to continue!**
