from __future__ import annotations

import re

from .theme_engine import Theme, get_theme


THEME_RULES = [
    ("block-adventure", ["pixel", "voxel", "block", "mining", "cube"]),
    ("dino-dash", ["dinosaur", "dino", "jurassic"]),
    ("cosmic-quest", ["space", "galaxy", "rocket", "astronaut", "planet"]),
    ("race-day", ["race car", "racing", "car party", "speed"]),
    ("ocean-magic", ["ocean", "under the sea", "mermaid", "sea party"]),
    ("rainbow-pop", ["rainbow", "confetti", "colour", "color", "birthday"]),
]


def infer_party_theme(phrase: str) -> str:
    text = re.sub(r"\s+", " ", phrase.lower()).strip()
    for slug, terms in THEME_RULES:
        if any(term in text for term in terms):
            return slug
    return "rainbow-pop"


def theme_pack(slug: str) -> list[Theme]:
    if slug == "block-adventure":
        return [
            get_theme("grass-earth"),
            get_theme("stone-crystal"),
            get_theme("red-energy"),
            get_theme("brick-dirt"),
        ]
    return [get_theme(slug)]


def commercial_theme_name(slug: str) -> str:
    if slug == "block-adventure":
        return "Block Adventure"
    return get_theme(slug).display_name
