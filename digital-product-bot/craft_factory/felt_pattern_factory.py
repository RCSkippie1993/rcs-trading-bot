from __future__ import annotations

import json
import math
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import svgwrite
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.pdfgen import canvas

import bot

MM = 72.0 / 25.4


@dataclass(frozen=True)
class FeltPiece:
    name: str
    points: tuple[tuple[float, float], ...]
    quantity: int
    material: str = "felt"
    note: str = ""


def design_for_phrase(phrase: str) -> str:
    text = phrase.lower()
    if any(term in text for term in ["dinosaur", "dino", "stegosaurus"]):
        return "dinosaur"
    if any(term in text for term in ["bunny", "rabbit"]):
        return "bunny"
    if "bear" in text:
        return "bear"
    return "fox" if "fox" in text or "woodland" in text else "fox"


def display_name(design: str) -> str:
    return {
        "fox": "Woodland Fox Felt Ornament",
        "bunny": "Bunny Felt Ornament",
        "dinosaur": "Friendly Dinosaur Felt Ornament",
        "bear": "Woodland Bear Felt Ornament",
    }[design]


def _scaled(points, sx=1.0, sy=1.0, dx=0.0, dy=0.0):
    return tuple((x * sx + dx, y * sy + dy) for x, y in points)


def pieces_for_design(design: str) -> list[FeltPiece]:
    if design == "bunny":
        body = (
            (43, 8), (51, 0), (57, 26), (66, 5), (73, 10), (69, 39),
            (83, 53), (86, 78), (76, 101), (58, 113), (37, 108), (22, 91),
            (18, 69), (25, 49), (39, 38),
        )
        belly = ((42, 60), (58, 55), (70, 67), (69, 87), (57, 98), (41, 94), (33, 82), (34, 69))
        return [FeltPiece("body", body, 2, note="Main ornament front/back."), FeltPiece("belly-applique", belly, 1, note="Optional contrast applique.")]

    if design == "dinosaur":
        body = (
            (8, 67), (20, 58), (28, 43), (37, 47), (43, 28), (51, 39),
            (61, 22), (68, 42), (78, 34), (83, 55), (105, 61), (117, 74),
            (109, 89), (88, 88), (77, 101), (65, 99), (58, 86), (43, 88),
            (35, 102), (24, 99), (22, 84), (10, 78),
        )
        belly = ((47, 62), (77, 58), (94, 69), (89, 82), (65, 86), (43, 79))
        return [FeltPiece("body", body, 2), FeltPiece("belly-applique", belly, 1)]

    if design == "bear":
        body = (
            (27, 24), (24, 12), (34, 5), (46, 13), (62, 11), (73, 3),
            (84, 11), (81, 26), (92, 42), (96, 67), (89, 91), (74, 108),
            (54, 114), (34, 107), (19, 92), (13, 71), (16, 47),
        )
        muzzle = ((35, 42), (61, 38), (76, 48), (75, 65), (60, 76), (40, 72), (29, 59))
        return [FeltPiece("body", body, 2), FeltPiece("muzzle-applique", muzzle, 1)]

    body = (
        (18, 34), (11, 16), (28, 23), (39, 6), (49, 27), (67, 29),
        (78, 12), (84, 35), (98, 49), (101, 72), (91, 94), (73, 106),
        (51, 108), (31, 99), (18, 82), (14, 59),
    )
    tail = ((83, 69), (103, 62), (119, 72), (114, 91), (99, 104), (80, 106), (68, 96), (76, 83))
    chest = ((39, 47), (62, 43), (77, 57), (73, 78), (59, 93), (40, 87), (29, 69))
    return [
        FeltPiece("body", body, 2),
        FeltPiece("tail", tail, 2, note="Layer or sandwich the tail between body pieces."),
        FeltPiece("chest-applique", chest, 1, note="Optional contrast applique."),
    ]


