"""add subject education_levels

Revision ID: e2a7f4c9b3d1
Revises: c1d005e18aed
Create Date: 2026-09-22 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import database


# revision identifiers, used by Alembic.
revision: str = 'e2a7f4c9b3d1'
down_revision: Union[str, Sequence[str], None] = 'c1d005e18aed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('subjects', sa.Column('education_levels', database.JSONDict(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('subjects', 'education_levels')
