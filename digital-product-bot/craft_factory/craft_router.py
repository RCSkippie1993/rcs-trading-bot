from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CraftRoute:
    factory: str
    format: str
    ready: bool
    reason: str


PAPERCRAFT_BOX_TERMS = [
    "favor box", "favour box", "treat box", "party box", "cube box",
    "foldable box", "papercraft box", "loot box", "box template",
]

CRAFT_PATTERN_TERMS = [
    "leather pattern", "wallet pattern", "sewing pattern", "woodworking plan",
    "craft pattern", "papercraft", "paper model", "stencil", "laser cut",
    "cricut", "silhouette", "dxf", "svg cut",
]


def route_craft_phrase(phrase: str) -> CraftRoute:
    text = re.sub(r"\s+", " ", phrase.lower()).strip()

    if any(term in text for term in PAPERCRAFT_BOX_TERMS):
        supported_theme = any(term in text for term in [
            "pixel", "voxel", "block adventure", "block party", "block-style", "block style"
        ])
        if supported_theme:
            return CraftRoute(
                factory="CRAFT",
                format="PAPERCRAFT",
                ready=True,
                reason="Block/pixel papercraft box can be built by the current craft geometry and artwork factory.",
            )
        return CraftRoute(
            factory="CRAFT",
            format="PAPERCRAFT",
            ready=False,
            reason="Box geometry is supported, but this theme still needs its own artwork pack before automatic manufacture.",
        )

    if "svg" in text and any(term in text for term in ["party", "box", "cut file", "template"]):
        return CraftRoute(
            factory="CRAFT",
            format="SVG_CUT",
            ready=False,
            reason="SVG demand detected; geometry may be supported but theme-specific cut artwork is not yet universally automated.",
        )

    if any(term in text for term in CRAFT_PATTERN_TERMS):
        return CraftRoute(
            factory="CRAFT",
            format="CRAFT_PATTERN",
            ready=False,
            reason="Craft demand detected, but this pattern type needs a dedicated geometry/pattern engine.",
        )

    if "printable" in text and any(term in text for term in ["party", "kids", "birthday", "craft"]):
        return CraftRoute(
            factory="PRINTABLE",
            format="PDF_PRINTABLE",
            ready=False,
            reason="Printable demand detected; general printable factory is not yet implemented.",
        )

    return CraftRoute(
        factory="NONE",
        format="UNKNOWN",
        ready=False,
        reason="No craft-specific route detected.",
    )
