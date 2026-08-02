"""add ticket category, SLA due date, and ticket comments

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('category', sa.String(length=20), nullable=False, server_default='IT'))
    op.add_column('tickets', sa.Column('sla_due_at', sa.DateTime(), nullable=True))

    op.create_table(
        'ticket_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('ticket_comments')
    op.drop_column('tickets', 'sla_due_at')
    op.drop_column('tickets', 'category')
