"""
Simple test script to verify document processing pipeline.

Usage:
    python test_pipeline.py [path/to/pdf]
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.core.document_processor import DocumentProcessor
from app.core.structure_extractor import StructureExtractor
from app.core.legal_chunker import LegalChunker


async def test_pipeline(pdf_path: str):
    """
    Test the complete document processing pipeline.

    Args:
        pdf_path: Path to PDF file
    """
    print("=" * 60)
    print("T&C Document Processing Pipeline Test")
    print("=" * 60)
    print()

    # Step 1: Document Processing
    print("Step 1: Extracting text from PDF...")
    processor = DocumentProcessor()
    
    try:
        result = await processor.extract_text(pdf_path)
        print(f"✓ Extracted {len(result['text'])} characters")
        print(f"✓ Page count: {result['page_count']}")
        print(f"✓ Extraction method: {result['extraction_method']}")
        
        # Check if it's a T&C document
        is_tc = await processor.is_tc_document(result['text'])
        print(f"✓ Is T&C document: {is_tc}")
        print()
    except Exception as e:
        print(f"✗ Failed to extract text: {e}")
        return

    # Step 2: Structure Extraction
    print("Step 2: Extracting structure...")
    extractor = StructureExtractor()
    
    try:
        structure = await extractor.extract_structure(result['text'])
        print(f"✓ Found {structure['num_sections']} sections")
        print(f"✓ Found {structure['num_clauses']} clauses")
        print()
        
        # Display sections
        print("Sections:")
        for i, section in enumerate(structure['sections'][:5], 1):
            print(f"  {i}. {section.get('title', 'Untitled')}")
        if len(structure['sections']) > 5:
            print(f"  ... and {len(structure['sections']) - 5} more")
        print()
    except Exception as e:
        print(f"✗ Failed to extract structure: {e}")
        return

    # Step 3: Chunking
    print("Step 3: Creating semantic chunks...")
    chunker = LegalChunker(max_chunk_size=500, overlap=50)
    
    try:
        chunks = await chunker.create_chunks(structure['sections'])
        print(f"✓ Created {len(chunks)} chunks")
        print()
        
        # Display sample chunks
        print("Sample chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"  Chunk {i}:")
            print(f"    Section: {chunk['metadata'].get('section', 'N/A')}")
            print(f"    Clause: {chunk['metadata'].get('clause_number', 'N/A')}")
            print(f"    Text length: {len(chunk['text'])} characters")
            print(f"    Preview: {chunk['text'][:100]}...")
            print()
    except Exception as e:
        print(f"✗ Failed to create chunks: {e}")
        return

    # Summary
    print("=" * 60)
    print("Pipeline Test Complete!")
    print("=" * 60)
    print(f"✓ Processed PDF with {result['page_count']} pages")
    print(f"✓ Extracted {structure['num_sections']} sections and {structure['num_clauses']} clauses")
    print(f"✓ Created {len(chunks)} semantic chunks")
    print()
    print("Next steps:")
    print("  1. Generate embeddings for chunks (requires OpenAI)")
    print("  2. Store in Pinecone vector database")
    print("  3. Run anomaly detection")


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline.py <path/to/pdf>")
        print()
        print("Example:")
        print("  python test_pipeline.py ../data/test_samples/sample_tc.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    await test_pipeline(pdf_path)


if __name__ == "__main__":
    asyncio.run(main())
