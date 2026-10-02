from __future__ import annotations

import json
import os
from pathlib import Path

import etsy_adapter


def validate(folder: Path, delivery_zip: Path, listing: dict, require_etsy: bool = False) -> dict:
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("delivery_zip", delivery_zip.exists() and delivery_zip.stat().st_size > 0, str(delivery_zip))
    add("workbook", any(folder.glob("*.xlsx")), "At least one XLSX workbook is required.")
    add("starter_csv", any(folder.glob("*.csv")), "At least one CSV file is required.")
    add("buyer_guide", (folder / "buyer-guide.md").exists(), "buyer-guide.md must exist.")

    images = sorted(folder.glob("listing-image-*.png"))
    add("listing_images", len(images) >= 7, f"{len(images)} listing images found; 7 required.")

    title = str(listing.get("title", ""))
    add("title", 1 <= len(title) <= 140, f"Title length: {len(title)} / 140.")

    description = str(listing.get("description", ""))
    add("description", len(description) >= 250, f"Description length: {len(description)} characters.")

    tags = listing.get("etsy_tags", [])
    add("etsy_tags_count", 1 <= len(tags) <= 13, f"{len(tags)} tags supplied.")
    bad_tags = [tag for tag in tags if len(tag) > 20]
    add("etsy_tag_lengths", not bad_tags, "All tags <= 20 characters." if not bad_tags else f"Too long: {bad_tags}")

    price = listing.get("price_usd")
    add("price", isinstance(price, (int, float)) and float(price) > 0, f"Price: {price}")

    status_path = folder / "status.json"
    status = {}
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
    add(
        "approval_status",
        status.get("status") in {"APPROVED_NOT_PUBLISHED", "ETSY_DRAFT_CREATED"},
        f"Status: {status.get('status')}",
    )

    if require_etsy:
        missing = etsy_adapter.missing_settings()
        add("etsy_connection", not missing, "Connected." if not missing else "Missing: " + ", ".join(missing))

    passed = all(item["passed"] for item in checks)
    report = {
        "ready": passed,
        "require_etsy": require_etsy,
        "checks": checks,
    }
    (folder / "publish-readiness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def failure_summary(report: dict) -> str:
    failed = [item for item in report.get("checks", []) if not item.get("passed")]
    if not failed:
        return "All readiness checks passed."
    return "; ".join(f"{item['name']}: {item['detail']}" for item in failed)



def validate_craft(folder: Path, delivery_zip: Path, listing: dict, require_etsy: bool = False) -> dict:
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("delivery_zip", delivery_zip.exists() and delivery_zip.stat().st_size > 0, str(delivery_zip))

    a4_pdfs = list(folder.glob("Shapes/*/A4/*.pdf"))
    letter_pdfs = list(folder.glob("Shapes/*/US-Letter/*.pdf"))
    svgs = list(folder.glob("Shapes/*/SVG/*.svg"))
    add("a4_pdfs", len(a4_pdfs) >= 1, f"{len(a4_pdfs)} A4 PDF files found.")
    add("letter_pdfs", len(letter_pdfs) >= 1, f"{len(letter_pdfs)} US Letter PDF files found.")
    add("svg_files", len(svgs) >= 1, f"{len(svgs)} SVG files found.")
    add("assembly_guide", (folder / "assembly-guide.pdf").exists(), "assembly-guide.pdf must exist.")

    images = sorted((folder / "Listing-Images").glob("listing-image-*.png"))
    add("listing_images", len(images) >= 7, f"{len(images)} listing images found; 7 required.")

    title = str(listing.get("title", ""))
    add("title", 1 <= len(title) <= 140, f"Title length: {len(title)} / 140.")

    description = str(listing.get("description", ""))
    add("description", len(description) >= 250, f"Description length: {len(description)} characters.")

    tags = listing.get("etsy_tags", listing.get("tags", []))
    add("etsy_tags_count", 1 <= len(tags) <= 13, f"{len(tags)} tags supplied.")
    bad_tags = [tag for tag in tags if len(tag) > 20]
    add("etsy_tag_lengths", not bad_tags, "All tags <= 20 characters." if not bad_tags else f"Too long: {bad_tags}")

    price = listing.get("price_usd")
    add("price", isinstance(price, (int, float)) and float(price) > 0, f"Price: {price}")

    status_path = folder / "status.json"
    status = {}
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
    add(
        "approval_status",
        status.get("status") in {"APPROVED_NOT_PUBLISHED", "ETSY_DRAFT_CREATED"},
        f"Status: {status.get('status')}",
    )

    if require_etsy:
        missing = etsy_adapter.missing_settings()
        add("etsy_connection", not missing, "Connected." if not missing else "Missing: " + ", ".join(missing))

    passed = all(item["passed"] for item in checks)
    report = {
        "ready": passed,
        "require_etsy": require_etsy,
        "factory": "CRAFT",
        "checks": checks,
    }
    (folder / "publish-readiness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
