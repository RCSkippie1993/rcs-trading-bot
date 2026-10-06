from __future__ import annotations

import json
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

from craft_factory.build_craft_product import build_product
from craft_factory.craft_router import route_craft_phrase
from craft_factory.leather_pattern_factory import build_from_opportunity as build_leather_pattern
from craft_factory.leather_pattern_factory import pattern_kind_for_phrase
from craft_factory.papercraft_geometry import build_cube_net, fits_paper


def main():
    net = build_cube_net(60, 10)
    assert net.width_mm == 200
    assert net.height_mm == 260
    assert fits_paper(net, 210, 297)
    assert fits_paper(net, 215.9, 279.4)
    assert len(net.faces) == 6
    assert len(net.tabs) == 7

    route = route_craft_phrase("pixel party favor box printable")
    assert route.factory == "CRAFT"
    assert route.format == "PAPERCRAFT"
    assert route.ready is True

    leather = route_craft_phrase("leather wallet pattern pdf")
    assert leather.factory == "CRAFT"
    assert leather.format == "LEATHER_PATTERN"
    assert leather.ready is True
    assert pattern_kind_for_phrase("bifold leather wallet pattern pdf") == "bifold-wallet"
    assert pattern_kind_for_phrase("leather card holder pattern pdf") == "card-holder"

    with tempfile.TemporaryDirectory() as tmp:
        root, zip_path, report = build_product(Path(tmp))
        assert report["ready"] is True
        assert zip_path.exists() and zip_path.stat().st_size > 0
        assert len(list((root / "A4").glob("*.pdf"))) == 4
        assert len(list((root / "US-Letter").glob("*.pdf"))) == 4
        assert len(list((root / "SVG").glob("*.svg"))) == 4
        assert len(list((root / "Listing-Images").glob("*.png"))) == 7

        for svg in (root / "SVG").glob("*.svg"):
            ET.parse(svg)

        status = json.loads((root / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "AWAITING_APPROVAL"
        assert status["publishing_enabled"] is False

    with tempfile.TemporaryDirectory() as tmp:
        root, zip_path, report = build_leather_pattern("bifold leather wallet pattern pdf", Path(tmp))
        assert report["ready"] is True, report
        assert zip_path.exists() and zip_path.stat().st_size > 0
        assert (root / "Pattern-A4.pdf").stat().st_size > 1000
        assert (root / "Pattern-US-Letter.pdf").stat().st_size > 1000
        assert (root / "assembly-guide.pdf").stat().st_size > 1000
        assert len(list((root / "SVG").glob("*.svg"))) == 3
        for svg in (root / "SVG").glob("*.svg"):
            ET.parse(svg)
        status = json.loads((root / "status.json").read_text(encoding="utf-8"))
        assert status["product_type"] == "LEATHER_PATTERN"
        assert status["publishing_enabled"] is False

    print("craft factory self-test passed")


if __name__ == "__main__":
    main()
