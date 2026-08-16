"""add player code and nationality

Revision ID: 2be721c10000
Revises: f8f876872f5b
Create Date: 2026-08-16 12:10:26.734506

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2be721c10000"
down_revision: Union[str, Sequence[str], None] = "f8f876872f5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("players", sa.Column("code", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("nationality", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("players", "nationality")
    op.drop_column("players", "code")
