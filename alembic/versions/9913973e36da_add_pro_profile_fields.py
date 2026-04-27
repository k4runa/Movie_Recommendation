"""add_pro_profile_fields

Revision ID: 9913973e36da
Revises: 0001_initial
Create Date: 2026-04-22 20:36:58.232217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9913973e36da'
down_revision: Union[str, Sequence[str], None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('social_links', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('favorite_genres', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'favorite_genres')
    op.drop_column('users', 'social_links')
    op.drop_column('users', 'full_name')
