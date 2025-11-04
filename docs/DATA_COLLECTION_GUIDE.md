# Baseline Corpus Collection Guide

## 📚 Overview

The baseline corpus consists of **100+ standard Terms & Conditions** documents used for anomaly detection. This guide explains how to collect, validate, and index the corpus.

---

## 🎯 Collection Goals

| Metric | Target | Purpose |
|--------|--------|---------|
| **Total Documents** | 100+ | Statistical significance |
| **Categories** | 5 | Industry diversity |
| **Docs per Category** | 20+ | Balanced representation |
| **Minimum Pages** | 2 | Sufficient content |
| **Minimum Length** | 500 chars | Extractable text |

---

## 📁 Corpus Structure

```
data/baseline_corpus/
├── tech/                    # Technology companies (25+ docs)
│   ├── google_tos.pdf
│   ├── facebook_tos.pdf
│   └── ...
├── ecommerce/               # E-commerce platforms (25+ docs)
│   ├── amazon_tos.pdf
│   ├── ebay_tos.pdf
│   └── ...
├── saas/                    # SaaS companies (20+ docs)
│   ├── slack_tos.pdf
│   ├── notion_tos.pdf
│   └── ...
├── finance/                 # Financial services (15+ docs)
│   ├── paypal_tos.pdf
│   ├── stripe_tos.pdf
│   └── ...
├── general/                 # General services (25+ docs)
│   ├── uber_tos.pdf
│   ├── airbnb_tos.pdf
│   └── ...
├── metadata.json            # Document metadata
└── indexing_results.json    # Indexing statistics
```

---

## 🚀 Quick Start

### Option 1: Automated Collection (Recommended)

```bash
# 1. Install dependencies
cd backend
pip install playwright httpx beautifulsoup4
playwright install chromium

# 2. Run collection script
python scripts/collect_baseline_corpus.py --output data/baseline_corpus

# 3. Validate collected documents
python scripts/validate_corpus.py

# 4. Index to Pinecone
python scripts/index_baseline_corpus.py

# 5. Analyze statistics
python scripts/analyze_corpus_stats.py --check-index --visualize
```

### Option 2: Manual Collection

