"""Add production metadata

Revision ID: a43f7f4c2a8d
Revises: d0cb1a7cee7e
Create Date: 2026-06-12 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a43f7f4c2a8d"
down_revision = "d0cb1a7cee7e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))

    with op.batch_alter_table("passkey_credential", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
        batch_op.add_column(sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("passkey_credential", schema=None) as batch_op:
        batch_op.drop_column("last_used_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
