import json
from typing import Any, Dict, List

import waveassist
from pydantic import BaseModel, Field


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)


model_name = "anthropic/claude-sonnet-4.5"
max_tokens = 2500
temperature = 0.4


class ExecutiveSummary(BaseModel):
    overview: str = ""
    key_findings: List[str] = Field(default_factory=list)
    top_opportunities: List[str] = Field(default_factory=list)


class GenerateSummaryResult(BaseModel):
    executive_summary: ExecutiveSummary


print("WaveContent: Starting executive summary generation...")


def _json_dumps(data: Any) -> str:
    """
    Compact JSON for prompt-inlining (token-efficient for LLMs).
    """
    try:
        return json.dumps(
            data,
            default=str,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except Exception:
        return "{}"

try:
    # Inputs: use derived analysis outputs only (avoid raw website crawl + segregated content)
    website_url = waveassist.fetch_data("website_url") or ""
    primary_content_suggestions = waveassist.fetch_data("primary_content_suggestions") or {}
    seo_report = waveassist.fetch_data("seo_report") or {}
    competitor_analysis = waveassist.fetch_data("competitor_analysis") or {}
    paa_opportunities = waveassist.fetch_data("paa_opportunities") or {}
    twitter_insights = waveassist.fetch_data("twitter_insights") or {}
    content_recommendations = waveassist.fetch_data("content_recommendations") or {}
    content_gaps = waveassist.fetch_data("content_gaps") or {}

    # Pass analysis outputs fully (no trimming/reshaping); exclude raw website crawl + segregated content.
    inputs_payload = {
        "website_url": website_url,
        "primary_content_suggestions": primary_content_suggestions,
        "seo_report": seo_report,
        "competitor_analysis": competitor_analysis,
        "paa_opportunities": paa_opportunities,
        "twitter_insights": twitter_insights,  # optional
        "content_recommendations": content_recommendations,
        "content_gaps": content_gaps,
    }

    prompt = f"""
You are an expert content strategist.

Goal: produce an executive summary to be sent on top of the email report.

Constraints:
- Use ONLY the provided analysis inputs. Do NOT ask/use for more data.
- Keep the output SHORT and skimmable; prioritize the highest-impact insights.
- Write bullets like a senior consultant: specific, concrete, and actionable.
- If Twitter insights are missing, do not mention.

What to produce:
- executive_summary.overview: 1–2 sentences max.
- executive_summary.key_findings: 2–4 short bullets (site content + SEO + audience intent + competitor patterns).
- executive_summary.top_opportunities: 2-4 short bullets (highest ROI actions/ideas across site + content plan).

Inputs (JSON):
{_json_dumps(inputs_payload)}
""".strip()

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=GenerateSummaryResult,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    if result and result.executive_summary:
        executive_summary = result.executive_summary.model_dump(by_alias=True)
        waveassist.store_data("executive_summary", executive_summary)
        print("WaveContent: Stored 'executive_summary'.")
    else:
        fallback = {
            "overview": "Summary could not be generated from the available inputs.",
            "key_findings": [],
            "top_opportunities": [],
        }
        waveassist.store_data("executive_summary", fallback)
        print("WaveContent: No result from LLM when generating summary; stored fallback.")

except Exception as e:
    print(f"WaveContent: Error while generating executive summary: {e}")
    fallback = {
        "overview": "Summary could not be generated due to an internal error.",
        "key_findings": [],
        "top_opportunities": [],
    }
    waveassist.store_data("executive_summary", fallback)
    raise


