from __future__ import annotations

import html
import re
import statistics
import time
from typing import Dict, List
from urllib.parse import unquote

import requests

USER_AGENT = "Mozilla/5.0 (compatible; RCS-Digital-Product-Scout/2.1; +market-research)"


def _decode_redirect(href: str) -> str:
    href = html.unescape(href)
    match = re.search(r"[?&]uddg=([^&]+)", href)
    return unquote(match.group(1)) if match else href


def _hrefs(page: str) -> List[str]:
    raw = re.findall(r"href\s*=\s*[\"']([^\"']+)[\"']", page, flags=re.I)
    return [_decode_redirect(x) for x in raw]


def _usd_prices(page: str) -> List[float]:
    values: List[float] = []
    patterns = [
        r"currency-value[^>]*>\s*([0-9]{1,4}(?:\.[0-9]{1,2})?)",
        r'\"amount\"\s*:\s*\"?([0-9]{1,4}(?:\.[0-9]{1,2})?)',
        r"\$\s?([0-9]{1,3}(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, page, flags=re.I):
            try:
                value = float(str(match).replace(",", ""))
            except ValueError:
                continue
            if 1.0 <= value <= 250.0:
                values.append(round(value, 2))
    return sorted(set(values))[:30]


def _ddg_search(session: requests.Session, phrase: str, domain: str) -> tuple[set[str], str]:
    query = f"site:{domain} {phrase}"
    response = session.get("https://html.duckduckgo.com/html/", params={"q": query}, timeout=12)
    response.raise_for_status()
    page = response.text
    links = {link for link in _hrefs(page) if domain.lower() in link.lower()}
    return links, page


def _bing_search(session: requests.Session, phrase: str, domain: str) -> tuple[set[str], str]:
    query = f"site:{domain} {phrase}"
    response = session.get(
        "https://www.bing.com/search",
        params={"q": query, "count": 20, "setlang": "en"},
        timeout=15,
    )
    response.raise_for_status()
    page = response.text
    links = {link for link in _hrefs(page) if domain.lower() in link.lower()}
    return links, page


def _etsy_direct(session: requests.Session, phrase: str) -> tuple[set[str], str]:
    response = session.get(
        "https://www.etsy.com/search",
        params={"q": phrase, "explicit": "1"},
        timeout=15,
    )
    response.raise_for_status()
    page = response.text
    links = set(re.findall(r"https://www\.etsy\.com/listing/[0-9]+[^\"' <]*", page, flags=re.I))
    for listing_id in re.findall(r"/listing/([0-9]+)", page):
        links.add(f"https://www.etsy.com/listing/{listing_id}")
    return links, page


def _gumroad_direct(session: requests.Session, phrase: str) -> tuple[set[str], str]:
    response = session.get(
        "https://gumroad.com/discover",
        params={"query": phrase},
        timeout=15,
    )
    response.raise_for_status()
    page = response.text
    links = {
        link for link in _hrefs(page)
        if "gumroad.com" in link.lower() and any(marker in link.lower() for marker in ["/l/", "/a/", "/discover?"])
    }
    return links, page


def research_market_data(phrase: str, config: dict) -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    errors: List[str] = []
    queries: List[str] = []
    prices: List[float] = []
    hits: Dict[str, int] = {"etsy": 0, "gumroad": 0}

    # Etsy: direct marketplace search first, then a broad indexed-web fallback.
    etsy_links: set[str] = set()
    try:
        queries.append(f"Etsy direct search: {phrase}")
        direct_links, page = _etsy_direct(session, phrase)
        etsy_links |= direct_links
        prices.extend(_usd_prices(page))
    except Exception as exc:
        errors.append(f"Etsy direct search failed: {exc}")
    time.sleep(float(config.get("market_research_delay_seconds", 0.25)))

    try:
        queries.append(f"DuckDuckGo: site:etsy.com/listing {phrase}")
        search_links, page = _ddg_search(session, phrase, "etsy.com/listing")
        etsy_links |= search_links
        prices.extend(_usd_prices(page))
    except Exception as exc:
        errors.append(f"Etsy indexed search failed: {exc}")
    try:
        queries.append(f"Bing: site:etsy.com/listing {phrase}")
        search_links, page = _bing_search(session, phrase, "etsy.com/listing")
        etsy_links |= search_links
        prices.extend(_usd_prices(page))
    except Exception as exc:
        errors.append(f"Etsy Bing search failed: {exc}")
    hits["etsy"] = min(40, len(etsy_links))
    time.sleep(float(config.get("market_research_delay_seconds", 0.25)))

    # Gumroad: direct discover search plus indexed-web fallback.
    gumroad_links: set[str] = set()
    try:
        queries.append(f"Gumroad discover search: {phrase}")
        direct_links, page = _gumroad_direct(session, phrase)
        gumroad_links |= direct_links
        prices.extend(_usd_prices(page))
    except Exception as exc:
        errors.append(f"Gumroad direct search failed: {exc}")
    time.sleep(float(config.get("market_research_delay_seconds", 0.25)))

    try:
        queries.append(f"DuckDuckGo: site:gumroad.com {phrase}")
        search_links, page = _ddg_search(session, phrase, "gumroad.com")
        gumroad_links |= search_links
        prices.extend(_usd_prices(page))
    except Exception as exc:
        errors.append(f"Gumroad indexed search failed: {exc}")
    try:
        queries.append(f"Bing: site:gumroad.com {phrase}")
        search_links, page = _bing_search(session, phrase, "gumroad.com")
        gumroad_links |= search_links
        prices.extend(_usd_prices(page))
    except Exception as exc:
        errors.append(f"Gumroad Bing search failed: {exc}")
    hits["gumroad"] = min(40, len(gumroad_links))

    unique_prices = sorted(set(prices))[:40]
    median = round(statistics.median(unique_prices), 2) if unique_prices else None
    return {
        "platform_hits": hits,
        "sampled_prices_usd": unique_prices,
        "median_price_usd": median,
        "evidence_queries": queries,
        "errors": errors,
    }
