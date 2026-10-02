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

    elif theme.motif == "space":
        for _ in range(34):
            x = rnd.randrange(0, size_px)
            y = rnd.randrange(0, size_px)
            r = rnd.choice([2, 3, 5, 7])
            draw.ellipse((x-r, y-r, x+r, y+r), fill=rnd.choice([theme.accent, "#FFFFFF", "#F08BC8"]))
        for _ in range(4):
            x = rnd.randrange(cell * 2, size_px - cell * 3)
            y = rnd.randrange(cell * 2, size_px - cell * 3)
            r = rnd.randrange(cell, cell * 2)
            draw.ellipse((x-r, y-r, x+r, y+r), fill=rnd.choice(theme.palette[1:4]))
            draw.arc((x-r*2, y-r//2, x+r*2, y+r//2), 0, 360, fill=theme.accent, width=max(2, cell//5))

    elif theme.motif == "dino":
        for _ in range(18):
            x = rnd.randrange(cell, size_px-cell*2)
            y = rnd.randrange(cell, size_px-cell*2)
            foot = max(4, cell // 2)
            draw.ellipse((x, y, x+foot, y+foot*2), fill=theme.dark)
            draw.ellipse((x+foot, y-foot//2, x+foot*2, y+foot), fill=theme.dark)
            draw.ellipse((x-foot//2, y-foot//2, x+foot//2, y+foot), fill=theme.dark)
        for _ in range(6):
            x = rnd.randrange(cell, size_px-cell*3)
            y = rnd.randrange(cell, size_px-cell*3)
            draw.ellipse((x, y, x+cell*2, y+cell*3), fill=theme.accent, outline=theme.dark, width=max(2, cell//5))

    elif theme.motif == "race":
        block = max(8, cell * 2)
        for y in range(0, size_px, block):
            for x in range(0, size_px, block):
                if (x // block + y // block) % 2 == 0:
                    draw.rectangle((x, y, x+block, y+block), fill="#FFFFFF")
                else:
                    draw.rectangle((x, y, x+block, y+block), fill=theme.dark)
        for stripe in range(-size_px, size_px*2, block*5):
            draw.line((stripe, 0, stripe-size_px, size_px), fill=theme.accent, width=max(4, cell))

    elif theme.motif == "confetti":
        for _ in range(60):
            x = rnd.randrange(0, size_px)
            y = rnd.randrange(0, size_px)
            length = rnd.randrange(max(4, cell//2), max(8, cell*2))
            color = rnd.choice(theme.palette + [theme.accent])
            if rnd.random() < 0.5:
                draw.ellipse((x, y, x+length, y+length), fill=color)
            else:
                draw.rectangle((x, y, x+length, y+max(3, length//3)), fill=color)

    elif theme.motif == "ocean":
        wave_h = max(10, cell * 2)
        for y in range(0, size_px + wave_h, wave_h):
            color = rnd.choice(theme.palette[:4])
            for x in range(-wave_h, size_px + wave_h, wave_h):
                draw.arc((x, y-wave_h//2, x+wave_h*2, y+wave_h), 180, 360, fill=color, width=max(4, cell//2))
        for _ in range(26):
            x = rnd.randrange(0, size_px)
            y = rnd.randrange(0, size_px)
            r = rnd.randrange(max(3, cell//4), max(5, cell))
            draw.ellipse((x-r, y-r, x+r, y+r), outline=theme.accent, width=max(2, cell//5))

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
