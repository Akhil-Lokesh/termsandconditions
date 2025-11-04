#!/usr/bin/env python3
"""
Baseline Corpus Collection Script

This script collects 100+ standard Terms & Conditions documents from public sources
for anomaly detection baseline comparison.

Features:
- Automated web scraping with Playwright
- Manual download support via URL list
- Organized by category (tech, ecommerce, saas, finance, general)
- Metadata tracking
- Progress tracking and resume capability

Prerequisites:
    pip install playwright httpx beautifulsoup4
    playwright install chromium

Usage:
    # Collect all sources
    python scripts/collect_baseline_corpus.py --output data/baseline_corpus

    # Collect specific category
    python scripts/collect_baseline_corpus.py --category tech

    # Resume interrupted collection
    python scripts/collect_baseline_corpus.py --resume
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import argparse

try:
    import httpx
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install playwright httpx beautifulsoup4")
    print("   playwright install chromium")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("corpus_collection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# BASELINE SOURCES DATABASE
# ============================================================================
# This is a curated list of 100+ T&C sources across 5 categories
# Format: {"name": "Company", "url": "https://...", "type": "web" or "pdf"}
# ============================================================================

BASELINE_SOURCES = {
    "tech": [
        # Social Media & Communication (15)
        {"name": "Google", "url": "https://policies.google.com/terms", "type": "web"},
        {"name": "Facebook", "url": "https://www.facebook.com/legal/terms", "type": "web"},
        {"name": "Twitter", "url": "https://twitter.com/en/tos", "type": "web"},
        {"name": "Instagram", "url": "https://help.instagram.com/581066165581870", "type": "web"},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/legal/user-agreement", "type": "web"},
        {"name": "WhatsApp", "url": "https://www.whatsapp.com/legal/terms-of-service", "type": "web"},
        {"name": "Telegram", "url": "https://telegram.org/tos", "type": "web"},
        {"name": "Discord", "url": "https://discord.com/terms", "type": "web"},
        {"name": "Reddit", "url": "https://www.redditinc.com/policies/user-agreement", "type": "web"},
        {"name": "TikTok", "url": "https://www.tiktok.com/legal/page/us/terms-of-service/en", "type": "web"},
        {"name": "Snapchat", "url": "https://www.snap.com/en-US/terms", "type": "web"},
        {"name": "Pinterest", "url": "https://policy.pinterest.com/en/terms-of-service", "type": "web"},
        {"name": "Tumblr", "url": "https://www.tumblr.com/policy/en/terms-of-service", "type": "web"},
        {"name": "YouTube", "url": "https://www.youtube.com/t/terms", "type": "web"},
        {"name": "Zoom", "url": "https://zoom.us/terms", "type": "web"},

        # Cloud & Enterprise (10)
        {"name": "Microsoft", "url": "https://www.microsoft.com/en-us/servicesagreement", "type": "web"},
        {"name": "Apple", "url": "https://www.apple.com/legal/internet-services/terms/site.html", "type": "web"},
        {"name": "Amazon_AWS", "url": "https://aws.amazon.com/service-terms/", "type": "web"},
        {"name": "Dropbox", "url": "https://www.dropbox.com/terms", "type": "web"},
        {"name": "GitHub", "url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service", "type": "web"},
        {"name": "GitLab", "url": "https://about.gitlab.com/terms/", "type": "web"},
        {"name": "Atlassian", "url": "https://www.atlassian.com/legal/cloud-terms-of-service", "type": "web"},
        {"name": "Adobe", "url": "https://www.adobe.com/legal/terms.html", "type": "web"},
        {"name": "Oracle", "url": "https://www.oracle.com/legal/terms.html", "type": "web"},
        {"name": "IBM", "url": "https://www.ibm.com/us-en/terms", "type": "web"},
    ],

    "ecommerce": [
        # Marketplaces (15)
        {"name": "Amazon", "url": "https://www.amazon.com/gp/help/customer/display.html?nodeId=508088", "type": "web"},
        {"name": "eBay", "url": "https://www.ebay.com/help/policies/member-behaviour-policies/user-agreement?id=4259", "type": "web"},
        {"name": "Etsy", "url": "https://www.etsy.com/legal/terms-of-use", "type": "web"},
        {"name": "Walmart", "url": "https://www.walmart.com/help/article/walmart-com-terms-of-use/3b3c4ce0e98f4ef5a93ef5fb2d983a2d", "type": "web"},
        {"name": "Target", "url": "https://www.target.com/c/terms-conditions/-/N-4sr7l", "type": "web"},
        {"name": "BestBuy", "url": "https://www.bestbuy.com/site/help-topics/terms-and-conditions/pcmcat204400050067.c", "type": "web"},
        {"name": "Wayfair", "url": "https://www.wayfair.com/customerservice/general_info.php#terms", "type": "web"},
        {"name": "Shopify", "url": "https://www.shopify.com/legal/terms", "type": "web"},
        {"name": "AliExpress", "url": "https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202204151511_54992.html", "type": "web"},
        {"name": "Wish", "url": "https://www.wish.com/terms", "type": "web"},
        {"name": "Overstock", "url": "https://www.overstock.com/terms-of-use", "type": "web"},
        {"name": "Newegg", "url": "https://kb.newegg.com/knowledge-base/terms-and-conditions/", "type": "web"},
        {"name": "Rakuten", "url": "https://www.rakuten.com/help/article/terms-and-conditions-360002101388", "type": "web"},
        {"name": "Mercari", "url": "https://www.mercari.com/us/terms-of-service/", "type": "web"},
        {"name": "Poshmark", "url": "https://poshmark.com/terms", "type": "web"},

        # Fashion & Retail (10)
        {"name": "Nike", "url": "https://www.nike.com/help/a/terms-of-use", "type": "web"},
        {"name": "Adidas", "url": "https://www.adidas.com/us/help/terms-and-conditions", "type": "web"},
        {"name": "Zara", "url": "https://www.zara.com/us/en/help-center/legal-notice", "type": "web"},
        {"name": "H&M", "url": "https://www2.hm.com/en_us/customer-service/legal-and-privacy.html", "type": "web"},
        {"name": "Gap", "url": "https://www.gap.com/customerService/info.do?cid=2070&cs=legal&mlink=footer,0,cs_9", "type": "web"},
        {"name": "Macy's", "url": "https://www.macys.com/service/terms-and-conditions", "type": "web"},
        {"name": "Nordstrom", "url": "https://www.nordstrom.com/browse/customer-service/policy/terms-of-use", "type": "web"},
        {"name": "ASOS", "url": "https://www.asos.com/terms-and-conditions/", "type": "web"},
        {"name": "Uniqlo", "url": "https://www.uniqlo.com/us/en/terms-of-use", "type": "web"},
        {"name": "Forever21", "url": "https://www.forever21.com/us/2000092118.html", "type": "web"},
    ],

    "saas": [
        # Productivity & Collaboration (20)
        {"name": "Slack", "url": "https://slack.com/terms-of-service", "type": "web"},
        {"name": "Notion", "url": "https://www.notion.so/Terms-and-Privacy-28ffdd083dc3473e9c2da6ec011b58ac", "type": "web"},
        {"name": "Asana", "url": "https://asana.com/terms", "type": "web"},
        {"name": "Trello", "url": "https://www.atlassian.com/legal/cloud-terms-of-service", "type": "web"},
        {"name": "Monday", "url": "https://monday.com/l/terms/terms-of-service/", "type": "web"},
        {"name": "ClickUp", "url": "https://clickup.com/terms", "type": "web"},
        {"name": "Airtable", "url": "https://www.airtable.com/tos", "type": "web"},
        {"name": "Basecamp", "url": "https://basecamp.com/about/policies/terms", "type": "web"},
        {"name": "Jira", "url": "https://www.atlassian.com/legal/cloud-terms-of-service", "type": "web"},
        {"name": "Confluence", "url": "https://www.atlassian.com/legal/cloud-terms-of-service", "type": "web"},
        {"name": "Miro", "url": "https://miro.com/legal/terms-of-service/", "type": "web"},
        {"name": "Figma", "url": "https://www.figma.com/tos/", "type": "web"},
        {"name": "Canva", "url": "https://www.canva.com/policies/terms-of-use/", "type": "web"},
        {"name": "DocuSign", "url": "https://www.docusign.com/company/terms-and-conditions/web", "type": "web"},
        {"name": "Salesforce", "url": "https://www.salesforce.com/company/legal/agreements/", "type": "web"},
        {"name": "HubSpot", "url": "https://legal.hubspot.com/terms-of-service", "type": "web"},
        {"name": "Mailchimp", "url": "https://www.intuit.com/legal/terms-of-service/mailchimp/", "type": "web"},
        {"name": "Zapier", "url": "https://zapier.com/legal/terms-of-service", "type": "web"},
        {"name": "Intercom", "url": "https://www.intercom.com/legal/terms-and-policies", "type": "web"},
        {"name": "Zendesk", "url": "https://www.zendesk.com/company/agreements-and-terms/master-subscription-agreement/", "type": "web"},
    ],

    "finance": [
        # Payment Platforms (15)
        {"name": "PayPal", "url": "https://www.paypal.com/us/legalhub/useragreement-full", "type": "web"},
        {"name": "Stripe", "url": "https://stripe.com/legal/ssa", "type": "web"},
        {"name": "Square", "url": "https://squareup.com/us/en/legal/general/ua", "type": "web"},
        {"name": "Venmo", "url": "https://venmo.com/legal/us-user-agreement/", "type": "web"},
        {"name": "Cash_App", "url": "https://cash.app/legal/us/en-us/tos", "type": "web"},
        {"name": "Zelle", "url": "https://www.zellepay.com/user-service-agreement", "type": "web"},
        {"name": "Wise", "url": "https://wise.com/us/legal/terms-of-use", "type": "web"},
        {"name": "Revolut", "url": "https://www.revolut.com/legal/terms", "type": "web"},
        {"name": "Chime", "url": "https://www.chime.com/policies/deposit-account-agreement/", "type": "web"},
        {"name": "Robinhood", "url": "https://robinhood.com/us/en/support/articles/customer-agreement/", "type": "web"},
        {"name": "Coinbase", "url": "https://www.coinbase.com/legal/user_agreement/united_states", "type": "web"},
        {"name": "Binance", "url": "https://www.binance.com/en/terms", "type": "web"},
        {"name": "Kraken", "url": "https://www.kraken.com/legal/terms", "type": "web"},
        {"name": "Gemini", "url": "https://www.gemini.com/legal/user-agreement", "type": "web"},
        {"name": "Plaid", "url": "https://plaid.com/legal/", "type": "web"},
    ],

    "general": [
        # Services & Platforms (25)
        {"name": "Uber", "url": "https://www.uber.com/legal/en/document/?name=general-terms-of-use&country=united-states", "type": "web"},
        {"name": "Lyft", "url": "https://www.lyft.com/terms", "type": "web"},
        {"name": "Airbnb", "url": "https://www.airbnb.com/help/article/2908", "type": "web"},
        {"name": "Booking", "url": "https://www.booking.com/content/terms.html", "type": "web"},
        {"name": "Expedia", "url": "https://www.expedia.com/p/support/terms-of-use", "type": "web"},
        {"name": "Hotels", "url": "https://www.hotels.com/customer_care/terms_conditions.html", "type": "web"},
        {"name": "DoorDash", "url": "https://www.doordash.com/terms/", "type": "web"},
        {"name": "UberEats", "url": "https://www.ubereats.com/legal", "type": "web"},
        {"name": "GrubHub", "url": "https://www.grubhub.com/legal/terms-of-use", "type": "web"},
        {"name": "Instacart", "url": "https://www.instacart.com/terms", "type": "web"},
        {"name": "Postmates", "url": "https://postmates.com/terms", "type": "web"},
        {"name": "Netflix", "url": "https://help.netflix.com/legal/termsofuse", "type": "web"},
        {"name": "Spotify", "url": "https://www.spotify.com/us/legal/end-user-agreement/", "type": "web"},
        {"name": "Hulu", "url": "https://www.hulu.com/terms", "type": "web"},
        {"name": "Disney_Plus", "url": "https://www.disneyplus.com/legal/subscriber-agreement", "type": "web"},
        {"name": "HBO_Max", "url": "https://www.max.com/terms-of-use", "type": "web"},
        {"name": "Twitch", "url": "https://www.twitch.tv/p/legal/terms-of-service/", "type": "web"},
        {"name": "Steam", "url": "https://store.steampowered.com/subscriber_agreement/", "type": "web"},
        {"name": "PlayStation", "url": "https://www.playstation.com/en-us/legal/terms-of-use/", "type": "web"},
        {"name": "Xbox", "url": "https://www.xbox.com/en-US/legal/termsofuse", "type": "web"},
        {"name": "Nintendo", "url": "https://www.nintendo.com/us/terms-of-use/", "type": "web"},
        {"name": "OpenAI", "url": "https://openai.com/policies/terms-of-use", "type": "web"},
        {"name": "Anthropic", "url": "https://www.anthropic.com/legal/consumer-terms", "type": "web"},
        {"name": "Yelp", "url": "https://www.yelp.com/tos", "type": "web"},
        {"name": "Tripadvisor", "url": "https://www.tripadvisor.com/pages/terms.html", "type": "web"},
    ],
}


# ============================================================================
# COLLECTION FUNCTIONS
# ============================================================================

async def download_pdf_direct(url: str, output_path: Path) -> bool:
    """
    Download PDF file directly from URL.

    Args:
        url: Direct PDF URL
        output_path: Where to save the PDF

    Returns:
        True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            logger.info(f"Downloading PDF: {url}")
            response = await client.get(url)
            response.raise_for_status()

            # Verify it's a PDF
            content_type = response.headers.get("content-type", "")
            if "pdf" not in content_type.lower() and not url.endswith(".pdf"):
                logger.warning(f"URL may not be a PDF: {content_type}")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)

            logger.info(f"✓ Downloaded: {output_path.name}")
            return True

    except Exception as e:
        logger.error(f"✗ Failed to download {url}: {e}")
        return False


