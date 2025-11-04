"""
Debug script for structure extraction issues.

This script helps identify why clause extraction is failing by:
1. Testing each regex pattern individually
2. Showing what text is being matched
3. Providing detailed debugging output
4. Testing with sample T&C text

Usage:
    cd backend
    source venv/bin/activate
    python3 scripts/debug_structure_extraction.py
"""

import sys
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.structure_extractor import StructureExtractor
import asyncio


# Sample T&C text with various formatting styles
SAMPLE_TC_TEXT = """
TERMS AND CONDITIONS

Last Updated: January 1, 2024

These Terms and Conditions ("Terms") govern your use of our service.

1. ACCEPTANCE OF TERMS

By accessing or using our service, you agree to be bound by these Terms.

1.1 Agreement to Terms
You acknowledge that you have read and understood these Terms.

1.2 Modifications
We may modify these Terms at any time. Continued use constitutes acceptance.

2. USER OBLIGATIONS

You agree to use our service in accordance with all applicable laws.

2.1 Account Registration
You must provide accurate information when creating an account.

2.2 Account Security
You are responsible for maintaining the security of your account credentials.

2.3 Prohibited Activities
You may not:
(a) Use the service for illegal purposes
(b) Attempt to gain unauthorized access
(c) Interfere with service operations

3. PRIVACY AND DATA PROTECTION

We respect your privacy and handle your data in accordance with our Privacy Policy.

3.1 Data Collection
We collect information you provide when using our service.

3.2 Data Usage
Your data may be used to improve our services and provide support.

4. INTELLECTUAL PROPERTY

All content and materials are owned by us or our licensors.

4.1 License Grant
We grant you a limited license to use our service.

4.2 Restrictions
You may not copy, modify, or distribute our content without permission.

5. LIMITATION OF LIABILITY

TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY DAMAGES.

5.1 Disclaimer of Warranties
THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND.

5.2 Indemnification
You agree to indemnify us against any claims arising from your use of the service.

6. TERMINATION

We may terminate your access at any time for any reason.

6.1 Effect of Termination
Upon termination, your right to use the service immediately ceases.

7. GOVERNING LAW

These Terms shall be governed by the laws of the State of California.

8. DISPUTE RESOLUTION

Any disputes shall be resolved through binding arbitration.

8.1 Arbitration Process
Arbitration shall be conducted in accordance with AAA rules.

8.2 Class Action Waiver
You waive any right to participate in class action lawsuits.

9. MISCELLANEOUS

9.1 Entire Agreement
These Terms constitute the entire agreement between you and us.

9.2 Severability
If any provision is invalid, the remaining provisions remain in effect.

9.3 Waiver
Failure to enforce any provision does not constitute a waiver.

10. CONTACT INFORMATION

For questions about these Terms, contact us at legal@example.com.
"""


def print_section(title, char="="):
    """Print a section header."""
    print(f"\n{char * 80}")
    print(f"{title}")
    print(f"{char * 80}\n")


def test_section_patterns(text):
    """Test all section patterns and show results."""
    print_section("TESTING SECTION PATTERNS")

    extractor = StructureExtractor()
    lines = text.split("\n")

    for idx, pattern in enumerate(extractor.SECTION_PATTERNS, 1):
        print(f"Pattern {idx}: {pattern}")
        print("-" * 80)

        matches = []
        for line_num, line in enumerate(lines):
            match = re.match(pattern, line.strip(), re.MULTILINE)
            if match:
                matches.append({
                    "line_num": line_num,
                    "line": line.strip(),
                    "group1": match.group(1),
                    "group2": match.group(2) if match.lastindex >= 2 else None
                })

        if matches:
            print(f"✓ Found {len(matches)} matches:")
            for match in matches[:10]:  # Show first 10
                print(f"  Line {match['line_num']:3d}: [{match['group1']}] {match['group2']}")
                print(f"               Full: {match['line'][:70]}")
        else:
            print(f"✗ No matches found")

        print()


def test_clause_patterns(text):
    """Test all clause patterns and show results."""
    print_section("TESTING CLAUSE PATTERNS")

    extractor = StructureExtractor()
    lines = text.split("\n")

    for idx, pattern in enumerate(extractor.CLAUSE_PATTERNS, 1):
        print(f"Pattern {idx}: {pattern}")
        print("-" * 80)

        matches = []
        for line_num, line in enumerate(lines):
            match = re.match(pattern, line.strip())
            if match:
                matches.append({
                    "line_num": line_num,
                    "line": line.strip(),
                    "clause_id": match.group(1),
                    "clause_text": match.group(2) if match.lastindex >= 2 else None
                })

        if matches:
            print(f"✓ Found {len(matches)} matches:")
            for match in matches[:15]:  # Show first 15
                print(f"  Line {match['line_num']:3d}: [{match['clause_id']}] {match['clause_text'][:60] if match['clause_text'] else 'N/A'}")
        else:
            print(f"✗ No matches found")

        print()


