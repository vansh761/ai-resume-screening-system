"""
Alembic environment configuration.

Design decision
----------------
We deliberately leave `sqlalchemy.url` blank in `alembic.ini` and set it
here from `app.core.config.settings` instead. Duplicating the database
URL in two config files (`.env` and `alembic.ini`) is a guaranteed way
to end up with them drifting out of sync — one source of truth wins.

We also import `app.models` (not individual model files) so that every
table is registered on `Base.metadata` before `autogenerate` runs — see
the docstring in `app/models/__init__.py` for why this matters.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the app's Base and all models — this registers every table on
# Base.metadata, which `autogenerate` diffs against the live database.
from app.core.config import settings
from app.db.base_class import Base
from app.models import *  # noqa: F401,F403  (imports register tables as a side effect)

config = context.config
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection — generates raw SQL.

    Useful for producing a `.sql` script to hand to a DBA in
    environments where the migration tool itself can't connect
    directly to production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection — the normal dev/CI path."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
