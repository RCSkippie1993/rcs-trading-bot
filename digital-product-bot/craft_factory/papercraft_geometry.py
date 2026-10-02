from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

Point = Tuple[float, float]
Line = Tuple[Point, Point]


@dataclass(frozen=True)
class Face:
    name: str
    x: float
    y: float
    width: float
    height: float | None = None

    @property
    def w(self) -> float:
        return float(self.width)

    @property
    def h(self) -> float:
        return float(self.height if self.height is not None else self.width)

    @property
    def size(self) -> float:
        # Backwards-compatible convenience for the original square cube engine.
        return self.w

    @property
    def rect(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.w, self.y + self.h)


@dataclass(frozen=True)
class Tab:
    name: str
    owner: str
    edge: str
    points: tuple[Point, ...]
    fold: Line


@dataclass
class PapercraftNet:
    shape: str
    size_mm: float
    tab_mm: float
    faces: Dict[str, Face]
    tabs: List[Tab]
    fold_lines: List[Line]
    cut_lines: List[Line]
    width_mm: float
    height_mm: float
    assembled_dimensions_mm: tuple[float, float, float]

    def to_dict(self) -> dict:
        return {
            "shape": self.shape,
            "size_mm": self.size_mm,
            "tab_mm": self.tab_mm,
            "faces": {k: asdict(v) for k, v in self.faces.items()},
            "tabs": [asdict(t) for t in self.tabs],
            "fold_lines": self.fold_lines,
            "cut_lines": self.cut_lines,
            "width_mm": self.width_mm,
            "height_mm": self.height_mm,
            "assembled_dimensions_mm": self.assembled_dimensions_mm,
        }


CubeNet = PapercraftNet


def _tab(face: Face, edge: str, depth: float, name: str) -> Tab:
    x, y, w, h = face.x, face.y, face.w, face.h
    edge_length = h if edge in {"left", "right"} else w
    chamfer = min(depth * 0.35, edge_length * 0.08)

    if edge == "left":
        pts = ((x, y), (x - depth, y + chamfer), (x - depth, y + h - chamfer), (x, y + h))
        fold = ((x, y), (x, y + h))
    elif edge == "right":
        pts = ((x + w, y), (x + w + depth, y + chamfer), (x + w + depth, y + h - chamfer), (x + w, y + h))
        fold = ((x + w, y), (x + w, y + h))
    elif edge == "top":
        pts = ((x, y), (x + chamfer, y - depth), (x + w - chamfer, y - depth), (x + w, y))
        fold = ((x, y), (x + w, y))
    elif edge == "bottom":
        pts = ((x, y + h), (x + chamfer, y + h + depth), (x + w - chamfer, y + h + depth), (x + w, y + h))
        fold = ((x, y + h), (x + w, y + h))
    else:
        raise ValueError(f"Unsupported tab edge: {edge}")

    return Tab(name=name, owner=face.name, edge=edge, points=pts, fold=fold)


def _poly_edges(points: tuple[Point, ...]) -> List[Line]:
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _tab_cut_lines(tabs: List[Tab]) -> List[Line]:
    lines: List[Line] = []
    for tab in tabs:
        lines.extend(_poly_edges(tab.points))
    return lines


