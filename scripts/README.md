# Scripts Directory

This directory contains utility scripts for the T&C Analysis System.

## Available Scripts

### `build_baseline_corpus.py`

**Purpose**: Process all baseline T&C documents and upload to Pinecone

**Usage**:
```bash
python build_baseline_corpus.py [--env production]
```

**What it does**:
1. Scans `data/baseline_corpus/` for PDF files
2. Processes each PDF:
   - Extracts text
   - Identifies structure (sections/clauses)
   - Generates embeddings
3. Uploads to Pinecone baseline namespace
4. Logs progress and errors

**Options**:
- `--env production` - Use production Pinecone index
- `--force` - Reprocess all documents (ignore cache)
- `--industry streaming` - Only process specific industry
- `--limit 10` - Process only first N documents (testing)

**Expected runtime**: 3-8 hours for 100 documents

**Output**:
```
Processing baseline corpus...
[1/100] spotify_tos_2024.pdf... ✓ (45 clauses, 2.3s)
[2/100] netflix_tos_2024.pdf... ✓ (38 clauses, 1.8s)
...
[100/100] discord_tos_2024.pdf... ✓ (52 clauses, 2.6s)

Summary:
- Processed: 100 documents
- Total clauses: 4,234
- Failed: 2 documents
- Total time: 4h 23m
```

---

### `test_structure_extraction.py`

**Purpose**: Test structure extraction on sample PDFs

**Usage**:
```bash
python test_structure_extraction.py data/test_samples/spotify_tos.pdf
```

**What it does**:
1. Extracts text from PDF
2. Runs structure extractor
3. Displays found sections and clauses
4. Shows extraction accuracy

**Output**:
```
Testing: spotify_tos.pdf

Company: Spotify
Sections: 12
Clauses: 45

Sections:
1. Introduction
2. The Spotify Service
3. Your Use of the Spotify Service
...

Sample Clauses:
3.1: You may use the Spotify Service only...
3.2: You may not reverse engineer...
...

Accuracy: 89% (40/45 clauses correctly identified)
```

---

### `evaluate_anomaly_detection.py`

**Purpose**: Evaluate anomaly detection accuracy on test set

**Usage**:
```bash
python evaluate_anomaly_detection.py
```

**What it does**:
1. Loads test T&Cs with known risky clauses
2. Runs anomaly detection
3. Compares detected vs. expected anomalies
4. Calculates metrics (precision, recall, F1)

**Output**:
```
Evaluating anomaly detection...

Test Case 1: spotify_tos.pdf
Expected anomalies: 3
Detected anomalies: 2
True positives: 2
False positives: 0
False negatives: 1

Test Case 2: example_risky_tos.pdf
Expected anomalies: 8
Detected anomalies: 7
True positives: 6
False positives: 1
False negatives: 2

Overall Metrics:
Precision: 85.7%
Recall: 72.7%
F1 Score: 78.6%
```

---

### `setup_dev_environment.sh`

**Purpose**: Automated development environment setup

**Usage**:
```bash
bash setup_dev_environment.sh
```

**What it does**:
1. Checks prerequisites (Python, Node, Docker)
2. Creates virtual environment
3. Installs dependencies
4. Copies .env.example files
5. Starts Docker services
6. Runs database migrations
7. Creates Pinecone indexes
8. Verifies setup

**Output**:
```
Setting up T&C Analysis System development environment...

✓ Python 3.10 found
✓ Node.js 18 found
✓ Docker found

Setting up backend...
✓ Virtual environment created
✓ Dependencies installed
✓ .env file created

Setting up frontend...
✓ Dependencies installed
✓ .env file created

Starting services...
✓ PostgreSQL running on port 5432
✓ Redis running on port 6379

Database setup...
✓ Migrations applied

Pinecone setup...
✓ Indexes created

Setup complete! ✨

Next steps:
1. Edit .env files with your API keys
2. Run: cd backend && uvicorn app.main:app --reload
3. Run: cd frontend && npm run dev
```

---

## Creating New Scripts

When creating new utility scripts:

### Script Template

```python
#!/usr/bin/env python3
"""
Script description here.

Usage:
    python script_name.py [options]

Examples:
    python script_name.py --option value
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.core.document_processor import DocumentProcessor


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Script logic here
    print(f"Processing: {args.input}")


if __name__ == "__main__":
    main()
```

### Best Practices

1. **Add docstring**: Describe purpose and usage
2. **Use argparse**: For command-line arguments
3. **Add logging**: Use Python logging module
4. **Error handling**: Catch and report errors gracefully
5. **Progress tracking**: Show progress for long operations
6. **Make executable**: `chmod +x script_name.py`
7. **Add shebang**: `#!/usr/bin/env python3`

---

## Development Scripts

### Quick Test Script

```python
# test_quick.py
"""Quick test of core functionality."""

from app.core.document_processor import DocumentProcessor

processor = DocumentProcessor()
result = processor.process_document(
    file_content=open('test.pdf', 'rb').read(),
    filename='test.pdf',
    user_id=1
)

print(f"Company: {result['company_name']}")
print(f"Sections: {result['num_sections']}")
```

### Database Reset Script

```bash
# reset_db.sh
#!/bin/bash

echo "Resetting database..."
alembic downgrade base
alembic upgrade head
echo "Database reset complete"
```

### Cleanup Script

```bash
# cleanup.sh
#!/bin/bash

echo "Cleaning up..."
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf .pytest_cache
rm -rf htmlcov
echo "Cleanup complete"
```

---

## Automation

### Cron Jobs (Optional)

For automated baseline corpus updates:

```bash
# Update baseline corpus monthly
0 0 1 * * /path/to/build_baseline_corpus.py --env production
```

### GitHub Actions

For CI/CD automation, see `.github/workflows/` directory.

---

## Troubleshooting

### Script Fails with Import Error

```bash
# Ensure you're in the correct directory
cd scripts

# Activate virtual environment
source ../backend/venv/bin/activate

# Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
```

### Permission Denied

```bash
# Make script executable
chmod +x script_name.py

# Run with python
python script_name.py
```

### Module Not Found

```bash
# Install dependencies
pip install -r ../backend/requirements.txt
```

---

## Next Steps

1. **Week 1**: Use `setup_dev_environment.sh` for initial setup
2. **Week 2**: Use `test_structure_extraction.py` to verify extraction
3. **Week 6**: Use `build_baseline_corpus.py` to process corpus
4. **Week 7**: Use `evaluate_anomaly_detection.py` to tune detection

---

## Contributing Scripts

When adding new scripts:

1. Add to this README
2. Include docstring with usage examples
3. Add to `.gitignore` if it generates sensitive data
4. Test on fresh environment
5. Document any dependencies
