# Data Directory

This directory contains data files for the T&C Analysis System.

## Structure

```
data/
├── baseline_corpus/      # 100+ standard T&C documents
│   ├── streaming/       # Streaming service T&Cs
│   ├── saas/           # SaaS company T&Cs
│   ├── ecommerce/      # E-commerce T&Cs
│   └── social_media/   # Social media T&Cs
│
└── test_samples/        # Test T&C documents for development
```

## Baseline Corpus

The baseline corpus is a collection of 100+ standard Terms & Conditions documents used for anomaly detection. By comparing user-uploaded T&Cs against this baseline, the system identifies unusual or risky clauses.

### Required Size

**Minimum**: 100 T&C documents
**Recommended**: 150-200 documents

### Organization by Industry

#### streaming/ (Target: 30 documents)
Examples:
- Spotify Terms of Service
- Netflix Terms of Use
- Hulu Subscriber Agreement
- Apple Music Terms
- YouTube Premium Terms
- Disney+ Subscriber Agreement
- Amazon Prime Video Terms
- Tidal Terms
- Pandora Terms
- Deezer Terms

#### saas/ (Target: 30 documents)
Examples:
- Notion Terms of Service
- Slack Terms of Service
- Zoom Terms of Service
- Asana Terms
- Trello Terms
- Monday.com Terms
- Dropbox Terms
- Google Workspace Terms
- Microsoft 365 Terms
- Figma Terms

#### ecommerce/ (Target: 20 documents)
Examples:
- Amazon Terms of Use
- eBay User Agreement
- Etsy Terms of Use
- Shopify Terms
- Walmart Terms
- Target Terms
- Best Buy Terms
- Wayfair Terms
- Alibaba Terms
- AliExpress Terms

#### social_media/ (Target: 20 documents)
Examples:
- Facebook Terms of Service
- Instagram Terms
- Twitter/X Terms
- TikTok Terms
- LinkedIn User Agreement
- Reddit User Agreement
- Snapchat Terms
- Discord Terms
- Pinterest Terms
- Tumblr Terms

## Collecting Baseline Documents

### Manual Collection (Recommended)

1. **Visit company websites**:
   - Look for "Terms of Service", "Terms & Conditions", or "User Agreement" links
   - Usually in footer or legal pages

2. **Save as PDF**:
   - Chrome: Print → Save as PDF
   - Safari: File → Export as PDF
   - Firefox: Print → Save to PDF

3. **Naming convention**:
   ```
   {company_name}_tos_{date}.pdf
   
   Examples:
   spotify_tos_2024.pdf
   netflix_tos_2024.pdf
   notion_tos_2024.pdf
   ```

4. **Organize by industry**:
   - Place in appropriate subdirectory
   - Keep files under 10MB if possible

### Web Scraping (Advanced)

```python
# Example script (scripts/scrape_tos.py)
import requests
from bs4 import BeautifulSoup

def download_tos(url, company_name, category):
    response = requests.get(url)
    # Parse and save as PDF
    # Save to data/baseline_corpus/{category}/{company_name}_tos.pdf
```

### Sources

**Aggregate Sources**:
- ToS;DR (Terms of Service; Didn't Read)
- Common Crawl (may contain T&Cs)
- Internet Archive Wayback Machine

**Direct from Companies**:
- Visit company websites directly
- Most reliable and up-to-date

## Processing Baseline Corpus

Once collected, process the baseline corpus:

```bash
# From project root
cd scripts
python build_baseline_corpus.py

# This will:
# 1. Process all PDFs in data/baseline_corpus/
# 2. Extract structure and metadata
# 3. Generate embeddings
# 4. Upload to Pinecone (baseline namespace)
```

**Time estimate**: ~2-5 minutes per document (depending on length)

**Total processing time**: ~3-8 hours for 100 documents

## Test Samples

The `test_samples/` directory contains a few T&C documents for development and testing.

### Recommended Test Samples

Start with these well-known T&Cs:

1. **Spotify** - Clear structure, standard streaming service terms
2. **Netflix** - User-friendly, good baseline
3. **Zoom** - SaaS example with privacy focus
4. **Amazon** - E-commerce, complex terms
5. **Discord** - Social/communication platform

### Adding Test Samples

```bash
# Download test PDFs
# Save to data/test_samples/

# Example files:
data/test_samples/
├── spotify_tos_test.pdf
├── netflix_tos_test.pdf
├── zoom_tos_test.pdf
└── example_risky_tos.pdf  # One with known risky clauses
```

## Data Privacy & Legal

### Important Notes

1. **Public Documents**: T&Cs are public documents, freely accessible
2. **No User Data**: This directory only contains company T&Cs, not user data
3. **Fair Use**: Using for analysis and comparison is generally fair use
4. **Don't Redistribute**: Don't publicly share large collections of T&Cs
5. **Attribution**: Keep source information (company name, date)

### Copyright Considerations

- T&Cs are copyrighted by companies
- Using for analysis is typically fair use
- Don't quote large sections verbatim
- Paraphrase findings in plain language

## Baseline Quality Standards

### What to Include

✅ Official Terms of Service documents
✅ User Agreements
✅ Subscriber Agreements
✅ Terms of Use
✅ Service Terms

### What to Exclude

❌ Privacy Policies (separate document type)
❌ Cookie Policies
❌ Community Guidelines alone
❌ FAQ pages
❌ Help articles
❌ Marketing materials

### Quality Checklist

- [ ] Document is a complete T&C (not partial)
- [ ] PDF is readable (not scanned image without OCR)
- [ ] Document is current (2023-2024)
- [ ] Company name is identifiable
- [ ] Document has clear sections/clauses
- [ ] File size is reasonable (<10MB)

## Maintenance

### Updating Baseline Corpus

**Frequency**: Every 6-12 months

**Process**:
1. Check for updated T&Cs from major companies
2. Replace outdated versions
3. Re-process updated documents
4. Verify anomaly detection still works correctly

### Version Control

Consider tracking:
- Date of collection
- Source URL
- Version/effective date of T&C
- Last processed date

Example metadata file:
```json
{
  "filename": "spotify_tos_2024.pdf",
  "company": "Spotify",
  "collected_date": "2024-01-15",
  "source_url": "https://spotify.com/legal/end-user-agreement",
  "effective_date": "2024-01-01",
  "processed_date": "2024-01-20"
}
```

## Storage Considerations

### File Sizes

- Average T&C PDF: 500KB - 2MB
- 100 documents: ~50-200MB total
- Processed (text only): ~10-30MB

### Backup

Recommended:
- Keep original PDFs backed up
- Version control metadata
- Export Pinecone data periodically

## Next Steps

1. **Week 6**: Collect 100+ T&C PDFs
   - Start with test samples
   - Focus on one industry at a time
   - 20-30 documents per day is reasonable

2. **Week 6**: Process baseline corpus
   - Run processing script
   - Verify all uploaded successfully
   - Check Pinecone dashboard

3. **Week 7**: Test anomaly detection
   - Upload test T&C with known risky clauses
   - Verify detection works
   - Tune thresholds if needed

## Resources

- ToS;DR: https://tosdr.org/
- Common Crawl: https://commoncrawl.org/
- Terms Feed: https://www.termsfeed.com/
