import json
from typing import List, Optional

import waveassist
from pydantic import BaseModel


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

max_tokens = 4000


class PAAQuery(BaseModel):
    question: str
    source_url: Optional[str] = None
    context_snippet: Optional[str] = None


class RedditQuestion(BaseModel):
    question: str
    subreddit: Optional[str] = None
    url: Optional[str] = None
    upvotes: Optional[int] = None
    context_snippet: Optional[str] = None


class ContentOpportunity(BaseModel):
    topic: str
    description: str
    suggested_format: Optional[str] = None
    priority: Optional[str] = None


class PAAOpportunitiesResult(BaseModel):
    google_paa_queries: List[PAAQuery]
    reddit_questions: List[RedditQuestion]
    content_opportunities: List[ContentOpportunity]
    search_intent_analysis: List[str]


print("WaveContent: Starting People Also Ask & question-opportunity analysis...")

try:
    website_content = waveassist.fetch_data("website_content", default={})
    if not isinstance(website_content, dict):
        website_content = {}
    if not website_content:
        raise ValueError(
            "website_content is required for people_also_ask_opportunities but was not found."
        )

    website_url = website_content.get("url")
    pages = website_content.get("pages") or []

    # Build a lightweight context: up to 5 key pages with title + meta description
    primary_pages_context = []
    for page in pages[:5]:
        primary_pages_context.append(
            {
                "url": page.get("url"),
                "title": page.get("title"),
                "meta_description": page.get("meta_description"),
            }
        )

    primary_pages_context_json = json.dumps(primary_pages_context, default=str)

    model_name = "perplexity/sonar"

    prompt = f"""
You are an expert content strategist and SEO/search-intent analyst.

Customer website:
- url: {website_url}

Primary website pages (for context):
{primary_pages_context_json}

Your job:
1. Use web search to discover **Google "People Also Ask" (PAA) questions** and closely related queries
   that are highly relevant to this website's industry, audience, and offerings.
2. Use **Reddit** (and similar Q&A/community sites if helpful) to find real user questions and
   discussion threads that reflect genuine pain points, objections, and information needs.
3. From all of these questions, identify **concrete content opportunities** for the customer:
   - New or refreshed blog posts, guides, FAQs, comparison pages, how-to content, etc.
4. Analyze the **underlying search intent** patterns:
   - What users are truly trying to accomplish
   - Where they feel confused or underserved
   - How this maps to the customer's current content and potential content strategy.

You must return a single JSON object with these exact keys:
- google_paa_queries: list[object] — each item representing a high-signal PAA or closely related query.
  Each object must include:
  - question: string — the exact or near-exact question text.
  - source_url: string or null — a representative URL where this PAA or query appears (Google result or target page).
  - context_snippet: string or null — short snippet explaining what this question is about or where it appears.

- reddit_questions: list[object] — each item representing a real user question from Reddit (or similar communities).
  Each object must include:
  - question: string — the core user question in natural language.
  - subreddit: string or null — subreddit or community name (if applicable).
  - url: string or null — direct URL to the thread or discussion.
  - upvotes: integer or null — approximate upvote/score if visible; otherwise null.
  - context_snippet: string or null — 1–2 sentence summary of the situation or context from the thread.

- content_opportunities: list[object] — concrete content ideas grounded in the questions you found.
  Each object must include:
  - topic: string — short label/title for the content piece.
  - description: string — 2–4 sentence description of what the content should cover and why it matters.
  - suggested_format: string or null — e.g., "blog_post", "guide", "FAQ page", "comparison page", "checklist", etc.
  - priority: string or null — e.g., "high", "medium", "low" based on demand, competition, and strategic value.

- search_intent_analysis: list[string] — a list of concise, standalone insight sentences about search
  intent patterns and clusters. Where possible, each string should also include an approximate time
  context (e.g. "last 30 days", "Q4 2024", "since 2023") inline in the text so you can tell when
  this pattern is most evident in search results and discussions.

Guidelines:
- Anchor findings in **real** queries and discussions using web search and community search.
- Avoid generic, made-up questions; prefer realistic phrasing you observe in search results and threads.
- Prefer quality and diversity of questions over sheer quantity.
- If data for a channel (e.g., Reddit) is sparse, say so but still return well-structured objects.
"""

    try:
        result = waveassist.call_llm(
            model=model_name,
            prompt=prompt,
            response_model=PAAOpportunitiesResult,
            max_tokens=max_tokens,
            extra_body={"web_search_options": {"search_context_size": "high"}},
        )

        if result:
            paa_opportunities = result.model_dump()
            waveassist.store_data("paa_opportunities", paa_opportunities, data_type="json")
            print(
                "WaveContent: People Also Ask opportunities stored as 'paa_opportunities'."
            )
        else:
            print("WaveContent: No result from LLM when generating People Also Ask opportunities.")
            waveassist.store_data("paa_opportunities", {}, data_type="json")

    except Exception as e:
        print(f"WaveContent: Error while generating People Also Ask opportunities: {e}")
        waveassist.store_data("paa_opportunities", {}, data_type="json")
        raise

except Exception as e:
    print(f"WaveContent: Error in people_also_ask_opportunities node: {e}")
    waveassist.store_data("paa_opportunities", {}, data_type="json")
    raise


