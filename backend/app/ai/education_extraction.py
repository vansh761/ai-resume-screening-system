"""Education level extraction via keyword matching."""

import re

from app.models.resume import EducationLevel

_EDUCATION_KEYWORDS: list[tuple[EducationLevel, list[str]]] = [
    (EducationLevel.HIGH_SCHOOL, [r"high school", r"secondary school", r"\bhsc\b"]),
    (EducationLevel.ASSOCIATE, [r"associate'?s? degree", r"\ba\.?a\.?\b"]),
    (
        EducationLevel.BACHELOR,
        [
            r"bachelor'?s?", r"\bb\.?tech\b", r"\bb\.?e\.?\b", r"\bb\.?sc\.?\b",
            r"\bb\.?a\.?\b", r"\bbca\b", r"undergraduate degree",
        ],
    ),
    (
        EducationLevel.MASTER,
        [
            r"master'?s?", r"\bm\.?tech\b", r"\bm\.?e\.?\b", r"\bm\.?sc\.?\b",
            r"\bm\.?a\.?\b", r"\bmba\b", r"\bmca\b", r"graduate degree",
        ],
    ),
    (EducationLevel.DOCTORATE, [r"\bph\.?d\.?\b", r"doctorate", r"doctoral"]),
]

_COMPILED_KEYWORDS = [
    (level, [re.compile(pattern, re.IGNORECASE) for pattern in patterns])
    for level, patterns in _EDUCATION_KEYWORDS
]


def extract_education_level(text: str) -> EducationLevel | None:
    if not text:
        return None

    highest_found: EducationLevel | None = None
    for level, patterns in _COMPILED_KEYWORDS:
        if any(pattern.search(text) for pattern in patterns):
            highest_found = level

    return highest_found
