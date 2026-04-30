"""Add telegram fields to usuarios"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '01d9b673df9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('telegram_chat_id', sa.String(length=50), nullable=True))
    op.add_column('usuarios', sa.Column('telegram_notify', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('usuarios', sa.Column('telegram_bot_token', sa.String(length=120), nullable=True))
    op.alter_column('usuarios', 'telegram_notify', server_default=None)


def downgrade() -> None:
    op.drop_column('usuarios', 'telegram_notify')
    op.drop_column('usuarios', 'telegram_chat_id')
    op.drop_column('usuarios', 'telegram_bot_token')
