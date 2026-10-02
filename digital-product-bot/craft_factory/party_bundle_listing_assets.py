from __future__ import annotations

from pathlib import Path
from typing import Dict

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


def _canvas():
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((60, 60, W - 60, H - 60), radius=34, fill=SURFACE, outline=PRIMARY, width=3)
    return image, draw


def _wrapped(draw, text: str, x: int, y: int, width: int, font, fill=PRIMARY, gap: int = 8) -> int:
    line = ""
    lines = []
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    for row in lines:
        draw.text((x, y), row, font=font, fill=fill)
        y += getattr(font, "size", 30) + gap
    return y


def _header(draw, label: str, title: str):
    draw.rounded_rectangle((100, 90, 500, 150), radius=18, fill=PRIMARY)
    draw.text((128, 108), title.upper()[:30], font=_font(21, True), fill="white")
    draw.rounded_rectangle((1260, 90, 1500, 150), radius=18, fill=ACCENT)
    draw.text((1290, 108), label.upper()[:17], font=_font(21, True), fill=PRIMARY)


def _thumb(path: Path, max_w: int, max_h: int) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img.thumbnail((max_w, max_h))
    return img


def create_bundle_listing_images(
    output_dir: Path,
    product_title: str,
    theme_name: str,
    themes: list[Theme],
    shape_previews: Dict[str, Path],
    shape_dimensions: Dict[str, tuple[float, float, float]],
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []

    # 1. Hero: five distinct dielines.
    img, draw = _canvas()
    _header(draw, "5 Shapes", theme_name)
    y = _wrapped(draw, product_title, 105, 205, 720, _font(58, True))
    _wrapped(draw, "Printable favor-box bundle • A4 + US Letter • PDF + SVG • Original kids-party artwork", 110, y + 20, 700, _font(27))
    positions = [(860, 245), (1180, 245), (860, 585), (1180, 585), (1020, 850)]
    for (shape, path), (x, yy) in zip(shape_previews.items(), positions):
        thumb = _thumb(path, 260, 240)
        img.paste(thumb, (x, yy))
        draw.text((x, yy + 245), shape.replace("-", " ").title(), font=_font(21, True), fill=PRIMARY)
    draw.rounded_rectangle((105, 720, 760, 1035), radius=28, fill=MUTED)
    draw.text((145, 765), "INCLUDED", font=_font(25, True), fill=ACCENT)
    draw.text((145, 825), "5 box shapes", font=_font(37, True), fill=PRIMARY)
    draw.text((145, 885), "PDF + SVG cut files", font=_font(31, True), fill=PRIMARY)
    draw.text((145, 945), "Print • Cut • Fold • Glue", font=_font(28, True), fill=PRIMARY)
    p=output_dir/"listing-image-01-hero.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    # 2. Shape overview.
    img, draw = _canvas()
    _header(draw, "Box Shapes", theme_name)
    draw.text((105, 205), "Five favor-box structures in one kit", font=_font(49, True), fill=PRIMARY)
    cards = list(shape_previews.items())
    positions = [(100,330),(590,330),(1080,330),(345,730),(835,730)]
    for (shape,path),(x,yy) in zip(cards,positions):
        draw.rounded_rectangle((x,yy,x+410,yy+330),radius=24,fill=MUTED)
        thumb=_thumb(path,340,235)
        img.paste(thumb,(x+35,yy+25))
        draw.text((x+35,yy+270),shape.replace("-"," ").title(),font=_font(27,True),fill=PRIMARY)
    p=output_dir/"listing-image-02-shapes.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    # 3. Theme/artwork.
    img, draw = _canvas()
    _header(draw, "Artwork", theme_name)
    draw.text((105, 205), "Original coordinated artwork and colour palette", font=_font(47, True), fill=PRIMARY)
    x=120
    for theme in themes[:4]:
        draw.rounded_rectangle((x,350,x+315,850),radius=24,fill=theme.palette[0],outline=theme.dark,width=3)
        y0=390
        sw=50
        for color in theme.palette[:5]:
            draw.rectangle((x+35,y0,x+280,y0+sw),fill=color)
            y0+=62
        draw.text((x+35,735),theme.display_name,font=_font(24,True),fill="white" if theme.dark != "#FFFFFF" else PRIMARY)
        x+=355
    draw.text((120,955),"Original party artwork — no licensed character art or copied franchise textures.",font=_font(26,True),fill=PRIMARY)
    p=output_dir/"listing-image-03-artwork.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    # 4. Files included.
    img, draw = _canvas()
    _header(draw, "Files", theme_name)
    draw.text((105, 205), "Ready for home printing and compatible cutting workflows", font=_font(45, True), fill=PRIMARY)
    items=[
        ("A4 PDF","True-size print files"),
        ("US Letter PDF","True-size Letter files"),
        ("SVG","Vector artwork + cut/fold lines"),
        ("Assembly Guide","Print, cut, fold and glue"),
        ("Dimensions","Each shape includes assembled size"),
        ("QA Report","Automated paper-fit and file checks"),
    ]
    for i,(head,body) in enumerate(items):
        row,col=divmod(i,2); x=110+col*735; yy=330+row*235
        draw.rounded_rectangle((x,yy,x+665,yy+185),radius=24,fill=MUTED)
        draw.text((x+30,yy+32),head,font=_font(31,True),fill=PRIMARY)
        draw.text((x+30,yy+92),body,font=_font(23),fill=PRIMARY)
    p=output_dir/"listing-image-04-files.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    # 5. How it works.
    img, draw = _canvas()
    _header(draw, "How It Works", theme_name)
    draw.text((105, 205), "From download to party table", font=_font(50, True), fill=PRIMARY)
    steps=[("1","PRINT","Choose A4 or US Letter and print at 100%."),("2","CUT","Cut only the solid outer lines."),("3","FOLD","Score and fold the dashed lines."),("4","GLUE","Secure the tabs inside the box."),("5","FILL","Add lightweight party treats or favours.")]
    y=330
    for n,h,b in steps:
        draw.ellipse((120,y,195,y+75),fill=ACCENT); draw.text((146,y+17),n,font=_font(31,True),fill=PRIMARY)
        draw.text((230,y),h,font=_font(30,True),fill=PRIMARY); draw.text((230,y+50),b,font=_font(24),fill=PRIMARY); y+=155
    p=output_dir/"listing-image-05-how.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    # 6. Dimensions.
    img, draw = _canvas()
    _header(draw, "Dimensions", theme_name)
    draw.text((105, 205), "Assembled sizes", font=_font(50, True), fill=PRIMARY)
    y=330
    for shape,dims in shape_dimensions.items():
        w,d,h=dims
        draw.rounded_rectangle((120,y,1480,y+120),radius=20,fill=MUTED)
        draw.text((155,y+32),shape.replace("-"," ").title(),font=_font(28,True),fill=PRIMARY)
        draw.text((760,y+32),f"{w:.0f} × {d:.0f} × {h:.0f} mm",font=_font(28,True),fill=PRIMARY)
        y+=145
    p=output_dir/"listing-image-06-dimensions.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    # 7. Notes.
    img, draw = _canvas()
    _header(draw, "Please Note", theme_name)
    draw.text((105, 205), "Important before purchase", font=_font(50, True), fill=PRIMARY)
    notes=[
        "Digital download only; no physical boxes are shipped.",
        "Print PDFs at 100% / Actual Size.",
        "SVG files require compatible design/cutting software.",
        "Cardstock suitability depends on your printer; test one sheet first.",
        "Adult supervision is recommended for cutting and glue assembly.",
        "Artwork is original and theme-inspired, not official franchise merchandise.",
    ]
    y=330
    for i,note in enumerate(notes,1):
        draw.rounded_rectangle((120,y,1480,y+110),radius=20,fill=MUTED)
        draw.text((150,y+29),f"{i}.",font=_font(27,True),fill=ACCENT)
        draw.text((215,y+29),note,font=_font(24),fill=PRIMARY); y+=130
    p=output_dir/"listing-image-07-notes.png"; img.save(p,"PNG",optimize=True); files.append(p.name)

    return files
