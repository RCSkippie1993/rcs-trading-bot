from __future__ import annotations

import re

import bot


def human_product_name(phrase: str) -> str:
    """Turn a search phrase into a natural customer-facing product name."""
    raw = re.sub(r"\s+", " ", phrase.lower()).strip()
    is_google_sheets = "google sheets" in raw
    is_excel = bool(re.search(r"\bexcel\b", raw))

    core = raw
    core = re.sub(r"\bgoogle sheets\b", " ", core)
    core = re.sub(r"\bexcel\b", " ", core)
    core = re.sub(r"\bfree\b", " ", core)
    core = re.sub(r"\btemplate\b", " ", core)
    core = re.sub(r"\s+", " ", core).strip(" -")

    base = bot.title_case_phrase(core or phrase)
    if is_google_sheets:
        return f"{base} – Google Sheets Template"
    if is_excel:
        return f"{base} – Excel Template"
    return f"{base} – Editable Template"


def _clean_tag(value: str) -> str:
    clean = re.sub(r"[^a-z0-9 ]+", "", value.lower()).strip()
    clean = re.sub(r"\s+", " ", clean)
    if len(clean) <= 20:
        return clean
    words = clean.split()
    while words and len(" ".join(words)) > 20:
        words.pop()
    return " ".join(words)[:20].strip()


def etsy_tags(phrase: str, kind: str) -> list[str]:
    tokens = [w for w in re.findall(r"[a-z0-9]+", phrase.lower()) if len(w) > 2]
    candidates = [
        phrase,
        f"{kind} template",
        "excel spreadsheet",
        "digital download",
        "editable template",
        "productivity tool",
        "small business",
        "business tracker",
        "planning template",
    ]
    if tokens:
        candidates.extend([
            f"{tokens[0]} template",
            f"{tokens[0]} tracker",
        ])
    if len(tokens) >= 2:
        candidates.append(f"{tokens[0]} {tokens[1]}")
    tags: list[str] = []
    for candidate in candidates:
        clean = _clean_tag(candidate)
        if clean and clean not in tags:
            tags.append(clean)
    return tags[:13]


def pricing(base_price: float, market_median: float | None, commercial_score: int) -> dict:
    anchor = float(base_price)
    if market_median and 3 <= float(market_median) <= 75:
        anchor = (anchor * 0.6) + (float(market_median) * 0.4)
    quality_factor = 1 + max(0, commercial_score - 70) * 0.005
    recommended = round(max(5.99, anchor * quality_factor), 2)
    floor = round(max(4.99, recommended * 0.78), 2)
    premium = round(max(recommended + 2.0, recommended * 1.24), 2)
    return {
        "floor_price_usd": floor,
        "recommended_price_usd": recommended,
        "premium_price_usd": premium,
        "pricing_note": "Use the recommended price for launch; the floor and premium figures are test boundaries, not guarantees of demand."
    }


def build_listing(decision, base_listing: dict, brand: dict) -> dict:
    display_name = human_product_name(decision.phrase)
    title = f"{display_name} | Digital Download"
    if len(title) > 140:
        title = display_name[:140]

    raw_price = (
        base_listing.get("suggested_price", {}).get("phase2_usd")
        or base_listing.get("suggested_price", {}).get("usd")
        or 9.99
    )
    prices = pricing(
        float(raw_price),
        decision.market_evidence.median_price_usd,
        decision.commercial_score,
    )

    hook = f"Use the {display_name} to turn repeated admin into a simple, repeatable workflow instead of rebuilding the same system from scratch."
    included = [
        "Editable Excel workbook",
        "Starter CSV",
        "Practical setup / buyer guide",
        "Reusable clean master",
        "Quick dashboard or working-table structure",
    ]
    benefits = [
        "Customise headings and categories",
        "Keep repeat work organised",
        "Use filters to review status and progress",
        "Duplicate the master whenever you need a fresh copy",
    ]

    description = "\n\n".join([
        hook,
        "WHAT YOU RECEIVE\n" + "\n".join(f"• {item}" for item in included),
        "WHY IT HELPS\n" + "\n".join(f"• {item}" for item in benefits),
        "HOW TO USE\n1. Download the files.\n2. Open the workbook and customise the labels.\n3. Add your information.\n4. Review the working table/dashboard as part of your normal routine.\n5. Keep the original as a clean master for reuse.",
        "PLEASE NOTE\nThis is a digital download; no physical item is shipped. This is a general productivity template and is not legal, tax, financial, medical, or other regulated professional advice. Please check that your software can open XLSX and CSV files.",
    ])

    return {
        "brand_name": brand["brand_name"],
        "display_name": display_name,
        "title": title,
        "short_hook": hook,
        "description": description,
        "price_usd": prices["recommended_price_usd"],
        "pricing": prices,
        "etsy_tags": etsy_tags(decision.phrase, decision.kind),
        "type": "download",
        "quantity": 999,
        "who_made": "i_did",
        "when_made": "2020_2026",
        "commercial_score": decision.commercial_score,
        "source_phrase": decision.phrase,
        "approval_status": "APPROVED_NOT_PUBLISHED",
        "included": included,
        "benefits": benefits,
    }
