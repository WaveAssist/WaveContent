<h1 align="center">WaveContent: Open-Source AI Agent for SEO & Content Strategy</h1>

<p align="center">
  <a href="https://waveassist.io/assistants/wavecontent">
    <img src="https://img.shields.io/badge/Deploy_with-WaveAssist-007F3B" alt="Deploy WaveContent on WaveAssist" />
  </a>
  <img src="https://img.shields.io/badge/WaveContent-AI%20Content%20Strategy%20Agent-blue" alt="WaveContent AI content strategy agent badge" />
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License" />
  </a>
</p>

---

## Overview

WaveContent is an AI agent that analyzes your website, benchmarks competitors, and delivers actionable SEO and content recommendations.

---

## One-Click Deploy on WaveAssist (Recommended)

<p>
  <a href="https://waveassist.io/assistants/wavecontent" target="_blank">
    <img src="https://waveassist.io/images/templates/Button.png" alt="Deploy WaveContent on WaveAssist" width="230" />
  </a>
</p>

Deploy WaveContent instantly on [WaveAssist](https://waveassist.io) — a zero-infrastructure AI agent platform that handles orchestration, scheduling, secrets, and hosting for you.

> 🔐 You may be prompted to log in or create a free WaveAssist account before continuing.

### How to Use

1. Set **`website_url`** (required) — the homepage to crawl and analyze.
2. (Optional) Set **`competitor_websites`** as a comma-separated list of competitor homepages.
3. (Optional) Set **`twitter_handle`** (e.g. `@brand`). If omitted, WaveContent tries to find a Twitter/X link from your site.
4. Click **Run & Deploy** (or **Run**).

---

## Inputs

- **Required**

  - **`website_url`**: Website homepage to crawl and analyze (e.g. `https://example.com`)

- **Optional**

  - **`competitor_websites`**: Comma-separated competitor URLs (e.g. `https://site1.com, https://site2.com`)
  - **`twitter_handle`**: Twitter/X handle or URL (e.g. `@brand` or `https://x.com/brand`)
  - **`schedule`**: Customize the run schedule (default: 1st and 15th of each month at 8:30 AM UTC)

---

## What You Get (Outputs)

WaveContent delivers a **comprehensive content strategy email** with an attached PDF report.

### 📧 Content Strategy Report

Structure:

| Section                              | Description                                                                                     |
| ------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **Executive Summary**                | 1–2 sentence overview + key findings + top opportunities.                                       |
| **Primary Page Recommendations**     | Per-page issues + structure recommendations + copy ideas + quick wins (up to 5 primary pages).  |
| **SEO & Discoverability Report**     | SEO insights, discoverability signals, technical SEO checks, and LLM readability notes.         |
| **New Content Recommendations**      | Long-form + short-form ideas and recurring themes.                                              |
| **Competitor Content Analysis**      | Competitor recent content updates + content strategy + trends + strengths.                       |
| **People Also Ask & Community**      | Google PAA questions + Reddit/community questions + content opportunities.                       |
| **Twitter/X Insights** *(optional)*  | Social presence analysis and engagement patterns (when a handle is available).                   |

Included: a **PDF attachment** of the full report for offline sharing.

---

## Schedule

WaveContent runs on a **configurable schedule** (default: 1st and 15th of each month at 8:30 AM UTC). Each report covers the latest state of your website, competitors, and audience questions.

---

## How It Works

WaveContent follows a multi-stage analysis pipeline:

1. **Collection**: Crawls up to 50 same-domain pages using Crawlee and classifies them into buckets (primary / blog / product / docs / legal / other).
2. **Competitive Intelligence**: Discovers up to 5 competitors via web search (or uses your list) and benchmarks their content strategy. Mines Google PAA and Reddit for real audience questions.
3. **Deep Analysis**: Analyzes up to 5 primary pages for content quality, structure, SEO, and LLM readability. Optionally analyzes your Twitter/X presence.
4. **Strategy Generation**: Produces long-form and short-form content recommendations, identifies content gaps vs. competitors, and writes an executive summary tying all findings together.
5. **Delivery**: Sends a styled HTML email with an attached PDF report.

## Notes

- **Website crawling**: Crawls up to 50 same-domain pages to build a comprehensive site map before analysis.
- **Competitor discovery**: Automatically finds up to 5 competitors if you don't provide a list.
- **Twitter insights are optional**: Skipped if no `twitter_handle` is provided and no Twitter/X link is found on your site.
- **PDF attachment**: Best-effort; the email still sends even if PDF generation is unavailable.
- **AI-powered**: All analysis and recommendations are generated by AI models via OpenRouter.

---

Built with ❤️ by the [WaveAssist](https://waveassist.io) team. Questions or integrations? [Say hello](https://waveassist.io).
