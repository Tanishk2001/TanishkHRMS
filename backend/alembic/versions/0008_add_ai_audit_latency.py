"""add latency_ms to ai_audit_logs

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Powers the AI usage dashboard's "average response latency" metric.
    # Nullable because rows written before this migration have no value.
    op.add_column('ai_audit_logs', sa.Column('latency_ms', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_audit_logs', 'latency_ms')
