from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Theme:
    slug: str
    display_name: str
    palette: List[str]
    accent: str
    dark: str
    description: str


THEMES: Dict[str, Theme] = {
    "grass-earth": Theme(
        slug="grass-earth",
        display_name="Grass & Earth",
        palette=["#65B84A", "#4E9D3A", "#8A613D", "#6E4A31", "#B17A48"],
        accent="#C9E66B",
        dark="#31452B",
        description="Original bright voxel landscape palette with green surface blocks and warm earth tones.",
    ),
    "stone-crystal": Theme(
        slug="stone-crystal",
        display_name="Stone & Crystal",
        palette=["#7D8791", "#69737C", "#919BA3", "#54616A", "#5FC9D8"],
        accent="#9BEAF2",
        dark="#34424B",
        description="Cool stone blocks with original crystal-like cyan accents.",
    ),
    "red-energy": Theme(
        slug="red-energy",
        display_name="Red Energy",
        palette=["#C7423D", "#A83232", "#DD5B4F", "#6D2529", "#F0B84C"],
        accent="#FFD36A",
        dark="#4B1D22",
        description="Original red energy-block design with geometric warning-style accents, not franchise artwork.",
    ),
    "brick-dirt": Theme(
        slug="brick-dirt",
        display_name="Brick & Dirt",
        palette=["#A8583C", "#874632", "#B86E4C", "#74513B", "#C38A5C"],
        accent="#E3B980",
        dark="#50382E",
        description="Warm pixel-brick and earth pattern designed as an original block-adventure theme.",
    ),
}


def get_theme(slug: str) -> Theme:
    if slug not in THEMES:
        raise KeyError(f"Unknown craft theme: {slug}")
    return THEMES[slug]
