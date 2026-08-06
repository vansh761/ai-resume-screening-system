"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.base_class  # noqa: F401  -- required: autogenerate references app.db.base_class.GUID() by dotted path but does not emit this import itself (a documented Alembic limitation for user-defined types).
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    # NOTE: if this migration adds a column with a NEW sa.Enum(...) type
    # (i.e. not already used by an existing table), Postgres needs that
    # enum TYPE created explicitly first -- CREATE TABLE auto-creates
    # enum types as a side effect, but ALTER TABLE ADD COLUMN does not.
    # Pattern: `my_enum = sa.Enum(..., name="..."); my_enum.create(op.get_bind(), checkfirst=True)`
    # before the add_column call, and `.drop(op.get_bind(), checkfirst=True)`
    # in downgrade() after dropping the column. (Hit this in Milestone 5 --
    # see docs/MILESTONES.md for the full story.)
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
