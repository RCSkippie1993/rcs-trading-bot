from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Tuple

from PIL import Image, ImageDraw, ImageFont

from .theme_engine import Theme


W, H = 1600, 1200
BG = "#F6F2EA"
SURFACE = "#FFFFFF"
PRIMARY = "#182033"
ACCENT = "#D89A5B"
MUTED = "#E8E0D3"


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _wrapped(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int, font, fill=PRIMARY, gap: int = 8) -> int:
    words = text.split()
    line = ""
    lines = []
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    for value in lines:
        draw.text((x, y), value, font=font, fill=fill)
        y += getattr(font, "size", 30) + gap
    return y


def _canvas():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((60, 60, W - 60, H - 60), radius=34, fill=SURFACE, outline=PRIMARY, width=3)
    return img, draw


def _header(draw: ImageDraw.ImageDraw, label: str) -> None:
    draw.rounded_rectangle((100, 90, 470, 150), radius=18, fill=PRIMARY)
    draw.text((128, 108), "BLOCK ADVENTURE PARTY", font=_font(23, True), fill="white")
    draw.rounded_rectangle((1260, 90, 1500, 150), radius=18, fill=ACCENT)
    draw.text((1290, 108), label.upper(), font=_font(22, True), fill=PRIMARY)


def _quad_point(quad, u: float, v: float):
    tl, tr, br, bl = quad
    x = (1-u)*(1-v)*tl[0] + u*(1-v)*tr[0] + u*v*br[0] + (1-u)*v*bl[0]
    y = (1-u)*(1-v)*tl[1] + u*(1-v)*tr[1] + u*v*br[1] + (1-u)*v*bl[1]
    return x, y


def _texture_quad(draw: ImageDraw.ImageDraw, texture: Image.Image, quad, cells: int = 14) -> None:
    tex = texture.resize((cells, cells))
    px = tex.load()
    for r in range(cells):
        for c in range(cells):
            u0, u1 = c / cells, (c + 1) / cells
            v0, v1 = r / cells, (r + 1) / cells
            poly = [
                _quad_point(quad, u0, v0),
                _quad_point(quad, u1, v0),
                _quad_point(quad, u1, v1),
                _quad_point(quad, u0, v1),
            ]
            draw.polygon(poly, fill=px[c, r])
    draw.line([quad[0], quad[1], quad[2], quad[3], quad[0]], fill=PRIMARY, width=4)


def _cube(draw: ImageDraw.ImageDraw, face_art: Dict[str, Image.Image], x: int, y: int, scale: float = 1.0) -> None:
    s = int(330 * scale)
    depth = int(150 * scale)
    front = [(x, y), (x+s, y), (x+s, y+s), (x, y+s)]
    top = [(x, y), (x+depth, y-depth), (x+s+depth, y-depth), (x+s, y)]
    right = [(x+s, y), (x+s+depth, y-depth), (x+s+depth, y+s-depth), (x+s, y+s)]
    _texture_quad(draw, face_art["front"], front)
    _texture_quad(draw, face_art["top"], top)
    _texture_quad(draw, face_art["right"], right)


def _save(img: Image.Image, path: Path) -> str:
    img.save(path, "PNG", optimize=True)
    return path.name


