"""add resume extraction fields

Revision ID: 45807443fb3d
Revises: 37ce979121ae
Create Date: 2026-07-14 06:48:04.763820

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.db.base_class  # noqa: F401

revision: str = '45807443fb3d'
down_revision: Union[str, None] = '37ce979121ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    education_level_enum = sa.Enum(
        'HIGH_SCHOOL', 'ASSOCIATE', 'BACHELOR', 'MASTER', 'DOCTORATE',
        name='education_level'
    )
    education_level_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('resumes', sa.Column('extracted_years_experience', sa.Float(), nullable=True))
    op.add_column('resumes', sa.Column('extracted_education_level', education_level_enum, nullable=True))


def downgrade() -> None:
    op.drop_column('resumes', 'extracted_education_level')
    op.drop_column('resumes', 'extracted_years_experience')

    sa.Enum(name='education_level').drop(op.get_bind(), checkfirst=True)
