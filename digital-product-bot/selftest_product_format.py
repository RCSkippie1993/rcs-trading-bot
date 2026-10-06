from __future__ import annotations

from product_format import factory_for_phrase, factory_readiness, preferred_format


def main():
    assert preferred_format("weekly planner word download") == "DOCX"
    assert preferred_format("wedding budget spreadsheet google sheets") == "XLSX"
    assert preferred_format("printable pet sitter checklist pdf") == "PDF_PRINTABLE"
    assert preferred_format("content planner") == "FLEXIBLE"
    assert preferred_format("pixel party favor box printable") == "PAPERCRAFT"
    assert preferred_format("leather wallet pattern pdf") == "LEATHER_PATTERN"
    assert preferred_format("felt fox sewing pattern pdf") == "FELT_PATTERN"

    assert factory_readiness("social media content calendar template excel")[0] is True
    assert factory_readiness("weekly planner word download")[0] is False
    assert factory_readiness("notion content planner template")[0] is False
    assert factory_readiness("pixel party favor box printable")[0] is True
    assert factory_readiness("leather wallet pattern pdf")[0] is True
    assert factory_readiness("felt fox sewing pattern pdf")[0] is True
    assert factory_readiness("kids costume sewing pattern printable")[0] is False

    assert factory_for_phrase("pixel party favor box printable") == "CRAFT"
    assert factory_for_phrase("leather wallet pattern pdf") == "CRAFT"
    assert factory_for_phrase("felt fox sewing pattern pdf") == "CRAFT"
    assert factory_for_phrase("inventory tracker spreadsheet") == "BUSINESS"

    print("product format self-test passed")


if __name__ == "__main__":
    main()
