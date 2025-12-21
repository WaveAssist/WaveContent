import json
from typing import Dict, List, Optional

import waveassist
from pydantic import BaseModel


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

max_tokens = 3000


class CompetitorData(BaseModel):
    url: str
    name: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    similarity_score: Optional[float] = None

class DiscoverCompetitorsResult(BaseModel):
    competitor_data: List[CompetitorData]

print("WaveContent: Starting competitor discovery...")

website_url = waveassist.fetch_data("website_url")
website_content = waveassist.fetch_data("website_content")
user_competitors: List[str] = waveassist.fetch_data("competitor_websites_list") or []
if len(user_competitors) >= 4:
    raise Exception("Competetion provided by user, no need to process this node")

pages = website_content.get("pages") or []

# Heuristic: use page whose URL matches website_url; fall back to the first page (page_0)
home_page = None
for page in pages:
    if str(page.get("url", "")).rstrip("/") == str(website_url).rstrip("/"):
        home_page = page
        break

if home_page is None:
    home_page = pages[0]

home_summary = {
    "url": home_page.get("url"),
    "title": home_page.get("title"),
    "meta_description": home_page.get("meta_description"),
}

home_summary_json = json.dumps(home_summary, default=str)
user_competitors_json = json.dumps(user_competitors, default=str)

model_name = "perplexity/sonar"

prompt = f"""
You are an expert in competitive landscape analysis and market research.
Your job is to find the top *5* most relevant competitors for the customer's website.
Only Five max competitors are allowed.


The customer's website (home/primary URL) is:
{home_summary_json}

User-provided competitor websites (if any) are:
{user_competitors_json}

Your tasks:
1. If **no competitors are provided**, use web search to discover the **top 5** realistic, high-signal competitors
   for this business based on its website content, industry, product/service type, and target audience.

2. If competitors **are** provided, validate and enrich them:
   - Add any obviously missing major competitors discovered via search, but keep the final total at **no more than 5**.

3. For each competitor, you must determine:
   - url: Canonical website URL (homepage)
   - name: Brand or company name
   - description: Short description of why they are a competitor
   - reason: Reason for why they are a competitor
   - similarity_score: A rough similarity score from 0.0–1.0 (1.0 = extremely similar direct competitor)

4. Only include **true competitors**:
   - Exclude directories, blog posts, agencies just writing about the space, or random mentions.
   - Exclude obviously unrelated businesses.

Return:
- A list `competitor_data` with **at most 5 items**, where each item follows the `CompetitorData` schema.

Return your answer strictly following the schema.
"""

try:
    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=DiscoverCompetitorsResult,
        max_tokens=max_tokens,
        extra_body={"web_search_options": {"search_context_size": "medium"}},
    )

    if result:
        data = result.model_dump(by_alias=True)
        competitor_data = data.get("competitor_data", []) or []
        competitor_data = competitor_data[:5]
        waveassist.store_data("competitor_data", competitor_data)
        print("WaveContent: Competitor data stored as 'competitor_data'.")
    else:
        waveassist.store_data("competitor_data", [])
        print("WaveContent: No result from LLM when discovering competitors.")

except Exception as e:
    print(f"WaveContent: Error while discovering competitors: {e}")
    waveassist.store_data("competitor_data", [])
    raise


