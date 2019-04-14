"""added article_organism table

Revision ID: c68155c3e88d
Revises: 8daf730d39ce
Create Date: 2019-04-13 16:19:23.485486

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c68155c3e88d'
down_revision = '8daf730d39ce'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('organism_article',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=True),
    sa.Column('organism_taxid', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
    sa.ForeignKeyConstraint(['organism_taxid'], ['organisms.taxid'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('articles', sa.Column('processed', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('articles', 'processed')
    op.drop_table('organism_article')
    # ### end Alembic commands ###