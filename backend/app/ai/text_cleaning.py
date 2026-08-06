"""Text cleaning - normalizes raw extracted text."""

import re
import unicodedata


def clean_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    normalized = unicodedata.normalize("NFKC", raw_text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]

    cleaned_lines: list[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run <= 1:
                cleaned_lines.append(line)
        else:
            blank_run = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
