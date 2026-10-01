import json
import tempfile
from collections import Counter
from pathlib import Path

import bot


def main():
    config = bot.load_config()
    candidate = bot.score_phrase(
        "small business project tracker spreadsheet",
        Counter({"google_suggest": 2, "reddit:smallbusiness": 1}),
        config,
    )
    assert candidate is not None
    assert candidate.score > 0
    assert candidate.kind == "tracker"

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        package = bot.create_product(candidate, root, config)
        assert package.exists()
        folder = root / bot.slugify(candidate.phrase)
        assert (folder / "status.json").exists()
        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "AWAITING_APPROVAL"
        assert status["publishing_enabled"] is False
        assert any(folder.glob("*.xlsx"))
        assert any(folder.glob("*.csv"))

    print("digital-product-bot self-test passed")


if __name__ == "__main__":
    main()
