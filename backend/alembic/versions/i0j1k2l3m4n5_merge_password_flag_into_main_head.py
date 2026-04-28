"""merge password flag branch into main head

Revision ID: i0j1k2l3m4n5
Revises: g1h2i3j4k5l6, h9i0j1k2l3m4
Create Date: 2026-04-28

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "i0j1k2l3m4n5"
down_revision: Union[str, Sequence[str], None] = ("g1h2i3j4k5l6", "h9i0j1k2l3m4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE aura_norm.users
            ADD COLUMN IF NOT EXISTS using_default_import_password
            BOOLEAN NOT NULL DEFAULT FALSE
            """
        )
    )


def downgrade() -> None:
    pass
