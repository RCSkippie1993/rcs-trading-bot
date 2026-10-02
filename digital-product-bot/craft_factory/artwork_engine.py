from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Dict

from PIL import Image, ImageDraw

from .theme_engine import Theme
from .papercraft_geometry import PapercraftNet


def _seed(theme: str, face: str) -> int:
    digest = hashlib.sha256(f"{theme}:{face}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _pixel_grid(theme: Theme, face: str, size_px: int) -> Image.Image:
    rnd = random.Random(_seed(theme.slug, face))
    image = Image.new("RGB", (size_px, size_px), theme.palette[0])
    draw = ImageDraw.Draw(image)

    cells = 18
    cell = max(1, size_px // cells)

    for row in range(cells + 1):
        for col in range(cells + 1):
            x0, y0 = col * cell, row * cell
            x1, y1 = min(size_px, x0 + cell + 1), min(size_px, y0 + cell + 1)
            color = rnd.choice(theme.palette)
            draw.rectangle((x0, y0, x1, y1), fill=color)

    if theme.slug == "grass-earth":
        if face == "top":
            for _ in range(28):
                x = rnd.randrange(0, cells) * cell
                y = rnd.randrange(0, cells) * cell
                draw.rectangle((x, y, x + cell, y + cell), fill=rnd.choice(["#77C95A", "#5AAE43", "#93D16A"]))
        elif face != "bottom":
            band = int(size_px * 0.23)
            draw.rectangle((0, 0, size_px, band), fill="#58A943")
            for _ in range(18):
                x = rnd.randrange(0, cells) * cell
                y = rnd.randrange(max(1, int(cells * 0.25)), cells) * cell
                draw.rectangle((x, y, x + cell, y + cell), fill=rnd.choice(["#8A613D", "#6E4A31", "#B17A48"]))

    elif theme.slug == "stone-crystal":
        for _ in range(18):
            x = rnd.randrange(1, cells - 1) * cell
            y = rnd.randrange(1, cells - 1) * cell
            draw.polygon(
                [(x, y + cell), (x + cell // 2, y), (x + cell, y + cell), (x + cell // 2, y + cell * 2)],
                fill=rnd.choice([theme.accent, "#49AFC2", "#79DAE3"]),
            )

    elif theme.slug == "red-energy":
        for i in range(0, size_px, cell * 4):
            draw.line((0, i, size_px, min(size_px, i + size_px // 3)), fill=theme.accent, width=max(2, cell // 5))
        for _ in range(10):
            x = rnd.randrange(0, cells - 2) * cell
            y = rnd.randrange(0, cells - 2) * cell
            draw.rectangle((x, y, x + cell * 2, y + cell), outline=theme.dark, width=max(2, cell // 5))

    elif theme.slug == "brick-dirt":
        brick_h = max(cell * 2, 8)
        brick_w = max(cell * 4, 16)
        for y in range(0, size_px, brick_h):
            offset = 0 if (y // brick_h) % 2 == 0 else brick_w // 2
            for x in range(-offset, size_px, brick_w):
                fill = rnd.choice(theme.palette[:3])
                draw.rectangle((x + 2, y + 2, x + brick_w - 2, y + brick_h - 2), fill=fill, outline=theme.dark, width=2)

    # Original small pixel accents to keep the design playful and distinct.
    for _ in range(9):
        x = rnd.randrange(1, cells - 2) * cell
        y = rnd.randrange(1, cells - 2) * cell
        draw.rectangle((x, y, x + cell, y + cell), fill=theme.accent)

    return image


def generate_face_art(theme: Theme, size_px: int = 720) -> Dict[str, Image.Image]:
    faces = {}
    for face in ["top", "left", "front", "right", "bottom", "back"]:
        faces[face] = _pixel_grid(theme, face, size_px)
    return faces


def generate_art_for_net(theme: Theme, net: PapercraftNet, dpi: int = 300) -> Dict[str, Image.Image]:
    artwork: Dict[str, Image.Image] = {}
    for name, face in net.faces.items():
        width_px = max(240, round(face.w / 25.4 * dpi))
        height_px = max(240, round(face.h / 25.4 * dpi))
        base = _pixel_grid(theme, name, max(width_px, height_px))
        artwork[name] = base.resize((width_px, height_px), Image.Resampling.NEAREST)
    return artwork


def save_face_art(face_art: Dict[str, Image.Image], folder: Path, prefix: str) -> Dict[str, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for face, image in face_art.items():
        path = folder / f"{prefix}-{face}.png"
        image.save(path, "PNG", optimize=True)
        paths[face] = path
    return paths
