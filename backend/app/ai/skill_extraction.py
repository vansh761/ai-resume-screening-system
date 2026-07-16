"""
Skill extraction via dictionary/gazetteer matching.

Design decision
----------------
We use spaCy's `PhraseMatcher` against the known `Skill` vocabulary
rather than spaCy's statistical NER or a general-purpose LLM call.
Reasoning:

1. **Precision.** A resume that says "Python" should match the skill
   "Python" — full stop. Statistical NER models trained on general
   text frequently misclassify niche technical terms (mistaking
   "Kafka" the tool for a person's surname, for instance), because
   they weren't trained specifically on technical vocabulary.
2. **Explainability.** Every match traces back to an exact, known
   `Skill` row — a recruiter can be told precisely *why* "Docker"
   was detected (it matched the literal string), which the scoring
   engine's explainability requirement (Milestone 7) depends on.
3. **Speed.** Phrase matching against a vocabulary of a few hundred
   terms is near-instant, no model inference required.

The trade-off, worth stating plainly: this approach only finds skills
that are already in the `Skill` table. A resume mentioning a skill we
haven't seeded (e.g., a brand-new framework) won't be detected until
someone adds it to the vocabulary. This is an acceptable trade-off for
an explainable, auditable system — the alternative (a model that
"guesses" at skills) trades explainability for a marginal recall gain.

We use `spacy.blank("en")` — a tokenizer with no statistical model
attached — rather than downloading `en_core_web_sm`. Phrase matching
only needs tokenization, not the full NLP pipeline (POS tagging, NER,
etc.), so skipping the model download keeps the Docker image smaller
and the build faster without sacrificing anything this module needs.
"""

from functools import lru_cache

import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill


@lru_cache
def _get_nlp():
    """
    Returns a cached blank English spaCy pipeline (tokenizer only).

    Cached at module level because building even a blank pipeline has
    nonzero cost — we want to pay it once per process, not once per
    resume.
    """
    return spacy.blank("en")


def build_skill_matcher(skill_names: list[str]) -> PhraseMatcher:
    """
    Builds a PhraseMatcher from a list of canonical skill names.

    Matching is case-insensitive (`attr="LOWER"`) since resumes are
    written in all sorts of casing conventions ("PYTHON", "Python",
    "python") that should all match the same canonical skill.
    """
    nlp = _get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(name) for name in skill_names]
    matcher.add("SKILL", patterns)
    return matcher


def extract_skill_names(text: str, skill_names: list[str]) -> set[str]:
    """
    Returns the set of canonical skill names found in `text`.

    Deduplicates by canonical name even if a skill is mentioned
    multiple times in the resume — for skill *matching* purposes,
    "mentioned 3 times" and "mentioned once" carry the same signal in
    this milestone. Frequency-weighted signal is a documented future
    improvement, not attempted here.
    """
    if not text:
        return set()

    nlp = _get_nlp()
    matcher = build_skill_matcher(skill_names)
    doc = nlp(text)
    matches = matcher(doc)

    name_by_lower = {name.lower(): name for name in skill_names}
    found: set[str] = set()
    for _, start, end in matches:
        matched_text = doc[start:end].text.lower()
        if matched_text in name_by_lower:
            found.add(name_by_lower[matched_text])
    return found


def extract_skills_for_resume(db: Session, text: str) -> list[Skill]:
    """
    Extracts skills from resume text and returns the matching `Skill`
    ORM rows from the database (not just names) — callers need the
    actual rows to create `ResumeSkill` association records.
    """
    all_skills = db.execute(select(Skill)).scalars().all()
    skill_names = [s.name for s in all_skills]
    found_names = extract_skill_names(text, skill_names)
    return [s for s in all_skills if s.name in found_names]
