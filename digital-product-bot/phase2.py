from __future__ import annotations

import csv
import html
import json
import re
import statistics
import sys
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from urllib.parse import quote_plus, unquote

import requests
from PIL import Image, ImageDraw, ImageFont

import bot

USER_AGENT = "RCS-Digital-Product-Scout/2.0 (commercial research; respectful rate limits)"
FORMAT_WORDS = {
    "template", "templates", "spreadsheet", "spreadsheets", "excel", "google", "sheets",
    "sheet", "download", "digital", "printable", "editable", "pdf", "xlsx", "csv", "best", "free",
}
STOP_WORDS = {"a", "an", "and", "for", "of", "the", "to", "with", "in", "on", "my", "your"}


@dataclass
class MarketEvidence:
    platform_hits: Dict[str, int]
    sampled_prices_usd: List[float]
    median_price_usd: float | None
    evidence_queries: List[str]
    errors: List[str]


@dataclass
class Decision:
    phrase: str
    base_score: int
    commercial_score: int
    decision: str
    kind: str
    signal_count: int
    sources: List[str]
    market_evidence: MarketEvidence
    reasons: List[str]


def clean_tokens(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in FORMAT_WORDS and w not in STOP_WORDS and len(w) > 1]


def canonical_key(text: str) -> str:
    tokens = clean_tokens(text)
    # Word order is not commercially meaningful for our duplicate families.
    return " ".join(sorted(dict.fromkeys(tokens)))


def similarity(a: str, b: str) -> float:
    sa, sb = set(clean_tokens(a)), set(clean_tokens(b))
    if not sa or not sb:
        return 0.0
    intersection = len(sa & sb)
    union = len(sa | sb)
    jaccard = intersection / union
    containment = intersection / min(len(sa), len(sb))
    return max(jaccard, containment * 0.92)


def cluster_opportunities(opportunities: Sequence[bot.Opportunity], threshold: float = 0.78) -> List[bot.Opportunity]:
    """Keep one representative from each close commercial family."""
    kept: List[bot.Opportunity] = []
    for candidate in sorted(opportunities, key=lambda x: (x.score, x.signal_count), reverse=True):
        duplicate_index = None
        for i, existing in enumerate(kept):
            if canonical_key(candidate.phrase) == canonical_key(existing.phrase) or similarity(candidate.phrase, existing.phrase) >= threshold:
                duplicate_index = i
                break
        if duplicate_index is None:
            kept.append(candidate)
        else:
            current = kept[duplicate_index]
            # Prefer the strongest evidence; break ties in favour of a concise phrase.
            if (candidate.score, candidate.signal_count, -len(candidate.phrase)) > (
                current.score, current.signal_count, -len(current.phrase)
            ):
                kept[duplicate_index] = candidate
    return sorted(kept, key=lambda x: (x.score, x.signal_count), reverse=True)


def _extract_redirect_target(href: str) -> str:
    href = html.unescape(href)
    if "uddg=" in href:
        match = re.search(r"uddg=([^&]+)", href)
        if match:
            return unquote(match.group(1))
    return href


def _search_duckduckgo(session: requests.Session, query: str) -> Tuple[List[str], str]:
    url = "https://html.duckduckgo.com/html/"
    response = session.get(url, params={"q": query}, timeout=15)
    response.raise_for_status()
    page = response.text
    hrefs = [_extract_redirect_target(x) for x in re.findall(r'href="([^"]+)"', page)]
    return hrefs, page


def _price_samples(text: str) -> List[float]:
    values = []
    for match in re.findall(r"\$\s?([0-9]{1,3}(?:\.[0-9]{1,2})?)", text):
        try:
            value = float(match)
        except ValueError:
            continue
        if 1.0 <= value <= 250.0:
            values.append(round(value, 2))
    # Snippets often repeat values in hidden/visible variants; collapse duplicates.
    return sorted(set(values))[:20]


def research_market(phrase: str, config: dict) -> MarketEvidence:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
    platforms = config.get("marketplace_domains", {"etsy": "etsy.com/listing", "gumroad": "gumroad.com"})
    hits: Dict[str, int] = {}
    prices: List[float] = []
    queries: List[str] = []
    errors: List[str] = []

    for platform, domain in platforms.items():
        query = f'"{phrase}" site:{domain}'
        queries.append(query)
        try:
            links, page = _search_duckduckgo(session, query)
            relevant = {
                link for link in links
                if domain.lower() in link.lower() and not any(x in link.lower() for x in ["privacy", "help", "terms"])
            }
            hits[platform] = min(25, len(relevant))
            prices.extend(_price_samples(page))
        except Exception as exc:
            hits[platform] = 0
            errors.append(f"{platform} research failed: {exc}")
        time.sleep(float(config.get("market_research_delay_seconds", 0.25)))

    unique_prices = sorted(set(prices))[:30]
    median = round(statistics.median(unique_prices), 2) if unique_prices else None
    return MarketEvidence(
        platform_hits=hits,
        sampled_prices_usd=unique_prices,
        median_price_usd=median,
        evidence_queries=queries,
        errors=errors,
    )


