from __future__ import annotations

import re
from datetime import datetime
from typing import Any


PAGE_PARAGRAPH_RE = re.compile(
    r"Page\s+(\d+),\s*Paragraph\s+(\d+)",
    re.IGNORECASE,
)


def build_grounded_context(chunks: list[Any]) -> str:
    """
    Convert extracted DocumentChunk objects into a stable evidence context
    for Evon. Every paragraph receives an explicit page/paragraph label.
    """
    if not chunks:
        return ""

    lines: list[str] = []

    for chunk in chunks:
        page = getattr(chunk, "page_number", None)
        paragraph = getattr(chunk, "paragraph_index", None)
        text = str(getattr(chunk, "raw_text", "")).strip()

        if not text:
            continue

        lines.append(
            f"[Page {page}, Paragraph {paragraph}]\n{text}"
        )

    return "\n\n".join(lines)


def valid_source_locations(
    chunks: list[Any],
) -> set[str]:
    """
    Return the exact page/paragraph labels that actually exist
    in the extracted document.
    """
    result: set[str] = set()

    for chunk in chunks:
        page = getattr(chunk, "page_number", None)
        paragraph = getattr(chunk, "paragraph_index", None)

        if page is not None and paragraph is not None:
            result.add(f"Page {page}, Paragraph {paragraph}")

    return result


def validate_citations(
    citations: list[Any],
    chunks: list[Any],
) -> list[Any]:
    """
    Remove citations pointing to page/paragraph locations that do not
    exist in the extracted document.
    """
    valid_locations = valid_source_locations(chunks)
    validated = []

    for citation in citations or []:
        location = str(
            getattr(citation, "source_location", "")
        ).strip()

        match = PAGE_PARAGRAPH_RE.search(location)

        if not match:
            continue

        normalized = (
            f"Page {int(match.group(1))}, "
            f"Paragraph {int(match.group(2))}"
        )

        if normalized not in valid_locations:
            continue

        validated.append(citation)

    return validated


def extract_calendar_date(text: str) -> str | None:
    """
    Detect common Indian/English calendar-date formats from
    extracted notice text.
    """
    patterns = [
        r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](20\d{2})\b",
        r"\b(\d{1,2})\s+"
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+"
        r"(20\d{2})\b",
        r"\b(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
        r"\.?\s+(20\d{2})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            continue

        try:
            if "/" in match.group(0) or "-" in match.group(0):
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                dt = datetime(year, month, day)
            else:
                day = int(match.group(1))
                month_name = match.group(2).lower().rstrip(".")
                year = int(match.group(3))

                month_map = {
                    "january": 1,
                    "jan": 1,
                    "february": 2,
                    "feb": 2,
                    "march": 3,
                    "mar": 3,
                    "april": 4,
                    "apr": 4,
                    "may": 5,
                    "june": 6,
                    "jun": 6,
                    "july": 7,
                    "jul": 7,
                    "august": 8,
                    "aug": 8,
                    "september": 9,
                    "sep": 9,
                    "sept": 9,
                    "october": 10,
                    "oct": 10,
                    "november": 11,
                    "nov": 11,
                    "december": 12,
                    "dec": 12,
                }

                dt = datetime(
                    year,
                    month_map[month_name],
                    day,
                )

            return dt.strftime("%Y-%m-%d")

        except (ValueError, KeyError):
            continue

    return None


def extract_relative_days(text: str) -> int | None:
    """
    Detect phrases such as:
    - within 7 days
    - within seven days
    - respond in 15 days
    """
    numeric = re.search(
        r"(?:within|in|before|after)\s+(\d+)\s+"
        r"(?:day|days|din)\b",
        text,
        re.IGNORECASE,
    )

    if numeric:
        return int(numeric.group(1))

    word_numbers = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
    }

    word_pattern = (
        r"(?:within|in|before|after)\s+"
        r"(" + "|".join(word_numbers.keys()) + r")\s+"
        r"(?:day|days|din)\b"
    )

    word_match = re.search(
        word_pattern,
        text,
        re.IGNORECASE,
    )

    if word_match:
        return word_numbers[word_match.group(1).lower()]

    return None