def bounds(piece: FeltPiece) -> tuple[float, float, float, float]:
    xs = [p[0] for p in piece.points]
    ys = [p[1] for p in piece.points]
    return min(xs), min(ys), max(xs), max(ys)


def normalize(piece: FeltPiece) -> FeltPiece:
    x1, y1, x2, y2 = bounds(piece)
    return FeltPiece(piece.name, tuple((x - x1, y - y1) for x, y in piece.points), piece.quantity, piece.material, piece.note)


def inset_points(points, amount_mm: float = 3.0):
    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    radius = max(math.hypot(x - cx, y - cy) for x, y in points) or 1.0
    factor = max(0.70, 1.0 - amount_mm / radius)
    return tuple((cx + (x - cx) * factor, cy + (y - cy) * factor) for x, y in points)


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


def _draw_poly_pdf(c: canvas.Canvas, points, x0, y0, page_h_mm, dashed=False):
    p = c.beginPath()
    x, y = points[0]
    p.moveTo((x0 + x) * MM, (page_h_mm - y0 - y) * MM)
    for x, y in points[1:]:
        p.lineTo((x0 + x) * MM, (page_h_mm - y0 - y) * MM)
    p.close()
    if dashed:
        c.setDash(3, 2)
        c.setLineWidth(0.45)
    else:
        c.setDash()
        c.setLineWidth(0.8)
    c.drawPath(p, stroke=1, fill=0)
    c.setDash()


def export_pattern_pdf(path: Path, design: str, paper: str) -> None:
    page = A4 if paper == "A4" else LETTER
    page_w_mm, page_h_mm = page[0] / MM, page[1] / MM
    c = canvas.Canvas(str(path), pagesize=page)
    title = display_name(design)

    for raw_piece in pieces_for_design(design):
        piece = normalize(raw_piece)
        _, _, x2, y2 = bounds(piece)
        x0 = max(12.0, (page_w_mm - x2) / 2)
        y0 = max(30.0, (page_h_mm - y2) / 2)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(10 * MM, (page_h_mm - 10) * MM, f"{title} — {piece.name.replace('-', ' ').title()}")
        c.setFont("Helvetica", 7.5)
        c.drawString(10 * MM, (page_h_mm - 15) * MM, "Print at 100% / Actual Size. Solid = cut line. Dashed = suggested blanket-stitch line.")
        _draw_poly_pdf(c, piece.points, x0, y0, page_h_mm, False)
        _draw_poly_pdf(c, inset_points(piece.points, 3.0), x0, y0, page_h_mm, True)

        c.rect(10 * MM, 10 * MM, 50 * MM, 50 * MM, stroke=1, fill=0)
        c.setFont("Helvetica", 7)
        c.drawString(10 * MM, 63 * MM, "50 mm calibration square")
        c.drawString(10 * MM, 6 * MM, f"Cut quantity: {piece.quantity} | Material: {piece.material}")
        if piece.note:
            c.drawString(10 * MM, 3 * MM, piece.note[:120])
        c.showPage()
    c.save()


def export_piece_svg(path: Path, raw_piece: FeltPiece) -> None:
    piece = normalize(raw_piece)
    _, _, width, height = bounds(piece)
    margin = 8.0
    dwg = svgwrite.Drawing(str(path), size=(f"{width + margin * 2}mm", f"{height + margin * 2}mm"), viewBox=f"0 0 {width + margin * 2} {height + margin * 2}")
    pts = [(x + margin, y + margin) for x, y in piece.points]
    stitch = [(x + margin, y + margin) for x, y in inset_points(piece.points, 3.0)]
    dwg.add(dwg.polygon(points=pts, fill="none", stroke="black", stroke_width=0.35))
    dwg.add(dwg.polygon(points=stitch, fill="none", stroke="black", stroke_width=0.22, stroke_dasharray="2,1.5"))
    dwg.save()


