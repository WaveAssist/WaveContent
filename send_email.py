import html
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import waveassist

# WeasyPrint is used to generate a PDF attachment containing the full report.
# (WaveAssist email supports attachments via `attachment_file`.)
from weasyprint import HTML  # type: ignore


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)

print("WaveContent: Starting send_email node...")


def _esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _is_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def _link(url: Any, label: Optional[str] = None) -> str:
    u = str(url or "").strip()
    if not u:
        return ""
    safe_label = _esc(label) if label else _esc(u)
    if _is_http_url(u):
        return f'<a href="{_esc(u)}" target="_blank" rel="noopener noreferrer">{safe_label}</a>'
    return safe_label


def _coerce_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _ul(items: Any) -> str:
    arr = [i for i in _coerce_list(items) if i not in (None, "")]
    if not arr:
        return ""
    lis = []
    for item in arr:
        lis.append(f"<li>{_esc(item)}</li>")
    return "<ul>" + "".join(lis) + "</ul>"


def _csv(items: Any) -> str:
    arr = [str(i).strip() for i in _coerce_list(items) if i not in (None, "")]
    arr = [a for a in arr if a]
    if not arr:
        return ""
    return _esc(", ".join(arr))


def _pill(text: str, kind: str = "neutral") -> str:
    t = (text or "").strip()
    if not t:
        return ""
    # Keep pills simple (avoid lots of colors); still helpful for skimming.
    return f'<span class="pill">Priority: {_esc(t.upper())}</span>'


def _section(title: str, anchor: str, body_html: str, css_class: str = "") -> str:
    if not body_html.strip():
        return ""
    cls = "section"
    if css_class:
        cls += f" {_esc(css_class)}"
    return f"""
    <div class="{cls}" id="{_esc(anchor)}">
      <h2>{_esc(title)}</h2>
      {body_html}
    </div>
    """


def _subsection(title: str, body_html: str) -> str:
    if not body_html.strip():
        return ""
    return f"""
    <div class="subsection">
      <h3>{_esc(title)}</h3>
      {body_html}
    </div>
    """


def _kv_row(label: str, value_html: str) -> str:
    if not value_html.strip():
        return ""
    return f"""
    <div class="kv-row">
      <div class="kv-label">{_esc(label)}</div>
      <div class="kv-value">{value_html}</div>
    </div>
    """


def _domain_label(url: str) -> str:
    try:
        p = urlparse(url)
        return (p.netloc or "").replace("www.", "")
    except Exception:
        return ""


def _render_executive_summary(executive_summary: Dict[str, Any]) -> str:
    if not isinstance(executive_summary, dict):
        executive_summary = {}

    overview = str(executive_summary.get("overview") or "").strip()
    key_findings = _coerce_list(executive_summary.get("key_findings"))
    top_opps = _coerce_list(executive_summary.get("top_opportunities"))

    if not overview and not key_findings and not top_opps:
        return ""

    body = ""
    if overview:
        body += f'<p class="lead">{_esc(overview)}</p>'

    body += _subsection("Key findings", _ul(key_findings))
    body += _subsection("Top opportunities", _ul(top_opps))
    return body


def _render_primary_content(primary_suggestions: Any) -> str:
    pages = _coerce_list(primary_suggestions)
    if not pages:
        return ""

    blocks: List[str] = []
    for i, rec in enumerate(pages, start=1):
        if not isinstance(rec, dict):
            continue
        url = str(rec.get("url") or "").strip()
        short_summary = str(rec.get("short_page_summary") or "").strip()

        key_issues = _coerce_list(rec.get("key_issues"))
        structure_recos = _coerce_list(rec.get("content_and_structure_recommendations"))
        copy_suggestions = _coerce_list(rec.get("copy_suggestions"))
        quick_actions = _coerce_list(rec.get("quick_priority_actions"))

        inner = ""
        if short_summary:
            inner += f"<p class='muted'><strong>Snapshot:</strong> {_esc(short_summary)}</p>"

        inner += _subsection("Key issues", _ul(key_issues))
        inner += _subsection("Content & structure recommendations", _ul(structure_recos))
        inner += _subsection("Copy suggestions", _ul(copy_suggestions))
        inner += _subsection("Quick priority actions", _ul(quick_actions))

        blocks.append(
            f"""
            <div class="card">
              <h3 class="card-title">{_esc(f"{i}.")} {_link(url, label=url) if url else "Page recommendations"}</h3>
              {inner}
            </div>
            """
        )

    if not blocks:
        return ""

    return "".join(blocks)


