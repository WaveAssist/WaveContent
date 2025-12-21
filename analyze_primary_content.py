import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import waveassist
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


# Initialize WaveAssist SDK for a downstream node (credits already checked)
waveassist.init(check_credits=True)


max_tokens = 6000
temperature = 0.4

# Extraction/prompt sizing guards (avoid sending raw HTML to the LLM)
MAX_LINK_SAMPLES = 30
MAX_IMAGE_SAMPLES = 20
MAX_JSONLD_ITEMS = 15
MAX_SECTION_COUNT = 12
MAX_SECTION_TEXT_CHARS = 1200
MAX_SECTION_BULLETS = 12


class PageRecommendation(BaseModel):
    page_id: str
    url: str
    short_page_summary: str
    key_issues: List[str] = Field(default_factory=list)
    content_and_structure_recommendations: List[str] = Field(default_factory=list)
    copy_suggestions: List[str] = Field(default_factory=list)
    quick_priority_actions: List[str] = Field(default_factory=list)


class SEOReport(BaseModel):
    seo_insights: List[str] = Field(default_factory=list)
    discoverability_metrics: List[str] = Field(default_factory=list)
    llm_readability: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    technical_seo: List[str] = Field(default_factory=list)


class AnalyzePrimaryContentResult(BaseModel):
    primary_content_suggestions: List[PageRecommendation]
    seo_report: SEOReport


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _truncate(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _split_internal_external_links(
    page_url: str, hrefs: List[str]
) -> Tuple[List[str], List[str]]:
    internal: List[str] = []
    external: List[str] = []
    try:
        base_netloc = (urlparse(page_url).netloc or "").lower()
    except Exception:
        base_netloc = ""

    for href in hrefs:
        if not href:
            continue
        href_str = str(href).strip()
        if href_str.startswith("#") or href_str.lower().startswith("mailto:") or href_str.lower().startswith("tel:"):
            continue

        try:
            abs_url = urljoin(page_url, href_str)
            netloc = (urlparse(abs_url).netloc or "").lower()
        except Exception:
            continue

        if base_netloc and netloc == base_netloc:
            internal.append(abs_url)
        elif netloc:
            external.append(abs_url)

    return internal, external


def _extract_jsonld_types(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    scripts = soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)})
    for script in scripts:
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            continue

        def _add_one(obj: Any) -> None:
            if not isinstance(obj, dict):
                return
            t = obj.get("@type") or obj.get("type")
            ctx = obj.get("@context")
            name = obj.get("name")
            url = obj.get("url")
            entry: Dict[str, Any] = {}
            if t is not None:
                entry["type"] = t
            if ctx is not None:
                entry["context"] = ctx
            if name is not None:
                entry["name"] = name
            if url is not None:
                entry["url"] = url
            if entry:
                items.append(entry)

        if isinstance(parsed, list):
            for obj in parsed:
                _add_one(obj)
        elif isinstance(parsed, dict):
            if "@graph" in parsed and isinstance(parsed["@graph"], list):
                for obj in parsed["@graph"]:
                    _add_one(obj)
            else:
                _add_one(parsed)

        if len(items) >= MAX_JSONLD_ITEMS:
            break

    return items[:MAX_JSONLD_ITEMS]


