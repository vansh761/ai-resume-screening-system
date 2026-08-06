"""Years-of-experience extraction."""

import re

_EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\b(?:\s*(?:of\s*)?experience)?",
    re.IGNORECASE,
)


def extract_years_experience(text: str) -> float | None:
    if not text:
        return None

    matches = _EXPERIENCE_PATTERN.findall(text)
    if not matches:
        return None

    years = [float(m) for m in matches]
    plausible_years = [y for y in years if 0 < y <= 60]
    if not plausible_years:
        return None

    return max(plausible_years)