def _render_seo_report(seo_report: Any) -> str:
    if not isinstance(seo_report, dict):
        seo_report = {}

    seo_insights = _ul(seo_report.get("seo_insights"))
    discoverability_metrics = _ul(seo_report.get("discoverability_metrics"))
    llm_readability = _ul(seo_report.get("llm_readability"))
    recommendations = _ul(seo_report.get("recommendations"))
    technical_seo = _ul(seo_report.get("technical_seo"))

    if not any(
        [
            seo_insights.strip(),
            discoverability_metrics.strip(),
            llm_readability.strip(),
            recommendations.strip(),
            technical_seo.strip(),
        ]
    ):
        return ""

    body = ""
    body += _subsection("SEO insights", seo_insights)
    body += _subsection("Discoverability signals", discoverability_metrics)
    body += _subsection("LLM readability", llm_readability)
    body += _subsection("Recommendations", recommendations)
    body += _subsection("Technical SEO notes", technical_seo)

    return body


def _render_content_recommendations(content_recommendations: Any) -> str:
    if not isinstance(content_recommendations, dict):
        content_recommendations = {}

    long_form = _coerce_list(content_recommendations.get("long_form_content"))
    short_form = _coerce_list(content_recommendations.get("short_form_content"))
    themes = _coerce_list(content_recommendations.get("content_themes"))

    long_blocks: List[str] = []
    for idea in long_form:
        if not isinstance(idea, dict):
            continue
        title = str(idea.get("title") or "").strip()
        priority = str(idea.get("priority") or "").strip().lower()
        target = str(idea.get("target_audience") or "").strip()
        primary_kw = str(idea.get("primary_keyword") or "").strip()
        secondary_kws = _coerce_list(idea.get("secondary_keywords"))
        intent = str(idea.get("search_intent") or "").strip()
        angle = str(idea.get("angle") or "").strip()
        outline = _coerce_list(idea.get("outline"))
        cta = str(idea.get("recommended_cta") or "").strip()

        head = f"{_esc(title) if title else 'Long-form idea'} {_pill(priority)}"

        body = ""
        body += _kv_row("Target audience", _esc(target))
        body += _kv_row("Primary keyword", _esc(primary_kw))
        body += _kv_row("Secondary keywords", _ul(secondary_kws))
        body += _kv_row("Search intent", _esc(intent))
        body += _kv_row("Angle", _esc(angle))
        body += _kv_row("Outline", _ul(outline))
        body += _kv_row("Recommended CTA", _esc(cta))

        long_blocks.append(
            f"""
            <div class="card">
              <h3 class="card-title">{head}</h3>
              <div class="kv">{body}</div>
            </div>
            """
        )

    short_blocks: List[str] = []
    for idea in short_form:
        if not isinstance(idea, dict):
            continue
        platform = str(idea.get("platform") or "").strip()
        content_type = str(idea.get("content_type") or "").strip()
        hook = str(idea.get("hook") or "").strip()
        concept = str(idea.get("concept") or "").strip()
        optional_post_text = str(idea.get("optional_post_text") or "").strip()
        hashtags = _coerce_list(idea.get("suggested_hashtags"))
        cta = str(idea.get("cta") or "").strip()
        priority = str(idea.get("priority") or "").strip().lower()

        title = " · ".join([b for b in [platform, content_type] if b]).strip() or "Short-form idea"
        head = f"{_esc(title)} {_pill(priority)}"

        body = ""
        body += _kv_row("Hook", _esc(hook))
        body += _kv_row("Concept", _esc(concept))
        if optional_post_text:
            # Keep readable (no dark blocks); still preserve formatting.
            body += _kv_row("Suggested post text", f"<pre>{_esc(optional_post_text)}</pre>")
        body += _kv_row("Suggested hashtags", _csv(hashtags))
        body += _kv_row("CTA", _esc(cta))

        short_blocks.append(
            f"""
            <div class="card">
              <h3 class="card-title">{head}</h3>
              <div class="kv">{body}</div>
            </div>
            """
        )

    theme_html = ""
    if themes:
        items = []
        for t in themes:
            if not isinstance(t, dict):
                continue
            theme = str(t.get("theme") or "").strip()
            desc = str(t.get("description") or "").strip()
            why = str(t.get("why_it_matters") or "").strip()
            if not (theme or desc or why):
                continue
            items.append(
                f"""
                <div class="card">
                  <h3 class="card-title">{_esc(theme or "Theme")}</h3>
                  <div class="kv">
                    {_kv_row("Description", _esc(desc))}
                    {_kv_row("Why it matters", _esc(why))}
                  </div>
                </div>
                """
            )
        theme_html = "".join(items)

    body = ""
    body += _subsection("Long-form content ideas", "".join(long_blocks))
    body += _subsection("Short-form content ideas", "".join(short_blocks))
    body += _subsection("Content themes", theme_html)

    return body


