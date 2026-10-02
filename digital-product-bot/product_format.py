from __future__ import annotations

import re


EXPLICIT_FORMATS = {
    "word": "DOCX",
    "docx": "DOCX",
    "pdf": "PDF",
    "printable": "PDF",
    "canva": "CANVA",
    "notion": "NOTION",
    "powerpoint": "PPTX",
    "ppt": "PPTX",
    "excel": "XLSX",
    "xlsx": "XLSX",
    "google sheets": "XLSX",
    "spreadsheet": "XLSX",
    "csv": "CSV",
}


def preferred_format(phrase: str) -> str:
    text = phrase.lower()
    for key in ["google sheets", "powerpoint", "printable", "notion", "canva", "docx", "word", "pdf", "xlsx", "excel", "spreadsheet", "csv"]:
        if re.search(rf"\b{re.escape(key)}\b", text):
            return EXPLICIT_FORMATS[key]

    if any(term in text for term in ["tracker", "calculator", "dashboard", "budget", "inventory"]):
        return "XLSX"
    if any(term in text for term in ["checklist", "planner", "calendar", "worksheet"]):
        return "FLEXIBLE"
    return "FLEXIBLE"


def factory_readiness(phrase: str) -> tuple[bool, str, str]:
    fmt = preferred_format(phrase)
    if fmt in {"XLSX", "CSV", "FLEXIBLE"}:
        return True, fmt, "Current factory can build this format as an editable spreadsheet/toolkit."
    return False, fmt, f"Demand explicitly calls for {fmt}; current factory should not substitute a spreadsheet."


def readiness_label(phrase: str) -> str:
    ready, fmt, _ = factory_readiness(phrase)
    return f"READY ({fmt})" if ready else f"EXPAND FACTORY ({fmt})"
