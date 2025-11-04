# Test Samples Directory

This directory contains sample T&C PDF documents for testing the document processing pipeline.

## Required Files

For testing, you need at least one sample T&C PDF. You can:

1. **Download real T&C PDFs** from companies:
   - Visit a company website (e.g., Google, Spotify, Netflix)
   - Navigate to their "Terms of Service" page
   - Save as PDF (Print → Save as PDF)
   - Save to this directory as `sample_tc.pdf`

2. **Use existing T&C PDFs** you have:
   - Copy any T&C PDF to this directory
   - Rename to `sample_tc.pdf` or update test fixtures

## Sample Files Structure

```
test_samples/
├── README.md                  # This file
├── sample_tc.pdf             # Simple T&C for basic testing
├── complex_tc.pdf            # Complex T&C with many sections
└── edge_cases/
    ├── scanned_doc.pdf       # Scanned document (OCR test)
    └── corrupted.pdf         # Corrupted/malformed PDF
```

## Quality Requirements

Good test samples should:
- ✅ Be actual T&C documents
- ✅ Have clear section structure (numbered or titled)
- ✅ Be text-based PDFs (not scanned images)
- ✅ Be under 10MB
- ✅ Be in English

## Quick Test

To verify a PDF works with the processor:

```python
import asyncio
from app.core.document_processor import DocumentProcessor

async def test():
    processor = DocumentProcessor()
    result = await processor.extract_text("data/test_samples/sample_tc.pdf")
    print(f"Extracted {len(result['text'])} characters")
    print(f"Pages: {result['page_count']}")
    print(f"Method: {result['extraction_method']}")

asyncio.run(test())
```

## Sources for Sample T&Cs

Good sources for test T&Cs:
- Google Terms of Service
- Spotify Terms of Service
- Netflix Terms of Use
- GitHub Terms of Service
- Any SaaS company T&C
