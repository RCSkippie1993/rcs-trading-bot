from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from .artwork_engine import generate_face_art
from .assembly_guide import export_assembly_guide
from .craft_listing_assets import create_listing_images
from .craft_quality import validate_product
from .papercraft_geometry import build_cube_net
from .pdf_export import export_print_pdf, render_flat_preview
from .svg_export import export_svg
from .theme_engine import get_theme


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "craft_config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _write_listing(root: Path, config: dict) -> dict:
    listing = {
        "title": "Block Adventure Party Favor Box Kit | Printable Pixel Cube Boxes | PDF SVG Digital Download",
        "short_description": "Four original block-adventure favor box designs supplied as print-ready PDF and SVG files.",
        "description": (
            "Create colourful party favor boxes with this original block-adventure printable kit. "
            "The download includes four coordinated designs, A4 and US Letter print-ready PDFs, "
            "SVG cut files and a simple assembly guide. Print at actual size, cut the solid lines, "
            "fold the dashed lines and glue the tabs inside the box.\n\n"
            "This is an original voxel/pixel-style party product. It is not official franchise merchandise "
            "and does not include copied game logos, characters or textures."
        ),
        "tags": [
            "pixel party", "block party", "favor box", "party printable",
            "cube box", "papercraft", "svg box", "kids party",
            "treat box", "digital download", "voxel party", "party craft", "printable box"
        ],
        "assembled_size_mm": [config["box_size_mm"]] * 3,
        "formats": ["PDF", "SVG"],
        "paper_sizes": ["A4", "US Letter"],
        "designs": config["themes"],
        "approval_status": "AWAITING_APPROVAL",
    }
    (root / "marketplace-listing.json").write_text(json.dumps(listing, indent=2), encoding="utf-8")
    return listing


def _zip_product(root: Path) -> Path:
    zip_path = root.parent / f"{root.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{root.name}/{path.relative_to(root)}")
    return zip_path


def build_product(output_dir: Path) -> tuple[Path, Path, dict]:
    config = load_config()
    root = output_dir / config["slug"]
    if root.exists():
        shutil.rmtree(root)

    for folder in ["A4", "US-Letter", "SVG", "Preview", "Listing-Images"]:
        (root / folder).mkdir(parents=True, exist_ok=True)

    net = build_cube_net(config["box_size_mm"], config["glue_tab_mm"])
    dpi = int(config["artwork_dpi"])
    face_px = max(600, round(config["box_size_mm"] / 25.4 * dpi))

    face_art_by_theme = {}
    theme_map = {}
    flat_previews = {}

    for theme_slug in config["themes"]:
        theme = get_theme(theme_slug)
        theme_map[theme_slug] = theme
        face_art = generate_face_art(theme, size_px=face_px)
        face_art_by_theme[theme_slug] = face_art

        export_print_pdf(
            root / "A4" / f"{theme_slug}.pdf",
            net,
            face_art,
            theme,
            tuple(config["paper_sizes"]["A4"]),
            f"{theme.display_name} - A4",
        )
        export_print_pdf(
            root / "US-Letter" / f"{theme_slug}.pdf",
            net,
            face_art,
            theme,
            tuple(config["paper_sizes"]["US_LETTER"]),
            f"{theme.display_name} - US Letter",
        )
        export_svg(root / "SVG" / f"{theme_slug}.svg", net, face_art, theme)
        flat_previews[theme_slug] = render_flat_preview(
            root / "Preview" / f"{theme_slug}-flat.png",
            net,
            face_art,
            theme,
        )

    export_assembly_guide(root / "assembly-guide.pdf", net, config["product_name"])

    (root / "printing-guide.txt").write_text(
        "PRINTING GUIDE\n\n"
        "1. Open the PDF for your paper size.\n"
        "2. Print at 100% / Actual Size. Do not select Fit, Shrink or Scale to Page.\n"
        "3. Use cardstock suitable for your printer; approximately 160-220 gsm is a practical range.\n"
        "4. Solid lines are cut lines. Dashed lines are fold/score lines.\n"
        "5. Adult supervision is recommended for cutting and assembly.\n",
        encoding="utf-8",
    )

    _write_listing(root, config)
    (root / "status.json").write_text(
        json.dumps(
            {
                "status": "AWAITING_APPROVAL",
                "publishing_enabled": False,
                "factory": "CRAFT",
                "product_type": "PAPERCRAFT",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    create_listing_images(
        root / "Listing-Images",
        theme_map,
        face_art_by_theme,
        flat_previews,
        float(config["box_size_mm"]),
    )

    report = validate_product(
        root,
        net,
        config["paper_sizes"],
        config["themes"],
        config["ip_safety"]["prohibited_commercial_terms"],
    )

    (root / "geometry.json").write_text(json.dumps(net.to_dict(), indent=2), encoding="utf-8")

    zip_path = _zip_product(root)
    return root, zip_path, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="craft-output", help="Folder in which to build the product.")
    args = parser.parse_args()

    root, zip_path, report = build_product(Path(args.output_dir))
    print(json.dumps({
        "product_folder": str(root),
        "zip": str(zip_path),
        "quality_ready": report["ready"],
        "checks": report["checks"],
    }, indent=2))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