def _render_competitor_analysis(competitor_analysis: Any) -> str:
    if not isinstance(competitor_analysis, dict):
        competitor_analysis = {}
    competitors = _coerce_list(competitor_analysis.get("competitor_data"))
    if not competitors:
        return ""

    blocks: List[str] = []
    for comp in competitors:
        if not isinstance(comp, dict):
            continue
        url = str(comp.get("url") or "").strip()
        name = str(comp.get("name") or "").strip()
        content_strategy = str(comp.get("content_strategy") or "").strip()
        trends = _coerce_list(comp.get("trends"))
        strengths = _coerce_list(comp.get("strengths"))
        recent_updates = _coerce_list(comp.get("recent_updates"))

        title = name or url or "Competitor"

        updates_html = ""
        if recent_updates:
            items = []
            for upd in recent_updates:
                if not isinstance(upd, dict):
                    continue
                t = str(upd.get("title") or "").strip()
                u = str(upd.get("url") or "").strip()
                published = str(upd.get("published_at") or "").strip()
                ctype = str(upd.get("content_type") or "").strip()
                summary = str(upd.get("summary") or "").strip()

                meta_bits = [b for b in [published, ctype] if b]
                meta = " · ".join(meta_bits)
                items.append(
                    f"""
                    <li>
                      <div><strong>{_link(u, label=t or u) if (u or t) else "Update"}</strong></div>
                      {f"<div class='muted'>{_esc(meta)}</div>" if meta else ""}
                      {f"<div class='muted'>{_esc(summary)}</div>" if summary else ""}
                    </li>
                    """
                )
            if items:
                updates_html = "<ul>" + "".join(items) + "</ul>"

        body = ""
        if url:
            body += f"<div class='meta'>{_link(url, label=url)}</div>"
        if content_strategy:
            body += f"<p>{_esc(content_strategy)}</p>"
        body += _subsection("Trends", _ul(trends))
        body += _subsection("Strengths (content only)", _ul(strengths))
        body += _subsection("Recent content updates", updates_html)

        blocks.append(
            f"""
            <div class="card">
              <h3 class="card-title">{_esc(title)}</h3>
              {body}
            </div>
            """
        )

    return "".join(blocks)


