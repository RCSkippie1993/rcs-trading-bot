from __future__ import annotations

import json
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

import bot
from craft_factory.box_shape_router import shapes_for_phrase
from craft_factory.craft_router import route_craft_phrase
from craft_factory.papercraft_geometry import (
    build_cube_net, build_gable_box_net, build_gift_box_net,
    build_milk_carton_net, build_treat_box_net, fits_paper
)
from craft_factory.party_box_bundle import build_from_opportunity
from craft_factory.party_theme_engine import infer_party_theme


def main():
    nets=[
        build_cube_net(),
        build_treat_box_net(),
        build_gift_box_net(),
        build_milk_carton_net(),
        build_gable_box_net(),
    ]
    for net in nets:
        assert fits_paper(net,210,297), (net.shape,net.width_mm,net.height_mm)
        assert fits_paper(net,215.9,279.4), (net.shape,net.width_mm,net.height_mm)
        assert len(net.faces)>=4
        assert len(net.fold_lines)>0
        assert len(net.cut_lines)>0

    assert len(shapes_for_phrase("printable favor box templates"))==5
    assert shapes_for_phrase("treat box for cricut")==["treat-box"]
    assert shapes_for_phrase("printable gift box pdf")==["gift-box"]

    assert infer_party_theme("pixel block party favor box")=="block-adventure"
    assert infer_party_theme("dinosaur birthday treat box")=="dino-dash"
    assert infer_party_theme("space rocket favor box")=="cosmic-quest"

    leather_route=route_craft_phrase("leather card holder pattern pdf")
    assert leather_route.ready is True
    assert leather_route.format=="LEATHER_PATTERN"

    config=bot.load_config()
    from collections import Counter
    assert bot.score_phrase("sewing pattern print shop near me",Counter({"test":2}),config) is None

    with tempfile.TemporaryDirectory() as tmp:
        root,zip_path,report=build_from_opportunity("printable favor box templates",Path(tmp))
        assert report["ready"] is True, report
        assert zip_path.exists() and zip_path.stat().st_size>0
        assert len(list((root/"Shapes").iterdir()))==5
        assert len(list((root/"Listing-Images").glob("*.png")))==7
        for svg in root.glob("Shapes/*/SVG/*.svg"):
            ET.parse(svg)
        status=json.loads((root/"status.json").read_text(encoding="utf-8"))
        assert status["status"]=="AWAITING_APPROVAL"
        assert status["publishing_enabled"] is False

    with tempfile.TemporaryDirectory() as tmp:
        root,zip_path,report=build_from_opportunity("leather card holder pattern pdf",Path(tmp))
        assert report["ready"] is True, report
        assert zip_path.exists() and zip_path.stat().st_size>0
        assert (root/"Pattern-A4.pdf").exists()
        assert (root/"Pattern-US-Letter.pdf").exists()
        assert len(list((root/"SVG").glob("*.svg")))==2
        status=json.loads((root/"status.json").read_text(encoding="utf-8"))
        assert status["product_type"]=="LEATHER_PATTERN"
        assert status["publishing_enabled"] is False

    print("craft factory phase2 self-test passed")


if __name__=="__main__":
    main()
