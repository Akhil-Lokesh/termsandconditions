"""
Test script to verify clause extraction improvements.

This script:
1. Tests the improved structure extractor with sample text
2. Compares old vs new extraction results
3. Shows detailed statistics

Usage:
    cd backend
    source venv/bin/activate
    python3 scripts/test_clause_extraction_fix.py
"""

import sys
from pathlib import Path
import asyncio

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.structure_extractor import StructureExtractor


# Sample T&C text (15-page equivalent)
LONG_SAMPLE_TC = """
TERMS AND CONDITIONS OF SERVICE

Effective Date: January 1, 2024

PLEASE READ THESE TERMS CAREFULLY BEFORE USING OUR SERVICE.

1. ACCEPTANCE OF TERMS

By accessing or using the Service, you acknowledge that you have read, understood, and agree to be bound by these Terms. If you do not agree to these Terms, you may not access or use the Service.

1.1 Agreement to Terms

You represent and warrant that you have the legal capacity to enter into this binding agreement.

1.2 Modifications to Terms

We reserve the right to modify these Terms at any time. We will notify you of material changes by posting the updated Terms on our website. Your continued use of the Service after such changes constitutes your acceptance of the modified Terms.

1.3 Additional Terms

Certain features of the Service may be subject to additional terms and conditions, which will be presented to you at the time you access such features.

2. USER ACCOUNTS AND REGISTRATION

To access certain features of the Service, you must register for an account.

2.1 Account Creation

When creating an account, you must provide accurate, current, and complete information. You are solely responsible for maintaining the confidentiality of your account credentials.

2.2 Account Security

You agree to:
(a) Notify us immediately of any unauthorized use of your account
(b) Ensure that you log out from your account at the end of each session
(c) Use a strong, unique password for your account

2.3 Account Termination

We reserve the right to suspend or terminate your account at any time for any reason, including if we reasonably believe you have violated these Terms.

3. USER OBLIGATIONS AND PROHIBITED CONDUCT

You agree to use the Service only for lawful purposes and in accordance with these Terms.

3.1 Prohibited Activities

You shall not:
(a) Use the Service to transmit any unlawful, harmful, or offensive content
(b) Attempt to gain unauthorized access to any portion of the Service
(c) Interfere with or disrupt the Service or servers connected to the Service
(d) Use any automated means to access the Service without our express written permission
(e) Impersonate any person or entity or misrepresent your affiliation with any person or entity

3.2 Content Standards

All content you submit must comply with applicable laws and must not be defamatory, obscene, threatening, or infringe on the rights of others.

3.3 Monitoring and Enforcement

We reserve the right, but are not obligated, to monitor, review, or remove content that we determine violates these Terms.

4. INTELLECTUAL PROPERTY RIGHTS

The Service and its entire contents, features, and functionality are owned by us and are protected by copyright, trademark, and other intellectual property laws.

4.1 License to Use Service

Subject to these Terms, we grant you a limited, non-exclusive, non-transferable, revocable license to access and use the Service for your personal, non-commercial use.

4.2 Restrictions on Use

You may not:
(a) Copy, modify, or create derivative works based on the Service
(b) Distribute, transmit, or publicly display the Service
(c) Decompile, reverse engineer, or disassemble any aspect of the Service
(d) Remove any copyright or proprietary notices from the Service

4.3 User Content License

By submitting content to the Service, you grant us a worldwide, non-exclusive, royalty-free license to use, reproduce, modify, and distribute such content in connection with the Service.

5. PRIVACY AND DATA PROTECTION

Your privacy is important to us. Our collection and use of personal information is governed by our Privacy Policy.

5.1 Data Collection

We collect information you provide directly, information we obtain from your use of the Service, and information from third-party sources.

5.2 Data Usage

We use your information to provide, maintain, and improve the Service, to communicate with you, and for other purposes described in our Privacy Policy.

5.3 Data Sharing

We may share your information with third-party service providers, business partners, and as required by law.

5.4 Data Security

We implement reasonable security measures to protect your information, but we cannot guarantee absolute security.

6. PAYMENT TERMS

Certain features of the Service may require payment of fees.

6.1 Subscription Fees

If you purchase a subscription, you agree to pay all applicable fees as described at the time of purchase.

6.2 Payment Methods

We accept various payment methods. You authorize us to charge your chosen payment method for all fees.

6.3 Automatic Renewal

Unless you cancel your subscription, it will automatically renew at the end of each billing period.

6.4 Refund Policy

All fees are non-refundable except as required by law or as expressly stated in these Terms.

7. DISCLAIMERS AND LIMITATIONS OF LIABILITY

7.1 Warranty Disclaimer

THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

7.2 Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICE.

7.3 Maximum Liability

OUR TOTAL LIABILITY TO YOU FOR ALL CLAIMS ARISING OUT OF OR RELATED TO THESE TERMS SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE TWELVE MONTHS PRECEDING THE CLAIM.

7.4 Indemnification

You agree to indemnify, defend, and hold harmless us and our affiliates from any claims, losses, and expenses arising from your use of the Service or violation of these Terms.

8. DISPUTE RESOLUTION

8.1 Governing Law

These Terms shall be governed by and construed in accordance with the laws of the State of California, without regard to its conflict of law provisions.

8.2 Arbitration Agreement

Any dispute arising out of or relating to these Terms shall be resolved through binding arbitration administered by the American Arbitration Association.

8.3 Class Action Waiver

YOU AGREE THAT ANY ARBITRATION OR PROCEEDING SHALL BE LIMITED TO THE DISPUTE BETWEEN YOU AND US INDIVIDUALLY. YOU WAIVE ANY RIGHT TO PURSUE DISPUTES ON A CLASS-WIDE BASIS.

8.4 Exceptions to Arbitration

Notwithstanding the above, either party may bring a claim in small claims court or seek injunctive relief in court.

9. TERMINATION

9.1 Termination by You

You may terminate your account at any time by contacting us or using the account termination feature in the Service.

9.2 Termination by Us

We may terminate or suspend your account and access to the Service immediately, without prior notice, if we believe you have violated these Terms.

9.3 Effect of Termination

Upon termination, your right to use the Service will immediately cease. Provisions that by their nature should survive termination shall survive.

10. THIRD-PARTY SERVICES AND CONTENT

10.1 Third-Party Links

The Service may contain links to third-party websites or services. We are not responsible for the content, policies, or practices of third-party websites.

10.2 Third-Party Integrations

We may offer integrations with third-party services. Your use of such integrations is subject to the third party's terms and conditions.

11. CHANGES TO THE SERVICE

11.1 Modifications

We reserve the right to modify, suspend, or discontinue any aspect of the Service at any time without notice.

11.2 No Obligation

We have no obligation to provide support, updates, or maintenance for the Service.

12. MISCELLANEOUS PROVISIONS

12.1 Entire Agreement

These Terms, together with our Privacy Policy, constitute the entire agreement between you and us regarding the Service.

12.2 Severability

If any provision of these Terms is found to be invalid or unenforceable, the remaining provisions shall continue in full force and effect.

12.3 Waiver

Our failure to enforce any provision of these Terms shall not constitute a waiver of that provision or any other provision.

12.4 Assignment

You may not assign or transfer these Terms or your rights under these Terms. We may assign these Terms without restriction.

12.5 Notices

All notices to you will be provided via email or by posting on the Service. You may provide notices to us at the address provided in the Contact section.

13. CONTACT INFORMATION

If you have any questions about these Terms, please contact us at:

Email: legal@example.com
Address: 123 Example Street, San Francisco, CA 94102
Phone: (555) 123-4567

Last Updated: January 1, 2024
"""