def _render_paa(paa_opportunities: Any, trending_topics: Any) -> str:
    if not isinstance(paa_opportunities, dict):
        paa_opportunities = {}

    google_paa_queries = _coerce_list(paa_opportunities.get("google_paa_queries"))
    reddit_questions = _coerce_list(paa_opportunities.get("reddit_questions"))
    trending = _coerce_list(trending_topics)

    google_html = ""
    if google_paa_queries:
        items = []
        for q in google_paa_queries:
            if not isinstance(q, dict):
                continue
            question = str(q.get("question") or "").strip()
            src = str(q.get("source_url") or "").strip()
            snippet = str(q.get("context_snippet") or "").strip()
            if not question:
                continue
            items.append(
                f"""
                <li>
                  <div><strong>{_esc(question)}</strong></div>
                  {f"<div class='muted'>Source: {_link(src, label=src)}</div>" if src else ""}
                  {f"<div class='muted'>{_esc(snippet)}</div>" if snippet else ""}
                </li>
                """
            )
        if items:
            google_html = "<ul>" + "".join(items) + "</ul>"

    reddit_html = ""
    if reddit_questions:
        items = []
        for q in reddit_questions:
            if not isinstance(q, dict):
                continue
            question = str(q.get("question") or "").strip()
            subreddit = str(q.get("subreddit") or "").strip()
            url = str(q.get("url") or "").strip()
            upvotes = q.get("upvotes")
            snippet = str(q.get("context_snippet") or "").strip()
            if not question:
                continue
            meta_bits = []
            if subreddit:
                meta_bits.append(f"r/{subreddit}")
            if upvotes is not None and str(upvotes).strip() != "":
                meta_bits.append(f"↑ {upvotes}")
            meta = " · ".join(meta_bits)
            items.append(
                f"""
                <li>
                  <div><strong>{_link(url, label=question) if url else _esc(question)}</strong></div>
                  {f"<div class='muted'>{_esc(meta)}</div>" if meta else ""}
                  {f"<div class='muted'>{_esc(snippet)}</div>" if snippet else ""}
                </li>
                """
            )
        if items:
            reddit_html = "<ul>" + "".join(items) + "</ul>"

    trending_html = _ul(trending)

    body = ""
    # Only show the three requested blocks; box them for readability.
    if google_html:
        body += f"""
        <div class="card section-card">
          <h3 class="card-title">Google "People Also Ask" questions</h3>
          {google_html}
        </div>
        """
    if reddit_html:
        body += f"""
        <div class="card section-card">
          <h3 class="card-title">Reddit / community questions</h3>
          {reddit_html}
        </div>
        """
    if trending_html:
        body += f"""
        <div class="card section-card">
          <h3 class="card-title">Trending topics</h3>
          {trending_html}
        </div>
        """

    return body


