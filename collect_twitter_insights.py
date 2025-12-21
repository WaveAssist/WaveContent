import json
from typing import List, Optional, Dict, Any

import waveassist
from pydantic import BaseModel


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

max_tokens = 4000


class TwitterInsights(BaseModel):
    recent_tweets_analysis: List[str]
    trending_topics: List[str]
    content_performance: List[str]
    audience_insights: List[str]
    content_suggestions: List[str]
    hashtag_analysis: List[str]
    competition_analysis: List[str]


print("WaveContent: Starting Twitter insights collection...")


def _find_twitter_links_from_website_content(
    website_content: Dict[str, Any]
) -> Optional[str]:
    """Scan all stored website page data objects for Twitter/X links."""
    page_ids: List[str] = website_content.get("page_ids") or []
    for page_id in page_ids:
        page_key = f"website_{page_id}_data"
        page_data = waveassist.fetch_data(page_key) or {}
        social_links = page_data.get("social_links") or []
        for link in social_links:
            try:
                platform = (link.get("platform") or "").lower()
                url = link.get("url") or ""
            except AttributeError:
                # Skip malformed link objects
                continue

            if platform == "twitter" and url:
                # Return immediately on the first Twitter/X link found
                return str(url)

    # No Twitter/X link found
    return None


def _build_primary_pages_context(
    website_content: Dict[str, Any],
    segregated_website_content: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build lightweight context for top primary pages."""
    if not website_content:
        return []

    pages = website_content.get("pages") or []
    pages_by_id: Dict[str, Dict[str, Any]] = {
        str(p.get("page_id")): p for p in pages if p.get("page_id") is not None
    }

    primary_context: List[Dict[str, Any]] = []

    if segregated_website_content:
        top_primary_pages = segregated_website_content.get("top_primary_pages") or []
        for ref in top_primary_pages[:5]:
            page_id = str(ref.get("page_id"))
            page = pages_by_id.get(page_id)
            if not page:
                continue
            primary_context.append(
                {
                    "page_id": page.get("page_id"),
                    "url": page.get("url"),
                    "title": page.get("title"),
                    "meta_description": page.get("meta_description"),
                }
            )

    # Fallback: if we didn't find anything via segregation, use up to 3 pages from website_content
    if not primary_context:
        for page in pages[:3]:
            primary_context.append(
                {
                    "page_id": page.get("page_id"),
                    "url": page.get("url"),
                    "title": page.get("title"),
                    "meta_description": page.get("meta_description"),
                }
            )

    return primary_context


try:
    # Core upstream data
    website_content = waveassist.fetch_data("website_content") or {}
    if not website_content:
        raise ValueError(
            "website_content is required for collect_twitter_insights but was not found."
        )

    segregated_website_content = waveassist.fetch_data("segregated_website_content")

    # 1. Determine Twitter handle / presence
    user_twitter_handle: Optional[str] = waveassist.fetch_data("twitter_handle")

    # Only scan website content for a Twitter link if the user has NOT provided a handle
    if not user_twitter_handle:
        user_twitter_handle = _find_twitter_links_from_website_content(
            website_content
        )

    if not user_twitter_handle:
        waveassist.store_data("twitter_insights", None)
        raise Exception('No Twitter handle or Twitter/X links found on the website; skipping collect_twitter_insights node.')

    # 2. Build context for primary pages
    primary_pages_context = _build_primary_pages_context(
        website_content, segregated_website_content
    )

    # 3. Optional competition context from discovered competitors (if available)
    competitor_data = waveassist.fetch_data("competitor_data") or []

    # Prepare JSON snippets for the prompt
    website_url = website_content.get("url")

    primary_pages_context_json = json.dumps(primary_pages_context, default=str)
    competitor_data_json = json.dumps(competitor_data, default=str)
    model_name = "x-ai/grok-4-fast"

    prompt = f"""
You are an expert social media and content strategist focused on Twitter/X.
Primary Twitter handle/url of the customer: {user_twitter_handle}
Other MetaData: 
    Customer website:
    - url: {website_url}

    Primary website pages (for context):
    {primary_pages_context_json}

    Competitor / market context (if available, for context):
    {competitor_data_json}

Your job:
1. Analyze the customer's recent Twitter/X activity and content strategy **for their handle and/or the Twitter URLs discovered from the website**.
2. Use **Twitter/X search** and broader web/Twitter context to understand:
   - What they tweet about
   - How frequently they post (if available)
   - Engagement levels (likes, replies, reposts) (if available)
   - Which topics, formats, and hooks perform best
3. Place this in a **competitive context**:
   - How their Twitter presence compares to close competitors or similar accounts in their niche
   - Where they are stronger or weaker on Twitter compared to peers

You must return a single JSON object with these exact keys:
- recent_tweets_analysis: list[string] — 3–5 short bullet highlights summarizing the most recent weeks/months of tweets (themes, tone, cadence, performance).
- trending_topics: list[string] — 3–5 key themes, topics, or narratives that are most prominent in or around this handle and its niche.
- content_performance: list[string] — 3–5 bullets describing what content performs best vs. worst (formats, hooks, topics, media types, posting times, threads vs. single tweets, etc.).
- audience_insights: list[string] — 3–5 concise bullets about the audience: who seems to follow/engage, what they care about, how they react, and any notable segments. (or whatever is available)
- content_suggestions: list[string] — 5–10 **Twitter-specific content ideas** and experiments this account should try, grounded in the above analysis.
- hashtag_analysis: list[string] — 3–5 bullets on which hashtags work well (or not), how they are used, and recommendations on hashtag strategy.
- competition_analysis: list[string] — 3–5 bullets analyzing how this account compares to relevant competitor or peer accounts on Twitter: strengths, weaknesses, content gaps, and differentiation opportunities. (Use web + Twitter search to infer peer accounts if not explicitly provided.)

Guidelines:
- Use Twitter/X search to ground your analysis in **recent, real activity**. Focus strictly on twitter/X activity. 
- If the handle is missing but only Twitter URLs are known, infer the handle(s) from those URLs and proceed.
"""
    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=TwitterInsights,
        max_tokens=max_tokens,
        extra_body={
            "search_parameters": {
                "mode": "on",
            }
        },
    )

    if result:
        twitter_insights = result.model_dump(by_alias=True)
        waveassist.store_data("twitter_insights", twitter_insights)
        print("WaveContent: Twitter insights stored as 'twitter_insights'.")
    else:
        print("WaveContent: No result from LLM when collecting Twitter insights.")
        waveassist.store_data("twitter_insights", None)

except Exception as e:
    print(f"WaveContent: Error while collecting Twitter insights: {e}")
    waveassist.store_data("twitter_insights", None)

