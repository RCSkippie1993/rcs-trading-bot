from __future__ import annotations

import json
from pathlib import Path

from .papercraft_geometry import PapercraftNet, fits_paper


def validate_shape_bundle(
    root: Path,
    nets: dict[str, PapercraftNet],
    paper_sizes: dict,
    theme_slugs: list[str],
    prohibited_terms: list[str],
) -> dict:
    checks=[]

    def add(name,passed,detail):
        checks.append({"name":name,"passed":bool(passed),"detail":detail})

    for shape,net in nets.items():
        for paper,dims in paper_sizes.items():
            add(
                f"{shape}_fits_{paper}",
                fits_paper(net,float(dims[0]),float(dims[1]),margin_mm=2),
                f"{net.width_mm:.1f} x {net.height_mm:.1f} mm on {dims[0]} x {dims[1]} mm"
            )
        for theme in theme_slugs:
            for folder,ext in [("A4","pdf"),("US-Letter","pdf"),("SVG","svg"),("Preview","png")]:
                suffix="-flat" if folder=="Preview" else ""
                path=root/"Shapes"/shape/folder/f"{theme}{suffix}.{ext}"
                add(f"{shape}_{theme}_{folder}",path.exists() and path.stat().st_size>0,str(path))

    for path in [root/"assembly-guide.pdf",root/"marketplace-listing.json",root/"status.json"]:
        add(f"file_{path.name}",path.exists() and path.stat().st_size>0,str(path))

    listing=(root/"marketplace-listing.json").read_text(encoding="utf-8").lower() if (root/"marketplace-listing.json").exists() else ""
    bad=[term for term in prohibited_terms if term.lower() in listing]
    add("commercial_ip_terms",not bad,"No prohibited franchise terms." if not bad else "Found: "+", ".join(bad))

    images=list((root/"Listing-Images").glob("*.png"))
    add("listing_images",len(images)>=7,f"{len(images)} listing images generated; 7 required.")

    ready=all(x["passed"] for x in checks)
    report={"ready":ready,"checks":checks}
    (root/"bundle-quality-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
