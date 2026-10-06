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

LEATHER_PATTERN_TERMS = [
    "leather pattern", "wallet pattern", "leather wallet", "card holder pattern",
    "cardholder pattern", "card wallet pattern", "slim wallet pattern",
    "minimalist wallet pattern", "bifold wallet pattern", "bi-fold wallet pattern",
]

CRAFT_PATTERN_TERMS = [
    "sewing pattern", "woodworking plan", "craft pattern", "papercraft", "paper model",
    "stencil", "laser cut", "cricut", "silhouette", "dxf", "svg cut",
]


def route_craft_phrase(phrase: str) -> CraftRoute:
    text = re.sub(r"\s+", " ", phrase.lower()).strip()

    if any(term in text for term in PAPERCRAFT_BOX_TERMS) or "gift box" in text:
        return CraftRoute(
            factory="CRAFT",
            format="PAPERCRAFT",
            ready=True,
            reason="Favor/gift/treat box demand can be built by the multi-shape party box factory with original theme artwork.",
        )

    if any(term in text for term in LEATHER_PATTERN_TERMS) or (
        "leather" in text and any(term in text for term in ["wallet", "card holder", "cardholder"]) and "pattern" in text
    ):
        return CraftRoute(
            factory="CRAFT",
            format="LEATHER_PATTERN",
            ready=True,
            reason="Leather wallet/cardholder demand can be built by the true-size leather pattern factory with PDF, SVG and assembly assets.",
        )

    if "svg" in text and any(term in text for term in ["party", "box", "cut file", "template"]):
        ready = any(term in text for term in ["box", "party", "favor", "favour", "treat", "gift"])
        return CraftRoute(
            factory="CRAFT",
            format="SVG_CUT",
            ready=ready,
            reason=(
                "Party-box SVG can be built by the current multi-shape factory."
                if ready else
                "SVG demand detected, but this cut-file category still needs a dedicated geometry engine."
            ),
        )

    if (
        any(term in text for term in CRAFT_PATTERN_TERMS)
        or ("sewing" in text and "pattern" in text)
        or ("woodworking" in text and ("plan" in text or "pattern" in text))
    ):
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
