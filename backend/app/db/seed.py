"""
Database seeding script.

Run with: python -m app.db.seed

Design decision
----------------
This is idempotent — running it multiple times never creates
duplicate rows, because it checks for an existing skill by name before
inserting. This matters because seeding isn't a one-time setup step
in practice: it gets re-run every time a fresh database is spun up
(new dev machine, CI pipeline, a teammate's first `docker compose up`),
and "safe to run repeatedly" is what makes that painless rather than
error-prone.

Kept as a standalone script (not folded into an Alembic migration)
deliberately: migrations should describe schema *shape*, not populate
reference data — mixing the two makes migrations harder to reason
about and re-run. This is the same separation most production systems
use: migrations for schema, seed scripts for reference/lookup data.
"""

from app.core.logging_config import configure_logging, get_logger
from app.data.skill_seed_data import SKILL_SEED_DATA
from app.db.session import SessionLocal
from app.models.skill import Skill

logger = get_logger(__name__)


def seed_skills() -> None:
    """Inserts every skill in `SKILL_SEED_DATA` that doesn't already exist."""
    db = SessionLocal()
    try:
        existing_names = {name for (name,) in db.query(Skill.name).all()}
        new_skills = [
            Skill(name=entry["name"], category=entry["category"])
            for entry in SKILL_SEED_DATA
            if entry["name"] not in existing_names
        ]

        if not new_skills:
            logger.info("Skills table already up to date; nothing to seed.")
            return

        db.add_all(new_skills)
        db.commit()
        logger.info(f"Seeded {len(new_skills)} new skills (total in dataset: {len(SKILL_SEED_DATA)}).")
    finally:
        db.close()


if __name__ == "__main__":
    configure_logging()
    seed_skills()