See [Manual Collection Process](#manual-collection-process) below.

---

## 🤖 Automated Collection

### Prerequisites

```bash
# Install required packages
pip install playwright httpx beautifulsoup4

# Install Chromium browser
playwright install chromium
```

### Collection Script Features

- ✅ **95+ pre-configured sources** across 5 categories
- ✅ **Automatic web-to-PDF conversion** using Playwright
- ✅ **Direct PDF download** support
- ✅ **Resume capability** (skips existing files)
- ✅ **Rate limiting** (respectful to servers)
- ✅ **Progress tracking** and metadata generation
- ✅ **Error recovery** with detailed logging

### Usage Examples

```bash
# Collect all categories
python scripts/collect_baseline_corpus.py

# Collect specific categories
python scripts/collect_baseline_corpus.py --category tech saas

# Force re-download existing files
python scripts/collect_baseline_corpus.py --force

# Faster collection (use with caution)
python scripts/collect_baseline_corpus.py --delay 0.5
```

### Expected Output

```
📚 Starting collection of 95 documents across 5 categories
============================================================
📁 Category: TECH (25 sources)
============================================================

[1/25] Processing: Google
   Converting to PDF: https://policies.google.com/terms
   ✓ Converted: google_tos.pdf (156KB)

[2/25] Processing: Facebook
   Converting to PDF: https://www.facebook.com/legal/terms
   ✓ Converted: facebook_tos.pdf (89KB)

...

📊 COLLECTION SUMMARY
============================================================
✓ Successful:     87
⊙ Already Exists: 5
✗ Failed:         3
📁 Total:         95

💾 Metadata saved to: data/baseline_corpus/metadata.json
```

### Troubleshooting Collection

| Issue | Cause | Solution |
|-------|-------|----------|
| Playwright not found | Not installed | `playwright install chromium` |
| Timeout errors | Slow server | Increase timeout: edit script, change `timeout=30000` |
| Rate limiting (429) | Too fast | Increase delay: `--delay 3.0` |
| Empty PDFs | Page not loaded | Some sites require JavaScript - may need manual collection |
| SSL errors | Certificate issues | Update certificates or use manual collection |

---

## 📝 Manual Collection Process

For sites that don't work with automated collection:

### Step-by-Step

1. **Visit company website**
   - Navigate to footer or legal section
   - Find "Terms of Service" or "Terms & Conditions"

2. **Save as PDF**
   - **Chrome**: Print → Save as PDF
   - **Firefox**: Print → Save to PDF
   - **Safari**: File → Export as PDF

3. **Name consistently**
   ```
   {company_name}_tos.pdf
   ```
   Examples:
   - `google_tos.pdf`
   - `amazon_tos.pdf`
   - `slack_tos.pdf`

4. **Place in category folder**
   ```
   data/baseline_corpus/tech/google_tos.pdf
   data/baseline_corpus/ecommerce/amazon_tos.pdf
   data/baseline_corpus/saas/slack_tos.pdf
   ```

5. **Update metadata.json**
   ```json
   {
     "filename": "google_tos.pdf",
     "category": "tech",
     "company": "Google",
     "source_url": "https://policies.google.com/terms",
     "collected_at": "2025-01-15T10:30:00",
     "status": "manual"
   }
   ```

---

## ✅ Validation

### Automatic Validation

```bash
# Validate entire corpus
python scripts/validate_corpus.py

# Validate specific categories
python scripts/validate_corpus.py --category tech saas

# Generate detailed report
python scripts/validate_corpus.py --detailed --output validation_report.json
```

### Validation Checks

The validator performs these checks:

1. ✅ **File Readability** - Can the PDF be opened?
2. ✅ **Text Extraction** - Can text be extracted?
3. ✅ **Minimum Pages** - At least 2 pages
4. ✅ **Minimum Content** - At least 500 characters
5. ✅ **Duplicate Detection** - Content hash comparison
6. ✅ **Language Check** - Appears to be English
7. ✅ **Metadata Completeness** - All required fields present

### Expected Output

```
🔍 CORPUS VALIDATION
============================================================
Found 95 PDF files

[1/95] Validating: google_tos.pdf
   ✓ Valid - 12 pages, 45,234 chars

[2/95] Validating: facebook_tos.pdf
   ✓ Valid - 8 pages, 32,109 chars

...

⚠️  Found 2 sets of duplicate documents:
   • amazon_tos.pdf, amazon_marketplace_tos.pdf

📊 VALIDATION SUMMARY
============================================================
Total Files:    95
✓ Valid:        92
✗ Invalid:      3
⚠️  Warnings:    2
❌ Errors:       3
🔄 Duplicates:  2

📈 STATISTICS:
Total Pages:    852
Total Chars:    3,456,789
Avg Pages/Doc:  8.9
Avg Chars/Doc:  36,387
Page Range:     2 - 45

✅ CORPUS VALIDATION PASSED
   (2 warnings)
```

### Fixing Validation Issues

| Issue | Action |
|-------|--------|
| **Text too short** | Re-save PDF with better quality, or remove if scanned |
| **Extraction failed** | Try different PDF tool or manual text extraction |
| **Duplicates found** | Remove duplicate or keep if from different jurisdiction |
| **Missing metadata** | Add to `metadata.json` manually |

---

## 🗂️ Indexing to Pinecone

### Prerequisites

- Baseline corpus collected and validated
- Pinecone API key configured in `.env`
- OpenAI API key configured in `.env`

### Indexing Process

```bash
# Index all documents to Pinecone baseline namespace
python scripts/index_baseline_corpus.py

# Dry run (test without uploading)
python scripts/index_baseline_corpus.py --dry-run

# Force re-index
python scripts/index_baseline_corpus.py --force

# Index specific categories
python scripts/index_baseline_corpus.py --category tech saas
```

### What Happens During Indexing

For each document:

1. **Extract text** from PDF (PyPDF2/pdfplumber)
2. **Parse structure** into sections and clauses
3. **Create chunks** (500 words, 50 word overlap)
4. **Generate embeddings** (OpenAI text-embedding-3-small)
5. **Upload to Pinecone** baseline namespace with metadata

### Expected Output

```
📚 INDEXING BASELINE CORPUS
============================================================
Total documents: 92
Target namespace: baseline
Dry run: False
============================================================

[1/92] google_tos.pdf
📄 Processing: Google
   1/5 Extracting text...
   2/5 Parsing structure...
       Found 47 clauses
   3/5 Creating chunks...
       Created 23 chunks
   4/5 Generating embeddings...
   5/5 Uploading to Pinecone baseline namespace...
✓ Indexed: Google (23 chunks, 8.3s)
Progress: 1.1% (1/92)

...

📊 INDEXING SUMMARY
============================================================
✓ Successful:     89
⊙ Skipped:        3
✗ Failed:         0
📄 Total Docs:    92
📦 Total Chunks:  2,145
📝 Total Chars:   3,234,567
⏱️  Avg Time/Doc:  7.2s
📊 Avg Chunks/Doc: 24.1

💰 Estimated OpenAI Cost: $0.04

✅ Indexing complete!
```

### Performance & Costs

| Metric | Expected Value |
|--------|----------------|
| **Processing Time** | 2-3 minutes per document |
| **Total Time (100 docs)** | 3-5 hours |
| **OpenAI Embedding Cost** | ~$0.04 per 100 documents |
| **Pinecone Storage** | ~10MB per 1000 vectors |

### Monitoring Indexing Progress

```bash
# Check Pinecone index stats
python scripts/analyze_corpus_stats.py --check-index

# View logs
tail -f backend/corpus_indexing.log
```

---

## 📊 Statistics & Analysis

### Generate Statistics

```bash
# Basic statistics
python scripts/analyze_corpus_stats.py

# Include Pinecone index stats
python scripts/analyze_corpus_stats.py --check-index

# Generate visualizations
python scripts/analyze_corpus_stats.py --visualize

# Save detailed report
python scripts/analyze_corpus_stats.py --output corpus_stats.json
```

### Statistics Included

1. **Document Statistics**
   - Total documents, pages, characters
   - Average and median values
   - Page count distribution

2. **Category Distribution**
   - Documents per category
   - Balance scores
   - Average content per category

3. **Pinecone Index**
   - Total vectors
   - Vectors per namespace
   - Average vectors per document

4. **Quality Metrics**
   - Completeness score (vs 100 doc target)
   - Diversity score (category balance)
   - Length quality score
   - Overall quality score

### Example Output

```
📊 BASELINE CORPUS STATISTICS
======================================================================

📄 DOCUMENT STATISTICS:
   Total Documents:      92
   Total Pages:          852
   Total Characters:     3,456,789
   Average Pages/Doc:    9.3
   Average Chars/Doc:    37,573
   Page Range:           2 - 45
   Median Pages:         8

   Extraction Methods:
      pdfplumber     :  87 (94.6%)
      pypdf2         :   5 (5.4%)

📁 CATEGORY DISTRIBUTION:
   tech           :  25 docs, 10.2 avg pages, balance: 0.98
   ecommerce      :  23 docs,  8.7 avg pages, balance: 0.95
   saas           :  20 docs,  9.1 avg pages, balance: 0.89
   finance        :  15 docs,  8.3 avg pages, balance: 0.78
   general        :   9 docs,  9.8 avg pages, balance: 0.65

🔍 PINECONE INDEX:
   Index Name:           tc-analysis
   Total Vectors:        2,198
   Dimension:            1536
   Namespaces:
      baseline         : 2,145 vectors
      user_tcs         :    53 vectors
   Avg Vectors/Doc:      23.3

✅ QUALITY METRICS:
   Completeness:         92.0%
   Diversity:            85.0%
   Length Quality:       95.0%
   Overall Score:        90.3%

💡 RECOMMENDATIONS:
   • Add 8 more documents to reach target of 100
   • Category 'general' has only 9 documents (target: 20+)
   • Category 'finance' has only 15 documents (target: 20+)

======================================================================
```

---

## 🎯 Quality Guidelines

### Document Requirements

✅ **Must Have:**
- Minimum 2 pages
- Minimum 500 characters
- Clean text extraction
- Recent version (within 2 years)
- English language

⚠️ **Avoid:**
- Scanned PDFs without OCR
- Non-English documents
- Privacy policies (we want T&Cs)
- Cookie policies
- Marketing materials

### Category Balance

Target distribution:
```
tech       : 25 documents (26%)
ecommerce  : 25 documents (26%)
saas       : 20 documents (21%)
finance    : 15 documents (16%)
general    : 25 documents (26%)
━━━━━━━━━━━━━━━━━━━━━━━━━━
Total      : 110 documents
```

### Diversity Within Categories

**Tech**: Mix of social media, cloud services, developer tools
**E-commerce**: Marketplaces, retailers, fashion brands
**SaaS**: Productivity, collaboration, CRM, communication
**Finance**: Payments, banking, crypto, fintech
**General**: Services, entertainment, travel, food delivery

---

## 🔧 Advanced Configuration

### Collection Script Configuration

Edit `scripts/collect_baseline_corpus.py`:

```python
# Add new sources to BASELINE_SOURCES dict
BASELINE_SOURCES = {
    "tech": [
        {"name": "NewCompany", "url": "https://...", "type": "web"},
        # ... more sources
    ],
}

# Adjust timeouts
await page.goto(url, wait_until="networkidle", timeout=60000)  # 60s

# Adjust PDF settings
await page.pdf(
    path=str(output_path),
    format="A4",
    print_background=True,
    margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"}
)
```

### Indexing Script Configuration

Edit `scripts/index_baseline_corpus.py` or `backend/app/core/legal_chunker.py`:

```python
# Adjust chunk size
chunker = LegalChunker(
    max_chunk_size=500,  # Increase for longer chunks
    overlap=50           # Increase for more context
)

# Adjust batch delay
await asyncio.sleep(1.0)  # Seconds between documents
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Playwright Installation Fails

**Error**: `playwright executable not found`

**Solution**:
```bash
pip install playwright --upgrade
playwright install chromium
```

#### 2. Indexing Takes Too Long

**Cause**: Processing 100+ documents with embeddings is slow

**Solutions**:
- Run overnight
- Process categories separately
- Use `--dry-run` first to test

#### 3. Pinecone Quota Exceeded

**Error**: `429 Too Many Requests`

**Solution**:
- Check Pinecone quotas
- Increase batch delay: `--delay 2.0`
- Upgrade Pinecone plan if needed

#### 4. OpenAI Rate Limit

**Error**: `Rate limit exceeded`

**Solution**:
- Batch operations are already used
- Wait and retry
- Check API tier limits

#### 5. Duplicate Documents

**Issue**: Validator reports duplicates

**Solution**:
- Review both documents
- Keep if different versions/jurisdictions
- Remove if truly duplicate

---

## 📚 Data Sources

### Pre-configured Sources (95 companies)

The collection script includes URLs for:

- **25 Tech companies**: Google, Facebook, Microsoft, Apple, etc.
- **25 E-commerce**: Amazon, eBay, Etsy, Walmart, etc.
- **20 SaaS**: Slack, Notion, Asana, Salesforce, etc.
- **15 Finance**: PayPal, Stripe, Coinbase, Robinhood, etc.
- **25 General**: Uber, Airbnb, Netflix, Spotify, etc.

### Adding New Sources

Edit `scripts/collect_baseline_corpus.py`:

```python
BASELINE_SOURCES = {
    "your_category": [
        {
            "name": "CompanyName",
            "url": "https://company.com/terms",
            "type": "web"  # or "pdf" for direct PDF links
        },
    ]
}
```

---

## 🚀 Next Steps

After completing corpus collection:

1. ✅ **Validate corpus** (should have 90%+ valid files)
2. ✅ **Index to Pinecone** baseline namespace
3. ✅ **Analyze statistics** (check quality score)
4. ✅ **Test anomaly detection** with user documents
5. ➡️ **Week 8-10**: Build frontend interface

---

## 📞 Support

### Issues & Questions

- Check troubleshooting section
- Review log files:
  - `corpus_collection.log`
  - `corpus_validation.log`
  - `corpus_indexing.log`
  - `corpus_analysis.log`

### Manual Review Needed

Some high-quality sources may require manual collection:
- Complex JavaScript-heavy sites
- Sites with captcha/login requirements
- Government/legal institution T&Cs
- Industry-specific terms (healthcare, finance, etc.)

---

## 📈 Success Criteria

Your corpus is ready when:

- ✅ **90+ documents** collected
- ✅ **5 categories** represented
- ✅ **Validation passes** (90%+ valid)
- ✅ **Indexed to Pinecone** baseline namespace
- ✅ **Quality score > 85%**
- ✅ **No critical errors** in validation
- ✅ **Category balance** reasonable (15+ docs each)

---

## 🎉 Completion Checklist

- [ ] Scripts installed and working
- [ ] Automated collection run successfully
- [ ] Manual collection completed for failed sources
- [ ] Validation passed with 90%+ valid
- [ ] All documents indexed to Pinecone
- [ ] Statistics analyzed and quality score good
- [ ] Metadata complete
- [ ] Ready for anomaly detection testing!

---

**Next**: [Testing Anomaly Detection](TESTING_ANOMALY_DETECTION.md)
