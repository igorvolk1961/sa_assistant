"""requirement epics

Revision ID: e94efb165f4c
Revises: d3829b21fdd0
Create Date: 2026-10-06 17:57:30.206807

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e94efb165f4c'
down_revision: str | None = 'd3829b21fdd0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'requirement_epics',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=300), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name', name='uq_requirement_epic_name'),
    )
    op.add_column('requirements', sa.Column('epic_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_requirements_epic', 'requirements', 'requirement_epics', ['epic_id'], ['id']
    )
    op.drop_column('requirements', 'epic')


def downgrade() -> None:
    op.add_column('requirements', sa.Column('epic', sa.VARCHAR(length=300), nullable=True))
    op.drop_constraint('fk_requirements_epic', 'requirements', type_='foreignkey')
    op.drop_column('requirements', 'epic_id')
    op.drop_table('requirement_epics')
