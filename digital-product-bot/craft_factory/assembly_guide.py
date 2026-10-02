from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .papercraft_geometry import CubeNet


def export_assembly_guide(path: Path, net: CubeNet, product_name: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    page_w, page_h = A4

    c.setFillColor(colors.HexColor("#182033"))
    c.setFont("Helvetica-Bold", 20)
    c.drawString(18 * mm, page_h - 22 * mm, product_name)

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#333333"))
    c.drawString(18 * mm, page_h - 31 * mm, f"Assembled size: {net.size_mm:.0f} x {net.size_mm:.0f} x {net.size_mm:.0f} mm")

    steps = [
        ("1. Print", "Print the selected design at 100% / Actual Size. Do not use Fit to Page."),
        ("2. Cut", "Cut only on the solid outer lines. Keep every glue tab attached."),
        ("3. Fold", "Score and fold along each dashed line. Fold printed faces outward and tabs inward."),
        ("4. Glue", "Glue tabs to the inside of adjoining faces. Hold each join until secure, then close the final face."),
    ]

    y = page_h - 50 * mm
    for title, body in steps:
        c.setFillColor(colors.HexColor("#E8E0D3"))
        c.roundRect(18 * mm, y - 30 * mm, 174 * mm, 25 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#182033"))
        c.setFont("Helvetica-Bold", 13)
        c.drawString(24 * mm, y - 13 * mm, title)
        c.setFont("Helvetica", 9)
        c.drawString(24 * mm, y - 21 * mm, body)
        y -= 35 * mm

    c.setFillColor(colors.HexColor("#182033"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(18 * mm, 41 * mm, "Line key")
    c.setLineWidth(1.2)
    c.setDash()
    c.line(18 * mm, 34 * mm, 48 * mm, 34 * mm)
    c.setFont("Helvetica", 9)
    c.drawString(53 * mm, 31.5 * mm, "Solid line = cut")

    c.setDash(3, 2)
    c.line(18 * mm, 27 * mm, 48 * mm, 27 * mm)
    c.setDash()
    c.drawString(53 * mm, 24.5 * mm, "Dashed line = fold / score")

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawString(18 * mm, 13 * mm, "Adult supervision is recommended for cutting and assembly. Digital product; no physical item included.")

    c.showPage()
    c.save()
    return path
