"""add expiry_days to levels and expires_at to user_levels

Revision ID: a1b2c3d4e5f6
Revises: 3835e37d22e8
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3835e37d22e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add expiry_days to levels table
    op.add_column('levels', sa.Column('expiry_days', sa.Integer(), nullable=True))

    # Add expires_at to user_levels table
    op.add_column('user_levels', sa.Column('expires_at', sa.DateTime(), nullable=True))

    # Add created_at to user_levels if missing (it was missing from the initial migration)
    # Use try/except to handle cases where it may already exist
    try:
        op.add_column('user_levels', sa.Column('created_at', sa.DateTime(), nullable=True))
    except Exception:
        pass  # Column already exists


def downgrade() -> None:
    op.drop_column('user_levels', 'expires_at')
    op.drop_column('levels', 'expiry_days')
