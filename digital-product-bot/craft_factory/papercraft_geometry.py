from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple

Point = Tuple[float, float]
Line = Tuple[Point, Point]


@dataclass(frozen=True)
class Face:
    name: str
    x: float
    y: float
    size: float

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.size, self.y + self.size)


@dataclass(frozen=True)
class Tab:
    name: str
    owner: str
    edge: str
    points: tuple[Point, ...]
    fold: Line


@dataclass
class CubeNet:
    size_mm: float
    tab_mm: float
    faces: Dict[str, Face]
    tabs: List[Tab]
    fold_lines: List[Line]
    cut_lines: List[Line]
    width_mm: float
    height_mm: float

    def to_dict(self) -> dict:
        return {
            "size_mm": self.size_mm,
            "tab_mm": self.tab_mm,
            "faces": {k: asdict(v) for k, v in self.faces.items()},
            "tabs": [asdict(t) for t in self.tabs],
            "fold_lines": self.fold_lines,
            "cut_lines": self.cut_lines,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
        }


def _tab(face: Face, edge: str, depth: float, name: str) -> Tab:
    x, y, s = face.x, face.y, face.size
    chamfer = min(depth * 0.35, s * 0.08)

    if edge == "left":
        pts = ((x, y), (x - depth, y + chamfer), (x - depth, y + s - chamfer), (x, y + s))
        fold = ((x, y), (x, y + s))
    elif edge == "right":
        pts = ((x + s, y), (x + s + depth, y + chamfer), (x + s + depth, y + s - chamfer), (x + s, y + s))
        fold = ((x + s, y), (x + s, y + s))
    elif edge == "top":
        pts = ((x, y), (x + chamfer, y - depth), (x + s - chamfer, y - depth), (x + s, y))
        fold = ((x, y), (x + s, y))
    elif edge == "bottom":
        pts = ((x, y + s), (x + chamfer, y + s + depth), (x + s - chamfer, y + s + depth), (x + s, y + s))
        fold = ((x, y + s), (x + s, y + s))
    else:
        raise ValueError(f"Unsupported tab edge: {edge}")

    return Tab(name=name, owner=face.name, edge=edge, points=pts, fold=fold)


def _poly_edges(points: tuple[Point, ...]) -> List[Line]:
    result: List[Line] = []
    for i in range(len(points) - 1):
        result.append((points[i], points[i + 1]))
    return result


def build_cube_net(size_mm: float = 60.0, tab_mm: float = 10.0) -> CubeNet:
    """
    Compact 3 x 4 cube net:
                  TOP
          LEFT  FRONT  RIGHT
                BOTTOM
                 BACK

    This layout fits a 60 mm cube plus 10 mm tabs on both A4 and US Letter.
    """
    s = float(size_mm)
    t = float(tab_mm)
    ox = t
    oy = t

    faces = {
        "top": Face("top", ox + s, oy, s),
        "left": Face("left", ox, oy + s, s),
        "front": Face("front", ox + s, oy + s, s),
        "right": Face("right", ox + 2 * s, oy + s, s),
        "bottom": Face("bottom", ox + s, oy + 2 * s, s),
        "back": Face("back", ox + s, oy + 3 * s, s),
    }

    fold_lines: List[Line] = [
        ((ox + s, oy + s), (ox + 2 * s, oy + s)),          # top-front
        ((ox + s, oy + 2 * s), (ox + 2 * s, oy + 2 * s)),  # front-bottom
        ((ox + s, oy + 3 * s), (ox + 2 * s, oy + 3 * s)),  # bottom-back
        ((ox + s, oy + s), (ox + s, oy + 2 * s)),          # left-front
        ((ox + 2 * s, oy + s), (ox + 2 * s, oy + 2 * s)),  # front-right
    ]

    tabs = [
        _tab(faces["top"], "left", t, "top-left"),
        _tab(faces["top"], "right", t, "top-right"),
        _tab(faces["top"], "top", t, "top-back"),
        _tab(faces["bottom"], "left", t, "bottom-left"),
        _tab(faces["bottom"], "right", t, "bottom-right"),
        _tab(faces["back"], "left", t, "back-left"),
        _tab(faces["back"], "right", t, "back-right"),
    ]

    fold_lines.extend(tab.fold for tab in tabs)

    cut_lines: List[Line] = []

    # Outer exposed face edges that are not replaced by glue tabs.
    left = faces["left"]
    cut_lines += [
        ((left.x, left.y), (left.x + s, left.y)),
        ((left.x, left.y + s), (left.x + s, left.y + s)),
        ((left.x, left.y), (left.x, left.y + s)),
    ]

    right = faces["right"]
    cut_lines += [
        ((right.x, right.y), (right.x + s, right.y)),
        ((right.x, right.y + s), (right.x + s, right.y + s)),
        ((right.x + s, right.y), (right.x + s, right.y + s)),
    ]

    back = faces["back"]
    cut_lines.append(((back.x, back.y + s), (back.x + s, back.y + s)))

    # The three non-fold edges of each tab are cut lines.
    for tab in tabs:
        cut_lines.extend(_poly_edges(tab.points))

    width_mm = 3 * s + 2 * t
    height_mm = 4 * s + 2 * t

    return CubeNet(
        size_mm=s,
        tab_mm=t,
        faces=faces,
        tabs=tabs,
        fold_lines=fold_lines,
        cut_lines=cut_lines,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def fits_paper(net: CubeNet, paper_width_mm: float, paper_height_mm: float, margin_mm: float = 2.0) -> bool:
    return (
        net.width_mm + margin_mm * 2 <= paper_width_mm
        and net.height_mm + margin_mm * 2 <= paper_height_mm
    )
