"""
Create a simple test PDF for development testing.
This creates a sample Terms & Conditions document.
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path

def create_test_tc_pdf():
    """Create a sample T&C PDF with realistic content."""

    output_path = Path(__file__).parent.parent.parent / "data" / "test_samples" / "sample_terms.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(inch, height - inch, "TERMS AND CONDITIONS OF SERVICE")

    # Subtitle
    c.setFont("Helvetica", 10)
    c.drawString(inch, height - inch * 1.3, "Effective Date: January 1, 2024")
    c.drawString(inch, height - inch * 1.5, "Company: Sample Tech Inc.")
    c.drawString(inch, height - inch * 1.7, "Jurisdiction: California, United States")

    y = height - inch * 2.2

    # Content sections
    sections = [
        ("1. ACCEPTANCE OF TERMS", [
            "By accessing or using our service, you agree to be bound by these Terms and Conditions.",
            "If you do not agree to these terms, please do not use our service.",
        ]),

        ("2. USER ACCOUNT", [
            "You must create an account to use certain features of our service.",
            "You are responsible for maintaining the confidentiality of your account credentials.",
            "You agree to notify us immediately of any unauthorized access to your account.",
        ]),

        ("3. ACCEPTABLE USE", [
            "You agree not to use our service for any unlawful purpose.",
            "You will not attempt to gain unauthorized access to our systems.",
            "You will not transmit viruses, malware, or other harmful code.",
        ]),

        ("4. INTELLECTUAL PROPERTY", [
            "All content and materials available through our service are owned by or licensed to us.",
            "You may not copy, modify, or distribute our content without permission.",
        ]),

        ("5. PAYMENT TERMS", [
            "Certain features of our service require payment.",
            "All fees are non-refundable unless otherwise stated.",
            "We reserve the right to change our pricing at any time.",
        ]),

        ("6. LIMITATION OF LIABILITY", [
            "TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY",
            "INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING",
            "FROM YOUR USE OF THE SERVICE.",
        ]),

        ("7. INDEMNIFICATION", [
            "You agree to indemnify and hold us harmless from any claims, losses, or damages",
            "arising from your use of the service or violation of these terms.",
        ]),

        ("8. TERMINATION", [
            "We may terminate or suspend your account at any time, with or without notice,",
            "for any reason, including violation of these terms.",
        ]),

        ("9. CHANGES TO TERMS", [
            "We reserve the right to modify these terms at any time.",
            "Continued use of the service after changes constitutes acceptance.",
        ]),

        ("10. GOVERNING LAW", [
            "These terms shall be governed by the laws of the State of California.",
            "Any disputes shall be resolved in the courts of California.",
        ]),

        ("11. CONTACT INFORMATION", [
            "For questions about these terms, please contact us at legal@sampletech.com",
        ]),
    ]

    for title, paragraphs in sections:
        # Check if we need a new page
        if y < 2 * inch:
            c.showPage()
            y = height - inch

        # Section title
        c.setFont("Helvetica-Bold", 12)
        c.drawString(inch, y, title)
        y -= 0.25 * inch

        # Section content
        c.setFont("Helvetica", 10)
        for para in paragraphs:
            # Word wrap
            words = para.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if c.stringWidth(test_line, "Helvetica", 10) < width - 2 * inch:
                    line = test_line
                else:
                    c.drawString(inch, y, line.strip())
                    y -= 0.2 * inch
                    line = word + " "

                    # Check for new page
                    if y < 2 * inch:
                        c.showPage()
                        y = height - inch

            if line.strip():
                c.drawString(inch, y, line.strip())
                y -= 0.2 * inch

        y -= 0.3 * inch  # Space between sections

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(inch, inch * 0.5, "© 2024 Sample Tech Inc. All rights reserved.")

    c.save()
    print(f"✅ Created test PDF: {output_path}")
    return output_path

if __name__ == "__main__":
    create_test_tc_pdf()
