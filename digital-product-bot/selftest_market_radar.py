from __future__ import annotations

import bot
from market_segments import segment_for_phrase


def main():
    config = bot.load_config()
    seeds = config.get("seed_markets", [])
    assert len(seeds) >= 90, f"Expected at least 90 seed markets, got {len(seeds)}"
    assert len(set(seeds)) == len(seeds), "Seed markets must be unique"
    assert config.get("phase2_research_candidates", 0) >= 30

    assert segment_for_phrase("social media content calendar template excel") == "Creator & Content"
    assert segment_for_phrase("wedding budget spreadsheet") == "Events & Weddings"
    assert segment_for_phrase("job application tracker") == "Career & Job Search"
    assert segment_for_phrase("pet care planner") == "Pets"

    print("market radar expansion self-test passed")


if __name__ == "__main__":
    main()
