import json
from typing import Any, Dict, List, Optional

import waveassist
from pydantic import BaseModel, Field


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

model_name = "google/gemini-3-flash-preview"
max_tokens = 6000
temperature = 0.4


class LongFormContentIdea(BaseModel):
    title: str
    target_audience: str = ""
    primary_keyword: str = ""
    secondary_keywords: List[str] = Field(default_factory=list)
    search_intent: str = ""
    angle: str = ""
    outline: List[str] = Field(default_factory=list)
    recommended_internal_links: List[str] = Field(default_factory=list)
    recommended_cta: str = ""
    priority: str = ""  # high|medium|low


class ShortFormContentIdea(BaseModel):
    platform: str = ""
    content_type: str = ""  # post|thread|carousel|video|reel|newsletter|etc.
    hook: str = ""
    concept: str = ""  # platform-appropriate concept (esp. for non-X platforms)
    optional_post_text: str = ""  # optional; primarily for X/Twitter-style output
    suggested_hashtags: List[str] = Field(default_factory=list)
    cta: str = ""
    priority: str = ""


class ContentTheme(BaseModel):
    theme: str
    description: str = ""
    why_it_matters: str = ""


class ContentRecommendations(BaseModel):
    long_form_content: List[LongFormContentIdea] = Field(default_factory=list)
    short_form_content: List[ShortFormContentIdea] = Field(default_factory=list)
    content_themes: List[ContentTheme] = Field(default_factory=list)


class ContentGaps(BaseModel):
    missing_topics: List[str] = Field(default_factory=list)
    content_opportunities: List[str] = Field(default_factory=list)
    competitive_advantages: List[str] = Field(default_factory=list)
    priority_gaps: List[str] = Field(default_factory=list)


class GenerateContentRecommendationsResult(BaseModel):
    content_recommendations: ContentRecommendations
    content_gaps: ContentGaps


print("WaveContent: Starting content recommendations generation...")


def _json_dumps(data: Any) -> str:
    """
    Compact JSON for prompt-inlining (token-efficient for LLMs).
    """
    try:
        return json.dumps(
            data,
            default=str,
            ensure_ascii=False,  # avoid \uXXXX escaping (usually fewer tokens)
            separators=(",", ":"),  # minify (no spaces after separators)
        )
    except Exception:
        return "{}"


try:
    # Core site understanding
    website_content: Dict[str, Any] = waveassist.fetch_data("website_content") or {}
    if not website_content:
        raise ValueError(
            "website_content is required for generate_content_recommendations but was not found."
        )

    segregated_website_content: Dict[str, Any] = (
        waveassist.fetch_data("segregated_website_content") or {}
    )

    # Prior analyses
    competitor_analysis = waveassist.fetch_data("competitor_analysis")
    paa_opportunities = waveassist.fetch_data("paa_opportunities")
    twitter_insights = waveassist.fetch_data("twitter_insights")

    # Build prompt payloads
    website_content_json = _json_dumps(website_content)
    segregated_json = _json_dumps(segregated_website_content)
    competitor_analysis_json = _json_dumps(competitor_analysis)
    paa_json = _json_dumps(paa_opportunities)
    twitter_json = _json_dumps(twitter_insights)

    website_url = website_content.get("url") or ""

    prompt = f"""
You are an expert content strategist.

Goal: generate high-quality content recommendations (long-form + short-form + platform-specific) and identify content gaps vs competitors.

Important constraints:
- Use the site's page structure from `segregated_website_content` to tailor recommendations (what should be a blog post vs product page vs docs vs other).
- Use the full crawled `website_content` (all pages summaries) to avoid recommending topics the site already covers.
- Use competitor insights from `competitor_analysis` to find missing topics and content competitive advantages.
- Use `paa_opportunities` to ground recommendations in real user questions and search intent.
- If `twitter_insights` is present, include it to tailor short-form and social recommendations; if missing, still produce strong ideas.

Important: Keep all the points short and to the point. 

What to produce:
- content_recommendations.long_form_content: 2-5 ideas for new/updated blog/article pages. For each idea, populate:
  - title, target_audience, primary_keyword
  - secondary_keywords (list), search_intent, angle, outline (list; 2-5 bullets)
  - recommended_internal_links (list of strings; pick 2–5 relevant internal pages from `segregated_website_content`. Prefer the format "<page_id> | <url>" when page_id is available.), recommended_cta, priority ("high", "medium", or "low")
- content_recommendations.short_form_content: 2-5 short-form ideas spanning X/Twitter + other platforms (LinkedIn, YouTube, Instagram, YouTube Shorts, etc.). For each idea, populate:
  - platform, content_type (e.g., post, thread, carousel, video, reel, newsletter)
  - hook, concept (platform-appropriate concept and structure notes)
  - optional_post_text (optional; use mainly for X/Twitter-style posts/threads), suggested_hashtags (list; optional), cta, priority ("high", "medium", or "low")
- content_recommendations.content_themes: 2-5 recurring themes. For each theme, populate: theme, description, why_it_matters.
- content_gaps: identify missing topics and priority gaps vs competitors. Populate: (max 2-5 points each, if any)
  - missing_topics (list; 2-5 points)
  - content_opportunities (list; 2-5 points)
  - competitive_advantages (list; 2-5 points)
  - priority_gaps (list; 2-5 points)

Inputs (JSON):

Customer website url:
{website_url}

Site page structure (segregated_website_content):
{segregated_json}

Full crawl summary (website_content):
{website_content_json}

Competitor analysis:
{competitor_analysis_json}

People Also Ask opportunities:
{paa_json}

Twitter insights (optional):
{twitter_json}
"""

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=GenerateContentRecommendationsResult,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    if result:
        data = result.model_dump(by_alias=True)
        waveassist.store_data("content_recommendations", data.get("content_recommendations"))
        waveassist.store_data("content_gaps", data.get("content_gaps"))
        print("WaveContent: Stored 'content_recommendations' and 'content_gaps'.")
    else:
        waveassist.store_data("content_recommendations", None)
        waveassist.store_data("content_gaps", None)
        print("WaveContent: No result from LLM when generating content recommendations.")

except Exception as e:
    print(f"WaveContent: Error while generating content recommendations: {e}")
    waveassist.store_data("content_recommendations", None)
    waveassist.store_data("content_gaps", None)
    raise


