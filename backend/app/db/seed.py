"""Database seeding script. Run with: python -m app.db.seed"""

from app.core.logging_config import configure_logging, get_logger
from app.data.skill_seed_data import SKILL_SEED_DATA
from app.db.session import SessionLocal
from app.models.skill import Skill

logger = get_logger(__name__)


def seed_skills() -> None:
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