def create_listing_images(
    output_dir: Path,
    themes: Dict[str, Theme],
    face_art_by_theme: Dict[str, Dict[str, Image.Image]],
    flat_previews: Dict[str, Path],
    size_mm: float,
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []

    # 1 Hero
    img, draw = _canvas()
    _header(draw, "Printable Kit")
    y = _wrapped(draw, "Block Adventure Party Favor Box Kit", 110, 210, 680, _font(62, True))
    _wrapped(draw, "Four original pixel-style designs • PDF + SVG • Print, cut, fold and glue", 115, y + 20, 650, _font(28))
    draw.rounded_rectangle((110, 650, 710, 1020), radius=28, fill=MUTED)
    draw.text((150, 700), f"{int(size_mm)} mm cube", font=_font(40, True), fill=PRIMARY)
    draw.text((150, 770), "A4 + US Letter", font=_font(34, True), fill=PRIMARY)
    draw.text((150, 835), "4 designs included", font=_font(34, True), fill=PRIMARY)
    draw.text((150, 930), "DIGITAL DOWNLOAD", font=_font(28, True), fill=ACCENT)
    first_key = next(iter(face_art_by_theme))
    _cube(draw, face_art_by_theme[first_key], 900, 410, 1.25)
    files.append(_save(img, output_dir / "listing-image-01-hero.png"))

    # 2 Four designs
    img, draw = _canvas()
    _header(draw, "4 Designs")
    draw.text((110, 205), "Four original block-adventure colourways", font=_font(48, True), fill=PRIMARY)
    positions = [(120, 360), (820, 360), (120, 770), (820, 770)]
    for (slug, theme), (x, y) in zip(themes.items(), positions):
        _cube(draw, face_art_by_theme[slug], x + 70, y, 0.55)
        draw.text((x, y + 245), theme.display_name, font=_font(30, True), fill=PRIMARY)
    files.append(_save(img, output_dir / "listing-image-02-designs.png"))

    # 3 Flat template
    img, draw = _canvas()
    _header(draw, "Flat Template")
    draw.text((110, 205), "Print-ready dieline with cut and fold guides", font=_font(48, True), fill=PRIMARY)
    preview = Image.open(flat_previews[first_key]).convert("RGB")
    preview.thumbnail((980, 790))
    img.paste(preview, (310, 310))
    draw.text((115, 1045), "Solid line = CUT   •   Dashed line = FOLD / SCORE", font=_font(28, True), fill=PRIMARY)
    files.append(_save(img, output_dir / "listing-image-03-flat-template.png"))

    # 4 Included
    img, draw = _canvas()
    _header(draw, "Included")
    draw.text((110, 205), "What you receive", font=_font(52, True), fill=PRIMARY)
    items = [
        ("4 × A4 PDFs", "One print-ready file for each design"),
        ("4 × US Letter PDFs", "True-size files for Letter paper"),
        ("4 × SVG cut files", "Vector cut/fold geometry with artwork"),
        ("Assembly guide", "Simple print, cut, fold and glue instructions"),
        ("7 listing previews", "Clear reference images for the digital kit"),
        ("Quality report", "Automated checks for size, files and commercial safety"),
    ]
    y = 330
    for idx, (head, body) in enumerate(items, 1):
        col = 0 if idx <= 3 else 1
        row = idx - 1 if idx <= 3 else idx - 4
        x = 120 + col * 720
        yy = 330 + row * 230
        draw.rounded_rectangle((x, yy, x + 650, yy + 180), radius=24, fill=MUTED)
        draw.text((x + 28, yy + 28), head, font=_font(30, True), fill=PRIMARY)
        _wrapped(draw, body, x + 28, yy + 82, 590, _font(23))
    files.append(_save(img, output_dir / "listing-image-04-included.png"))

    # 5 How it works
    img, draw = _canvas()
    _header(draw, "How It Works")
    draw.text((110, 205), "Four simple assembly steps", font=_font(52, True), fill=PRIMARY)
    steps = [
        ("1", "PRINT", "Print at 100% / Actual Size"),
        ("2", "CUT", "Cut only on the solid outer lines"),
        ("3", "FOLD", "Score and fold every dashed line"),
        ("4", "GLUE", "Glue tabs inside adjoining faces"),
    ]
    y = 345
    for number, head, body in steps:
        draw.ellipse((120, y, 200, y + 80), fill=ACCENT)
        draw.text((146, y + 19), number, font=_font(34, True), fill=PRIMARY)
        draw.text((240, y + 3), head, font=_font(34, True), fill=PRIMARY)
        draw.text((240, y + 54), body, font=_font(26), fill=PRIMARY)
        y += 190
    files.append(_save(img, output_dir / "listing-image-05-how-it-works.png"))

    # 6 Size / formats
    img, draw = _canvas()
    _header(draw, "Size & Formats")
    draw.text((110, 205), "Designed to print at home", font=_font(52, True), fill=PRIMARY)
    draw.rounded_rectangle((120, 340, 760, 930), radius=30, fill=MUTED)
    draw.text((175, 400), "ASSEMBLED SIZE", font=_font(26, True), fill=ACCENT)
    draw.text((175, 465), f"{int(size_mm)} × {int(size_mm)} × {int(size_mm)} mm", font=_font(47, True), fill=PRIMARY)
    draw.text((175, 575), "PAPER", font=_font(26, True), fill=ACCENT)
    draw.text((175, 630), "A4 + US Letter", font=_font(39, True), fill=PRIMARY)
    draw.text((175, 740), "FILES", font=_font(26, True), fill=ACCENT)
    draw.text((175, 795), "PDF + SVG", font=_font(39, True), fill=PRIMARY)
    _cube(draw, face_art_by_theme[first_key], 950, 520, 0.9)
    files.append(_save(img, output_dir / "listing-image-06-size-formats.png"))

    # 7 Important notes
    img, draw = _canvas()
    _header(draw, "Please Note")
    draw.text((110, 205), "Before you purchase", font=_font(52, True), fill=PRIMARY)
    notes = [
        "Digital product only - no physical box is shipped.",
        "Print PDFs at 100% / Actual Size for the intended dimensions.",
        "SVG files are provided for compatible cutting/design software.",
        "Adult supervision is recommended for cutting and glue assembly.",
        "Artwork is an original block-adventure / voxel aesthetic and is not official franchise artwork.",
    ]
    y = 340
    for idx, note in enumerate(notes, 1):
        draw.rounded_rectangle((120, y, 1480, y + 125), radius=22, fill=MUTED)
        draw.text((155, y + 34), f"{idx}.", font=_font(30, True), fill=ACCENT)
        _wrapped(draw, note, 220, y + 30, 1190, _font(26))
        y += 150
    files.append(_save(img, output_dir / "listing-image-07-important.png"))

    return files
