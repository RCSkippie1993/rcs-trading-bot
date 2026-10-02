from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .papercraft_geometry import PapercraftNet, fits_paper


def validate_product(
    root: Path,
    net: PapercraftNet,
    paper_sizes: dict,
    themes: Iterable[str],
    prohibited_terms: Iterable[str],
) -> dict:
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    for label, dims in paper_sizes.items():
        add(
            f"fits_{label}",
            fits_paper(net, float(dims[0]), float(dims[1]), margin_mm=2.0),
            f"Net {net.width_mm:.1f} x {net.height_mm:.1f} mm on {dims[0]} x {dims[1]} mm.",
        )

    required_common = [
        root / "assembly-guide.pdf",
        root / "printing-guide.txt",
        root / "marketplace-listing.json",
        root / "status.json",
    ]
    for path in required_common:
        add(f"file_{path.name}", path.exists() and path.stat().st_size > 0, str(path))

    for theme in themes:
        required = [
            root / "A4" / f"{theme}.pdf",
            root / "US-Letter" / f"{theme}.pdf",
            root / "SVG" / f"{theme}.svg",
            root / "Preview" / f"{theme}-flat.png",
        ]
        for path in required:
            add(f"{theme}_{path.suffix[1:]}", path.exists() and path.stat().st_size > 0, str(path))

    listing_path = root / "marketplace-listing.json"
    listing_text = listing_path.read_text(encoding="utf-8").lower() if listing_path.exists() else ""
    bad = [term for term in prohibited_terms if term.lower() in listing_text]
    add(
        "commercial_ip_terms",
        not bad,
        "No prohibited franchise terms in commercial listing." if not bad else "Found: " + ", ".join(bad),
    )

    listing_images = list((root / "Listing-Images").glob("*.png")) if (root / "Listing-Images").exists() else []
    add("listing_images", len(listing_images) >= 7, f"{len(listing_images)} listing images generated; 7 required.")

    ready = all(item["passed"] for item in checks)
    report = {"ready": ready, "checks": checks}
    (root / "craft-quality-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
