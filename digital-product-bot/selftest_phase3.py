from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import phase2
import phase3
import phase3_checks


def sample_decision() -> phase2.Decision:
    evidence = phase2.MarketEvidence(
        platform_hits={"etsy": 3, "gumroad": 2},
        sampled_prices_usd=[8.0, 12.0, 15.0],
        median_price_usd=12.0,
        evidence_queries=["test"],
        errors=[],
    )
    return phase2.Decision(
        phrase="small business project tracker spreadsheet",
        base_score=78,
        commercial_score=84,
        decision="CREATE",
        kind="tracker",
        signal_count=4,
        sources=["test"],
        market_evidence=evidence,
        reasons=["test"],
    )


def sample_craft_decision() -> phase2.Decision:
    evidence = phase2.MarketEvidence(
        platform_hits={"etsy": 2, "gumroad": 4},
        sampled_prices_usd=[6.0, 8.0, 12.0],
        median_price_usd=8.0,
        evidence_queries=["test-craft"],
        errors=[],
    )
    return phase2.Decision(
        phrase="printable gift box template pdf",
        base_score=83,
        commercial_score=83,
        decision="CREATE",
        kind="papercraft",
        signal_count=2,
        sources=["test"],
        market_evidence=evidence,
        reasons=["test"],
    )


def test_queue_decode():
    row = {"slug": "sample-product", "phrase": "sample product"}
    encoded = base64.urlsafe_b64encode(json.dumps([row]).encode()).decode()
    body = f"<!-- DIGITAL_PRODUCT_QUEUE:{encoded} -->"
    assert phase3.decode_queue(body)[0]["slug"] == "sample-product"


def test_final_assets():
    with tempfile.TemporaryDirectory() as tmp:
        folder, zip_path, marketplace, readiness = phase3.finalise(sample_decision(), Path(tmp))

        assert zip_path.exists()
        assert zip_path.stat().st_size > 0
        assert (folder / "marketplace-listing.json").exists()
        assert (folder / "publish-readiness.json").exists()
        assert marketplace["approval_status"] == "APPROVED_NOT_PUBLISHED"
        assert marketplace["publish_readiness"] is True

        images = sorted(folder.glob("listing-image-*.png"))
        assert len(images) == 7
        for image in images:
            assert image.stat().st_size > 1000

        pricing = marketplace["pricing"]
        assert pricing["floor_price_usd"] < pricing["recommended_price_usd"] < pricing["premium_price_usd"]
        assert 1 <= len(marketplace["etsy_tags"]) <= 13
        assert all(len(tag) <= 20 for tag in marketplace["etsy_tags"])
        assert len(marketplace["title"]) <= 140
        assert marketplace["display_name"] == "Small Business Project Tracker Spreadsheet – Editable Template"

        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "APPROVED_NOT_PUBLISHED"
        assert status["publishing_enabled"] is False
        assert status["phase3_version"] == "3.6"

        assert readiness["ready"] is True
        assert all(item["passed"] for item in readiness["checks"])


def test_craft_finalise_preserves_craft_files():
    with tempfile.TemporaryDirectory() as tmp:
        folder, zip_path, marketplace, readiness = phase3.finalise(sample_craft_decision(), Path(tmp))

        assert marketplace["factory"] == "CRAFT"
        assert zip_path.exists() and zip_path.stat().st_size > 0
        assert readiness["ready"] is True

        assert len(list(folder.glob("Shapes/*/A4/*.pdf"))) >= 1
        assert len(list(folder.glob("Shapes/*/US-Letter/*.pdf"))) >= 1
        assert len(list(folder.glob("Shapes/*/SVG/*.svg"))) >= 1
        assert len(list((folder / "Listing-Images").glob("listing-image-*.png"))) == 7

        assert not list(folder.rglob("*.xlsx"))
        assert not list(folder.rglob("*.csv"))

        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "APPROVED_NOT_PUBLISHED"
        assert status["publishing_enabled"] is False
        assert status["phase3_version"] == "3.7-craft"

        assert marketplace["approval_status"] == "APPROVED_NOT_PUBLISHED"
        assert marketplace["publish_readiness"] is True
        assert marketplace["display_name"] == "Printable Gift Box – PDF & SVG Craft Pattern"


def test_readiness_blocks_missing_asset():
    with tempfile.TemporaryDirectory() as tmp:
        folder, zip_path, marketplace, _ = phase3.finalise(sample_decision(), Path(tmp))
        first_image = sorted(folder.glob("listing-image-*.png"))[0]
        first_image.unlink()
        report = phase3_checks.validate(folder, zip_path, marketplace, require_etsy=False)
        assert report["ready"] is False
        assert "listing_images" in phase3_checks.failure_summary(report)


if __name__ == "__main__":
    test_queue_decode()
    test_final_assets()
    test_craft_finalise_preserves_craft_files()
    test_readiness_blocks_missing_asset()
    assert __import__("phase3_copy").human_product_name("social media content calendar template excel") == "Social Media Content Calendar – Excel Template"
    assert __import__("phase3_copy").human_product_name("content planner template google sheets") == "Content Planner – Google Sheets Template"
    print("phase3.7 approval-routing self-test passed")
