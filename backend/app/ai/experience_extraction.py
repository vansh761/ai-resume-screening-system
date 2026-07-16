"""
Years-of-experience extraction.

Design decision
----------------
Regex against known phrasings ("5+ years of experience", "3 years
experience in...") rather than a statistical model. Resumes express
experience in a small number of highly conventional ways — this is
exactly the kind of deterministic pattern where a model would add
inference cost and unpredictability without improving accuracy over a
well-tested regex. When multiple mentions are found (e.g., "5+ years
of Python" and "8 years of experience" in different sections), we take
the maximum, on the assumption that the highest stated figure is the
candidate's total professional experience and smaller figures refer to
specific skills within that span.

This deliberately does NOT attempt to compute experience by parsing
employment date ranges (e.g., "Jan 2019 - Present") and summing gaps —
that requires reliably segmenting a resume into a work-history section
first, which is a substantially harder structured-parsing problem.
Documented as a future improvement once section segmentation exists.
"""

import re

# Matches: "5 years", "5+ years", "5 yrs", optionally followed by
# "of experience" / "experience in" / etc. The number is captured; the
# "of experience"/"experience" suffix is optional so we also catch
# phrasings like "Python (5+ years)".
_EXPERIENCE_PATTERN = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)\b(?:\s*(?:of\s*)?experience)?",
    re.IGNORECASE,
)


def extract_years_experience(text: str) -> float | None:
    """
    Returns the maximum years-of-experience figure found in `text`, or
    None if no such figure appears anywhere.
    """
    if not text:
        return None

    matches = _EXPERIENCE_PATTERN.findall(text)
    if not matches:
        return None

    years = [float(m) for m in matches]
    # Sanity bound: reject implausible figures (e.g., "404 years" from
    # a mis-matched phone number or ID) rather than silently returning
    # nonsense to the scoring engine downstream.
    plausible_years = [y for y in years if 0 < y <= 60]
    if not plausible_years:
        return None

    return max(plausible_years)
