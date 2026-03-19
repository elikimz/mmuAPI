"""add status fields to user_levels and user_tasks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-19 00:00:00.000000

Adds:
  - user_levels.status  VARCHAR default 'active'
  - user_tasks.status   VARCHAR default 'active'

Existing rows are back-filled to 'active' so the system treats all
pre-migration data as active until the scheduler runs its first expiry check.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column to user_levels
    try:
        op.add_column(
            'user_levels',
            sa.Column('status', sa.String(), nullable=False, server_default='active')
        )
    except Exception:
        pass  # Column already exists

    # Add status column to user_tasks
    try:
        op.add_column(
            'user_tasks',
            sa.Column('status', sa.String(), nullable=False, server_default='active')
        )
    except Exception:
        pass  # Column already exists

    # Back-fill existing rows to 'active'
    op.execute("UPDATE user_levels SET status = 'active' WHERE status IS NULL OR status = ''")
    op.execute("UPDATE user_tasks  SET status = 'active' WHERE status IS NULL OR status = ''")


def downgrade() -> None:
    try:
        op.drop_column('user_tasks', 'status')
    except Exception:
        pass
    try:
        op.drop_column('user_levels', 'status')
    except Exception:
        pass
