"""requirement fields code epic priority moscow implementation status acceptance criteria stakeholder type

Revision ID: 32fcce4aeac2
Revises: 8f300c5c6553
Create Date: 2026-10-06 16:55:13.728241

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '32fcce4aeac2'
down_revision: str | None = '8f300c5c6553'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

priority_moscow = postgresql.ENUM(
    'must', 'should', 'could', 'wont', name='priority_moscow', create_type=False
)
implementation_status = postgresql.ENUM(
    'implemented', 'partial', 'missing', 'planned', 'unknown',
    name='implementation_status', create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    priority_moscow.create(bind, checkfirst=True)
    implementation_status.create(bind, checkfirst=True)

    op.add_column('requirements', sa.Column('stakeholder_type_id', sa.UUID(), nullable=True))
    op.add_column('requirements', sa.Column('code', sa.String(length=50), nullable=True))
    op.add_column('requirements', sa.Column('epic', sa.String(length=300), nullable=True))
    op.add_column('requirements', sa.Column('acceptance_criteria', sa.Text(), nullable=True))
    op.add_column('requirements', sa.Column('priority_moscow', priority_moscow, nullable=True))
    op.add_column(
        'requirements', sa.Column('implementation_status', implementation_status, nullable=True)
    )
    op.alter_column('requirements', 'stakeholder_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_index('uq_requirement_project_code', 'requirements', ['project_id', 'code'], unique=True, postgresql_where=sa.text('code IS NOT NULL'))
    op.create_foreign_key('fk_requirements_stakeholder_type', 'requirements', 'positions', ['stakeholder_type_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_requirements_stakeholder_type', 'requirements', type_='foreignkey')
    op.drop_index('uq_requirement_project_code', table_name='requirements', postgresql_where=sa.text('code IS NOT NULL'))
    op.alter_column('requirements', 'stakeholder_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('requirements', 'implementation_status')
    op.drop_column('requirements', 'priority_moscow')
    op.drop_column('requirements', 'acceptance_criteria')
    op.drop_column('requirements', 'epic')
    op.drop_column('requirements', 'code')
    op.drop_column('requirements', 'stakeholder_type_id')
    op.execute("DROP TYPE IF EXISTS priority_moscow")
    op.execute("DROP TYPE IF EXISTS implementation_status")
