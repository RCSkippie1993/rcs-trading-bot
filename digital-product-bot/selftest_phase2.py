import json
import tempfile
from pathlib import Path

import bot
import phase2


def make_opportunity(phrase, score=72, signals=2):
    return bot.Opportunity(
        phrase=phrase,
        score=score,
        signal_count=signals,
        sources=["google_suggest"],
        kind=bot.infer_kind(phrase),
        reason="test",
    )


def main():
    config = bot.load_config()

    a = make_opportunity("social media content calendar google sheets", 72, 2)
    b = make_opportunity("social media content calendar excel", 71, 2)
    c = make_opportunity("inventory tracker spreadsheet", 68, 2)
    clustered = phase2.cluster_opportunities([a, b, c], threshold=0.78)
    assert len(clustered) == 2, clustered

    evidence = phase2.MarketEvidence(
        platform_hits={"etsy": 2, "gumroad": 1},
        sampled_prices_usd=[9.0, 12.0, 15.0],
        median_price_usd=12.0,
        evidence_queries=["test"],
        errors=[],
    )
    decision = phase2.classify(a, evidence, config)
    assert decision.decision == "CREATE", decision
    assert decision.commercial_score >= config["create_threshold"]

    weak_evidence = phase2.MarketEvidence(
        platform_hits={"etsy": 0, "gumroad": 0},
        sampled_prices_usd=[],
        median_price_usd=None,
        evidence_queries=["test-no-market-evidence"],
        errors=[],
    )
    weak_decision = phase2.classify(a, weak_evidence, config)
    assert weak_decision.decision == "CREATE", weak_decision
    assert any("unverified" in reason.lower() for reason in weak_decision.reasons)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package = Path(phase2.enrich_product(decision, root, config))
        folder = root / bot.slugify(decision.phrase)
        assert package.exists()
        assert (folder / "listing-preview.png").exists()
        assert (folder / "market-research.json").exists()
        listing = json.loads((folder / "listing.json").read_text(encoding="utf-8"))
        assert listing["phase2"]["decision"] == "CREATE"
        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "AWAITING_APPROVAL"
        assert status["publishing_enabled"] is False

    print("digital-product-bot Phase 2 self-test passed")


if __name__ == "__main__":
    main()
