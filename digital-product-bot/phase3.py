from __future__ import annotations

import base64
import json
import os
import re
import textwrap
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw

import bot
import etsy_adapter
import phase2

MARKER_RE = re.compile(r"<!--\s*DIGITAL_PRODUCT_QUEUE:([A-Za-z0-9_=-]+)\s*-->")
COMMAND_RE = re.compile(r"^\s*/(approve|reject|publish)\s+([a-z0-9-]+)\s*$", re.I)


def decode_queue(issue_body: str) -> list[dict]:
    match = MARKER_RE.search(issue_body or "")
    if not match:
        raise ValueError("Approval dashboard queue payload is missing")
    raw = base64.urlsafe_b64decode(match.group(1).encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def decision_from_row(row: dict) -> phase2.Decision:
    market = row["market_evidence"]
    evidence = phase2.MarketEvidence(
        platform_hits=dict(market.get("platform_hits", {})),
        sampled_prices_usd=list(market.get("sampled_prices_usd", [])),
        median_price_usd=market.get("median_price_usd"),
        evidence_queries=list(market.get("evidence_queries", [])),
        errors=list(market.get("errors", [])),
    )
    return phase2.Decision(
        phrase=row["phrase"],
        base_score=int(row["base_score"]),
        commercial_score=int(row["commercial_score"]),
        decision=row["decision"],
        kind=row["kind"],
        signal_count=int(row.get("signal_count", 1)),
        sources=list(row.get("sources", [])),
        market_evidence=evidence,
        reasons=list(row.get("reasons", [])),
    )


def post_comment(repo: str, issue_number: int, body: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(body)
        return
    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"body": body},
        timeout=20,
    )
    response.raise_for_status()


def _draw_wrapped(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], font, width: int, line_gap: int = 8) -> int:
    x, y = xy
    words = text.split()
    line = ""
    lines = []
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    for value in lines:
        draw.text((x, y), value, font=font, fill="black")
        y += font.size + line_gap if hasattr(font, "size") else 34
    return y


def create_listing_images(folder: Path, decision: phase2.Decision, listing: dict) -> list[str]:
    assets = []

    def canvas():
        img = Image.new("RGB", (1600, 1200), "white")
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((70, 70, 1530, 1130), radius=30, outline="black", width=4)
        return img, d

    title_font = phase2._font(70, bold=True)
    heading_font = phase2._font(44, bold=True)
    body_font = phase2._font(34)
    small_font = phase2._font(25)

    img, draw = canvas()
    draw.text((120, 120), "EDITABLE DIGITAL PRODUCT", font=small_font, fill="black")
    y = _draw_wrapped(draw, bot.title_case_phrase(decision.phrase), (120, 230), title_font, 1320, 14)
    draw.text((120, y + 45), f"{decision.kind.capitalize()} + workbook + guide", font=heading_font, fill="black")
    draw.text((120, 1000), "Instant digital download • Easy to customise", font=body_font, fill="black")
    path = folder / "listing-image-01-hero.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    img, draw = canvas()
    draw.text((120, 120), "WHAT'S INCLUDED", font=heading_font, fill="black")
    included = [
        "Editable Excel workbook",
        "Starter CSV",
        "Practical buyer guide",
        "Quick dashboard / working table",
        "Clean master file for reuse",
    ]
    y = 260
    for item in included:
        draw.text((150, y), "• " + item, font=body_font, fill="black")
        y += 105
    draw.text((120, 1000), "No subscription required for the supplied files.", font=small_font, fill="black")
    path = folder / "listing-image-02-included.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    img, draw = canvas()
    draw.text((120, 120), "HOW IT WORKS", font=heading_font, fill="black")
    steps = ["1. Download", "2. Open & customise", "3. Add your records", "4. Review your dashboard", "5. Reuse the clean master"]
    y = 270
    for step in steps:
        draw.rounded_rectangle((130, y - 18, 1470, y + 62), radius=15, outline="black", width=2)
        draw.text((170, y), step, font=body_font, fill="black")
        y += 145
    path = folder / "listing-image-03-workflow.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    img, draw = canvas()
    draw.text((120, 120), "BUILT FOR PRACTICAL USE", font=heading_font, fill="black")
    points = [
        f"Commercial research score: {decision.commercial_score}/100",
        "Editable columns and workflow",
        "General productivity use — no regulated advice",
        "Designed for small-business and personal workflows",
    ]
    y = 270
    for point in points:
        y = _draw_wrapped(draw, "✓ " + point, (150, y), body_font, 1280, 15) + 45
    draw.text((120, 1000), "Review the listing description for compatibility before purchase.", font=small_font, fill="black")
    path = folder / "listing-image-04-features.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    return assets


def etsy_tags(phrase: str, kind: str) -> list[str]:
    candidates = [
        phrase,
        f"{kind} template",
        "excel template",
        "digital download",
        "business planner",
        "productivity",
        "editable tracker",
        "small business",
    ]
    tags = []
    for value in candidates:
        clean = re.sub(r"[^a-z0-9 ]+", "", value.lower()).strip()
        if len(clean) > 20:
            words = clean.split()
            clean = " ".join(words[:3])[:20].strip()
        if clean and clean not in tags:
            tags.append(clean)
    return tags[:13]


