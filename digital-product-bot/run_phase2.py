import phase2
from market_probe import research_market_data


def researched_market(phrase: str, config: dict) -> phase2.MarketEvidence:
    data = research_market_data(phrase, config)
    return phase2.MarketEvidence(**data)


phase2.research_market = researched_market


if __name__ == "__main__":
    raise SystemExit(phase2.main())
