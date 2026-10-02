from __future__ import annotations

import re

SUPPORTED_SHAPES = ["cube", "treat-box", "gift-box", "milk-carton", "gable-box"]


def shape_for_phrase(phrase: str) -> str:
    text = re.sub(r"\s+", " ", phrase.lower()).strip()
    if "milk carton" in text or "carton box" in text:
        return "milk-carton"
    if "gable" in text:
        return "gable-box"
    if "gift box" in text:
        return "gift-box"
    if "treat box" in text or "cricut" in text:
        return "treat-box"
    if any(term in text for term in ["cube", "pixel box", "voxel box", "block box"]):
        return "cube"
    if any(term in text for term in ["favor box", "favour box", "party box", "box template"]):
        return "bundle"
    return "bundle"


def shapes_for_phrase(phrase: str) -> list[str]:
    shape = shape_for_phrase(phrase)
    return SUPPORTED_SHAPES[:] if shape == "bundle" else [shape]