async def convert_web_to_pdf(url: str, output_path: Path, timeout: int = 30000) -> bool:
    """
    Convert web page to PDF using Playwright headless browser.

    Args:
        url: Web page URL
        output_path: Where to save the PDF
        timeout: Page load timeout in milliseconds

    Returns:
        True if successful, False otherwise
    """
    try:
        async with async_playwright() as p:
            logger.info(f"Converting to PDF: {url}")

            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()

            # Navigate to page
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout)
            except Exception as e:
                logger.warning(f"Navigation timeout/error for {url}: {e}")
                # Try to save anyway if page partially loaded

            # Wait a bit for dynamic content
            await asyncio.sleep(2)

            # Save as PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            await page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"}
            )

            await browser.close()

            # Verify file was created and has content
            if output_path.exists() and output_path.stat().st_size > 1000:
                logger.info(f"✓ Converted: {output_path.name} ({output_path.stat().st_size // 1024}KB)")
                return True
            else:
                logger.error(f"✗ PDF file too small or empty: {output_path.name}")
                return False

    except Exception as e:
        logger.error(f"✗ Failed to convert {url}: {e}")
        return False


async def collect_document(
    source: Dict,
    category: str,
    output_dir: Path,
    force: bool = False
) -> Optional[Dict]:
    """
    Collect a single T&C document.

    Args:
        source: Source dict with name, url, type
        category: Category name (tech, ecommerce, etc.)
        output_dir: Base output directory
        force: Re-download even if exists

    Returns:
        Metadata dict if successful, None otherwise
    """
    filename = f"{source['name'].lower().replace(' ', '_')}_tos.pdf"
    category_dir = output_dir / category
    output_path = category_dir / filename

    # Skip if already exists (unless force)
    if output_path.exists() and not force:
        logger.info(f"⊙ Skipping (exists): {filename}")
        file_size = output_path.stat().st_size
        return {
            "filename": filename,
            "category": category,
            "company": source['name'],
            "source_url": source['url'],
            "source_type": source['type'],
            "file_size": file_size,
            "collected_at": datetime.now().isoformat(),
            "status": "existing"
        }

    # Collect based on type
    success = False
    if source['type'] == 'pdf':
        success = await download_pdf_direct(source['url'], output_path)
    else:  # web
        success = await convert_web_to_pdf(source['url'], output_path)

    if success and output_path.exists():
        file_size = output_path.stat().st_size
        return {
            "filename": filename,
            "category": category,
            "company": source['name'],
            "source_url": source['url'],
            "source_type": source['type'],
            "file_size": file_size,
            "collected_at": datetime.now().isoformat(),
            "status": "collected"
        }
    else:
        return None


