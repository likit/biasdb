"""empty message

Revision ID: 5dbb84329760
Revises: d3c42c6d13d0
Create Date: 2019-04-13 10:16:18.295599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5dbb84329760'
down_revision = 'd3c42c6d13d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organisms',
        sa.Column('taxid', sa.Integer),
        sa.Column('species', sa.String(), index=True),
        sa.Column('parentid', sa.Integer)
    )


def downgrade():
    op.drop_table('organisms')