try:
    website_url = (
        str(waveassist.fetch_data("website_url") or "").strip()
        or str((waveassist.fetch_data("website_content") or {}).get("url") or "").strip()
    )
    domain = _domain_label(website_url) if website_url else ""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Core analysis outputs
    executive_summary = waveassist.fetch_data("executive_summary") or {}
    primary_content_suggestions = waveassist.fetch_data("primary_content_suggestions") or []
    seo_report = waveassist.fetch_data("seo_report") or {}
    content_recommendations = waveassist.fetch_data("content_recommendations") or {}
    competitor_analysis = waveassist.fetch_data("competitor_analysis") or {}
    paa_opportunities = waveassist.fetch_data("paa_opportunities") or {}
    twitter_insights = waveassist.fetch_data("twitter_insights") or {}

    # Render sections (priority order requested)
    summary_html = _render_executive_summary(executive_summary)
    if not summary_html.strip():
        # Keep the email readable even if summary is missing.
        summary_html = "<p class='muted'>Executive summary was not available for this run.</p>"

    primary_html = _render_primary_content(primary_content_suggestions)
    seo_html = _render_seo_report(seo_report)
    if seo_html.strip():
        # Keep this section boxed like others (requested).
        seo_html = f"<div class='card section-card'>{seo_html}</div>"

    recos_html = _render_content_recommendations(content_recommendations)

    competitors_html = _render_competitor_analysis(competitor_analysis)
    paa_html = _render_paa(paa_opportunities, trending_topics=twitter_insights.get("trending_topics"))

    # Email "Sections" list (non-clickable). Many email clients don't reliably support in-email anchors.
    sections_present: List[str] = ["Executive summary"]
    if primary_html.strip():
        sections_present.append("Primary page recommendations")
    if seo_html.strip():
        sections_present.append("SEO & discoverability")
    if recos_html.strip():
        sections_present.append("New content recommendations")
    if competitors_html.strip():
        sections_present.append("Competitor content analysis")
    if paa_html.strip():
        sections_present.append("People Also Ask & community questions")
    sections_present.append("PDF attachment")

    email_sections_html = (
        "<div class='sections'>" + " · ".join([_esc(s) for s in sections_present]) + "</div>"
    )

    # PDF table of contents (only include sections that exist)
    pdf_toc_items: List[str] = []
    if summary_html.strip():
        pdf_toc_items.append('<li><a href="#summary">Key Summary</a></li>')
    if primary_html.strip():
        pdf_toc_items.append('<li><a href="#primary">Primary page recommendations</a></li>')
    if seo_html.strip():
        pdf_toc_items.append('<li><a href="#seo">SEO & discoverability</a></li>')
    if recos_html.strip():
        pdf_toc_items.append('<li><a href="#recommendations">New content recommendations</a></li>')
    if competitors_html.strip():
        pdf_toc_items.append('<li><a href="#competitors">Competitor content analysis</a></li>')
    if paa_html.strip():
        pdf_toc_items.append('<li><a href="#paa">People Also Ask & community questions</a></li>')

    pdf_toc_html = (
        f"<ul class='toc'>{''.join(pdf_toc_items)}</ul>"
        if pdf_toc_items
        else "<p class='muted'>No sections available.</p>"
    )

    # If everything is empty, send a graceful fallback (email + no PDF)
    any_content = any(
        [
            primary_html.strip(),
            seo_html.strip(),
            recos_html.strip(),
            competitors_html.strip(),
            paa_html.strip(),
        ]
    ) or bool(summary_html.strip())

    if not any_content:
        html_body = f"""
        <div style="text-align:center; padding:40px; font-family: 'Helvetica Neue', Arial, sans-serif;">
          <h2 style="color:#d32f2f;">WaveContent report unavailable</h2>
          <p style="color:#666; font-size:16px;">We could not generate a usable report from the available inputs.</p>
          <p style="color:#666; font-size:14px;">Generated: {_esc(timestamp)}</p>
        </div>
        """
        subject = "WaveContent: Report unavailable"
        waveassist.send_email(subject=subject, html_content=html_body)
        waveassist.store_data(
            "display_output",
            {"title": subject, "html_content": html_body, "status": "error"},
            run_based=True,
        )
        raise Exception("WaveContent: send_email had no content to send.")

    title = "WaveContent: Content Roadmap & Strategy"
    if domain:
        title = f"WaveContent: Content Roadmap — {domain}"

    # 1) Build the email HTML (full report + attachment note)
    email_html_body = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color:#0f172a; margin: 18px; }}
          a {{ color:#148F47; text-decoration:none; }}
          a:hover {{ text-decoration:underline; }}
          h1 {{ color:#0f1116; font-size: 22px; margin: 0 0 6px 0; }}
          h2 {{ color:#0f1116; margin-top: 28px; font-size: 22px; padding: 10px 0 10px 12px; border-left: 4px solid #1ED66C; border-bottom: 1px solid #e5e7eb; }}
          h2 {{ page-break-after: avoid; break-after: avoid-page; }}
          h3 {{ color:#0f1116; margin: 14px 0 8px 0; font-size: 14px; }}
          p {{ margin: 8px 0; line-height: 1.45; }}
          ul {{ margin: 6px 0 10px 18px; padding: 0; }}
          li {{ margin: 4px 0; line-height: 1.45; }}
          pre {{ white-space: pre-wrap; word-wrap: break-word; background: transparent; color:#0f172a; padding: 10px; border-radius: 8px; font-size: 12px; border: 1px solid #e5e7eb; font-family: ui-monospace, "JetBrains Mono", Menlo, Monaco, Consolas, monospace; }}

          .header {{ padding: 14px; border: 1px solid #e5e7eb; border-top: 4px solid #1ED66C; border-radius: 12px; background: #ffffff; }}
          .meta {{ color:#6b7280; font-size: 12px; margin-top: 6px; }}
          .lead {{ font-size: 14px; }}
          .muted {{ color:#6b7280; font-size: 12px; }}
          .section {{ margin-top: 8px; }}
          .subsection {{ margin-top: 8px; }}
          .card {{ border: 1px solid #e5e7eb; border-left: 3px solid #1ED66C; border-radius: 12px; padding: 12px; margin: 10px 0; background: #ffffff; }}
          .card-title {{ margin: 0 0 8px 0; font-size: 14px; }}

          .kv {{ margin-top: 6px; }}
          .kv-row {{ display: flex; gap: 10px; padding: 6px 0; border-top: 1px solid #f3f4f6; }}
          .kv-row:first-child {{ border-top: none; padding-top: 0; }}
          .kv-label {{ width: 160px; color:#6b7280; font-size: 12px; }}
          .kv-value {{ flex: 1; font-size: 12px; }}

          .toc {{ margin: 10px 0 0 18px; }}
          .pill {{ display:inline-block; font-size: 11px; padding: 2px 8px; border-radius: 999px; border: 1px solid #e5e7eb; color:#374151; margin-left: 6px; }}
          .sections {{ margin-top: 6px; color:#374151; font-size: 12px; }}

          @media (max-width: 600px) {{
            .kv-row {{ display:block; }}
            .kv-label {{ width:auto; margin-bottom: 2px; }}
          }}
        </style>
      </head>
      <body>
        <div class="header">
          <h1>{_esc(title)}</h1>
          <div class="meta">
            Website: {_link(website_url, label=website_url) if website_url else "<span class='muted'>(not provided)</span>"}
            &nbsp;·&nbsp; Generated: {_esc(timestamp)}
          </div>
          <div class="subsection">
            <h3>Sections</h3>
            {email_sections_html}
          </div>
        </div>

        {_section("Key Summary", "summary", summary_html)}
        {_section("Primary page recommendations", "primary", primary_html)}
        {_section("SEO & discoverability", "seo", seo_html)}
        {_section("New content recommendations", "recommendations", recos_html)}
        {_section("Competitor content analysis", "competitors", competitors_html)}
        {_section('People Also Ask & community questions', "paa", paa_html)}

        <div class="section" id="attachments">
          <h2>Content in the attachments (PDF)</h2>
          <p class="lead">This full report is also attached as a PDF for easier sharing and printing.</p>
          <p class="muted">If you don’t see the attachment, try viewing this email in a desktop client or download attachments in your inbox.</p>
        </div>

        <div class="muted" style="margin-top: 26px; text-align:center;">
          Powered by WaveAssist · WaveContent
        </div>
      </body>
    </html>
    """

    # 2) Build the PDF HTML (full report)
    pdf_html_body = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          @page {{ margin: 18mm; }}
          body {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color:#0f1116; }}
          a {{ color:#148F47; text-decoration:none; }}
          h1 {{ font-size: 22px; margin: 0 0 6px 0; }}
          h2 {{ font-size: 18px; margin-top: 18px; border-left: 4px solid #1ED66C; padding: 8px 0 8px 10px; border-bottom: 1px solid #e5e7eb; }}
          h2 {{ page-break-after: avoid; break-after: avoid-page; }}
          h3 {{ font-size: 13px; margin: 12px 0 6px 0; }}
          p {{ margin: 7px 0; line-height: 1.4; }}
          ul {{ margin: 6px 0 10px 16px; padding: 0; }}
          li {{ margin: 3px 0; line-height: 1.4; }}
          pre {{ white-space: pre-wrap; word-wrap: break-word; background: transparent; color:#0f1116; padding: 10px; border-radius: 8px; font-size: 11px; border: 1px solid #e5e7eb; font-family: ui-monospace, "JetBrains Mono", Menlo, Monaco, Consolas, monospace; }}

          .header {{ padding: 12px; border: 1px solid #e5e7eb; border-top: 4px solid #1ED66C; border-radius: 10px; background: #ffffff; }}
          .meta {{ color:#6b7280; font-size: 11px; margin-top: 6px; }}
          .lead {{ font-size: 13px; }}
          .muted {{ color:#6b7280; font-size: 11px; }}
          .section {{ margin-top: 8px; }}
          .subsection {{ margin-top: 8px; }}
          .card {{ border: 1px solid #e5e7eb; border-left: 3px solid #1ED66C; border-radius: 10px; padding: 10px; margin: 10px 0; background: #ffffff; page-break-inside: auto; break-inside: auto; }}
          .card-title {{ margin: 0 0 8px 0; font-size: 13px; }}
          .page-break {{ page-break-before: always; break-before: page; }}

          .kv {{ margin-top: 6px; }}
          .kv-row {{ padding: 6px 0; border-top: 1px solid #f3f4f6; }}
          .kv-row:first-child {{ border-top: none; padding-top: 0; }}
          .kv-label {{ color:#6b7280; font-size: 11px; margin-bottom: 2px; }}
          .kv-value {{ font-size: 11px; }}

          .toc {{ margin: 10px 0 0 16px; }}
          .pill {{ display:inline-block; font-size: 10px; padding: 2px 7px; border-radius: 999px; border: 1px solid #e5e7eb; color:#374151; margin-left: 6px; }}
        </style>
      </head>
      <body>
        <div class="header">
          <h1>{_esc(title)}</h1>
          <div class="meta">
            Website: {_link(website_url, label=website_url) if website_url else "<span class='muted'>(not provided)</span>"}
            &nbsp;·&nbsp; Generated: {_esc(timestamp)}
          </div>
          <div class="subsection">
            <h3>Quick links</h3>
            {pdf_toc_html}
          </div>
        </div>

        {_section("Key Summary", "summary", summary_html)}
        {_section("Primary page recommendations", "primary", primary_html)}
        {_section("SEO & discoverability", "seo", seo_html, css_class="page-break")}
        {_section("New content recommendations", "recommendations", recos_html)}
        {_section("Competitor content analysis", "competitors", competitors_html)}
        {_section('People Also Ask & community questions', "paa", paa_html)}

        <div class="muted" style="margin-top: 22px; text-align:center;">
          Powered by WaveAssist · WaveContent
        </div>
      </body>
    </html>
    """

    # 3) Generate the PDF (WeasyPrint) and send as attachment
    pdf_file = None
    pdf_error: Optional[str] = None
    pdf_filename_bits = ["WaveContent_Report"]
    if domain:
        pdf_filename_bits.append(domain.replace(".", "_"))
    pdf_filename_bits.append(datetime.now().strftime("%Y%m%d_%H%M"))
    pdf_filename = "_".join(pdf_filename_bits) + ".pdf"

    try:
        pdf_bytes = HTML(string=pdf_html_body).write_pdf()
        pdf_file = io.BytesIO(pdf_bytes)
        # WaveAssist SDK reads attachment_file.name for filename.
        setattr(pdf_file, "name", pdf_filename)
        pdf_file.seek(0)
    except Exception as e:
        pdf_error = f"WeasyPrint PDF generation failed: {e}"
        pdf_file = None

    subject = title
    print("WaveContent: Sending email (summary in body, full report as PDF attachment)...")
    success = waveassist.send_email(
        subject=subject,
        html_content=email_html_body,
        attachment_file=pdf_file,
    )
    if success:
        print("WaveContent: Email sent successfully.")
    else:
        print("WaveContent: Email sending returned unsuccessful response.")

    waveassist.store_data(
        "display_output",
        {
            "title": subject,
            "html_content": email_html_body,
            "status": "success" if success else "error",
            "pdf_attachment": {
                "enabled": True,
                "file_name": pdf_filename,
                "generated": pdf_file is not None,
                "error": pdf_error,
            },
        },
        run_based=True,
    )
    print("WaveContent: send_email node completed.")

except Exception as e:
    print(f"WaveContent: Error in send_email node: {e}")
    # Store a fallback display_output so the run UI has something to show
    fallback = {
        "title": "WaveContent: Email generation error",
        "html_content": f"<p>WaveContent failed to generate/send the email due to an error: <strong>{_esc(e)}</strong></p>",
        "status": "error",
    }
    waveassist.store_data("display_output", fallback, run_based=True)
    raise


