"""Skill extraction via dictionary/gazetteer matching."""

from functools import lru_cache

import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill


@lru_cache
def _get_nlp():
    return spacy.blank("en")


def build_skill_matcher(skill_names: list[str]) -> PhraseMatcher:
    nlp = _get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(name) for name in skill_names]
    matcher.add("SKILL", patterns)
    return matcher


def extract_skill_names(text: str, skill_names: list[str]) -> set[str]:
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
    all_skills = db.execute(select(Skill)).scalars().all()
    skill_names = [s.name for s in all_skills]
    found_names = extract_skill_names(text, skill_names)
    return [s for s in all_skills if s.name in found_names]