async def collect_corpus(
    output_dir: Path,
    categories: Optional[List[str]] = None,
    force: bool = False,
    rate_limit_delay: float = 2.0
):
    """
    Collect entire baseline corpus.

    Args:
        output_dir: Where to save corpus
        categories: List of categories to collect (None = all)
        force: Re-download existing files
        rate_limit_delay: Seconds to wait between requests
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter categories
    if categories:
        sources = {cat: BASELINE_SOURCES[cat] for cat in categories if cat in BASELINE_SOURCES}
    else:
        sources = BASELINE_SOURCES

    # Calculate totals
    total_sources = sum(len(sources[cat]) for cat in sources)
    logger.info(f"📚 Starting collection of {total_sources} documents across {len(sources)} categories")

    # Collect metadata
    all_metadata = []
    successful = 0
    failed = 0
    skipped = 0

    # Process each category
    for category, category_sources in sources.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"📁 Category: {category.upper()} ({len(category_sources)} sources)")
        logger.info(f"{'='*60}")

        for idx, source in enumerate(category_sources, 1):
            logger.info(f"\n[{idx}/{len(category_sources)}] Processing: {source['name']}")

            metadata = await collect_document(source, category, output_dir, force)

            if metadata:
                all_metadata.append(metadata)
                if metadata['status'] == 'collected':
                    successful += 1
                else:
                    skipped += 1
            else:
                failed += 1

            # Rate limiting (be respectful to servers)
            if idx < len(category_sources):
                await asyncio.sleep(rate_limit_delay)

    # Save metadata
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(all_metadata, indent=2))

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("📊 COLLECTION SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Successful:     {successful}")
    logger.info(f"⊙ Already Exists: {skipped}")
    logger.info(f"✗ Failed:         {failed}")
    logger.info(f"📁 Total:         {len(all_metadata)}")
    logger.info(f"\n💾 Metadata saved to: {metadata_path}")

    # Category breakdown
    logger.info(f"\n📈 By Category:")
    for category in sources.keys():
        cat_count = sum(1 for m in all_metadata if m['category'] == category)
        logger.info(f"   {category:12s}: {cat_count:3d} documents")

    return all_metadata


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Collect baseline T&C corpus for anomaly detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Collect all categories
    python collect_baseline_corpus.py --output data/baseline_corpus

    # Collect specific categories
    python collect_baseline_corpus.py --category tech saas --output data/baseline_corpus

    # Force re-download existing files
    python collect_baseline_corpus.py --force --output data/baseline_corpus

    # Faster collection (less polite, might get rate limited)
    python collect_baseline_corpus.py --delay 0.5
        """
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/baseline_corpus"),
        help="Output directory (default: data/baseline_corpus)"
    )

    parser.add_argument(
        "--category",
        nargs="+",
        choices=list(BASELINE_SOURCES.keys()),
        help="Specific categories to collect (default: all)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download existing files"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)"
    )

    args = parser.parse_args()

    # Run collection
    try:
        asyncio.run(collect_corpus(
            output_dir=args.output,
            categories=args.category,
            force=args.force,
            rate_limit_delay=args.delay
        ))

        logger.info("\n✅ Collection complete!")
        logger.info(f"📁 Documents saved to: {args.output}")
        logger.info("\n🚀 Next steps:")
        logger.info("   1. Validate corpus: python scripts/validate_corpus.py")
        logger.info("   2. Index to Pinecone: python scripts/index_baseline_corpus.py")

    except KeyboardInterrupt:
        logger.info("\n⚠️  Collection interrupted by user")
        logger.info("   Run again with same arguments to resume")
    except Exception as e:
        logger.error(f"\n❌ Collection failed: {e}", exc_info=True)
        exit(1)


if __name__ == "__main__":
    main()