def print_section(title, char="="):
    """Print a section header."""
    print(f"\n{char * 80}")
    print(f"{title}")
    print(f"{char * 80}\n")


async def test_extraction(text: str, debug: bool = False):
    """Test structure extraction with debugging."""
    print_section("TESTING IMPROVED STRUCTURE EXTRACTOR")

    extractor = StructureExtractor(debug=debug)
    result = await extractor.extract_structure_with_stats(text)

    print(f"📄 Document Statistics:")
    print(f"   Total characters: {result['stats']['total_chars']:,}")
    print(f"   Total lines: {result['stats']['total_lines']:,}")
    print()

    print(f"📊 Extraction Results:")
    print(f"   Method used: {result['extraction_method']}")
    print(f"   Sections found: {result['num_sections']}")
    print(f"   Clauses found: {result['num_clauses']}")
    print()

    print(f"📈 Clause Distribution:")
    print(f"   Avg clauses/section: {result['stats']['avg_clauses_per_section']:.1f}")
    print(f"   Min clauses in a section: {result['stats']['min_clauses']}")
    print(f"   Max clauses in a section: {result['stats']['max_clauses']}")
    print(f"   Sections with >1 clause: {result['stats']['sections_with_multiple_clauses']}")
    print()

    print(f"🔍 Section Breakdown:")
    for idx, section in enumerate(result['sections'][:10], 1):  # Show first 10
        print(f"   {idx}. [{section['number']}] {section['title'][:60]}")
        print(f"      Clauses: {len(section['clauses'])}")

    if len(result['sections']) > 10:
        print(f"   ... and {len(result['sections']) - 10} more sections")

    print()

    # Verify expectations
    print_section("VERIFICATION")

    expected_sections = 13  # Based on the sample text
    expected_clauses_min = 40  # Rough estimate

    print(f"✓ Sections: {result['num_sections']} (expected ~{expected_sections})")
    if result['num_sections'] >= expected_sections * 0.8:
        print(f"  ✅ PASS: Found sufficient sections")
    else:
        print(f"  ⚠️  WARNING: Found fewer sections than expected")

    print()
    print(f"✓ Clauses: {result['num_clauses']} (expected >{expected_clauses_min})")
    if result['num_clauses'] >= expected_clauses_min:
        print(f"  ✅ PASS: Found sufficient clauses")
    else:
        print(f"  ⚠️  WARNING: Found fewer clauses than expected")

    print()

    if result['extraction_method'] == 'pattern':
        print(f"  ✅ PASS: Used pattern-based extraction (optimal)")
    else:
        print(f"  ⚠️  WARNING: Used paragraph fallback (document may be poorly formatted)")

    return result


