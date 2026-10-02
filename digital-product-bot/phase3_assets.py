from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw

import bot
import phase2

BASE_DIR = Path(__file__).resolve().parent
BRAND_CONFIG = BASE_DIR / "brand_config.json"


def load_brand() -> dict:
    return json.loads(BRAND_CONFIG.read_text(encoding="utf-8"))


def _rgb(value: str) -> str:
    return value


def _canvas(brand: dict):
    width = int(brand["style"].get("image_width", 1600))
    height = int(brand["style"].get("image_height", 1200))
    img = Image.new("RGB", (width, height), _rgb(brand["palette"]["background"]))
    draw = ImageDraw.Draw(img)
    return img, draw


def _font(size: int, bold: bool = False):
    return phase2._font(size, bold=bold)


def _wrapped(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, max_width: int, font, fill: str, gap: int = 8, max_lines: int | None = None) -> int:
    words = text.split()
    lines: list[str] = []
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
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += getattr(font, "size", 32) + gap
    return y


def _brand_header(draw: ImageDraw.ImageDraw, brand: dict, label: str) -> None:
    primary = _rgb(brand["palette"]["primary"])
    accent = _rgb(brand["palette"]["accent"])
    small = _font(24, bold=True)
    draw.rounded_rectangle((90, 70, 450, 126), radius=18, fill=primary)
    draw.text((115, 86), brand["brand_name"].upper(), font=small, fill="white")
    draw.rounded_rectangle((1280, 70, 1500, 126), radius=18, fill=accent)
    draw.text((1305, 86), label.upper()[:18], font=small, fill=primary)


def _badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, brand: dict, width: int | None = None) -> int:
    font = _font(24, bold=True)
    primary = _rgb(brand["palette"]["primary"])
    muted = _rgb(brand["palette"]["muted"])
    if width is None:
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0] + 50
    draw.rounded_rectangle((x, y, x + width, y + 56), radius=18, fill=muted)
    draw.text((x + 24, y + 14), text, font=font, fill=primary)
    return x + width


def _spreadsheet_screen(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], headers: Sequence[str], brand: dict) -> None:
    left, top, right, bottom = box
    primary = _rgb(brand["palette"]["primary"])
    surface = _rgb(brand["palette"]["surface"])
    soft = _rgb(brand["palette"]["soft"])
    accent = _rgb(brand["palette"]["accent"])
    small = _font(19, bold=True)
    tiny = _font(16)

    draw.rounded_rectangle(box, radius=22, fill=surface, outline=primary, width=3)
    toolbar_h = 62
    draw.rounded_rectangle((left, top, right, top + toolbar_h), radius=22, fill=primary)
    draw.rectangle((left, top + 34, right, top + toolbar_h), fill=primary)
    draw.ellipse((left + 20, top + 21, left + 36, top + 37), fill=accent)
    draw.ellipse((left + 46, top + 21, left + 62, top + 37), fill=soft)
    draw.ellipse((left + 72, top + 21, left + 88, top + 37), fill=surface)
    draw.text((left + 118, top + 19), "Working Spreadsheet", font=small, fill="white")

    table_top = top + toolbar_h + 22
    table_left = left + 25
    table_right = right - 25
    table_bottom = bottom - 25
    cols = min(5, max(3, len(headers)))
    rows = 7
    col_w = (table_right - table_left) / cols
    row_h = (table_bottom - table_top) / rows

    draw.rectangle((table_left, table_top, table_right, table_top + row_h), fill=soft)
    for r in range(rows + 1):
        y = table_top + r * row_h
        draw.line((table_left, y, table_right, y), fill=primary, width=1)
    for c in range(cols + 1):
        x = table_left + c * col_w
        draw.line((x, table_top, x, table_bottom), fill=primary, width=1)

    for idx, header in enumerate(headers[:cols]):
        x = int(table_left + idx * col_w + 12)
        draw.text((x, int(table_top + 15)), header[:15], font=tiny, fill=primary)

    for r in range(1, rows):
        for c in range(cols):
            if (r + c) % 4 == 0:
                x1 = table_left + c * col_w + 10
                y1 = table_top + r * row_h + 12
                x2 = table_left + (c + 1) * col_w - 10
                y2 = y1 + 12
                draw.rounded_rectangle((x1, y1, x2, y2), radius=5, fill=accent if c == 0 else soft)


