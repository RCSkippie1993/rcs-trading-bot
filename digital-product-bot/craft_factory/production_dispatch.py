from __future__ import annotations

from pathlib import Path

from .craft_router import route_craft_phrase


def build_craft_from_opportunity(phrase: str, output_dir: Path):
    route = route_craft_phrase(phrase)
    if not route.ready:
        raise ValueError(f"Craft route is not factory-ready: {route.format} — {route.reason}")

    if route.format in {"PAPERCRAFT", "SVG_CUT"}:
        from .party_box_bundle import build_from_opportunity
        return build_from_opportunity(phrase, output_dir)

    if route.format == "LEATHER_PATTERN":
        from .leather_pattern_factory import build_from_opportunity
        return build_from_opportunity(phrase, output_dir)

    if route.format == "FELT_PATTERN":
        from .felt_pattern_factory import build_from_opportunity
        return build_from_opportunity(phrase, output_dir)

    raise ValueError(f"No production dispatcher is configured for ready craft format {route.format}")
