from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .papercraft_geometry import CubeNet
from .theme_engine import Theme


def _image_reader(image: Image.Image) -> ImageReader:
    buf = BytesIO()
    image.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return ImageReader(buf)


def export_print_pdf(
    path: Path,
    net: CubeNet,
    face_art: Dict[str, Image.Image],
    theme: Theme,
    paper_size_mm: Tuple[float, float],
    label: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    page_w_mm, page_h_mm = paper_size_mm
    c = canvas.Canvas(str(path), pagesize=(page_w_mm * mm, page_h_mm * mm))

    offset_x = (page_w_mm - net.width_mm) / 2.0
    offset_y = (page_h_mm - net.height_mm) / 2.0

    # Artwork.
    for name, face in net.faces.items():
        c.drawImage(
            _image_reader(face_art[name]),
            (offset_x + face.x) * mm,
            (page_h_mm - offset_y - face.y - face.size) * mm,
            width=face.size * mm,
            height=face.size * mm,
            preserveAspectRatio=False,
            mask="auto",
        )

    # Glue tabs use a matching neutral theme fill.
    c.setFillColor(theme.palette[-1])
    c.setStrokeColor(theme.palette[-1])
    for tab in net.tabs:
        p = c.beginPath()
        first_x, first_y = tab.points[0]
        p.moveTo((offset_x + first_x) * mm, (page_h_mm - offset_y - first_y) * mm)
        for x, y in tab.points[1:]:
            p.lineTo((offset_x + x) * mm, (page_h_mm - offset_y - y) * mm)
        p.close()
        c.drawPath(p, fill=1, stroke=0)

    # Cut lines.
    c.setStrokeColorRGB(0.08, 0.09, 0.11)
    c.setLineWidth(0.55)
    c.setDash()
    for (x1, y1), (x2, y2) in net.cut_lines:
        c.line(
            (offset_x + x1) * mm,
            (page_h_mm - offset_y - y1) * mm,
            (offset_x + x2) * mm,
            (page_h_mm - offset_y - y2) * mm,
        )

    # Fold lines.
    c.setStrokeColorRGB(0.35, 0.38, 0.43)
    c.setLineWidth(0.45)
    c.setDash(3, 2)
    for (x1, y1), (x2, y2) in net.fold_lines:
        c.line(
            (offset_x + x1) * mm,
            (page_h_mm - offset_y - y1) * mm,
            (offset_x + x2) * mm,
            (page_h_mm - offset_y - y2) * mm,
        )
    c.setDash()

    # Tiny print note in unused margin; does not affect the dieline.
    c.setFillColorRGB(0.15, 0.16, 0.18)
    c.setFont("Helvetica", 6)
    c.drawCentredString(
        page_w_mm * mm / 2,
        3.5 * mm,
        f"{label} - print at 100% / Actual Size - solid=cut, dashed=fold",
    )

    c.showPage()
    c.save()
    return path


def render_flat_preview(
    path: Path,
    net: CubeNet,
    face_art: Dict[str, Image.Image],
    theme: Theme,
    px_per_mm: int = 5,
) -> Path:
    width = int(net.width_mm * px_per_mm)
    height = int(net.height_mm * px_per_mm)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    for name, face in net.faces.items():
        art = face_art[name].resize((int(face.size * px_per_mm), int(face.size * px_per_mm)))
        img.paste(art, (int(face.x * px_per_mm), int(face.y * px_per_mm)))

    for tab in net.tabs:
        pts = [(int(x * px_per_mm), int(y * px_per_mm)) for x, y in tab.points]
        draw.polygon(pts, fill=theme.palette[-1])

    for (x1, y1), (x2, y2) in net.cut_lines:
        draw.line(
            (int(x1 * px_per_mm), int(y1 * px_per_mm), int(x2 * px_per_mm), int(y2 * px_per_mm)),
            fill="#16191D",
            width=max(1, px_per_mm // 2),
        )

    dash = max(3, px_per_mm)
    for (x1, y1), (x2, y2) in net.fold_lines:
        x1p, y1p, x2p, y2p = [v * px_per_mm for v in (x1, y1, x2, y2)]
        length = max(abs(x2p - x1p), abs(y2p - y1p))
        steps = max(1, int(length // dash))
        for i in range(0, steps, 2):
            a = i / steps
            b = min(1, (i + 1) / steps)
            xa, ya = x1p + (x2p - x1p) * a, y1p + (y2p - y1p) * a
            xb, yb = x1p + (x2p - x1p) * b, y1p + (y2p - y1p) * b
            draw.line((int(xa), int(ya), int(xb), int(yb)), fill="#666B73", width=max(1, px_per_mm // 3))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path