def export_guide(path: Path, design: str, pieces: list[FeltPiece]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawString(42, h - 55, f"{display_name(design)} — Sewing Guide")
    c.setFont("Helvetica", 9.5)
    y = h - 83
    lines = [
        "Digital sewing pattern only. No physical item is included.",
        "Suggested materials: craft felt, embroidery floss, needle, small amount of stuffing, scissors, pins/clips and optional ribbon loop.",
        "Print at 100% / Actual Size and confirm the 50 mm square before cutting.",
        "The solid line is the cut line. The dashed line is a suggested hand-stitch path, approximately 3 mm inside the edge.",
    ]
    for line in lines:
        c.drawString(42, y, line)
        y -= 16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y - 2, "Pieces")
    y -= 23
    c.setFont("Helvetica", 9)
    for p in pieces:
        c.drawString(52, y, f"• {p.name.replace('-', ' ').title()} — cut {p.quantity} from {p.material}")
        y -= 15

    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y - 2, "Assembly")
    y -= 23
    steps = [
        "1. Cut all felt pieces from the printed templates.",
        "2. Attach applique pieces to the front body with small running stitches or blanket stitch.",
        "3. Add simple embroidered eyes/details if desired; avoid loose small parts for products intended for young children.",
        "4. Place front and back body pieces together and stitch around the dashed guide, leaving a small opening.",
        "5. Add a modest amount of stuffing, then close the opening with the same stitch.",
        "6. If making an ornament, insert a ribbon loop securely between layers before closing the top edge.",
        "7. Trim stray fibres and check all seams before use or sale.",
    ]
    c.setFont("Helvetica", 9.5)
    for step in steps:
        c.drawString(52, y, step)
        y -= 17

    c.setFont("Helvetica", 8.5)
    c.drawString(42, 64, "Finished handmade items may be sold. Redistribution/resale of the digital pattern files is not included by default.")
    c.save()


def render_preview(path: Path, design: str, pieces: list[FeltPiece]) -> None:
    img = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(60, True)
    body_font = _font(30)
    small = _font(23)
    draw.rounded_rectangle((65, 55, 1535, 1145), radius=36, outline="black", width=4)
    draw.text((110, 100), display_name(design), font=title_font, fill="black")
    draw.text((110, 180), "Printable felt sewing pattern | PDF + SVG | A4 + US Letter", font=body_font, fill="black")

    y = 300
    for raw in pieces:
        p = normalize(raw)
        _, _, w, h = bounds(p)
        scale = min(4.2, 650 / max(w, h))
        pts = [(130 + x * scale, y + yy * scale) for x, yy in p.points]
        stitch = [(130 + x * scale, y + yy * scale) for x, yy in inset_points(p.points, 3.0)]
        draw.polygon(pts, outline="black")
        draw.line(stitch + [stitch[0]], fill="black", width=2)
        draw.text((850, y + 15), p.name.replace("-", " ").title(), font=body_font, fill="black")
        draw.text((850, y + 58), f"Cut {p.quantity}", font=small, fill="black")
        y += int(h * scale) + 60
        if y > 990:
            break
    draw.text((110, 1085), "True-size calibration • Original geometry • AWAITING APPROVAL", font=small, fill="black")
    img.save(path, optimize=True)


def render_features(path: Path, design: str) -> None:
    img = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(62, True)
    body = _font(34)
    draw.rounded_rectangle((70, 60, 1530, 1140), radius=36, outline="black", width=4)
    draw.text((115, 115), display_name(design), font=title_font, fill="black")
    features = [
        "A4 + US Letter true-size pattern PDFs",
        "SVG cut templates for each piece",
        "Suggested hand-stitch guide",
        "50 mm print calibration square",
        "Assembly and materials guide",
        "Original, non-licensed artwork",
    ]
    y = 275
    for feature in features:
        draw.ellipse((125, y + 8, 145, y + 28), outline="black", width=3)
        draw.text((175, y), feature, font=body, fill="black")
        y += 112
    img.save(path, optimize=True)