def _extract_page_features(full_html: str, page_url: str) -> Dict[str, Any]:
    """
    Extract multiple structured data points for LLM consumption.
    IMPORTANT: Do not return raw HTML.
    """
    soup = BeautifulSoup(full_html or "", "html.parser")

    # Remove heavy/noisy nodes before extracting text
    for tag in soup(["script", "style", "noscript", "svg"]):
        try:
            tag.decompose()
        except Exception:
            continue

    # Main content node (heuristic: main > article > body)
    main_node = soup.find("main") or soup.find("article") or soup.body or soup

    # Basic doc-level meta
    title = ""
    if soup.title and soup.title.string:
        title = _collapse_ws(soup.title.string)

    meta_description = ""
    description_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if description_tag:
        meta_description = _collapse_ws(description_tag.get("content", ""))

    canonical = ""
    canonical_tag = soup.find("link", rel=lambda v: v and "canonical" in str(v).lower())
    if canonical_tag:
        canonical = _collapse_ws(canonical_tag.get("href", ""))

    meta_robots = ""
    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if robots_tag:
        meta_robots = _collapse_ws(robots_tag.get("content", ""))

    lang = ""
    try:
        if soup.html and soup.html.get("lang"):
            lang = str(soup.html.get("lang")).strip()
    except Exception:
        lang = ""

    # OpenGraph + Twitter cards
    og: Dict[str, str] = {}
    tw: Dict[str, str] = {}
    for m in soup.find_all("meta"):
        prop = (m.get("property") or "").strip()
        name = (m.get("name") or "").strip()
        content = _collapse_ws(m.get("content", ""))
        if not content:
            continue
        if prop.lower().startswith("og:"):
            og[prop.lower()] = content
        if name.lower().startswith("twitter:"):
            tw[name.lower()] = content

    # Headings outline (h1-h6)
    headings: List[Dict[str, str]] = []
    for level in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for tag in soup.find_all(level):
            txt = _collapse_ws(tag.get_text(" ", strip=True))
            if txt:
                headings.append({"level": level, "text": txt})

    # Links + samples
    hrefs: List[str] = []
    link_samples: List[Dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = str(a.get("href") or "").strip()
        if not href:
            continue
        hrefs.append(href)
        if len(link_samples) < MAX_LINK_SAMPLES:
            link_samples.append(
                {
                    "text": _truncate(_collapse_ws(a.get_text(" ", strip=True)), 120),
                    "href": href,
                }
            )

    internal_links, external_links = _split_internal_external_links(page_url, hrefs)

    # Images
    images: List[Dict[str, str]] = []
    images_missing_alt = 0
    for img in soup.find_all("img"):
        src = str(img.get("src") or "").strip()
        alt = _collapse_ws(str(img.get("alt") or ""))
        if not alt:
            images_missing_alt += 1
        if len(images) < MAX_IMAGE_SAMPLES:
            images.append(
                {
                    "src": src,
                    "alt": _truncate(alt, 140),
                    "width": str(img.get("width") or ""),
                    "height": str(img.get("height") or ""),
                    "loading": str(img.get("loading") or ""),
                }
            )

    # CTA detection helpers (CTAs are stored within content_sections only)
    cta_class_keywords = [
        "cta",
        "btn",
        "button",
        "primary",
        "secondary",
        "get-started",
        "get_started",
        "signup",
        "sign-up",
        "sign_up",
        "start",
        "trial",
        "contact",
        "demo",
        "pricing",
        "subscribe",
        "download",
        "book",
        "schedule",
        "talk-to-sales",
        "talk_to_sales",
    ]
    cta_text_keywords = [
        "get started",
        "start",
        "start free",
        "start trial",
        "free trial",
        "try free",
        "sign up",
        "signup",
        "request demo",
        "book a demo",
        "book demo",
        "schedule a demo",
        "contact",
        "contact us",
        "talk to sales",
        "view pricing",
        "pricing",
        "subscribe",
        "download",
        "join",
        "learn more",
    ]

    def _location_hint(tag: Any) -> str:
        try:
            for parent in [tag] + list(tag.parents):
                name = getattr(parent, "name", None)
                if name in {"header", "nav", "main", "article", "section", "footer"}:
                    return str(name)
        except Exception:
            pass
        return "unknown"

    def _nearest_heading_text(tag: Any) -> str:
        try:
            prev = tag.find_previous(["h1", "h2", "h3"])
            if prev and main_node and main_node in prev.parents:
                return _truncate(_collapse_ws(prev.get_text(" ", strip=True)), 160)
        except Exception:
            pass
        return ""

    def _is_cta_candidate(tag: Any) -> bool:
        try:
            name = getattr(tag, "name", "") or ""
            if name not in {"a", "button", "input"}:
                return False

            text = _collapse_ws(tag.get_text(" ", strip=True) if name != "input" else "")
            href = str(tag.get("href") or "").strip() if name == "a" else ""
            input_type = str(tag.get("type") or "").lower().strip() if name == "input" else ""

            class_list = tag.get("class") or []
            class_id = " ".join([str(c) for c in class_list]) + " " + str(tag.get("id") or "")
            class_id_l = class_id.lower()
            text_l = text.lower()

            if any(k in class_id_l for k in cta_class_keywords):
                return True
            if text and any(k in text_l for k in cta_text_keywords):
                return True

            if name == "button" and text:
                return True
            if name == "input" and input_type in {"submit", "button"}:
                return True
            if name == "a" and href and ("button" in class_id_l or "btn" in class_id_l):
                return True
        except Exception:
            return False

        return False

    def _cta_to_obj(tag: Any, kind: str, href: str = "", form_action: str = "") -> Dict[str, Any]:
        text = ""
        if getattr(tag, "name", "") == "input":
            text = _collapse_ws(str(tag.get("value") or "")) or _collapse_ws(str(tag.get("aria-label") or ""))
        else:
            text = _collapse_ws(tag.get_text(" ", strip=True))

        href_abs = ""
        if href:
            try:
                href_abs = urljoin(page_url, href)
            except Exception:
                href_abs = href

        action_abs = ""
        if form_action:
            try:
                action_abs = urljoin(page_url, form_action)
            except Exception:
                action_abs = form_action

        class_list = tag.get("class") or []
        classes = " ".join([str(c) for c in class_list])[:200]

        return {
            "kind": kind,  # link|button|form_submit
            "text": _truncate(text, 140),
            "href": href_abs,
            "form_action": action_abs,
            "location_hint": _location_hint(tag),
            "context_heading": _nearest_heading_text(tag),
            "rel": str(tag.get("rel") or ""),
            "target": str(tag.get("target") or ""),
            "aria_label": _truncate(_collapse_ws(str(tag.get("aria-label") or "")), 140),
            "classes": classes,
        }

    # Content sections (hero + major sections; no HTML)
    def _section_obj(container: Any, kind: str) -> Optional[Dict[str, Any]]:
        try:
            heading_tag = container.find(["h1", "h2", "h3", "h4"])
            heading_txt = _collapse_ws(heading_tag.get_text(" ", strip=True)) if heading_tag else ""
            raw_text = _collapse_ws(container.get_text(" ", strip=True))
            if not raw_text or len(raw_text) < 80:
                return None

            bullets = []
            for li in container.find_all("li"):
                t = _collapse_ws(li.get_text(" ", strip=True))
                if t:
                    bullets.append(_truncate(t, 220))
                if len(bullets) >= MAX_SECTION_BULLETS:
                    break

            # Section-level CTA subset
            section_ctas: List[Dict[str, Any]] = []
            for t in container.find_all(["a", "button", "input"]):
                if len(section_ctas) >= 6:
                    break
                if not _is_cta_candidate(t):
                    continue
                n = getattr(t, "name", "") or ""
                if n == "a":
                    href = str(t.get("href") or "").strip()
                    if not href or href.startswith("#") or href.lower().startswith("mailto:") or href.lower().startswith("tel:"):
                        continue
                    section_ctas.append(_cta_to_obj(t, kind="link", href=href))
                elif n == "button":
                    section_ctas.append(_cta_to_obj(t, kind="button"))
                else:
                    typ = str(t.get("type") or "").lower().strip()
                    if typ in {"submit", "button"}:
                        section_ctas.append(_cta_to_obj(t, kind="button"))

            return {
                "kind": kind,  # hero|section|article
                "heading": _truncate(heading_txt, 180),
                "summary_text": _truncate(raw_text, MAX_SECTION_TEXT_CHARS),
                "bullet_points": bullets,
                "cta_blocks": section_ctas,
            }
        except Exception:
            return None

    content_sections: List[Dict[str, Any]] = []

    header = soup.find("header")
    if header:
        hero_obj = _section_obj(header, kind="hero")
        if hero_obj:
            content_sections.append(hero_obj)

    # Use main/article/body as the base for section extraction
    base = main_node
    for container in base.find_all(["section", "article"], recursive=True) if base else []:
        if len(content_sections) >= MAX_SECTION_COUNT:
            break
        # skip footer/nav areas
        try:
            if container.find_parent(["footer", "nav"]) is not None:
                continue
        except Exception:
            pass

        kind = "article" if getattr(container, "name", "") == "article" else "section"
        obj = _section_obj(container, kind=kind)
        if obj:
            content_sections.append(obj)

    # Word count estimate derived from extracted sections (no separate main_text field)
    joined_section_text = " ".join(
        [str(s.get("summary_text") or "") for s in content_sections if isinstance(s, dict)]
    )
    word_count = len(joined_section_text.split()) if joined_section_text else 0

    jsonld_items = _extract_jsonld_types(soup)

    return {
        "url": page_url,
        "lang": lang,
        "title": title,
        "meta_description": meta_description,
        "canonical": canonical,
        "meta_robots": meta_robots,
        "open_graph": og,
        "twitter_cards": tw,
        "headings": headings,
        "internal_link_count": len(internal_links),
        "external_link_count": len(external_links),
        "link_samples": link_samples,
        "images_count": len(soup.find_all("img")),
        "images_missing_alt_count": images_missing_alt,
        "image_samples": images,
        "content_sections": content_sections,
        "word_count_estimate": word_count,
        "structured_data": jsonld_items,
    }


print("WaveContent: Starting merged primary content + SEO analysis (Top 5 segregated pages)...")

try:
    website_content = waveassist.fetch_data("website_content") or {}
    if not website_content:
        raise ValueError("website_content is required for analyze_primary_content but was not found.")

    segregated = waveassist.fetch_data("segregated_website_content") or {}
    top_primary_pages = (segregated.get("top_primary_pages") or [])[:5]

    # Fallback: if segregation failed, use up to first 5 pages from website_content
    if not top_primary_pages:
        pages = website_content.get("pages") or []
        top_primary_pages = [
            {"page_id": p.get("page_id"), "url": p.get("url")}
            for p in pages[:5]
            if p.get("page_id") and p.get("url")
        ]

    if not top_primary_pages:
        raise ValueError("No primary pages available to analyze (top_primary_pages empty).")

    extracted_pages: List[Dict[str, Any]] = []

    for ref in top_primary_pages[:5]:
        page_id = str(ref.get("page_id") or "").strip()
        ref_url = str(ref.get("url") or "").strip()
        if not page_id:
            continue

        page_key = f"website_{page_id}_data"
        page_data = waveassist.fetch_data(page_key) or {}
        page_url = str(page_data.get("url") or ref_url or "").strip()

        full_html = page_data.get("full_html") or ""
        if not full_html:
            # We can still proceed with whatever we have in summary fields
            extracted = {
                "url": page_url,
                "title": _collapse_ws(str(page_data.get("title") or "")),
                "meta_description": _collapse_ws(str(page_data.get("meta_description") or "")),
                "headings": page_data.get("headings") or [],
                "note": "full_html_missing_for_page",
            }
        else:
            extracted = _extract_page_features(full_html=str(full_html), page_url=page_url)

        extracted_pages.append(
            {
                "page_id": page_id,
                "url": page_url,
                "extracted": extracted,
            }
        )

    if not extracted_pages:
        raise ValueError("No usable pages extracted for analysis.")

    # Store extracted non-HTML page data for downstream debugging/visibility
    waveassist.store_data("primary_pages_extracted_data", extracted_pages)
    model_name = "google/gemini-2.5-flash"

    pages_json = json.dumps(extracted_pages, default=str)
    website_url = website_content.get("url") or waveassist.fetch_data("website_url")

    prompt = f"""
You are an expert content strategist, SEO auditor, and LLM-readability specialist.

You will analyze ONLY the Top Primary Pages (up to 5) selected by a prior segmentation step.
You are given *structured extractions* from each page produced via BeautifulSoup.
Do NOT assume you have the raw HTML (you do not). You must base your analysis strictly on the extracted fields.

Key extracted fields to rely on:
- content_sections: major page sections with heading, section summary text, bullet points, and section-level CTAs (this is the main content signal)
- headings/meta/links/images/structured_data: use these for SEO + technical checks and information architecture evaluation

What to produce (two top-level outputs):

1) primary_content_suggestions
- Return a LIST with one item per page (each item is a PageRecommendation).
- Keep recommendations concrete and specific to this page's extracted sections/CTAs.

Inside each primary_content_suggestions item:
- page_id: the provided page id
- url: the provided page url
- key_issues: 2–5 specific, page-specific problems (unclear value prop, weak proof, confusing flow, mismatched CTAs, missing sections, etc.)
- content_and_structure_recommendations: 2–5 actionable edits (what to add/remove/change, what section to create, what proof to include, section order/headings/scannability)
- copy_suggestions: 2–5 rewrite suggestions (headline variants, subhead hooks, CTA text variants, microcopy, proof/claims wording)
- quick_priority_actions: 2–5 highest-impact actions to do first (fastest path to improvement)

2) seo_report (2-5 points each, if any)
- seo_insights: key SEO observations across the Top 5 pages (titles/descriptions, headings, internal linking, etc.)
- discoverability_metrics: lightweight, qualitative “metrics”/signals derived from extraction (e.g., title/description presence/quality, schema presence, image alt coverage, internal link depth)
- llm_readability: what helps/hurts AI/LLM consumption (clear entities, definitions, headings, structured FAQs, etc.)
- recommendations: prioritized SEO + discoverability improvements (what to fix and why)
- technical_seo: technical findings visible from extraction (canonical/robots/meta tags, structured data, link patterns, potential indexability issues)

Critical Note: Keep everything short and to the point. 
Customer website url: {website_url}

Top pages extracted data (JSON):
{pages_json}

"""

    result = waveassist.call_llm(
        model=model_name,
        prompt=prompt,
        response_model=AnalyzePrimaryContentResult,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    if result:
        data = result.model_dump(by_alias=True)
        waveassist.store_data("primary_content_suggestions", data.get("primary_content_suggestions"))
        waveassist.store_data("seo_report", data.get("seo_report"))
        print(
            f"WaveContent: Stored primary_content_suggestions + seo_report for {len(extracted_pages)} primary pages."
        )
    else:
        waveassist.store_data("primary_content_suggestions", None)
        waveassist.store_data("seo_report", None)
        print("WaveContent: No result from LLM when analyzing primary content + SEO.")

except Exception as e:
    print(f"WaveContent: Error while analyzing primary content + SEO: {e}")
    waveassist.store_data("primary_content_suggestions", None)
    waveassist.store_data("seo_report", None)
    raise


