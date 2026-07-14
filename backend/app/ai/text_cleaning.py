"""
Text cleaning — normalizes raw extracted text before it's stored or
fed into later NLP stages (NER, embeddings in Milestones 5-6).

Kept as its own module, separate from extraction, because cleaning
rules are format-agnostic (the same cleanup applies whether the text
came from a PDF or a DOCX) while extraction is deeply format-specific.
Mixing the two would make either concern harder to test in isolation.
"""

import re
import unicodedata


def clean_text(raw_text: str) -> str:
    """
    Normalizes extracted resume text:
    - Unicode normalization (NFKC) so visually-identical characters
      from different fonts/encodings compare equal later (important
      once Milestone 5's skill matching does string comparison).
    - Collapses runs of whitespace within a line to single spaces.
    - Collapses 3+ consecutive blank lines down to a single blank line
      (PDF extraction often leaves large vertical gaps as blank lines).
    - Strips leading/trailing whitespace from each line and the
      document as a whole.
    """
    if not raw_text:
        return ""

    normalized = unicodedata.normalize("NFKC", raw_text)

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]

    cleaned_lines: list[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run <= 1:  # keep at most one consecutive blank line
                cleaned_lines.append(line)
        else:
            blank_run = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
