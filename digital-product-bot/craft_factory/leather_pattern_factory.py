from __future__ import annotations

import json
import math
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import svgwrite
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.pdfgen import canvas

import bot

MM = 72.0 / 25.4


@dataclass(frozen=True)
class LeatherPiece:
    name: str
    width_mm: float
    height_mm: float
    corner_radius_mm: float = 4.0
    stitch_offset_mm: float = 4.0
    stitch_edges: tuple[str, ...] = ("left", "right", "bottom")
    quantity: int = 1
    note: str = ""


def pattern_kind_for_phrase(phrase: str) -> str:
    text = phrase.lower()
    if "bifold" in text or "bi-fold" in text:
        return "bifold-wallet"
    if any(term in text for term in ["card holder", "cardholder", "card wallet"]):
        return "card-holder"
    if any(term in text for term in ["slim wallet", "minimalist wallet", "front pocket wallet"]):
        return "slim-wallet"
    return "card-holder" if "card" in text else "slim-wallet"


def pattern_display_name(kind: str) -> str:
    return {
        "card-holder": "Minimal Card Holder",
        "slim-wallet": "Slim Wallet",
        "bifold-wallet": "Classic Bifold Wallet",
    }[kind]


def pattern_pieces(kind: str) -> list[LeatherPiece]:
    if kind == "bifold-wallet":
        return [
            LeatherPiece(
                "outer-body", 225, 95, 5, 4, ("top", "bottom"), 1,
                "Fold at centre after skiving or conditioning the fold area as needed for your leather.",
            ),
            LeatherPiece("left-pocket", 104, 67, 4, 4, ("left", "right", "bottom"), 2, "Card pocket layer."),
            LeatherPiece("right-pocket", 104, 67, 4, 4, ("left", "right", "bottom"), 2, "Card pocket layer."),
        ]
    if kind == "slim-wallet":
        return [
            LeatherPiece("back-panel", 165, 78, 5, 4, ("left", "right", "bottom"), 1, "Main back panel."),
            LeatherPiece("front-pocket", 104, 60, 4, 4, ("left", "right", "bottom"), 2, "Front/rear card pocket."),
        ]
    return [
        LeatherPiece("back-panel", 108, 78, 5, 4, ("left", "right", "bottom"), 1, "Main card-holder panel."),
        LeatherPiece("front-pocket", 108, 60, 4, 4, ("left", "right", "bottom"), 2, "Card pocket; cut two."),
    ]


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


def _rounded_rect_path(x: float, y: float, w: float, h: float, r: float) -> str:
    r = max(0.0, min(r, w / 2, h / 2))
    return (
        f"M {x+r},{y} H {x+w-r} "
        f"A {r},{r} 0 0 1 {x+w},{y+r} V {y+h-r} "
        f"A {r},{r} 0 0 1 {x+w-r},{y+h} H {x+r} "
        f"A {r},{r} 0 0 1 {x},{y+h-r} V {y+r} "
        f"A {r},{r} 0 0 1 {x+r},{y} Z"
    )


def _stitch_segments(piece: LeatherPiece) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    o = piece.stitch_offset_mm
    w, h = piece.width_mm, piece.height_mm
    segments = []
    if "top" in piece.stitch_edges:
        segments.append(((o, o), (w - o, o)))
    if "bottom" in piece.stitch_edges:
        segments.append(((o, h - o), (w - o, h - o)))
    if "left" in piece.stitch_edges:
        segments.append(((o, o), (o, h - o)))
    if "right" in piece.stitch_edges:
        segments.append(((w - o, o), (w - o, h - o)))
    return segments