def listing_payload(phrase: str, design: str) -> dict:
    return {
        "title": f"{display_name(design)} Sewing Pattern PDF & SVG | Printable Felt Craft Template",
        "description": (
            f"Create an original {display_name(design).lower()} with this digital felt sewing pattern. "
            "The download includes true-size A4 and US Letter PDFs, SVG templates, a 50 mm calibration square, "
            "suggested stitch guides and an assembly guide. Print at 100% / Actual Size before cutting. "
            "Digital download only; no physical item is shipped."
        ),
        "tags": [
            "felt sewing pattern", "felt ornament", "sewing pdf", "felt craft", "hand sewing",
            "svg sewing pattern", "printable pattern", f"{design} pattern", "diy ornament",
            "digital download", "beginner sewing", "felt animal", "craft template",
        ],
        "formats": ["PDF", "SVG"],
        "paper_sizes": ["A4", "US Letter"],
        "source_phrase": phrase,
        "design": design,
        "approval_status": "AWAITING_APPROVAL",
    }


def _zip(root: Path) -> Path:
    out = root.parent / f"{root.name}.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            if item.is_file():
                zf.write(item, arcname=f"{root.name}/{item.relative_to(root)}")
    return out


def validate(root: Path, pieces: list[FeltPiece]) -> dict:
    checks = {
        "a4_pdf": (root / "A4-pattern.pdf").exists(),
        "letter_pdf": (root / "US-Letter-pattern.pdf").exists(),
        "guide": (root / "assembly-guide.pdf").exists(),
        "listing": (root / "marketplace-listing.json").exists(),
        "status": (root / "status.json").exists(),
        "svg_count": len(list((root / "SVG").glob("*.svg"))) == len(pieces),
        "listing_images": len(list((root / "Listing-Images").glob("*.png"))) >= 2,
    }
    return {"ready": all(checks.values()), "checks": checks}


def build_from_opportunity(phrase: str, output_dir: Path) -> tuple[Path, Path, dict]:
    design = design_for_phrase(phrase)
    pieces = pieces_for_design(design)
    root = output_dir / f"felt-{bot.slugify(phrase)}"
    if root.exists():
        shutil.rmtree(root)
    (root / "SVG").mkdir(parents=True, exist_ok=True)
    (root / "Listing-Images").mkdir(parents=True, exist_ok=True)

    export_pattern_pdf(root / "A4-pattern.pdf", design, "A4")
    export_pattern_pdf(root / "US-Letter-pattern.pdf", design, "US_LETTER")
    for p in pieces:
        export_piece_svg(root / "SVG" / f"{p.name}.svg", p)
    export_guide(root / "assembly-guide.pdf", design, pieces)
    render_preview(root / "Listing-Images" / "01-pattern-preview.png", design, pieces)
    render_features(root / "Listing-Images" / "02-features.png", design)

    listing = listing_payload(phrase, design)
    (root / "marketplace-listing.json").write_text(json.dumps(listing, indent=2), encoding="utf-8")
    (root / "status.json").write_text(json.dumps({
        "status": "AWAITING_APPROVAL",
        "publishing_enabled": False,
        "factory": "CRAFT",
        "product_type": "FELT_SEWING_PATTERN",
        "source_phrase": phrase,
        "design": design,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding="utf-8")
    (root / "pattern-manifest.json").write_text(json.dumps({
        "design": design,
        "pieces": [{"name": p.name, "quantity": p.quantity, "points": p.points} for p in pieces],
    }, indent=2), encoding="utf-8")

    report = validate(root, pieces)
    (root / "quality-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return root, _zip(root), report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phrase", default="felt fox sewing pattern pdf")
    parser.add_argument("--output-dir", default="felt-pattern-output")
    args = parser.parse_args()
    root, zip_path, report = build_from_opportunity(args.phrase, Path(args.output_dir))
    print(json.dumps({"product_folder": str(root), "zip": str(zip_path), "quality_ready": report["ready"], "checks": report["checks"]}, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