def build_cube_net(size_mm: float = 60.0, tab_mm: float = 10.0) -> PapercraftNet:
    s = float(size_mm)
    t = float(tab_mm)
    ox, oy = t, t

    faces = {
        "top": Face("top", ox + s, oy, s),
        "left": Face("left", ox, oy + s, s),
        "front": Face("front", ox + s, oy + s, s),
        "right": Face("right", ox + 2 * s, oy + s, s),
        "bottom": Face("bottom", ox + s, oy + 2 * s, s),
        "back": Face("back", ox + s, oy + 3 * s, s),
    }

    fold_lines: List[Line] = [
        ((ox + s, oy + s), (ox + 2 * s, oy + s)),
        ((ox + s, oy + 2 * s), (ox + 2 * s, oy + 2 * s)),
        ((ox + s, oy + 3 * s), (ox + 2 * s, oy + 3 * s)),
        ((ox + s, oy + s), (ox + s, oy + 2 * s)),
        ((ox + 2 * s, oy + s), (ox + 2 * s, oy + 2 * s)),
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

    left = faces["left"]
    right = faces["right"]
    back = faces["back"]
    cut_lines: List[Line] = [
        ((left.x, left.y), (left.x + s, left.y)),
        ((left.x, left.y + s), (left.x + s, left.y + s)),
        ((left.x, left.y), (left.x, left.y + s)),
        ((right.x, right.y), (right.x + s, right.y)),
        ((right.x, right.y + s), (right.x + s, right.y + s)),
        ((right.x + s, right.y), (right.x + s, right.y + s)),
        ((back.x, back.y + s), (back.x + s, back.y + s)),
    ]
    cut_lines.extend(_tab_cut_lines(tabs))

    return PapercraftNet(
        shape="cube",
        size_mm=s,
        tab_mm=t,
        faces=faces,
        tabs=tabs,
        fold_lines=fold_lines,
        cut_lines=cut_lines,
        width_mm=3 * s + 2 * t,
        height_mm=4 * s + 2 * t,
        assembled_dimensions_mm=(s, s, s),
    )


def _build_tuck_box(
    shape: str,
    width_mm: float,
    depth_mm: float,
    height_mm: float,
    flap_mm: float,
    tab_mm: float,
) -> PapercraftNet:
    w, d, h, f, t = map(float, (width_mm, depth_mm, height_mm, flap_mm, tab_mm))
    x0, y0 = t, f
    widths = [w, d, w, d]
    names = ["front", "right", "back", "left"]

    faces: Dict[str, Face] = {}
    x = x0
    for name, pw in zip(names, widths):
        faces[name] = Face(name, x, y0, pw, h)
        x += pw
    strip_right = x

    tabs: List[Tab] = []
    for name in names:
        face = faces[name]
        top_depth = min(f, face.w * 0.62)
        bottom_depth = min(f, face.w * 0.62)
        tabs.append(_tab(face, "top", top_depth, f"{name}-top"))
        tabs.append(_tab(face, "bottom", bottom_depth, f"{name}-bottom"))
    tabs.append(_tab(faces["left"], "right", t, "side-seam"))

    fold_lines: List[Line] = [tab.fold for tab in tabs]
    for name in ["right", "back", "left"]:
        fx = faces[name].x
        fold_lines.append(((fx, y0), (fx, y0 + h)))

    cut_lines: List[Line] = [
        ((x0, y0), (x0, y0 + h)),
    ]
    cut_lines.extend(_tab_cut_lines(tabs))

    return PapercraftNet(
        shape=shape,
        size_mm=max(w, d, h),
        tab_mm=t,
        faces=faces,
        tabs=tabs,
        fold_lines=fold_lines,
        cut_lines=cut_lines,
        width_mm=strip_right + t,
        height_mm=h + 2 * f,
        assembled_dimensions_mm=(w, d, h),
    )


def build_treat_box_net(
    width_mm: float = 36.0,
    depth_mm: float = 26.0,
    height_mm: float = 72.0,
    flap_mm: float = 20.0,
    tab_mm: float = 8.0,
) -> PapercraftNet:
    return _build_tuck_box("treat-box", width_mm, depth_mm, height_mm, flap_mm, tab_mm)


def build_gift_box_net(
    width_mm: float = 50.0,
    depth_mm: float = 35.0,
    height_mm: float = 45.0,
    flap_mm: float = 22.0,
    tab_mm: float = 8.0,
) -> PapercraftNet:
    return _build_tuck_box("gift-box", width_mm, depth_mm, height_mm, flap_mm, tab_mm)


def _roof_tab(face: Face, depth: float, name: str, peak: bool) -> Tab:
    x, y, w = face.x, face.y, face.w
    if peak:
        shoulder = depth * 0.45
        ridge = min(12.0, w * 0.28)
        cx = x + w / 2
        pts = (
            (x, y),
            (x, y - shoulder),
            (cx - ridge / 2, y - depth),
            (cx + ridge / 2, y - depth),
            (x + w, y - shoulder),
            (x + w, y),
        )
    else:
        inset = min(w * 0.18, depth * 0.5)
        pts = (
            (x, y),
            (x + inset, y - depth),
            (x + w - inset, y - depth),
            (x + w, y),
        )
    return Tab(name=name, owner=face.name, edge="top", points=pts, fold=((x, y), (x + w, y)))


def build_milk_carton_net(
    width_mm: float = 38.0,
    depth_mm: float = 28.0,
    height_mm: float = 65.0,
    roof_mm: float = 30.0,
    bottom_flap_mm: float = 18.0,
    tab_mm: float = 8.0,
) -> PapercraftNet:
    w, d, h, roof, bf, t = map(float, (width_mm, depth_mm, height_mm, roof_mm, bottom_flap_mm, tab_mm))
    x0, y0 = t, roof
    widths = [w, d, w, d]
    names = ["front", "right", "back", "left"]

    faces: Dict[str, Face] = {}
    x = x0
    for name, pw in zip(names, widths):
        faces[name] = Face(name, x, y0, pw, h)
        x += pw
    strip_right = x

    tabs: List[Tab] = []
    for name in names:
        tabs.append(_tab(faces[name], "bottom", min(bf, faces[name].w * 0.58), f"{name}-bottom"))
    for name in ["front", "back"]:
        tabs.append(_roof_tab(faces[name], roof, f"{name}-gable", peak=True))
    for name in ["right", "left"]:
        tabs.append(_roof_tab(faces[name], roof * 0.76, f"{name}-roof", peak=False))
    tabs.append(_tab(faces["left"], "right", t, "side-seam"))

    fold_lines: List[Line] = [tab.fold for tab in tabs]
    for name in ["right", "back", "left"]:
        fx = faces[name].x
        fold_lines.append(((fx, y0), (fx, y0 + h)))
    # Extra roof score lines help the side roof panels collapse inward.
    for name in ["right", "left"]:
        face = faces[name]
        fold_lines.append(((face.x + face.w / 2, y0), (face.x + face.w / 2, y0 - roof * 0.70)))

    cut_lines: List[Line] = [((x0, y0), (x0, y0 + h))]
    cut_lines.extend(_tab_cut_lines(tabs))

    return PapercraftNet(
        shape="milk-carton",
        size_mm=max(w, d, h + roof),
        tab_mm=t,
        faces=faces,
        tabs=tabs,
        fold_lines=fold_lines,
        cut_lines=cut_lines,
        width_mm=strip_right + t,
        height_mm=roof + h + bf,
        assembled_dimensions_mm=(w, d, h + roof * 0.58),
    )


def _gable_handle_tab(face: Face, depth: float, name: str) -> tuple[Tab, List[Line]]:
    x, y, w = face.x, face.y, face.w
    shoulder = depth * 0.42
    handle_w = min(20.0, w * 0.52)
    cx = x + w / 2
    pts = (
        (x, y),
        (x, y - shoulder),
        (cx - handle_w / 2, y - depth),
        (cx + handle_w / 2, y - depth),
        (x + w, y - shoulder),
        (x + w, y),
    )
    tab = Tab(name=name, owner=face.name, edge="top", points=pts, fold=((x, y), (x + w, y)))
    hole_y = y - depth + 6.0
    hole_h = 5.0
    hole_left = cx - handle_w * 0.32
    hole_right = cx + handle_w * 0.32
    hole = [
        ((hole_left, hole_y), (hole_right, hole_y)),
        ((hole_right, hole_y), (hole_right, hole_y + hole_h)),
        ((hole_right, hole_y + hole_h), (hole_left, hole_y + hole_h)),
        ((hole_left, hole_y + hole_h), (hole_left, hole_y)),
    ]
    return tab, hole


def build_gable_box_net(
    width_mm: float = 45.0,
    depth_mm: float = 28.0,
    height_mm: float = 58.0,
    gable_mm: float = 34.0,
    bottom_flap_mm: float = 18.0,
    tab_mm: float = 8.0,
) -> PapercraftNet:
    w, d, h, g, bf, t = map(float, (width_mm, depth_mm, height_mm, gable_mm, bottom_flap_mm, tab_mm))
    x0, y0 = t, g
    widths = [w, d, w, d]
    names = ["front", "right", "back", "left"]

    faces: Dict[str, Face] = {}
    x = x0
    for name, pw in zip(names, widths):
        faces[name] = Face(name, x, y0, pw, h)
        x += pw
    strip_right = x

    tabs: List[Tab] = []
    internal_cut_lines: List[Line] = []
    for name in names:
        tabs.append(_tab(faces[name], "bottom", min(bf, faces[name].w * 0.58), f"{name}-bottom"))
    for name in ["front", "back"]:
        tab, hole = _gable_handle_tab(faces[name], g, f"{name}-handle")
        tabs.append(tab)
        internal_cut_lines.extend(hole)
    for name in ["right", "left"]:
        face = faces[name]
        x, y, pw = face.x, face.y, face.w
        pts = ((x, y), (x + pw / 2, y - g * 0.62), (x + pw, y))
        tabs.append(Tab(f"{name}-gusset", name, "top", pts, ((x, y), (x + pw, y))))

    tabs.append(_tab(faces["left"], "right", t, "side-seam"))

    fold_lines: List[Line] = [tab.fold for tab in tabs]
    for name in ["right", "back", "left"]:
        fx = faces[name].x
        fold_lines.append(((fx, y0), (fx, y0 + h)))
    for name in ["right", "left"]:
        face = faces[name]
        fold_lines.append(((face.x + face.w / 2, y0), (face.x + face.w / 2, y0 - g * 0.62)))

    cut_lines: List[Line] = [((x0, y0), (x0, y0 + h))]
    cut_lines.extend(_tab_cut_lines(tabs))
    cut_lines.extend(internal_cut_lines)

    return PapercraftNet(
        shape="gable-box",
        size_mm=max(w, d, h + g),
        tab_mm=t,
        faces=faces,
        tabs=tabs,
        fold_lines=fold_lines,
        cut_lines=cut_lines,
        width_mm=strip_right + t,
        height_mm=g + h + bf,
        assembled_dimensions_mm=(w, d, h + g * 0.45),
    )


SHAPE_BUILDERS = {
    "cube": build_cube_net,
    "treat-box": build_treat_box_net,
    "gift-box": build_gift_box_net,
    "milk-carton": build_milk_carton_net,
    "gable-box": build_gable_box_net,
}


def build_shape_net(shape: str, **kwargs) -> PapercraftNet:
    if shape not in SHAPE_BUILDERS:
        raise KeyError(f"Unknown papercraft shape: {shape}")
    return SHAPE_BUILDERS[shape](**kwargs)


def fits_paper(net: PapercraftNet, paper_width_mm: float, paper_height_mm: float, margin_mm: float = 2.0) -> bool:
    return (
        net.width_mm + margin_mm * 2 <= paper_width_mm
        and net.height_mm + margin_mm * 2 <= paper_height_mm
    )