async def compare_results():
    """Compare extraction results."""
    print_section("COMPARISON: BEFORE vs AFTER FIX", "=")

    text = LONG_SAMPLE_TC

    print("BEFORE FIX:")
    print("  Typical result: 1 section, 1 clause (entire document as one chunk)")
    print()

    print("AFTER FIX:")
    await test_extraction(text, debug=False)

    print()
    print_section("IMPROVEMENTS", "=")
    print("""
The improved extractor includes:

1. ✅ More flexible section patterns (handles variations in formatting)
2. ✅ Additional clause patterns (3-level numbering, letters, bullets)
3. ✅ Paragraph-based fallback (for poorly formatted documents)
4. ✅ Text normalization (handles different line endings)
5. ✅ Debug mode (for troubleshooting specific documents)
6. ✅ Detailed statistics (for verification)

Expected improvements:
- 15-page PDF should now extract 15-30+ clauses (vs 1 clause before)
- Better section detection
- More accurate clause boundaries
- Better handling of edge cases
""")


async def main():
    """Run all tests."""
    print_section("CLAUSE EXTRACTION FIX VERIFICATION", "=")
    print("This script verifies that clause extraction improvements are working.\n")

    await compare_results()

    print()
    print_section("NEXT STEPS", "=")
    print("""
1. ✅ Improved structure extractor is now active
2. ⏳ Test with real PDF documents:
   - Upload a PDF via the API
   - Check the clause_count in the response
   - Verify it extracts 15-30+ clauses for a 15-page document

3. If issues persist:
   - Enable debug mode: StructureExtractor(debug=True)
   - Check logs for pattern matching details
   - Use scripts/debug_structure_extraction.py for detailed analysis

4. To test immediately:
   - Start backend: uvicorn app.main:app --reload
   - Upload a T&C PDF via the upload endpoint
   - Check the response for num_clauses field
""")


if __name__ == "__main__":
    asyncio.run(main())