def _laptop_mockup(draw: ImageDraw.ImageDraw, center_x: int, top: int, width: int, headers: Sequence[str], brand: dict) -> None:
    primary = _rgb(brand["palette"]["primary"])
    surface = _rgb(brand["palette"]["surface"])
    screen_h = int(width * 0.59)
    left = center_x - width // 2
    right = center_x + width // 2
    draw.rounded_rectangle((left, top, right, top + screen_h), radius=30, fill=primary)
    bezel = 24
    _spreadsheet_screen(draw, (left + bezel, top + bezel, right - bezel, top + screen_h - bezel), headers, brand)

    base_y = top + screen_h + 8
    base_left = left - 70
    base_right = right + 70
    draw.polygon(
        [(base_left, base_y), (base_right, base_y), (base_right - 60, base_y + 70), (base_left + 60, base_y + 70)],
        fill=primary,
    )
    draw.rounded_rectangle((center_x - 120, base_y + 15, center_x + 120, base_y + 32), radius=8, fill=surface)


def _card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], heading: str, body: str, brand: dict, number: str | None = None) -> None:
    primary = _rgb(brand["palette"]["primary"])
    surface = _rgb(brand["palette"]["surface"])
    accent = _rgb(brand["palette"]["accent"])
    draw.rounded_rectangle(box, radius=28, fill=surface, outline=primary, width=2)
    x1, y1, x2, y2 = box
    if number:
        draw.ellipse((x1 + 30, y1 + 28, x1 + 90, y1 + 88), fill=accent)
        num_font = _font(26, bold=True)
        draw.text((x1 + 50, y1 + 42), number, font=num_font, fill=primary)
        text_x = x1 + 115
    else:
        text_x = x1 + 35
    head_font = _font(27, bold=True)
    body_font = _font(22)
    draw.text((text_x, y1 + 34), heading, font=head_font, fill=primary)
    _wrapped(draw, body, text_x, y1 + 82, x2 - text_x - 35, body_font, primary, gap=5, max_lines=3)


