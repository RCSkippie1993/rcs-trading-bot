from __future__ import annotations

import re

from craft_factory.craft_router import route_craft_phrase


EXPLICIT_FORMATS = {
    "word": "DOCX",
    "docx": "DOCX",
    "pdf": "PDF",
    "printable": "PDF_PRINTABLE",
    "canva": "CANVA",
    "notion": "NOTION",
    "powerpoint": "PPTX",
    "ppt": "PPTX",
    "excel": "XLSX",
    "xlsx": "XLSX",
    "google sheets": "XLSX",
    "spreadsheet": "XLSX",
    "csv": "CSV",
    "svg": "SVG_CUT",
    "dxf": "DXF",
}


def preferred_format(phrase: str) -> str:
    craft = route_craft_phrase(phrase)
    if craft.factory != "NONE":
        return craft.format

    text = phrase.lower()
    for key in [
        "google sheets", "powerpoint", "printable", "notion", "canva",
        "docx", "word", "pdf", "xlsx", "excel", "spreadsheet", "csv",
        "svg", "dxf"
    ]:
        if re.search(rf"\b{re.escape(key)}\b", text):
            return EXPLICIT_FORMATS[key]

    if any(term in text for term in ["tracker", "calculator", "dashboard", "budget", "inventory"]):
        return "XLSX"
    if any(term in text for term in ["checklist", "planner", "calendar", "worksheet"]):
        return "FLEXIBLE"
    return "FLEXIBLE"


def factory_for_phrase(phrase: str) -> str:
    craft = route_craft_phrase(phrase)
    if craft.factory != "NONE":
        return craft.factory

    fmt = preferred_format(phrase)
    if fmt in {"XLSX", "CSV", "FLEXIBLE"}:
        return "BUSINESS"
    if fmt in {"PDF", "PDF_PRINTABLE", "DOCX", "PPTX"}:
        return "PRINTABLE"
    return "EXPAND"


def factory_readiness(phrase: str) -> tuple[bool, str, str]:
    craft = route_craft_phrase(phrase)
    if craft.factory != "NONE":
        return craft.ready, craft.format, craft.reason

    fmt = preferred_format(phrase)
    if fmt in {"XLSX", "CSV", "FLEXIBLE"}:
        return True, fmt, "Business/productivity factory can build this editable spreadsheet/toolkit."
    return False, fmt, f"Demand calls for {fmt}; no production factory is enabled for this format yet."


def readiness_label(phrase: str) -> str:
    ready, fmt, _ = factory_readiness(phrase)
    factory = factory_for_phrase(phrase)
    if ready:
        return f"{factory} READY ({fmt})"
    return f"{factory} EXPAND ({fmt})"
