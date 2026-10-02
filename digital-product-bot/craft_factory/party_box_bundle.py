from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import bot

from .artwork_engine import generate_art_for_net
from .box_shape_router import shapes_for_phrase
from .papercraft_geometry import build_shape_net
from .party_bundle_guide import export_bundle_guide
from .party_bundle_listing_assets import create_bundle_listing_images
from .party_bundle_quality import validate_shape_bundle
from .party_theme_engine import commercial_theme_name, infer_party_theme, theme_pack
from .pdf_export import export_print_pdf, render_flat_preview
from .svg_export import export_svg

BASE_DIR=Path(__file__).resolve().parent
CONFIG_PATH=BASE_DIR/"craft_config.json"


def load_config()->dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _shape_kwargs(shape:str)->dict:
    return {
        "cube": {"size_mm":60.0,"tab_mm":10.0},
        "treat-box": {"width_mm":36.0,"depth_mm":26.0,"height_mm":72.0,"flap_mm":20.0,"tab_mm":8.0},
        "gift-box": {"width_mm":50.0,"depth_mm":35.0,"height_mm":45.0,"flap_mm":22.0,"tab_mm":8.0},
        "milk-carton": {"width_mm":38.0,"depth_mm":28.0,"height_mm":65.0,"roof_mm":30.0,"bottom_flap_mm":18.0,"tab_mm":8.0},
        "gable-box": {"width_mm":45.0,"depth_mm":28.0,"height_mm":58.0,"gable_mm":34.0,"bottom_flap_mm":18.0,"tab_mm":8.0},
    }[shape]


def _commercial_title(phrase:str,theme_slug:str,shape_count:int)->str:
    from phase3_copy import human_product_name
    base=human_product_name(phrase)
    if shape_count>1:
        return f"{commercial_theme_name(theme_slug)} Favor Box Shape Bundle | 5 Printable PDF & SVG Box Patterns"
    return base


def _listing(phrase:str,theme_slug:str,shapes:list[str],themes)->dict:
    title=_commercial_title(phrase,theme_slug,len(shapes))
    return {
        "title":title[:140],
        "short_description":(
            f"Original {commercial_theme_name(theme_slug)} kids-party box craft files with "
            f"{len(shapes)} printable shape{'s' if len(shapes)!=1 else ''}, supplied as PDF and SVG."
        ),
        "description":(
            f"Create coordinated party favor boxes with this original {commercial_theme_name(theme_slug)} digital craft kit. "
            f"The bundle includes {', '.join(s.replace('-',' ') for s in shapes)} shapes, true-size A4 and US Letter PDFs, "
            "SVG cut files, assembled-size information and an assembly guide. Print at 100% / Actual Size, cut solid lines, "
            "score dashed lines and glue the tabs inside the box.\n\n"
            "Artwork is original and theme-inspired. No physical product is shipped and no licensed character artwork is included."
        ),
        "tags":[
            "favor box","party printable","papercraft","svg box","kids party",
            "treat box","gift box","digital download","box template","party craft",
            "printable box","cricut box","birthday printable"
        ],
        "formats":["PDF","SVG"],
        "paper_sizes":["A4","US Letter"],
        "shapes":shapes,
        "themes":[t.slug for t in themes],
        "theme_family":theme_slug,
        "source_phrase":phrase,
        "approval_status":"AWAITING_APPROVAL",
    }


def _zip(root:Path)->Path:
    path=root.parent/f"{root.name}.zip"
    if path.exists(): path.unlink()
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for item in sorted(root.rglob("*")):
            if item.is_file():
                z.write(item,arcname=f"{root.name}/{item.relative_to(root)}")
    return path


def build_from_opportunity(phrase:str,output_dir:Path)->tuple[Path,Path,dict]:
    config=load_config()
    theme_slug=infer_party_theme(phrase)
    themes=theme_pack(theme_slug)
    shapes=shapes_for_phrase(phrase)

    root=output_dir/f"craft-{bot.slugify(phrase)}"
    if root.exists(): shutil.rmtree(root)
    (root/"Listing-Images").mkdir(parents=True,exist_ok=True)

    paper_sizes=config["paper_sizes"]
    nets={}
    first_previews={}
    shape_dimensions={}

    for shape in shapes:
        net=build_shape_net(shape,**_shape_kwargs(shape))
        nets[shape]=net
        shape_dimensions[shape]=net.assembled_dimensions_mm

        for folder in ["A4","US-Letter","SVG","Preview"]:
            (root/"Shapes"/shape/folder).mkdir(parents=True,exist_ok=True)

        for theme in themes:
            art=generate_art_for_net(theme,net,dpi=int(config.get("artwork_dpi",300)))
            export_print_pdf(
                root/"Shapes"/shape/"A4"/f"{theme.slug}.pdf",
                net,art,theme,tuple(paper_sizes["A4"]),
                f"{theme.display_name} {shape.replace('-',' ').title()} - A4",
            )
            export_print_pdf(
                root/"Shapes"/shape/"US-Letter"/f"{theme.slug}.pdf",
                net,art,theme,tuple(paper_sizes["US_LETTER"]),
                f"{theme.display_name} {shape.replace('-',' ').title()} - US Letter",
            )
            export_svg(root/"Shapes"/shape/"SVG"/f"{theme.slug}.svg",net,art,theme)
            preview=render_flat_preview(
                root/"Shapes"/shape/"Preview"/f"{theme.slug}-flat.png",
                net,art,theme,
            )
            first_previews.setdefault(shape,preview)

    listing=_listing(phrase,theme_slug,shapes,themes)
    (root/"marketplace-listing.json").write_text(json.dumps(listing,indent=2),encoding="utf-8")
    (root/"status.json").write_text(json.dumps({
        "status":"AWAITING_APPROVAL",
        "publishing_enabled":False,
        "factory":"CRAFT",
        "product_type":"PAPERCRAFT_BUNDLE",
        "source_phrase":phrase,
        "theme_family":theme_slug,
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
    },indent=2),encoding="utf-8")

    export_bundle_guide(root/"assembly-guide.pdf",listing["title"],shape_dimensions)
    create_bundle_listing_images(
        root/"Listing-Images",
        listing["title"],
        commercial_theme_name(theme_slug),
        themes,
        first_previews,
        shape_dimensions,
    )

    (root/"shape-manifest.json").write_text(json.dumps({
        "source_phrase":phrase,
        "theme_family":theme_slug,
        "shapes":{name:net.to_dict() for name,net in nets.items()},
    },indent=2),encoding="utf-8")

    report=validate_shape_bundle(
        root,nets,paper_sizes,[t.slug for t in themes],
        config["ip_safety"]["prohibited_commercial_terms"],
    )
    zip_path=_zip(root)
    return root,zip_path,report
