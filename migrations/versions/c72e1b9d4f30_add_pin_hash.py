
"""Add PIN hash to user.

Revision ID: c72e1b9d4f30
Revises: a43f7f4c2a8d
"""

from alembic import op
import sqlalchemy as sa

revision = "c72e1b9d4f30"
down_revision = "a43f7f4c2a8d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column("pin_hash", sa.String(length=256), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("pin_hash")
