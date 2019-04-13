"""initial revision

Revision ID: d3c42c6d13d0
Revises: 
Create Date: 2019-04-13 09:57:47.914154

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3c42c6d13d0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'articles',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('pmid', sa.String(), unique=True, index=True),
        sa.Column('pubyear', sa.Integer, nullable=False),
        sa.Column('data', sa.JSON()),
        sa.Column('term', sa.String()),
    )


def downgrade():
    op.drop_table('articles')
