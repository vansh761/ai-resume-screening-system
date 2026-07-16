"""
Education level extraction via keyword matching.

Same reasoning as skill extraction: degree levels are expressed in a
small, well-known vocabulary ("Bachelor's", "B.Tech", "M.Sc", "PhD"),
so keyword matching is precise and explainable where a general model
would add cost without improving accuracy. When multiple education
levels are mentioned (common — a resume often lists both a Bachelor's
and a Master's), we return the highest one found, since that's the
figure relevant to matching against a job's minimum requirement.
"""

import re

from app.models.resume import EducationLevel

# Ordered low-to-high, matching EducationLevel's own ordering, with
# each level mapped to the keyword variants that indicate it. This
# ordering directly determines which level "wins" when several appear.
_EDUCATION_KEYWORDS: list[tuple[EducationLevel, list[str]]] = [
    (EducationLevel.HIGH_SCHOOL, [r"high school", r"secondary school", r"\bhsc\b"]),
    (EducationLevel.ASSOCIATE, [r"associate'?s? degree", r"\ba\.?a\.?\b"]),
    (
        EducationLevel.BACHELOR,
        [
            r"bachelor'?s?",
            r"\bb\.?tech\b",
            r"\bb\.?e\.?\b",
            r"\bb\.?sc\.?\b",
            r"\bb\.?a\.?\b",
            r"\bbca\b",
            r"undergraduate degree",
        ],
    ),
    (
        EducationLevel.MASTER,
        [
            r"master'?s?",
            r"\bm\.?tech\b",
            r"\bm\.?e\.?\b",
            r"\bm\.?sc\.?\b",
            r"\bm\.?a\.?\b",
            r"\bmba\b",
            r"\bmca\b",
            r"graduate degree",
        ],
    ),
    (EducationLevel.DOCTORATE, [r"\bph\.?d\.?\b", r"doctorate", r"doctoral"]),
]

_COMPILED_KEYWORDS = [
    (level, [re.compile(pattern, re.IGNORECASE) for pattern in patterns])
    for level, patterns in _EDUCATION_KEYWORDS
]


def extract_education_level(text: str) -> EducationLevel | None:
    """
    Returns the highest education level mentioned in `text`, or None
    if no recognized education keyword appears at all.
    """
    if not text:
        return None

    highest_found: EducationLevel | None = None
    for level, patterns in _COMPILED_KEYWORDS:
        if any(pattern.search(text) for pattern in patterns):
            highest_found = level  # list is ordered low-to-high, so last match wins

    return highest_found