def classify(opportunity: bot.Opportunity, evidence: MarketEvidence, config: dict) -> Decision:
    total_hits = sum(evidence.platform_hits.values())
    if total_hits == 0:
        competition_points = 8  # Either an opening or weak evidence: useful, but not a full green light.
        competition_note = "No marketplace result links observed in the research sample."
    elif total_hits <= 3:
        competition_points = 18
        competition_note = "Low observed competition in the research sample."
    elif total_hits <= 8:
        competition_points = 14
        competition_note = "Moderate observed competition in the research sample."
    elif total_hits <= 15:
        competition_points = 8
        competition_note = "Meaningful competition observed in the research sample."
    else:
        competition_points = 3
        competition_note = "High observed competition in the research sample."

    median = evidence.median_price_usd
    if median is None:
        price_points = 4
        price_note = "No reliable price snippet was observed; using configured price bands."
    elif 7 <= median <= 45:
        price_points = 10
        price_note = f"Observed median price sample around ${median:.2f}."
    elif 4 <= median <= 70:
        price_points = 7
        price_note = f"Observed price sample is commercially usable but less ideal (median ${median:.2f})."
    else:
        price_points = 3
        price_note = f"Observed price sample sits outside the preferred range (median ${median:.2f})."

    phrase_tokens = clean_tokens(opportunity.phrase)
    niche_points = min(10, max(3, len(phrase_tokens) * 2))
    base_points = round(opportunity.score * 0.62)
    computed_commercial = min(100, base_points + competition_points + price_points + niche_points)
    has_market_evidence = total_hits > 0 or median is not None
    # If marketplace evidence is unavailable, do not punish the opportunity for a
    # technical research gap. Use the demand/build score as the candidate score,
    # and surface the lack of market confirmation separately.
    commercial_score = computed_commercial if has_market_evidence else opportunity.score

    create_threshold = int(config.get("create_threshold", 70))
    watch_threshold = int(config.get("watch_threshold", 58))
    minimum_base = int(config.get("minimum_score", 62))

    if commercial_score >= create_threshold and opportunity.score >= minimum_base:
        decision = "CREATE"
    elif commercial_score >= watch_threshold:
        decision = "WATCH"
    else:
        decision = "REJECT"

    reasons = [
        f"Demand/buildability base score: {opportunity.score}/100.",
        competition_note,
        price_note,
        f"Commercial specificity contribution: {niche_points}/10.",
        (
            "Marketplace evidence confirmed; composite commercial score applied."
            if has_market_evidence
            else "Marketplace evidence remains unverified; candidate score falls back to demand/build strength."
        ),
    ]
    return Decision(
        phrase=opportunity.phrase,
        base_score=opportunity.score,
        commercial_score=commercial_score,
        decision=decision,
        kind=opportunity.kind,
        signal_count=opportunity.signal_count,
        sources=opportunity.sources,
        market_evidence=evidence,
        reasons=reasons,
    )


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_preview(path: Path, decision: Decision, headers: Sequence[str]) -> None:
    image = Image.new("RGB", (1200, 900), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(52, bold=True)
    subtitle_font = _font(25)
    badge_font = _font(23, bold=True)
    body_font = _font(24)
    small_font = _font(18)

    draw.rounded_rectangle((60, 55, 1140, 845), radius=28, outline="black", width=3)
    draw.rounded_rectangle((90, 90, 330, 145), radius=18, outline="black", width=2)
    draw.text((120, 103), "EDITABLE DIGITAL TOOL", font=badge_font, fill="black")

    y = 190
    for line in _wrap(draw, bot.title_case_phrase(decision.phrase), title_font, 970)[:3]:
        draw.text((100, y), line, font=title_font, fill="black")
        y += 64

    draw.text((100, y + 8), "Excel workbook + starter CSV + practical setup guide", font=subtitle_font, fill="black")
    y += 78

    # Simple visual table preview.
    left, top, right = 100, y, 1100
    col_count = min(5, len(headers))
    col_width = (right - left) / max(1, col_count)
    row_height = 58
    for row in range(4):
        row_top = top + row * row_height
        draw.rectangle((left, row_top, right, row_top + row_height), outline="black", width=2)
        for col in range(1, col_count):
            x = left + col * col_width
            draw.line((x, row_top, x, row_top + row_height), fill="black", width=2)
    for col, header in enumerate(headers[:col_count]):
        x = int(left + col * col_width + 10)
        draw.text((x, top + 17), header[:18], font=small_font, fill="black")

    bottom_y = top + 4 * row_height + 34
    draw.text((100, bottom_y), f"Commercial score: {decision.commercial_score}/100   |   Review status: AWAITING APPROVAL", font=body_font, fill="black")
    draw.text((100, bottom_y + 48), "Preview generated automatically. Final listing artwork can be refined after approval.", font=small_font, fill="black")
    image.save(path, format="PNG", optimize=True)


def _rewrite_zip(folder: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(folder.iterdir()):
            if item.is_file():
                zf.write(item, arcname=f"{folder.name}/{item.name}")


def enrich_product(decision: Decision, product_root: Path, config: dict) -> str:
    opportunity = bot.Opportunity(
        phrase=decision.phrase,
        score=decision.base_score,
        signal_count=decision.signal_count,
        sources=decision.sources,
        kind=decision.kind,
        reason="Phase 2 selected after market research",
    )
    zip_path = bot.create_product(opportunity, product_root, config)
    folder = product_root / bot.slugify(decision.phrase)
    headers = bot.headers_for_phrase(decision.phrase)

    market_payload = {
        "commercial_score": decision.commercial_score,
        "decision": decision.decision,
        "market_evidence": asdict(decision.market_evidence),
        "reasons": decision.reasons,
        "competition_metric_note": "Competition is a search-result sample/proxy, not a complete marketplace listing count.",
    }
    (folder / "market-research.json").write_text(json.dumps(market_payload, indent=2), encoding="utf-8")
    create_preview(folder / "listing-preview.png", decision, headers)

    listing_path = folder / "listing.json"
    listing = json.loads(listing_path.read_text(encoding="utf-8"))
    listing["phase2"] = {
        "commercial_score": decision.commercial_score,
        "decision": decision.decision,
        "market_median_price_usd": decision.market_evidence.median_price_usd,
        "marketplace_result_proxy": decision.market_evidence.platform_hits,
    }
    if decision.market_evidence.median_price_usd is not None:
        configured = float(listing["suggested_price"]["usd"])
        market = decision.market_evidence.median_price_usd
        listing["suggested_price"]["phase2_usd"] = round((configured * 0.55) + (market * 0.45), 2)
    listing_path.write_text(json.dumps(listing, indent=2), encoding="utf-8")

    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["phase"] = 2
    manifest["decision"] = decision.decision
    manifest["commercial_score"] = decision.commercial_score
    manifest["files"] = sorted(p.name for p in folder.iterdir() if p.is_file())
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    _rewrite_zip(folder, zip_path)
    return str(zip_path)


def write_review_queue(path: Path, decisions: Sequence[Decision]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Decision", "Commercial Score", "Base Score", "Product Idea", "Type",
            "Etsy Proxy Hits", "Gumroad Proxy Hits", "Median Sample Price USD", "Signals"
        ])
        for d in decisions:
            writer.writerow([
                d.decision,
                d.commercial_score,
                d.base_score,
                d.phrase,
                d.kind,
                d.market_evidence.platform_hits.get("etsy", 0),
                d.market_evidence.platform_hits.get("gumroad", 0),
                d.market_evidence.median_price_usd or "",
                d.signal_count,
            ])


def main() -> int:
    config = bot.load_config()
    run_date = datetime.now(timezone.utc).date().isoformat()
    output_base = Path(__import__("os").environ.get("OUTPUT_DIR", str(bot.BASE_DIR / "output")))
    run_root = output_base / run_date
    products_root = run_root / "products"
    products_root.mkdir(parents=True, exist_ok=True)

    signals, source_errors = bot.discover_signals(config)
    raw = bot.build_opportunities(signals, config)
    clustered = cluster_opportunities(raw, float(config.get("duplicate_similarity_threshold", 0.78)))
    research_limit = int(config.get("phase2_research_candidates", 12))

    decisions: List[Decision] = []
    for opportunity in clustered[:research_limit]:
        evidence = research_market(opportunity.phrase, config)
        decisions.append(classify(opportunity, evidence, config))

    decisions.sort(key=lambda d: d.commercial_score, reverse=True)
    from product_format import factory_readiness

    create_candidates = [d for d in decisions if d.decision == "CREATE"]
    confirmed_create = [
        d for d in create_candidates
        if (sum(d.market_evidence.platform_hits.values()) > 0 or d.market_evidence.median_price_usd is not None)
    ]
    factory_ready = [d for d in confirmed_create if factory_readiness(d.phrase)[0]]
    max_products = int(config.get("max_products_per_run", 3))
    selected = factory_ready[:max_products]

    packages: List[str] = []
    for decision in selected:
        packages.append(str(Path(enrich_product(decision, products_root, config)).relative_to(run_root)))

    write_review_queue(run_root / "review_queue.csv", decisions)
    report = {
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": 2,
        "status": "COMPLETE",
        "publishing_performed": False,
        "signals_seen": len(signals),
        "raw_opportunities": len(raw),
        "after_duplicate_clustering": len(clustered),
        "researched": len(decisions),
        "decision_counts": {
            "CREATE": sum(d.decision == "CREATE" for d in decisions),
            "WATCH": sum(d.decision == "WATCH" for d in decisions),
            "REJECT": sum(d.decision == "REJECT" for d in decisions),
        },
        "selected_for_creation": [asdict(d) for d in selected],
        "review_queue": [asdict(d) for d in decisions],
        "packages": packages,
        "source_errors": source_errors,
        "notes": [
            "Marketplace competition uses sampled public search-result links as a proxy, not an exhaustive listing count.",
            "Products remain AWAITING_APPROVAL and are not published automatically.",
        ],
    }
    (run_root / "phase2_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
