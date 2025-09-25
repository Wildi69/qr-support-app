"""add email_log observability fields

Revision ID: 40337e53cf25
Revises: 831682154725
Create Date: 2025-09-25 12:32:46.624734

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "40337e53cf25"
down_revision: Union[str, Sequence[str], None] = "831682154725"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("email_log") as batch_op:
        batch_op.add_column(sa.Column("provider_message_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("payload_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("email_log") as batch_op:
        batch_op.drop_column("payload_hash")
        batch_op.drop_column("error")
        batch_op.drop_column("provider_message_id")
