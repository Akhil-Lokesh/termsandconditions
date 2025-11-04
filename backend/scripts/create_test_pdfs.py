#!/usr/bin/env python3
"""
Generate test PDF samples for development and testing.

Creates two sample T&C documents:
1. simple_tos.pdf - Standard terms with normal clauses
2. risky_tos.pdf - Contains risky/unusual clauses for anomaly detection testing

Usage:
    python scripts/create_test_pdfs.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def wrap_text(c, text, x, y, max_width, line_height=15):
    """
    Wrap text to fit within max_width.

    Returns the new y position after writing all lines.
    """
    words = text.split()
    line = ""

    for word in words:
        # Test if adding this word exceeds max width
        test_line = line + word + " "
        if c.stringWidth(test_line) < max_width:
            line = test_line
        else:
            # Write current line and start new one
            if line:
                c.drawString(x, y, line.strip())
                y -= line_height
            line = word + " "

    # Write final line
    if line:
        c.drawString(x, y, line.strip())
        y -= line_height

    return y


def create_simple_tos():
    """Create a simple T&C document for testing."""
    output = project_root / "data" / "test_samples" / "simple_tos.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1*inch, height - 1*inch, "TERMS OF SERVICE")

    # Metadata
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.3*inch, "Example Corporation")
    c.drawString(1*inch, height - 1.5*inch, "Effective Date: January 1, 2024")
    c.drawString(1*inch, height - 1.7*inch, "Last Updated: October 30, 2024")

    y = height - 2.2*inch

    # Sections with standard clauses
    sections = [
        {
            "title": "1. ACCEPTANCE OF TERMS",
            "content": "By accessing or using our services, you agree to be bound by these Terms of Service. "
                      "If you do not agree to these terms, please do not use our services. "
                      "Your continued use of the services constitutes acceptance of any modifications to these terms."
        },
        {
            "title": "2. USER ACCOUNTS",
            "content": "You may be required to create an account to access certain features. "
                      "You are responsible for maintaining the confidentiality of your account credentials. "
                      "You agree to notify us immediately of any unauthorized use of your account."
        },
        {
            "title": "3. USER CONDUCT",
            "content": "You agree to use the services only for lawful purposes. "
                      "You shall not engage in any activity that interferes with or disrupts the services. "
                      "You shall not attempt to gain unauthorized access to any portion of the services."
        },
        {
            "title": "4. INTELLECTUAL PROPERTY",
            "content": "All content and materials available through our services are protected by intellectual property rights. "
                      "You may not copy, modify, distribute, or create derivative works without our express written permission. "
                      "You retain ownership of any content you submit to the services."
        },
        {
            "title": "5. PAYMENT TERMS",
            "content": "Certain features may require payment. You agree to pay all applicable fees as described on our website. "
                      "Payments are non-refundable except as required by law or as expressly stated in our refund policy. "
                      "We reserve the right to change our fees with 30 days notice."
        },
        {
            "title": "6. LIMITATION OF LIABILITY",
            "content": "To the maximum extent permitted by law, we shall not be liable for any indirect, incidental, "
                      "special, consequential, or punitive damages arising out of your use of the services. "
                      "Our total liability shall not exceed the amount you paid us in the past 12 months."
        },
        {
            "title": "7. TERMINATION",
            "content": "We may suspend or terminate your access to the services at any time for violation of these terms. "
                      "You may terminate your account at any time by contacting customer support. "
                      "Upon termination, your right to use the services will immediately cease."
        },
        {
            "title": "8. GOVERNING LAW",
            "content": "These terms shall be governed by and construed in accordance with the laws of the State of California. "
                      "Any disputes shall be resolved in the courts located in San Francisco County, California. "
                      "You consent to the personal jurisdiction of such courts."
        },
    ]

    for section in sections:
        # Section title
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1*inch, y, section["title"])
        y -= 20

        # Section content
        c.setFont("Helvetica", 10)
        y = wrap_text(c, section["content"], 1*inch, y, 6.5*inch)
        y -= 15

        # New page if needed
        if y < 1.5*inch:
            c.showPage()
            y = height - 1*inch

    c.save()
    print(f"✓ Created: {output}")
    return str(output)


def create_risky_tos():
    """Create a T&C with risky clauses for anomaly detection testing."""
    output = project_root / "data" / "test_samples" / "risky_tos.pdf"

    c = canvas.Canvas(str(output), pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1*inch, height - 1*inch, "TERMS OF SERVICE")

    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.3*inch, "Risky Corporation Inc.")
    c.drawString(1*inch, height - 1.5*inch, "Effective Date: October 1, 2024")

    y = height - 2*inch

    # Risky clauses designed to trigger anomaly detection
    risky_sections = [
        {
            "title": "1. CHANGES TO TERMS",
            "content": "We reserve the right to change, modify, or revise these terms at any time "
                      "at our sole and absolute discretion without any prior notice to you whatsoever. "
                      "Your continued use of the service after such changes constitutes your binding acceptance. "
                      "It is your responsibility to check these terms daily for updates."
        },
        {
            "title": "2. UNLIMITED LIABILITY",
            "content": "You agree to assume unlimited personal liability for any and all claims, "
                      "damages, or expenses arising from your use of our services. "
                      "You waive any right to contest the amount of liability or damages claimed by us. "
                      "This includes liability for actions taken by third parties using your account."
        },
        {
            "title": "3. DISPUTE RESOLUTION",
            "content": "You hereby waive your right to participate in any class action lawsuit or class-wide arbitration. "
                      "All disputes must be resolved through binding individual arbitration. "
                      "The arbitrator's decision is final and cannot be appealed. "
                      "You waive your right to a jury trial and to any legal recourse in court."
        },
        {
            "title": "4. DATA USAGE AND SHARING",
            "content": "We may collect, use, and share all of your personal data including but not limited to "
                      "browsing history, location data, financial information, and communications with third parties "
                      "for any purpose including selling to advertisers and data brokers without restriction. "
                      "We are not required to notify you of data breaches or security incidents."
        },
        {
            "title": "5. AUTOMATIC RENEWAL AND CHARGES",
            "content": "Your subscription will automatically renew indefinitely and we will charge your payment method "
                      "without advance notice. Cancellation requests may be denied at our sole discretion. "
                      "We may increase fees at any time without notice. You authorize us to charge any payment method on file."
        },
        {
            "title": "6. NO REFUNDS POLICY",
            "content": "All payments, fees, and charges are final, non-refundable, and non-transferable "
                      "under any and all circumstances including but not limited to service outages, dissatisfaction, "
                      "duplicate charges, unauthorized transactions, or account termination. "
                      "No exceptions will be made regardless of circumstances."
        },
        {
            "title": "7. CONTENT OWNERSHIP",
            "content": "By uploading or submitting any content to our services, you grant us a perpetual, "
                      "irrevocable, worldwide, royalty-free license to use, modify, reproduce, and distribute "
                      "your content for any purpose. We may use your likeness and personal information in marketing. "
                      "You waive all moral rights to your content."
        },
        {
            "title": "8. INDEMNIFICATION",
            "content": "You agree to indemnify, defend, and hold harmless the company and all its officers, "
                      "directors, employees, and affiliates from any and all claims, liabilities, damages, losses, "
                      "costs, expenses, and fees (including reasonable attorneys' fees) arising from your use "
                      "of the services or violation of these terms, with no limit on liability amount."
        },
        {
            "title": "9. WARRANTY DISCLAIMER",
            "content": "THE SERVICES ARE PROVIDED AS IS WITHOUT ANY WARRANTIES OF ANY KIND. "
                      "WE DISCLAIM ALL WARRANTIES EXPRESS OR IMPLIED INCLUDING MERCHANTABILITY AND FITNESS "
                      "FOR A PARTICULAR PURPOSE. WE DO NOT WARRANT THAT THE SERVICES WILL BE UNINTERRUPTED OR ERROR-FREE. "
                      "USE AT YOUR OWN RISK."
        },
        {
            "title": "10. ACCOUNT SUSPENSION",
            "content": "We may suspend, terminate, or delete your account at any time for any reason or no reason "
                      "without notice or explanation. We have no obligation to preserve your data or content. "
                      "You will not be entitled to any refunds or compensation upon account termination."
        },
    ]

    for section in risky_sections:
        # Section title
        c.setFont("Helvetica-Bold", 11)
        c.drawString(1*inch, y, section["title"])
        y -= 18

        # Section content
        c.setFont("Helvetica", 9)
        y = wrap_text(c, section["content"], 1*inch, y, 6.5*inch, line_height=13)
        y -= 20

        # New page if needed
        if y < 1.5*inch:
            c.showPage()
            y = height - 1*inch

    c.save()
    print(f"✓ Created: {output}")
    return str(output)


def main():
    """Generate all test PDFs."""
    print("="*70)
    print("GENERATING TEST PDF SAMPLES")
    print("="*70)
    print()

    print("Creating test samples...")
    print()

    simple_path = create_simple_tos()
    risky_path = create_risky_tos()

    print()
    print("="*70)
    print("✓ TEST PDFS CREATED SUCCESSFULLY!")
    print("="*70)
    print()
    print("Generated files:")
    print(f"  1. {simple_path}")
    print(f"     → Standard T&C with normal clauses")
    print()
    print(f"  2. {risky_path}")
    print(f"     → T&C with risky clauses (for anomaly detection testing)")
    print()
    print("You can now upload these files to test the system:")
    print("  - Use simple_tos.pdf for basic functionality testing")
    print("  - Use risky_tos.pdf to verify anomaly detection works")
    print()


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        if "reportlab" in str(e):
            print("\n❌ ERROR: reportlab not installed")
            print("\nPlease install it with:")
            print("  pip install reportlab")
            print("\nThen run this script again.")
            sys.exit(1)
        else:
            raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
