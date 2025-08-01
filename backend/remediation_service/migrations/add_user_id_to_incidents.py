"""Add user_id to incidents table

Revision ID: add_user_id_001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_user_id_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add user_id column to incidents table
    op.add_column('incidents', sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))
    
    # Create index on user_id for better query performance
    op.create_index('ix_incidents_user_id', 'incidents', ['user_id'])

def downgrade():
    # Remove index and column
    op.drop_index('ix_incidents_user_id', 'incidents')
    op.drop_column('incidents', 'user_id')