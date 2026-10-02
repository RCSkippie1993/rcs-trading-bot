from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Dict

import svgwrite
from PIL import Image

from .papercraft_geometry import PapercraftNet
from .theme_engine import Theme


def _data_uri(image: Image.Image) -> str:
    buf = BytesIO()
    image.save(buf, "PNG", optimize=True)
    payload = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def export_svg(
    path: Path,
    net: PapercraftNet,
    face_art: Dict[str, Image.Image],
    theme: Theme,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    dwg = svgwrite.Drawing(
        filename=str(path),
        size=(f"{net.width_mm}mm", f"{net.height_mm}mm"),
        viewBox=f"0 0 {net.width_mm} {net.height_mm}",
        profile="full",
    )

    artwork_group = dwg.g(id="artwork")
    tab_group = dwg.g(id="glue-tabs")
    fold_group = dwg.g(id="fold-lines")
    cut_group = dwg.g(id="cut-lines")

    for name, face in net.faces.items():
        artwork_group.add(
            dwg.image(
                href=_data_uri(face_art[name]),
                insert=(face.x, face.y),
                size=(face.w, face.h),
                preserveAspectRatio="none",
            )
        )

    for tab in net.tabs:
        tab_group.add(
            dwg.polygon(
                points=list(tab.points),
                fill=theme.palette[-1],
                stroke="none",
                opacity=0.92,
            )
        )

    for (x1, y1), (x2, y2) in net.fold_lines:
        fold_group.add(
            dwg.line(
                start=(x1, y1),
                end=(x2, y2),
                stroke="#5D6470",
                stroke_width=0.35,
                stroke_dasharray="3,2",
            )
        )

    for (x1, y1), (x2, y2) in net.cut_lines:
        cut_group.add(
            dwg.line(
                start=(x1, y1),
                end=(x2, y2),
                stroke="#16191D",
                stroke_width=0.45,
            )
        )

    dwg.add(artwork_group)
    dwg.add(tab_group)
    dwg.add(fold_group)
    dwg.add(cut_group)
    dwg.save(pretty=True)
    return path
