import json
from typing import List, Optional

import waveassist
from pydantic import BaseModel, Field


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

max_tokens = 5000


class RecentUpdate(BaseModel):
    title: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    content_type: Optional[str] = None
    summary: Optional[str] = None


class CompetitorAnalysisItem(BaseModel):
    url: str
    name: Optional[str] = None
    recent_updates: List[RecentUpdate] = Field(default_factory=list)
    content_strategy: str = ""
    trends: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)


class CompetitorAnalysisResult(BaseModel):
    competitor_data: List[CompetitorAnalysisItem]


print("WaveContent: Starting competitor analysis...")

# Fetch required data
competitor_data = waveassist.fetch_data("competitor_data") or []
website_content = waveassist.fetch_data("website_content")

customer_url = website_content.get("url") if website_content else None
customer_pages_summary = []
if website_content and website_content.get("pages"):
    # Include lightweight summaries of customer pages for context
    for page in website_content.get("pages", [])[:5]:  # Limit to first 5 pages
        customer_pages_summary.append(
            {
                "url": page.get("url"),
                "title": page.get("title"),
                "meta_description": page.get("meta_description"),
            }
        )

customer_context = {
    "url": customer_url,
    "pages": customer_pages_summary,
}

competitor_data_json = json.dumps(competitor_data, default=str)
customer_context_json = json.dumps(customer_context, default=str)

model_name = "perplexity/sonar"

prompt = f"""
You are an expert **content strategist** and competitive intelligence analyst.
Your job is to analyze competitor websites and extract insights specifically about their **content**, not their product features.

The customer's website context (for comparison, limited to first 5 pages):
{customer_context_json}

The list of competitors to analyze:
{competitor_data_json}

You must return a JSON object with a single top-level key:
- competitor_data: a list of objects, one per competitor.

Each item inside competitor_data must have this exact schema:
- url: string — the competitor's website URL.
- name: string or null — the competitor's name/brand (if available from the input data or search).
- recent_updates: list of objects — recent **content** updates, publications, blog posts, articles, or other new content pieces. Maximum 10 items.
  Each object must have:
  - title: string — title or short label of the content.
  - url: string or null — canonical URL to that content, if available.
  - published_at: string or null — approximate publication date (ISO format preferred, or human-readable if not available).
  - content_type: string or null — e.g. "blog_post", "case_study", "docs", "ebook", "video", etc.
  - summary: string or null — 1–2 sentence summary of what that content piece covers.
- content_strategy: string — 2–4 sentences summarizing their **content strategy** and publishing approach.
- trends: list of strings — 3–5 **content trends and patterns** you observe in what they publish.
- strengths: list of strings — 3–5 **strengths of their content only** (writing quality, depth, clarity, topical coverage, SEO, formats, cadence, etc.). Do **not** describe product or feature strengths here.

For each competitor, you must:

1. **Recent Updates (recent_updates)**:
   - Use web search to find recent content pieces (blog posts, articles, case studies, videos, docs, etc.) from roughly the last few months.
   - Each item should point to a specific piece of content (title/topic, type, and ideally URL), not a generic statement.

2. **Content Strategy (content_strategy)**:
   - Summarize the competitor's overall **content strategy**, not product positioning.
   - Cover main content types, topics/themes, and how they structure and distribute content (e.g., SEO blogs, thought leadership, docs-heavy, community-focused).

3. **Trends (trends)**:
   - Capture clear **content trends and patterns**: current focus topics, preferred formats, and any noticeable shifts over time.

4. **Strengths (strengths)**:
   - Describe **strengths of their content only**, ignoring product features and pricing.
   - Focus on things like depth, clarity, SEO targeting, narrative quality, use of examples/case studies, media richness, and publishing cadence.

Use web search to gather current information about each competitor's website, recent publications, and content strategy.

Return your answer **strictly following the schema** described above.
"""

try:
    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=CompetitorAnalysisResult,
        max_tokens=max_tokens,
        extra_body={"web_search_options": {"search_context_size": "high"}},
    )

    if result:
        analysis_data = result.model_dump(by_alias=True)
        waveassist.store_data("competitor_analysis", analysis_data)
        print(
            f"WaveContent: Competitor analysis stored as 'competitor_analysis' for {len(analysis_data.get('competitor_data', []))} competitors."
        )
    else:
        print("WaveContent: No result from LLM when analyzing competitors.")
        waveassist.store_data(
            "competitor_analysis",
            {"competitor_data": []},
        )

except Exception as e:
    print(f"WaveContent: Error while analyzing competitors: {e}")
    waveassist.store_data(
        "competitor_analysis",
        {"competitor_data": []},
    )
    raise