def _punch_points(piece: LeatherPiece, spacing_mm: float = 5.0) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for (x1, y1), (x2, y2) in _stitch_segments(piece):
        length = math.hypot(x2 - x1, y2 - y1)
        count = max(1, int(length // spacing_mm))
        for i in range(count + 1):
            t = i / count
            p = (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
            if not any(abs(p[0] - q[0]) < 0.2 and abs(p[1] - q[1]) < 0.2 for q in points):
                points.append(p)
    return points


def _page_size_for_piece(piece: LeatherPiece, paper: str):
    base = A4 if paper == "A4" else LETTER
    portrait_w = base[0] / MM
    portrait_h = base[1] / MM
    margin = 18.0
    if piece.width_mm + margin <= portrait_w and piece.height_mm + margin <= portrait_h:
        return base
    return landscape(base)


def _draw_pdf_piece(c: canvas.Canvas, piece: LeatherPiece, paper: str, title: str) -> None:
    page = _page_size_for_piece(piece, paper)
    c.setPageSize(page)
    page_w_mm, page_h_mm = page[0] / MM, page[1] / MM
    x0 = (page_w_mm - piece.width_mm) / 2
    y0 = (page_h_mm - piece.height_mm) / 2 - 3

    c.setFont("Helvetica-Bold", 11)
    c.drawString(10 * MM, (page_h_mm - 10) * MM, f"{title} — {piece.name.replace('-', ' ').title()}")
    c.setFont("Helvetica", 7.5)
    c.drawString(10 * MM, (page_h_mm - 15) * MM, "Print at 100% / Actual Size. Solid line = cut. Dashed line = stitch guide. Dots = suggested punch spacing.")

    c.setLineWidth(0.8)
    c.roundRect(x0 * MM, y0 * MM, piece.width_mm * MM, piece.height_mm * MM, piece.corner_radius_mm * MM, stroke=1, fill=0)

    c.setDash(3, 2)
    c.setLineWidth(0.45)
    for (x1, y1), (x2, y2) in _stitch_segments(piece):
        c.line((x0 + x1) * MM, (y0 + piece.height_mm - y1) * MM, (x0 + x2) * MM, (y0 + piece.height_mm - y2) * MM)
    c.setDash()

    c.setFillColorRGB(0, 0, 0)
    for x, y in _punch_points(piece):
        c.circle((x0 + x) * MM, (y0 + piece.height_mm - y) * MM, 0.45 * MM, stroke=0, fill=1)

    square_x, square_y = 10.0, 10.0
    c.rect(square_x * MM, square_y * MM, 50 * MM, 50 * MM, stroke=1, fill=0)
    c.setFont("Helvetica", 7)
    c.drawString(square_x * MM, (square_y + 52) * MM, "50 mm calibration square")
    c.drawString(square_x * MM, (square_y - 4) * MM, f"Finished piece: {piece.width_mm:g} × {piece.height_mm:g} mm | Qty {piece.quantity}")
    if piece.note:
        c.drawString(square_x * MM, (square_y - 8) * MM, piece.note[:120])
    c.showPage()


def export_pattern_pdf(path: Path, kind: str, paper: str) -> None:
    pieces = pattern_pieces(kind)
    title = pattern_display_name(kind)
    first = _page_size_for_piece(pieces[0], paper)
    c = canvas.Canvas(str(path), pagesize=first)
    for piece in pieces:
        _draw_pdf_piece(c, piece, paper, title)
    c.save()


def export_piece_svg(path: Path, piece: LeatherPiece) -> None:
    margin = 10.0
    width = piece.width_mm + margin * 2
    height = piece.height_mm + margin * 2
    dwg = svgwrite.Drawing(str(path), size=(f"{width}mm", f"{height}mm"), viewBox=f"0 0 {width} {height}")
    group = dwg.g(transform=f"translate({margin},{margin})")
    group.add(dwg.path(d=_rounded_rect_path(0, 0, piece.width_mm, piece.height_mm, piece.corner_radius_mm), fill="none", stroke="black", stroke_width=0.35))
    for (x1, y1), (x2, y2) in _stitch_segments(piece):
        group.add(dwg.line((x1, y1), (x2, y2), stroke="black", stroke_width=0.22, stroke_dasharray="2,1.5"))
    for x, y in _punch_points(piece):
        group.add(dwg.circle(center=(x, y), r=0.45, fill="black"))
    dwg.add(group)
    dwg.save()


def export_assembly_guide(path: Path, kind: str, pieces: list[LeatherPiece]) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    title = pattern_display_name(kind)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(42, h - 55, f"{title} — Build Guide")
    c.setFont("Helvetica", 9.5)
    y = h - 82
    intro = [
        "Digital pattern only. No physical leather item is included.",
        "Print pattern pages at 100% / Actual Size and verify the 50 mm calibration square before cutting leather.",
        "Suggested starting point: 1.2–1.6 mm leather for pockets and 1.4–2.0 mm for body panels, adjusted to your material and preference.",
        "Suggested tools: knife, ruler, awl/pricking irons, needles, thread, adhesive, edge-finishing tools and cutting mat.",
    ]
    for line in intro:
        c.drawString(42, y, line)
        y -= 16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y - 4, "Pattern pieces")
    y -= 24
    c.setFont("Helvetica", 9)
    for piece in pieces:
        c.drawString(52, y, f"• {piece.name.replace('-', ' ').title()}: {piece.width_mm:g} × {piece.height_mm:g} mm — quantity {piece.quantity}")
        y -= 15

    c.setFont("Helvetica-Bold", 12)
    c.drawString(42, y - 3, "Assembly sequence")
    y -= 23
    steps = [
        "1. Print and verify scale using the 50 mm square.",
        "2. Cut the paper pieces and transfer the solid cut lines to leather.",
        "3. Mark stitch guides and punch locations. Adjust punch spacing to your tools before committing to leather.",
        "4. Finish pocket top edges before gluing or stitching layered pieces.",
        "5. Lightly glue layers in position, then punch through aligned layers where appropriate.",
        "6. Saddle-stitch along the indicated edges and back-stitch at the start/end.",
        "7. Trim, bevel, sand and burnish/paint edges to your preferred finish.",
        "8. Test-fit cards and condition the item. Make a paper or scrap-leather prototype before premium material.",
    ]
    c.setFont("Helvetica", 9.5)
    for step in steps:
        c.drawString(52, y, step)
        y -= 17

    c.setFont("Helvetica-Bold", 11)
    c.drawString(42, 92, "Important")
    c.setFont("Helvetica", 8.5)
    c.drawString(42, 76, "Stitch holes are a suggested visual guide, not a machine-specific punch file. Leather thickness, stretch and tool spacing affect final fit.")
    c.drawString(42, 62, "Commercial use of finished handmade items is permitted; redistribution or resale of the digital pattern files is not included by default.")
    c.save()


def _render_pattern_preview(path: Path, kind: str, pieces: list[LeatherPiece]) -> None:
    img = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(62, True)
    body_font = _font(32)
    small = _font(24)
    draw.rounded_rectangle((65, 55, 1535, 1145), radius=36, outline="black", width=4)
    draw.text((110, 95), f"{pattern_display_name(kind)} Pattern", font=title_font, fill="black")
    draw.text((110, 180), "Printable PDF + SVG | A4 + US Letter | True-size calibration", font=body_font, fill="black")

    scale = min(4.6, 1180 / max(p.width_mm for p in pieces))
    y = 300
    for piece in pieces:
        x = 130
        w = int(piece.width_mm * scale)
        h = int(piece.height_mm * scale)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=max(8, int(piece.corner_radius_mm * scale)), outline="black", width=4)
        off = int(piece.stitch_offset_mm * scale)
        draw.rounded_rectangle((x + off, y + off, x + w - off, y + h - off), radius=max(5, int((piece.corner_radius_mm - 1) * scale)), outline="black", width=2)
        draw.text((x + w + 35, y + 8), piece.name.replace("-", " ").title(), font=body_font, fill="black")
        draw.text((x + w + 35, y + 50), f"{piece.width_mm:g} × {piece.height_mm:g} mm | Qty {piece.quantity}", font=small, fill="black")
        y += h + 65

    draw.text((110, 1085), "Print at 100% • Verify 50 mm square • AWAITING APPROVAL", font=small, fill="black")
    img.save(path, optimize=True)


def _render_feature_image(path: Path, kind: str) -> None:
    img = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(img)
    title_font = _font(64, True)
    body_font = _font(34)
    small = _font(26)
    draw.rounded_rectangle((70, 60, 1530, 1140), radius=36, outline="black", width=4)
    draw.text((115, 120), pattern_display_name(kind), font=title_font, fill="black")
    features = [
        "True-size A4 pattern PDF",
        "True-size US Letter pattern PDF",
        "SVG cut/stitch reference files",
        "50 mm calibration square",
        "Suggested stitch + punch guides",
        "Step-by-step build guide",
    ]
    y = 290
    for feature in features:
        draw.ellipse((130, y + 7, 154, y + 31), outline="black", width=3)
        draw.text((185, y), feature, font=body_font, fill="black")
        y += 105
    draw.text((115, 1010), "Digital download • Original geometry • No physical item", font=small, fill="black")
    img.save(path, optimize=True)


def _listing(phrase: str, kind: str) -> dict:
    title = f"{pattern_display_name(kind)} Leather Pattern PDF + SVG | A4 US Letter Printable Template | Stitch Guide"
    price = {"card-holder": 5.95, "slim-wallet": 7.95, "bifold-wallet": 9.95}[kind]
    return {
        "title": title[:140],
        "short_description": f"Original printable {pattern_display_name(kind).lower()} leathercraft pattern with PDF, SVG, calibration and build guide.",
        "description": (
            f"Build a {pattern_display_name(kind).lower()} from this original digital leathercraft pattern. "
            "The download includes true-size A4 and US Letter PDF patterns, SVG reference files, a 50 mm calibration square, "
            "suggested stitch/punch guides, dimensions and an assembly guide. Print PDF pages at 100% / Actual Size and verify scale before cutting leather.\n\n"
            "Digital product only; no physical wallet, leather, tools or hardware are supplied. Pattern geometry is intended as a practical starting point and may be adjusted for leather thickness, tool spacing and personal fit preferences."
        ),
        "tags": [
            "leather pattern", "wallet pattern", "pdf pattern", "card holder", "leather craft",
            "svg pattern", "wallet template", "diy wallet", "leatherworking", "printable pattern",
            "minimal wallet", "stitch guide", "digital download",
        ],
        "formats": ["PDF", "SVG"],
        "paper_sizes": ["A4", "US Letter"],
        "pattern_kind": kind,
        "source_phrase": phrase,
        "suggested_price_usd": price,
        "approval_status": "AWAITING_APPROVAL",
    }


def validate_product(root: Path, kind: str, pieces: list[LeatherPiece]) -> dict:
    required = [
        root / "Pattern-A4.pdf",
        root / "Pattern-US-Letter.pdf",
        root / "assembly-guide.pdf",
        root / "marketplace-listing.json",
        root / "status.json",
        root / "measurements.json",
        root / "Listing-Images" / "01-pattern-preview.png",
        root / "Listing-Images" / "02-features.png",
    ]
    checks = {
        "required_files": all(p.exists() and p.stat().st_size > 250 for p in required),
        "svg_files": len(list((root / "SVG").glob("*.svg"))) == len(pieces),
        "piece_dimensions_positive": all(p.width_mm > 0 and p.height_mm > 0 for p in pieces),
        "largest_piece_printable": max(p.width_mm for p in pieces) <= 260 and max(p.height_mm for p in pieces) <= 190,
        "approval_gate": json.loads((root / "status.json").read_text(encoding="utf-8"))["publishing_enabled"] is False,
    }
    return {"ready": all(checks.values()), "checks": checks, "pattern_kind": kind}


def _zip(root: Path) -> Path:
    zip_path = root.parent / f"{root.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            if item.is_file():
                zf.write(item, arcname=f"{root.name}/{item.relative_to(root)}")
    return zip_path


def build_from_opportunity(phrase: str, output_dir: Path) -> tuple[Path, Path, dict]:
    kind = pattern_kind_for_phrase(phrase)
    pieces = pattern_pieces(kind)
    root = output_dir / f"leather-{bot.slugify(phrase)}"
    if root.exists():
        shutil.rmtree(root)
    (root / "SVG").mkdir(parents=True, exist_ok=True)
    (root / "Listing-Images").mkdir(parents=True, exist_ok=True)

    export_pattern_pdf(root / "Pattern-A4.pdf", kind, "A4")
    export_pattern_pdf(root / "Pattern-US-Letter.pdf", kind, "US-Letter")
    for piece in pieces:
        export_piece_svg(root / "SVG" / f"{piece.name}.svg", piece)
    export_assembly_guide(root / "assembly-guide.pdf", kind, pieces)
    _render_pattern_preview(root / "Listing-Images" / "01-pattern-preview.png", kind, pieces)
    _render_feature_image(root / "Listing-Images" / "02-features.png", kind)

    (root / "measurements.json").write_text(json.dumps({
        "pattern_kind": kind,
        "display_name": pattern_display_name(kind),
        "units": "mm",
        "pieces": [asdict(piece) for piece in pieces],
        "calibration_square_mm": 50,
        "recommended_print_scale": "100% / Actual Size",
    }, indent=2), encoding="utf-8")
    (root / "marketplace-listing.json").write_text(json.dumps(_listing(phrase, kind), indent=2), encoding="utf-8")
    (root / "status.json").write_text(json.dumps({
        "status": "AWAITING_APPROVAL",
        "publishing_enabled": False,
        "factory": "CRAFT",
        "product_type": "LEATHER_PATTERN",
        "pattern_kind": kind,
        "source_phrase": phrase,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2), encoding="utf-8")

    report = validate_product(root, kind, pieces)
    (root / "quality-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return root, _zip(root), report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phrase", default="leather card holder pattern pdf")
    parser.add_argument("--output-dir", default="leather-pattern-output")
    args = parser.parse_args()
    root, zip_path, report = build_from_opportunity(args.phrase, Path(args.output_dir))
    print(json.dumps({"product_folder": str(root), "zip": str(zip_path), "quality_ready": report["ready"], "checks": report["checks"]}, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
