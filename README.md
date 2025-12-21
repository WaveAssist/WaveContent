<h1 align="center">WaveContent: AI website content audit</h1>

<p align="center">
  <a href="https://waveassist.io">
    <img src="https://img.shields.io/badge/Deploy_with-WaveAssist-007F3B" alt="Deploy with WaveAssist" />
  </a>
  <img src="https://img.shields.io/badge/WaveContent-content%20strategy%20report-blue" alt="WaveContent Badge" />
</p>

---

## Overview

WaveContent crawls your website, segments your pages, audits your **top primary pages** for content + SEO + “LLM readability”, benchmarks competitors’ **content strategy**, mines **People Also Ask / Reddit** for real questions, optionally analyzes your **Twitter/X presence**, and then emails a polished report (HTML + PDF).

---

## One-Click Deploy on WaveAssist (Recommended)

<p>
  <a href="https://waveassist.io" target="_blank">
    <img src="https://waveassistapps.s3.us-east-1.amazonaws.com/public/Button.png" alt="Deploy on WaveAssist" width="230" />
  </a>
</p>

Deploy WaveContent instantly on [WaveAssist](https://waveassist.io) — a zero-infrastructure automation platform that handles orchestration, scheduling, secrets, and hosting for you.

> 🔐 You may be prompted to log in or create a free WaveAssist account before continuing.

### How to Use

1. Set **`website_url`** (required).
2. (Optional) Set **`competitor_websites`** as a comma-separated list of competitor homepages.
3. (Optional) Set **`twitter_handle`** (e.g. `@brand`). If omitted, WaveContent tries to find a Twitter/X link from your site.
4. Click **Run & Deploy** (or **Run**).

---

## Inputs

- **Required**

  - **`website_url`**: website homepage to crawl and analyze (e.g. `https://example.com`)

- **Optional**
  - **`competitor_websites`**: comma-separated competitor URLs (e.g. `https://site1.com, https://site2.com`)
  - **`twitter_handle`**: Twitter/X handle or URL (e.g. `@brand` or `https://x.com/brand`)

---

## What You Get (Outputs)

WaveContent sends an email with:

- **Executive summary**: 1–2 sentence overview + key findings + top opportunities.
- **Primary page recommendations**: per-page issues + structure recommendations + copy ideas + quick wins for up to 5 primary pages.
- **SEO & discoverability report**: SEO insights, discoverability signals, technical SEO checks, and LLM readability notes.
- **New content recommendations**: long-form + short-form ideas and recurring themes.
- **Competitor content analysis**: competitor recent content updates + content strategy + trends + content strengths.
- **People Also Ask & community questions**: Google PAA questions + Reddit/community questions + content opportunities.
- **PDF attachment**: the full report is also attached as a PDF when PDF generation is available.

---

## Workflow (Nodes)

WaveContent runs the following nodes in order (see `WaveContent/config.yaml`):

- **`check_credits_and_init`**

  - Checks credits once and initializes the run.
  - Parses `competitor_websites` into `competitor_websites_list`.

- **`fetch_website_content`**

  - Crawls up to **50** same-domain pages.
  - Stores a lightweight site map to `website_content`, and full per-page payloads to keys like `website_page_0_data`, `website_page_1_data`, etc.

- **`segregrate_website_content`**

  - Classifies pages into buckets (primary/blog/product/docs/legal/other).
  - Stores `segregated_website_content`.

- **`analyze_primary_content`**

  - Audits up to **5** primary pages for content/structure/copy + SEO + LLM readability.
  - Stores `primary_pages_extracted_data`, `primary_content_suggestions`, and `seo_report`.

- **`discover_competitors`**

  - Discovers up to **5** competitors via web search (unless you provided competitors).
  - Stores `competitor_data`.

- **`analyze_competitors`**

  - Benchmarks competitors’ **content** (recent updates + strategy + trends + content strengths).
  - Stores `competitor_analysis`.

- **`people_also_ask_opportunities`**

  - Uses web search to find PAA queries + Reddit/community questions and turns them into content opportunities.
  - Stores `paa_opportunities`.

- **`collect_twitter_insights`** (optional)

  - If a Twitter handle/link can be determined, analyzes recent activity and suggests improvements/ideas using Twitter/X search.
  - Stores `twitter_insights` (otherwise stores `None`).

- **`generate_content_recommendations`**

  - Generates long-form + short-form recommendations and identifies gaps vs competitors.
  - Stores `content_recommendations` and `content_gaps`.

- **`generate_summary`**

  - Produces an executive summary from the analysis outputs.
  - Stores `executive_summary`.

- **`send_email`**
  - Renders a styled HTML email and attaches a PDF version of the report (when available).
  - Stores `display_output` (run-based) for the WaveAssist UI.

---

## Key Stored Data (Debugging)

These are the main keys WaveContent reads/writes via `waveassist.fetch_data()` / `waveassist.store_data()`:

- **Inputs**: `website_url`, `competitor_websites`, `twitter_handle`
- **Crawl**: `website_content`, `website_page_0_data` … `website_page_N_data`
- **Segmentation**: `segregated_website_content`
- **Primary-page audit**: `primary_pages_extracted_data`, `primary_content_suggestions`, `seo_report`
- **Competitors**: `competitor_websites_list`, `competitor_data`, `competitor_analysis`
- **Intent & questions**: `paa_opportunities`
- **Social**: `twitter_insights`
- **Strategy output**: `content_recommendations`, `content_gaps`, `executive_summary`
- **UI/email**: `display_output` (run-based)

---

## Notes

- **Twitter insights may be skipped** if no `twitter_handle` is provided and no Twitter/X link is found on your site.
- **PDF attachment** is best-effort; the email still sends even if PDF generation is unavailable.
