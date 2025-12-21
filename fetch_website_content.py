import asyncio
from typing import Any, Dict, List

import crawlee
import waveassist
from crawlee.crawlers import BeautifulSoupCrawler, BeautifulSoupCrawlingContext
PAGES_TO_EXTRACT = 50

waveassist.init(check_credits=True)


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop → safe to block
        return asyncio.run(coro)
    else:
        # Running loop → schedule task, and return the task
        return loop.create_task(coro)


def _extract_page_data(context: BeautifulSoupCrawlingContext) -> Dict[str, Any]:
    soup = context.soup
    url = context.request.url

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # Meta description
    description_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = (
        description_tag.get("content", "").strip() if description_tag else ""
    )

    # Headings
    headings: List[Dict[str, str]] = []
    for level in ["h1", "h2", "h3"]:
        for tag in soup.find_all(level):
            text = tag.get_text(strip=True)
            if text:
                headings.append({"level": level, "text": text})

    # Links
    links: List[Dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        links.append({"text": text, "href": href})

    # Social links (Twitter/X, YouTube, LinkedIn, etc.)
    social_domains = {
        "twitter.com": "twitter",
        "x.com": "twitter",
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "linkedin.com": "linkedin",
        "facebook.com": "facebook",
        "fb.com": "facebook",
        "instagram.com": "instagram",
        "tiktok.com": "tiktok",
        "github.com": "github",
    }

    social_links: List[Dict[str, str]] = []
    for link in links:
        href_lower = (link.get("href") or "").lower()
        for domain, platform in social_domains.items():
            if domain in href_lower:
                social_links.append(
                    {
                        "platform": platform,
                        "url": link.get("href"),
                        "text": link.get("text"),
                    }
                )
                break

    # Basic content summary: first few paragraphs concatenated
    paragraphs: List[str] = [p.get_text(strip=True) for p in soup.find_all("p")]
    content_summary = " ".join(paragraphs[:5])

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "links": links,
        "social_links": social_links,
        "text_snippet": content_summary,
        # Full page dump as HTML string
        "full_html": str(soup),
    }


async def crawl_site(start_url: str) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    crawler = BeautifulSoupCrawler(
        max_requests_per_crawl=PAGES_TO_EXTRACT  # homepage + up to 19 linked pages
    )

    @crawler.router.default_handler
    async def handle_page(context: BeautifulSoupCrawlingContext) -> None:  # type: ignore[override]
        page_data = _extract_page_data(context)
        pages.append(page_data)

        # Enqueue more links from this page, limited to same-domain using Crawlee strategy
        await context.enqueue_links(strategy="same-domain")

    await crawler.run([start_url])
    return pages



##Primary code here
print("WaveContent: Starting website content fetch with Crawlee HTTP crawler...")
website_url = waveassist.fetch_data("website_url")
if not website_url:
    raise ValueError("website_url is required but was not provided.")

try:
    pages_raw = run_async(crawl_site(website_url))

    if not pages_raw:
        raise RuntimeError("No pages were crawled from the website.")

    # Build website_pages array with lightweight metadata + page_id
    website_pages: List[Dict[str, Any]] = []
    page_ids: List[str] = []

    for idx, page in enumerate(pages_raw):
        page_id = f"page_{idx}"
        page_ids.append(page_id)

        # Store full page data (including full_html) in a separate variable
        waveassist.store_data(f"website_{page_id}_data", page)

        # Summary entry for website_pages array (exclude full_html to keep it lighter)
        website_pages.append(
            {
                "page_id": page_id,
                "url": page.get("url"),
                "title": page.get("title"),
                "meta_description": page.get("meta_description"),
                "headings": page.get("headings"),
                "links": page.get("links"),
                "text_snippet": page.get("text_snippet"),
            }
        )

    # Use same 20 pages as "key" pages for now
    key_pages = website_pages
    key_page_urls = [p["url"] for p in key_pages]

    # Assign simple IDs to pages and store each page separately
    # (page_ids already built above; each page stored as website_page_{id}_data)

    website_content = {
        "url": website_url,
        # Lightweight array of page summaries; full dumps are in website_page_{id}_data
        "pages": website_pages,
        "page_ids": page_ids,
        "sitemap": None,
        "main_pages": key_page_urls,
    }

    # Store a single clean variable with all website content
    waveassist.store_data("website_content", website_content)

    print("WaveContent: Website content crawled and stored successfully.")

except Exception as e:
    print(f"WaveContent: Error while fetching website content with Crawlee: {e}")
    raise



