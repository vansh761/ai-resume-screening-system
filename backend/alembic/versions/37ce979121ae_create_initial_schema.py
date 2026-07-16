"""create initial schema (placeholder — original migration file was lost
during a git history cleanup; the schema it describes is already
applied to the database, confirmed via `alembic_version`. This file
exists only to restore Alembic's revision graph, not to re-run DDL.)

Revision ID: 37ce979121ae
Revises:
Create Date: 2026-07-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.base_class


revision: str = '37ce979121ae'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: this schema state is already applied to the database.
    pass


def downgrade() -> None:
    # No-op: intentionally not reversible via this placeholder.
    pass