def show_text_preview(text, num_lines=30):
    """Show preview of text to understand structure."""
    print_section("TEXT PREVIEW (First 30 lines)")

    lines = text.split("\n")
    for i, line in enumerate(lines[:num_lines], 1):
        if line.strip():
            print(f"{i:3d}: {line}")


def analyze_text_characteristics(text):
    """Analyze text to identify patterns."""
    print_section("TEXT ANALYSIS")

    lines = text.split("\n")
    non_empty_lines = [l for l in lines if l.strip()]

    print(f"Total lines: {len(lines)}")
    print(f"Non-empty lines: {len(non_empty_lines)}")
    print(f"Total characters: {len(text)}")
    print()

    # Identify potential sections by looking for numbered lines
    print("Potential section headers (lines starting with digits):")
    numbered_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and re.match(r'^\d+\.', stripped):
            numbered_lines.append((i, stripped))

    if numbered_lines:
        for line_num, line in numbered_lines[:20]:
            print(f"  Line {line_num:3d}: {line[:70]}")
    else:
        print("  None found")

    print()

    # Identify lines with subsection numbering
    print("Potential subsections (lines starting with X.Y):")
    subsection_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and re.match(r'^\d+\.\d+', stripped):
            subsection_lines.append((i, stripped))

    if subsection_lines:
        for line_num, line in subsection_lines[:20]:
            print(f"  Line {line_num:3d}: {line[:70]}")
    else:
        print("  None found")

    print()

    # Identify all-caps lines (potential section headers)
    print("All-caps lines (potential section headers):")
    caps_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and len(stripped) > 5 and stripped.isupper():
            caps_lines.append((i, stripped))

    if caps_lines:
        for line_num, line in caps_lines[:20]:
            print(f"  Line {line_num:3d}: {line[:70]}")
    else:
        print("  None found")


async def test_actual_extraction(text):
    """Test actual extraction process."""
    print_section("ACTUAL EXTRACTION TEST")

    extractor = StructureExtractor()
    result = await extractor.extract_structure(text)

    print(f"Number of sections: {result['num_sections']}")
    print(f"Number of clauses: {result['num_clauses']}")
    print()

    for section in result['sections'][:5]:  # Show first 5 sections
        print(f"Section {section['number']}: {section['title']}")
        print(f"  Clauses: {len(section['clauses'])}")
        if section['clauses']:
            for clause in section['clauses'][:3]:  # Show first 3 clauses
                print(f"    - {clause['id']}: {clause['text'][:80]}...")
        print()


def suggest_improvements():
    """Suggest improvements based on analysis."""
    print_section("SUGGESTED IMPROVEMENTS", "=")

    print("""
Based on the analysis, here are potential improvements:

1. SECTION PATTERNS:
   - Current patterns require exact formatting (e.g., "1. TITLE" with period and space)
   - Add more flexible patterns:
     * r'^(\d+)\s+([A-Z][^\n]+)'  # "1 TITLE" (no period)
     * r'^(\d+)\.\s*([A-Z].*?)$'  # More flexible with whitespace
     * r'^([IVX]+)\.\s+(.+)'      # Roman numerals

2. CLAUSE PATTERNS:
   - Add support for:
     * r'^(\d+\.\d+\.\d+)\s+(.+)'  # "1.1.1 Sub-clause"
     * r'^([A-Z])\.\s+(.+)'        # "A. Clause"
     * r'^\((\d+)\)\s+(.+)'        # "(1) Clause"

3. TEXT PREPROCESSING:
   - Normalize whitespace (convert multiple spaces to single)
   - Handle different line endings (\\r\\n, \\n, \\r)
   - Trim lines consistently

4. FALLBACK STRATEGIES:
   - If no sections found, try paragraph-based splitting
   - Look for blank lines as section separators
   - Use heading detection (bold, all-caps, numbered)

5. DEBUGGING:
   - Add debug flag to log pattern matching attempts
   - Show which patterns matched and how many times
   - Log when falling back to default behavior
""")


async def main():
    """Run all debug tests."""
    print_section("STRUCTURE EXTRACTION DEBUG TOOL", "=")
    print("This tool helps identify why clause extraction is failing.\n")

    # Use sample text
    text = SAMPLE_TC_TEXT

    # Run all tests
    show_text_preview(text)
    analyze_text_characteristics(text)
    test_section_patterns(text)
    test_clause_patterns(text)
    await test_actual_extraction(text)
    suggest_improvements()

    print_section("DEBUG COMPLETE", "=")
    print("""
Next steps:
1. Review the pattern matching results above
2. Identify which patterns work for your specific document format
3. Update structure_extractor.py with working patterns
4. Add new patterns for formats not currently supported
5. Test with real PDF documents

To test with a real PDF:
1. Place PDF in data/test_samples/
2. Modify this script to use document_processor to extract text
3. Run the debug tests on the extracted text
""")


if __name__ == "__main__":
    asyncio.run(main())