def create_listing_images(folder: Path, decision, listing: dict, brand: dict | None = None) -> list[str]:
    brand = brand or load_brand()
    primary = _rgb(brand["palette"]["primary"])
    accent = _rgb(brand["palette"]["accent"])
    surface = _rgb(brand["palette"]["surface"])
    soft = _rgb(brand["palette"]["soft"])
    heading = _font(52, bold=True)
    body = _font(30)
    small = _font(23)
    title = listing.get("display_name") or bot.title_case_phrase(decision.phrase)
    headers = bot.headers_for_phrase(decision.phrase)

    assets: list[str] = []

    # 1. Hero with laptop mock-up.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "Editable")
    title_bottom = _wrapped(draw, title, 100, 185, 700, _font(66, bold=True), primary, gap=10, max_lines=4)
    subtitle_y = max(455, title_bottom + 24)
    subtitle_bottom = _wrapped(
        draw,
        "A practical digital system you can edit and reuse.",
        105,
        subtitle_y,
        610,
        body,
        primary,
        gap=7,
        max_lines=2,
    )
    badge_y = min(625, subtitle_bottom + 22)
    x = 105
    for badge in brand.get("badges", []):
        x = _badge(draw, x, badge_y, badge, brand) + 18
    _laptop_mockup(draw, 1150, 255, 660, headers, brand)
    draw.rounded_rectangle((100, 720, 780, 1040), radius=30, fill=surface)
    draw.text((140, 765), "INSTANT DIGITAL DOWNLOAD", font=_font(29, bold=True), fill=accent)
    draw.text((140, 830), "Workbook + CSV + Guide", font=_font(40, bold=True), fill=primary)
    _wrapped(draw, "Designed to turn a repeated task into a simple, organised workflow.", 140, 900, 580, small, primary, gap=7)
    path = folder / "listing-image-01-hero.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    # 2. What's included.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "Included")
    draw.text((100, 180), "Everything you need to get started", font=heading, fill=primary)
    cards = [
        ("Excel workbook", "Editable working sheets with organised fields and a quick dashboard."),
        ("Starter CSV", "A lightweight version for importing, sharing or adapting elsewhere."),
        ("Buyer guide", "Clear setup steps so the template is useful from the first session."),
        ("Reusable master", "Keep one clean copy and duplicate it whenever you need a fresh workflow."),
    ]
    positions = [(100, 300, 760, 560), (840, 300, 1500, 560), (100, 630, 760, 890), (840, 630, 1500, 890)]
    for box, item in zip(positions, cards):
        _card(draw, box, item[0], item[1], brand)
    draw.text((105, 1010), "No physical item is shipped.", font=body, fill=primary)
    path = folder / "listing-image-02-included.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    # 3. Inside look.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "Inside Look")
    draw.text((100, 175), "See the workflow before you buy", font=heading, fill=primary)
    _spreadsheet_screen(draw, (100, 290, 1500, 900), headers, brand)
    draw.text((105, 975), "Editable columns • Filter-ready table • Dashboard-ready structure", font=body, fill=primary)
    path = folder / "listing-image-03-inside.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    # 4. Features.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "Features")
    draw.text((100, 175), "Built for practical everyday use", font=heading, fill=primary)
    features = [
        ("Editable", "Change headings, categories and workflow fields to fit your own process."),
        ("Reusable", "Keep a clean master and use it again for future projects or periods."),
        ("Simple", "No complicated setup or specialist software workflow is required."),
        ("Organised", "Structured fields make filtering, reviewing and handover easier."),
        ("Actionable", "Built around what needs to be tracked, completed or reviewed."),
        ("Flexible", "Suitable for both personal administration and small-business workflows."),
    ]
    for i, (head, text_value) in enumerate(features):
        row, col = divmod(i, 2)
        x1 = 100 + col * 740
        y1 = 300 + row * 260
        _card(draw, (x1, y1, x1 + 660, y1 + 210), head, text_value, brand)
    path = folder / "listing-image-04-features.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    # 5. How it works.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "How It Works")
    draw.text((100, 175), "From download to useful in four steps", font=heading, fill=primary)
    steps = [
        ("Download", "Receive the digital files after purchase."),
        ("Customise", "Adjust labels and categories for your workflow."),
        ("Add records", "Start entering the information you need to manage."),
        ("Review & reuse", "Use the dashboard and duplicate the clean master as needed."),
    ]
    for i, (head, body_value) in enumerate(steps, start=1):
        y = 300 + (i - 1) * 205
        _card(draw, (130, y, 1470, y + 155), head, body_value, brand, number=str(i))
    path = folder / "listing-image-05-how-it-works.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    # 6. Best for.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "Best For")
    draw.text((100, 175), "A useful fit for organised people and teams", font=heading, fill=primary)
    audiences = [
        ("Small business", "Track repeatable admin without introducing another software subscription."),
        ("Freelancers", "Create a consistent process for work you manage repeatedly."),
        ("Creators", "Keep planning and operational information in one editable system."),
        ("Personal admin", "Use a structured spreadsheet when a simple list is no longer enough."),
    ]
    positions = [(100, 310, 760, 555), (840, 310, 1500, 555), (100, 635, 760, 880), (840, 635, 1500, 880)]
    for box, item in zip(positions, audiences):
        _card(draw, box, item[0], item[1], brand)
    draw.rounded_rectangle((100, 965, 1500, 1070), radius=24, fill=accent)
    draw.text((150, 996), f"Commercial research score: {decision.commercial_score}/100", font=_font(31, bold=True), fill=primary)
    path = folder / "listing-image-06-best-for.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    # 7. Important notes / compatibility.
    img, draw = _canvas(brand)
    _brand_header(draw, brand, "Please Note")
    draw.text((100, 175), "Important before you purchase", font=heading, fill=primary)
    notes = [
        ("Digital product", "No physical item will be shipped."),
        ("Editable files", "The main product is supplied as an Excel workbook with supporting files."),
        ("General-use template", "This product is for productivity and organisation; it is not regulated professional advice."),
        ("Check compatibility", "Confirm that your software can open XLSX and CSV files before purchase."),
    ]
    for i, (head, body_value) in enumerate(notes, start=1):
        y = 300 + (i - 1) * 205
        _card(draw, (130, y, 1470, y + 155), head, body_value, brand, number=str(i))
    path = folder / "listing-image-07-important.png"
    img.save(path, "PNG", optimize=True)
    assets.append(path.name)

    return assets