def finalise(decision: phase2.Decision, output_root: Path) -> tuple[Path, Path, dict]:
    config = bot.load_config()
    product_root = output_root / "approved-products"
    product_root.mkdir(parents=True, exist_ok=True)

    zip_path = Path(phase2.enrich_product(decision, product_root, config))
    folder = product_root / bot.slugify(decision.phrase)
    listing_path = folder / "listing.json"
    base_listing = json.loads(listing_path.read_text(encoding="utf-8"))

    price = base_listing.get("suggested_price", {}).get("phase2_usd") or base_listing.get("suggested_price", {}).get("usd")
    title = base_listing["title"][:140]
    description = "\n\n".join([
        base_listing["long_description"],
        "WHAT YOU RECEIVE\n• Editable Excel workbook\n• Starter CSV\n• Practical buyer guide\n• Reusable clean master",
        "HOW TO USE IT\nDownload the files, customise the headings and categories, enter your records, and review the dashboard as part of your regular workflow.",
        "PLEASE NOTE\nThis is a digital download. No physical item is shipped. It is a general productivity template and is not legal, tax, financial, medical, or other regulated professional advice.",
    ])
    marketplace = {
        "title": title,
        "description": description,
        "price_usd": round(float(price), 2),
        "etsy_tags": etsy_tags(decision.phrase, decision.kind),
        "type": "download",
        "quantity": 999,
        "who_made": "i_did",
        "when_made": "2020_2026",
        "commercial_score": decision.commercial_score,
        "source_phrase": decision.phrase,
        "approval_status": "APPROVED_NOT_PUBLISHED",
    }
    images = create_listing_images(folder, decision, marketplace)
    marketplace["listing_images"] = images
    (folder / "marketplace-listing.json").write_text(json.dumps(marketplace, indent=2), encoding="utf-8")

    status_path = folder / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update({
        "status": "APPROVED_NOT_PUBLISHED",
        "approved_by": os.environ.get("GITHUB_ACTOR", "repository-owner"),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "publishing_enabled": False,
    })
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    phase2._rewrite_zip(folder, zip_path)
    return folder, zip_path, marketplace


def main() -> int:
    event_path = Path(os.environ["GITHUB_EVENT_PATH"])
    event = json.loads(event_path.read_text(encoding="utf-8"))
    comment = event.get("comment", {}).get("body", "")
    issue_body = event.get("issue", {}).get("body", "")
    issue_number = int(event.get("issue", {}).get("number", 0))
    repo = os.environ["GITHUB_REPOSITORY"]

    match = COMMAND_RE.match(comment)
    if not match:
        print("No supported command found")
        return 0
    action, slug = match.group(1).lower(), match.group(2).lower()

    queue = decode_queue(issue_body)
    row = next((item for item in queue if item.get("slug") == slug), None)
    if not row:
        post_comment(repo, issue_number, f"Could not find `{slug}` in the current approval queue.")
        return 0

    if action == "reject":
        out = Path(os.environ.get("PHASE3_OUTPUT_DIR", "phase3-output")) / "rejections"
        out.mkdir(parents=True, exist_ok=True)
        payload = {
            "slug": slug,
            "phrase": row["phrase"],
            "decision": "REJECTED_BY_OWNER",
            "actor": os.environ.get("GITHUB_ACTOR"),
            "at": datetime.now(timezone.utc).isoformat(),
        }
        (out / f"{slug}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        post_comment(repo, issue_number, f"Recorded **REJECT** for `{slug}`. No product was published.")
        return 0

    decision = decision_from_row(row)
    out = Path(os.environ.get("PHASE3_OUTPUT_DIR", "phase3-output"))
    folder, delivery_zip, marketplace = finalise(decision, out)

    if action == "approve":
        post_comment(
            repo,
            issue_number,
            f"Approved and finalised `{slug}`. The workflow generated the marketplace package and listing images. "
            "It remains offline with status **APPROVED_NOT_PUBLISHED**.",
        )
        return 0

    try:
        result = etsy_adapter.create_draft(folder, delivery_zip, marketplace)
    except etsy_adapter.EtsyConfigurationError as exc:
        missing = ", ".join(etsy_adapter.missing_settings())
        post_comment(
            repo,
            issue_number,
            f"`{slug}` is approved and finalised, but Etsy is not connected yet. Missing repository secrets: **{missing}**. "
            "No listing was created.",
        )
        print(str(exc))
        return 0

    status_path = folder / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status.update({
        "status": "ETSY_DRAFT_CREATED",
        "publishing_enabled": True,
        "etsy": result,
    })
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")
    phase2._rewrite_zip(folder, delivery_zip)

    post_comment(
        repo,
        issue_number,
        f"Created an Etsy **draft** for `{slug}` (listing ID **{result['listing_id']}**), uploaded the listing images and digital ZIP. "
        "The Etsy listing was **not activated**.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
