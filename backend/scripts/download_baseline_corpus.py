"""
Download baseline T&C corpus from public sources.

This script collects 100+ Terms & Conditions documents from various industries
to build the baseline corpus for anomaly detection.
"""

import asyncio
import os
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Top companies by category
COMPANIES = {
    "streaming": [
        "https://www.spotify.com/us/legal/end-user-agreement/",
        "https://help.netflix.com/legal/termsofuse",
        "https://www.hulu.com/terms",
        "https://www.youtube.com/t/terms",
        "https://www.apple.com/legal/internet-services/itunes/us/terms.html",
        "https://www.disneyplus.com/legal/subscriber-agreement",
        "https://www.hbomax.com/terms-of-use",
        "https://www.amazon.com/gp/help/customer/display.html?nodeId=201909000",
        "https://www.twitch.tv/p/legal/terms-of-service/",
        "https://www.pandora.com/legal",
    ],
    "saas": [
        "https://www.notion.so/Terms-and-Privacy",
        "https://slack.com/terms-of-service",
        "https://zoom.us/terms",
        "https://www.dropbox.com/terms",
        "https://www.atlassian.com/legal/customer-agreement",
        "https://www.salesforce.com/company/legal/agreements/",
        "https://support.google.com/a/answer/2855120",
        "https://www.microsoft.com/en-us/servicesagreement",
        "https://www.adobe.com/legal/terms.html",
        "https://asana.com/terms",
        "https://www.monday.com/terms",
        "https://trello.com/legal",
    ],
    "ecommerce": [
        "https://www.amazon.com/gp/help/customer/display.html?nodeId=508088",
        "https://www.ebay.com/help/policies/member-behaviour-policies/user-agreement",
        "https://www.etsy.com/legal/terms-of-use",
        "https://www.walmart.com/help/article/walmart-com-terms-of-use/3b75080af40340d6bbd596f116fae5a0",
        "https://www.target.com/c/terms-conditions/-/N-4sr7l",
        "https://www.bestbuy.com/site/help-topics/terms-and-conditions/pcmcat204400050067.c",
        "https://www.shopify.com/legal/terms",
        "https://www.wayfair.com/customerservice/general_info.php#terms",
    ],
    "social": [
        "https://www.facebook.com/legal/terms",
        "https://twitter.com/en/tos",
        "https://www.instagram.com/legal/terms/",
        "https://www.tiktok.com/legal/terms-of-service",
        "https://www.reddit.com/policies/user-agreement",
        "https://www.linkedin.com/legal/user-agreement",
        "https://www.snapchat.com/legal/terms-of-service",
        "https://www.pinterest.com/about/terms/",
        "https://discord.com/terms",
    ],
    "cloud": [
        "https://aws.amazon.com/agreement/",
        "https://cloud.google.com/terms",
        "https://azure.microsoft.com/en-us/support/legal/",
        "https://www.heroku.com/policy/tos",
        "https://www.digitalocean.com/legal/terms-of-service-agreement",
        "https://www.linode.com/legal-tos/",
    ],
    "finance": [
        "https://www.paypal.com/us/webapps/mpp/ua/useragreement-full",
        "https://stripe.com/legal/ssa",
        "https://squareup.com/us/en/legal/general/ua",
        "https://venmo.com/legal/us-user-agreement/",
        "https://cash.app/legal/us/en-us/tos",
        "https://wise.com/us/legal/terms-of-use",
    ],
    "gaming": [
        "https://www.ea.com/legal/user-agreement",
        "https://www.epicgames.com/site/en-US/tos",
        "https://store.steampowered.com/subscriber_agreement/",
        "https://www.playstation.com/en-us/legal/terms-of-use/",
        "https://www.xbox.com/en-US/legal/termsofuse",
        "https://www.nintendo.com/terms-of-use/",
    ],
    "productivity": [
        "https://www.evernote.com/legal/tos",
        "https://1password.com/legal/terms-of-service/",
        "https://www.lastpass.com/legal-center/terms-of-service",
        "https://www.grammarly.com/terms-of-service",
        "https://www.canva.com/policies/terms-of-use/",
    ],
    "travel": [
        "https://www.airbnb.com/help/article/2908",
        "https://www.uber.com/legal/en/document/?name=general-terms-of-use",
        "https://www.lyft.com/terms",
        "https://www.expedia.com/p/support/terms-of-use",
        "https://www.booking.com/content/terms.html",
    ],
    "food": [
        "https://www.doordash.com/terms/",
        "https://www.ubereats.com/legal",
        "https://www.grubhub.com/legal/terms-of-use",
        "https://www.instacart.com/terms",
    ],
}

BASE_PATH = Path("/Users/akhil/Desktop/Project T&C/data/baseline_corpus")


async def download_html_as_text(url: str, filename: str):
    """Download HTML T&C and save as text."""
    try:
        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True, verify=False
        ) as client:
            # Add headers to avoid bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Parse HTML and extract text
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            text = soup.get_text()

            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            # Only save if substantial content
            if len(text) < 500:
                logger.warning(
                    f"⚠ Skipping {filename}: Too short ({len(text)} chars)"
                )
                return

            # Save
            filepath = BASE_PATH / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)

            logger.info(f"✓ Downloaded: {filename} ({len(text)} chars)")

    except Exception as e:
        logger.error(f"✗ Failed to download {url}: {e}")


async def main():
    """Download all baseline T&C documents."""
    logger.info("Starting baseline corpus collection...")
    logger.info(f"Output directory: {BASE_PATH}")

    tasks = []
    for category, urls in COMPANIES.items():
        category_path = BASE_PATH / category
        category_path.mkdir(parents=True, exist_ok=True)

        for idx, url in enumerate(urls):
            try:
                company_name = url.split("/")[2].replace("www.", "").split(".")[0]
                filename = f"{category}/{company_name}_tos.txt"

                tasks.append(download_html_as_text(url, filename))
            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")

    # Run downloads with rate limiting
    logger.info(f"Downloading {len(tasks)} T&C documents...")
    await asyncio.gather(*tasks)

    logger.info("\n" + "=" * 60)
    logger.info("Baseline corpus collection complete!")

    # Count files by category
    for category in COMPANIES.keys():
        category_path = BASE_PATH / category
        if category_path.exists():
            count = len(list(category_path.glob("*.txt")))
            logger.info(f"  {category}: {count} documents")

    total = sum(1 for _ in BASE_PATH.rglob("*.txt"))
    logger.info(f"\nTotal documents collected: {total}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
