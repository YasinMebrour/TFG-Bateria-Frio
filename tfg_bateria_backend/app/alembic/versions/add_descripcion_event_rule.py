"""Add descripcion to event_rules

Revision ID: 01d9b673df9b
Revises: c23f43cbf146
Create Date: 2025-06-03 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '01d9b673df9b'
down_revision: Union[str, None] = 'c23f43cbf146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('event_rules', sa.Column('descripcion', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('event_rules', 'descripcion')
