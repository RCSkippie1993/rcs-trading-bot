from __future__ import annotations

import bot
import phase2
from collections import Counter
from market_segments import segment_for_phrase


def main():
    config = bot.load_config()
    seeds = config.get("seed_markets", [])
    assert len(seeds) >= 90, f"Expected at least 90 seed markets, got {len(seeds)}"
    assert len(set(seeds)) == len(seeds), "Seed markets must be unique"
    assert config.get("phase2_research_candidates", 0) >= 30
    assert config.get("craft_research_quota", 0) >= 8

    sample = [
        bot.Opportunity("business tracker spreadsheet", 90, 2, ["test"], "tracker", "test"),
        bot.Opportunity("pixel party favor box printable", 82, 2, ["test"], "papercraft", "test"),
        bot.Opportunity("leather wallet pattern pdf", 80, 2, ["test"], "craft-pattern", "test"),
        bot.Opportunity("content calendar template", 79, 2, ["test"], "planner", "test"),
    ]
    pool = phase2.select_research_candidates(sample, limit=3, craft_quota=2)
    craft_count = sum(segment_for_phrase(x.phrase) in {"Kids Party & Papercraft", "Craft & DIY"} for x in pool)
    assert craft_count == 2, pool

    assert segment_for_phrase("social media content calendar template excel") == "Creator & Content"
    assert segment_for_phrase("wedding budget spreadsheet") == "Events & Weddings"
    assert segment_for_phrase("job application tracker") == "Career & Job Search"
    assert segment_for_phrase("pet care planner") == "Pets"
    assert segment_for_phrase("printable gift box template pdf") == "Kids Party & Papercraft"
    assert segment_for_phrase("leather dice bag pattern printable") == "Craft & DIY"

    assert bot.infer_kind("printable gift box template pdf") == "papercraft"
    assert bot.infer_kind("leather dice bag pattern printable") == "craft-pattern"

    free_item = bot.score_phrase(
        "printable favor box templates free download",
        Counter({"google_suggest": 1}),
        config,
    )
    paid_item = bot.score_phrase(
        "printable favor box templates",
        Counter({"google_suggest": 1}),
        config,
    )
    assert free_item is not None and paid_item is not None
    assert paid_item.score > free_item.score

    assert bot.score_phrase(
        "sewing pattern print shop near me",
        Counter({"google_suggest": 2}),
        config,
    ) is None

    print("market radar expansion self-test passed")


if __name__ == "__main__":
    main()
