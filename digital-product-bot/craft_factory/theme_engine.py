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
    motif: str = "pixel"


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
    "cosmic-quest": Theme(
        slug="cosmic-quest",
        display_name="Cosmic Quest",
        palette=["#1A245C", "#3046A5", "#6E5DD8", "#18213E", "#F08BC8"],
        accent="#F5D65B",
        dark="#11172F",
        description="Original space-adventure party palette with stars, planets and geometric rocket accents.",
        motif="space",
    ),
    "dino-dash": Theme(
        slug="dino-dash",
        display_name="Dino Dash",
        palette=["#6EA842", "#4E7F35", "#D49A45", "#8A5C35", "#A7C96B"],
        accent="#F2C84B",
        dark="#35502B",
        description="Original dinosaur-adventure palette using footprints, eggs and jungle geometry without franchise characters.",
        motif="dino",
    ),
    "race-day": Theme(
        slug="race-day",
        display_name="Race Day",
        palette=["#E14A3B", "#252A34", "#F3C548", "#FFFFFF", "#3B78C8"],
        accent="#F3C548",
        dark="#20242B",
        description="Original racing-party palette with checks, numbers and speed-stripe motifs.",
        motif="race",
    ),
    "rainbow-pop": Theme(
        slug="rainbow-pop",
        display_name="Rainbow Pop",
        palette=["#FF6B8A", "#FFB84C", "#65C98B", "#5CB7E8", "#A57BE8"],
        accent="#FFE36B",
        dark="#4A3D65",
        description="Bright original kids-party palette with confetti, stars and playful geometric colour blocks.",
        motif="confetti",
    ),
    "ocean-magic": Theme(
        slug="ocean-magic",
        display_name="Ocean Magic",
        palette=["#2A9DAD", "#4CC8C7", "#6E8FD5", "#8C6ED6", "#F0A7C4"],
        accent="#F7D47A",
        dark="#24506B",
        description="Original undersea party palette with bubbles, shells and wave geometry without licensed characters.",
        motif="ocean",
    ),
}


def get_theme(slug: str) -> Theme:
    if slug not in THEMES:
        raise KeyError(f"Unknown craft theme: {slug}")
    return THEMES[slug]
