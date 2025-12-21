import json
from typing import List, Optional

import waveassist
from pydantic import BaseModel


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

max_tokens = 5000


class PageRef(BaseModel):
    page_id: str
    url: str

class SegregatedWebsiteContentResult(BaseModel):
    top_primary_pages: List[PageRef]
    blog_article_pages: List[PageRef]
    product_pages: List[PageRef]
    documentation_pages: List[PageRef]
    legal_or_policy_pages: List[PageRef]
    other_pages: List[PageRef]

print("WaveContent: Starting website content segregation...")

website_content = waveassist.fetch_data("website_content")

if not website_content:
    raise ValueError(
        "website_content is required for segregrate_website_content node but was not found."
    )

pages = website_content.get("pages") or []
if not pages:
    raise ValueError(
        "website_content.pages is empty or missing; cannot segregate website content."
    )

# To keep prompt size manageable, only include lightweight page summaries
pages_for_prompt = []
for page in pages:
    pages_for_prompt.append(
        {
            "page_id": page.get("page_id"),
            "url": page.get("url"),
            "title": page.get("title"),
            "meta_description": page.get("meta_description"),
            "headings": page.get("headings"),
            "text_snippet": page.get("text_snippet"),
        }
    )

# If there are more than 100 pages for some reason, truncate to first 100
pages_for_prompt = pages_for_prompt[:100]

pages_json = json.dumps(pages_for_prompt, default=str)

model_name = "deepseek/deepseek-chat-v3.1"

prompt = f"""
You are an expert content strategist and information architect.
You are given a list of website pages (up to 100) with lightweight metadata.

Each page has:
- page_id
- url
- title
- meta_description
- headings (h1–h3)
- text_snippet (first few paragraphs)

Your job is to **segment the site into clear content blocks** that are useful for downstream content analysis.

1. Identify the **Top 5 Primary Pages** for content analysis
   - These are usually: home, about, pricing, product/solutions overview, main landing pages, etc.
   - Choose **up to 5** pages that best represent the core value proposition and main navigation flows.

2. Identify **Blog / Article pages**
   - Any pages that look like articles, posts, case studies, or resources.

3. Identify other useful sections if present, for example:
   - Product / feature pages
   - Documentation / help / FAQ
   - Legal / policy pages (privacy, terms, cookie policy, etc.)
   - Any other logical groupings that would help analyze the site structure.

4. For each group, always reference pages **by page_id, url**.

5. If some groups do not exist for this site, return an **empty list** for that group.

Return your answer **strictly following** the schema.

One page can only be in one group. Do not assign the same page to multiple groups.

Here is the website pages data (JSON):
{pages_json}


"""

try:
    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=SegregatedWebsiteContentResult,
        max_tokens=max_tokens,
    )

    if result:
        segregated = result.model_dump(by_alias=True)
        waveassist.store_data("segregated_website_content", segregated)
        print("WaveContent: Segregated website content stored as 'segregated_website_content'.")
    else:
        # Store a minimal error object so downstream nodes can fail gracefully if needed
        waveassist.store_data(
            "segregated_website_content",
            {"error": "segmentation_failed_or_no_result"},
        )
        print("WaveContent: No result from LLM when segregating website content.")

except Exception as e:
    print(f"WaveContent: Error while segregating website content: {e}")
    waveassist.store_data(
        "segregated_website_content",
        {"error": f"segmentation_error: {e}"},
    )
    raise


