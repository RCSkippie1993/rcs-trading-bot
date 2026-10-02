from __future__ import annotations

from product_format import factory_readiness, preferred_format


def main():
    assert preferred_format("weekly planner word download") == "DOCX"
    assert preferred_format("wedding budget spreadsheet google sheets") == "XLSX"
    assert preferred_format("printable pet sitter checklist pdf") == "PDF"
    assert preferred_format("content planner") == "FLEXIBLE"

    assert factory_readiness("social media content calendar template excel")[0] is True
    assert factory_readiness("weekly planner word download")[0] is False
    assert factory_readiness("notion content planner template")[0] is False

    print("product format self-test passed")


if __name__ == "__main__":
    main()
