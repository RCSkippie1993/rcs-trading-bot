from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import bot
import phase2
import phase3


def test_queue_decode():
    row = {"slug": "sample-product", "phrase": "sample product"}
    encoded = base64.urlsafe_b64encode(json.dumps([row]).encode()).decode()
    body = f"<!-- DIGITAL_PRODUCT_QUEUE:{encoded} -->"
    assert phase3.decode_queue(body)[0]["slug"] == "sample-product"


def test_final_assets():
    evidence = phase2.MarketEvidence(
        platform_hits={"etsy": 3, "gumroad": 2},
        sampled_prices_usd=[8.0, 12.0, 15.0],
        median_price_usd=12.0,
        evidence_queries=["test"],
        errors=[],
    )
    decision = phase2.Decision(
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
    with tempfile.TemporaryDirectory() as tmp:
        folder, zip_path, marketplace = phase3.finalise(decision, Path(tmp))
        assert zip_path.exists()
        assert (folder / "marketplace-listing.json").exists()
        assert marketplace["approval_status"] == "APPROVED_NOT_PUBLISHED"
        assert len(list(folder.glob("listing-image-*.png"))) == 4
        status = json.loads((folder / "status.json").read_text())
        assert status["status"] == "APPROVED_NOT_PUBLISHED"
        assert status["publishing_enabled"] is False


if __name__ == "__main__":
    test_queue_decode()
    test_final_assets()
    print("phase3 self-test passed")
