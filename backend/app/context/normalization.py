"""Normalize human-entered list fragments without splitting compound names."""

import re


def context_label(value: str) -> str:
    label = " ".join(value.split()).strip(" ,;•")
    # Oxford-comma fragments arrive as a distinct field, e.g. ', and Invoicing'.
    # Preserve internal conjunctions such as 'Research and Development'.
    return re.sub(r"^(?:and|&)\s+", "", label, flags=re.IGNORECASE).strip()


def context_list(values: list[str]) -> list[str]:
    result: dict[str, str] = {}
    for value in values:
        label = context_label(value)
        if label:
            result.setdefault(label.casefold(), label)
    return list(result.values())
