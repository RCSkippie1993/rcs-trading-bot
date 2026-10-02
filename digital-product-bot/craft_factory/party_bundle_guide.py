from __future__ import annotations

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def export_bundle_guide(path: Path, product_name: str, shape_dimensions: dict[str, tuple[float,float,float]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    c=canvas.Canvas(str(path),pagesize=A4)
    pw,ph=A4
    c.setFillColor(colors.HexColor("#182033")); c.setFont("Helvetica-Bold",20)
    c.drawString(18*mm,ph-22*mm,product_name)
    c.setFont("Helvetica",9); c.drawString(18*mm,ph-31*mm,"Digital papercraft bundle • print at 100% / Actual Size")

    y=ph-48*mm
    steps=[("1. Print","Use the PDF matching your paper size. Disable Fit/Shrink/Scale."),
           ("2. Cut","Cut only solid outer lines. Internal solid lines on gable handles are cut-outs."),
           ("3. Score & fold","Score every dashed line before folding for cleaner edges."),
           ("4. Glue","Glue tabs to the inside of adjoining panels and allow the joins to set."),
           ("5. Fill","Use for lightweight party favours; do not use for hot, wet or unpackaged food.")]
    for title,body in steps:
        c.setFillColor(colors.HexColor("#E8E0D3")); c.roundRect(18*mm,y-22*mm,174*mm,18*mm,3*mm,fill=1,stroke=0)
        c.setFillColor(colors.HexColor("#182033")); c.setFont("Helvetica-Bold",11); c.drawString(23*mm,y-10*mm,title)
        c.setFont("Helvetica",8); c.drawString(23*mm,y-16*mm,body); y-=27*mm

    c.setFont("Helvetica-Bold",11); c.drawString(18*mm,y-4*mm,"Assembled sizes")
    y-=11*mm; c.setFont("Helvetica",8)
    for shape,dims in shape_dimensions.items():
        c.drawString(23*mm,y,f"{shape.replace('-',' ').title()}: {dims[0]:.0f} × {dims[1]:.0f} × {dims[2]:.0f} mm"); y-=7*mm

    c.setFont("Helvetica",7); c.setFillColor(colors.HexColor("#555555"))
    c.drawString(18*mm,12*mm,"Adult supervision recommended. Original digital artwork; no physical product included.")
    c.showPage(); c.save(); return path
