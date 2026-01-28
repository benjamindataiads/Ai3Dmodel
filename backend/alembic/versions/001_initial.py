"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sections table FIRST (projects references it)
    op.create_table(
        'sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('position', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create projects table with section_id
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('position', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create parts table
    op.create_table(
        'parts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('bounding_box', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'generated', 'error', name='partstatus'), nullable=False, default='draft'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    
    # Create part_versions table
    op.create_table(
        'part_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('part_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('parts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('bounding_box', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('source', sa.String(50), default='manual'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    
    # Create indexes
    op.create_index('ix_parts_project_id', 'parts', ['project_id'])
    op.create_index('ix_part_versions_part_id', 'part_versions', ['part_id'])
    op.create_index('ix_part_versions_created_at', 'part_versions', ['created_at'])
    op.create_index('ix_projects_section_id', 'projects', ['section_id'])


def downgrade() -> None:
    op.drop_index('ix_projects_section_id')
    op.drop_index('ix_part_versions_created_at')
    op.drop_index('ix_part_versions_part_id')
    op.drop_index('ix_parts_project_id')
    op.drop_table('part_versions')
    op.drop_table('parts')
    op.drop_table('projects')
    op.drop_table('sections')
    op.execute('DROP TYPE IF EXISTS partstatus')
